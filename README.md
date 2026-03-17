[README.md](https://github.com/user-attachments/files/26047413/README.md)
# 밈레이더 크롤러

디시인사이드 · 에펨코리아 · YouTube Shorts 수집기  
완전 무료 스택으로 동작 (Supabase Free + GitHub Actions)

## 프로젝트 구조

```
meme-radar/
├── crawlers/
│   ├── dcinside.py   # 디시인사이드 크롤러
│   ├── fmkorea.py    # 에펨코리아 크롤러
│   └── youtube.py    # YouTube Shorts 크롤러
├── utils/
│   └── db.py         # Supabase 저장 유틸
├── .github/
│   └── workflows/
│       └── crawl.yml # GitHub Actions (2시간마다 자동 실행)
├── main.py           # 통합 실행기
├── schema.sql        # Supabase 테이블 생성 SQL
└── requirements.txt
```

## 세팅 순서

### 1. Supabase 설정
1. https://supabase.com 에서 무료 프로젝트 생성
2. SQL Editor → `schema.sql` 내용 붙여넣고 실행
3. Settings → API → `URL`과 `anon key` 복사

### 2. YouTube API 키 발급
1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성 → YouTube Data API v3 활성화
3. 사용자 인증 정보 → API 키 생성

### 3. GitHub Secrets 설정
Repository → Settings → Secrets → New repository secret

| 이름 | 값 |
|------|-----|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase anon key |
| `YOUTUBE_API_KEY` | YouTube Data API v3 키 |

### 4. 로컬 테스트

```bash
pip install -r requirements.txt

# .env 파일 만들기
echo "SUPABASE_URL=https://xxx.supabase.co" > .env
echo "SUPABASE_KEY=eyJ..." >> .env
echo "YOUTUBE_API_KEY=AIza..." >> .env

# 전체 실행
python main.py

# 개별 실행
python main.py --only dci   # 디시만
python main.py --only fmk   # 에펨만
python main.py --only yt    # 유튜브만
```

## 실행 주기

GitHub Actions cron으로 2시간마다 자동 실행.  
Actions 탭에서 수동 실행(workflow_dispatch)도 가능.

## 무료 한도 요약

| 서비스 | 무료 한도 | 소진 예상 |
|--------|-----------|-----------|
| Supabase | 500MB · 무제한 req | 수개월 여유 |
| GitHub Actions | 월 2,000분 | 2시간 주기 실행 시 ~720분/월 |
| YouTube API | 10,000유닛/일 | 쿼리 6개×100유닛 = 600유닛/회 |

## 다음 단계

- `utils/classifier.py` — 흐름 방향 분류 (유입/독립/역수출)
- `utils/lifecycle.py` — 생애주기 단계 자동 태깅
- `crawlers/reddit.py` — Reddit PRAW 크롤러 추가
