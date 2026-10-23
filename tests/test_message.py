"""메일 본문 문자 인코딩 처리 (EUC-KR 등 한국어 메일)."""

import base64

import pytest

from sip_and_sort.classifier import check_candidate, detect_scenario, Scenario
from sip_and_sort.message import decode_body_bytes, parse_message
from conftest import MY_ADDRESS

BODY = "안녕하세요. 저희 브랜드 신제품 협찬을 제안드립니다. 릴스 1건 단가 알려주세요."


def gmail_message(raw: bytes, content_type: str | None, mime: str = "text/plain") -> dict:
    """제목에는 협업 키워드가 없고 본문에만 있는 메일."""
    headers = [
        {"name": "From", "value": "담당자 <pr@brand.example>"},
        {"name": "To", "value": MY_ADDRESS},
        {"name": "Subject", "value": "안녕하세요"},
    ]
    part_headers = [{"name": "Content-Type", "value": content_type}] if content_type else []
    return {
        "id": "m1",
        "threadId": "t1",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": headers,
            "parts": [
                {
                    "mimeType": mime,
                    "headers": part_headers,
                    "body": {"data": base64.urlsafe_b64encode(raw).decode("ascii")},
                }
            ],
        },
    }


@pytest.mark.parametrize(
    "encoding, content_type",
    [
        ("euc-kr", 'text/plain; charset="euc-kr"'),
        ("euc-kr", "text/plain; charset=EUC-KR"),
        ("cp949", 'text/plain; charset="ks_c_5601-1987"'),  # Outlook 등에서 흔한 표기
        ("cp949", None),  # charset 표기가 없어도 CP949 로 다시 시도
        ("utf-8", "text/plain; charset=utf-8"),
    ],
)
def test_korean_body_is_decoded_and_classified(encoding, content_type, config):
    email = parse_message(gmail_message(BODY.encode(encoding), content_type))
    assert email.body == BODY
    assert check_candidate(email, config, {MY_ADDRESS}).is_candidate
    assert detect_scenario(email).scenario is Scenario.PRICE_QUOTE


def test_euc_kr_html_body_is_decoded(config):
    html = f"<html><body><p>{BODY}</p></body></html>".encode("euc-kr")
    email = parse_message(gmail_message(html, 'text/html; charset="euc-kr"', mime="text/html"))
    assert "협찬" in email.body and "단가" in email.body
    assert check_candidate(email, config, {MY_ADDRESS}).is_candidate


def test_wrong_charset_label_falls_back():
    # utf-8 이라고 적혀 있지만 실제로는 CP949 인 메일
    assert decode_body_bytes(BODY.encode("cp949"), "utf-8") == BODY
    # 알 수 없는 charset 이름
    assert decode_body_bytes(BODY.encode("utf-8"), "x-unknown-charset") == BODY


def test_undecodable_bytes_do_not_crash():
    assert isinstance(decode_body_bytes(b"\xff\xfe\xfa invalid", None), str)
