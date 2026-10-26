"""(선택 기능) AI 판단: 규칙으로 판단하지 못한 메일만 LLM 에 묻는다. 실제 API 대신 가짜 응답 사용."""

import io
import json
import urllib.error
from unittest.mock import MagicMock

import pytest

from sip_and_sort.classifier import Category, Scenario, check_candidate, detect_scenario
from sip_and_sort.llm import (
    AIVerdict,
    LLMClassifier,
    LLMError,
    LLMSettings,
    build_messages,
    mask_text,
    parse_verdict,
    validate_base_url,
)
from sip_and_sort.runner import format_report, run
from sip_and_sort.setup_server import SetupState
from conftest import MY_ADDRESS, gmail_message, load_email
from test_runner import make_client


class FakeAI:
    """정해 둔 판단을 돌려주고, 어떤 메일을 물어봤는지 기록한다."""

    min_confidence = 0.7

    def __init__(self, verdicts=None, error=None):
        self.verdicts = verdicts or {}
        self.error = error
        self.asked = []

    def classify(self, email):
        self.asked.append(email.subject)
        if self.error:
            raise self.error
        return self.verdicts.get(email.subject, AIVerdict(False, Category.OTHER, None, 0.9, "협업 아님"))


UNPAID = AIVerdict(True, Category.BRAND_SPONSORSHIP, Scenario.DECLINE_UNPAID, 0.92, "비용 언급 없이 제품 수령 후 릴스 업로드 요구")


# ---------------------------------------------------------------- 문제의 메일: 규칙만으로는 놓친다


def test_rules_alone_miss_implicit_unpaid_offer(config):
    email = load_email("unpaid_implicit")
    assert not check_candidate(email, config, {MY_ADDRESS}).is_candidate
    assert detect_scenario(email).scenario is None


def test_ai_catches_implicit_unpaid_offer_and_drafts_decline(config):
    ai = FakeAI({"신제품 소개드립니다": UNPAID})
    client = make_client({"thread-unpaid_implicit": [gmail_message("unpaid_implicit")]})
    report = run(client, config, now=1_800_000_000, ai=ai)

    assert ai.asked == ["신제품 소개드립니다"]
    [result] = report.results
    assert result.decided_by == "ai"
    assert result.scenario is Scenario.DECLINE_UNPAID and result.category is Category.BRAND_SPONSORSHIP
    assert "테스트크리에이터" in result.draft_body
    client.create_reply_draft.assert_called_once()
    labels = client.add_thread_labels.call_args.args[1]
    assert labels == ["id:협업제안/브랜드협찬", "id:답장초안완료"]
    assert "[AI]" in format_report(report)


def test_without_ai_the_program_behaves_as_before(config):
    client = make_client({"thread-unpaid_implicit": [gmail_message("unpaid_implicit")]})
    report = run(client, config, now=1_800_000_000)
    assert report.results == [] and report.ai_calls == 0


# ---------------------------------------------------------------- 무엇을 AI 에 보내고, 무엇을 안 보내는가


def test_only_rule_unmatched_mails_are_sent_to_ai(config):
    names = ["price_inquiry", "unpaid_collab", "gift_offer", "ambiguous", "newsletter", "non_collab"]
    client = make_client({f"thread-{n}": [gmail_message(n)] for n in names})
    ai = FakeAI()
    run(client, config, dry_run=True, now=1_800_000_000, ai=ai)
    # 규칙이 A/B/C 를 정한 메일, 뉴스레터, 신호 없는 일반 메일은 보내지 않는다
    assert ai.asked == ["브랜드 협업 관련 미팅 요청"]


def test_low_confidence_ai_keeps_manual_review(config):
    ai = FakeAI({"브랜드 협업 관련 미팅 요청": AIVerdict(True, Category.OTHER, Scenario.PRICE_QUOTE, 0.4, "애매함")})
    client = make_client({"thread-ambiguous": [gmail_message("ambiguous")]})
    report = run(client, config, dry_run=True, now=1_800_000_000, ai=ai)
    [result] = report.results
    assert result.scenario is None and result.decided_by == "rule"
    assert any("AI도 확신하지 못함" in r for r in result.reasons)


def test_ai_failure_falls_back_to_rules(config):
    ai = FakeAI(error=LLMError("AI API 오류 (HTTP 500)"))
    names = ["ambiguous", "unpaid_implicit"]
    client = make_client({f"thread-{n}": [gmail_message(n)] for n in names})
    report = run(client, config, dry_run=True, now=1_800_000_000, ai=ai)
    assert not report.errors  # 실행은 멈추지 않는다
    assert len(report.ai_errors) == 2
    assert [r.subject for r in report.results] == ["브랜드 협업 관련 미팅 요청"]  # 규칙 결과는 그대로
    assert "AI 판단 실패" in format_report(report)


# ---------------------------------------------------------------- 전처리 / 응답 해석 / API 호출


def test_mask_text_hides_contacts_but_keeps_dates():
    text = "담당 김민지 010-1234-5678, pr@brand.co.kr, https://brand.co.kr/x 계좌 123-456-789012 마감 2026-10-30"
    masked = mask_text(text, ("김민지",))
    for secret in ("010-1234-5678", "pr@brand.co.kr", "brand.co.kr/x", "123-456-789012", "김민지"):
        assert secret not in masked
    assert "2026-10-30" in masked


