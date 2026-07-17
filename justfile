# rwmod — RimWorld Mod CLI + Web UI

dev:
    start "rwmod-backend" uv run uvicorn rwmod.server:app --host 0.0.0.0 --port 8000 --reload
    cd frontend && npx vite --port 5173

start:
    cd frontend && npx vite build --outDir ../static --emptyOutDir
    uv run uvicorn rwmod.server:app --host 0.0.0.0 --port 8000

build:
    cd frontend && npx vite build --outDir ../static --emptyOutDir

build-check:
    cd frontend && npx tsc --noEmit && npx vite build --outDir ../static --emptyOutDir

download id:
    uv run rwmod download {{id}}

sync:
    uv sync
    cd frontend && npm install

lint:
    uv run ruff check src/rwmod/
    cd frontend && npx tsc --noEmit
