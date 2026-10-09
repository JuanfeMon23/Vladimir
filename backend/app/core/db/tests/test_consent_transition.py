"""Logica pura (sin BD ni API) de la transicion de documentos a firmar:
calcula el nuevo set de documentos de un examen y es idempotente."""

from app.core.db.seeds.demo.consent_transition import plan_links


def link(version_id: str, *, mandatory: bool = True, active: bool = True) -> dict:
    return {
        "id": f"link-{version_id}",
        "consent_document_version_id": version_id,
        "is_mandatory": mandatory,
        "is_active": active,
    }


def test_quita_las_versiones_indicadas_y_conserva_el_resto():
    links = [link("venop"), link("datos"), link("vih", mandatory=False)]

    plan = plan_links(links, remove={"venop", "datos"})

    assert plan == [{"consent_document_version_id": "vih", "is_mandatory": False}]


def test_reemplaza_una_version_por_otra_conservando_si_es_obligatoria():
    plan = plan_links([link("vih-v1", mandatory=False)], replace={"vih-v1": "vih-v2"})

    assert plan == [{"consent_document_version_id": "vih-v2", "is_mandatory": False}]


def test_sin_nada_que_cambiar_devuelve_none_para_ser_idempotente():
    links = [link("vih-v2")]

    assert plan_links(links, remove={"venop"}, replace={"vih-v1": "vih-v2"}) is None


def test_ignora_los_enlaces_inactivos():
    links = [link("venop", active=False), link("vih-v2")]

    assert plan_links(links, remove={"venop"}) is None


def test_quitar_todo_deja_un_set_vacio_distinto_de_none():
    assert plan_links([link("datos")], remove={"datos"}) == []


def test_reemplazo_que_ya_estaba_enlazado_no_duplica():
    links = [link("vih-v1"), link("vih-v2")]

    plan = plan_links(links, replace={"vih-v1": "vih-v2"})

    assert plan == [{"consent_document_version_id": "vih-v2", "is_mandatory": True}]
