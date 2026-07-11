# Deployment Guide

This document covers both the general deployment steps and the actual
configuration used for this project's live deployment, including the
Windows-specific fixes and platform gotchas hit along the way. See
`docs/DEBUGGING.md` for full technical detail on any issue referenced here.

---

## Live Deployment (this project)

| | |
|---|---|
| Frontend | https://ethara-seat-allocation-phi.vercel.app |
| Backend API | https://ethara-seat-allocation-production.up.railway.app |
| API Docs (Swagger) | https://ethara-seat-allocation-production.up.railway.app/docs |
| GitHub Repository | https://github.com/pragya302002/Ethara-Seat-Allocation |
| Demo login | any seeded employee email · password `Password123!` |
| Demo admin | `eric.bernard1@etharatest.com` / `Password123!` |

---

## Architecture

- **Backend**: FastAPI, deployed on Railway from `backend/` (monorepo root directory set explicitly)
- **Database**: PostgreSQL, Railway-managed plugin in the same project as the backend service
- **Frontend**: Next.js, deployed on Vercel from `frontend/` (monorepo root directory set explicitly)
- **AI Assistant**: Groq API (originally built against Anthropic; switched — see `docs/DEBUGGING.md` entry 10)

---

## Prerequisites

- GitHub repo pushed
- Railway account connected to GitHub
- Vercel account connected to GitHub
- A Groq API key (free tier, no billing required) from [console.groq.com](https://console.groq.com)

---

## 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Ethara AI seat allocation system"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

**Watch for GitHub secret scanning.** If any real API key or credential
ever gets pasted directly into a source file (rather than `.env`, which is
gitignored) instead of left as an empty default, GitHub will block the
push. If this happens: fix the file, then either amend the commit (safe if
it's the only commit and hasn't been pushed yet) or rewrite history before
pushing. Never push past a secret-scanning block by force — rotate the
key afterward regardless, as a precaution. See `docs/DEBUGGING.md` entry
covering this exact incident during this project's build.

---

## 2. Backend — Railway

### Step 1 — Create the Postgres database first
1. Railway dashboard → **New** → **Database** → **PostgreSQL**
2. This becomes the source of `DATABASE_URL` for your backend service

### Step 2 — Create the backend service
1. In the **same Railway project** as your Postgres database: **New** → **GitHub Repo** → select your repo
2. If this is the first connection, you'll be prompted to **Install the Railway GitHub App** — authorize it and grant access to your repo

### Step 3 — Set the Root Directory
This project is a monorepo (`backend/` and `frontend/` both in one repo).
Railway's build system will fail instantly if this isn't set — it'll try
to build from the repo root, which only contains markdown files.

1. Service → **Settings** tab
2. Find **Root Directory** → set to `backend`
3. Save

### Step 4 — Set environment variables
Service → **Variables** tab → add each of these individually:

JWT_SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://ethara-seat-allocation-phi.vercel.app
GROQ_API_KEY=<Groq key>


`DATABASE_URL` should already be present automatically if this service is
in the same Railway project as the Postgres plugin — don't add it manually
if so.

**Critical: after adding/editing variables, you must explicitly click the
"Deploy" button.** Railway shows a banner like "Apply N changes" with a
purple Deploy button — saving a variable's value does NOT automatically
redeploy the running service. This is the single most common point of
confusion in this deployment: a variable can be correctly saved in the UI
while the live app is still running an older deployment without it. If
something "isn't working" after a variable change, check the deployment
timestamp against the variable edit timestamp before debugging further.

### Step 5 — Set the start command
Settings → **Deploy** section → **Custom Start Command**:
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT

Running the migration in the start command keeps schema and deploy in
lockstep on every redeploy.

### Step 6 — Generate a public domain
Settings → **Networking** → **Generate Domain**.

### Step 7 — Deploy and verify
Click **Deploy**. Watch the Deployments tab progress through Initialization
→ Build → Deploy → Network (healthcheck). All four should go green.

If Build fails: check Root Directory is actually set (Step 3).
If it passes Build/Deploy but fails Healthcheck: check for a missing
dependency in `requirements.txt` — a package installed locally via `pip
install X` but never added to the file will work locally (already in your
venv) but crash on Railway's fresh build environment on `import`, which
surfaces as a healthcheck timeout rather than an obvious dependency error.

### Step 8 — Seed the database
Once live, run one-off via Railway's service shell/CLI:
python3 -m app.seed.seed

Only needs to run once — the script refuses to re-run if employees already
exist.

### Step 9 — Verify
```bash
curl https://<your-backend-domain>/health
# should return: {"status":"ok","environment":"production"}
```

---

## 3. Frontend — Vercel

### Step 1 — Import the project
1. Vercel → **Add New** → **Project** → import your GitHub repo
2. Vercel should auto-detect Next.js once the root directory is set correctly

### Step 2 — Set the Root Directory
Set to `frontend` (same monorepo reasoning as the backend).

### Step 3 — Environment variable
NEXT_PUBLIC_API_URL=https://<your-railway-backend-domain>/api/v1

No trailing slash.

### Step 4 — Deploy
Click **Deploy**. Vercel gives you the live frontend URL on completion
(e.g. `https://<project-name>-<hash>.vercel.app`, or a cleaner alias like
`https://<project-name>.vercel.app` / `-<random>.vercel.app` depending on
naming collisions).

### Step 5 — Update backend CORS to match (do not skip this)
Go back to Railway → backend service → Variables → update `CORS_ORIGINS`
to the **exact** Vercel URL from Step 4, then **explicitly click Deploy**
again.

Skipping this step produces a specific, confusing symptom: the frontend
loads fine, the login page renders, but submitting credentials that work
correctly via direct API calls fails with a generic "check your
credentials" error — because the browser's CORS policy silently blocks
the cross-origin request before the frontend ever receives a real
response to distinguish "wrong password" from "request never reached the
server." If login fails on the live site but works via `curl`/
`Invoke-RestMethod` against the same backend, CORS is the first thing to
check.

### Step 6 — Verify end-to-end
Open the live frontend URL, log in with a seeded employee email +
`Password123!`, confirm the dashboard loads with real data.

---

## Local development on Windows — known gotchas

This project was originally built and tested on Linux. Setting up locally
on Windows surfaced several platform-specific issues, all now fixed in
the codebase, but worth knowing if you're setting up fresh:

1. **`python3` isn't recognized** — use `py` instead on Windows.
2. **`source venv/bin/activate` doesn't work in PowerShell** — use
   `venv\Scripts\Activate.ps1` instead. If PowerShell blocks script
   execution, run once:
```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
3. **`asyncpg` fails to build** with `Microsoft Visual C++ 14.0 or greater
   is required` — this project already uses `psycopg[binary,pool]`
   instead specifically to avoid this (prebuilt Windows wheels, no
   compiler needed).
4. **`psycopg.InterfaceError: ... cannot use the 'ProactorEventLoop'`** —
   already handled in `app/database/session.py` and `alembic/env.py` via
   an explicit `WindowsSelectorEventLoopPolicy` guard gated on
   `sys.platform == "win32"`.
5. **Node.js/`npm` not found even after installing** — usually means
   PATH hasn't refreshed; a full system restart (not just closing/
   reopening the terminal) resolves this reliably.
6. **Port 3000 already in use by another local project** — run the
   frontend on a different port: `npm run dev -- -p 3001`, and remember
   to add that port to the backend's local `CORS_ORIGINS` too.

---

## Environment variables reference

| Variable | Where | Required? | Notes |
|---|---|---|---|
| `DATABASE_URL` | Backend | Yes | Auto-provided by Railway if Postgres plugin is in the same project |
| `JWT_SECRET_KEY` | Backend | Yes | Any random string; generate your own, don't reuse across environments |
| `ENVIRONMENT` | Backend | Recommended | `production` on live deploys |
| `DEBUG` | Backend | Recommended | `false` on live deploys |
| `CORS_ORIGINS` | Backend | Yes | Must exactly match your live frontend URL, no trailing slash |
| `GROQ_API_KEY` | Backend | Optional | Only powers the AI Assistant; app works fully without it, assistant just reports "not configured" |
| `NEXT_PUBLIC_API_URL` | Frontend | Yes | Must point at `<backend-url>/api/v1`, no trailing slash |

