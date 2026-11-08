"""새 버전 안내와 다운로드. 실제 GitHub 대신 가짜 응답을 쓴다."""

import io
import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sip_and_sort import setup_server, updates
from sip_and_sort.setup_server import SetupState
from sip_and_sort.updates import UpdateInfo, check_latest, clean_notes, download, is_newer

# conftest 가 check_latest 를 막아 두므로 원본을 따로 잡아 둔다
REAL_CHECK_LATEST = updates.__dict__["check_latest"]

BODY = "\n### ✨ 업데이트 안내 팝업\n- 새 버전이 나오면 **안내**합니다.\n\n\n---\n**다운로드:** 공통 안내"
EXE_URL = "https://github.com/jmni817/sip-and-sort/releases/download/v9.9.9/sip-and-sort.exe"


def release(tag="v9.9.9", url=EXE_URL, size=6, **extra):
    return {
        "tag_name": tag,
        "body": BODY,
        "html_url": f"https://github.com/jmni817/sip-and-sort/releases/tag/{tag}",
        "assets": [{"name": "sip-and-sort.exe", "browser_download_url": url, "size": size}],
        **extra,
    }


def opener_returning(payload):
    resp = MagicMock()
    resp.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return MagicMock(return_value=resp)


@pytest.fixture
def real_check(monkeypatch):
    monkeypatch.setattr(updates, "check_latest", REAL_CHECK_LATEST)


@pytest.mark.parametrize(
    "candidate, current, expected",
    [("v0.1.11", "0.1.10", True), ("v0.1.10", "0.1.10", False), ("v0.1.9", "0.1.10", False),
     ("v0.2", "0.1.10", True), ("v1.0.0", "0.9.99", True), ("nightly", "0.1.10", False)],
)
def test_is_newer_compares_numbers_not_text(candidate, current, expected):
    assert is_newer(candidate, current) is expected


def test_check_latest_returns_new_version_info(real_check):
    info = check_latest("0.1.10", opener=opener_returning(release()))
    assert info.version == "9.9.9" and info.download_url == EXE_URL and info.size == 6
    assert "업데이트 안내 팝업" in info.notes and "**" not in info.notes
    assert "공통 안내" not in info.notes  # --- 아래 공통 문구는 뺀다


@pytest.mark.parametrize(
    "payload",
    [release(tag="v0.1.10"), release(draft=True), release(prerelease=True), ["not", "a", "dict"]],
)
def test_check_latest_ignores_old_or_unofficial_releases(real_check, payload):
    assert check_latest("0.1.10", opener=opener_returning(payload)) is None


def test_check_latest_is_silent_when_offline(real_check):
    assert check_latest("0.1.10", opener=MagicMock(side_effect=OSError("offline"))) is None


def test_check_latest_drops_download_link_outside_github(real_check):
    info = check_latest("0.1.10", opener=opener_returning(release(url="https://evil.example.com/x.exe")))
    assert info is not None and info.download_url is None


def test_clean_notes_trims_markdown():
    assert clean_notes("## 제목\n- **굵게** `코드`\n---\n꼬리") == "제목\n- 굵게 코드"


def _info(size=6):
    return UpdateInfo("9.9.9", "v9.9.9", "notes", "https://github.com/x", EXE_URL, size)


def _download_response(data, final_url="https://objects.githubusercontent.com/abc"):
    resp = MagicMock()
    body = io.BytesIO(data)
    inner = resp.__enter__.return_value
    inner.read.side_effect = lambda n=-1: body.read(n)
    inner.geturl.return_value = final_url
    inner.headers = {"Content-Length": str(len(data))}
    return MagicMock(return_value=resp)


def test_download_writes_file_and_reports_progress(tmp_path):
    seen = []
    dest = download(_info(), tmp_path / "new.exe", opener=_download_response(b"MZ1234"),
                    on_progress=lambda d, t: seen.append((d, t)))
    assert dest.read_bytes() == b"MZ1234" and seen[-1] == (6, 6)
    assert not (tmp_path / "new.exe.part").exists()


def test_download_rejects_truncated_file(tmp_path):
    with pytest.raises(ValueError, match="끊겼"):
        download(_info(size=100), tmp_path / "new.exe", opener=_download_response(b"MZ1234"))
    assert not (tmp_path / "new.exe").exists() and not (tmp_path / "new.exe.part").exists()


def test_download_rejects_redirect_outside_github(tmp_path):
    with pytest.raises(ValueError, match="예상하지 못한 주소"):
        download(_info(), tmp_path / "new.exe", opener=_download_response(b"MZ1234", "https://evil.example.com/x"))


# ---------------------------------------------------------------- 설정 서버 연결


def test_status_shows_update_after_background_check(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "check_latest", lambda *a, **k: _info())
    state = SetupState(tmp_path / "config.yaml")
    assert state.status()["update"] is None
    state.maybe_check_update()
    for _ in range(50):
        if state.status()["update"]:
            break
        time.sleep(0.02)
    update = state.status()["update"]
    assert update["version"] == "9.9.9" and update["can_install"] is False  # 테스트는 exe 실행이 아님
    state.maybe_check_update()  # 12시간 안에는 다시 묻지 않는다


def test_install_downloads_launches_new_version_and_exits(tmp_path, monkeypatch):
    state = SetupState(tmp_path / "config.yaml")
    state._update = _info()
    monkeypatch.setattr(setup_server, "_is_frozen_exe", lambda: True)
    monkeypatch.setattr(setup_server, "_update_destination", lambda info: tmp_path / "sip-and-sort-v9.9.9.exe")
    monkeypatch.setattr(setup_server, "UPDATE_LAUNCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(updates, "download", lambda info, dest, on_progress: (on_progress(6, 6), dest.write_bytes(b"MZ"))[1])
    launched, exited = [], []
    monkeypatch.setattr(setup_server, "_launch", launched.append)
    state.request_exit = lambda: exited.append(True)

    assert state.status()["update"]["can_install"] is True
    state.start_update_download()
    for _ in range(100):
        if exited:
            break
        time.sleep(0.02)
    assert launched == [tmp_path / "sip-and-sort-v9.9.9.exe"] and exited == [True]
    assert state.status()["update"]["download"]["state"] == "done"


def test_install_refused_when_not_running_as_exe(tmp_path):
    state = SetupState(tmp_path / "config.yaml")
    state._update = _info()
    with pytest.raises(ValueError, match="릴리스 페이지"):
        state.start_update_download()


def test_update_destination_is_next_to_current_exe(tmp_path, monkeypatch):
    monkeypatch.setattr(setup_server.sys, "executable", str(tmp_path / "sip-and-sort.exe"))
    assert setup_server._update_destination(_info()) == tmp_path / "sip-and-sort-v9.9.9.exe"
