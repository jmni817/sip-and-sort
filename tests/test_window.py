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


# ---------------------------------------------------------------- 창이 안 뜰 때 (WebView2 시작 실패)


def _start_that_fails(module, message=None):
    """webview.start 흉내: WebView2 시작 실패 로그를 남기고, 화면은 끝내 로드되지 않는다."""
    import logging
    import threading

    module.window.events.loaded = threading.Event()

    def start(func=None, **kwargs):
        if message:
            logging.getLogger("pywebview").error(message)
        func()

    module.start = MagicMock(side_effect=start)


def test_webview_init_failure_raises_with_reason_and_closes_window(tmp_path, fake_webview):
    _start_that_fails(fake_webview, "WebView2 initialization failed with exception:\n (0x80070070): disk full")
    state = SetupState(tmp_path / "config.yaml")
    with pytest.raises(WindowUnavailable, match="0x80070070"):
        setup_server._run_window(state, "http://127.0.0.1:1/")
    fake_webview.window.destroy.assert_called_once()
    assert state.on_shutdown is None  # 없어진 창을 [종료] 버튼이 닫으려 하지 않도록


def test_page_that_never_loads_also_falls_back(tmp_path, fake_webview, monkeypatch):
    monkeypatch.setattr(setup_server, "WINDOW_LOAD_TIMEOUT_SECONDS", 0.3)
    _start_that_fails(fake_webview)
    with pytest.raises(WindowUnavailable):
        setup_server._run_window(SetupState(tmp_path / "config.yaml"), "http://127.0.0.1:1/")
    fake_webview.window.destroy.assert_called_once()


def test_loaded_window_is_not_closed(tmp_path, fake_webview):
    fake_webview.window.events.loaded.wait.return_value = True
    fake_webview.start = MagicMock(side_effect=lambda func=None, **kwargs: func())
    setup_server._run_window(SetupState(tmp_path / "config.yaml"), "http://127.0.0.1:1/")
    fake_webview.window.destroy.assert_not_called()


def test_serve_opens_browser_and_tells_user_when_window_fails(tmp_path, fake_webview, monkeypatch):
    import http.client
    from urllib.parse import parse_qs, urlparse

    _start_that_fails(fake_webview, "WebView2 initialization failed: (0x80070070)")
    reasons, opened = [], []
    monkeypatch.setattr(setup_server, "_notify_window_fallback", reasons.append)

    def fake_open(url):  # 브라우저가 열린 뒤 페이지가 살아 있는지 확인하고 [종료]
        opened.append(url)
        parsed = urlparse(url)
        token = parse_qs(parsed.query)["t"][0]
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        conn.request("GET", f"/?t={token}")
        assert conn.getresponse().status == 200
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        conn.request("POST", "/api/shutdown", b"{}", {"X-Setup-Token": token, "Content-Type": "application/json"})
        assert conn.getresponse().status == 200

    monkeypatch.setattr(setup_server.webbrowser, "open", fake_open)
    serve(tmp_path / "config.yaml", port=0, window=True)
    assert len(opened) == 1 and "0x80070070" in reasons[0]
