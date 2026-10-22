"""로컬 설정 랜딩 페이지 (`sip-and-sort setup`).

clone 받은 이용자가 '본인의' Google OAuth 클라이언트(credentials.json)를 등록하고,
이름(활동명)을 입력하고, Gmail 계정을 연결하는 웹 페이지를 이 PC에서만 띄운다.

- 127.0.0.1 에만 바인딩되며, 실행 시마다 새로 만든 접속 토큰이 있어야 API를 호출할 수 있다.
- 입력한 값은 이 PC의 credentials.json / token.json / config.yaml 에만 저장되고 외부로 전송되지 않는다.
  (Google 로그인 자체는 Google 서버와 직접 통신)
- 이 저장소에는 어떤 API 키/토큰도 포함되어 있지 않다.
"""

from __future__ import annotations

import copy
import hmac
import json
import logging
import secrets
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from .config import DEFAULT_CONFIG, ConfigError, _deep_merge, load_config, parse_duration
from .gmail_client import (
    AuthError,
    GmailClient,
    build_service,
    load_credentials,
    save_private_file,
    validate_client_secrets,
)
from .runner import format_report, run
from .templates import DEFAULT_TEMPLATES, TEMPLATE_LABELS

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 1_000_000
MAX_NAME_LENGTH = 50


class _LiteralDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_LiteralDumper.add_representer(str, _str_representer)


def dump_config(config: dict[str, Any]) -> str:
    header = (
        "# sip-and-sort 설정 파일 (개인정보 포함 - 절대 커밋하지 마세요)\n"
        "# `sip-and-sort setup` 랜딩 페이지 또는 직접 편집으로 수정할 수 있습니다.\n\n"
    )
    return header + yaml.dump(
        config, Dumper=_LiteralDumper, allow_unicode=True, sort_keys=False, width=1000
    )


def resolve_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (config_path.parent / path)


