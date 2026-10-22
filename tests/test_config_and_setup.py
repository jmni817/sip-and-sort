import json
from pathlib import Path

import pytest
import yaml

from sip_and_sort.config import ConfigError, load_config, parse_duration
from sip_and_sort.main import build_parser
from sip_and_sort.setup_server import SetupState
from sip_and_sort.templates import DEFAULT_TEMPLATES

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("value, hours", [("48h", 48), ("2d", 48), ("90m", 1.5), ("24", 24), (12, 12), ("1w", 168)])
def test_parse_duration(value, hours):
    assert parse_duration(value) == pytest.approx(hours)


@pytest.mark.parametrize("value", ["abc", "0h", "-1h"])
def test_parse_duration_rejects_invalid(value):
    with pytest.raises(ValueError):
        parse_duration(value)


def test_example_config_loads():
    config = load_config(ROOT / "config.example.yaml")
    assert config["lookback_hours"] == 24
    assert config["gmail_labels"]["draft_done"] == "답장초안완료"
    assert set(config["templates"]) == set(DEFAULT_TEMPLATES)


def test_missing_config_gives_helpful_error(tmp_path):
    with pytest.raises(ConfigError, match="config.example.yaml"):
        load_config(tmp_path / "config.yaml")


def test_cli_parses_run_options():
    args = build_parser().parse_args(["run", "--dry-run", "--since", "48h", "--config", "x.yaml"])
    assert args.dry_run and args.since == 48 and args.config == "x.yaml"


# ---------------------------------------------------------------- 랜딩 페이지 상태/저장


def test_setup_saves_activity_name_and_templates(tmp_path):
    state = SetupState(tmp_path / "config.yaml")
    state.save_profile(
        {
            "activity_name": "새크리에이터",
            "lookback_hours": "48",
            "templates": {"price_quote": "단가 안내 {activity_name}\r\n두번째 줄", "decline_unpaid": ""},
        }
    )
    config = load_config(tmp_path / "config.yaml")
    assert config["activity_name"] == "새크리에이터"
    assert config["lookback_hours"] == 48
    assert config["templates"]["price_quote"] == "단가 안내 {activity_name}\n두번째 줄"
    assert config["templates"]["decline_unpaid"] == DEFAULT_TEMPLATES["decline_unpaid"]  # 빈 값 → 기본 문구
    assert "gmail_labels" in yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))


def test_setup_preserves_other_existing_settings(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("activity_name: old\nextra_query: in:inbox\n", encoding="utf-8")
    SetupState(path).save_profile({"activity_name": "new"})
    config = load_config(path)
    assert config["activity_name"] == "new" and config["extra_query"] == "in:inbox"


@pytest.mark.parametrize("name", ["", "   ", "줄\n바꿈", "{activity_name}", "가" * 51])
def test_setup_rejects_invalid_activity_name(tmp_path, name):
    with pytest.raises(ValueError):
        SetupState(tmp_path / "config.yaml").save_profile({"activity_name": name})


def test_setup_saves_valid_credentials_and_rejects_dummy(tmp_path):
    state = SetupState(tmp_path / "config.yaml")
    with pytest.raises(ValueError):
        state.save_credentials((ROOT / "credentials.example.json").read_text(encoding="utf-8"))
    assert not state.credentials_path.exists()

    state.save_credentials(json.dumps({"installed": {"client_id": "a.apps.googleusercontent.com", "client_secret": "b"}}))
    assert state.credentials_path == tmp_path / "credentials.json"
    status = state.status()
    assert status["credentials"] is True
    assert "client_secret" not in json.dumps(status)  # 비밀 값은 다시 내보내지 않음


def test_no_arguments_opens_setup_page(monkeypatch):
    # exe 더블클릭(인자 없음) → 설정/실행 페이지
    from sip_and_sort import main as main_module

    called = {}
    monkeypatch.setattr(main_module, "_cmd_setup", lambda args: called.setdefault("cmd", args.command) and 0)
    assert main_module.main([]) == 0
    assert called["cmd"] == "setup"


def test_frozen_exe_stores_config_in_app_data(monkeypatch, tmp_path):
    from sip_and_sort import main as main_module

    monkeypatch.delenv("SIP_AND_SORT_CONFIG", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(main_module, "FROZEN", True)
    path = Path(main_module.default_config_path())
    assert path.name == "config.yaml" and path.parent.name == "sip-and-sort"


def test_oauth_login_link_is_exposed_and_failures_are_reported(tmp_path, monkeypatch):
    import webbrowser

    from sip_and_sort import setup_server

    state = SetupState(tmp_path / "config.yaml")
    state.save_credentials(json.dumps({"installed": {"client_id": "a.apps.googleusercontent.com", "client_secret": "b"}}))

    def fake_load_credentials(*args, browser=None, **kwargs):
        webbrowser.get(browser).open("https://accounts.google.com/o/oauth2/auth?x=1")
        assert state.status()["oauth"]["auth_url"].startswith("https://accounts.google.com/")
        raise SystemExit("worker died")  # BaseException 이어도 '진행 중'에 멈추지 않아야 함

    monkeypatch.setattr(setup_server, "load_credentials", fake_load_credentials)
    state.start_oauth()
    state._oauth_thread.join(5)
    oauth = state.status()["oauth"]
    assert oauth["state"] == "error" and "worker died" in oauth["message"]
