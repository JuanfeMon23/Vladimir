"""Texto de los documentos a firmar: fuente UNICA de los PDFs y del `content`.

De aqui salen (1) el PDF que arma `build_consent_pdfs.py` y (2) el texto plano
que se guarda como `content` de la version (`plain_text`). Solo biblioteca
estandar: el constructor de PDFs lo carga por ruta, sin instalar el proyecto.

Normas citadas (y solo estas, sin numerar articulos): Ley 1581 de 2012,
Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015), Decreto 1543 de
1997, Resolucion 2338 de 2013 y Resolucion 309 de 2025. Los datos del
responsable quedan en blanco: solo los conoce el laboratorio y se completan
subiendo una version nueva. El area juridica debe revisar todo antes de usarlo.

Si cambias un texto, regenera los PDFs (ver `build_consent_pdfs.py`): un test
compara el SHA-256 de `plain_text` con el del `manifest.json`.
"""

import hashlib
from typing import NamedTuple

LEGAL_NOTE = (
    "Documento de referencia sujeto a revisión del área jurídica del "
    "laboratorio antes de su uso."
)


class Heading(NamedTuple):
    text: str


class Paragraph(NamedTuple):
    text: str


class Bullets(NamedTuple):
    items: tuple[str, ...]


class Fields(NamedTuple):
    """Renglones en blanco para completar a mano (o por la app de firmas)."""

    labels: tuple[str, ...]


class Note(NamedTuple):
    text: str


Block = Heading | Paragraph | Bullets | Fields | Note


class ConsentText(NamedTuple):
    code: str
    name: str
    description: str
    document_type: str
    signer: str
    title: str  # encabezado del PDF y primera linea del texto plano
    version: int  # numero de version que se imprime en el pie del PDF
    pdf_name: str
    blocks: tuple[Block, ...]


_RESPONSIBLE = (
    Heading("1. Datos del responsable del tratamiento"),
    Paragraph(
        "El responsable del tratamiento de sus datos personales es el laboratorio "
        "clínico identificado a continuación:"
    ),
    Fields(
        (
            "Razón social",
            "NIT",
            "Dirección",
            "Correo electrónico de contacto",
            "Teléfono de contacto",
        )
    ),
)

