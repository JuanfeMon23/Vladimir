"""Comando: `uv run python -m app.core.db.seeds.demo [--reset] --yes`."""

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.db.seeds.demo import (
    consent_documents,
    deactivations,
    lab_areas,
    lab_tests,
    preconditions,
    print_labels,
    result_templates,
    samples,
    staff,
)
from app.core.db.seeds.demo.client import DemoApiError, open_api
from app.core.db.seeds.demo.guard import (
    GuardError,
    check_empty,
    check_target,
    describe_target,
)
from app.core.db.seeds.demo.registry import Registry
from app.core.db.seeds.demo.reset import (
    SEEDED_CATALOGS,
    business_tables,
    reset,
    row_counts,
    seed_catalogs,
)
from app.core.db.seeds.demo.verify import verify

# Orden de carga: cada modulo depende de los anteriores.
LOADERS = (
    staff,
    lab_areas,
    samples,
    preconditions,
    print_labels,
    consent_documents,
    result_templates,
    lab_tests,
    deactivations,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.core.db.seeds.demo",
        description="Puebla la BD de desarrollo con datos de demostración.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="vacía TODAS las tablas (TRUNCATE) antes de poblar",
    )
    parser.add_argument(
        "--yes", action="store_true", help="confirma la operación (obligatorio)"
    )
    return parser.parse_args(argv)


def format_counts(counts: dict[str, int]) -> str:
    width = max(len(table) for table in counts)
    return "\n".join(f"  {table:<{width}}  {n:>6}" for table, n in counts.items())


async def run(args: argparse.Namespace) -> None:
    from app.core.database import engine

    database_url = get_settings().database_url
    check_target(database_url, yes=args.yes)
    print(f"Destino: {describe_target(database_url)}")

    tables = business_tables()
    try:
        async with engine.begin() as connection:
            if args.reset:
                await connection.run_sync(reset)
                print("Tablas vaciadas y semillas de catálogo recargadas.")
            else:
                counts = await connection.run_sync(row_counts, tables)
                check_empty(
                    {t: n for t, n in counts.items() if t not in SEEDED_CATALOGS}
                )
                await connection.run_sync(seed_catalogs)

        registry = Registry()
        async with open_api() as api:
            for loader in LOADERS:
                await loader.load(api, registry)
                print(f"ok: {loader.__name__.rsplit('.', 1)[-1]}")
            problems = await verify(api, registry)

        async with engine.connect() as connection:
            counts = await connection.run_sync(row_counts, tables)
        print("Filas por tabla:\n" + format_counts(counts))
        if problems:
            print("PROBLEMAS DE INTEGRIDAD:")
            for problem in problems:
                print(f"  - {problem}")
            raise SystemExit(1)
        print("Integridad verificada: sin problemas.")
    except DemoApiError as error:
        print(f"La API rechazó un dato de la demostración:\n  {error}", file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):  # consola de Windows (cp1252)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        asyncio.run(run(parse_args(argv)))
    except GuardError as error:
        print(error, file=sys.stderr)
        raise SystemExit(error.code) from error


if __name__ == "__main__":
    main()
