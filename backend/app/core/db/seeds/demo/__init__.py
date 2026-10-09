"""Datos de demostracion para la BD de DESARROLLO de Vladimir.

    cd backend
    uv run python -m app.core.db.seeds.demo --reset --yes

Vacia todas las tablas (`--reset`; sin el flag, se niega si hay datos),
recarga las semillas de catalogo y puebla un laboratorio clinico colombiano
completo (personal, areas, muestras, precondiciones, etiquetas, plantillas
de resultados, documentos a firmar y ~33 examenes) pasando por la API en
proceso (`app.main:app`), es decir por las reglas de negocio reales.

Solo el personal es inventado; el resto son datos reales de un laboratorio
(valores de referencia de adultos de fuentes reconocidas) que el laboratorio
debe validar antes de usarlos en produccion. Un modulo por area de datos:
`staff`, `lab_areas`, `samples`, `preconditions`, `print_labels`,
`consent_documents`, `result_templates/` (por area clinica) y `lab_tests`.

Seguridad: solo corre contra `localhost` y exige `--yes` (ver `guard.py`).
"""
