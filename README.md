<p align="center"><img src="assets/icon.png" alt="sip-and-sort icon" width="160"></p>

<h1 align="center">🍓 sip-and-sort</h1>

<p align="center">
  <a href="https://github.com/jmni817/sip-and-sort/releases/latest"><img src="https://img.shields.io/github/downloads/jmni817/sip-and-sort/total?label=%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C&color=D36279" alt="총 다운로드 수"></a>
  <a href="https://github.com/jmni817/sip-and-sort/releases/latest"><img src="https://img.shields.io/github/v/release/jmni817/sip-and-sort?label=%EC%B5%9C%EC%8B%A0%20%EB%B2%84%EC%A0%84&color=EC5564" alt="최신 버전"></a>
</p>

<p align="center">
  <b>"딸기우유 한 모금 마시는 사이에, 쌓여있던 협업 메일 분류부터 답장 초안 작성까지 한번에 끝!"</b><br>
  A smart & aesthetic open-source Gmail sorter for creators.
</p>

<p align="center">
  <a href="https://github.com/jmni817/sip-and-sort/releases/latest"><b>⬇️ Windows용 exe 다운로드</b></a>
</p>

---

> [!IMPORTANT]
> **메일을 절대 자동으로 보내지 않습니다.**
> 라벨을 붙이고, Gmail 임시보관함에 답장 **초안**만 저장합니다.
> 최종 확인과 발송은 사용자가 직접 합니다.

> [!NOTE]
> **이 저장소와 exe에는 어떤 API 키·토큰도 들어 있지 않습니다.**
> 각자 본인의 Google 키(`credentials.json`)를 등록해서 본인 Gmail에 연결합니다.

<br>

## 📚 목차

