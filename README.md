# Weekly Free Trend Report Automation

PC가 꺼져 있어도 GitHub Actions에서 매주 월요일 오전 8시(KST)에 실행되는 무료 자동화입니다.

## 현재 운영 방식

- 실행 위치: GitHub Actions
- 실행 시간: 매주 월요일 08:00 KST
- OpenAI API: 사용하지 않음
- 이미지 생성: 자동 생성하지 않음
- 결과물: 전체 HTML 리포트, 수동 이미지 생성 프롬프트, 수집 원본 요약
- 발송: Gmail SMTP로 `sunghyun.yang@hanwha.com`, `sunghyun1003@naver.com` 동시 발송

## 비용 구조

무료 운영을 위해 아래 기능은 자동 실행에서 제외합니다.

- OpenAI 텍스트 생성
- OpenAI 이미지 생성
- LLM 검증

대신 Python 규칙 기반 로직으로 트렌드 키워드 추출, 점수화, 광고 콘셉트, 배너 카피, 이미지 생성 프롬프트를 생성합니다.

## 필요한 GitHub Secrets

GitHub repository의 `Settings > Secrets and variables > Actions > Repository secrets`에 아래 값을 등록해야 합니다.

| Secret name | 설명 |
|---|---|
| `SMTP_USERNAME` | Gmail 주소, 예: `sunghyun1003@gmail.com` |
| `SMTP_PASSWORD` | Gmail 앱 비밀번호 |
| `EMAIL_FROM` | 발신 Gmail 주소 |
| `YOUTUBE_API_KEY` | YouTube Data API key |
| `NAVER_CLIENT_ID` | Naver Developers Client ID |
| `NAVER_CLIENT_SECRET` | Naver Developers Client Secret |

OpenAI 키는 등록하지 않아도 됩니다.

## 실행 파일

- `.github/workflows/weekly-free-trend-report.yml`: GitHub Actions 예약 실행
- `scripts/run_weekly.py`: 주간 리포트 실행 진입점
- `src/trend_banner_automation/free_report.py`: 무료 규칙 기반 리포트 생성기
- `src/trend_banner_automation/full_report_html.py`: HTML 리포트 변환기
- `config/sources.json`: 수집 소스 설정

## 로컬 테스트

실제 이메일 발송이나 외부 API 호출을 피하려면 `.env`에서 아래처럼 설정합니다.

```env
ENABLE_OPENAI_REPORT=false
ENABLE_LLM_VALIDATION=false
GENERATE_IMAGES=false
COMPOSE_FINAL_BANNERS=false
SEND_EMAIL=false
EMAIL_DRY_RUN=true
```

실행:

```powershell
.\.venv\Scripts\python.exe scripts\run_weekly.py --root .
```

결과는 `outputs/YYYYMMDD_HHMMSS/`에 생성됩니다.
