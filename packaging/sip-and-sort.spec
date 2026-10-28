# PyInstaller 빌드 설정: 단일 실행 파일(sip-and-sort.exe) 생성
#   pip install -r requirements-build.txt
#   pyinstaller packaging/sip-and-sort.spec
# 결과물: dist/sip-and-sort.exe (macOS/Linux 에서는 dist/sip-and-sort)

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent

datas = [
    (str(root / "sip_and_sort" / "web"), "sip_and_sort/web"),
]
# Gmail API 정적 discovery 문서만 포함 (전체 googleapiclient 문서는 수십 MB)
datas += [
    (src, dest)
    for src, dest in collect_data_files("googleapiclient")
    if Path(src).name == "gmail.v1.json"
]
# HTTPS 인증서 번들
datas += collect_data_files("certifi") + collect_data_files("httplib2")

a = Analysis(
    [str(root / "packaging" / "launcher.py")],
    pathex=[str(root)],
    datas=datas,
    hiddenimports=["sip_and_sort.setup_server"],
    excludes=["tkinter", "pytest"],  # unittest 는 pyparsing 이 사용하므로 제외하면 안 됨
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="sip-and-sort",
    icon=str(root / "assets" / ("icon.ico" if sys.platform == "win32" else "icon.png")),
    # 검은 콘솔 창 없이 프로그램 창(pywebview)만 뜬다. 출력은 %APPDATA%\sip-and-sort\sip-and-sort.log 로 기록.
    console=False,
    upx=False,
)
