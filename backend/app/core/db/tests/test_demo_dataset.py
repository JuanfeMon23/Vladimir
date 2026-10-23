"""Validez estructural del dataset de demostracion, EN MEMORIA (sin BD):
codigos unicos, referencias internas resueltas y las mismas reglas de
plantillas que aplica la API (formulas, campos por tipo de resultado,
rangos sin solaparse), para detectar un dato mal escrito sin necesidad de
correr la carga contra la BD.
"""

import base64
import hashlib
import re
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from app.core.db.seeds.demo import (
    consent_documents,
    consent_files,
    consent_texts,
    deactivations,
    lab_areas,
    lab_tests,
    preconditions,
    print_labels,
    samples,
    staff,
)
from app.core.db.seeds.demo.result_templates import (
    ANALYTES,
    DISCONTINUED_ANALYTE,
    TEMPLATES,
)
from app.core.db.seeds.demo.result_templates.catalogs import (
    EXTRA_OPTION_SETS,
    EXTRA_UNITS,
)
from app.core.db.seeds.result_option_sets import RESULT_OPTION_SETS
from app.core.db.seeds.units import UNITS
from app.modules.consent_documents.files import MIB
from app.modules.consent_documents.models import DOCUMENT_TYPE_VALUES, SIGNER_VALUES
from app.modules.consent_documents.schemas import DATA_TREATMENT_TYPE
from app.modules.preconditions.models import CATEGORY_VALUES, DURATION_UNIT_VALUES
from app.modules.print_labels.models import OUTPUT_FORMAT_VALUES
from app.modules.result_templates.controller import (
    _not_allowed_range_fields,
    _ranges_overlap,
)
from app.modules.result_templates.formula import FormulaNode, formula_problems
from app.modules.result_templates.schemas import reference_range_bound_errors
from app.modules.samples.models import SPECIMEN_VALUES


def _duplicates(values) -> list:
    return [value for value, n in Counter(values).items() if n > 1]


# --- unicidad de codigos ---------------------------------------------------


def test_codigos_unicos_en_cada_catalogo():
    sample_types = [t.code for s in samples.SAMPLES for t in s.types]
    sample_types.append(samples.DISCONTINUED_SAMPLE_TYPE.code)
    preconditions_codes = [p.code for p in preconditions.PRECONDITIONS] + [
        i.code for p in preconditions.PRECONDITIONS for i in p.items
    ]
    groups = {
        "personal": [p.document_number for p in staff.STAFF],
        "áreas": [a.code for a in lab_areas.AREAS],
        "muestras": [s.code for s in samples.SAMPLES],
        "tipos de muestra": sample_types,
        "precondiciones": preconditions_codes,
        "etiquetas": [label.code for label in print_labels.LABELS],
        "documentos": [c.code for c in consent_documents.CONSENTS],
        "analitos": [a.code for a in ANALYTES],
        "plantillas": [t.code for t in TEMPLATES],
        "exámenes": [t.code for t in lab_tests.LAB_TESTS],
        "unidades extra": [u.code for u in EXTRA_UNITS],
        "conjuntos extra": [s.code for s in EXTRA_OPTION_SETS],
    }
    for name, codes in groups.items():
        assert not _duplicates(codes), f"{name}: códigos repetidos {_duplicates(codes)}"


def test_el_dataset_no_pisa_las_semillas_de_catalogo():
    seeded_units = {u.code for u in UNITS}
    assert not seeded_units & {u.code for u in EXTRA_UNITS}
    seeded_sets = {s.code for s in RESULT_OPTION_SETS}
    assert not seeded_sets & {s.code for s in EXTRA_OPTION_SETS}


def test_opciones_unicas_dentro_de_cada_conjunto():
    for option_set in EXTRA_OPTION_SETS:
        codes = [o.code for o in option_set.options]
        assert not _duplicates(codes), option_set.code


# --- personal, areas y muestras -------------------------------------------


