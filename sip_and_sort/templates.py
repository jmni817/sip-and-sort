"""답장 초안 템플릿과 렌더링.

사용 가능한 placeholder:
    {activity_name}     랜딩 페이지에서 입력한 이용자 이름(활동명)
    {contact_name}      상대 담당자 이름 (From 헤더의 표시 이름)
    {original_subject}  받은 메일 제목
값을 알 수 없는 placeholder 는 "[ ]" 로 남겨, 사용자가 초안에서 직접 채우도록 한다.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .classifier import Scenario
from .message import Email

UNKNOWN = "[ ]"

DEFAULT_TEMPLATES: dict[str, str] = {
    "price_quote": """안녕하세요, {contact_name}님.
{activity_name}입니다. 협업 제안 주셔서 감사합니다.

문의 주신 단가는 콘텐츠 형식과 진행 범위에 따라 달라집니다.
아래 내용을 알려주시면 확인 후 정확한 견적을 안내드리겠습니다.

- 희망 콘텐츠 형식 및 수량:
- 업로드 희망 일정:
- 콘텐츠 2차 활용 / 광고 집행 여부 및 기간:

감사합니다.
{activity_name} 드림
""",
    "decline_unpaid": """안녕하세요, {contact_name}님.
{activity_name}입니다. 좋은 제안 주셔서 감사합니다.

다만 콘텐츠 제작이 필요한 협업은 현재 제품 제공만으로는 진행하지 않고 있습니다.
유료 협업으로 검토가 가능하시다면 다시 연락 주시면 감사하겠습니다.

다음에 좋은 기회로 함께할 수 있기를 바랍니다.
{activity_name} 드림
""",
    "gift_accept": """안녕하세요, {contact_name}님.
{activity_name}입니다. 따뜻한 제안 주셔서 감사합니다.

콘텐츠 제작 의무가 없는 선물로 이해하고 감사히 받겠습니다.
배송받을 정보는 확인 후 별도로 회신드리겠습니다.

감사합니다.
{activity_name} 드림
""",
}

TEMPLATE_LABELS = {
    "price_quote": "A. 단가/비용 문의 → 단가 안내",
    "decline_unpaid": "B. 무가 협업(제품만 제공 + 콘텐츠 의무) → 거절",
    "gift_accept": "C. 의무 없는 선물 제안 → 수락",
}

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render_template(template: str, values: Mapping[str, Any]) -> str:
    """{name} 을 값으로 치환. 값이 없거나(None/빈 문자열) 모르는 키면 "[ ]"."""

    def substitute(match: re.Match[str]) -> str:
        value = values.get(match.group(1))
        if value is None or (isinstance(value, str) and not value.strip()):
            return UNKNOWN
        return str(value)

    rendered = _PLACEHOLDER.sub(substitute, template)
    return re.sub(r"\n{3,}", "\n\n", rendered).strip() + "\n"


def get_template(config: Mapping[str, Any], scenario: Scenario) -> str:
    custom = (config.get("templates") or {}).get(scenario.template_key)
    if isinstance(custom, str) and custom.strip():
        return custom
    return DEFAULT_TEMPLATES[scenario.template_key]


def build_values(config: Mapping[str, Any], email: Email) -> dict[str, Any]:
    return {
        "activity_name": config.get("activity_name"),
        "contact_name": email.sender_name or None,
        "original_subject": email.subject or None,
    }


def render_reply(config: Mapping[str, Any], scenario: Scenario, email: Email) -> str:
    return render_template(get_template(config, scenario), build_values(config, email))


def reply_subject(subject: str) -> str:
    return subject if re.match(r"(?i)^\s*re\s*:", subject) else f"Re: {subject}".rstrip()
