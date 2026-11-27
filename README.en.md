<p align="center"><img src="assets/icon.png" alt="sip-and-sort icon" width="160"></p>

<h1 align="center">🍓 sip-and-sort</h1>

<p align="center">
  <a href="README.md">한국어</a> · <b>English</b>
</p>

<p align="center">
  <a href="https://github.com/eight-studio/sip-and-sort/releases/latest"><img src="https://img.shields.io/github/downloads/eight-studio/sip-and-sort/total?label=downloads&color=D36279" alt="Total downloads"></a>
  <a href="https://github.com/eight-studio/sip-and-sort/releases/latest"><img src="https://img.shields.io/github/v/release/eight-studio/sip-and-sort?label=latest&color=EC5564" alt="Latest version"></a>
</p>

<p align="center">
  <b>"In the time it takes to sip a strawberry milk, your pile of collab emails is sorted and the reply drafts are written."</b><br>
  A smart & aesthetic open-source Gmail sorter for creators.
</p>

<p align="center">
  <a href="https://github.com/eight-studio/sip-and-sort/releases/latest"><b>🍓 Download the Windows exe</b></a>
</p>

---

> <img src="assets/labels/en/important.svg" alt="Important" height="36">
>
> **It never sends email automatically.**
> It only adds labels and saves reply **drafts** to your Gmail Drafts folder.
> You review and send every reply yourself.

> <img src="assets/labels/en/note.svg" alt="Note" height="36">
>
> **This repository and the exe contain no API keys or tokens.**
> Everyone registers their own Google key (`credentials.json`) and connects their own Gmail.

> <img src="assets/labels/en/tip.svg" alt="Tip" height="36">
>
> sip-and-sort is built for **Korean-speaking creators**.
> The app screens, keyword rules, label names and default reply drafts are in Korean.
> English collab keywords are detected too, and you can rewrite the reply drafts in any language.

<br>

## 🎀 Contents

