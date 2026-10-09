"""Archivo PDF (base64) de las versiones de documentos a firmar y unicidad
del consentimiento general de tratamiento de datos, sobre el esquema migrado.
"""

from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consent_documents.models import ConsentDocumentVersion

from .conftest import unique_code

HASH = "a" * 64


async def _insert_document(
    session: AsyncSession,
    *,
    document_type: str = "consentimiento_informado",
    is_active: bool = True,
) -> UUID:
    return (
        await session.execute(
            text(
                "INSERT INTO consent_documents "
                "(code, name, document_type, is_active) "
                "VALUES (:code, 'Doc de prueba', :t, :a) RETURNING id"
            ),
            {"code": unique_code("cd"), "t": document_type, "a": is_active},
        )
    ).scalar_one()


async def _insert_version(session: AsyncSession, document_id: UUID, **file) -> None:
    cols = {
        "file_base64": None,
        "file_content_type": None,
        "file_sha256": None,
        "file_size_bytes": None,
    }
    cols.update(file)
    await session.execute(
        text(
            "INSERT INTO consent_document_versions "
            "(consent_document_id, version_number, status, content, signer, "
            "file_base64, file_content_type, file_sha256, file_size_bytes) "
            "VALUES (:d, 1, 'draft', 'texto', 'paciente', "
            ":file_base64, :file_content_type, :file_sha256, :file_size_bytes)"
        ),
        {"d": document_id, **cols},
    )


GOOD = {
    "file_base64": "JVBERi0=",
    "file_content_type": "application/pdf",
    "file_sha256": HASH,
    "file_size_bytes": 5,
}


async def test_version_sin_archivo_es_valida(session: AsyncSession) -> None:
    doc = await _insert_document(session)
    await _insert_version(session, doc)


async def test_version_con_archivo_completo_es_valida(session: AsyncSession) -> None:
    doc = await _insert_document(session)
    await _insert_version(session, doc, **GOOD)


@pytest.mark.parametrize(
    "bad",
    [
        {"file_sha256": "A" * 64},
        {"file_sha256": "a" * 63},
        {"file_sha256": "g" * 64},
        {"file_content_type": "image/png"},
        {"file_size_bytes": 0},
        {"file_size_bytes": -1},
        {"file_base64": None},
        {"file_sha256": None},
        {"file_content_type": None},
        {"file_size_bytes": None},
    ],
)
async def test_archivo_invalido_o_incompleto_se_rechaza(
    session: AsyncSession, bad: dict
) -> None:
    doc = await _insert_document(session)
    with pytest.raises(IntegrityError):
        await _insert_version(session, doc, **{**GOOD, **bad})


async def test_un_solo_campo_de_archivo_se_rechaza(session: AsyncSession) -> None:
    doc = await _insert_document(session)
    with pytest.raises(IntegrityError):
        await _insert_version(session, doc, file_sha256=HASH)


def test_file_base64_es_diferido_en_las_consultas() -> None:
    sql = str(select(ConsentDocumentVersion).compile())
    assert "file_base64" not in sql
    assert "file_sha256" in sql
    assert "content" in sql


def test_file_base64_se_incluye_con_undefer() -> None:
    from sqlalchemy.orm import undefer

    stmt = select(ConsentDocumentVersion).options(
        undefer(ConsentDocumentVersion.file_base64)
    )
    assert "file_base64" in str(stmt.compile())


# --- a lo sumo un documento activo de tratamiento de datos ---
# El dataset de desarrollo ya tiene uno activo: los tests lo desactivan dentro
# de la transaccion que se revierte.


async def _deactivate_existing(session: AsyncSession) -> None:
    await session.execute(
        text(
            "UPDATE consent_documents SET is_active = false "
            "WHERE document_type = 'tratamiento_datos'"
        )
    )


async def test_segundo_documento_activo_de_tratamiento_de_datos_se_rechaza(
    session: AsyncSession,
) -> None:
    await _deactivate_existing(session)
    await _insert_document(session, document_type="tratamiento_datos")
    with pytest.raises(IntegrityError):
        await _insert_document(session, document_type="tratamiento_datos")


async def test_documento_inactivo_o_de_otro_tipo_se_permite(
    session: AsyncSession,
) -> None:
    await _deactivate_existing(session)
    await _insert_document(session, document_type="tratamiento_datos")
    await _insert_document(session, document_type="tratamiento_datos", is_active=False)
    await _insert_document(session, document_type="consentimiento_informado")
    await _insert_document(session, document_type="consentimiento_informado")
    await _insert_document(session, document_type="otro")


async def test_reactivar_con_otro_activo_se_rechaza(session: AsyncSession) -> None:
    await _deactivate_existing(session)
    await _insert_document(session, document_type="tratamiento_datos")
    inactive = await _insert_document(
        session, document_type="tratamiento_datos", is_active=False
    )
    with pytest.raises(IntegrityError):
        await session.execute(
            text("UPDATE consent_documents SET is_active = true WHERE id = :i"),
            {"i": inactive},
        )
