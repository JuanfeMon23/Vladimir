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

## Tags de permisos (backend ↔ frontend)

El contrato `frontend/app/generated/permissions.json` se genera desde el backend y se commitea. Al agregar, quitar o renombrar un módulo o acción en cualquier `permissions.py`, regenéralo y commitéalo:

```bash
cd backend
uv run python -m app.core.permissions_export          # regenera el JSON
uv run python -m app.core.permissions_export --check  # sale con 1 si está desalineado
```

Un test del backend falla si el JSON está desactualizado y uno del frontend falla si el código usa un tag inexistente o si un tag asignable no se usa.

Datos de demostración (opcional): `cd backend && uv run python -m app.core.db.seeds.demo --yes`

## Producción (backend)

- **Roles de BD de mínimo privilegio** (`vladimir_migrator` para Alembic, `vladimir_app` para la API). Requiere un superusuario de PostgreSQL:
  ```bash
  cd backend
  psql -d vladimir -v ON_ERROR_STOP=1 -f deploy/db_roles.sql   # crea los roles (sin contraseña)
  psql -d vladimir -c "\password vladimir_migrator"            # fija las contraseñas
  psql -d vladimir -c "\password vladimir_app"
  # .env: MIGRATION_DATABASE_URL con vladimir_migrator, DATABASE_URL con vladimir_app
  uv run alembic upgrade head                                  # corre como vladimir_migrator
  psql -d vladimir -v ON_ERROR_STOP=1 -f deploy/db_roles.sql   # re-aplicar tras cada migración que agregue tablas
  ```
  `vladimir_app` no puede borrar filas ni hacer DDL; `activity_events` y `settings_history` son de solo lectura/inserción. Los seeds de demostración (`seeds.demo`, que borra datos) deben correr con un rol administrador, no con `vladimir_app`.
