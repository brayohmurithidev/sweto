# SWETO — Sweat Together

SWETO is a mobile fitness marketplace for East Africa. The MVP loop is:
**discover a gym → book a day pass → pay with M-Pesa → check in.**

## Repository layout

| Path | What it is |
|---|---|
| `sweto-api/` | Backend: FastAPI (Python 3.12), PostgreSQL 16, Redis, Alembic, S3 |
| `sweto_app/` | Mobile app: Flutter (iOS and Android), Riverpod, go_router, Dio |
| `.github/workflows/` | CI for both projects |

Both projects keep their full git history from before they were combined
into this repository (see `git log -- sweto-api` and `git log -- sweto_app`).

## Getting started

### API

```bash
cd sweto-api
cp .env.example .env          # then fill in secrets
docker compose up -d          # Postgres + Redis
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Checks: `uv run ruff check . && uv run mypy app && uv run pytest`

### Mobile app

```bash
cd sweto_app
flutter pub get
./tool/run_local.sh           # iOS simulator; see tool/ for Android
```

Google Maps keys live in untracked local files; see
`sweto_app/docs/google-maps-setup.md`.

Checks: `flutter analyze && flutter test`

## Secrets

Never commit `.env`, `android/local.properties`, `GoogleMaps.local.xcconfig`,
keystores or provider credentials. They are git-ignored.

## Project documentation

Product, design and engineering decisions, the roadmap and the project
tracker live in the SWETO Google Drive folder (start with PROJECT_TRACKER).
