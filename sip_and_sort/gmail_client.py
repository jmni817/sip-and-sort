"""Gmail API 얇은 wrapper: 인증, 검색, 라벨, 초안(draft) 생성.

!!! 중요 !!!
이 모듈에는 메일을 '발송(send)'하는 함수가 의도적으로 존재하지 않는다.
users.messages.send / users.drafts.send 는 어디에서도 호출하지 않는다.
답장은 오직 '초안(draft)'으로만 저장되며, 실제 발송은 사용자가 Gmail에서 직접 확인 후 한다.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import random
import socket
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable

from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)

# gmail.modify: 메일 읽기 + 라벨 변경 + 초안 생성. (영구 삭제 불가)
# 이 스코프는 기술적으로 발송도 허용하지만, 이 프로그램 코드는 발송 API를 절대 호출하지 않는다.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRYABLE_403_REASONS = ("rateLimitExceeded", "userRateLimitExceeded", "backendError")


class AuthError(Exception):
    """OAuth 인증 실패 / 자격증명 파일 문제."""


class GmailApiError(Exception):
    """재시도 후에도 실패한 Gmail API 호출."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------- 인증


def validate_client_secrets(data: Any) -> None:
    """credentials.json 내용이 OAuth '데스크톱 앱' 클라이언트 형식인지 검사."""
    if not isinstance(data, dict):
        raise AuthError("credentials.json 형식이 올바르지 않습니다 (JSON 객체가 아님).")
    if "web" in data and "installed" not in data:
        raise AuthError(
            "'웹 애플리케이션' 유형의 OAuth 클라이언트입니다. "
            "Google Cloud Console에서 '데스크톱 앱' 유형으로 다시 만들어 주세요."
        )
    installed = data.get("installed")
    if not isinstance(installed, dict):
        raise AuthError("credentials.json 에 'installed' 항목이 없습니다 (데스크톱 앱 클라이언트 필요).")
    for key in ("client_id", "client_secret"):
        value = installed.get(key)
        if not value or str(value).startswith("YOUR_"):
            raise AuthError(f"credentials.json 의 {key} 값이 비어 있거나 예시 값입니다.")


