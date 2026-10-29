# AGENTS.md

Instructions for AI coding agents (and humans) working in this repository.
Read this fully before changing anything. The setup looks simple, but several
pieces depend on each other and break quietly when one is changed in isolation.

## What this project is

- `fastapi-backend/` — FastAPI app. Entry point `app/main.py`. Tests in `tests/`.
- `next-frontend/salmon/` — Next.js 15 (App Router, Tailwind 3, TypeScript).
- `nginx/default.conf` — the gateway config.
- `docker-compose.yml` — runs everything. See `README.md` for how to use it.

**Architecture in one line:** the browser talks only to nginx; nginx proxies
`/api/*` to the backend and everything else to the frontend; the frontend and
backend sit on a private Docker network that has no host ports and no internet.

## Hard rules (do not break these)

### 1. Keep the services private

- **Never add `ports:` to `frontend` or `backend`** in `docker-compose.yml`.
  Not for debugging, not "temporarily". Use `docker compose exec` or
  `docker compose logs` instead. Use `expose:` only.
- **Never put `frontend` or `backend` on the `edge` network**, and never remove
  `internal: true` from the `private` network. That flag is what stops them
  from reaching the internet.
- **nginx is the only service allowed to publish a port**, and it publishes
  exactly one (`8080` inside the container).
- If a service needs outbound internet at runtime, stop and ask the user. Do
  not weaken the network to make it work.

### 2. Keep the nginx / FastAPI `/api` prefix contract in sync

Three places work together and must change together:

| Where | What it does |
|---|---|
| `nginx/default.conf` `location /api/` + `proxy_pass http://backend/;` | The **trailing slash** on `proxy_pass` strips `/api/`. Remove it and every API call 404s. |
| `fastapi-backend/Dockerfile` `--root-path /api` | Only makes docs/OpenAPI links point at `/api/...`. Routes themselves stay at `/` and `/items/...`. |
| Backend routes in `app/main.py` | Must NOT include an `/api` prefix themselves. |

### 3. Keep the container hardening

Every service uses `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges`,
and runs as a non-root user. Do not remove these to fix an error. If something
needs to write, add a `tmpfs:` mount for that specific path (as done for
`/tmp` and `/app/.next/cache`). Do not make the filesystem writable.

### 4. Keep the Next.js standalone output

`next.config.ts` sets `output: "standalone"`. The frontend Dockerfile copies
`.next/standalone` and `.next/static` and runs `node server.js`. Removing it
breaks the image. If you add files the server reads at runtime (e.g. `public/`
assets), make sure the Dockerfile still copies them.

### 5. Do not break health checks

nginx starts only after `frontend` and `backend` are healthy
(`depends_on: condition: service_healthy`). The backend check requests `/` and
expects `200`; the frontend check requests `/` and expects a successful
response. If you change those routes or ports, update the healthchecks in
`docker-compose.yml`, or the stack will hang at startup.

### 6. Ports are coupled across files

| Port | Appears in |
|---|---|
| Backend `8000` | `fastapi-backend/Dockerfile` (`--port`, `EXPOSE`), `docker-compose.yml` (`expose`, healthcheck), `nginx/default.conf` (`upstream backend`) |
| Frontend `3000` | `next-frontend/salmon/Dockerfile` (`PORT`, `EXPOSE`), `docker-compose.yml` (`expose`, healthcheck), `nginx/default.conf` (`upstream frontend`) |
| nginx `8080` | `nginx/default.conf` (`listen`), `docker-compose.yml` (port mapping, healthcheck) |

Change one, change all of them. The nginx image is `nginx-unprivileged`, which
cannot bind ports below 1024, so do not switch the listen port to 80.

### 7. Secrets and generated files

- Never commit `.env` or any real credentials. `.env.example` is the only env
  file that is tracked (the `!.env.example` line in `.gitignore` is
  intentional; do not remove it).
- Do not commit `__pycache__/`, `.venv/`, `node_modules/` or `.next/`.
- Keep the committed `package-lock.json` in sync with `package.json`. Use
  `npm ci` to install and `npm install <pkg>` to change dependencies. The
  Docker build runs `npm ci` and fails if they disagree.

## Conventions

- **Backend:** keep input validation on endpoints (`Path`/`Query` constraints).
  Handlers are `async def` and must not do blocking I/O. If you need blocking
  work, use a plain `def` handler or run it in a thread pool.
- **CORS:** origins come from the `CORS_ORIGINS` env var. Do not hardcode `*`
  or add `allow_credentials=True` with broad origins.
- **Frontend:** the browser should call the API at the relative path `/api/...`
  (same origin through nginx). Do not hardcode `localhost:8000` into frontend
  code. Server-side code inside the frontend container reaches the backend at
  `http://backend:8000`.
- **nginx:** there is intentionally no Content-Security-Policy yet, because
  Next.js emits inline scripts. Adding a CSP means doing it properly with
  nonces; do not add a strict one blindly.
- **Dependencies:** `npm audit` currently reports 2 known issues that can only
  be cleared by upgrading Next.js to 16 (a major version). Do not run
  `npm audit fix --force` to chase that; propose the upgrade to the user
  instead.
- Keep changes small and focused. Update `README.md` when behavior, ports,
  variables or commands change.

## How to verify your changes

Run what applies before telling the user the work is done. Do not claim a check
passed unless you ran it and saw it pass.

**Always (no Docker needed):**

```bash
# Backend tests
cd fastapi-backend && pip install -r requirements-dev.txt && pytest

# Frontend lint + types
cd next-frontend/salmon && npm ci && npm run lint && npx tsc --noEmit
```

**Compose file** (works without a Docker daemon):

```bash
docker compose config            # must print the resolved config without errors
```

Then confirm that only `nginx` has a published port in that output.

**Full stack** (needs a Docker daemon and internet for the first build):

```bash
docker compose up --build -d
docker compose ps                                  # all services healthy; only nginx has a port mapping
curl -s localhost:8080/api/                        # {"Hello":"World"}
curl -s localhost:8080/api/items/5?q=hi            # {"item_id":5,"q":"hi"}
curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/          # 200
curl --max-time 3 localhost:3000; curl --max-time 3 localhost:8000   # both must FAIL
docker compose down
```

If you could not run the full stack (for example, no Docker daemon available),
say so plainly in your summary and list which checks you did and did not run.

## Known limitations

- `next/font/google` downloads the Geist fonts at **build** time, so
  `docker compose build` needs internet access. The running containers do not.
- `npm run lint` uses `next lint`, which is deprecated and removed in Next 16.
  `npx eslint .` also works and is the replacement.
- nginx serves HTTP only; TLS is expected to be terminated in front of it.
- The frontend is still the create-next-app starter page, and the backend has
  only the two starter endpoints.

## Git

- Work on a branch; do not push directly to `master`.
- Write clear commit messages explaining what changed and why.
- Do not rewrite or force-push shared history unless the user asks.
- Do not change the git author or committer identity configured for the user.
