"""config.yaml 로딩, 기본값 병합, 검증."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """설정 파일이 없거나 형식이 잘못된 경우."""


DEFAULT_CONFIG: dict[str, Any] = {
    # 답장 초안 서명에 쓰이는 이름(활동명). `sip-and-sort setup` 랜딩 페이지에서 입력.
    "activity_name": "",
    "lookback_hours": 24,
    # 한 번 실행에서 검사할 최대 메일 수 (안전장치)
    "max_messages": 200,
    # Gmail 검색어에 덧붙일 추가 조건 (예: "in:inbox")
    "extra_query": "",
    # 본인 주소 외에 포워딩/별칭으로 받는 주소 (BCC 판별용)
    "my_addresses": [],
    "credentials_path": "credentials.json",
    "token_path": "token.json",
    "gmail_labels": {
        "brand_sponsorship": "협업제안/브랜드협찬",
        "paid_ad": "협업제안/유료광고",
        "other": "협업제안/기타",
        "draft_done": "답장초안완료",
    },
    "keywords": {
        "korean": ["협업", "제휴", "협찬", "광고", "PPL", "브랜드", "캠페인", "서포터즈", "앰버서더"],
        "english": [
            "collaboration",
            "collab",
            "sponsorship",
            "sponsor",
            "partnership",
            "campaign",
            "advertise",
            "advertising",
            "PR",
            "brand deal",
            "ambassador",
        ],
        "exclude_bulk_mail_heuristics": True,
    },
    # 설정 페이지(exe)를 켜 둔 동안 일정 간격으로 자동 정리
    "auto_run": {"enabled": False, "interval_minutes": 60},
    # 비어 있으면 templates.DEFAULT_TEMPLATES 사용
    "templates": {},
    # 분류 규칙 키워드 오버라이드 (비어 있으면 classifier.DEFAULT_RULES 사용)
    "rules": {},
}

REQUIRED_LABEL_KEYS = ("brand_sponsorship", "paid_ad", "other", "draft_done")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def parse_duration(value: str | int | float) -> float:
    """'48h', '2d', '90m', '1w', '24' 같은 값을 시간(hours) 단위 float로 변환."""
    if isinstance(value, (int, float)):
        hours = float(value)
    else:
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([mhdw]?)\s*", str(value).lower())
        if not match:
            raise ValueError(f"기간 형식을 이해할 수 없습니다: {value!r} (예: 24h, 2d, 90m)")
        number, unit = float(match.group(1)), match.group(2) or "h"
        hours = number * {"m": 1 / 60, "h": 1, "d": 24, "w": 24 * 7}[unit]
    if hours <= 0:
        raise ValueError("기간은 0보다 커야 합니다.")
    return hours


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    try:
        config["lookback_hours"] = parse_duration(config["lookback_hours"])
    except ValueError as exc:
        raise ConfigError(f"lookback_hours: {exc}") from exc

    labels = config.get("gmail_labels") or {}
    for key in REQUIRED_LABEL_KEYS:
        if not isinstance(labels.get(key), str) or not labels[key].strip():
            raise ConfigError(f"gmail_labels.{key} 값이 비어 있습니다.")

    keywords = config.get("keywords") or {}
    for key in ("korean", "english"):
        if not isinstance(keywords.get(key) or [], list):
            raise ConfigError(f"keywords.{key} 는 목록(list)이어야 합니다.")

    if not isinstance(config.get("my_addresses") or [], list):
        raise ConfigError("my_addresses 는 목록(list)이어야 합니다.")

    try:
        config["max_messages"] = int(config["max_messages"])
    except (TypeError, ValueError) as exc:
        raise ConfigError("max_messages 는 정수여야 합니다.") from exc
    return config


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"설정 파일을 찾을 수 없습니다: {path}\n"
            "  config.example.yaml 을 config.yaml 로 복사한 뒤 값을 채워 주세요."
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML 형식 오류 ({path}): {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"설정 파일 최상위는 key: value 형태여야 합니다: {path}")
    return validate_config(_deep_merge(DEFAULT_CONFIG, raw))


def default_config() -> dict[str, Any]:
    """테스트 등에서 쓰는 기본 설정 사본."""
    return validate_config(copy.deepcopy(DEFAULT_CONFIG))
