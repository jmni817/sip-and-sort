"""새 버전 확인과 다운로드 (GitHub Releases).

- GitHub 공개 API 로 최신 릴리스만 묻는다. 로그인·키 불필요, 메일이나 설정 정보는 보내지 않는다.
- 인터넷이 끊겼거나 응답이 이상하면 조용히 '업데이트 없음'으로 처리한다.
- 다운로드는 이 저장소의 GitHub 릴리스 파일만 https 로 받는다.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from . import __version__

log = logging.getLogger(__name__)

GITHUB_REPO = "jmni817/sip-and-sort"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXE_ASSET_NAME = "sip-and-sort.exe"
# 릴리스 파일은 github.com 에서 GitHub 파일 서버로 넘겨주므로 그 주소들만 허용
ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
CHUNK = 256 * 1024


@dataclass
class UpdateInfo:
    version: str  # "0.1.11"
    tag: str  # "v0.1.11"
    notes: str  # 릴리스 설명 (CHANGELOG 의 해당 버전 부분)
    page_url: str  # 릴리스 페이지
    download_url: str | None  # exe 파일 (없으면 None)
    size: int  # exe 크기 (바이트)


def parse_version(text: str) -> tuple[int, ...] | None:
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", str(text).strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def is_newer(candidate: str, current: str = __version__) -> bool:
    new, cur = parse_version(candidate), parse_version(current)
    if new is None or cur is None:
        return False
    width = max(len(new), len(cur))
    return new + (0,) * (width - len(new)) > cur + (0,) * (width - len(cur))


def clean_notes(body: str, limit: int = 1200) -> str:
    """릴리스 설명(마크다운)을 팝업에 보여 줄 평문으로. 공통 안내(--- 아래)는 뺀다."""
    text = body.split("\n---", 1)[0]
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^#+\s*", "", line)  # 제목 기호
        line = line.replace("**", "").replace("`", "")
        lines.append(line.rstrip())
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def check_latest(
    current: str = __version__,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
    timeout: float = 8.0,
) -> UpdateInfo | None:
    """새 버전이 있으면 UpdateInfo, 없거나 확인할 수 없으면 None."""
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"sip-and-sort/{current}"},
    )
    try:
        with opener(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # 오프라인, 요청 제한, 형식 오류 등
        log.debug("업데이트 확인 실패: %s", exc)
        return None
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "")
    if not is_newer(tag, current):
        return None
    asset = next(
        (a for a in data.get("assets") or [] if isinstance(a, dict) and a.get("name") == EXE_ASSET_NAME),
        None,
    )
    download_url = asset.get("browser_download_url") if asset else None
    if download_url and not _allowed(download_url):
        download_url = None
    return UpdateInfo(
        version=tag.lstrip("v"),
        tag=tag,
        notes=clean_notes(str(data.get("body") or "")),
        page_url=str(data.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases/latest"),
        download_url=download_url,
        size=int(asset.get("size") or 0) if asset else 0,
    )


def _allowed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "") in ALLOWED_DOWNLOAD_HOSTS


def download(
    info: UpdateInfo,
    dest: Path,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
    on_progress: Callable[[int, int], None] = lambda done, total: None,
    timeout: float = 30.0,
) -> Path:
    """새 exe 를 dest 로 받는다. 받는 중에는 .part 파일에 쓰고, 크기가 맞을 때만 완성본으로 바꾼다."""
    if not info.download_url or not _allowed(info.download_url):
        raise ValueError("다운로드 주소가 이 프로그램의 GitHub 릴리스가 아닙니다.")
    part = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(info.download_url, headers={"User-Agent": f"sip-and-sort/{__version__}"})
    with opener(request, timeout=timeout) as response:
        final_url = response.geturl() if hasattr(response, "geturl") else info.download_url
        if not _allowed(final_url):
            raise ValueError("다운로드가 예상하지 못한 주소로 넘어가 중단했습니다.")
        total = int(response.headers.get("Content-Length") or info.size or 0)
        done = 0
        with open(part, "wb") as out:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                on_progress(done, total)
    expected = info.size or total
    if expected and done != expected:
        part.unlink(missing_ok=True)
        raise ValueError(f"다운로드가 중간에 끊겼습니다 ({done:,} / {expected:,} 바이트). 다시 시도해 주세요.")
    part.replace(dest)
    return dest
