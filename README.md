# Salmon Myths

Next.js frontend + FastAPI backend, run with Docker Compose behind an nginx gateway.

```
                 host
                   │  only published port (default 8080)
          ┌────────▼────────┐
          │      nginx      │   edge network  → reachable from the host
          └───┬─────────┬───┘
   /api/* ────┘         └──── everything else
 ┌──────────▼──┐     ┌────▼─────────┐
 │   backend   │     │   frontend   │   private network (internal: true)
 │ FastAPI:8000│     │ Next.js:3000 │   → no host ports, no outbound internet
 └─────────────┘     └──────────────┘
```

## Run

```bash
cp .env.example .env      # optional; defaults work
docker compose up --build
```

Open http://localhost:8080 (frontend) or http://localhost:8080/api/ (API,
docs at `/api/docs`).

The frontend image build downloads the Geist fonts from Google Fonts, so
`docker compose build` needs internet access. Running the containers does not.

## What is private

- `frontend` and `backend` have **no `ports:`** mapping, so nothing on the host
  listens for them. They only `expose` ports to other containers.
- They sit on a Docker network with `internal: true`: only nginx can reach them,
  and they cannot make outbound connections.
- nginx is the single entry point. It rate-limits, adds security headers, and
  proxies `/api/*` to the backend (prefix stripped) and everything else to the
  frontend.
- All containers run as non-root with a read-only filesystem, all Linux
  capabilities dropped, and `no-new-privileges`.

To verify from the host: `docker compose ps` should show a published port only
for `nginx`, and `curl localhost:3000` / `curl localhost:8000` should fail.

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `HTTP_PORT` | `8080` | Host port for nginx |
| `BIND_ADDR` | `0.0.0.0` | Interface to bind (`127.0.0.1` = local only) |
| `CORS_ORIGINS` | `http://localhost:8080` | Browser origins the API accepts |

## Local development without Docker

```bash
# backend
cd fastapi-backend && pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000
pytest

# frontend
cd next-frontend/salmon && npm ci && npm run dev   # http://localhost:3000
```

## TLS

nginx here serves plain HTTP. For production, terminate TLS in front of it
(a cloud load balancer, Caddy/Traefik, or add a `listen 8443 ssl` server block
with your certificates).
