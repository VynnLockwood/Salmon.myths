# Salmon Myths

A Next.js frontend and a FastAPI backend, run with Docker Compose behind an
nginx gateway. nginx is the only thing exposed to your machine; the app
containers are on a private network and cannot be reached directly.

```
                 host
                   │  only published port (default 8080)
          ┌────────▼────────┐
          │      nginx      │   "edge" network    → reachable from the host
          └───┬─────────┬───┘
   /api/* ────┘         └──── everything else
 ┌──────────▼──┐     ┌────▼─────────┐
 │   backend   │     │   frontend   │   "private" network (internal: true)
 │ FastAPI:8000│     │ Next.js:3000 │   → no host ports, no outbound internet
 └─────────────┘     └──────────────┘
```

| Path | What it is |
|---|---|
| `docker-compose.yml` | The whole stack: services, networks, hardening |
| `nginx/default.conf` | Gateway: routing, rate limits, security headers |
| `fastapi-backend/` | FastAPI app (`app/main.py`), tests, Dockerfile |
| `next-frontend/salmon/` | Next.js app (App Router + Tailwind), Dockerfile |
| `.env.example` | Settings you can override |
| `AGENTS.md` | Rules for AI coding agents working in this repo |

## Quick start

**Requirements:** Docker with the Compose plugin (`docker compose version`
should work) and an internet connection for the first build.

```bash
git clone https://github.com/VynnLockwood/Salmon.myths.git
cd Salmon.myths

cp .env.example .env          # optional; the defaults work
docker compose up --build     # add -d to run in the background
```

Then open:

| URL | What you get |
|---|---|
| http://localhost:8080/ | The Next.js frontend |
| http://localhost:8080/api/ | The API (`{"Hello":"World"}`) |
| http://localhost:8080/api/items/5?q=hi | Example endpoint |
| http://localhost:8080/api/docs | Interactive API docs |
| http://localhost:8080/healthz | Gateway liveness check |

The first build takes a few minutes. The first start waits for the frontend and
backend to report healthy before nginx comes up, so give it ~15 seconds.

### Everyday commands

```bash
docker compose up --build -d     # build and start in the background
docker compose ps                # status and health of each service
docker compose logs -f nginx     # follow one service's logs (or: backend, frontend)
docker compose restart backend   # restart one service
docker compose down              # stop and remove containers and networks
docker compose build --no-cache  # rebuild images from scratch
```

After changing code you must rebuild (`docker compose up --build`). The
containers run production builds and do not hot-reload. For live reload, see
[Develop without Docker](#develop-without-docker).

## Configuration

Set these in `.env` (copied from `.env.example`) or in your shell:

| Variable | Default | Purpose |
|---|---|---|
| `HTTP_PORT` | `8080` | Host port nginx listens on |
| `BIND_ADDR` | `0.0.0.0` | Interface to bind. `127.0.0.1` = reachable from this machine only |
| `CORS_ORIGINS` | `http://localhost:8080` | Comma-separated browser origins the API accepts. Match your public URL |

Changing `HTTP_PORT`? Update `CORS_ORIGINS` to match, e.g. `HTTP_PORT=9000` and
`CORS_ORIGINS=http://localhost:9000`.

## Check that it is really private

Only nginx should be published:

```bash
docker compose ps
```

`nginx` shows a `0.0.0.0:8080->8080/tcp` mapping; `frontend` and `backend` show
none. Direct access must fail:

```bash
curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/healthz   # 200
curl --max-time 3 localhost:3000                                  # fails: connection refused
curl --max-time 3 localhost:8000                                  # fails: connection refused
```

### What makes it private

- `frontend` and `backend` have no `ports:` entry, so nothing on the host
  listens for them. They only `expose` their port to other containers.
- They are attached only to a Docker network with `internal: true`: just nginx
  can reach them, and they have no outbound internet access.
- nginx is on both networks. It is the single entry point and applies request
  rate limits, security headers and gzip.
- Every container runs as a non-root user with a read-only filesystem, all
  Linux capabilities dropped, and `no-new-privileges`.

## Develop without Docker

Handy for fast feedback with hot reload. Needs Python 3.13 and Node 22.

**Backend** (http://localhost:8000):

```bash
cd fastapi-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest                           # run the tests
```

**Frontend** (http://localhost:3000):

```bash
cd next-frontend/salmon
npm ci
npm run dev
npm run lint
npx tsc --noEmit                 # typecheck
```

Without nginx there is no `/api` prefix: the backend is at
`http://localhost:8000/` and its docs at `/docs`. The backend allows
`http://localhost:3000` by default for browser calls.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/` | `{"Hello": "World"}` |
| GET | `/items/{item_id}` | `item_id` must be an integer from 1 to 2147483647. Optional `q` (max 100 characters). Invalid input returns `422`. |

Through the gateway, prefix these with `/api`.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Build fails fetching `Geist` / Google Fonts | The frontend build downloads fonts from Google. Allow outbound access to `fonts.googleapis.com` while building. Running the containers needs no internet. |
| `port is already allocated` / `address already in use` | Something else uses 8080. Set `HTTP_PORT=8081` (and `CORS_ORIGINS`) in `.env`. |
| nginx never starts / stays "waiting" | It waits for healthy backend and frontend. Run `docker compose ps` and `docker compose logs backend frontend`. |
| `502 Bad Gateway` | An upstream is down or restarting. Check `docker compose ps` and the logs of `backend` / `frontend`. |
| `429 Too Many Requests` | The nginx rate limit (about 50 req/s for pages, 20 req/s for `/api`, per client IP). |
| Browser CORS error calling the API | The page's origin is not in `CORS_ORIGINS`. |
| Code changes not showing up | Rebuild: `docker compose up --build`. |

## TLS

nginx serves plain HTTP. For production, terminate TLS in front of it (a cloud
load balancer, Caddy or Traefik), or add an HTTPS `server` block with your
certificates to `nginx/default.conf`.

## Contributing / AI agents

Read [`AGENTS.md`](AGENTS.md) before changing the Docker, nginx or networking
setup. It lists the rules that keep the stack private and working.
