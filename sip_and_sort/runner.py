"""1회 실행 오케스트레이션: 검색 → 후보 판별 → 분류/라벨 → (조건부) 답장 초안 → 요약.

메일은 절대 발송하지 않는다. 생성하는 것은 Gmail '초안(draft)' 뿐이다.
"""

from __future__ import annotations

import logging
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .classifier import Category, Scenario, categorize, check_candidate, detect_scenario, get_rules
from .message import Email, parse_message
from .templates import render_reply, reply_subject

log = logging.getLogger(__name__)


@dataclass
class MailResult:
    thread_id: str
    sender: str
    subject: str
    category: Category
    scenario: Scenario | None
    matched_keywords: list[str]
    reasons: list[str]
    draft_body: str | None = None

    @property
    def needs_review(self) -> bool:
        return self.scenario is None


@dataclass
class RunReport:
    dry_run: bool
    since_hours: float
    scanned_threads: int = 0
    results: list[MailResult] = field(default_factory=list)
    excluded_bulk: list[tuple[str, str, str]] = field(default_factory=list)  # (발신자, 제목, 사유)
    skipped_already_processed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)  # (thread_id, 메시지)

    def counts(self) -> dict[Category, int]:
        counter = Counter(r.category for r in self.results)
        return {c: counter.get(c, 0) for c in Category}

    @property
    def drafted(self) -> list[MailResult]:
        return [r for r in self.results if r.scenario is not None]

    @property
    def review_needed(self) -> list[MailResult]:
        return [r for r in self.results if r.scenario is None]


def build_query(after_epoch: int, extra_query: str = "") -> str:
    query = f"after:{after_epoch} -in:sent -in:draft -in:chats"
    return f"{query} {extra_query}".strip() if extra_query else query


def _latest_incoming(messages: list[Email], my_addresses: set[str]) -> Email | None:
    incoming = [
        m
        for m in messages
        if "SENT" not in m.label_ids
        and "DRAFT" not in m.label_ids
        and m.sender_email not in my_addresses
    ]
    return max(incoming, key=lambda m: m.internal_date_ms) if incoming else None


def run(
    client,
    config: dict[str, Any],
    *,
    since_hours: float | None = None,
    dry_run: bool = False,
    now: float | None = None,
) -> RunReport:
    hours = float(since_hours or config["lookback_hours"])
    report = RunReport(dry_run=dry_run, since_hours=hours)
    after_epoch = int((now if now is not None else time.time()) - hours * 3600)

    labels_cfg = config["gmail_labels"]
    category_labels = {c: labels_cfg[c.value] for c in Category}
    draft_done_label = labels_cfg["draft_done"]
    rules = get_rules(config)

    # 이미 처리된 스레드(우리 라벨이 하나라도 붙은 스레드)는 건너뛴다 → 반복 실행해도 안전(idempotent)
    existing_labels = client.list_labels()
    processed_ids = {
        existing_labels[name]
        for name in [*category_labels.values(), draft_done_label]
        if name in existing_labels
    }
    my_addresses = client.get_my_addresses() | {a.lower() for a in config.get("my_addresses") or []}

    query = build_query(after_epoch, config.get("extra_query", ""))
    log.debug("Gmail 검색어: %s", query)
    refs = client.search_messages(query, max_results=config["max_messages"])
    thread_ids = list(dict.fromkeys(ref["threadId"] for ref in refs))

    for thread_id in thread_ids:
        try:
            thread = client.get_thread(thread_id)
            messages = [parse_message(m) for m in thread.get("messages", [])]
            if any(processed_ids.intersection(m.label_ids) for m in messages):
                report.skipped_already_processed += 1
                continue
            mail = _latest_incoming(messages, my_addresses)
            if mail is None:
                continue
            report.scanned_threads += 1

            candidate = check_candidate(mail, config, my_addresses)
            if candidate.excluded_reason:
                report.excluded_bulk.append((mail.sender, mail.subject, candidate.excluded_reason))
                continue
            if not candidate.is_candidate:
                continue

            category = categorize(mail, rules)
            scenario_result = detect_scenario(mail, rules)
            result = MailResult(
                thread_id=thread_id,
                sender=mail.sender,
                subject=mail.subject,
                category=category,
                scenario=scenario_result.scenario,
                matched_keywords=candidate.matched_keywords,
                reasons=scenario_result.reasons,
            )
            if result.scenario is not None:
                result.draft_body = render_reply(config, result.scenario, mail)

            if not dry_run:
                _apply(client, mail, result, category_labels[category], draft_done_label)
            report.results.append(result)
        except Exception as exc:  # 한 스레드 실패가 전체 실행을 멈추지 않도록
            log.debug("스레드 %s 처리 실패", thread_id, exc_info=True)
            report.errors.append((thread_id, str(exc)))
    return report