def test_prompt_contains_masked_body_only():
    email = load_email("price_inquiry")
    email.body += "\n연락처 010-9999-8888"
    content = build_messages(email)[1]["content"]
    assert "010-9999-8888" not in content and "[전화번호]" in content
    assert "김담당" not in content  # 보낸 사람 이름도 가림


def test_parse_verdict_handles_code_fences_and_bad_values():
    v = parse_verdict('```json\n{"is_collab": true, "category": "paid_ad", "scenario": "a", "confidence": 1.7, "reason": "단가 문의"}\n```')
    assert v.is_collab and v.category is Category.PAID_AD and v.scenario is Scenario.PRICE_QUOTE and v.confidence == 1.0
    v = parse_verdict('{"is_collab": true, "category": "weird", "scenario": "Z", "confidence": "x"}')
    assert v.category is Category.OTHER and v.scenario is None and v.confidence == 0.0
    with pytest.raises(LLMError):
        parse_verdict("죄송합니다, 판단할 수 없습니다.")


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://api.example.com/v1/", "https://api.example.com/v1"),
        ("https://api.example.com/v1/chat/completions", "https://api.example.com/v1"),
        ("http://localhost:11434/v1", "http://localhost:11434/v1"),
    ],
)
def test_validate_base_url_accepts(url, expected):
    assert validate_base_url(url) == expected


def test_validate_base_url_rejects_plain_http_to_remote():
    with pytest.raises(ValueError):
        validate_base_url("http://api.example.com/v1")


def _response(payload):
    resp = MagicMock()
    resp.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return resp


def test_classifier_calls_openai_compatible_endpoint():
    opener = MagicMock(return_value=_response({"choices": [{"message": {"content": json.dumps(
        {"is_collab": True, "category": "brand_sponsorship", "scenario": "B", "confidence": 0.9, "reason": "무가"})}}]}))
    ai = LLMClassifier(LLMSettings("https://gw.example.com/v1", "some-model", "sk-test"), opener=opener)
    verdict = ai.classify(load_email("unpaid_implicit"))
    assert verdict.scenario is Scenario.DECLINE_UNPAID

    request = opener.call_args.args[0]
    assert request.full_url == "https://gw.example.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer sk-test"
    body = json.loads(request.data)
    assert body["model"] == "some-model" and body["temperature"] == 0
    assert "sk-test" not in request.data.decode("utf-8")


def test_classifier_reports_bad_key_without_retrying():
    err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b""))
    opener = MagicMock(side_effect=err)
    ai = LLMClassifier(LLMSettings("https://gw.example.com/v1", "m", "bad"), opener=opener, sleep=lambda _: None)
    with pytest.raises(LLMError, match="API 키"):
        ai.classify(load_email("ambiguous"))
    assert opener.call_count == 1


def test_classifier_retries_rate_limit():
    err = urllib.error.HTTPError("u", 429, "Too Many", {}, io.BytesIO(b""))
    ok = _response({"choices": [{"message": {"content": '{"is_collab": false, "confidence": 0.9}'}}]})
    opener = MagicMock(side_effect=[err, ok])
    ai = LLMClassifier(LLMSettings("https://gw.example.com/v1", "m", "k"), opener=opener, sleep=lambda _: None)
    assert ai.classify(load_email("ambiguous")).is_collab is False


# ---------------------------------------------------------------- 설정 페이지


def test_setup_saves_llm_settings_and_keeps_key_out_of_config(tmp_path):
    state = SetupState(tmp_path / "config.yaml")
    state.save_profile({"activity_name": "테스트"})
    with pytest.raises(ValueError):  # 켜려면 주소·모델·키가 모두 필요
        state.save_llm({"enabled": True, "base_url": "https://gw.example.com/v1", "model": "m"})
    state.save_llm({"enabled": True, "base_url": "https://gw.example.com/v1/chat/completions", "model": "m", "api_key": "sk-secret"})

    config_text = (tmp_path / "config.yaml").read_text(encoding="utf-8")
    assert "sk-secret" not in config_text
    assert (tmp_path / "llm_api_key.txt").read_text(encoding="utf-8") == "sk-secret"
    status = state.status()["llm"]
    assert status == {"enabled": True, "base_url": "https://gw.example.com/v1", "model": "m", "has_key": True}
    assert "sk-secret" not in json.dumps(state.status())

    # 키 칸을 비워 두고 저장하면 기존 키 유지
    state.save_llm({"enabled": False, "base_url": "https://gw.example.com/v1", "model": "m2"})
    assert (tmp_path / "llm_api_key.txt").read_text(encoding="utf-8") == "sk-secret"
    with pytest.raises(ValueError):
        state.save_llm({"enabled": True, "base_url": "http://remote.example.com/v1", "model": "m", "api_key": "k"})


def test_setup_llm_connection_test_uses_example_mail(tmp_path, monkeypatch):
    state = SetupState(tmp_path / "config.yaml")
    state.save_llm({"enabled": True, "base_url": "https://gw.example.com/v1", "model": "m", "api_key": "k"})
    seen = []

    def fake_chat(self, messages):
        seen.append(messages[1]["content"])
        return json.dumps({"is_collab": True, "category": "brand_sponsorship", "scenario": "B", "confidence": 0.9, "reason": "무가"})

    monkeypatch.setattr(LLMClassifier, "_chat", fake_chat)
    output = state.test_llm()
    assert "연결 성공" in output and "B 무가협업 거절" in output
    assert "릴스" in seen[0]