class SetupState:
    """랜딩 페이지가 다루는 파일들과 OAuth 진행 상태."""

    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        self.lock = threading.Lock()
        self.oauth = {"state": "idle", "message": ""}
        self.connected_email: str | None = None

    # ---- 파일 경로

    def _raw_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        return raw if isinstance(raw, dict) else {}

    def merged_config(self) -> dict[str, Any]:
        return _deep_merge(DEFAULT_CONFIG, self._raw_config())

    @property
    def credentials_path(self) -> Path:
        return resolve_path(self.config_path, self.merged_config()["credentials_path"])

    @property
    def token_path(self) -> Path:
        return resolve_path(self.config_path, self.merged_config()["token_path"])

    # ---- 상태

    def status(self) -> dict[str, Any]:
        config = self.merged_config()
        templates = config.get("templates") or {}
        return {
            "config_path": str(self.config_path),
            "config_exists": self.config_path.exists(),
            "credentials": self.credentials_path.exists(),
            "token": self.token_path.exists(),
            "email": self.connected_email,
            "oauth": dict(self.oauth),
            "activity_name": config.get("activity_name") or "",
            "lookback_hours": config.get("lookback_hours"),
            "templates": {k: templates.get(k) or v for k, v in DEFAULT_TEMPLATES.items()},
            "default_templates": DEFAULT_TEMPLATES,
            "template_labels": TEMPLATE_LABELS,
        }

    # ---- 저장

    def save_credentials(self, text: str) -> None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON 형식이 아닙니다: {exc}") from exc
        try:
            validate_client_secrets(data)
        except AuthError as exc:
            raise ValueError(str(exc)) from exc
        save_private_file(self.credentials_path, json.dumps(data, indent=2))

    def save_profile(self, payload: dict[str, Any]) -> None:
        name = str(payload.get("activity_name") or "").strip()
        if not name:
            raise ValueError("이름(활동명)을 입력해 주세요.")
        if len(name) > MAX_NAME_LENGTH or any(ch in name for ch in "\r\n{}"):
            raise ValueError(f"이름(활동명)은 줄바꿈/중괄호 없이 {MAX_NAME_LENGTH}자 이내로 입력해 주세요.")
        try:
            lookback = parse_duration(payload.get("lookback_hours") or 24)
        except ValueError as exc:
            raise ValueError(f"검사 기간: {exc}") from exc

        templates: dict[str, str] = {}
        for key, default in DEFAULT_TEMPLATES.items():
            text = str((payload.get("templates") or {}).get(key) or "").replace("\r\n", "\n")
            templates[key] = text if text.strip() else default

        raw = self._raw_config() or copy.deepcopy(DEFAULT_CONFIG)
        raw["activity_name"] = name
        raw["lookback_hours"] = int(lookback) if lookback == int(lookback) else lookback
        raw["templates"] = templates
        raw.pop("sender_name", None)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        save_private_file(self.config_path, dump_config(raw))

    # ---- Gmail 연결

    def start_oauth(self) -> None:
        with self.lock:
            if self.oauth["state"] == "running":
                return
            if not self.credentials_path.exists():
                raise ValueError("먼저 1단계에서 credentials.json 을 등록해 주세요.")
            self.oauth = {"state": "running", "message": "브라우저에서 Google 로그인을 진행해 주세요..."}
        threading.Thread(target=self._oauth_worker, daemon=True).start()

    def _oauth_worker(self) -> None:
        try:
            creds = load_credentials(self.credentials_path, self.token_path, interactive=True)
            self.connected_email = GmailClient(build_service(creds)).get_my_addresses_primary()
            self.oauth = {"state": "done", "message": "Gmail 연결 완료"}
        except Exception as exc:  # 사용자에게 그대로 보여줌
            log.debug("OAuth 실패", exc_info=True)
            self.oauth = {"state": "error", "message": str(exc)}

    def refresh_connected_email(self) -> None:
        if not self.token_path.exists() or self.connected_email:
            return
        try:
            creds = load_credentials(self.credentials_path, self.token_path, interactive=False)
            self.connected_email = GmailClient(build_service(creds)).get_my_addresses_primary()
        except Exception as exc:
            log.debug("저장된 토큰 확인 실패: %s", exc)

    def disconnect(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()
        self.connected_email = None
        self.oauth = {"state": "idle", "message": "연결이 해제되었습니다."}

    def preview(self) -> str:
        try:
            config = load_config(self.config_path)
        except ConfigError as exc:
            raise ValueError(f"2단계 설정을 먼저 저장해 주세요. ({exc})") from exc
        if not self.token_path.exists():
            raise ValueError("3단계에서 Gmail을 먼저 연결해 주세요.")
        try:
            creds = load_credentials(self.credentials_path, self.token_path, interactive=False)
        except AuthError as exc:
            raise ValueError(str(exc)) from exc
        report = run(GmailClient(build_service(creds)), config, dry_run=True)
        return format_report(report, show_drafts=True)


def _make_handler(state: SetupState, access_token: str, allowed_hosts: set[str]):
    web = resources.files("sip_and_sort").joinpath("web")
    page = web.joinpath("setup.html").read_text(encoding="utf-8")
    icon = web.joinpath("icon.png").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        server_version = "sip-and-sort-setup"

        def log_message(self, fmt, *args):  # 기본 stderr 로그 끄기
            log.debug("setup: " + fmt, *args)

        # ---- 공통

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict[str, Any]) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _host_ok(self) -> bool:
            # DNS rebinding 방지: localhost 주소로 들어온 요청만 허용
            return self.headers.get("Host", "") in allowed_hosts

        def _token_ok(self) -> bool:
            return hmac.compare_digest(self.headers.get("X-Setup-Token", ""), access_token)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                raise ValueError("요청이 너무 큽니다.")
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("잘못된 요청 형식입니다.")
            return data

        # ---- 라우팅

        def do_GET(self):
            if not self._host_ok():
                return self._send(HTTPStatus.FORBIDDEN, b"forbidden host", "text/plain")
            url = urlparse(self.path)
            if url.path == "/":
                given = (parse_qs(url.query).get("t") or [""])[0]
                if not hmac.compare_digest(given, access_token):
                    msg = "터미널에 표시된 전체 주소(?t=...)로 접속해 주세요.".encode("utf-8")
                    return self._send(HTTPStatus.FORBIDDEN, msg, "text/plain; charset=utf-8")
                return self._send(HTTPStatus.OK, page.encode("utf-8"), "text/html; charset=utf-8")
            if url.path in ("/icon.png", "/favicon.ico"):
                return self._send(HTTPStatus.OK, icon, "image/png")
            if url.path == "/api/status":
                if not self._token_ok():
                    return self._json(HTTPStatus.FORBIDDEN, {"error": "invalid token"})
                state.refresh_connected_email()
                return self._json(HTTPStatus.OK, state.status())
            return self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self):
            if not self._host_ok() or not self._token_ok():
                return self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
                if path == "/api/credentials":
                    state.save_credentials(str(payload.get("json") or ""))
                    state.disconnect()  # 클라이언트가 바뀌면 기존 토큰은 무효
                    state.oauth = {"state": "idle", "message": ""}
                    return self._json(HTTPStatus.OK, {"ok": True})
                if path == "/api/profile":
                    state.save_profile(payload)
                    return self._json(HTTPStatus.OK, {"ok": True})
                if path == "/api/connect":
                    state.start_oauth()
                    return self._json(HTTPStatus.OK, {"ok": True})
                if path == "/api/disconnect":
                    state.disconnect()
                    return self._json(HTTPStatus.OK, {"ok": True})
                if path == "/api/preview":
                    return self._json(HTTPStatus.OK, {"ok": True, "output": state.preview()})
                if path == "/api/shutdown":
                    self._json(HTTPStatus.OK, {"ok": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return None
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                log.debug("setup API 오류", exc_info=True)
                return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    return Handler


def serve(config_path: str | Path, *, port: int = 8765, open_browser: bool = True) -> None:
    state = SetupState(Path(config_path))
    access_token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", port), None)  # type: ignore[arg-type]
    actual_port = server.server_address[1]
    allowed = {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}
    server.RequestHandlerClass = _make_handler(state, access_token, allowed)
    url = f"http://127.0.0.1:{actual_port}/?t={access_token}"
    print("sip-and-sort 설정 페이지를 시작합니다. (이 PC에서만 접속 가능)")
    print(f"  {url}")
    print("  설정을 마치면 페이지의 [설정 종료] 버튼을 누르거나 Ctrl+C 로 종료하세요.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("설정 페이지를 종료했습니다.")
