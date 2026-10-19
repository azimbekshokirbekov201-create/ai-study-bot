# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000
WORKDIR /app

COPY requirements.lock ./
# Optional build secret supports managed environments with a trusted HTTPS proxy.
# Ordinary builds use the image's system CA bundle. Verification stays enabled.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    python -m pip install --no-cache-dir --require-hashes -r requirements.lock

RUN groupadd --gid 10001 study && useradd --uid 10001 --gid study --no-create-home study
COPY --chown=study:study app ./app
COPY --chown=study:study scripts ./scripts
COPY --chown=study:study migrations ./migrations
COPY --chown=study:study alembic.ini ./
USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health/ready',timeout=3)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --workers 1 --timeout-graceful-shutdown 90 --no-access-log --no-proxy-headers"]
