FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Run as an unprivileged user.
RUN useradd --system --uid 10001 --no-create-home app
USER 10001

EXPOSE 8000

# nginx strips the /api prefix before proxying; --root-path only makes the
# generated docs/OpenAPI links point at /api/... again.
# This container is reachable only from the private network (nginx), so trusting
# its forwarded headers is safe.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--root-path", "/api", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
