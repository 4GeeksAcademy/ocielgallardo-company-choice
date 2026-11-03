# Server / network baseline — HealthCore (Hito 29)

Academic hardening for `ai-eng-cybersecurity-vulnerabilities` (BRIEFING §7).  
**No PHI** in evidence. Prefer Codespaces or Ubuntu for SSH/UFW; Windows hosts use Compose controls below.

## Goals (acceptance)

| Control | Evidence |
| --- | --- |
| No direct root SSH login | `PermitRootLogin no` via `scripts/hardening/` |
| Non-root deploy user | `healthcore` (or `DEPLOY_USER`) with sudo |
| Explicit folder permissions | `/opt/healthcore/{app,logs,secrets,config}` modes 750/750/700/750 |
| Firewall with minimal ports | UFW: 22, 80, 443 only |
| Clinical APIs / dashboards not exposing DB/queues/admin | Compose: Redis, Qdrant, Flower **not** published on the host |

## Linux / Codespaces (host)

```bash
# On Ubuntu or Codespaces (as root)
sudo bash scripts/hardening/harden-linux-baseline.sh
sudo bash scripts/hardening/verify-baseline.sh
```

Optional:

```bash
DEPLOY_USER=myuser HEALTHCORE_ROOT=/opt/healthcore sudo -E bash scripts/hardening/harden-linux-baseline.sh
```

### Folder separation (code / logs / secrets)

Created by `harden-linux-baseline.sh` under `HEALTHCORE_ROOT` (default `/opt/healthcore`):

| Path | Purpose | Mode | Owner |
| --- | --- | --- | --- |
| `app/` | Application code / deploy checkout | `750` | deploy user |
| `logs/` | Runtime / operational logs | `750` | deploy user |
| `secrets/` | `.env`, PEM keys, TinyDB auth stores | `700` | deploy user (owner-only) |
| `config/` | Non-secret templates / static config | `750` | deploy user |

**Compose mapping:** keep the monorepo (or release tarball) under `app/`; place host `.env` and `data/process/auth/*` under `secrets/` (never world-readable); write container/host logs into `logs/`.

Verify modes with `verify-baseline.sh` (`stat` checks for `750` / `700`).

### Windows workstation limitation

`harden-linux-baseline.sh` / `verify-baseline.sh` **exit on non-Linux**. Capture SSH/UFW/folder evidence from Codespaces; keep Compose port lockdown as the in-repo, locally verifiable control on Windows.

## Compose / image mapping (in-repo firewall)

| Service | Host ports (prod compose) | Rationale |
| --- | --- | --- |
| website / backoffice | 3000, 3001 | Staff / public UI |
| backend API | 8000 | Clinical/staff API (front with TLS at edge in real deploy) |
| MCP | 8100 | OAuth-protected tools |
| redis | **none** (internal only) | Broker — not public |
| qdrant | **none** (internal only) | Vector DB — not public |
| flower | **none** (internal only) | Celery admin — not public |
| worker | none | Background only |

Verify:

```bash
docker compose config | rg -n "published|6379|6333|5555" || true
```

Expect **no** host publish for 6379 / 6333 / 6334 / 5555.

## Container non-root

`services/Dockerfile.prod` and `uis/Dockerfile.prod` run as user `app` (uid 10001), not root.

## API docs in production

Set `APP_ENV=production` or `DISABLE_API_DOCS=true` so FastAPI disables `/docs`, `/redoc`, and `/openapi.json`.

## Secrets / TLS (A02 notes)

- LLM and DB secrets only via `.env` / `*_FILE` (gitignored); never bake `data/process/auth/*.pem` or `auth.json` into images (see root `.dockerignore`).
- Production edge should terminate HTTPS (Caddy/nginx) in front of 3000/3001/8000/8100; set `SUPABASE_DB_SSLMODE=require` for the database.
- Vendor LLM keys require a signed BAA (US) / DPA (UK) before production PHI workloads — process control, documented here, not enforced in code.

## Related env flags (app)

| Variable | Purpose |
| --- | --- |
| `APP_ENV=production` | Disables OpenAPI docs; tightens telemetry ingest |
| `DISABLE_API_DOCS=true` | Force-disable docs regardless of `APP_ENV` |
| `ALLOW_PUBLIC_REGISTRATION=false` | Close open signup in production |
| `TELEMETRY_INGEST_KEY` | Shared secret for `POST /telemetry/events` (`X-Telemetry-Ingest-Key`) |
| `RFP_*_OWNER_EMAIL` | Department approver emails for RFP HITL |