def test_personal_inventado_con_correos_ficticios():
    assert len(staff.STAFF) >= 12
    for person in staff.STAFF:
        assert person.email.endswith(".example")
        assert person.document_number.isdigit()


def test_encargados_de_area_existen_y_el_historial_es_coherente():
    documents = {p.document_number for p in staff.STAFF}
    now = datetime.now(UTC)
    with_history = 0
    for area in lab_areas.AREAS:
        assert area.manager in documents, area.code
        if area.previous_manager is not None:
            with_history += 1
            assert area.previous_manager in documents
            assert area.previous_manager != area.manager
            assert area.previous_start is not None and area.previous_start < now
    assert with_history >= 2


def test_tipos_de_muestra_con_enums_validos():
    all_types = [t for s in samples.SAMPLES for t in s.types]
    all_types.append(samples.DISCONTINUED_SAMPLE_TYPE)
    for sample_type in all_types:
        assert sample_type.specimen in SPECIMEN_VALUES, sample_type.code
        if sample_type.cap_color_hex is not None:
            assert re.fullmatch(r"#[0-9A-F]{6}", sample_type.cap_color_hex)


def test_precondiciones_con_enums_validos_y_unidad_junto_a_la_duracion():
    for root in preconditions.PRECONDITIONS:
        for node in (root, *root.items):
            assert node.category in CATEGORY_VALUES, node.code
            assert (node.duration_value is None) == (node.duration_unit is None), (
                node.code
            )
            if node.duration_unit is not None:
                assert node.duration_unit in DURATION_UNIT_VALUES, node.code


# --- etiquetas y documentos ------------------------------------------------


def test_etiquetas_declaran_los_placeholders_que_usan():
    for label in print_labels.LABELS:
        assert label.output_format in OUTPUT_FORMAT_VALUES
        used = set(re.findall(r"\{\{(\w+)\}\}", label.template_content))
        assert used == set(label.placeholders), label.code
        assert set(label.placeholders) <= set(print_labels.PLACEHOLDERS)
        assert label.copies >= 1 and label.dpi > 0


def test_documentos_a_firmar_con_enums_validos_y_cuerpo_real():
    for consent in consent_documents.CONSENTS:
        assert consent.document_type in DOCUMENT_TYPE_VALUES
        assert consent.signer in SIGNER_VALUES
        assert len(consent.content) > 500
        assert "lorem" not in consent.content.lower()


def test_solo_hay_consentimiento_general_y_el_de_vih():
    assert {c.code for c in consent_documents.CONSENTS} == {
        "CONSENT_DATOS",
        "CONSENT_VIH",
    }
    by_code = consent_documents.CONSENTS_BY_CODE
    assert by_code["CONSENT_DATOS"].document_type == "tratamiento_datos"
    assert by_code["CONSENT_VIH"].document_type == "consentimiento_informado"
    assert all(c.signer == "paciente_o_representante" for c in by_code.values())


def test_exactamente_un_consentimiento_general_activo():
    general = [
        c for c in consent_documents.CONSENTS if c.document_type == DATA_TREATMENT_TYPE
    ]
    assert len(general) == 1


def test_el_contenido_guardado_es_el_texto_fuente_de_los_pdfs():
    for doc in consent_texts.DOCUMENTS:
        seed = consent_documents.CONSENTS_BY_CODE[doc.code]
        assert seed.content == consent_texts.plain_text(doc)


def test_cada_documento_tiene_su_pdf_en_el_manifest():
    manifest = consent_files.load_manifest()
    assert set(manifest) == {c.code for c in consent_documents.CONSENTS}
    for doc in consent_texts.DOCUMENTS:
        assert manifest[doc.code]["file"] == doc.pdf_name