DATA_TREATMENT = ConsentText(
    code="CONSENT_DATOS",
    name="Autorización de tratamiento de datos personales",
    description=(
        "Consentimiento general de tratamiento de datos personales y sensibles "
        "(Ley 1581 de 2012); se firma primero, para todo paciente."
    ),
    document_type="tratamiento_datos",
    signer="paciente_o_representante",
    title="Autorización para el tratamiento de datos personales",
    version=1,
    pdf_name="consentimiento_tratamiento_datos_v1.pdf",
    blocks=(
        Paragraph(
            "En cumplimiento de la Ley 1581 de 2012, del Decreto 1377 de 2013 "
            "(compilado en el Decreto 1074 de 2015) y de las demás normas que los "
            "complementen, el laboratorio le solicita su autorización previa, "
            "expresa e informada para tratar sus datos personales, incluidos los "
            "datos sensibles relacionados con su salud."
        ),
        *_RESPONSIBLE,
        Heading("2. Datos sensibles y carácter voluntario de la autorización"),
        Paragraph(
            "Los datos relacionados con su salud, como las órdenes médicas, las "
            "muestras, los resultados de los exámenes y su historia clínica, son "
            "datos sensibles: afectan su intimidad y su uso indebido puede generar "
            "discriminación."
        ),
        Paragraph(
            "Usted NO está obligado a autorizar el tratamiento de datos sensibles. "
            "Su decisión será respetada; tenga en cuenta que, sin esos datos, el "
            "laboratorio puede no estar en condiciones de prestarle el servicio "
            "solicitado."
        ),
        Heading("3. Datos personales que se tratan"),
        Bullets(
            (
                (
                    "Datos de identificación: nombre, tipo y número de documento, "
                    "fecha de nacimiento y sexo."
                ),
                "Datos de contacto: dirección, teléfono y correo electrónico.",
                (
                    "Datos de la orden médica: médico ordenante, diagnóstico y "
                    "exámenes solicitados."
                ),
                "Datos de las muestras tomadas y de los resultados de sus exámenes.",
                "Datos de afiliación y facturación: EPS o aseguradora y forma de pago.",
            )
        ),
        Heading("4. Finalidades del tratamiento"),
        Bullets(
            (
                (
                    "Prestar el servicio de laboratorio clínico: registrar su "
                    "identidad, tomar y procesar las muestras."
                ),
                "Procesar los exámenes y entregarle sus resultados.",
                "Comunicarnos con usted sobre su atención, sus citas y sus resultados.",
                (
                    "Facturar y relacionarnos con la EPS, la aseguradora o el médico "
                    "ordenante, cuando aplique."
                ),
                (
                    "Gestionar la calidad del servicio y cumplir las obligaciones "
                    "legales y las solicitudes de las autoridades competentes."
                ),
                (
                    "Conservar su historia clínica y sus resultados durante el tiempo "
                    "que exija la ley."
                ),
            )
        ),
        Heading("5. Transmisión y transferencia a terceros"),
        Paragraph(
            "El laboratorio solo transmitirá o transferirá sus datos a terceros "
            "cuando la ley lo exija o cuando sea necesario para prestarle el "
            "servicio, por ejemplo al médico que ordenó los exámenes, a la entidad "
            "responsable del pago o a otro laboratorio al que deba remitirse una "
            "muestra. En esos casos se exigirá a quien los reciba el cumplimiento "
            "de las normas de protección de datos personales."
        ),
        Heading("6. Derechos del titular"),
        Paragraph("Como titular de los datos usted tiene derecho a:"),
        Bullets(
            (
                "Conocer, actualizar y rectificar sus datos personales.",
                "Solicitar prueba de esta autorización.",
                "Ser informado, previa solicitud, del uso que se ha dado a sus datos.",
                (
                    "Presentar quejas ante la Superintendencia de Industria y Comercio "
                    "por infracciones a la ley de protección de datos."
                ),
                (
                    "Revocar la autorización y solicitar la supresión de sus datos, "
                    "salvo que exista un deber legal o contractual de conservarlos."
                ),
                "Acceder de forma gratuita a sus datos personales.",
            )
        ),
        Heading("7. Canales de atención"),
        Paragraph(
            "Puede ejercer sus derechos y presentar consultas o reclamos por "
            "escrito, mediante los datos de contacto del numeral 1 o en la sede "
            "donde fue atendido. Las solicitudes se atenderán en los plazos que "
            "fije la ley."
        ),
        Heading("8. Vigencia"),
        Paragraph(
            "Esta autorización permanece vigente mientras dure su relación con el "
            "laboratorio y durante el tiempo en que la ley exija conservar la "
            "historia clínica y demás información, sin perjuicio de que usted la "
            "revoque en los términos del numeral 6."
        ),
        Heading("9. Menores de edad"),
        Paragraph(
            "Si el titular es menor de edad, la autorización la otorga su "
            "representante legal (padre, madre o tutor). El laboratorio tendrá en "
            "cuenta la opinión del menor, según su madurez y su capacidad para "
            "entender el asunto."
        ),
        Heading("10. Declaración y autorización"),
        Paragraph(
            "Declaro que leí y entendí este documento; que se me informó que no "
            "estoy obligado a autorizar el tratamiento de mis datos sensibles y "
            "cuáles son mis derechos como titular; y que, de manera previa, expresa "
            "e informada, AUTORIZO al laboratorio para tratar mis datos personales, "
            "incluidos los datos sensibles de salud, para las finalidades "
            "descritas."
        ),
        Heading("Firma del titular"),
        Fields(
            (
                "Nombre completo",
                "Tipo de documento",
                "Número de documento",
                "Fecha y hora",
                "Firma",
            )
        ),
        Heading("Representante legal (solo si el titular es menor de edad)"),
        Fields(
            (
                "Nombre completo",
                "Tipo y número de documento",
                "Parentesco o calidad en que actúa",
                "Firma",
            )
        ),
        Note(LEGAL_NOTE),
    ),
)

