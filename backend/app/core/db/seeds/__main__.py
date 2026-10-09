"""Runner de semillas: `uv run python -m app.core.db.seeds` (desde
`backend/`, con el esquema ya en `alembic upgrade head`). Idempotente."""

import asyncio

from app.core.database import engine
from app.core.db.seeds.result_option_sets import seed_result_option_sets
from app.core.db.seeds.units import seed_units

SEEDS = (seed_units, seed_result_option_sets)


async def main() -> None:
    async with engine.begin() as connection:
        for seed in SEEDS:
            await connection.run_sync(seed)
            print(f"ok: {seed.__name__}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
