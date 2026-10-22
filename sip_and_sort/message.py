"""Gmail API 메시지(dict)를 다루기 쉬운 Email 객체로 변환."""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass, field
from email.utils import getaddresses, parseaddr
from typing import Any


@dataclass
class Email:
    id: str
    thread_id: str
    subject: str
    sender: str  # "이름 <주소>" 원문
    sender_name: str
    sender_email: str
    to: list[str] = field(default_factory=list)  # 주소만 (소문자)
    cc: list[str] = field(default_factory=list)
    raw_to: str = ""
    headers: dict[str, str] = field(default_factory=dict)  # 헤더 이름은 소문자
    body: str = ""
    label_ids: list[str] = field(default_factory=list)
    internal_date_ms: int = 0
    snippet: str = ""

    @property
    def message_id_header(self) -> str:
        return self.headers.get("message-id", "")

    @property
    def reply_to_address(self) -> str:
        reply_to = self.headers.get("reply-to", "").strip()
        return reply_to or self.sender


def _decode_b64(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")


def html_to_text(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", markup)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _collect_parts(payload: dict[str, Any], plain: list[str], rich: list[str]) -> None:
    mime = payload.get("mimeType", "")
    data = (payload.get("body") or {}).get("data")
    if payload.get("filename"):
        return  # 첨부파일은 무시
    if data and mime == "text/plain":
        plain.append(_decode_b64(data))
    elif data and mime == "text/html":
        rich.append(_decode_b64(data))
    for part in payload.get("parts") or []:
        _collect_parts(part, plain, rich)


def extract_body(payload: dict[str, Any]) -> str:
    """text/plain 우선, 없으면 text/html을 텍스트로 변환."""
    plain: list[str] = []
    rich: list[str] = []
    _collect_parts(payload, plain, rich)
    if plain:
        return "\n".join(plain).strip()
    if rich:
        return html_to_text("\n".join(rich))
    return ""


def _addresses(value: str) -> list[str]:
    return [addr.lower() for _, addr in getaddresses([value]) if addr]


def parse_message(message: dict[str, Any]) -> Email:
    payload = message.get("payload") or {}
    headers = {h["name"].lower(): h.get("value", "") for h in payload.get("headers") or []}
    sender = headers.get("from", "")
    sender_name, sender_email = parseaddr(sender)
    return Email(
        id=message.get("id", ""),
        thread_id=message.get("threadId", ""),
        subject=headers.get("subject", ""),
        sender=sender,
        sender_name=sender_name.strip().strip('"'),
        sender_email=sender_email.lower(),
        to=_addresses(headers.get("to", "")),
        cc=_addresses(headers.get("cc", "")),
        raw_to=headers.get("to", ""),
        headers=headers,
        body=extract_body(payload),
        label_ids=list(message.get("labelIds") or []),
        internal_date_ms=int(message.get("internalDate") or 0),
        snippet=message.get("snippet", ""),
    )
