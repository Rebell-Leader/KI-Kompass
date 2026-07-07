# Deploying KI Kompass

The app runs anywhere Python runs. Auth and database adapt to environment
variables, so the same codebase serves three setups:

| Environment | Database | Auth |
|---|---|---|
| Local development | SQLite (automatic) | Dev login (automatic) |
| Replit | Replit Postgres (`DATABASE_URL`) | Replit OIDC (`REPL_ID`) |
| **Production: Render + Supabase** | Supabase Postgres | Supabase email/password |

## Production: Supabase + Render (free tiers)

### 1. Supabase project (database + auth)

1. Create a project at [supabase.com](https://supabase.com).
2. **Database**: in *Project Settings → Database*, copy the **Session pooler**
   connection string (port 5432 — long-lived SQLAlchemy connections need
   session mode, not the transaction pooler on 6543). It looks like
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
3. **Auth**: in *Authentication → Providers*, make sure **Email** is enabled.
   - For the smoothest MVP flow, disable *Confirm email* (users can log in
     immediately after signup). With confirmation enabled, the app tells
     users to check their inbox first — both modes are supported.
4. Note your **Project URL** (`https://<ref>.supabase.co`) and the
   **anon/public key** from *Project Settings → API*.

### 2. Qdrant Cloud (vector search for the AI chat)

Embeddings and vector search run in [Qdrant Cloud](https://cloud.qdrant.io)
(free tier) with **server-side inference** — no embedding model runs on the
web instance, which both fits Render's free-tier memory and avoids the
`onnxruntime` build problem on that platform.

1. Create a free cluster at cloud.qdrant.io and copy its URL
   (`https://<cluster-id>.<region>.gcp.cloud.qdrant.io:6333`) and API key.
2. Set `QDRANT_URL` and `QDRANT_API_KEY` on the Render service (step 3).

The app creates and syncs the `munich_relocation_kb` collection
automatically, re-syncing whenever the knowledge base is refreshed.
Without Qdrant configured the chat still works, using a simple keyword
ranking over the knowledge base instead of semantic search.

### 3. Render web service

1. Push this repository to GitHub.
2. In the [Render dashboard](https://dashboard.render.com), choose
   **New → Blueprint** and select the repo — `render.yaml` configures a free
   web service (`SESSION_SECRET` is generated automatically).
3. After the first deploy, set the remaining environment variables on the
   service:
   - `DATABASE_URL` — the Supabase session-pooler connection string
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY` — enables Supabase login/signup
   - `FEATHERLESS_API_KEY` *or* `OPENAI_API_KEY` — enables the AI chat
     (without a key the app runs; chat explains it's unavailable)
   - `QDRANT_URL` and `QDRANT_API_KEY` — semantic retrieval via Qdrant Cloud
4. Redeploy. The start command runs `flask db upgrade` before gunicorn, so
   schema migrations apply automatically on every deploy.

Note: free Render services sleep after inactivity; the first request after
idle takes ~30s to wake.

### 4. Scheduled jobs (knowledge refresh + email reminders)

Render's free tier has no cron, so `.github/workflows/scheduled-jobs.yml`
runs the daily jobs from GitHub Actions against the production database:

1. In the GitHub repo, add **Actions secrets**: `DATABASE_URL` (same
   Supabase string) and, for reminder emails, `SMTP_HOST`, `SMTP_PORT`,
   `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`.
2. Add an **Actions variable** `ENABLE_SCHEDULED_JOBS` = `true`.

The workflow runs `flask refresh-knowledge` (re-scrapes official Munich
sources into the AI knowledge base and bumps each task's *verified* date)
and `flask send-reminders` (emails users their overdue/upcoming tasks)
daily at 06:00 UTC. Run it manually anytime via *Actions → Scheduled jobs →
Run workflow*.

## Replit

Unchanged: with `REPL_ID` present the app uses Replit OIDC auth, and
`.replit`/`pyproject.toml` drive the run button and autoscale deployment.

## Local development

```bash
uv sync --group dev
uv run python main.py     # SQLite + dev login, http://localhost:5000
uv run pytest             # test suite
```

## Environment variable reference

| Variable | Required | Purpose |
|---|---|---|
| `SESSION_SECRET` | production | Flask session signing key |
| `DATABASE_URL` | production | Postgres connection string (SQLite fallback without it) |
| `SESSION_COOKIE_SECURE` | production | `true` behind HTTPS |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | for Supabase auth | enables email/password login |
| `REPL_ID` | on Replit | enables Replit OIDC (takes precedence over Supabase) |
| `FEATHERLESS_API_KEY` / `OPENAI_API_KEY` | for AI chat | LLM provider (Featherless preferred) |
| `QDRANT_URL`, `QDRANT_API_KEY` | for semantic search | Qdrant Cloud cluster (keyword fallback without it) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`, `MAIL_FROM` | for reminders | outbound email |
| `FLASK_SKIP_DB_CREATE` | migrations | skip startup `create_all` during `flask db` commands |
