# One image for api, worker, worker-heavy, scheduler and bot.
FROM python:3.13-slim-trixie AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# Print toolchain: ImageMagick (threshold), potrace (vectorise), tesseract (text detection),
# ghostscript, cairo (SVG render), fonts.
RUN apt-get update && apt-get install -y --no-install-recommends \
      imagemagick potrace tesseract-ocr tesseract-ocr-eng ghostscript \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      curl ca-certificates tini fonts-dejavu-core zstd \
    && rm -rf /var/lib/apt/lists/*

# Postgres 16 client tools (pg_dump/pg_restore) from the official PostgreSQL apt repo: they must
# match the Postgres 16 server, and Debian trixie only ships version 17.
RUN install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
         https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" \
         > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Chromium for Playwright cover rendering
RUN playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*

COPY . .
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 app && mkdir -p /backups /work && chown -R app /backups /work /app
USER app

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "crayonlark.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

# Dev/test image: includes dev dependencies (pytest, ruff, mypy)
FROM base AS dev
USER root
RUN uv sync --frozen
USER app
