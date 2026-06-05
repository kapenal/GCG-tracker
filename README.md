# 遊々亭 GCG 販売 시세 관리

**React** + **FastAPI** + **PostgreSQL** 로 遊々亭 GCG 販売 가격을 수집·저장·비교합니다.

## 구조

```
yuyu-gcg-tracker/
├── docker-compose.yml    # PostgreSQL + API + React
├── backend/              # FastAPI, 스크래퍼, DB 모델
├── frontend/             # React (Vite + TypeScript)
└── data/latest.json      # 기존 JSON → DB 이관용 (선택)
```

| 계층 | 기술 |
|------|------|
| Frontend | React 18, Vite, TypeScript |
| Backend | FastAPI, SQLAlchemy, httpx |
| DB | PostgreSQL 16 |

## 빠른 시작 (Docker)

Docker Desktop이 필요합니다.

```powershell
cd C:\Users\dlsgh\yuyu-gcg-tracker

# 전체 기동
docker compose up --build

# (선택) 기존 latest.json을 DB에 넣기 — API 기동 후 다른 터미널에서
docker compose run --rm backend python scripts/import_latest_json.py
```

| 서비스 | URL |
|--------|-----|
| React UI | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| API 문서 | http://localhost:8000/docs |
| PostgreSQL | `localhost:5432` (user/pass/db: `gcg` / `gcg` / `gcg_prices`) |

UI에서 **「가격 수집」** 버튼 → `POST /api/sync` (19개 세트, 약 50초).

## 로컬 개발 (Python·Node 설치 시)

### DB

```powershell
docker compose up db -d
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

프록시: `/api` → `http://localhost:8000` (`vite.config.ts`).

## API 요약

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/sets` | 세트 목록 + 카드 수 |
| GET | `/api/cards?set=&rarity=&q=` | 최신 스냅샷 카드 (등급 필터) |
| GET | `/api/rarities?set=` | 등급별 카드 수 (LR++, LR+, …) |
| GET | `/api/cards/changes` | 직전 스냅샷 대비 가격 변동 |
| GET | `/api/cards/{id}/history` | 카드별 가격 이력 |
| POST | `/api/sync` | 遊々亭에서 전체 수집 |
| GET | `/api/sync/snapshots` | 스냅샷 목록 |

## DB 스키마

- `card_sets` — gd01, st01, promo-rp100 …
- `cards` — 이름, 이미지, 카드번호, **rarity**(LR++, LR+, LR, R+, …), `external_id`
- `price_snapshots` — 수집 시각
- `price_records` — 스냅샷별 가격·재고

## 매일 수집 (스케줄)

```powershell
# Docker 환경
curl -X POST http://localhost:8000/api/sync
```

Windows 작업 스케줄러에 위 명령을 등록하면 됩니다.

## 대상 URL

`backend/app/scraper_config.py` — GD01–04, ST01–09, 프로모, reto.  
`promo-rp100` 등은 사이트 인덱스 URL이 아니라 `rp-100` 등 실제 목록 URL을 사용합니다.

## 주의

- 遊々亭 공식 API 없음. 개인용·요청 간격(기본 2초) 준수.
- 이전 Node 단일 프로젝트(`src/*.js`, `public/`)는 v2에서 제거되었습니다.
