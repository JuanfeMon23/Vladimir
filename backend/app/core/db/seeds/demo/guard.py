"""Guardas de seguridad del comando de datos de demostracion.

El comando vacia tablas (`TRUNCATE`), asi que solo corre contra una BD local
y con confirmacion explicita. Funciones puras (sin BD) para poder probarlas.
"""

from sqlalchemy.engine import URL, make_url

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class GuardError(SystemExit):
    """El comando se niega a continuar (codigo de salida 2)."""

    def __init__(self, message: str) -> None:
        super().__init__(f"ABORTADO: {message}")
        self.code = 2


def describe_target(database_url: str) -> str:
    """`host:puerto/base` (sin credenciales) para mostrar a quien lo ejecuta."""
    url = make_url(database_url)
    return f"{url.host}:{url.port or 5432}/{url.database}"


def check_target(
    database_url: str, *, yes: bool, action: str = "vaciaria y repoblaria"
) -> URL:
    """Valida que el destino sea local y que haya confirmacion (`--yes`).

    Devuelve la URL parseada; levanta `GuardError` si algo no cumple.
    """
    url = make_url(database_url)
    if url.host not in LOCAL_HOSTS:
        raise GuardError(
            f"el host de la BD es {url.host!r}; este comando solo corre contra "
            f"{', '.join(sorted(LOCAL_HOSTS))}."
        )
    if not yes:
        raise GuardError(
            f"{action} {describe_target(database_url)}; "
            "repite el comando con --yes para confirmar."
        )
    return url


def check_empty(counts: dict[str, int]) -> None:
    """Sin `--reset` la BD debe estar vacia de datos de negocio."""
    filled = {table: n for table, n in counts.items() if n}
    if filled:
        detail = ", ".join(f"{table}={n}" for table, n in sorted(filled.items()))
        raise GuardError(
            f"la BD ya tiene datos ({detail}); usa --reset para vaciarla y repoblarla."
        )
