# syntax=docker/dockerfile:1
# Dependency versions come from uv.lock. Record resolved image digests at release.
FROM python:3.15.0-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY . /app
RUN uv sync --frozen --no-dev --extra postgres --no-editable

FROM python:3.15.0-slim AS runtime
RUN groupadd --gid 10001 mdm \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/mdm mdm
COPY --from=builder --chown=10001:10001 /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    DBT_LOG_PATH=/tmp/dbt-logs \
    DBT_TARGET_PATH=/tmp/dbt-target
WORKDIR /app
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()"
CMD ["uvicorn", "mdm.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "32", "--no-access-log", "--timeout-graceful-shutdown", "20"]
