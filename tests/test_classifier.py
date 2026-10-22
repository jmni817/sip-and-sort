import pytest

from sip_and_sort.classifier import (
    Category,
    Scenario,
    categorize,
    check_candidate,
    detect_bulk_mail,
    detect_scenario,
    find_keywords,
    strip_quoted,
)
from conftest import load_email


# ---------------------------------------------------------------- 키워드 매칭


def test_korean_keyword_ignores_spacing():
    assert find_keywords("유료광고 문의드립니다", ["유료 광고"]) == ["유료 광고"]


def test_short_uppercase_english_keyword_is_case_sensitive():
    assert find_keywords("PR 패키지를 보내드려요", ["PR"]) == ["PR"]
    assert find_keywords("we will improve the product", ["PR"]) == []


def test_english_keyword_uses_word_boundary():
    assert find_keywords("Thanks for the campaign!", ["campaign"]) == ["campaign"]
    assert find_keywords("campaigner newsletter", ["campaign"]) == []
    assert find_keywords("Let's talk about a Brand  Deal", ["brand deal"]) == ["brand deal"]


def test_ppl_matches_next_to_korean():
    assert find_keywords("PPL문의", ["PPL"]) == ["PPL"]


def test_strip_quoted_removes_previous_conversation():
    text = "새 내용\n\n2026년 10월 1일 (목) 오전 10:00, 누군가님이 작성:\n> 단가 안내"
    assert "단가" not in strip_quoted(text)


# ---------------------------------------------------------------- 후보 판별 / 대량메일


@pytest.mark.parametrize(
    "name", ["price_inquiry", "unpaid_collab", "gift_offer", "ambiguous", "english_price"]
)
def test_collab_mails_are_candidates(name, config, my_addresses):
    result = check_candidate(load_email(name), config, my_addresses)
    assert result.is_candidate, result
    assert result.matched_keywords


def test_non_collab_mail_is_not_candidate(config, my_addresses):
    # "피드백" 같은 일상 단어는 협업 키워드로 오인하지 않는다
    result = check_candidate(load_email("non_collab"), config, my_addresses)
    assert not result.is_candidate
    assert result.excluded_reason is None


@pytest.mark.parametrize(
    "name, reason_part",
    [
        ("newsletter", "List-Unsubscribe"),
        ("ad_subject", "(광고)"),
        ("bcc_bulk", "발신자=수신자"),
    ],
)
def test_bulk_mails_are_excluded(name, reason_part, config, my_addresses):
    result = check_candidate(load_email(name), config, my_addresses)
    assert not result.is_candidate
    assert reason_part in result.excluded_reason


def test_bcc_only_mail_is_excluded_when_my_address_missing():
    email = load_email("price_inquiry")
    email.to = ["someone-else@example.net"]
    assert "BCC" in detect_bulk_mail(email, {"creator@example.com"})


def test_alias_address_is_treated_as_mine():
    email = load_email("price_inquiry")
    email.to = ["business@my-domain.example"]
    assert detect_bulk_mail(email, {"creator@example.com", "business@my-domain.example"}) is None


def test_noreply_sender_is_bulk():
    email = load_email("price_inquiry")
    email.sender_email = "no-reply@brand-example.co.kr"
    assert "자동발송" in detect_bulk_mail(email)


def test_bulk_heuristics_can_be_disabled(config, my_addresses):
    config["keywords"]["exclude_bulk_mail_heuristics"] = False
    assert check_candidate(load_email("newsletter"), config, my_addresses).is_candidate


# ---------------------------------------------------------------- 분류


@pytest.mark.parametrize(
    "name, expected",
    [
        ("price_inquiry", Category.PAID_AD),
        ("english_price", Category.PAID_AD),
        ("unpaid_collab", Category.BRAND_SPONSORSHIP),  # "원고료" 가 있어도 무가 신호가 우선
        ("gift_offer", Category.BRAND_SPONSORSHIP),
        ("ambiguous", Category.OTHER),
    ],
)
def test_categorize(name, expected):
    assert categorize(load_email(name)) is expected


# ---------------------------------------------------------------- A/B/C 판별


@pytest.mark.parametrize(
    "name, expected",
    [
        ("price_inquiry", Scenario.PRICE_QUOTE),
        ("english_price", Scenario.PRICE_QUOTE),
        ("unpaid_collab", Scenario.DECLINE_UNPAID),
        ("gift_offer", Scenario.GIFT_ACCEPT),
    ],
)
def test_detect_scenario(name, expected):
    result = detect_scenario(load_email(name))
    assert result.scenario is expected, result.reasons
    assert result.reasons


@pytest.mark.parametrize("name", ["ambiguous", "mixed_ab", "reply_with_quote"])
def test_ambiguous_mails_need_manual_review(name):
    assert detect_scenario(load_email(name)).scenario is None


def test_gift_without_explicit_no_obligation_is_not_c():
    email = load_email("gift_offer")
    email.body = "저희 신제품을 선물로 보내드리고 싶습니다."
    assert detect_scenario(email).scenario is None


def test_no_obligation_cancels_unpaid_decline():
    email = load_email("unpaid_collab")
    email.body = "무상으로 제품을 보내드리고 싶어요. 업로드 의무 없습니다."
    assert detect_scenario(email).scenario is Scenario.GIFT_ACCEPT


def test_rules_can_be_overridden(config):
    from sip_and_sort.classifier import get_rules

    config["rules"] = {"price_inquiry": ["얼마"]}
    rules = get_rules(config)
    assert rules["price_inquiry"] == ["얼마"]
    assert detect_scenario(load_email("price_inquiry"), rules).scenario is None
