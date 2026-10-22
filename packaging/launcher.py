"""PyInstaller 진입점. 더블클릭하면 설정/실행 페이지가 열린다."""

import sys

from sip_and_sort.main import main

if __name__ == "__main__":
    sys.exit(main())
