from sip_and_sort.classifier import Scenario
from sip_and_sort.templates import (
    DEFAULT_TEMPLATES,
    UNKNOWN,
    render_reply,
    render_template,
    reply_subject,
)
from conftest import load_email


def test_unknown_placeholder_becomes_brackets():
    assert render_template("안녕 {who}, {activity_name}", {"activity_name": "나"}) == f"안녕 {UNKNOWN}, 나\n"


def test_empty_or_none_value_becomes_brackets():
    out = render_template("{a}/{b}", {"a": "", "b": None})
    assert out == f"{UNKNOWN}/{UNKNOWN}\n"


def test_stray_braces_do_not_break_rendering():
    assert render_template("JSON 예시 {\"k\": 1} {activity_name}", {"activity_name": "나"}).startswith(
        'JSON 예시 {"k": 1} 나'
    )


def test_activity_name_from_landing_page_is_used_in_draft(config):
    body = render_reply(config, Scenario.PRICE_QUOTE, load_email("price_inquiry"))
    assert "테스트크리에이터입니다" in body
    assert body.rstrip().endswith("테스트크리에이터 드림")
    assert "김담당님" in body  # From 표시 이름


def test_missing_activity_name_and_contact_left_blank(config):
    config["activity_name"] = ""
    email = load_email("price_inquiry")
    email.sender_name = ""
    body = render_reply(config, Scenario.DECLINE_UNPAID, email)
    assert f"안녕하세요, {UNKNOWN}님." in body
    assert f"{UNKNOWN}입니다" in body


def test_custom_template_from_config_overrides_default(config):
    config["templates"] = {"gift_accept": "감사합니다 - {activity_name}"}
    body = render_reply(config, Scenario.GIFT_ACCEPT, load_email("gift_offer"))
    assert body == "감사합니다 - 테스트크리에이터\n"


def test_default_templates_only_use_supported_placeholders():
    import re

    allowed = {"activity_name", "contact_name", "original_subject"}
    for text in DEFAULT_TEMPLATES.values():
        assert set(re.findall(r"\{(\w+)\}", text)) <= allowed


def test_reply_subject():
    assert reply_subject("협업 제안") == "Re: 협업 제안"
    assert reply_subject("RE: 협업 제안") == "RE: 협업 제안"
