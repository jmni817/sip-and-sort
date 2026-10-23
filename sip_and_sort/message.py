"""Gmail API 메시지(dict)를 다루기 쉬운 Email 객체로 변환."""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass, field
from email.message import Message
from email.utils import getaddresses, parseaddr
from typing import Any

# 한국 메일에서 흔한 문자셋 이름들. EUC-KR 의 확장판인 CP949 로 읽어야 일부 글자가 깨지지 않는다.
_KOREAN_CHARSETS = {"euc-kr", "euckr", "ks_c_5601-1987", "ks_c_5601", "ksc5601", "x-windows-949", "windows-949", "cp949"}


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


def _part_charset(part: dict[str, Any]) -> str | None:
    """메일 파트의 Content-Type 헤더에 적힌 charset (없으면 None)."""
    for header in part.get("headers") or []:
        if header.get("name", "").lower() == "content-type":
            msg = Message()
            msg["Content-Type"] = header.get("value", "")
            charset = msg.get_content_charset()
            if charset:
                return "cp949" if charset in _KOREAN_CHARSETS else charset
    return None


def decode_body_bytes(raw: bytes, charset: str | None) -> str:
    """메일에 적힌 charset 으로 읽고, 없거나 틀렸으면 UTF-8 → CP949(EUC-KR) 순서로 시도한다.

    Gmail API 는 본문을 원래 인코딩 그대로 돌려주므로, 무조건 UTF-8 로 읽으면
    EUC-KR 한국어 메일이 깨져 키워드를 찾지 못한다.
    """
    for encoding in dict.fromkeys(filter(None, (charset, "utf-8", "cp949"))):
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def _decode_b64(data: str, charset: str | None = None) -> str:
    padded = data + "=" * (-len(data) % 4)
    return decode_body_bytes(base64.urlsafe_b64decode(padded.encode("ascii")), charset)


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
        plain.append(_decode_b64(data, _part_charset(payload)))
    elif data and mime == "text/html":
        rich.append(_decode_b64(data, _part_charset(payload)))
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
