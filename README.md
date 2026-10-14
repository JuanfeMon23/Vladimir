# Vladimir

## Requisitos

Python 3.13+, [uv](https://docs.astral.sh/uv/), Node.js con [pnpm](https://pnpm.io/) y PostgreSQL 18 (extensión `unaccent`).

## Ejecutar

1. Crea una base de datos vacía (por ejemplo `vladimir`).
2. Variables de entorno:
   ```bash
   cp backend/.env.example backend/.env      # DATABASE_URL, CORS_ORIGINS
   cp frontend/.env.example frontend/.env    # NUXT_PUBLIC_API_BASE
   ```
3. Backend (`http://localhost:8000`, documentación en `/docs`):
   ```bash
   cd backend
   uv sync
   uv run alembic upgrade head
   uv run python -m app.core.db.seeds
   uv run uvicorn app.main:app --port 8000 --reload
   ```
4. Frontend (`http://localhost:3000`):
   ```bash
   cd frontend
   pnpm install
   pnpm run dev
   ```

Datos de demostración (opcional): `cd backend && uv run python -m app.core.db.seeds.demo --yes`
