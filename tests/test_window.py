"""프로그램 창 모드 (pywebview). 실제 창 대신 가짜 webview 모듈로 검증한다."""

import sys
import types
from unittest.mock import MagicMock

import pytest

from sip_and_sort import setup_server
from sip_and_sort.main import build_parser
from sip_and_sort.setup_server import DesktopBridge, SetupState, WindowUnavailable, serve


@pytest.fixture
def fake_webview(monkeypatch):
    module = types.ModuleType("webview")
    module.window = MagicMock()
    module.create_window = MagicMock(return_value=module.window)
    module.start = MagicMock()  # 즉시 반환 = 사용자가 창을 닫은 것과 같음
    monkeypatch.setitem(sys.modules, "webview", module)
    return module


def test_double_click_opens_program_window(monkeypatch):
    from sip_and_sort import main as main_module

    seen = {}
    monkeypatch.setattr(main_module, "_cmd_setup", lambda args: seen.setdefault("window", args.window) and 0)
    main_module.main([])
    assert seen["window"] is True
    assert build_parser().parse_args(["setup"]).window is False  # 명령어로 실행하면 기존처럼 브라우저


def test_serve_in_window_mode_exits_when_window_closes(tmp_path, fake_webview, monkeypatch):
    opened = []
    monkeypatch.setattr(setup_server.webbrowser, "open", opened.append)
    serve(tmp_path / "config.yaml", port=0, window=True)  # 창이 닫히면 돌아와야 한다

    title, url = fake_webview.create_window.call_args.args
    kwargs = fake_webview.create_window.call_args.kwargs
    assert title == "sip-and-sort" and url.startswith("http://127.0.0.1:") and "?t=" in url
    assert isinstance(kwargs["js_api"], DesktopBridge)
    fake_webview.start.assert_called_once()
    assert opened == []  # 브라우저는 열지 않는다


def test_window_failure_falls_back_to_browser(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "webview", None)  # pywebview 없음
    with pytest.raises(WindowUnavailable):
        setup_server._run_window(SetupState(tmp_path / "config.yaml"), "http://127.0.0.1:1/")


def test_bridge_opens_only_https_links_in_system_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(setup_server, "open_in_system_browser", lambda url: opened.append(url) or True)
    bridge = DesktopBridge()
    assert bridge.open_external("https://accounts.google.com/o/oauth2/auth?x=1") is True
    assert bridge.open_external("file:///C:/Windows/System32/calc.exe") is False
    assert bridge.open_external("javascript:alert(1)") is False
    assert opened == ["https://accounts.google.com/o/oauth2/auth?x=1"]


def test_bridge_close_destroys_window():
    bridge = DesktopBridge()
    bridge.close()  # 창이 없어도 오류 없음
    bridge._window = MagicMock()
    bridge.close()
    bridge._window.destroy.assert_called_once()
