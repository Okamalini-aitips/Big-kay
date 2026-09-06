# OkaMoney AI Tips — Deployment Guide (Full-Stack WEB App)

This project is a **full-stack WEB application** — it is **NOT** an Expo / React Native
mobile app. Deploy it using an Emergent **Full Stack App** workspace (Web / Kubernetes
template), never a Mobile / Expo template.

- **Backend:** FastAPI (`/app/backend`) — runs on `0.0.0.0:8001`, all routes under `/api`
- **Frontend:** React + Vite SPA (`/app/web-frontend`) — build output served as static files
- **Database:** MongoDB (accessed via `MONGO_URL`)

---

## Why a Full Stack workspace is required

Earlier deploys of this app failed inside the Expo **EAS** build lane with
`ERROR: No app.json, app.config.js, or app.config.ts found!` because the workspace was
provisioned on a mobile (Expo) base image while the source is a Vite web app. See
`deployer-agent-docs/` for the root-cause analyses. The fix is a **template change**:
run the app in a Full Stack App workspace, which uses the correct Web/Kubernetes
deployment pipeline.

---

## Migration steps (from a mobile workspace)

1. **Save to GitHub** — use the "Save to GitHub" button in the Emergent chat input.
2. **Create a new Full Stack App workspace** — pick the E1 / E1.5 agent, **not** Mobile/Expo.
3. **Import from GitHub** into the new workspace.
4. **Preview**, verify, then **Deploy**.

---

## Environment variables (set these in the deploy env panel)

Secrets are intentionally **not** committed to git. Configure them in the new workspace:

### Backend (`backend/.env`)
| Variable            | Required | Notes |
|---------------------|----------|-------|
| `MONGO_URL`         | Yes      | Provided automatically by the platform. Do not hardcode. |
| `DB_NAME`           | Yes      | e.g. `okamoney` (or `test_database`). |
| `ADMIN_SECRET_KEY`  | No       | Guards admin endpoints. Defaults to `okamoney_admin_2024` if unset. |
| `API_FOOTBALL_KEY`  | No       | API-Sports key. If absent/suspended, app uses generated data. |
| `API_FOOTBALL_HOST` | No       | e.g. `v3.football.api-sports.io`. |

### Frontend
No frontend URL env var is needed. The SPA calls the backend using the **relative**
path `/api`, which the reverse proxy routes to the backend. Do not add
`EXPO_PUBLIC_*` variables — this is a web app.

---

## How it is served

| Concern            | Configuration |
|--------------------|---------------|
| Frontend dir       | `web-frontend` |
| Build command      | `yarn install && yarn build` |
| Build output       | `web-frontend/dist` |
| Backend command    | `uvicorn server:app --host 0.0.0.0 --port 8001` |
| API proxy          | `/api` → `localhost:8001` |
| SPA fallback       | serve `index.html` for unknown routes (React Router) |
| Health check       | `GET /api/health` and `GET /health` → `{"status":"healthy"}` |

These are declared in `emergent.toml`. A standalone `nginx.conf` + `start.sh` are also
included as a reference production setup (static `web-frontend/dist` on port 3000 with an
`/api/` proxy to `:8001`).

---

## App routes (for post-deploy smoke test)

Public:
- `/` → redirects to `/games`
- `/games` — daily predictions (3 free, rest gated)
- `/build-a-bet` — Same Game Parlay betslips
- `/mixed-markets` — multi-game parlays
- `/ticket-machine` — custom betslip builder
- `/settings`
- `/login`, `/register`

Admin (append `?key=<ADMIN_SECRET_KEY>` where required):
- `/admin/cards?key=okamoney_admin_2024`
- `/admin/results?key=okamoney_admin_2024`
- `/admin/verify`
- `/admin/whatsapp-tickets`

Quick backend check after deploy:
```bash
curl -s https://<your-domain>/api/health
curl -s "https://<your-domain>/api/games?limit=3"
```

---

## Notes
- Betting data is currently **generated/mock** (the API-Sports account was suspended).
  Set a valid `API_FOOTBALL_KEY` to switch to live data.
- `frontend/` in this repo contains only a small launcher shim used by the preview
  environment; the real frontend is `web-frontend/`.
