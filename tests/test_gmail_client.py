"""Gmail API 호출부 테스트 — 실제 API 대신 unittest.mock 사용."""

import base64
import json
from email import message_from_bytes
from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from sip_and_sort.gmail_client import (
    AuthError,
    GmailApiError,
    GmailClient,
    execute_with_retry,
    validate_client_secrets,
)


def http_error(status: int, reason: str = "") -> HttpError:
    content = json.dumps({"error": {"code": status, "errors": [{"reason": reason}]}}).encode()
    return HttpError(httplib2.Response({"status": status}), content)


def request_returning(*outcomes):
    """execute() 가 outcomes 를 차례로 반환/발생시키는 가짜 요청."""
    request = MagicMock()
    request.execute.side_effect = list(outcomes)
    return request


# ---------------------------------------------------------------- 재시도


def test_retries_on_rate_limit_then_succeeds():
    sleeps = []
    request = request_returning(http_error(429), http_error(503), {"ok": True})
    assert execute_with_retry(request, sleep=sleeps.append) == {"ok": True}
    assert request.execute.call_count == 3
    assert len(sleeps) == 2 and sleeps[1] > sleeps[0] - 0.5  # 지수 백오프


def test_retries_on_403_user_rate_limit():
    request = request_returning(http_error(403, "userRateLimitExceeded"), {"ok": 1})
    assert execute_with_retry(request, sleep=lambda _: None) == {"ok": 1}


def test_does_not_retry_on_permission_error():
    request = request_returning(http_error(403, "insufficientPermissions"))
    with pytest.raises(GmailApiError) as info:
        execute_with_retry(request, sleep=lambda _: None)
    assert info.value.status == 403
    assert request.execute.call_count == 1


def test_gives_up_after_max_retries():
    request = request_returning(*[http_error(500)] * 4)
    with pytest.raises(GmailApiError):
        execute_with_retry(request, max_retries=3, sleep=lambda _: None)
    assert request.execute.call_count == 4


def test_revoked_token_becomes_auth_error_without_retry():
    from google.auth.exceptions import RefreshError

    request = request_returning(RefreshError("invalid_grant"))
    with pytest.raises(AuthError, match="다시 연결"):
        execute_with_retry(request, sleep=lambda _: None)
    assert request.execute.call_count == 1


def test_retries_network_errors():
    request = request_returning(ConnectionError("reset"), {"ok": 1})
    assert execute_with_retry(request, sleep=lambda _: None) == {"ok": 1}


# ---------------------------------------------------------------- 클라이언트


@pytest.fixture
def service():
    return MagicMock()


@pytest.fixture
def client(service):
    return GmailClient(service, sleep=lambda _: None)


def test_client_never_exposes_send(client, service):
    assert not any("send" in name.lower() for name in dir(client))


def test_search_paginates(client, service):
    messages = service.users.return_value.messages.return_value
    messages.list.return_value.execute.side_effect = [
        {"messages": [{"id": "1", "threadId": "t1"}], "nextPageToken": "p2"},
        {"messages": [{"id": "2", "threadId": "t2"}]},
    ]
    assert [m["id"] for m in client.search_messages("after:1")] == ["1", "2"]
    assert messages.list.call_args_list[1].kwargs["pageToken"] == "p2"


def test_get_or_create_label_creates_parent_then_child_and_caches(client, service):
    labels = service.users.return_value.labels.return_value
    labels.list.return_value.execute.return_value = {"labels": [{"name": "INBOX", "id": "INBOX"}]}
    labels.create.return_value.execute.side_effect = [{"id": "L_parent"}, {"id": "L_child"}]

    assert client.get_or_create_label("협업제안/유료광고") == "L_child"
    created = [c.kwargs["body"]["name"] for c in labels.create.call_args_list]
    assert created == ["협업제안", "협업제안/유료광고"]

    assert client.get_or_create_label("협업제안/유료광고") == "L_child"  # 캐시 사용
    assert labels.create.call_count == 2


def test_existing_label_is_reused(client, service):
    labels = service.users.return_value.labels.return_value
    labels.list.return_value.execute.return_value = {"labels": [{"name": "답장초안완료", "id": "L1"}]}
    assert client.get_or_create_label("답장초안완료") == "L1"
    labels.create.assert_not_called()


def test_create_reply_draft_builds_threaded_mime(client, service):
    drafts = service.users.return_value.drafts.return_value
    drafts.create.return_value.execute.return_value = {"id": "d1"}

    client.create_reply_draft(
        thread_id="t1",
        to="김담당 <manager@brand-example.co.kr>",
        subject="Re: 문의",
        body="안녕하세요",
        in_reply_to="<m1@brand>",
        references="<m0@brand>",
    )
    body = drafts.create.call_args.kwargs["body"]
    assert body["message"]["threadId"] == "t1"
    mime = message_from_bytes(base64.urlsafe_b64decode(body["message"]["raw"]))
    assert mime["In-Reply-To"] == "<m1@brand>"
    assert mime["References"] == "<m0@brand> <m1@brand>"
    assert mime.get_payload(decode=True).decode("utf-8").strip() == "안녕하세요"
    # 초안만 만들고 발송 API는 호출하지 않는다
    drafts.send.assert_not_called()
    service.users.return_value.messages.return_value.send.assert_not_called()


def test_my_addresses_include_send_as_aliases(client, service):
    users = service.users.return_value
    users.getProfile.return_value.execute.return_value = {"emailAddress": "Me@Example.com"}
    users.settings.return_value.sendAs.return_value.list.return_value.execute.return_value = {
        "sendAs": [{"sendAsEmail": "me@example.com"}, {"sendAsEmail": "biz@example.org"}]
    }
    assert client.get_my_addresses() == {"me@example.com", "biz@example.org"}


# ---------------------------------------------------------------- credentials.json 검증


def test_validate_client_secrets_accepts_desktop_client():
    validate_client_secrets({"installed": {"client_id": "abc.apps.googleusercontent.com", "client_secret": "s"}})


@pytest.mark.parametrize(
    "data",
    [
        {"web": {"client_id": "x", "client_secret": "y"}},
        {"installed": {"client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com", "client_secret": "YOUR_CLIENT_SECRET"}},
        {"installed": {"client_id": "x"}},
        [],
    ],
)
def test_validate_client_secrets_rejects_invalid(data):
    with pytest.raises(AuthError):
        validate_client_secrets(data)


def test_example_credentials_file_is_rejected():
    from pathlib import Path

    example = Path(__file__).parents[1] / "credentials.example.json"
    with pytest.raises(AuthError):
        validate_client_secrets(json.loads(example.read_text(encoding="utf-8")))
