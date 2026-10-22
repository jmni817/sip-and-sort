<p align="center"><img src="assets/icon.png" alt="sip-and-sort icon" width="160"></p>

<h1 align="center">🍓 sip-and-sort</h1>

> "딸기우유 한 모금 마시는 사이에, 쌓여있던 협업 메일 분류부터 답장 초안 작성까지 한번에 끝!"
> A smart & aesthetic open-source Gmail sorter for creators and developers.

⚠️ **중요 주의사항 (Disclaimer)**
본 프로그램은 수신된 메일을 분석하여 라벨을 부여하고, 조건이 충족될 시 **Gmail 임시보관함(Drafts)에 '초안'만을 저장**합니다. 어떠한 경우에도 메일을 **자동으로 발송(Send)하지 않으며**, 최종 확인 및 발송 책임은 전적으로 사용자에게 있습니다.

🔑 이 저장소에는 **어떤 API 키·OAuth 클라이언트·토큰도 포함되어 있지 않습니다.** 사용하는 분이 각자 본인의 Google Cloud 프로젝트에서 발급한 `credentials.json`을 로컬 설정 페이지에 등록해 본인 Gmail에 연결합니다.

---

## ✨ 무엇을 해주나요?

1. 최근 N시간(기본 24시간) 안에 받은 메일 중 `협업 · 제휴 · 협찬 · 광고 · PPL · 브랜드 · 캠페인 · 서포터즈 · 앰버서더`, `collaboration · sponsorship · partnership · campaign · PR · brand deal` 등의 키워드가 들어간 메일을 찾습니다.
   뉴스레터·대량 마케팅 메일(`List-Unsubscribe` 헤더, 제목의 `(광고)` 표기, `noreply` 발신, 발신자=수신자, BCC 수신 등)은 자동으로 제외합니다.
2. 메일을 **브랜드협찬 / 유료광고 / 기타**로 분류하고 Gmail 라벨을 붙입니다. (라벨이 없으면 자동 생성)
3. 아래 상황 중 **하나에만 명확히** 해당할 때만 답장 초안을 임시보관함에 저장합니다.

   | 상황 | 판단 예시 | 초안 |
   |---|---|---|
   | **A** 단가/비용 문의 | "단가", "견적", "rate card" | 단가 안내 |
   | **B** 무가 협업 | "무상·제품만 제공" + "업로드·리뷰 필수" | 정중한 거절 |
   | **C** 순수 선물 | "선물·보내드리고" + "업로드 의무 없음" | 감사히 수락 |
   | 그 외 / 여러 상황에 동시 해당 | — | 초안 없이 **직접 검토 필요** 표시 |

4. 초안을 만든 메일에는 `답장초안완료` 라벨을 추가로 붙이고, 끝나면 분류별 건수와 메일 목록을 요약 출력합니다.

이미 라벨이 붙은 스레드는 다시 처리하지 않으므로 여러 번 실행해도 초안이 중복되지 않습니다. 답장 초안의 인사말·서명에는 설정 페이지에서 입력한 **이름(활동명)** 이 들어갑니다.

---

## 💾 가장 쉬운 방법: exe 다운로드 (Windows, 설치 없음)

Python이나 명령어 없이 바로 쓸 수 있습니다.

