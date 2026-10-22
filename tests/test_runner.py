"""runner.run() 통합 흐름 — GmailClient 를 MagicMock 으로 대체."""

from unittest.mock import MagicMock

import pytest

from sip_and_sort.classifier import Category, Scenario
from sip_and_sort.runner import build_query, format_report, run
from conftest import MY_ADDRESS, gmail_message

FIXTURE_NAMES = [
    "price_inquiry",
    "unpaid_collab",
    "gift_offer",
    "ambiguous",
    "newsletter",
    "non_collab",
]


def make_client(threads: dict[str, list[dict]], existing_labels: dict[str, str] | None = None):
    client = MagicMock()
    client.list_labels.return_value = existing_labels or {}
    client.get_my_addresses.return_value = {MY_ADDRESS}
    client.search_messages.return_value = [
        {"id": msg["id"], "threadId": tid} for tid, msgs in threads.items() for msg in msgs
    ]
    client.get_thread.side_effect = lambda tid: {"id": tid, "messages": threads[tid]}
    client.get_or_create_label.side_effect = lambda name: f"id:{name}"
    return client


@pytest.fixture
def threads():
    return {f"thread-{n}": [gmail_message(n)] for n in FIXTURE_NAMES}


def test_dry_run_classifies_without_any_writes(threads, config):
    client = make_client(threads)
    report = run(client, config, dry_run=True, now=1_800_000_000)

    by_subject = {r.subject: r for r in report.results}
    assert len(report.results) == 4
    assert report.counts() == {Category.BRAND_SPONSORSHIP: 2, Category.PAID_AD: 1, Category.OTHER: 1}
    assert {r.scenario for r in report.drafted} == {Scenario.PRICE_QUOTE, Scenario.DECLINE_UNPAID, Scenario.GIFT_ACCEPT}
    assert [r.subject for r in report.review_needed] == ["브랜드 협업 관련 미팅 요청"]
    assert len(report.excluded_bulk) == 1
    assert "테스트크리에이터" in by_subject["[협업 제안] 신제품 숏폼 광고 진행 문의"].draft_body

    client.get_or_create_label.assert_not_called()
    client.create_reply_draft.assert_not_called()
    client.add_thread_labels.assert_not_called()


def test_real_run_labels_and_creates_drafts_only(threads, config):
    client = make_client(threads)
    report = run(client, config, now=1_800_000_000)

    assert client.create_reply_draft.call_count == 3
    assert not report.errors
    labels_by_thread = {c.args[0]: c.args[1] for c in client.add_thread_labels.call_args_list}
    assert labels_by_thread["thread-price_inquiry"] == ["id:협업제안/유료광고", "id:답장초안완료"]
    assert labels_by_thread["thread-ambiguous"] == ["id:협업제안/기타"]  # 직접 검토: 초안 라벨 없음
    assert "thread-newsletter" not in labels_by_thread

    draft = next(
        c.kwargs for c in client.create_reply_draft.call_args_list if c.kwargs["thread_id"] == "thread-price_inquiry"
    )
    assert draft["subject"] == "Re: [협업 제안] 신제품 숏폼 광고 진행 문의"
    assert draft["in_reply_to"] == "<price-1@brand-example.co.kr>"
    assert "manager@brand-example.co.kr" in draft["to"]
    assert not hasattr(client, "send") or not client.send.called


def test_already_labeled_threads_are_skipped(config):
    labeled = gmail_message("price_inquiry", label_ids=["INBOX", "L_PAID"])
    client = make_client({"thread-price_inquiry": [labeled]}, existing_labels={"협업제안/유료광고": "L_PAID"})
    report = run(client, config, now=1_800_000_000)

    assert report.skipped_already_processed == 1
    assert report.results == []
    client.create_reply_draft.assert_not_called()


def test_my_own_sent_reply_is_not_processed(config):
    mine = gmail_message("price_inquiry", msg_id="mine", label_ids=["SENT"], internal_date=2)
    mine["payload"]["headers"] = [{"name": "From", "value": MY_ADDRESS}, {"name": "Subject", "value": "Re: x"}]
    incoming = gmail_message("price_inquiry", internal_date=1)
    client = make_client({"thread-price_inquiry": [incoming, mine]})
    report = run(client, config, dry_run=True, now=1_800_000_000)
    assert [r.subject for r in report.results] == ["[협업 제안] 신제품 숏폼 광고 진행 문의"]


def test_one_failing_thread_does_not_stop_the_run(threads, config):
    client = make_client(threads)
    original = client.get_thread.side_effect
    client.get_thread.side_effect = lambda tid: (_ for _ in ()).throw(RuntimeError("boom")) if tid == "thread-gift_offer" else original(tid)
    report = run(client, config, dry_run=True, now=1_800_000_000)
    assert report.errors == [("thread-gift_offer", "boom")]
    assert len(report.results) == 3


def test_since_override_changes_query(config):
    client = make_client({})
    run(client, config, since_hours=48, dry_run=True, now=1_800_000_000)
    query = client.search_messages.call_args.args[0]
    assert query.startswith(f"after:{1_800_000_000 - 48 * 3600}")


def test_build_query_appends_extra():
    assert build_query(100, "in:inbox") == "after:100 -in:sent -in:draft -in:chats in:inbox"


def test_format_report_summary_only_hides_senders(threads, config):
    report = run(make_client(threads), config, dry_run=True, now=1_800_000_000)
    full = format_report(report, show_drafts=True)
    short = format_report(report, summary_only=True)
    assert "manager@brand-example.co.kr" in full and "초안 미리보기" in full
    assert "manager@brand-example.co.kr" not in short
    assert "유료광고" in short