1. [무엇을 해주나요?](#-무엇을-해주나요)
2. [AI로 키워드의 사각지대 없애기](#-ai로-키워드의-사각지대-없애기-선택-기능)
3. [시작하기 (Windows exe)](#-시작하기-windows-exe)
4. [Google Cloud 설정 (최초 1회)](#-google-cloud-설정-최초-1회)
5. [설정 파일](#-설정-파일-configyaml)
6. [개발자용: Python으로 실행하기](#-개발자용-python으로-실행하기)
7. [자동 실행 (GitHub Actions · 작업 스케줄러)](#-자동-실행)
8. [분류 규칙과 한계](#-분류-규칙과-한계)
9. [보안 · 개인정보](#-보안--개인정보)
10. [프로젝트 구조 · 빌드 · 기여](#-프로젝트-구조)

<br>

---

## ✨ 무엇을 해주나요?

크리에이터 메일함에 쌓이는 **협업·협찬·광고 제안 메일**을 찾아 정리하고, 답장 초안까지 만들어 둡니다.

### ① 협업 메일 찾기

최근 N시간(기본 24시간) 안에 받은 메일 중 협업 키워드가 들어간 메일을 찾습니다.

- 한국어: `협업` `제휴` `협찬` `광고` `PPL` `브랜드` `캠페인` `서포터즈` `앰버서더`
- 영어: `collaboration` `sponsorship` `partnership` `campaign` `PR` `brand deal`

뉴스레터·대량 마케팅 메일은 걸러 냅니다.
(수신거부 헤더, 제목의 `(광고)` 표기, `noreply` 발신, BCC 발송 등으로 판별)

### ② 유형별로 라벨 붙이기

**브랜드협찬 / 유료광고 / 기타** 중 하나로 분류해서 Gmail 라벨을 붙입니다.
라벨이 없으면 자동으로 만듭니다.

### ③ 상황이 명확할 때만 답장 초안 저장

| 상황 | 이런 메일 | 저장되는 초안 |
|---|---|---|
| **A** 단가·비용 문의 | "단가", "견적", "rate card" | 단가 안내 |
| **B** 무가 협업 | "제품만 제공" + "업로드·리뷰 필수" | 정중한 거절 |
| **C** 순수 선물 | "선물 보내드리고 싶어요" + "업로드 의무 없음" | 감사히 수락 |
| 그 외 · 여러 상황이 겹침 | — | 초안 없이 **직접 검토 필요** |

초안의 인사말과 서명에는 설정에서 입력한 **이름(활동명)** 이 들어갑니다.
초안을 만든 메일에는 `답장초안완료` 라벨이 하나 더 붙습니다.

### ④ 결과 요약

분류별 건수와 메일 목록을 보여 줍니다.
이미 라벨이 붙은 메일은 다시 처리하지 않아서, 여러 번 돌려도 초안이 중복되지 않습니다.

<br>

---

## 🤖 AI로 키워드의 사각지대 없애기 (선택 기능)

### 키워드만으로는 놓치는 메일이 있었습니다

> 제품 수령 후 7일 이내 피드 또는 릴스 콘텐츠 1건을 업로드해 주시면 됩니다.

이 메일은 **무가 협찬**입니다.
그런데 '무가', '단가', '협찬' 같은 단어가 하나도 없어서 키워드 규칙이 놓쳤습니다.

규칙을 더 늘리는 방법도 있지만, 그러면 원고료를 따로 안내하는 **유료 제안까지 무가로 오판**할 수 있습니다.
이런 건 문맥을 읽어야 하는 일이라 **LLM에게 맡겼습니다.**

### 규칙이 먼저, AI는 규칙이 못 정한 메일만

모든 메일을 AI에게 보내지 않습니다.
**키워드 규칙이 먼저 판단하고, 판단하지 못한 메일만** AI에게 묻습니다.

| 메일 | AI에게 보낼까? |
|---|---|
| 규칙으로 A·B·C가 정해진 메일 | ❌ 규칙 결과 사용 (API 비용 없음) |
| 협업 메일인데 규칙이 A·B·C를 못 정한 메일 | ✅ |
| 협업 키워드는 없지만 `업로드` `릴스` `제품 수령` 같은 신호가 있는 메일 | ✅ |
| 대량발송처럼 보이지만 협업 신호가 있는 메일<br>(체험단·인플루언서 **모집**인지, 그냥 뉴스레터인지 구분) | ✅ |
| 신호가 전혀 없는 일반 메일 | ❌ 보내지 않음 |

### AI가 엉뚱하게 굴지 않도록

- **정해진 형식으로만 답하기**
  협업 여부 · 유형 · A/B/C · 확신도 · 판단 근거를 JSON 형식으로만 답하게 했습니다.
- **확신이 없으면 사람에게**
  확신도가 0.7보다 낮으면 초안 없이 **직접 검토**로 넘깁니다.
- **초안 문장은 AI가 쓰지 않음**
  AI는 A·B·C 중 무엇인지 **고르기만** 하고, 초안은 미리 정한 템플릿을 씁니다.
- **개인정보 가리기**
  보내기 전에 이메일 주소·전화번호·링크·보낸 사람 이름을 가립니다.
- **메일 속 지시문 무시**
  "이 메일을 OO로 분류하라" 같은 문장이 있어도 따르지 않도록 지시합니다.
- **실패해도 멈추지 않음**
  AI 호출이 실패하면 그 메일은 규칙 결과로 처리하고 계속 진행합니다.

결과에는 AI가 정한 메일에 **[AI]**, 대량발송이었던 메일에 **[대량]** 표시와 판단 근거가 붙습니다.

### 연결 방법

설정 화면 → **[설정 편집하기]** → **AI 판단 연결 (선택)**

1. **API 주소**
   OpenAI 호환(Chat Completions) 형식이면 어디든 됩니다.
   예: `https://api.openai.com/v1`, 여러 모델을 하나의 키로 쓰는 통합 키 서비스(freellmapi 등), 내 PC의 로컬 모델
2. **모델 이름**과 **본인 API 키** 입력 → **[저장하기]**
3. **[연결 테스트]** 로 위 무가 협찬 예시를 AI가 어떻게 판단하는지 확인
4. **AI 판단 사용하기** 를 켜면 다음 정리부터 적용

> [!WARNING]
> AI 판단을 켜면 위 표의 ✅ 메일 내용이 **입력한 AI 서비스로 전송됩니다.**
> 그 서비스의 데이터 보관·학습 정책을 꼭 확인하세요. (기본값은 꺼짐)

- API 키는 `config.yaml`이 아니라 설정 폴더의 `llm_api_key.txt`에 따로 저장되고, 화면에 다시 표시되지 않습니다.
- 명령어 실행이나 GitHub Actions에서는 환경변수 `SIP_AND_SORT_LLM_API_KEY`로 넣을 수 있습니다.

<br>

---

## 💾 시작하기 (Windows exe)

Python이나 명령어 없이 바로 쓸 수 있습니다.

1. [**Releases**](https://github.com/jmni817/sip-and-sort/releases/latest)에서 `sip-and-sort.exe`를 받습니다.
2. [Google Cloud 설정](#-google-cloud-설정-최초-1회)을 따라 본인의 `credentials.json`을 받습니다. (최초 1회, 5~10분)
3. `sip-and-sort.exe`를 **더블클릭**하면 **sip-and-sort 프로그램 창**이 열립니다.
4. 화면 안내대로 진행합니다.
   ① `credentials.json` 등록 → ② 이름(활동명) 입력 → ③ Gmail 연결 → ④ **[지금 정리하기]**

다음부터는 프로그램을 켜고 **[지금 정리하기]** 만 누르면 됩니다.
다 쓰면 창을 닫거나 [종료]를 누르면 끝납니다.

### 알아두면 좋은 기능

- **⏰ 자동 정리**
  [자동 정리] 스위치를 켜고 간격(30분 · 1시간 · 2시간 · 3시간)을 고르면, 프로그램을 켜 둔 동안 알아서 정리합니다.
  끝나면 "정리 완료! 답장 초안 N건" 알림이 잠깐 떴다 사라집니다.

- **🔔 새 버전 안내** (v0.1.11부터)
  켤 때 새 버전이 있으면 팝업으로 알려 줍니다.
  [다운로드하기] → 기존 exe 삭제 안내 → [확인]을 누르면 새 버전을 받아 바로 실행합니다.
  새 버전이 열리면 예전 exe 파일은 지워 주세요.

- **🔐 Google 로그인은 평소 브라우저에서**
  Google이 프로그램 안 창에서의 로그인을 막기 때문에, [Gmail 연결하기]를 누르면 그때만 브라우저가 열립니다.
  로그인을 마치면 프로그램 창이 자동으로 '연결됨'으로 바뀝니다.

- **💾 설정이 저장되는 곳**
  `%APPDATA%\sip-and-sort\` (키, 로그인 정보, 설정)
  exe를 어디로 옮기거나 새 버전으로 바꿔도 그대로 이어집니다. 이 폴더를 지우면 초기화됩니다.

### 이럴 땐 이렇게

- **"Windows의 PC 보호" 경고가 떠요**
  서명하지 않은 개인 프로젝트라서 나오는 안내입니다. **추가 정보 → 실행**을 누르세요.
  걱정되면 이 저장소의 코드를 직접 확인하거나 [Python으로 실행](#-개발자용-python으로-실행하기)해도 됩니다.

- **프로그램 창이 안 뜨고 브라우저로 열려요**
  창을 띄우는 화면 엔진(Microsoft Edge WebView2)이 시작하지 못한 경우입니다. 기능은 그대로 쓸 수 있습니다.
  PC를 **다시 시작**(시스템 종료가 아니라 [다시 시작])한 뒤 실행해 보세요.
  실행 기록은 `%APPDATA%\sip-and-sort\sip-and-sort.log`에 남습니다.

<br>

---

## 🔧 Google Cloud 설정 (최초 1회)

sip-and-sort는 각자 **본인 Google Cloud 프로젝트에서 만든 키**로 본인 Gmail에 접속합니다.
무료이고, 결제 정보는 필요 없습니다.

> [!TIP]
> Google Cloud 콘솔은 자주 개편되어 메뉴 이름이 조금 다를 수 있습니다.
> 최신 화면은 왼쪽 메뉴 **Google 인증 플랫폼**(브랜딩 · 대상 · 클라이언트),
> 예전 화면은 **API 및 서비스 → OAuth 동의 화면 / 사용자 인증 정보**를 보면 됩니다.

### STEP 1. 프로젝트 만들기

1. [Google Cloud Console](https://console.cloud.google.com/)에 **연결할 Gmail 계정**으로 로그인합니다.
2. 왼쪽 위 **프로젝트 선택** → **[새 프로젝트]**
3. 이름(예: `sip-and-sort`)을 입력하고 **[만들기]**
4. 왼쪽 위에 **방금 만든 프로젝트가 선택되어 있는지** 꼭 확인합니다.

### STEP 2. Gmail API 켜기

1. 위쪽 검색창에 `Gmail API` 입력 → **Gmail API** 선택
2. **[사용]** 클릭 → "API 사용 설정됨"이 나오면 완료

### STEP 3. 앱 정보 입력

1. 왼쪽 메뉴 **Google 인증 플랫폼** → **[시작하기]**
2. 아래처럼 입력하고 **[만들기]**

| 항목 | 입력할 값 |
|---|---|
| 앱 이름 | 아무 이름 (예: `sip and sort`) |
| 사용자 지원 이메일 | 본인 Gmail |
| 대상 | **외부(External)** |
| 연락처 정보 | 본인 이메일 |

> [!CAUTION]
> **앱 로고는 올리지 마세요.**
> 로고가 있으면 Google 인증 심사를 받아야 앱을 게시할 수 있고, Gmail 권한을 쓰는 앱의 심사는 개인이 통과하기 어렵습니다.
> 홈페이지·개인정보처리방침·승인된 도메인도 비워 두면 됩니다.

### STEP 4. 테스트 사용자에 내 Gmail 추가 ⭐ 꼭 필요

새 앱은 **"테스트" 상태**라서 등록한 계정만 로그인할 수 있습니다.
빠뜨리면 로그인할 때 **"액세스 차단됨 … 403 오류: access_denied"** 가 나옵니다.

1. **Google 인증 플랫폼 → 대상**
2. **테스트 사용자 → [+ Add users]**
3. 연결할 **Gmail 주소**를 입력하고 저장 (프로젝트를 만든 계정이어도 직접 추가)

### STEP 5. 데스크톱 앱 키 만들고 JSON 받기

1. **Google 인증 플랫폼 → 클라이언트 → [+ 클라이언트 만들기]**
2. 애플리케이션 유형: 반드시 **데스크톱 앱**
3. 이름 입력 → **[만들기]**
4. 완료 창에서 **[JSON 다운로드]**

> [!WARNING]
> 콘솔 버전에 따라 **보안 비밀번호는 이 창에서만** 받을 수 있습니다. 창을 닫기 전에 꼭 받으세요.
> 이 파일은 **비밀번호처럼** 다루고, 다른 사람에게 보내거나 GitHub에 올리지 마세요.

### STEP 6. sip-and-sort에서 연결

1. sip-and-sort를 실행합니다.
2. **1단계**에서 받은 JSON 파일 선택 → [등록하기]
3. **3단계 [Gmail 연결하기]** → 브라우저에서 STEP 4에 추가한 Gmail로 로그인
4. **"Google에서 확인하지 않은 앱"** 이 나오면 **[고급] → [(앱 이름)(으)로 이동]**
5. **[계속]** → 화면이 **연결됨**으로 바뀌면 완료

### STEP 7. (권장) 7일마다 다시 로그인하지 않게 하기

"테스트" 상태의 로그인은 **7일 뒤 만료**됩니다.

1. **Google 인증 플랫폼 → 대상 → [앱 게시]**
   - "인증이 필요하다"는 안내가 나와도 **신청하지 않아도 됩니다.** (사용자 100명까지 사용 가능)
2. sip-and-sort에서 **[연결 해제] → [Gmail 연결하기]** 를 **한 번 다시** 합니다.

### 자주 나오는 문제

| 증상 | 해결 |
|---|---|
| **403 오류: access_denied** | STEP 4 — 테스트 사용자에 Gmail 추가 |
| "웹 애플리케이션 유형의 OAuth 클라이언트입니다" | STEP 5 — **데스크톱 앱**으로 다시 만들기 |
| "client_id 값이 비어 있거나 예시 값입니다" | 예시 파일이 아니라 STEP 5에서 받은 파일 등록 |
| Google 로그인 창이 안 열림 | 3단계의 **[Google 로그인 열기]** 버튼 사용 |
| "Gmail 로그인이 만료되었거나 권한이 해제되었습니다" | 3단계에서 다시 연결 (STEP 7 참고) |
| "Gmail API has not been used in project …" | STEP 2 — 선택된 프로젝트에서 Gmail API **[사용]** |
| 앱 게시 시 "브랜딩 페이지 구성 완료 필요" | STEP 3 필수 항목 입력, **앱 로고 삭제** 후 저장 |

<br>

---

## 🧩 설정 파일 (config.yaml)

대부분은 설정 화면에서 바꿀 수 있습니다.
키워드나 라벨 이름처럼 더 세밀하게 바꾸고 싶을 때만 `config.yaml`을 직접 편집하세요.
(예시: [`config.example.yaml`](config.example.yaml))

| 키 | 설명 | 기본값 |
|---|---|---|
| `activity_name` | 답장 초안에 들어갈 이름(활동명) | 비어 있으면 초안에 `[ ]` |
| `lookback_hours` | 몇 시간 이내 메일을 검사할지 | `24` |
| `gmail_labels.*` | 분류·초안완료 라벨 이름 (`/`로 하위 라벨) | `협업제안/브랜드협찬` 등 |
| `keywords.*` | 협업 후보 키워드, 대량메일 제외 여부 | 위 목록 |
| `templates.*` | A/B/C 답장 문구 | 범용 기본 문구 |
| `llm.*` | AI 판단 사용 여부, API 주소, 모델, 확신도 기준 | 꺼짐 |
| `auto_run.*` | 자동 정리 사용 여부와 간격 | 꺼짐, 60분 |
| `my_addresses` | 포워딩·별칭으로 받는 본인 주소 | `[]` |

**답장 문구에 쓸 수 있는 자리표시자**

- `{activity_name}` — 내 이름(활동명)
- `{contact_name}` — 상대 담당자 이름
- `{original_subject}` — 받은 메일 제목

값을 알 수 없는 자리는 초안에 `[ ]`로 남으니, Gmail에서 채운 뒤 보내세요.

<br>

---

## 💻 개발자용: Python으로 실행하기

Python **3.11 이상**이 필요합니다.

```bash
git clone https://github.com/jmni817/sip-and-sort.git
cd sip-and-sort
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # 프로그램 창까지 쓰려면 ".[dev,desktop]"
```

### 자주 쓰는 명령어

```bash
sip-and-sort setup               # 설정 화면 (브라우저로 열기)
sip-and-sort setup --window      # 설정 화면 (프로그램 창으로 열기)

sip-and-sort run --dry-run       # 미리 보기: 아무것도 바꾸지 않고 결과만 출력
sip-and-sort run                 # 실제 실행: 라벨 + 초안 저장 (발송 없음)
sip-and-sort run --since 48h     # 최근 48시간 (90m, 2d, 1w 도 가능)
sip-and-sort run --summary-only  # 건수만 출력

sip-and-sort auth --no-browser   # 원격 서버: 로그인 주소만 출력
```

### 출력 예시

```text
============================================================
 협업메일 자동분류 결과 (DRY-RUN: 실제 변경 없음)
 검사 기간: 최근 24시간 | 검사한 스레드: 8개
============================================================
[분류별 건수]
  브랜드협찬: 3건
  유료광고  : 1건
  기타      : 1건
  (대량발송 제외 2건, 이미 처리되어 건너뜀 0건, 오류 0건)
  (AI 판단 요청 4건 → AI가 결정 1건, AI 오류 0건)

[답장 초안 작성 예정] 4건
  - [A 단가안내] [유료광고] 김담당 <manager@brand-example.co.kr> | [협업 제안] 신제품 숏폼 광고 진행 문의
  - [B 무가협업 거절] [브랜드협찬] "코스메틱예시 PR" <pr@cosmetic-example.com> | 코스메틱예시 협찬 제안드립니다
  - [B 무가협업 거절] [브랜드협찬] [AI] 마케팅팀 <hello@lip-example.kr> | 신제품 소개드립니다
      AI 판단 (확신도 0.92): 비용 언급 없이 제품 수령 후 릴스 업로드 요구
  - [C 선물 수락] [브랜드협찬] 리빙예시 <hello@living-example.kr> | 리빙예시 브랜드에서 작은 선물을 보내드리고 싶어요

[직접 검토 필요] 1건
  - [기타] 박팀장 <park@agency-example.com> | 브랜드 협업 관련 미팅 요청
      사유: A/B/C 어느 상황에도 명확히 해당하지 않음; AI도 확신하지 못함 (확신도 0.40): 미팅 요청만 있음

[대량발송으로 제외] 2건
  - 쇼핑몰예시 <news@shop-example.com> | 이번 주 브랜드 캠페인 소식  (List-Unsubscribe 헤더 (뉴스레터/대량발송) · AI: 협업 아님 (쇼핑몰 뉴스레터))
  - 마케팅예시 <event@marketing-example.com> | (광고) 브랜드 위크 최대 70% 할인  (제목에 (광고) 표기 (광고성 대량메일) · AI: 협업 아님 (할인 광고))

※ 메일은 발송되지 않았습니다. Gmail 임시보관함에서 초안을 확인 후 직접 보내세요.
============================================================
```

종료 코드: `0` 정상 · `1` 일부 메일 처리 오류 · `2` 설정·인증 오류

<br>

---

## ⏰ 자동 실행

프로그램을 켜 둔 동안 정리하려면 [자동 정리 스위치](#알아두면-좋은-기능)로 충분합니다.
**프로그램을 꺼 둬도** 돌리고 싶을 때 아래 방법을 쓰세요.

### Windows 작업 스케줄러

PowerShell에서 경로만 바꿔 실행하면, 1시간마다 최근 2시간 메일을 정리합니다.

```powershell
$exe = "C:\path\to\sip-and-sort.exe"
$action = New-ScheduledTaskAction -Execute $exe -Argument "run --non-interactive --since 2h"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "sip-and-sort" -Action $action -Trigger $trigger
```

`--non-interactive`: 로그인이 만료됐을 때 브라우저를 띄우지 않고 오류로 끝냅니다.

### macOS / Linux cron

```cron
0 * * * * cd /path/to/sip-and-sort && .venv/bin/sip-and-sort run --non-interactive --since 2h >> run.log 2>&1
```

### GitHub Actions (PC를 꺼 둬도 실행)

1. 로컬에서 만들어진 `config.yaml`, `credentials.json`, `token.json`의 내용을 준비합니다.
2. 저장소 **Settings → Secrets and variables → Actions** 에 시크릿 3개를 등록합니다.
   - `GMAIL_CONFIG_YAML` ← `config.yaml`
   - `GMAIL_CREDENTIALS_JSON` ← `credentials.json`
   - `GMAIL_TOKEN_JSON` ← `token.json`
3. [`run.yml`](.github/workflows/run.yml)이 **매시간 정각**에 최근 3시간 메일을 정리합니다.
   Actions 탭에서 수동 실행도 됩니다. (수동 실행은 기본값이 미리 보기)

> [!WARNING]
> **공개 저장소의 Actions 로그는 누구나 볼 수 있습니다.**
> 그래서 기본 워크플로는 건수만 출력합니다. 가능하면 비공개 저장소에서 운영하세요.

<br>

---

## 🧠 분류 규칙과 한계

- 기본 판단은 [`classifier.py`](sip_and_sort/classifier.py)의 **키워드 규칙**으로 합니다.
  AI 판단을 켠 경우에만, 규칙이 판단하지 못한 메일이 AI에게 전송됩니다.
- 한국어 키워드는 띄어쓰기를 무시합니다. (`유료 광고` = `유료광고`)
  영어는 단어 단위로 찾고, `PR` `PPL` 같은 짧은 대문자 약어는 대소문자를 구분합니다.
- 답장 메일 속 인용된 이전 대화(`>` 줄, "…님이 작성:")는 판단에서 뺍니다.
- EUC-KR 같은 옛 한국어 인코딩 메일도 깨지지 않게 읽습니다.
- **애매하면 초안을 만들지 않는 쪽**으로 설계했습니다.
  그래도 완벽하지 않으니 **초안은 반드시 읽어 보고 보내세요.**

**알아둘 점**

- 라벨이 붙은 메일은 나중에 새 답장이 와도 다시 처리하지 않습니다. (중복 초안 방지)
- 다른 주소에서 포워딩 받는다면 `my_addresses`에 그 주소를 넣어야 BCC 대량메일로 오인하지 않습니다.
- Gmail API 요청 제한이나 일시 오류는 자동으로 다시 시도합니다.

<br>

---

## 🔒 보안 · 개인정보

- **하는 일은 검색·읽기, 라벨 붙이기, 초안 저장뿐입니다.** 메일을 보내거나 지우지 않습니다.
- **설정 화면은 내 PC 안에서만** 동작하고, 실행할 때마다 바뀌는 접속 토큰이 있어야 열립니다.
- **외부로 나가는 정보**
  - Google: Gmail 연결과 메일 처리
  - AI 서비스: AI 판단을 켠 경우, 가림 처리한 일부 메일 내용
  - GitHub: 새 버전 확인 (IP 주소 정도만 전달, 메일·설정 정보는 보내지 않음)
- `credentials.json` `token.json` `config.yaml` `llm_api_key.txt`는 `.gitignore`에 들어 있어 커밋되지 않습니다.
- `token.json`이 유출되면 다른 사람이 내 메일을 읽을 수 있습니다.
  의심되면 [Google 계정 → 서드파티 액세스](https://myaccount.google.com/permissions)에서 바로 권한을 해제하세요.

<br>

---

## 📁 프로젝트 구조

```text
sip-and-sort/
├── sip_and_sort/
│   ├── main.py            # 실행 진입점: setup / auth / run
│   ├── setup_server.py    # 설정 화면 서버, 프로그램 창, 자동 정리, 새 버전 안내
│   ├── web/               # 설정 화면(setup.html) + 아이콘
│   ├── runner.py          # 1회 정리 흐름 + 결과 요약
│   ├── classifier.py      # 협업 메일 판별, 대량메일 판별, 분류, A/B/C 판단
│   ├── llm.py             # AI 판단 (OpenAI 호환 API, 개인정보 가림)
│   ├── templates.py       # 답장 초안 템플릿
│   ├── gmail_client.py    # Gmail 인증·검색·라벨·초안 (발송 기능 없음)
│   ├── message.py         # 메일 읽기 (인코딩 처리)
│   ├── updates.py         # 새 버전 확인·다운로드
│   └── config.py          # 설정 파일 읽기·검증
├── tests/                 # 자동 테스트 (Gmail·AI·GitHub는 가짜 응답)
├── packaging/             # exe 빌드 설정
├── .github/workflows/     # 테스트, exe 배포, 정기 실행
├── assets/                # 아이콘
├── CHANGELOG.md           # 버전별 변경 기록
└── config.example.yaml / credentials.example.json
```

### exe 직접 빌드하기

```bash
pip install -r requirements-build.txt -e .
pyinstaller --noconfirm packaging/sip-and-sort.spec   # → dist/sip-and-sort.exe
```

`v`로 시작하는 태그를 올리면 GitHub가 exe를 빌드해서 Releases에 올리고,
[`CHANGELOG.md`](CHANGELOG.md)의 해당 버전 내용을 릴리스 설명으로 넣습니다.

### 🤝 기여하기

버그 제보와 기능 제안은 언제나 환영합니다! Issue나 Pull Request로 남겨 주세요.
코드를 고친 뒤에는 `pytest`로 테스트가 통과하는지 확인해 주세요. (Google 계정 없이 실행됩니다)
자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

<br>

---

## 🌏 English summary

**sip-and-sort** finds collaboration / sponsorship / ad proposals in a creator's Gmail, labels them (*Brand sponsorship / Paid ad / Other*), and saves a reply **draft** only when the case is clear. **It never sends email.**

Keyword rules decide first. Optionally, only the mails the rules can't decide (e.g. an unpaid offer that never says "unpaid") are sent to any OpenAI-compatible LLM with your own key — personal details masked, low-confidence answers left for human review, and template-based drafts only.

Download `sip-and-sort.exe` from Releases and double-click it. No API keys ship with this repo: create your own Google Cloud OAuth client (Desktop app) and connect it in the app.

<br>

---

## 📄 라이선스

[MIT License](LICENSE)
자유롭게 사용·수정·배포할 수 있으며, 소프트웨어는 "있는 그대로" 제공됩니다.
초안 내용과 실제 발송에 대한 책임은 사용자에게 있습니다.