1. [What does it do?](#-what-does-it-do)
2. [Covering keyword blind spots with AI (optional)](#-covering-keyword-blind-spots-with-ai-optional)
3. [Getting started (Windows exe)](#-getting-started-windows-exe)
4. [Google Cloud setup (one time)](#-google-cloud-setup-one-time)
5. [Config file](#-config-file-configyaml)
6. [For developers: run with Python](#-for-developers-run-with-python)
7. [Scheduled runs (GitHub Actions · Task Scheduler)](#-scheduled-runs)
8. [Rules and limits](#-rules-and-limits)
9. [Security · privacy](#-security--privacy)
10. [Project structure · build · contributing](#-project-structure)

<br>

---

## 🍓 What does it do?

It finds the **collaboration, sponsorship and ad proposals** piling up in a creator's inbox, sorts them, and prepares reply drafts.

### ① Find collab emails

It looks for collab keywords in emails received in the last N hours (24 by default).

- Korean: `협업` (collaboration) `제휴` (partnership) `협찬` (sponsorship) `광고` (ad) `PPL` `브랜드` (brand) `캠페인` (campaign) `서포터즈` (supporters) `앰버서더` (ambassador)
- English: `collaboration` `sponsorship` `partnership` `campaign` `PR` `brand deal`

Newsletters and bulk marketing emails are filtered out.
(Detected by unsubscribe headers, an `(광고)` "(ad)" tag in the subject, `noreply` senders, BCC sends and so on.)

### ② Label by type

Each email is sorted into **Brand sponsorship / Paid ad / Other** and gets a Gmail label.
Missing labels are created automatically.

### ③ Save a reply draft only when the case is clear

| Case | Emails like | Draft saved |
|---|---|---|
| **A** Rate inquiry | "rate", "quote", "rate card" | Rate information |
| **B** Unpaid collab | "product only" + "upload / review required" | Polite decline |
| **C** Pure gift | "we'd like to send you a gift" + "no obligation to post" | Thankful acceptance |
| **D** Group buy | "공동구매" (group buy), with or without a space — takes priority over other cases | Polite decline |
| Anything else · several cases at once | — | No draft, **needs manual review** |

Drafts are signed with the **name (creator name)** you entered in the settings.
Emails that got a draft also get a `답장초안완료` ("draft done") label.

### ④ Summary

It shows counts per type and the list of emails.
Already-labeled emails are skipped, so running it again never creates duplicate drafts.

<br>

---

## 💗 Covering keyword blind spots with AI (optional)

### Some emails slip past keywords

> Please upload one feed post or reel within 7 days of receiving the product.

This is an **unpaid sponsorship**.
But it contains none of the words "unpaid", "rate" or "sponsorship", so the keyword rules missed it.

Adding more rules is possible, but then **paid offers that mention the fee separately could be misread as unpaid**.
This takes reading the context, so it is **handed to an LLM**.

### Rules first, AI only for what the rules can't decide

Not every email goes to the AI.
**The keyword rules decide first, and only the emails they can't decide** are sent to the AI.

| Email | Sent to the AI? |
|---|---|
| Rules already decided A/B/C/D | ❌ Rule result used (no API cost) |
| Collab email, but the rules couldn't pick A/B/C/D | ⭕ |
| No collab keywords, but signals such as `업로드` (upload), `릴스` (reels), `제품 수령` (product received) | ⭕ |
| Looks like a bulk send but has collab signals<br>(tells a creator **recruitment** apart from a plain newsletter) | ⭕ |
| Ordinary email with no signals at all | ❌ Not sent |

### Keeping the AI in line

- **Fixed answer format**
  It must answer only in JSON: collab or not · type · A/B/C/D · confidence · reason.
- **Unsure → a human decides**
  Below a confidence of 0.7, no draft is made and the email goes to **manual review**.
- **The AI never writes the draft**
  It only **picks** the case; the draft comes from your fixed template.
- **Personal details masked**
  Email addresses, phone numbers, links and the sender's name are masked before sending.
- **Instructions inside emails are ignored**
  It is told not to follow lines like "classify this email as X".
- **Failures don't stop the run**
  If an AI call fails, that email falls back to the rule result and the run continues.

AI-decided emails are tagged **[AI]**, bulk-sent ones **[대량]** ("bulk"), each with the reason.

### How to connect

App → **[설정 편집하기]** (Edit settings) → **AI 판단 연결 (선택)** (Connect AI judgment, optional)

1. **API URL**
   Any OpenAI-compatible (Chat Completions) API works.
   e.g. `https://api.openai.com/v1`, a gateway that serves many models with one key (such as freellmapi), or a local model on your PC
2. Enter the **model name** and **your own API key** → **[저장하기]** (Save)
3. **[연결 테스트]** (Test connection) shows how the AI judges the unpaid example above
4. Turn on **AI 판단 사용하기** (Use AI judgment); it applies from the next run

> <img src="assets/labels/en/warning.svg" alt="Warning" height="36">
>
> With AI judgment on, the content of the ⭕ emails above **is sent to the AI service you entered.**
> Check that service's data retention and training policy. (Off by default)

- The API key is stored separately in `llm_api_key.txt` in the settings folder, not in `config.yaml`, and is never shown again on screen.
- For command-line runs or GitHub Actions, pass it in the `SIP_AND_SORT_LLM_API_KEY` environment variable.

<br>

---

## 💌 Getting started (Windows exe)

No Python or command line needed.

1. Download `sip-and-sort.exe` from [**Releases**](https://github.com/eight-studio/sip-and-sort/releases/latest).
2. Follow [Google Cloud setup](#-google-cloud-setup-one-time) to get your own `credentials.json`. (One time, 5–10 minutes)
3. **Double-click** `sip-and-sort.exe` to open the **sip-and-sort window**.
4. Follow the on-screen steps:
   ① register `credentials.json` → ② enter your name (creator name) → ③ connect Gmail → ④ **[지금 정리하기]** (Sort now)

After that, just open the app and press **[지금 정리하기]**.
Close the window or press [종료] (Quit) when you're done.

### Good to know

- **🍒 Auto-sort**
  Turn on the [자동 정리] (Auto-sort) switch and pick an interval (30 min · 1 h · 2 h · 3 h); it sorts on its own while the app is open.
  A "done! N reply drafts" toast pops up briefly after each run.

- **💌 New-version notice** (from v0.1.11)
  If a new version is out when you open the app, a popup tells you.
  [다운로드하기] (Download) → notice about deleting the old exe → [확인] (OK) downloads the new version and starts it right away.
  Once the new version opens, delete the old exe.

- **🌷 Google sign-in happens in your usual browser**
  Google blocks sign-in inside embedded app windows, so a browser opens only when you press [Gmail 연결하기] (Connect Gmail).
  After you sign in, the app window switches to "connected" by itself.

- **🧁 Where settings are stored**
  `%APPDATA%\sip-and-sort\` (key, sign-in, settings)
  They carry over when you move the exe or update to a new version. Delete this folder to reset.

### Troubleshooting

- **"Windows protected your PC" warning**
  It appears because this is an unsigned personal project. Click **More info → Run anyway**.
  If you're worried, read the code in this repository or [run it with Python](#-for-developers-run-with-python).

- **It opens in the browser instead of its own window**
  The engine that draws the window (Microsoft Edge WebView2) failed to start. All features still work.
  **Restart** the PC (Restart, not Shut down) and try again.
  The log is at `%APPDATA%\sip-and-sort\sip-and-sort.log`.

<br>

---

## 🌷 Google Cloud setup (one time)

sip-and-sort connects to your Gmail with **a key you create in your own Google Cloud project**.
It's free and needs no billing details.

> <img src="assets/labels/en/tip.svg" alt="Tip" height="36">
>
> The Google Cloud console changes often, so menu names may differ a little.
> In the newer console look under **Google Auth Platform** (Branding · Audience · Clients);
> in the older one, **APIs & Services → OAuth consent screen / Credentials**.

### STEP 1. Create a project

1. Sign in to the [Google Cloud Console](https://console.cloud.google.com/) with **the Gmail account you'll connect**.
2. Top left **Select a project** → **[New project]**
3. Enter a name (e.g. `sip-and-sort`) → **[Create]**
4. Make sure **the project you just created is selected** at the top left.

### STEP 2. Enable the Gmail API

1. Type `Gmail API` in the search bar → choose **Gmail API**
2. Click **[Enable]** → done when you see "API enabled"

### STEP 3. App information

1. Left menu **Google Auth Platform** → **[Get started]**
2. Fill in as below → **[Create]**

| Field | Value |
|---|---|
| App name | Anything (e.g. `sip and sort`) |
| User support email | Your Gmail |
| Audience | **External** |
| Contact information | Your email |

> <img src="assets/labels/en/caution.svg" alt="Caution" height="36">
>
> **Don't upload an app logo.**
> With a logo, the app must pass Google's verification before it can be published, and verification for apps using Gmail scopes is hard for individuals to pass.
> Leave the homepage, privacy policy and authorized domains empty too.

### STEP 4. Add your Gmail as a test user ❗ required

A new app is in **"Testing"** status, so only registered accounts can sign in.
If you skip this, sign-in fails with **"Access blocked … Error 403: access_denied"**.

1. **Google Auth Platform → Audience**
2. **Test users → [+ Add users]**
3. Enter the **Gmail address** you'll connect and save (add it even if it's the account that created the project)

### STEP 5. Create a desktop app key and download the JSON

1. **Google Auth Platform → Clients → [+ Create client]**
2. Application type: must be **Desktop app**
3. Enter a name → **[Create]**
4. In the dialog, click **[Download JSON]**

> <img src="assets/labels/en/warning.svg" alt="Warning" height="36">
>
> In some console versions **the client secret can only be downloaded from this dialog.** Download it before closing.
> Treat this file **like a password**: don't send it to anyone or upload it to GitHub.

### STEP 6. Connect in sip-and-sort

1. Open sip-and-sort.
2. In **step 1**, choose the JSON file → [등록하기] (Register)
3. **Step 3 [Gmail 연결하기]** (Connect Gmail) → sign in with the Gmail you added in STEP 4
4. If you see **"Google hasn't verified this app"**, click **[Advanced] → [Go to (app name)]**
5. **[Continue]** → done when the screen shows **connected**

### STEP 7. (Recommended) Stop signing in again every 7 days

Sign-ins for apps in "Testing" status **expire after 7 days**.

1. **Google Auth Platform → Audience → [Publish app]**
   - If it says verification is required, **you don't need to apply.** (Up to 100 users)
2. In sip-and-sort, do **[연결 해제] (Disconnect) → [Gmail 연결하기] (Connect Gmail)** **once more**.

### Common problems

| Symptom | Fix |
|---|---|
| **Error 403: access_denied** | STEP 4 — add your Gmail as a test user |
| "This is a web application OAuth client" | STEP 5 — create it again as a **Desktop app** |
| "client_id is empty or an example value" | Register the file from STEP 5, not the example file |
| Google sign-in window doesn't open | Use the **[Google 로그인 열기]** (Open Google sign-in) button in step 3 |
| "Gmail sign-in expired or access was revoked" | Connect again in step 3 (see STEP 7) |
| "Gmail API has not been used in project …" | STEP 2 — **[Enable]** the Gmail API in the selected project |
| "Branding page must be completed" when publishing | Fill in the STEP 3 required fields, **remove the app logo**, save |

<br>

---

## 🧁 Config file (config.yaml)

Most settings can be changed in the app.
Edit `config.yaml` directly only for finer control, such as keywords or label names.
(Example: [`config.example.yaml`](config.example.yaml))

| Key | Description | Default |
|---|---|---|
| `activity_name` | Name (creator name) used in reply drafts | `[ ]` in drafts when empty |
| `lookback_hours` | How many hours back to check | `24` |
| `gmail_labels.*` | Type and draft-done label names (`/` makes sub-labels) | `협업제안/브랜드협찬` etc. |
| `keywords.*` | Collab keywords, bulk-mail filtering on/off | The list above |
| `templates.*` | A/B/C/D reply texts | Generic default texts (Korean) |
| `llm.*` | AI judgment on/off, API URL, model, confidence threshold | Off |
| `auto_run.*` | Auto-sort on/off and interval | Off, 60 min |
| `my_addresses` | Your own addresses that forward or alias to this inbox | `[]` |

**Placeholders for reply texts**

- `{activity_name}` — your name (creator name)
- `{contact_name}` — the sender's contact name
- `{original_subject}` — subject of the received email

Unknown values stay as `[ ]` in the draft; fill them in Gmail before sending.

<br>

---

## 🌸 For developers: run with Python

Requires Python **3.11 or later**.

```bash
git clone https://github.com/eight-studio/sip-and-sort.git
cd sip-and-sort
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # for the app window too: ".[dev,desktop]"
```

### Common commands

```bash
sip-and-sort setup               # settings screen (in the browser)
sip-and-sort setup --window      # settings screen (in the app window)

sip-and-sort run --dry-run       # preview: prints results without changing anything
sip-and-sort run                 # real run: labels + drafts (never sends)
sip-and-sort run --since 48h     # last 48 hours (90m, 2d, 1w also work)
sip-and-sort run --summary-only  # counts only

sip-and-sort auth --no-browser   # remote server: print the sign-in URL only
```

### Sample output

The app prints its results in Korean. Example:

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

It lists counts per type (brand sponsorship / paid ad / other), the drafts to be written with their case, the emails that need manual review with the reason, and the bulk emails that were excluded.

Exit codes: `0` OK · `1` some emails failed · `2` config or auth error

<br>

---

## 🍒 Scheduled runs

To sort while the app is open, the [auto-sort switch](#good-to-know) is enough.
To run **even with the app closed**, use one of the options below.

### Windows Task Scheduler

Change the path and run this in PowerShell to sort the last 2 hours of email every hour.

```powershell
$exe = "C:\path\to\sip-and-sort.exe"
$action = New-ScheduledTaskAction -Execute $exe -Argument "run --non-interactive --since 2h"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "sip-and-sort" -Action $action -Trigger $trigger
```

`--non-interactive`: if the sign-in has expired, it exits with an error instead of opening a browser.

### macOS / Linux cron

```cron
0 * * * * cd /path/to/sip-and-sort && .venv/bin/sip-and-sort run --non-interactive --since 2h >> run.log 2>&1
```

### GitHub Actions (runs even with your PC off)

1. Get the contents of the `config.yaml`, `credentials.json` and `token.json` created locally.
2. Add 3 secrets under the repository's **Settings → Secrets and variables → Actions**:
   - `GMAIL_CONFIG_YAML` ← `config.yaml`
   - `GMAIL_CREDENTIALS_JSON` ← `credentials.json`
   - `GMAIL_TOKEN_JSON` ← `token.json`
3. [`run.yml`](.github/workflows/run.yml) sorts the last 3 hours of email **every hour on the hour**.
   You can also run it manually from the Actions tab. (Manual runs default to preview)

> <img src="assets/labels/en/warning.svg" alt="Warning" height="36">
>
> **Anyone can read the Actions logs of a public repository.**
> That's why the default workflow prints counts only. Run it from a private repository if you can.

<br>

---

## 📌 Rules and limits

- The default judgment uses the **keyword rules** in [`classifier.py`](sip_and_sort/classifier.py).
  Only when AI judgment is on are the emails the rules couldn't decide sent to the AI.
- Korean keywords ignore spacing (`유료 광고` = `유료광고`).
  English is matched by whole words, and short uppercase acronyms like `PR` and `PPL` are case-sensitive.
- Quoted earlier messages in replies (`>` lines, "… wrote:") are left out of the judgment.
- Emails in older Korean encodings such as EUC-KR are read without garbling.
- It is designed to **skip the draft when in doubt**.
  It still isn't perfect, so **always read a draft before sending it.**

**Keep in mind**

- Labeled emails are not processed again, even if a new reply arrives later. (Prevents duplicate drafts)
- If you receive email forwarded from another address, add that address to `my_addresses` so it isn't mistaken for BCC bulk mail.
- Gmail API rate limits and temporary errors are retried automatically.

<br>

---

## 🌹 Security · privacy

- **It only searches and reads, adds labels and saves drafts.** It never sends or deletes email.
- **The settings screen runs only on your PC** and opens only with an access token that changes on every launch.
- **What leaves your PC**
  - Google: connecting to Gmail and processing email
  - AI service: when AI judgment is on, parts of some emails, with personal details masked
  - GitHub: checking for a new version (only about your IP address; no email or settings data)
- `credentials.json` `token.json` `config.yaml` `llm_api_key.txt` are in `.gitignore` and never committed.
- If `token.json` leaks, someone else could read your email.
  If you suspect that, revoke access right away at [Google Account → Third-party access](https://myaccount.google.com/permissions).

<br>

---

## 🍰 Project structure

```text
sip-and-sort/
├── sip_and_sort/
│   ├── main.py            # entry point: setup / auth / run
│   ├── setup_server.py    # settings server, app window, auto-sort, new-version notice
│   ├── web/               # settings screen (setup.html) + icon
│   ├── runner.py          # one sorting pass + summary
│   ├── classifier.py      # collab detection, bulk-mail detection, typing, A/B/C/D cases
│   ├── llm.py             # AI judgment (OpenAI-compatible API, masking)
│   ├── templates.py       # reply draft templates
│   ├── gmail_client.py    # Gmail auth, search, labels, drafts (no send feature)
│   ├── message.py         # reading email (encoding handling)
│   ├── updates.py         # new-version check and download
│   └── config.py          # reading and validating the config file
├── tests/                 # automated tests (fake Gmail, AI and GitHub responses)
├── packaging/             # exe build settings
├── .github/workflows/     # tests, exe release, scheduled runs
├── assets/                # icon
├── CHANGELOG.md           # changes per version (Korean)
└── config.example.yaml / credentials.example.json
```

### Build the exe yourself

```bash
pip install -r requirements-build.txt -e .
pyinstaller --noconfirm packaging/sip-and-sort.spec   # → dist/sip-and-sort.exe
```

Pushing a tag that starts with `v` makes GitHub build the exe, upload it to Releases,
and use that version's section of [`CHANGELOG.md`](CHANGELOG.md) as the release notes.

### 💞 Contributing

Bug reports and ideas are always welcome! Open an Issue or a Pull Request.
After changing code, check that the tests pass with `pytest`. (No Google account needed)
See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

<br>

---

## 🔖 License

[MIT License](LICENSE)
Free to use, modify and distribute; the software is provided "as is".
You are responsible for draft contents and for anything you actually send.
