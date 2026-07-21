# ============================================================
# rwmod — Self-contained RimWorld Mod Manager
# Multi-stage build: Python backend + Vite frontend + SteamCMD
# ============================================================

# ── Stage 1: Frontend build (Node) ──────────────────────────
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock* ./
RUN npm install
COPY frontend/ ./
RUN npx vite build --outDir /app/static

# ── Stage 2: Python dependencies ────────────────────────────
FROM python:3.13-slim AS python-deps
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install \
    "typer>=0.25" "fastapi>=0.100" "uvicorn[standard]>=0.30" \
    "python-multipart>=0.0.9" "websockets>=14"

# ── Stage 3: Runtime ────────────────────────────────────────
FROM python:3.13-slim
WORKDIR /app

# Create non-root user
RUN groupadd -r rwmod -g 1001 && \
    useradd -r -g rwmod -u 1001 rwmod

# Copy Python deps from builder
COPY --from=python-deps /install /usr/local

# Copy source
COPY pyproject.toml ./
COPY src/ ./src/

# Copy frontend build
COPY --from=frontend-builder /app/static ./static/

# Copy built-in SteamCMD (user populates this)
# docker run -v ./steamcmd:/app/steamcmd ...
VOLUME ["/app/steamcmd", "/app/mods"]

# Switch to non-root
USER rwmod

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/config')" || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "rwmod.server:app", "--host", "0.0.0.0", "--port", "8000"]
