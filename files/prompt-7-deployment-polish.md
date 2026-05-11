# Prompt 7 — Deployment Configs and Polish

Final pass — deployment readiness and polish.

## Backend (Render deployment)

Confirm `backend/build.sh` contains:

```bash
#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

Confirm `Procfile` contains:

```
web: gunicorn trip_planner.wsgi --log-file -
```

In `settings.py`:

- `SECRET_KEY = config('SECRET_KEY', default='dev-secret-change-me')`
- `DEBUG = config('DEBUG', default=False, cast=bool)`
- `ALLOWED_HOSTS` read from env var `ALLOWED_HOSTS`, comma-split, default `['*']`
- `CORS_ALLOWED_ORIGINS` read from env var, default empty list when `DEBUG=False`; `CORS_ALLOW_ALL_ORIGINS=True` only when `DEBUG=True`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`
- WhiteNoise storage configured

Add a `render.yaml` at repo root describing the web service (Python env, build command `./build.sh`, start command `gunicorn trip_planner.wsgi`).

## Frontend (Vercel deployment)

- Add `vercel.json` at `frontend/` root with a rewrite for SPA routing
- Confirm `.env.example` shows `VITE_API_URL`
- README section explaining: set `VITE_API_URL` in Vercel project settings to the deployed Render backend URL

## Error handling polish

- **Frontend**: if API returns 502, show "Map service temporarily unavailable, please try again". If 400, show the validation message from the response body.
- **Backend**: log errors with `logging` module, don't leak stack traces in production responses.

## README.md (top-level) — make it portfolio-quality

- Project title and 1-paragraph description
- Demo links section (placeholder for hosted URL and Loom URL)
- Features bullet list
- Tech stack
- Local development setup (backend + frontend, step by step)
- Environment variables
- Architecture diagram (ASCII or describe)
- HOS rules implemented (bullet list referencing FMCSA)
- Known limitations / future work

## Final check

Run:

```bash
python manage.py check
python manage.py test planner
cd ../frontend && npm run build
```

All three should succeed.
