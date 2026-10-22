# 기여 가이드

sip-and-sort 에 관심 가져 주셔서 감사합니다! 버그 제보, 분류 키워드 개선, 문서 수정 모두 환영합니다.

## 개발 환경

```bash
git clone https://github.com/<your-id>/sip-and-sort.git
cd sip-and-sort
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

테스트는 Gmail API를 `unittest.mock` 으로 대체하므로 Google 계정 없이 실행됩니다.

## 지켜야 할 원칙

1. **자동 발송 금지** — `messages.send`, `drafts.send` 등 발송 API를 호출하는 코드는 받지 않습니다.
   이 프로그램은 라벨과 *초안*만 다룹니다.
2. **비밀 값 커밋 금지** — `credentials.json`, `token.json`, `config.yaml`, 실제 이메일 주소·전화번호·주소·단가가
   들어간 파일은 절대 커밋하지 마세요. 테스트 픽스처에는 `example.com` 같은 가짜 값만 사용합니다.
3. **외부 전송 금지** — 메일 내용을 Google 이외의 서버(분석 API, LLM 등)로 보내는 기능은
   기본값으로 켜지지 않도록, 별도 옵트인 옵션과 README 설명이 있어야 합니다.

## 분류 규칙을 고치고 싶다면

- 키워드 규칙: `sip_and_sort/classifier.py` 의 `DEFAULT_RULES`
- 새 규칙에는 `tests/fixtures/emails/` 에 샘플 메일(.eml)을 추가하고 `tests/test_classifier.py` 에 테스트를 넣어 주세요.
- 오탐(일반 메일을 협업으로 판단)과 미탐(협업 메일을 놓침) 중 **오탐을 줄이는 쪽**을 우선합니다.
  애매한 메일은 초안 없이 "직접 검토 필요"로 두는 것이 원칙입니다.

## Pull Request

1. 이슈를 먼저 열어 변경 방향을 공유해 주시면 좋습니다.
2. 브랜치를 만들어 작업하고, `pytest -q` 가 통과하는지 확인해 주세요.
3. PR 설명에 무엇을, 왜 바꿨는지 적어 주세요.
