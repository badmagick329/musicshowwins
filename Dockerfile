# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.12.3 AS uv

FROM python:3.13-slim-bookworm AS python-builder
COPY --from=uv /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev --no-install-project
COPY manage.py ./
COPY musicshowwins ./musicshowwins
ENV PATH="/opt/venv/bin:${PATH}"
RUN DEBUG=0 \
    SECRET_KEY=build-only-static-collection-secret \
    ALLOWED_HOSTS=localhost \
    CSRF_TRUSTED_ORIGINS=https://localhost \
    python manage.py collectstatic --noinput

FROM node:24-bookworm-slim AS frontend-builder
RUN npm install --global pnpm@11.6.0
WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend ./
RUN pnpm build
RUN swc_source="$(find node_modules/.pnpm -path '*/node_modules/@swc/helpers' -type d -print -quit)" \
    && swc_target="$(find .next/standalone/node_modules/.pnpm -path '*/node_modules/@swc/helpers' -type d -print -quit)" \
    && test -n "${swc_source}" \
    && test -n "${swc_target}" \
    && cp -aL "${swc_source}/." "${swc_target}/"

FROM python:3.13-slim-bookworm AS runtime
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node
RUN groupadd --system --gid 10001 kpopwins \
    && useradd --system --uid 10001 --gid kpopwins --home-dir /app kpopwins \
    && install --directory --owner=kpopwins --group=kpopwins --mode=0755 /app
WORKDIR /app
COPY --from=python-builder --chown=kpopwins:kpopwins /opt/venv /opt/venv
COPY --from=python-builder --chown=kpopwins:kpopwins /build/manage.py ./manage.py
COPY --from=python-builder --chown=kpopwins:kpopwins /build/musicshowwins ./musicshowwins
COPY --from=frontend-builder --chown=kpopwins:kpopwins /build/frontend/.next/standalone ./frontend
COPY --from=frontend-builder --chown=kpopwins:kpopwins /build/frontend/.next/static ./frontend/.next/static
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app/musicshowwins \
    NODE_ENV=production \
    HOSTNAME=0.0.0.0
USER kpopwins
CMD ["node", "/app/frontend/server.js"]
