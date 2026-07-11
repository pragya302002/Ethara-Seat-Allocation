# Deployment Guide

## Prerequisites
- GitHub repo pushed (see steps below if not done yet)
- Railway account connected to GitHub
- Vercel account connected to GitHub

---

## 1. Push to GitHub

From the project root:
```bash
git init
git add .
git commit -m "Initial commit: Ethara AI seat allocation system"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

---

## 2. Backend — Railway

1. **New Project → Deploy from GitHub repo** → select this repo.
2. Railway will detect the `backend/` folder isn't at the repo root — set
   the **Root Directory** to `backend` in the service's Settings tab.
3. **Add a PostgreSQL plugin**: New → Database → PostgreSQL. Railway
   auto-injects `DATABASE_URL` into your backend service's environment —
   you don't need to copy/paste it manually if both are in the same project.
4. **Set environment variables** on the backend service (Settings → Variables):
   ```
   JWT_SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
   ENVIRONMENT=production
   DEBUG=false
   CORS_ORIGINS=https://<your-vercel-app>.vercel.app
   ANTHROPIC_API_KEY=<your key, if you want the AI Assistant live>
   ```
   (`DATABASE_URL` is auto-provided by the Postgres plugin — leave it as-is.)
5. **Set the start command** (Settings → Deploy):
   ```
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   Running the migration in the start command keeps schema and deploy in
   lockstep — no separate manual migration step to forget.
6. **Seed the database** — once the service is live, run one-off via
   Railway's shell (Service → the "..." menu → "Run command" or the CLI):
   ```
   python3 -m app.seed.seed
   ```
   This only needs to run once; the script refuses to run again if
   employees already exist (see the guard at the top of `main()` in
   `seed.py`).
7. Note the generated public URL (Settings → Networking → Generate Domain)
   — this is your **Backend API URL**. Confirm it works:
   ```
   curl https://<your-backend>.up.railway.app/health
   ```

---

## 3. Frontend — Vercel

1. **New Project → Import** this GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset should auto-detect as Next.js.
4. **Environment variable**:
   ```
   NEXT_PUBLIC_API_URL=https://<your-backend>.up.railway.app/api/v1
   ```
5. Deploy. Vercel gives you the **Frontend URL**.
6. Go back to Railway and update `CORS_ORIGINS` on the backend to match
   this exact Vercel URL (with `https://`, no trailing slash), then
   redeploy the backend service so the CORS change takes effect.

---

## 4. Verify the live deployment

```bash
# Backend health
curl https://<backend-url>/health

# Login
curl -X POST https://<backend-url>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<a seeded employee email>","password":"Password123!"}'

# Swagger docs
open https://<backend-url>/docs
```

Then open the Vercel frontend URL in a browser and log in with the same
credentials.

---

## Notes

- **Railway free tier**: the $5/30-day trial credit is enough for this
  assessment's lifespan; no card required to start.
- **Cold starts**: Railway's free tier may sleep the service after
  inactivity — the first request after a while can be slow. This is a
  platform characteristic, not an application bug.
- **Migrations on redeploy**: because `alembic upgrade head` runs in the
  start command, every redeploy re-checks the schema is current — safe
  to leave as-is for future changes.
