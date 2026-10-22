"""테스트 공용 fixture: 샘플 .eml 파일을 Gmail API 메시지 dict / Email 객체로 변환."""

from __future__ import annotations

import base64
from email import message_from_string
from pathlib import Path

import pytest

from sip_and_sort.config import default_config
from sip_and_sort.message import Email, parse_message

FIXTURES = Path(__file__).parent / "fixtures" / "emails"
MY_ADDRESS = "creator@example.com"


def gmail_message(
    name: str,
    *,
    msg_id: str | None = None,
    thread_id: str | None = None,
    label_ids: list[str] | None = None,
    internal_date: int = 1_700_000_000_000,
) -> dict:
    """fixtures/emails/<name>.eml → users.messages.get(format=full) 형태의 dict."""
    parsed = message_from_string((FIXTURES / f"{name}.eml").read_text(encoding="utf-8"))
    body = parsed.get_payload()
    return {
        "id": msg_id or f"msg-{name}",
        "threadId": thread_id or f"thread-{name}",
        "labelIds": label_ids if label_ids is not None else ["INBOX", "UNREAD"],
        "internalDate": str(internal_date),
        "snippet": body[:50],
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": k, "value": v} for k, v in parsed.items()],
            "body": {"data": base64.urlsafe_b64encode(body.encode("utf-8")).decode("ascii")},
        },
    }


def load_email(name: str) -> Email:
    return parse_message(gmail_message(name))


@pytest.fixture
def config() -> dict:
    cfg = default_config()
    cfg["activity_name"] = "테스트크리에이터"
    return cfg


@pytest.fixture
def my_addresses() -> set[str]:
    return {MY_ADDRESS}