def test_los_pdf_existen_son_validos_y_coinciden_con_el_manifest():
    for code, entry in consent_files.load_manifest().items():
        data = consent_files.pdf_bytes(code)
        assert data.startswith(b"%PDF-"), code
        assert 0 < len(data) <= 5 * MIB, code
        assert len(data) == entry["pdf_size_bytes"], code
        assert hashlib.sha256(data).hexdigest() == entry["pdf_sha256"], (
            f"{code}: el PDF no coincide con el manifest; regenerar con "
            "build_consent_pdfs.py"
        )
        assert base64.b64decode(consent_files.pdf_base64(code)) == data


def test_el_texto_fuente_no_cambio_sin_regenerar_el_pdf():
    manifest = consent_files.load_manifest()
    for doc in consent_texts.DOCUMENTS:
        assert (
            consent_texts.source_sha256(doc) == manifest[doc.code]["source_sha256"]
        ), f"{doc.code}: el texto cambió; regenerar los PDFs con build_consent_pdfs.py"
        assert manifest[doc.code]["version"] == doc.version


def test_los_textos_solo_citan_las_normas_permitidas():
    allowed = {
        "Ley 1581 de 2012",
        "Decreto 1377 de 2013",
        "Decreto 1074 de 2015",
        "Decreto 1543 de 1997",
        "Resolución 2338 de 2013",
        "Resolución 309 de 2025",
    }
    pattern = re.compile(r"(?:Ley|Decreto|Resolución) \d+ de \d{4}")
    for doc in consent_texts.DOCUMENTS:
        cited = set(pattern.findall(consent_texts.plain_text(doc)))
        assert cited <= allowed, (doc.code, cited - allowed)
        assert consent_texts.LEGAL_NOTE in consent_texts.plain_text(doc)


# --- plantillas ------------------------------------------------------------

ALL_UNITS = {u.code for u in UNITS} | {u.code for u in EXTRA_UNITS}
OPTION_SETS = {s.code: {o.code for o in s.options} for s in RESULT_OPTION_SETS} | {
    s.code: {o.code for o in s.options} for s in EXTRA_OPTION_SETS
}
ANALYTES_BY_CODE = {a.code: a for a in ANALYTES}
OPTION_RESULT_TYPES = {"qualitative", "semi_quantitative", "titer"}


def test_analitos_con_unidad_existente_y_sin_huerfanos():
    for analyte in ANALYTES:
        if analyte.unit is not None:
            assert analyte.unit in ALL_UNITS, analyte.code
    used = {f.analyte for t in TEMPLATES for f in t.fields()}
    assert used <= set(ANALYTES_BY_CODE)
    assert set(ANALYTES_BY_CODE) - used == {DISCONTINUED_ANALYTE}


def test_analitos_con_loinc_de_formato_valido():
    for analyte in ANALYTES:
        if analyte.loinc is not None:
            assert re.fullmatch(r"\d{1,5}-\d", analyte.loinc), analyte.code


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.code)
def test_plantilla_cumple_las_reglas_de_publicacion(template):
    fields = template.fields()
    assert not _duplicates(f.analyte for f in fields), "analito repetido"
    assert not _duplicates(s.name for s in template.sections)
    nodes = [FormulaNode(f.analyte, f.formula, True) for f in fields]

    for field in fields:
        analyte = ANALYTES_BY_CODE[field.analyte]
        if field.unit is not None:
            assert field.unit in ALL_UNITS, field.analyte
            assert field.unit == analyte.unit, f"{field.analyte}: unidad distinta"
        if field.result_type in ("numeric", "calculated"):
            assert field.unit and field.decimals is not None, field.analyte
        if field.result_type == "calculated":
            assert field.formula
            problems = formula_problems(
                FormulaNode(field.analyte, field.formula, True), nodes
            )
            assert not problems, f"{field.analyte}: {problems}"
        else:
            assert field.formula is None, field.analyte
        if field.result_type in OPTION_RESULT_TYPES:
            assert field.option_set in OPTION_SETS, field.analyte
        else:
            assert field.option_set is None, field.analyte
        if field.result_type == "numeric" and field.reportable:
            assert field.ranges, f"{field.analyte}: numérico reportable sin rangos"

        range_dicts = [asdict(r) for r in field.ranges]
        for spec, values in zip(field.ranges, range_dicts, strict=True):
            assert not reference_range_bound_errors(values), field.analyte
            values = {**values, "expected_option_id": spec.option}
            assert not _not_allowed_range_fields(field.result_type, values), (
                f"{field.analyte}: campo no admitido por {field.result_type}"
            )
            if spec.option is not None:
                assert spec.option in OPTION_SETS[field.option_set], field.analyte
        for i, first in enumerate(range_dicts):
            for second in range_dicts[i + 1 :]:
                assert not _ranges_overlap(first, second), (
                    f"{field.analyte}: rangos solapados"
                )


