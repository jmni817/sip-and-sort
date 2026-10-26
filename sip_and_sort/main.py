"""CLI 진입점: `sip-and-sort setup | auth | run`.

이 프로그램은 메일을 읽고, 라벨을 붙이고, 답장 '초안'만 저장한다. 자동 발송은 절대 하지 않는다.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config, parse_duration

EXIT_OK, EXIT_PARTIAL, EXIT_FATAL = 0, 1, 2
# PyInstaller 로 만든 exe 로 실행 중인지 여부
FROZEN = bool(getattr(sys, "frozen", False))


def app_data_dir() -> Path:
    """exe 사용자의 설정 폴더. (exe 를 어디에 두든 같은 곳에 저장)"""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "sip-and-sort"


def default_config_path() -> str:
    if os.environ.get("SIP_AND_SORT_CONFIG"):
        return os.environ["SIP_AND_SORT_CONFIG"]
    return str(app_data_dir() / "config.yaml") if FROZEN else "config.yaml"


DEFAULT_CONFIG_PATH = default_config_path()


def _duration(value: str) -> float:
    try:
        return parse_duration(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sip-and-sort",
        description="Gmail 협업 제안 메일 자동 분류 + 답장 '초안' 작성 (자동 발송 없음)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="디버그 로그 출력")
    sub = parser.add_subparsers(dest="command")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=DEFAULT_CONFIG_PATH, help=f"설정 파일 경로 (기본: {DEFAULT_CONFIG_PATH})")
    common.add_argument("--credentials", help="credentials.json 경로 (기본: config 의 credentials_path)")
    common.add_argument("--token", help="token.json 경로 (기본: config 의 token_path)")

    setup = sub.add_parser("setup", parents=[common], help="로컬 설정 랜딩 페이지 열기 (최초 1회)")
    setup.add_argument("--port", type=int, default=8765, help="설정 페이지 포트 (0 = 자동)")
    setup.add_argument("--no-browser", action="store_true", help="브라우저 자동 실행 안 함")

    auth = sub.add_parser("auth", parents=[common], help="터미널에서 Gmail OAuth 로그인만 수행")
    auth.add_argument("--no-browser", action="store_true", help="로그인 URL만 출력 (원격 서버용)")

    run = sub.add_parser("run", parents=[common], help="1회 실행")
    run.add_argument("--dry-run", action="store_true", help="라벨/초안 작업 없이 결과만 출력")
    run.add_argument("--since", type=_duration, help="검사 기간 override (예: 48h, 2d, 90m)")
    run.add_argument("--max-messages", type=int, help="검사할 최대 메일 수 override")
    run.add_argument("--show-drafts", action="store_true", help="초안 본문까지 출력 (dry-run 시 기본 켜짐)")
    run.add_argument(
        "--summary-only",
        action="store_true",
        help="건수만 출력하고 발신자/제목은 숨김 (공개 저장소의 GitHub Actions 로그용)",
    )
    run.add_argument(
        "--non-interactive",
        action="store_true",
        help="브라우저 로그인을 시도하지 않음 (CI 환경변수가 있으면 자동 적용)",
    )
    return parser


def _resolve(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else config_path.resolve().parent / path


def _paths(args, config: dict) -> tuple[Path, Path]:
    config_path = Path(args.config)
    credentials = Path(args.credentials) if args.credentials else _resolve(config_path, config["credentials_path"])
    token = Path(args.token) if args.token else _resolve(config_path, config["token_path"])
    return credentials, token


def _cmd_setup(args) -> int:
    from .setup_server import serve

    if args.credentials or args.token:
        print("참고: setup 에서는 config.yaml 의 credentials_path / token_path 값을 사용합니다.")
    serve(args.config, port=args.port, open_browser=not args.no_browser)
    return EXIT_OK


def _load_config_or_default(path: str) -> dict:
    from .config import default_config

    try:
        return load_config(path)
    except ConfigError:
        return default_config()


def _cmd_auth(args) -> int:
    from .gmail_client import GmailClient

    credentials, token = _paths(args, _load_config_or_default(args.config))
    client = GmailClient.from_files(credentials, token, interactive=True, open_browser=not args.no_browser)
    print(f"인증 완료: {client.get_my_addresses_primary()} (토큰 저장 위치: {token})")
    return EXIT_OK


def _cmd_run(args) -> int:
    from .gmail_client import GmailClient
    from .runner import format_report, run

    config = load_config(args.config)
    if not str(config.get("activity_name") or "").strip():
        print("경고: activity_name(이름/활동명)이 비어 있어 초안에 '[ ]'로 표시됩니다. "
              "`sip-and-sort setup` 에서 입력하세요.", file=sys.stderr)
    if args.max_messages:
        config["max_messages"] = args.max_messages
    credentials, token = _paths(args, config)
    interactive = not (args.non_interactive or os.environ.get("CI"))
    client = GmailClient.from_files(credentials, token, interactive=interactive)

    from .llm import load_classifier

    ai = load_classifier(config, args.config)  # 켜져 있고 키가 있을 때만 (없으면 규칙만 사용)
    report = run(client, config, since_hours=args.since, dry_run=args.dry_run, ai=ai)
    print(
        format_report(
            report,
            show_drafts=(args.show_drafts or args.dry_run) and not args.summary_only,
            summary_only=args.summary_only,
        )
    )
    return EXIT_PARTIAL if report.errors else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # Windows 콘솔에서 한글/특수문자 출력 오류 방지
        except (AttributeError, ValueError):
            pass
    raw_args = sys.argv[1:] if argv is None else argv
    # 인자 없이 실행(= exe 더블클릭) 하면 설정/실행 페이지를 연다
    double_clicked = not raw_args
    args = build_parser().parse_args(raw_args or ["setup"])
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    from .gmail_client import AuthError, GmailApiError

    handlers = {"setup": _cmd_setup, "auth": _cmd_auth, "run": _cmd_run}
    try:
        return handlers[args.command](args)
    except (ConfigError, AuthError, GmailApiError, OSError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        if FROZEN and double_clicked:  # 더블클릭 실행 시 창이 바로 닫혀 오류를 못 보는 것 방지
            input("Enter 키를 누르면 종료합니다...")
        return EXIT_FATAL
    except KeyboardInterrupt:
        return EXIT_FATAL


if __name__ == "__main__":
    sys.exit(main())