def _apply(client, mail: Email, result: MailResult, category_label: str, draft_done_label: str):
    label_ids = [client.get_or_create_label(category_label)]
    if result.scenario is not None and result.draft_body:
        # 초안(draft)만 생성한다. 발송(send)은 하지 않는다.
        client.create_reply_draft(
            thread_id=mail.thread_id,
            to=mail.reply_to_address,
            subject=reply_subject(mail.subject),
            body=result.draft_body,
            in_reply_to=mail.message_id_header,
            references=mail.headers.get("references", ""),
        )
        label_ids.append(client.get_or_create_label(draft_done_label))
    try:
        client.add_thread_labels(mail.thread_id, label_ids)
    except Exception as exc:
        drafted = " (초안은 이미 생성됨)" if result.scenario else ""
        raise RuntimeError(f"라벨 부착 실패{drafted}: {exc}") from exc


# --------------------------------------------------------------------------- 요약 출력


def _pad(text: str, width: int) -> str:
    """한글(전각) 폭을 고려한 왼쪽 정렬."""
    used = sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)
    return text + " " * max(0, width - used)


def format_report(report: RunReport, *, show_drafts: bool = False, summary_only: bool = False) -> str:
    lines: list[str] = []
    bar = "=" * 60
    mode = " (DRY-RUN: 실제 변경 없음)" if report.dry_run else ""
    lines += [
        bar,
        f" 협업메일 자동분류 결과{mode}",
        f" 검사 기간: 최근 {report.since_hours:g}시간 | 검사한 스레드: {report.scanned_threads}개",
        bar,
        "[분류별 건수]",
    ]
    for category, count in report.counts().items():
        lines.append(f"  {_pad(category.display, 10)}: {count}건")
    lines.append(
        f"  (대량발송 제외 {len(report.excluded_bulk)}건, "
        f"이미 처리되어 건너뜀 {report.skipped_already_processed}건, 오류 {len(report.errors)}건)"
    )
    verb = "작성 예정" if report.dry_run else "작성 완료"

    if summary_only:
        lines.append(f"  답장 초안 {verb}: {len(report.drafted)}건 / 직접 검토 필요: {len(report.review_needed)}건")
        lines.append(bar)
        return "\n".join(lines)

    lines += ["", f"[답장 초안 {verb}] {len(report.drafted)}건"]
    for r in report.drafted:
        lines.append(f"  - [{r.scenario.display}] [{r.category.display}] {r.sender} | {r.subject}")
        if show_drafts and r.draft_body:
            lines += ["    ┌─ 초안 미리보기", *[f"    │ {ln}" for ln in r.draft_body.splitlines()], "    └─"]

    lines += ["", f"[직접 검토 필요] {len(report.review_needed)}건"]
    for r in report.review_needed:
        lines.append(f"  - [{r.category.display}] {r.sender} | {r.subject}")
        if r.reasons:
            lines.append(f"      사유: {'; '.join(r.reasons)}")

    if report.excluded_bulk:
        lines += ["", f"[대량발송으로 제외] {len(report.excluded_bulk)}건"]
        for sender, subject, reason in report.excluded_bulk:
            lines.append(f"  - {sender} | {subject}  ({reason})")
    if report.errors:
        lines += ["", f"[오류] {len(report.errors)}건"]
        for thread_id, message in report.errors:
            lines.append(f"  - thread {thread_id}: {message}")

    lines += ["", "※ 메일은 발송되지 않았습니다. Gmail 임시보관함에서 초안을 확인 후 직접 보내세요.", bar]
    return "\n".join(lines)
