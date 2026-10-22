"""규칙(키워드) 기반 협업 메일 판별 / 분류 / 답장 상황(A·B·C) 판별.

LLM이나 외부 서비스를 쓰지 않는다. 모든 판단은 이 파일의 키워드 규칙과
config.yaml 의 `keywords`, `rules` 값으로만 이뤄진다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Iterable

from .message import Email


class Category(str, Enum):
    BRAND_SPONSORSHIP = "brand_sponsorship"
    PAID_AD = "paid_ad"
    OTHER = "other"

    @property
    def display(self) -> str:
        return {"brand_sponsorship": "브랜드협찬", "paid_ad": "유료광고", "other": "기타"}[self.value]


class Scenario(str, Enum):
    PRICE_QUOTE = "A"  # 단가/비용 문의 → 단가 안내
    DECLINE_UNPAID = "B"  # 무가 협업(제품만 제공 + 콘텐츠 의무) → 거절
    GIFT_ACCEPT = "C"  # 의무 없는 순수 선물 → 수락

    @property
    def display(self) -> str:
        return {"A": "A 단가안내", "B": "B 무가협업 거절", "C": "C 선물 수락"}[self.value]

    @property
    def template_key(self) -> str:
        return {"A": "price_quote", "B": "decline_unpaid", "C": "gift_accept"}[self.value]


# 공백이 들어간 한국어 키워드는 띄어쓰기 유무와 상관없이 매칭된다 ("유료 광고" == "유료광고").
DEFAULT_RULES: dict[str, list[str]] = {
    # 분류: 유료광고 신호
    "paid_ad": [
        "유료 광고", "광고비", "광고 비용", "원고료", "제작비", "출연료", "단가", "견적",
        "비용 지급", "페이 지급", "paid", "fee", "budget", "rate card", "compensation",
        "paid partnership",
    ],
    # 분류: 브랜드협찬 신호
    "brand_sponsorship": [
        "협찬", "제품 제공", "제품을 제공", "체험단", "시딩", "선물", "기프팅", "무가", "무상",
        "앰버서더", "서포터즈", "seeding", "gifting", "gift", "free product", "ambassador",
    ],
    # 상황 B: 비용 없이 제품만 제공
    "unpaid": [
        "무가", "무상", "비용 없이", "비용은 없", "원고료 없이", "원고료는 없", "제품만 제공",
        "제품 제공만", "별도 비용 없", "별도의 비용 없", "별도 원고료 없", "unpaid", "no fee",
        "without payment", "no budget", "in exchange for",
    ],
    # 상황 B: 콘텐츠 제작/업로드 의무
    "content_obligation": [
        "업로드", "포스팅", "게시", "리뷰 작성", "후기 작성", "콘텐츠 제작", "컨텐츠 제작",
        "영상 제작", "릴스", "쇼츠", "해시태그", "가이드라인", "필수", "post", "posting",
        "upload", "review", "reel", "reels", "content creation", "create content", "tag us",
        "deliverable", "deliverables",
    ],
    # 상황 C: 의무 없음 명시 (B의 콘텐츠 의무를 무효화)
    "no_obligation": [
        "의무 없", "의무는 없", "의무가 없", "의무는 전혀 없", "의무가 전혀 없", "의무 사항 없", "업로드 부담 없", "포스팅 부담 없",
        "게시 부담 없", "리뷰 부담 없", "강요하지", "강제하지", "업로드하지 않으셔도",
        "올리지 않으셔도", "안 올리셔도", "필수가 아닙", "필수 아님", "no obligation",
        "no strings attached", "not required", "not obligated", "no posting required",
        "no need to post",
    ],
    # 상황 C: 선물/제품 발송 제안
    "gift": [
        "선물", "기프트", "기프팅", "제품을 보내", "제품 보내", "보내드리고", "보내 드리고",
        "보내드려도", "발송해 드리", "gift", "gifting", "send you", "sending you", "PR package",
    ],
    # 상황 A: 단가/비용 문의
    "price_inquiry": [
        "단가", "견적", "광고비", "광고 비용", "비용 문의", "비용이 어떻게", "금액 문의",
        "제안 금액", "rate card", "your rate", "your rates", "pricing", "price", "how much",
    ],
}

BULK_SENDER_LOCALPART = re.compile(
    r"^(no-?reply|do-?not-?reply|newsletter|news|mailer-daemon|notifications?|bounce)[\w.+-]*$",
    re.IGNORECASE,
)
# 정보통신망법상 광고성 메일은 제목에 (광고) 표기 의무가 있다 → 대량 마케팅 메일 신호
AD_SUBJECT_PREFIX = re.compile(r"^\s*[\(\[]\s*(광고|AD)\s*[\)\]]", re.IGNORECASE)

QUOTE_SEPARATORS = re.compile(
    r"^(-{2,}\s*original message\s*-{2,}|-{2,}\s*원본 메시지\s*-{2,}|"
    r"on .{0,200} wrote:|20\d\d[./년 -].{0,80}(작성|wrote).{0,10}:)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@lru_cache(maxsize=2048)
def _compile(keyword: str) -> re.Pattern[str]:
    words = keyword.strip().split()
    if keyword.isascii() and re.search(r"[A-Za-z]", keyword):
        # 영어: 단어 경계 기준. "PR"/"PPL" 처럼 짧은 대문자 약어는 대소문자 구분.
        flags = 0 if (keyword.strip().isupper() and len(keyword.strip()) <= 4) else re.IGNORECASE
        body = r"\s+".join(map(re.escape, words))
        return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", flags)
    return re.compile(r"\s*".join(map(re.escape, words)), re.IGNORECASE)


def find_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    """text 안에서 발견된 키워드 목록(입력 순서 유지, 중복 제거)."""
    found: list[str] = []
    for kw in keywords:
        if kw and str(kw).strip() and kw not in found and _compile(str(kw)).search(text):
            found.append(kw)
    return found


def strip_quoted(text: str) -> str:
    """답장 메일 속 인용된 이전 대화를 제거 (오탐 방지)."""
    match = QUOTE_SEPARATORS.search(text)
    if match:
        text = text[: match.start()]
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))


def analysis_text(email: Email) -> str:
    return f"{email.subject}\n{strip_quoted(email.body)}"


def get_rules(config: dict[str, Any] | None = None) -> dict[str, list[str]]:
    rules = {k: list(v) for k, v in DEFAULT_RULES.items()}
    for key, value in ((config or {}).get("rules") or {}).items():
        if key in rules and isinstance(value, list):
            rules[key] = [str(v) for v in value]
    return rules


# --------------------------------------------------------------------------- 1) 후보 판별


def detect_bulk_mail(email: Email, my_addresses: Iterable[str] = ()) -> str | None:
    """대량발송/뉴스레터로 보이면 사유 문자열, 아니면 None."""
    headers = email.headers
    if "list-unsubscribe" in headers:
        return "List-Unsubscribe 헤더 (뉴스레터/대량발송)"
    if "list-id" in headers:
        return "메일링 리스트 (List-Id 헤더)"
    if headers.get("precedence", "").strip().lower() in {"bulk", "list", "junk"}:
        return f"Precedence: {headers['precedence'].strip()}"
    if AD_SUBJECT_PREFIX.search(email.subject):
        return "제목에 (광고) 표기 (광고성 대량메일)"
    local_part = email.sender_email.split("@", 1)[0]
    if local_part and BULK_SENDER_LOCALPART.match(local_part):
        return f"자동발송 주소 ({email.sender_email})"
    if email.sender_email and email.to and set(email.to) == {email.sender_email}:
        return "발신자=수신자 (BCC 대량발송)"
    if "undisclosed-recipients" in email.raw_to.lower():
        return "수신자 비공개 (BCC 대량발송)"
    mine = {a.lower() for a in my_addresses if a}
    recipients = set(email.to) | set(email.cc)
    if mine and recipients and not (recipients & mine):
        return "BCC로만 수신 (수신자 목록에 본인 주소 없음)"
    return None


@dataclass
class CandidateResult:
    is_candidate: bool
    matched_keywords: list[str] = field(default_factory=list)
    excluded_reason: str | None = None


def check_candidate(
    email: Email, config: dict[str, Any], my_addresses: Iterable[str] = ()
) -> CandidateResult:
    keywords_cfg = config.get("keywords") or {}
    keywords = list(keywords_cfg.get("korean") or []) + list(keywords_cfg.get("english") or [])
    matched = find_keywords(analysis_text(email), keywords)
    if not matched:
        return CandidateResult(False)
    if keywords_cfg.get("exclude_bulk_mail_heuristics", True):
        reason = detect_bulk_mail(email, my_addresses)
        if reason:
            return CandidateResult(False, matched, reason)
    return CandidateResult(True, matched)


# --------------------------------------------------------------------------- 2) 분류


def categorize(email: Email, rules: dict[str, list[str]] | None = None) -> Category:
    rules = rules or get_rules()
    text = analysis_text(email)
    # "원고료 없이" 같은 무가 표현에도 유료 키워드가 섞이므로 무가/선물 신호를 먼저 본다.
    if find_keywords(text, rules["unpaid"]) or find_keywords(text, rules["gift"]):
        return Category.BRAND_SPONSORSHIP
    if find_keywords(text, rules["paid_ad"]):
        return Category.PAID_AD
    if find_keywords(text, rules["brand_sponsorship"]):
        return Category.BRAND_SPONSORSHIP
    return Category.OTHER


# --------------------------------------------------------------------------- 3) A/B/C 판별


@dataclass
class ScenarioResult:
    scenario: Scenario | None
    reasons: list[str] = field(default_factory=list)


def detect_scenario(email: Email, rules: dict[str, list[str]] | None = None) -> ScenarioResult:
    """A/B/C 중 '정확히 하나'에만 해당할 때만 그 상황을 반환. 모호하면 None(직접 검토)."""
    rules = rules or get_rules()
    text = analysis_text(email)
    price = find_keywords(text, rules["price_inquiry"])
    unpaid = find_keywords(text, rules["unpaid"])
    obligation = find_keywords(text, rules["content_obligation"])
    no_obligation = find_keywords(text, rules["no_obligation"])
    gift = find_keywords(text, rules["gift"])

    hits: dict[Scenario, list[str]] = {}
    if price:
        hits[Scenario.PRICE_QUOTE] = [f"단가/비용 문의: {', '.join(price)}"]
    if unpaid and obligation and not no_obligation:
        hits[Scenario.DECLINE_UNPAID] = [
            f"무가 표현: {', '.join(unpaid)}",
            f"콘텐츠 의무: {', '.join(obligation)}",
        ]
    if gift and no_obligation and not price:
        hits[Scenario.GIFT_ACCEPT] = [
            f"선물/제품 제공: {', '.join(gift)}",
            f"의무 없음: {', '.join(no_obligation)}",
        ]

    if len(hits) == 1:
        scenario, reasons = next(iter(hits.items()))
        return ScenarioResult(scenario, reasons)
    if len(hits) > 1:
        names = "/".join(s.value for s in hits)
        return ScenarioResult(None, [f"여러 상황({names})에 동시에 해당 → 모호"])
    return ScenarioResult(None, ["A/B/C 어느 상황에도 명확히 해당하지 않음"])