def save_private_file(path: Path, content: str) -> None:
    """토큰/키 파일은 소유자만 읽을 수 있게 저장 (POSIX에서 0600)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:  # Windows 등
        pass


def load_credentials(
    credentials_path: str | Path,
    token_path: str | Path,
    *,
    interactive: bool = True,
    open_browser: bool = True,
):
    """token.json 이 있으면 재사용(필요 시 refresh), 없으면 브라우저 OAuth 로그인."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials_path, token_path = Path(credentials_path), Path(token_path)
    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except (ValueError, json.JSONDecodeError) as exc:
            log.warning("token.json 을 읽을 수 없어 재인증합니다: %s", exc)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_private_file(token_path, creds.to_json())
            return creds
        except RefreshError as exc:
            log.warning("토큰 갱신 실패 (만료/폐기됨): %s", exc)
            creds = None

    if not interactive:
        raise AuthError(
            f"유효한 토큰({token_path})이 없습니다. 로컬에서 `sip-and-sort setup` "
            "또는 `sip-and-sort auth` 로 먼저 로그인해 주세요."
        )
    if not credentials_path.exists():
        raise AuthError(
            f"OAuth 클라이언트 파일({credentials_path})이 없습니다. "
            "`sip-and-sort setup` 랜딩 페이지에서 본인의 credentials.json 을 등록해 주세요."
        )
    try:
        validate_client_secrets(json.loads(credentials_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise AuthError(f"credentials.json JSON 파싱 실패: {exc}") from exc

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(
        host="localhost",
        port=0,
        open_browser=open_browser,
        authorization_prompt_message="브라우저에서 아래 주소로 Google 로그인을 진행하세요:\n{url}",
        success_message="인증이 완료되었습니다. 이 창을 닫고 터미널/설정 페이지로 돌아가세요.",
    )
    save_private_file(token_path, creds.to_json())
    return creds


def build_service(creds):
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --------------------------------------------------------------------------- 재시도


def _is_retryable(error: HttpError) -> bool:
    status = getattr(error.resp, "status", None)
    if status in RETRYABLE_STATUS:
        return True
    if status == 403:
        content = error.content.decode("utf-8", "replace") if isinstance(error.content, bytes) else str(error.content)
        return any(reason in content for reason in RETRYABLE_403_REASONS)
    return False


def execute_with_retry(
    request,
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
):
    """Gmail API 요청 실행. 레이트리밋(429/403 rateLimit)·5xx·네트워크 오류는 지수 백오프로 재시도."""
    for attempt in range(max_retries + 1):
        try:
            return request.execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            if not _is_retryable(exc) or attempt == max_retries:
                raise GmailApiError(f"Gmail API 오류 (HTTP {status}): {exc}", status) from exc
            log.debug("Gmail API HTTP %s, 재시도 %d/%d", status, attempt + 1, max_retries)
        except (socket.timeout, TimeoutError, ConnectionError) as exc:
            if attempt == max_retries:
                raise GmailApiError(f"네트워크 오류: {exc}") from exc
            log.debug("네트워크 오류, 재시도 %d/%d: %s", attempt + 1, max_retries, exc)
        sleep(min(base_delay * (2**attempt), 60.0) + random.uniform(0, 0.5))
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------- 클라이언트


class GmailClient:
    """Gmail API wrapper. (send 메서드는 의도적으로 없음)"""

    def __init__(self, service, *, user_id: str = "me", max_retries: int = 5, sleep=time.sleep):
        self._service = service
        self._user = user_id
        self._max_retries = max_retries
        self._sleep = sleep
        self._label_cache: dict[str, str] | None = None

    @classmethod
    def from_files(cls, credentials_path, token_path, *, interactive=True, open_browser=True):
        creds = load_credentials(
            credentials_path, token_path, interactive=interactive, open_browser=open_browser
        )
        return cls(build_service(creds))

    def _call(self, request):
        return execute_with_retry(request, max_retries=self._max_retries, sleep=self._sleep)

    @property
    def _users(self):
        return self._service.users()

    # ---- 계정

    def get_my_addresses_primary(self) -> str:
        return self._call(self._users.getProfile(userId=self._user))["emailAddress"].lower()

    def get_my_addresses(self) -> set[str]:
        addresses = {self.get_my_addresses_primary()}
        try:
            send_as = self._call(self._users.settings().sendAs().list(userId=self._user))
            addresses |= {s["sendAsEmail"].lower() for s in send_as.get("sendAs", [])}
        except GmailApiError as exc:  # 별칭 조회 실패는 치명적이지 않음
            log.debug("sendAs 조회 실패: %s", exc)
        return addresses

    # ---- 검색 / 조회

    def search_messages(self, query: str, max_results: int = 200) -> list[dict[str, str]]:
        """검색 결과 [{id, threadId}, ...] (최신순, 페이지네이션 처리)."""
        results: list[dict[str, str]] = []
        page_token = None
        while len(results) < max_results:
            response = self._call(
                self._users.messages().list(
                    userId=self._user,
                    q=query,
                    maxResults=min(100, max_results - len(results)),
                    pageToken=page_token,
                )
            )
            results.extend(response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return results[:max_results]

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        return self._call(self._users.threads().get(userId=self._user, id=thread_id, format="full"))

    # ---- 라벨

    def list_labels(self, *, refresh: bool = False) -> dict[str, str]:
        """{라벨 이름: 라벨 ID}"""
        if self._label_cache is None or refresh:
            response = self._call(self._users.labels().list(userId=self._user))
            self._label_cache = {lb["name"]: lb["id"] for lb in response.get("labels", [])}
        return dict(self._label_cache)

    def find_label_id(self, name: str) -> str | None:
        return self.list_labels().get(name)

    def get_or_create_label(self, name: str) -> str:
        """라벨이 없으면 생성. "부모/자식" 형태면 부모 라벨부터 만든다."""
        existing = self.find_label_id(name)
        if existing:
            return existing
        if "/" in name:
            self.get_or_create_label(name.rsplit("/", 1)[0])
        body = {"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        try:
            created = self._call(self._users.labels().create(userId=self._user, body=body))
        except GmailApiError as exc:
            if exc.status == 409:  # 다른 실행이 동시에 만든 경우
                label_id = self.list_labels(refresh=True).get(name)
                if label_id:
                    return label_id
            raise
        assert self._label_cache is not None
        self._label_cache[name] = created["id"]
        log.info("라벨 생성: %s", name)
        return created["id"]

    def add_thread_labels(self, thread_id: str, label_ids: list[str]) -> None:
        self._call(
            self._users.threads().modify(
                userId=self._user, id=thread_id, body={"addLabelIds": label_ids}
            )
        )

    # ---- 초안 (발송 아님!)

    def create_reply_draft(
        self,
        *,
        thread_id: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = "",
        references: str = "",
    ) -> dict[str, Any]:
        """답장 '초안'을 임시보관함에 저장. 절대 발송하지 않는다."""
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = f"{references} {in_reply_to}".strip()
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        return self._call(
            self._users.drafts().create(
                userId=self._user, body={"message": {"raw": raw, "threadId": thread_id}}
            )
        )
