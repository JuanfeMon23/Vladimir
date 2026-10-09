"""Semillas de datos por modulo: idempotentes (insertan solo los `code` que
faltan, nunca pisan lo que el laboratorio edito) y separadas de las
migraciones.

Cada semilla recibe una `Connection` sincronica de SQLAlchemy (sirve igual
desde `op.get_bind()`, desde `AsyncSession.run_sync` o desde el runner
`uv run python -m app.core.db.seeds`) y usa tablas ligeras (`sa.table`) en
vez de los modelos, para no romperse si el modelo gana columnas despues.
"""
