# The API image: build the virtualenv with uv, then copy only it into a slim runtime.
# docker build -t quiet-camps-api api/

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
# Compile .pyc now, since the runtime can't write them; copy files out of uv's cache, since the
# cache is a mount that isn't in the image.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies only, from the lockfile: this layer is reused until uv.lock changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# Then the project itself, installed into .venv rather than linked to src/.
COPY pyproject.toml uv.lock README.md ./
COPY src src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


FROM python:3.14-slim
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv .venv
# For `alembic upgrade head`, run as a one-off: docker run ... alembic upgrade head
COPY alembic.ini ./
COPY migrations migrations
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PORT=8000
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health', timeout=4)"]
CMD ["sh", "-c", "exec uvicorn quiet_camps.api.app:create_app --factory --host 0.0.0.0 --port $PORT"]