def test_los_calculados_se_pueden_crear_en_orden():
    """El cargador crea primero los no calculados y luego los calculados en
    el orden listado: un calculado solo puede usar los ya creados."""
    for template in TEMPLATES:
        fields = template.fields()
        created = {f.analyte for f in fields if f.formula is None}
        for field in (f for f in fields if f.formula is not None):
            refs = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", field.formula))
            assert refs <= created, f"{template.code}/{field.analyte}: {refs - created}"
            created.add(field.analyte)


# --- examenes ---------------------------------------------------------------


def test_cada_examen_referencia_codigos_que_existen():
    areas = {a.code for a in lab_areas.AREAS}
    sample_types = {t.code for s in samples.SAMPLES for t in s.types}
    precondition_codes = {p.code for p in preconditions.PRECONDITIONS}
    labels = {label.code for label in print_labels.LABELS}
    consents = {c.code for c in consent_documents.CONSENTS}
    templates = {t.code for t in TEMPLATES}
    for test in lab_tests.LAB_TESTS:
        assert test.area in areas, test.code
        assert test.template in templates, test.code
        assert test.label in labels, test.code
        assert set(lab_tests.consent_codes(test)) <= consents, test.code
        assert not _duplicates(lab_tests.consent_codes(test)), test.code
        links = [link.sample_type for link in test.samples]
        assert links and set(links) <= sample_types, test.code
        assert not _duplicates(links), test.code
        assert sum(link.preferred for link in test.samples) == 1, test.code
        assert not _duplicates(link.precondition for link in test.preconditions)
        for link in test.preconditions:
            assert link.precondition in precondition_codes, test.code
            assert (link.duration_value_override is None) == (
                link.duration_unit_override is None
            ), test.code
            if link.duration_unit_override is not None:
                assert link.duration_unit_override in DURATION_UNIT_VALUES


def test_ninguna_plantilla_queda_sin_examen_y_hay_entre_25_y_40_examenes():
    assert 25 <= len(lab_tests.LAB_TESTS) <= 40
    assert {t.template for t in lab_tests.LAB_TESTS} == {t.code for t in TEMPLATES}


def test_solo_el_examen_de_vih_enlaza_un_consentimiento_y_nadie_el_general():
    by_code = {t.code: t for t in lab_tests.LAB_TESTS}
    assert lab_tests.consent_codes(by_code["VIH"]) == ["CONSENT_VIH"]
    for test in lab_tests.LAB_TESTS:
        if test.code != "VIH":
            assert lab_tests.consent_codes(test) == [], test.code
        assert "CONSENT_DATOS" not in lab_tests.consent_codes(test)


def test_lo_desactivado_no_lo_usa_ningun_examen_ni_plantilla():
    legacy_type = samples.DISCONTINUED_SAMPLE_TYPE.code
    for test in lab_tests.LAB_TESTS:
        assert all(link.sample_type != legacy_type for link in test.samples)
    assert len(deactivations.DEACTIVATIONS) <= 3
    staff_documents = {p.document_number for p in staff.STAFF}
    assert deactivations.RETIRED_STAFF_DOCUMENT in staff_documents
    for area in lab_areas.AREAS:  # el retirado ya no es encargado vigente
        assert area.manager != deactivations.RETIRED_STAFF_DOCUMENT