1. [**Releases**](https://github.com/jmni817/sip-and-sort/releases/latest) 페이지에서 `sip-and-sort.exe`를 다운로드합니다.
2. 아래 **🛠️ Google Cloud 콘솔 설정 방법**을 따라 본인의 `credentials.json`을 받습니다. (최초 1회, 약 5분)
3. `sip-and-sort.exe`를 **더블클릭**하면 검은 창과 함께 브라우저에 설정 페이지가 열립니다.
4. 페이지에서 차례대로 ① `credentials.json` 등록 → ② 이름(활동명) 입력 → ③ Gmail 연결 → ④ **[지금 정리하기]** 를 누릅니다.

다음부터는 exe를 실행해 **[지금 정리하기]** 만 누르면 됩니다. 다 쓰면 페이지의 [종료] 버튼을 누르거나 검은 창을 닫으세요.

- **"Windows의 PC 보호" 경고가 뜨면:** 서명되지 않은 개인 프로젝트라서 나오는 안내입니다. **추가 정보 → 실행**을 누르세요. 걱정된다면 이 저장소의 코드를 직접 확인하거나 아래 "로컬 설치" 방법을 쓰셔도 됩니다.
- **설정이 저장되는 곳:** `%APPDATA%\sip-and-sort\` (`config.yaml`, `credentials.json`, `token.json`). exe를 어디로 옮겨도 설정은 유지되고, 이 폴더를 지우면 초기화됩니다.
- **매시간 자동으로 돌리고 싶다면:** 아래 [작업 스케줄러](#로컬-cron--launchd--작업-스케줄러로-돌리기) 예시에서 `$exe`를 다운로드한 `sip-and-sort.exe` 경로로 바꾸면 됩니다.
- exe도 명령어를 그대로 지원합니다. 예: `sip-and-sort.exe run --dry-run`

> exe에도 어떤 API 키나 토큰도 들어 있지 않습니다. Google Cloud에서 본인 키를 발급받는 단계는 Google 정책상 생략할 수 없습니다.

---

## 🛠️ Google Cloud 콘솔 설정 방법 (최초 1회)

1. [Google Cloud Console](https://console.cloud.google.com/)에 로그인 후 새 프로젝트를 생성합니다.
2. **API 및 서비스 > 라이브러리**로 이동하여 **Gmail API**를 검색하고 `사용` 단추를 누릅니다.
3. **OAuth 동의 화면** 탭(콘솔 버전에 따라 **Google 인증 플랫폼**)으로 이동하여 `외부(External)`를 선택하고 필수 앱 정보를 입력합니다. 테스팅 단계이므로 **테스트 사용자**에 본인 Gmail 계정을 명시적으로 등록해야 합니다.
4. **사용자 인증 정보** 탭으로 이동하여 `사용자 인증 정보 만들기` -> `OAuth 클라이언트 ID`를 선택합니다.
5. 애플리케이션 유형을 반드시 `데스크톱 앱(Desktop App)`으로 선택하고 생성을 완료합니다. (웹 애플리케이션 유형은 동작하지 않습니다.)
6. 발급된 클라이언트 오른쪽의 **다운로드(JSON 다운로드)** 버튼을 눌러 JSON 파일을 받습니다. 이 파일은 아래 **설정 페이지**에서 그대로 선택하면 되고, 직접 두고 싶다면 파일명을 `credentials.json`으로 바꿔 프로젝트 루트 폴더에 저장합니다.
   (형식은 [`credentials.example.json`](credentials.example.json) 더미 파일 참고. 이 파일은 비밀번호처럼 다루고 절대 공유·커밋하지 마세요.)

> 💡 GitHub Actions처럼 오래 자동 실행할 계획이라면 **OAuth 동의 화면 > 앱 게시 > 프로덕션으로 푸시**를 해 두세요. "테스트" 상태 앱의 리프레시 토큰은 **7일 후 만료**됩니다. 본인만 쓰는 경우 Google 검증은 필요 없고, 로그인 시 "확인되지 않은 앱" 경고만 표시됩니다.

---

## 🚀 로컬 설치 및 실행 방법 (Python / 개발자용)

### 1. 환경 설정 및 의존성 설치
Python **3.11 이상**이 필요합니다.
```bash
git clone https://github.com/<github-id>/sip-and-sort.git
cd sip-and-sort

# 가상환경 구축 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지를 개발자 모드로 설치 (sip-and-sort 명령 등록)
pip install -e ".[dev]"
```
의존성만 설치하려면 `pip install -r requirements.txt`, 명령어로만 쓰려면 `pipx install .` 도 가능합니다.

### 2. 설정 페이지(랜딩 페이지)에서 연결하기 🍓
```bash
sip-and-sort setup
```
브라우저에 **내 PC에서만 열리는 설정 페이지**(`http://127.0.0.1:8765/?t=...`)가 뜹니다. (자동으로 안 열리면 터미널에 출력된 주소를 그대로 여세요.)

| 단계 | 할 일 | 저장되는 파일 |
|---|---|---|
| **1. OAuth 클라이언트 등록** | 위에서 받은 JSON 파일 선택(또는 내용 붙여넣기) → `등록하기` | `credentials.json` |
| **2. 이름(활동명)과 답장 문구** | 이름(활동명), 검사 기간 입력, A/B/C 답장 문구 수정 → `저장하기` | `config.yaml` |
| **3. Gmail 연결** | `Gmail 연결하기` → 새 탭에서 Google 로그인 → 권한 허용 | `token.json` |
| **4. 미리 실행** | `미리 실행`으로 최근 메일이 어떻게 분류될지 확인 (라벨·초안 변경 없음) | — |

- "Google에서 확인하지 않은 앱" 화면이 나오면 본인이 만든 앱이므로 **고급 → (앱 이름)(으)로 이동**을 누르면 됩니다.
- 요청 권한은 `gmail.modify` 하나(메일 읽기·라벨·초안 저장)입니다. 이 범위는 Google 정책상 발송도 포함하지만 **코드는 발송 API를 호출하지 않습니다.**
- 설정 페이지는 `127.0.0.1`에만 열리고, 실행할 때마다 새로 만들어지는 접속 토큰(`?t=...`)이 있어야만 동작합니다. 등록한 `client_secret`은 화면에 다시 표시되지 않으며 외부로 전송되지 않습니다.

### 3. 설정 파일 직접 편집하기 (선택)
설정 페이지에서 저장하면 `config.yaml`이 자동 생성됩니다. 키워드·라벨 이름 등을 바꾸고 싶거나 처음부터 직접 만들고 싶다면 예시 파일을 복사해 편집하세요.
```bash
cp config.example.yaml config.yaml   # Windows: copy config.example.yaml config.yaml
```

| 키 | 설명 | 기본값 |
|---|---|---|
| `activity_name` | 답장 초안에 들어갈 이름(활동명) | `""` (비어 있으면 초안에 `[ ]`) |
| `lookback_hours` | 몇 시간 이내 메일을 검사할지 | `24` |
| `gmail_labels.*` | 분류/초안완료 라벨 이름 (`/`로 하위 라벨) | `협업제안/브랜드협찬` 등 |
| `keywords.*` | 협업 후보 키워드, 대량메일 제외 여부 | 위 목록 |
| `templates.*` | A/B/C 답장 문구 (`price_quote`, `decline_unpaid`, `gift_accept`) | 범용 기본 문구 |
| `my_addresses` | 포워딩/별칭으로 받는 본인 주소 (BCC 판별용) | `[]` |
| `extra_query`, `max_messages`, `rules` | Gmail 검색 추가 조건, 최대 검사 수, 분류 규칙 오버라이드 | — |

템플릿 자리표시자: `{activity_name}` 내 이름(활동명) · `{contact_name}` 상대 담당자 이름 · `{original_subject}` 받은 메일 제목.
값을 알 수 없는 자리는 초안에 `[ ]`로 남으니 Gmail에서 채운 뒤 보내세요. 단가·주소 같은 민감 정보를 템플릿에 넣는다면 `config.yaml`은 절대 공유하지 마세요(`.gitignore`에 포함됨).

### 4. 최초 실행 및 인증
```bash
sip-and-sort run --dry-run
```
설정 페이지에서 Gmail을 연결했다면 바로 실행됩니다. 연결하지 않았다면 이때 최초 1회 브라우저 창이 열리며 구글 로그인 플로우가 진행되고(터미널만 쓰고 싶다면 `sip-and-sort auth`), 인증이 완료되면 루트 경로에 `token.json`이 생성되어 이후부터는 재인증 없이 동작합니다.

### 5. 고급 실행 명령어 지원
```bash
# 실제 이메일을 조작하지 않고 콘솔에 분류 결과와 초안 미리보기만 출력
sip-and-sort run --dry-run

# 실제 실행: 라벨 부착 + 초안 저장 (발송 없음)
sip-and-sort run

# 기본 24시간 대신 최근 48시간 이내의 메일을 분석 (m/h/d/w 단위: 90m, 2d, 1w)
sip-and-sort run --since 48h

# 다른 위치의 설정 파일 사용 / 건수만 출력 / 초안 본문까지 출력
sip-and-sort run --config path/to/config.yaml
sip-and-sort run --summary-only
sip-and-sort run --show-drafts

# 원격 서버에서 로그인 URL만 출력
sip-and-sort auth --no-browser
```

출력 예시:
```text
============================================================
 협업메일 자동분류 결과 (DRY-RUN: 실제 변경 없음)
 검사 기간: 최근 24시간 | 검사한 스레드: 7개
============================================================
[분류별 건수]
  브랜드협찬: 2건
  유료광고  : 1건
  기타      : 1건
  (대량발송 제외 2건, 이미 처리되어 건너뜀 0건, 오류 0건)

[답장 초안 작성 예정] 3건
  - [A 단가안내] [유료광고] 김담당 <manager@brand-example.co.kr> | [협업 제안] 신제품 숏폼 광고 진행 문의
  - [B 무가협업 거절] [브랜드협찬] "코스메틱예시 PR" <pr@cosmetic-example.com> | 코스메틱예시 협찬 제안드립니다
  - [C 선물 수락] [브랜드협찬] 리빙예시 <hello@living-example.kr> | 리빙예시 브랜드에서 작은 선물을 보내드리고 싶어요

[직접 검토 필요] 1건
  - [기타] 박팀장 <park@agency-example.com> | 브랜드 협업 관련 미팅 요청
      사유: A/B/C 어느 상황에도 명확히 해당하지 않음

[대량발송으로 제외] 2건
  - 쇼핑몰예시 <news@shop-example.com> | 이번 주 브랜드 캠페인 소식  (List-Unsubscribe 헤더 (뉴스레터/대량발송))
  - 마케팅예시 <event@marketing-example.com> | (광고) 브랜드 위크 최대 70% 할인  (제목에 (광고) 표기 (광고성 대량메일))

※ 메일은 발송되지 않았습니다. Gmail 임시보관함에서 초안을 확인 후 직접 보내세요.
============================================================
```
종료 코드: `0` 정상 · `1` 일부 메일 처리 오류 · `2` 설정/인증 오류

---

## 🤖 GitHub Actions로 자동 스케줄링 운영하기

1. 로컬에서 최초 구동(`sip-and-sort setup` → `sip-and-sort run --dry-run`)에 성공하여 만들어진 `config.yaml`, `credentials.json`, `token.json` 세 파일의 텍스트 내용을 복사합니다.
2. 본인의 GitHub 저장소 설정(`Settings > Secrets and variables > Actions`)으로 이동합니다.
3. 아래의 이름으로 3개의 **Repository Secret**을 등록합니다:
   - `GMAIL_CONFIG_YAML`: 로컬 `config.yaml` 내용 붙여넣기
   - `GMAIL_CREDENTIALS_JSON`: 로컬 `credentials.json` 내용 붙여넣기
   - `GMAIL_TOKEN_JSON`: 로컬 `token.json` 내용 붙여넣기

   GitHub CLI를 쓴다면:
   ```bash
   gh secret set GMAIL_CONFIG_YAML < config.yaml
   gh secret set GMAIL_CREDENTIALS_JSON < credentials.json
   gh secret set GMAIL_TOKEN_JSON < token.json
   ```
4. 코드를 main 브랜치에 푸시하면 [`.github/workflows/run.yml`](.github/workflows/run.yml) 설정에 의해 **매 시간 정각**마다 최근 3시간 메일을 체크하고 정리합니다. (이미 처리한 메일은 건너뛰므로 기간이 겹쳐도 안전합니다.)
   - **Actions 탭 > sip-and-sort > Run workflow**로 수동 실행할 수 있으며, 수동 실행은 기본값이 dry-run입니다.
   - 일정은 `run.yml`의 `cron`(UTC 기준)에서 바꿀 수 있습니다. 시크릿이 없는 저장소에서는 아무 작업 없이 성공 처리됩니다.

> ⚠️ **공개(public) 저장소의 Actions 로그는 누구나 볼 수 있습니다.** 그래서 기본 워크플로는 `--summary-only`로 **건수만** 출력합니다. 가능하면 비공개(private) 저장소에서 운영하세요.
> 토큰이 만료·폐기되면(테스트 앱 7일 만료, 비밀번호 변경, 권한 해제 등) 로컬에서 `sip-and-sort auth`로 다시 로그인한 뒤 `GMAIL_TOKEN_JSON`을 새 내용으로 갱신하세요.

### 로컬 cron / launchd / 작업 스케줄러로 돌리기
```cron
# macOS / Linux (crontab -e): 매시간 정각, 최근 2시간 검사
0 * * * * cd /path/to/sip-and-sort && .venv/bin/sip-and-sort run --non-interactive --since 2h >> run.log 2>&1
```
- **macOS launchd**: `~/Library/LaunchAgents/`에 `ProgramArguments`를 `.venv/bin/sip-and-sort run --non-interactive --since 2h`, `StartInterval`을 `3600`으로 둔 plist를 만들고 `launchctl load`로 등록합니다.
- **Windows 작업 스케줄러**:
  ```powershell
  $exe = "C:\path\to\sip-and-sort\.venv\Scripts\sip-and-sort.exe"
  $action = New-ScheduledTaskAction -Execute $exe -Argument "run --non-interactive --since 2h" -WorkingDirectory "C:\path\to\sip-and-sort"
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
  Register-ScheduledTask -TaskName "sip-and-sort" -Action $action -Trigger $trigger
  ```

`--non-interactive`는 토큰이 만료됐을 때 브라우저를 띄우지 않고 오류(종료 코드 2)로 끝냅니다.

---

## 🧠 분류 규칙과 한계

- 모든 판단은 [`sip_and_sort/classifier.py`](sip_and_sort/classifier.py)의 키워드 규칙(`DEFAULT_RULES`)으로만 이뤄지며, 메일 내용은 Google 외 어떤 서버로도 전송되지 않습니다. `config.yaml`의 `rules:`로 바꿀 수 있습니다.
- 한국어 키워드는 띄어쓰기를 무시하고(`유료 광고` = `유료광고`), 영어는 단어 단위로 매칭합니다. `PR`, `PPL` 같은 짧은 대문자 약어는 대소문자를 구분합니다.
- 답장 메일 속 인용된 이전 대화(`>` 줄, "…님이 작성:", "On … wrote:")는 판단에서 제외합니다.
- 애매하면 초안을 만들지 않는 쪽으로 설계했습니다. 그래도 규칙 기반이라 완벽하지 않으니 **초안은 반드시 읽어 보고 보내세요.**
- 라벨이 붙은 스레드는 이후 새 답장이 와도 다시 처리하지 않습니다(중복 초안 방지).
- 다른 주소에서 Gmail로 포워딩 받는다면 `my_addresses`에 그 주소를 넣어야 BCC 대량메일로 오인하지 않습니다.
- 모든 Gmail API 호출은 레이트리밋(429, 403 rateLimitExceeded)과 일시적 서버 오류(5xx)에 지수 백오프로 재시도합니다.

---

## 🔒 보안 · 개인정보

- `credentials.json`, `token.json`, `config.yaml`은 `.gitignore`에 포함되어 커밋되지 않습니다. 절대 `git add -f`로 강제 추가하지 마세요.
- `token.json`이 유출되면 다른 사람이 내 메일을 읽을 수 있습니다. 의심되면 [Google 계정 > 서드파티 액세스](https://myaccount.google.com/permissions)에서 즉시 권한을 해제하세요.
- 프로그램은 메일을 발송하거나 삭제하지 않습니다. 하는 일은 검색·읽기, 라벨 생성/부착, 초안 생성뿐입니다.

---

## 📁 프로젝트 구조
```text
sip-and-sort/
├── sip_and_sort/
│   ├── main.py            # CLI: setup / auth / run
│   ├── setup_server.py    # 로컬 설정 랜딩 페이지 서버
│   ├── web/               # 랜딩 페이지 화면(setup.html) + 아이콘
│   ├── gmail_client.py    # 인증, 검색, 라벨, 초안 (send 없음), 재시도
│   ├── classifier.py      # 후보 판별, 대량메일 제외, 분류, A/B/C 판별
│   ├── templates.py       # 기본 답장 템플릿, 렌더링("[ ]" 처리)
│   ├── runner.py          # 1회 실행 흐름 + 요약 출력
│   ├── message.py         # Gmail 메시지 파싱
│   └── config.py          # config.yaml 로딩/검증
├── tests/                 # pytest + 샘플 메일 fixtures (Gmail API는 mock)
├── packaging/             # exe 빌드 설정 (PyInstaller)
├── .github/workflows/     # run.yml(매시간 실행), test.yml(CI), release.yml(exe 배포)
├── assets/            # 아이콘 (icon.png, icon.ico)
├── config.example.yaml
├── credentials.example.json
├── pyproject.toml / requirements*.txt
└── LICENSE / CONTRIBUTING.md
```

---

## 📦 exe 직접 빌드하기
```bash
pip install -r requirements-build.txt -e .
pyinstaller --noconfirm packaging/sip-and-sort.spec   # 결과물: dist/sip-and-sort.exe
```
`v`로 시작하는 태그를 push하면(`git tag v0.2.0` → `git push origin v0.2.0`) [`release.yml`](.github/workflows/release.yml)이 GitHub에서 exe를 빌드해 Releases에 자동으로 올립니다.

---

## 🤝 기여 안내
버그 제보나 기능 제안은 언제나 환영합니다! Issue를 발행하거나 Pull Request를 제출해 주세요. 코드 수정 후에는 `pytest` 명령어를 통해 분류 규칙이 오작동하지 않는지 반드시 확인해 주시기 바랍니다. (테스트는 Gmail API를 mock으로 대체하므로 Google 계정 없이 실행됩니다.)
```bash
pytest
```
자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

---

## 🌏 English summary
**sip-and-sort** scans your Gmail for collaboration / sponsorship / ad proposals (Korean & English keywords), skips newsletters and bulk mail, labels each as *Brand sponsorship / Paid ad / Other*, and — only when the case is clear — saves a reply **draft** (price inquiry → quote, unpaid product-for-content → polite decline, no-strings gift → accept). **It never sends email.**
Windows users can simply download `sip-and-sort.exe` from Releases and double-click it. No API keys ship with this repo or the exe: create your own Google Cloud OAuth client (Desktop app), run `sip-and-sort setup` to open a local-only setup page, register `credentials.json`, enter your name (used to sign drafts), and connect Gmail. Then `sip-and-sort run --dry-run` → `sip-and-sort run`.

---

## 📄 라이선스
[MIT License](LICENSE) — 자유롭게 사용·수정·배포할 수 있으며, 소프트웨어는 "있는 그대로" 제공됩니다. 초안 내용과 실제 발송에 대한 책임은 사용자에게 있습니다.
