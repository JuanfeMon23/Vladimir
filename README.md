# Vladimir

Panel de administración (*admin panel*) para la **gestión de flujos de laboratorio clínico**: personal, áreas, exámenes, muestras, precondiciones, etiquetas, plantillas de resultados y documentos a firmar. Lo que se gestiona aquí **alimenta a otra aplicación** externa (captura de resultados, firma de consentimientos) a través de una API versionada.

> **Estado:** en desarrollo. Aún **no tiene autenticación ni roles**: no la expongas a internet. La exportación del catálogo para la aplicación externa está pendiente.

## Tecnologías

| Parte | Stack |
|---|---|
| `frontend/` | Nuxt 4, Vue 3, TypeScript, Tailwind CSS v4, vee-validate + zod, Vitest |
| `backend/` | Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + asyncpg, Alembic, pytest, ruff |
| Base de datos | PostgreSQL 18 |
| Gestores | `uv` (Python) y `pnpm` (JavaScript; no uses `npm` ni `yarn`) |

## Puesta en marcha

Requisitos: Python 3.13+, [uv](https://docs.astral.sh/uv/), Node.js con [pnpm](https://pnpm.io/) y PostgreSQL 18 (la migración inicial usa `uuidv7()` y la extensión `unaccent`).

1. **Base de datos.** Crea una base vacía (por ejemplo `vladimir`) y un usuario con permisos sobre ella.
2. **Variables de entorno.** Copia los ejemplos y completa los valores. Los `.env` no se versionan y ningún valor de entorno vive en el código.
   ```bash
   cp backend/.env.example backend/.env      # DATABASE_URL, CORS_ORIGINS
   cp frontend/.env.example frontend/.env    # NUXT_PUBLIC_API_BASE
   ```
3. **Backend** (`http://localhost:8000`, documentación interactiva en `/docs`):
   ```bash
   cd backend
   uv sync
   uv run alembic upgrade head
   uv run python -m app.core.db.seeds          # catálogos base: unidades UCUM y conjuntos de opciones
   uv run uvicorn app.main:app --port 8000 --reload
   ```
4. **Frontend** (`http://localhost:3000`):
   ```bash
   cd frontend
   pnpm install
   pnpm run dev
   ```

### Datos de demostración (opcional)

Carga un laboratorio ficticio completo (áreas, exámenes, plantillas con rangos de referencia, etiquetas, consentimientos). El personal es inventado; los valores de referencia y los textos legales son de **referencia** y deben validarse con el laboratorio y el área jurídica antes de cualquier uso real.

```bash
cd backend
uv run python -m app.core.db.seeds.demo --yes            # sobre una base sin datos de negocio
uv run python -m app.core.db.seeds.demo --reset --yes    # VACÍA todas las tablas y repuebla
```

El comando solo corre contra `localhost` y exige `--yes`. `--reset` es destructivo: haz un respaldo antes (`pg_dump`).

## Pruebas y calidad

```bash
cd backend  && uv run pytest -q && uv run ruff check . && uv run ruff format --check .
cd frontend && pnpm exec vitest run && pnpm exec nuxi typecheck
```

Las pruebas del backend usan la base configurada en `backend/.env` dentro de transacciones con *rollback*; la prueba de migraciones crea y elimina una base temporal (necesita el permiso `CREATEDB`).

## Arquitectura

Monorepo con **arquitectura *screaming***: la estructura grita lo que hace el negocio, no el framework. Cada rama se divide en un **núcleo** transversal (sin lógica de negocio) y **módulos de negocio** autocontenidos. Un módulo no usa el código interno de otro: solo su interfaz pública o la API. El mismo nombre de módulo se usa en el frontend (*layer*) y en el backend.

| Módulo (frontend `layers/` · backend `app/modules/`) | Negocio |
|---|---|
| `staff` | Personal |
| `lab_areas` | Áreas del laboratorio y sus encargados (con historial) |
| `lab_tests` | Exámenes: área, muestras, precondiciones, etiqueta, plantilla y documentos |
| `preconditions` | Precondiciones del paciente (jerarquía de un nivel) |
| `samples` | Muestras y tipos de muestra (recipientes) |
| `print_labels` | Diseños de etiqueta versionados |
| `result_templates` | Analitos, unidades (UCUM), conjuntos de opciones, plantillas versionadas y rangos de referencia |
| `consent_documents` | Documentos a firmar versionados, con su PDF en base64 |

Capas del backend: `router → controller → repository → models`. Errores con formato uniforme `{code, message, details}`. La API vive bajo **`/api/v1`** y es el **contrato** con el frontend y con la aplicación externa: romperlo exige una versión nueva.

### Reglas de negocio transversales

- **Nada se elimina, solo se desactiva** (`is_active`). La base de datos rechaza los `DELETE` con triggers, y cada activación o desactivación queda registrada con fecha, hora y motivo (`activity_events`, consulta en `GET /api/v1/activity`).
- **No se crean relaciones con elementos desactivados.** Las existentes se conservan y no se puede publicar una versión que las incluya.
- **Versionado** (borrador → publicada → retirada) en etiquetas, plantillas de resultados y documentos a firmar: un solo borrador a la vez, lo publicado es inmutable y no se retira una versión que usa un examen activo.
- **Todo examen lleva al menos un tipo de muestra**, con exactamente uno preferido.
- **Consentimientos:** un único consentimiento general de tratamiento de datos activo (no se asocia a exámenes) y consentimientos propios de examen (hoy, VIH). Cada versión guarda su PDF y su huella `sha256`.
- Búsqueda `?q=` en los listados, sin distinguir mayúsculas ni tildes.

## Convenciones

- Código, identificadores, commits y nombres de archivo en **inglés**; documentación y textos de interfaz en **español**.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/) y el módulo como *scope*: `feat(lab_tests): ...`, `fix(frontend-core): ...`.
- Configuración solo en `.env` por rama (nunca versionado) y `.env.example` con las claves.
- Antes de crear un componente, utilidad o endpoint nuevo, revisa si ya existe algo reutilizable: `frontend/app/components/ui/CATALOG.md` y `backend/app/core/CATALOG.md`.

## Licencia

Pendiente de definir.