HIV = ConsentText(
    code="CONSENT_VIH",
    name="Consentimiento informado para prueba de VIH",
    description=(
        "Consentimiento informado escrito, con asesoría previa y posterior a la "
        "prueba de VIH (Resolución 2338 de 2013, Decreto 1543 de 1997)."
    ),
    document_type="consentimiento_informado",
    signer="paciente_o_representante",
    title="Consentimiento informado para la prueba de VIH",
    version=1,
    pdf_name="consentimiento_vih_v1.pdf",
    blocks=(
        Paragraph(
            "De acuerdo con el Decreto 1543 de 1997 y la Resolución 2338 de 2013, "
            "la prueba de VIH se realiza con su consentimiento informado por "
            "escrito y con asesoría antes y después de la prueba. Este documento "
            "le explica en qué consiste la prueba y recoge su decisión."
        ),
        *_RESPONSIBLE,
        Heading("2. La prueba es voluntaria"),
        Paragraph(
            "Usted decide libremente si se hace la prueba. Puede negarse, o retirar "
            "su consentimiento en cualquier momento antes de que se tome la "
            "muestra, y esa decisión no le hará perder ningún otro servicio ni "
            "atención del laboratorio."
        ),
        Heading("3. Asesoría antes y después de la prueba"),
        Bullets(
            (
                (
                    "Antes de la prueba, un profesional le explicó qué es el VIH, cómo "
                    "se transmite y cómo se previene, en qué consiste la prueba y qué "
                    "significan sus posibles resultados, y respondió sus preguntas."
                ),
                (
                    "Después de la prueba se le ofrece asesoría para la entrega y "
                    "comprensión del resultado, y para orientarlo sobre los pasos "
                    "siguientes."
                ),
            )
        ),
        Heading("4. Qué es la prueba y qué significa el resultado"),
        Paragraph(
            "La prueba que se realiza en este laboratorio es una prueba de "
            "tamizaje (presuntiva): indica si hay señales que sugieren una "
            "infección, pero por sí sola no establece el diagnóstico. El resultado "
            "puede ser:"
        ),
        Bullets(
            (
                (
                    "No reactivo: no se encontraron señales de infección en la muestra. "
                    "Si la exposición fue muy reciente (período de ventana), puede ser "
                    "necesario repetir la prueba más adelante."
                ),
                (
                    "Reactivo: se encontraron señales que sugieren una infección. No es "
                    "un diagnóstico y debe confirmarse."
                ),
                (
                    "Indeterminado: el resultado no es concluyente y se requieren una "
                    "nueva muestra o pruebas adicionales."
                ),
            )
        ),
        Heading("5. Prueba confirmatoria"),
        Paragraph(
            "Un resultado reactivo requiere una prueba confirmatoria realizada con "
            "una segunda muestra. Solo con esa confirmación se puede establecer el "
            "diagnóstico."
        ),
        Heading("6. Entrega del resultado"),
        Paragraph(
            "El resultado se le entrega a usted, o a su representante legal cuando "
            "corresponda, con asesoría posterior a la prueba. Si el resultado "
            "requiere atención médica, se le orientará sobre cómo acceder a ella."
        ),
        Heading("7. Confidencialidad y datos sensibles"),
        Paragraph(
            "El resultado es confidencial y es un dato sensible, tratado conforme a "
            "la Ley 1581 de 2012 y a la autorización de tratamiento de datos "
            "personales que usted otorgó al laboratorio. Solo se comparte con "
            "terceros con su autorización o cuando la ley lo exija."
        ),
        Heading("8. Notificación en salud pública"),
        Paragraph(
            "Conforme a la ley, los casos confirmados deben notificarse a las "
            "autoridades de vigilancia en salud pública. Esa notificación se hace "
            "con la reserva que la ley exige y no equivale a divulgar su "
            "información a terceros."
        ),
        Heading("9. No discriminación"),
        Paragraph(
            "Ninguna persona puede ser discriminada ni se le pueden negar servicios "
            "de salud por haberse realizado la prueba de VIH o por su resultado."
        ),
        Heading("10. Quién firma este consentimiento"),
        Bullets(
            (
                (
                    "Personas de 14 años o más: firman por sí mismas su consentimiento "
                    "para la prueba, de acuerdo con la Resolución 309 de 2025."
                ),
                (
                    "Menores de 14 años: firma su representante legal y, además, el "
                    "menor da su asentimiento, según lo previsto en la Resolución 309 "
                    "de 2025."
                ),
            )
        ),
        Heading("11. Constancia de la asesoría previa"),
        Paragraph("A cargo del profesional que brindó la asesoría antes de la prueba:"),
        Fields(
            (
                "Nombre del profesional",
                "Cargo y registro profesional",
                "Fecha y hora de la asesoría",
                "Firma del profesional",
            )
        ),
        Heading("12. Declaración y consentimiento"),
        Paragraph(
            "Declaro que recibí la asesoría previa; que entendí la información de "
            "este documento y mis preguntas fueron respondidas; que sé que la "
            "prueba es voluntaria; y que, libremente, doy mi CONSENTIMIENTO para "
            "que se me tome una muestra de sangre y se procese la prueba de VIH."
        ),
        Heading("Firma del paciente"),
        Fields(
            (
                "Nombre completo",
                "Tipo de documento",
                "Número de documento",
                "Fecha y hora",
                "Firma",
            )
        ),
        Heading("Representante legal y asentimiento (si es menor de 14 años)"),
        Fields(
            (
                "Nombre del representante legal",
                "Tipo y número de documento",
                "Parentesco o calidad en que actúa",
                "Firma del representante legal",
                "Asentimiento del menor (nombre y firma)",
            )
        ),
        Note(LEGAL_NOTE),
    ),
)

DOCUMENTS: tuple[ConsentText, ...] = (DATA_TREATMENT, HIV)


def plain_text(doc: ConsentText) -> str:
    """Texto plano legible del documento (el `content` de la version)."""
    lines: list[str] = [doc.title.upper()]
    for block in doc.blocks:
        lines.append("")
        match block:
            case Heading(text):
                lines.append(text.upper())
            case Paragraph(text) | Note(text):
                lines.append(text)
            case Bullets(items):
                lines.extend(f"- {item}" for item in items)
            case Fields(labels):
                lines.extend(f"{label}: ______________________" for label in labels)
    return "\n".join(lines) + "\n"


def source_sha256(doc: ConsentText) -> str:
    """SHA-256 del texto fuente; el manifest lo guarda para detectar que el
    texto cambio y falta regenerar el PDF."""
    return hashlib.sha256(plain_text(doc).encode("utf-8")).hexdigest()
