"""
ContaEC - Generador de RIDE (Representación Impresa de Documento Electrónico)
Genera PDF conforme a las especificaciones del SRI (Ecuador)

El RIDE es la representación impresa oficial de un comprobante electrónico
y debe cumplir con los requisitos establecidos por el SRI en la Resolución
NAC-DNCRASC20-00000005 y la Ficha Técnica v2.32.

Elementos obligatorios del RIDE:
1. RUC del emisor
2. Clave de Acceso (con código de barras CODE128)
3. Número de Autorización y Fecha/Hora de Autorización
4. Ambiente y Tipo de Emisión
5. Información del emisor (Razón Social, Nombre Comercial, Direcciones)
6. Información del comprobante (Tipo, Número, Fecha)
7. Información del comprador (RUC/Cédula, Razón Social, Dirección)
8. Detalle de bienes/servicios (o retenciones para comprobantes de retención)
9. Totales desglosados
10. Información adicional
11. Leyenda SRI con número de autorización
"""
import io
import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, HRFlowable, KeepTogether
)
from reportlab.graphics.barcode import code128

logger = logging.getLogger(__name__)

# Márgenes de página (mm)
MARGIN_LEFT = 15
MARGIN_RIGHT = 15
MARGIN_TOP = 10
MARGIN_BOTTOM = 10

# Ancho útil de la página (A4 = 210mm - márgenes)
PAGE_WIDTH = 210 - MARGIN_LEFT - MARGIN_RIGHT  # 180mm

# Colores ContaEC
COLOR_PRIMARY = colors.HexColor("#1B5E20")       # Verde oscuro (marca ContaEC)
COLOR_HEADER_BG = colors.HexColor("#E8F5E9")     # Verde claro
COLOR_BORDER = colors.HexColor("#BDBDBD")         # Gris borde
COLOR_TEXT = colors.black                          # Texto negro
COLOR_LABEL = colors.HexColor("#616161")           # Gris oscuro para etiquetas
COLOR_TOTAL_BG = colors.HexColor("#F5F5F5")        # Gris claro para totales
COLOR_TABLE_HEADER_BG = colors.HexColor("#2E7D32") # Verde tabla encabezado
COLOR_TABLE_HEADER_TEXT = colors.white             # Blanco texto encabezado
COLOR_TABLE_ALT_ROW = colors.HexColor("#F1F8E9")   # Verde muy claro fila alterna

# Nombres de tipos de comprobante (Tabla 1 SRI)
TIPOS_COMPROBANTE = {
    "01": "FACTURA",
    "03": "LIQUIDACIÓN DE COMPRA DE BIENES Y PRESTACIÓN DE SERVICIOS",
    "04": "NOTA DE CRÉDITO",
    "05": "NOTA DE DÉBITO",
    "06": "GUÍA DE REMISIÓN",
    "07": "COMPROBANTE DE RETENCIÓN",
}

# Nombres de ambiente
AMBIENTES = {
    "1": "PRUEBAS",
    "2": "PRODUCCIÓN",
}

# Nombres de tipo de emisión
TIPOS_EMISION = {
    "1": "NORMAL",
    "2": "CONTINGENCIA",
}

# Nombres de tarifa IVA (Tabla 16 SRI)
TARIFAS_IVA = {
    "0": "0%",
    "2": "12%",
    "3": "14%",
    "4": "15%",
    "5": "5%",
    "6": "No Objeto de IVA",
    "7": "Exento de IVA",
    "8": "13%",
    "9": "IVA Diferenciado",
}

# Nombres de tipo de identificación (Tabla 7 SRI)
TIPOS_IDENTIFICACION = {
    "01": "RUC",
    "02": "Cédula de Identidad",
    "03": "Pasaporte",
    "04": "Venta a Consumidor Final",
    "05": "Identificación del Exterior",
    "06": "Placa",
    "07": "Consumidor Final",
}


def _format_amount(value: Decimal | float | None) -> str:
    """Formatea un valor decimal con 2 decimales y separador de miles."""
    if value is None:
        return "0.00"
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "0.00"


def _format_quantity(value: Decimal | float | None) -> str:
    """Formatea una cantidad con hasta 6 decimales y separador de miles."""
    if value is None:
        return "0"
    try:
        val = float(value)
        if val == int(val):
            return f"{int(val):,d}"
        return f"{val:,.6f}".rstrip("0").rstrip(".")
    except (ValueError, TypeError):
        return "0"


def _format_date(dt: datetime | None) -> str:
    """Formatea una fecha al formato DD/MM/YYYY del SRI."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%d/%m/%Y")


def _format_datetime(dt: datetime | None) -> str:
    """Formatea una fecha y hora al formato DD/MM/YYYY HH:MM:SS del SRI."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _safe_str(value: str | None, default: str = "") -> str:
    """Retorna el valor o un default si es None/vacío."""
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


def _build_label_value(label: str, value: str, styles) -> Paragraph:
    """Construye un párrafo con etiqueta en gris y valor en negro."""
    return Paragraph(
        f'<font color="#{COLOR_LABEL.hexval()[2:]}">{label}:</font> '
        f'<font color="#{COLOR_TEXT.hexval()[2:]}">{value}</font>',
        styles["RideValue"],
    )


def _build_two_column_table(
    left_content: list,
    right_content: list,
    col_widths: tuple = (90 * mm, 90 * mm),
) -> Table:
    """
    Construye una tabla de dos columnas sin bordes para alinear contenido.
    """
    # Emparejar las listas al mismo largo
    max_rows = max(len(left_content), len(right_content))
    left_padded = left_content + [""] * (max_rows - len(left_content))
    right_padded = right_content + [""] * (max_rows - len(right_content))

    data = list(zip(left_padded, right_padded))
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return table


def _create_styles() -> dict:
    """Crea y retorna los estilos personalizados para el RIDE."""
    styles = getSampleStyleSheet()

    # Título principal del RIDE
    styles.add(ParagraphStyle(
        name="RideTitle",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=COLOR_PRIMARY,
        alignment=1,  # Centro
        spaceAfter=1 * mm,
        spaceBefore=0,
        fontName="Helvetica-Bold",
        leading=16,
    ))

    # Subtítulo (tipo de comprobante)
    styles.add(ParagraphStyle(
        name="RideSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=COLOR_PRIMARY,
        alignment=1,
        spaceAfter=2 * mm,
        fontName="Helvetica-Bold",
        leading=13,
    ))

    # Etiqueta (texto gris pequeño)
    styles.add(ParagraphStyle(
        name="RideLabel",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_LABEL,
        fontName="Helvetica",
        leading=9,
    ))

    # Valor (texto negro normal)
    styles.add(ParagraphStyle(
        name="RideValue",
        parent=styles["Normal"],
        fontSize=8,
        textColor=COLOR_TEXT,
        fontName="Helvetica",
        leading=10,
    ))

    # Valor en negrita
    styles.add(ParagraphStyle(
        name="RideValueBold",
        parent=styles["Normal"],
        fontSize=8,
        textColor=COLOR_TEXT,
        fontName="Helvetica-Bold",
        leading=10,
    ))

    # Texto pequeño
    styles.add(ParagraphStyle(
        name="RideSmall",
        parent=styles["Normal"],
        fontSize=6.5,
        textColor=COLOR_LABEL,
        fontName="Helvetica",
        leading=8,
    ))

    # Texto pequeño centrado
    styles.add(ParagraphStyle(
        name="RideSmallCenter",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_LABEL,
        alignment=1,
        fontName="Helvetica",
        leading=9,
    ))

    # Texto de sección
    styles.add(ParagraphStyle(
        name="RideSectionTitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=COLOR_PRIMARY,
        fontName="Helvetica-Bold",
        leading=12,
        spaceBefore=2 * mm,
        spaceAfter=1 * mm,
    ))

    # Etiqueta en tabla de detalle
    styles.add(ParagraphStyle(
        name="RideTableHeader",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_TABLE_HEADER_TEXT,
        fontName="Helvetica-Bold",
        alignment=1,
        leading=9,
    ))

    # Valor en tabla de detalle
    styles.add(ParagraphStyle(
        name="RideTableCell",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_TEXT,
        fontName="Helvetica",
        leading=9,
    ))

    # Valor en tabla de detalle centrado
    styles.add(ParagraphStyle(
        name="RideTableCellCenter",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_TEXT,
        fontName="Helvetica",
        alignment=1,
        leading=9,
    ))

    # Valor en tabla de detalle derecha
    styles.add(ParagraphStyle(
        name="RideTableCellRight",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_TEXT,
        fontName="Helvetica",
        alignment=2,
        leading=9,
    ))

    # Valor total (negrita, derecha)
    styles.add(ParagraphStyle(
        name="RideTotalLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=COLOR_TEXT,
        fontName="Helvetica-Bold",
        alignment=2,  # Derecha
        leading=10,
    ))

    # Valor total (negrita, derecha)
    styles.add(ParagraphStyle(
        name="RideTotalValue",
        parent=styles["Normal"],
        fontSize=8,
        textColor=COLOR_PRIMARY,
        fontName="Helvetica-Bold",
        alignment=2,
        leading=10,
    ))

    # Leyenda SRI
    styles.add(ParagraphStyle(
        name="RideSRI",
        parent=styles["Normal"],
        fontSize=7,
        textColor=COLOR_TEXT,
        fontName="Helvetica-Bold",
        alignment=1,
        leading=9,
    ))

    return styles


# ─────────────────────────────────────────────────────────────────────
# SECCIONES DEL RIDE
# ─────────────────────────────────────────────────────────────────────

def _build_header(
    comprobante_data: dict,
    company_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de encabezado del RIDE:
    - Logo de la empresa (si existe)
    - RUC
    - Tipo de comprobante (título grande)
    - Número del comprobante
    """
    elements = []

    tipo_codigo = comprobante_data.get("tipo_comprobante", "01")
    tipo_nombre = TIPOS_COMPROBANTE.get(tipo_codigo, "COMPROBANTE")
    numero = _build_numero_comprobante(comprobante_data, company_data)

    # Tabla de encabezado: logo + info | tipo comprobante
    logo_path = company_data.get("logo_path")
    ruc = _safe_str(company_data.get("ruc"))

    # Columna izquierda: logo + datos empresa
    left_items = []

    if logo_path and Path(logo_path).exists():
        try:
            logo = Image(logo_path, width=35 * mm, height=15 * mm)
            logo.hAlign = "LEFT"
            left_items.append(logo)
            left_items.append(Spacer(1, 2 * mm))
        except Exception:
            logger.warning(f"No se pudo cargar el logo: {logo_path}")

    if ruc:
        left_items.append(
            Paragraph(f'<font size="9"><b>RUC: {ruc}</b></font>', styles["RideValue"])
        )

    # Columna derecha: tipo de comprobante y número
    right_items = [
        Paragraph(f"RIDE", styles["RideTitle"]),
        Paragraph(tipo_nombre, styles["RideSubtitle"]),
        Paragraph(f"<b>No. {numero}</b>", styles["RideValueBold"]),
    ]

    # Ambiente y tipo emisión
    ambiente_code = comprobante_data.get("ambiente", "1")
    tipo_emision_code = comprobante_data.get("tipo_emision", "1")
    ambiente_name = AMBIENTES.get(ambiente_code, "DESCONOCIDO")
    tipo_emision_name = TIPOS_EMISION.get(tipo_emision_code, "NORMAL")
    right_items.append(
        Paragraph(
            f'<font size="7">AMBIENTE: {ambiente_name} | EMISIÓN: {tipo_emision_name}</font>',
            styles["RideSmallCenter"],
        )
    )

    header_data = [[left_items, right_items]]
    header_table = Table(header_data, colWidths=(100 * mm, 80 * mm))
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (0, 0), "TOP"),
        ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_HEADER_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_PRIMARY),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3 * mm))

    return elements


def _build_numero_comprobante(comprobante_data: dict, company_data: dict) -> str:
    """Construye el número de comprobante formato: estab-ptoEmi-secuencial."""
    estab = _safe_str(company_data.get("cod_establecimiento"), "001")
    pto_emi = _safe_str(company_data.get("cod_punto_emision"), "001")
    secuencial = _safe_str(comprobante_data.get("secuencial"), "000000000")
    return f"{estab}-{pto_emi}-{secuencial}"


def _build_clave_acceso_section(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de Clave de Acceso con código de barras CODE128.
    Si no hay clave de acceso (comprobante aún no autorizado), muestra aviso.
    """
    elements = []

    clave_acceso = comprobante_data.get("clave_acceso")
    numero_autorizacion = comprobante_data.get("numero_autorizacion")
    fecha_autorizacion = comprobante_data.get("fecha_autorizacion")

    # ─── Clave de Acceso ───
    clave_label = Paragraph("CLAVE DE ACCESO", styles["RideLabel"])
    elements.append(clave_label)

    if clave_acceso and len(str(clave_acceso)) >= 49:
        # Generar código de barras CODE128
        try:
            barcode = code128.Code128(
                str(clave_acceso),
                barHeight=12 * mm,
                barWidth=0.35,
                quiet=0,
            )
            elements.append(barcode)
        except Exception as e:
            logger.warning(f"Error generando código de barras: {e}")
            elements.append(Paragraph(str(clave_acceso), styles["RideValue"]))

        # Número de clave de acceso debajo del código de barras
        clave_str = str(clave_acceso)
        clave_display = "  ".join(clave_str[i:i + 4] for i in range(0, len(clave_str), 4))
        elements.append(Paragraph(clave_display, styles["RideSmallCenter"]))
    else:
        elements.append(
            Paragraph(
                '<i>Clave de acceso no disponible (comprobante no autorizado)</i>',
                styles["RideSmallCenter"],
            )
        )

    elements.append(Spacer(1, 2 * mm))

    # ─── Número de Autorización ───
    auth_label = Paragraph("NÚMERO DE AUTORIZACIÓN", styles["RideLabel"])
    elements.append(auth_label)

    if numero_autorizacion:
        auth_str = str(numero_autorizacion)
        auth_display = "  ".join(auth_str[i:i + 4] for i in range(0, len(auth_str), 4))
        elements.append(Paragraph(auth_display, styles["RideValue"]))
    else:
        elements.append(
            Paragraph(
                '<i>Pendiente de autorización</i>',
                styles["RideSmall"],
            )
        )

    elements.append(Spacer(1, 2 * mm))

    # ─── Fecha y Hora de Autorización ───
    fecha_auth = _format_datetime(fecha_autorizacion) if fecha_autorizacion else "Pendiente"
    elements.append(_build_label_value("FECHA Y HORA DE AUTORIZACIÓN", fecha_auth, styles))
    elements.append(Spacer(1, 3 * mm))

    # Línea separadora
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=COLOR_BORDER,
        spaceBefore=1 * mm, spaceAfter=2 * mm,
    ))

    return elements


def _build_emisor_section(
    company_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de información del emisor:
    - Razón Social
    - Nombre Comercial
    - Dirección Matriz
    - Dirección Establecimiento
    - Obligado a llevar contabilidad
    - Contribuyente Especial / RIMPE / Agente Retención
    """
    elements = []

    elements.append(Paragraph("INFORMACIÓN DEL EMISOR", styles["RideSectionTitle"]))

    razon_social = _safe_str(company_data.get("razon_social"))
    nombre_comercial = _safe_str(company_data.get("nombre_comercial"))
    dir_matriz = _safe_str(company_data.get("dir_matriz"))
    dir_estab = _safe_str(company_data.get("dir_establecimiento"))
    obligado = _safe_str(company_data.get("obligado_contabilidad"), "NO")
    contrib_especial = company_data.get("contribuyente_especial")
    rimpe = company_data.get("contribuyente_rimpe")
    agente_ret = company_data.get("agente_retencion")

    # Contenido del emisor (sin tabla, usando párrafos directos)
    elements.append(Paragraph(f'<b>Razón Social:</b> {razon_social}', styles["RideValue"]))

    if nombre_comercial:
        elements.append(Paragraph(f'<b>Nombre Comercial:</b> {nombre_comercial}', styles["RideValue"]))

    elements.append(Paragraph(f'<b>Dirección Matriz:</b> {dir_matriz}', styles["RideValue"]))

    if dir_estab:
        elements.append(Paragraph(f'<b>Dirección Establecimiento:</b> {dir_estab}', styles["RideValue"]))

    # Información fiscal adicional
    fiscal_info = []
    if obligado == "SI":
        fiscal_info.append("OBLIGADO A LLEVAR CONTABILIDAD")
    if contrib_especial:
        fiscal_info.append(f"CONTRIBUYENTE ESPECIAL N° {contrib_especial}")
    if rimpe:
        fiscal_info.append(rimpe)
    if agente_ret:
        fiscal_info.append(f"AGENTE DE RETENCIÓN N° {agente_ret}")

    if fiscal_info:
        elements.append(Paragraph(" | ".join(fiscal_info), styles["RideSmall"]))

    # Línea separadora
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=COLOR_BORDER,
        spaceBefore=2 * mm, spaceAfter=2 * mm,
    ))

    return elements


def _build_comprobante_section(
    comprobante_data: dict,
    company_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de información del comprobante:
    - Tipo de comprobante
    - Número (estab-ptoEmi-secuencial)
    - Fecha de emisión
    """
    elements = []

    tipo_codigo = comprobante_data.get("tipo_comprobante", "01")
    tipo_nombre = TIPOS_COMPROBANTE.get(tipo_codigo, "COMPROBANTE")
    numero = _build_numero_comprobante(comprobante_data, company_data)
    fecha_emision = _format_date(comprobante_data.get("fecha_emision"))

    elements.append(Paragraph("INFORMACIÓN DEL COMPROBANTE", styles["RideSectionTitle"]))

    comp_table_data = [
        [
            Paragraph(f'<b>Tipo:</b> {tipo_nombre}', styles["RideValue"]),
            Paragraph(f'<b>Número:</b> {numero}', styles["RideValue"]),
        ],
        [
            Paragraph(f'<b>Fecha de Emisión:</b> {fecha_emision}', styles["RideValue"]),
            "",
        ],
    ]

    comp_table = Table(comp_table_data, colWidths=(90 * mm, 90 * mm))
    comp_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    elements.append(comp_table)

    # Línea separadora
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=COLOR_BORDER,
        spaceBefore=2 * mm, spaceAfter=2 * mm,
    ))

    return elements


def _build_comprador_section(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de información del comprador:
    - RUC / Cédula de Identidad
    - Razón Social / Nombre
    - Dirección
    - Email / Teléfono (si están disponibles)
    """
    elements = []

    # Etiqueta dinámica según tipo de comprobante
    tipo_codigo = comprobante_data.get("tipo_comprobante", "01")
    if tipo_codigo == "03":
        section_title = "INFORMACIÓN DEL VENDEDOR"
    elif tipo_codigo == "07":
        section_title = "INFORMACIÓN DEL SUJETO RETENIDO"
    elif tipo_codigo == "06":
        section_title = "INFORMACIÓN DEL DESTINATARIO"
    else:
        section_title = "INFORMACIÓN DEL COMPRADOR"

    elements.append(Paragraph(section_title, styles["RideSectionTitle"]))

    tipo_id = comprobante_data.get("cliente_tipo_identificacion", "")
    identificacion = _safe_str(comprobante_data.get("cliente_identificacion"))
    razon_social = _safe_str(comprobante_data.get("cliente_razon_social"))
    direccion = _safe_str(comprobante_data.get("cliente_direccion"))
    email = _safe_str(comprobante_data.get("cliente_email"))
    telefono = _safe_str(comprobante_data.get("cliente_telefono"))

    tipo_id_nombre = TIPOS_IDENTIFICACION.get(tipo_id, "Identificación")

    elements.append(Paragraph(f'<b>{tipo_id_nombre}:</b> {identificacion}', styles["RideValue"]))
    elements.append(Paragraph(f'<b>Razón Social / Nombre:</b> {razon_social}', styles["RideValue"]))

    if direccion:
        elements.append(Paragraph(f'<b>Dirección:</b> {direccion}', styles["RideValue"]))

    # Email y teléfono en la misma línea
    contact_parts = []
    if email:
        contact_parts.append(f"<b>Email:</b> {email}")
    if telefono:
        contact_parts.append(f"<b>Tel:</b> {telefono}")
    if contact_parts:
        elements.append(Paragraph(" | ".join(contact_parts), styles["RideValue"]))

    # Línea separadora
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=COLOR_BORDER,
        spaceBefore=2 * mm, spaceAfter=2 * mm,
    ))

    return elements


def _build_detalle_table(
    detalles_data: list[dict],
    styles: dict,
) -> list:
    """
    Construye la tabla de detalle de bienes/servicios.
    Columnas: Código | Descripción | Cantidad | P.Unit. | Descuento | P.Total
    """
    elements = []

    elements.append(Paragraph("DETALLE DE BIENES Y/O SERVICIOS", styles["RideSectionTitle"]))

    # Anchos de columna (en mm, total = PAGE_WIDTH = 180mm)
    col_widths = [
        18 * mm,   # Código principal
        72 * mm,   # Descripción
        18 * mm,   # Cantidad
        24 * mm,   # Precio Unitario
        22 * mm,   # Descuento
        26 * mm,   # Precio Total
    ]

    # Encabezado de la tabla
    header_row = [
        Paragraph("Código", styles["RideTableHeader"]),
        Paragraph("Descripción", styles["RideTableHeader"]),
        Paragraph("Cant.", styles["RideTableHeader"]),
        Paragraph("P. Unit.", styles["RideTableHeader"]),
        Paragraph("Desc.", styles["RideTableHeader"]),
        Paragraph("P. Total", styles["RideTableHeader"]),
    ]

    table_data = [header_row]

    # Filas de detalle
    for det in detalles_data:
        codigo = _safe_str(det.get("codigo_principal"), "-")
        descripcion = _safe_str(det.get("descripcion"), "-")
        # Truncar descripción larga
        if len(descripcion) > 80:
            descripcion = descripcion[:77] + "..."
        cantidad = _format_quantity(det.get("cantidad"))
        precio_unit = _format_amount(det.get("precio_unitario"))
        descuento = _format_amount(det.get("descuento"))
        precio_total = _format_amount(det.get("precio_total_sin_impuestos"))

        row = [
            Paragraph(codigo, styles["RideTableCellCenter"]),
            Paragraph(descripcion, styles["RideTableCell"]),
            Paragraph(cantidad, styles["RideTableCellCenter"]),
            Paragraph(precio_unit, styles["RideTableCellRight"]),
            Paragraph(descuento, styles["RideTableCellRight"]),
            Paragraph(precio_total, styles["RideTableCellRight"]),
        ]
        table_data.append(row)

    # Crear tabla
    detalle_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Estilo de la tabla
    style_commands = [
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_TABLE_HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_PRIMARY),
        # Alineación
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    # Filas alternas con color de fondo
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style_commands.append(
                ("BACKGROUND", (0, i), (-1, i), COLOR_TABLE_ALT_ROW)
            )

    detalle_table.setStyle(TableStyle(style_commands))
    elements.append(detalle_table)

    return elements


def _build_retenciones_table(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye la tabla de retenciones para Comprobante de Retención (tipo 07).
    Muestra: Impuesto | Código | Porcentaje | Base Imponible | Valor Retenido
    """
    elements = []

    elements.append(Paragraph("DETALLE DE RETENCIONES", styles["RideSectionTitle"]))

    col_widths = [
        36 * mm,   # Impuesto
        36 * mm,   # Código
        27 * mm,   # Porcentaje
        36 * mm,   # Base Imponible
        45 * mm,   # Valor Retenido
    ]

    header_row = [
        Paragraph("Impuesto", styles["RideTableHeader"]),
        Paragraph("Código", styles["RideTableHeader"]),
        Paragraph("Porcentaje", styles["RideTableHeader"]),
        Paragraph("Base Imponible", styles["RideTableHeader"]),
        Paragraph("Valor Retenido", styles["RideTableHeader"]),
    ]

    table_data = [header_row]

    # Retención de IVA
    ret_iva_codigo = comprobante_data.get("retencion_iva_codigo")
    ret_iva_porcentaje = comprobante_data.get("retencion_iva_porcentaje")
    ret_iva_valor = comprobante_data.get("retencion_iva_valor")

    if ret_iva_codigo and ret_iva_valor:
        subtotal = comprobante_data.get("subtotal_sin_impuestos", 0)
        table_data.append([
            Paragraph("RETENCIÓN IVA", styles["RideTableCell"]),
            Paragraph(str(ret_iva_codigo), styles["RideTableCellCenter"]),
            Paragraph(f"{_format_quantity(ret_iva_porcentaje)}%", styles["RideTableCellCenter"]),
            Paragraph(_format_amount(subtotal), styles["RideTableCellRight"]),
            Paragraph(_format_amount(ret_iva_valor), styles["RideTableCellRight"]),
        ])

    # Retención de Renta
    ret_renta_codigo = comprobante_data.get("retencion_renta_codigo")
    ret_renta_porcentaje = comprobante_data.get("retencion_renta_porcentaje")
    ret_renta_valor = comprobante_data.get("retencion_renta_valor")

    if ret_renta_codigo and ret_renta_valor:
        subtotal = comprobante_data.get("subtotal_sin_impuestos", 0)
        table_data.append([
            Paragraph("RETENCIÓN RENTA", styles["RideTableCell"]),
            Paragraph(str(ret_renta_codigo), styles["RideTableCellCenter"]),
            Paragraph(f"{_format_quantity(ret_renta_porcentaje)}%", styles["RideTableCellCenter"]),
            Paragraph(_format_amount(subtotal), styles["RideTableCellRight"]),
            Paragraph(_format_amount(ret_renta_valor), styles["RideTableCellRight"]),
        ])

    if len(table_data) == 1:
        # No hay retenciones
        table_data.append([
            Paragraph("<i>Sin retenciones</i>", styles["RideTableCell"]),
            "", "", "", "",
        ])

    ret_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    ret_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_TABLE_HEADER_TEXT),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(ret_table)

    return elements


def _build_totales_section(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de totales del comprobante:
    - Subtotal sin impuestos
    - Desglose de IVA por tarifa (0%, 5%, 8%, 12%, 13%, 14%, 15%, No Objeto, Exento)
    - Total IVA
    - Total ICE
    - Total Descuento
    - Importe Total (con impuestos)
    """
    elements = []

    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("INFORMACIÓN TOTAL", styles["RideSectionTitle"]))

    # Recopilar datos de totales
    subtotal_sin_imp = _format_amount(comprobante_data.get("subtotal_sin_impuestos"))
    total_iva = _format_amount(comprobante_data.get("total_iva"))
    total_ice = _format_amount(comprobante_data.get("total_ice", 0))
    total_desc = _format_amount(comprobante_data.get("total_descuento"))
    total_con_imp = _format_amount(comprobante_data.get("total_con_impuestos"))

    # IVA por tarifa
    iva_tarifas = []
    for tarifa_field, tarifa_code in [
        ("subtotal_iva_0", "0"),
        ("subtotal_iva_5", "5"),
        ("subtotal_iva_8", "8"),
        ("subtotal_iva_12", "12"),
        ("subtotal_iva_13", "13"),
        ("subtotal_iva_14", "14"),
        ("subtotal_iva_15", "15"),
        ("subtotal_iva_diferenciado", "9"),
    ]:
        valor = comprobante_data.get(tarifa_field, 0)
        if valor and float(valor) != 0:
            nombre_tarifa = TARIFAS_IVA.get(tarifa_code, f"{tarifa_code}%")
            iva_tarifas.append((f"Subtotal IVA {nombre_tarifa}", _format_amount(valor)))

    # Subtotal no objeto y exento
    no_obj = comprobante_data.get("subtotal_no_objeto_iva", 0)
    exento = comprobante_data.get("subtotal_exento_iva", 0)
    if no_obj and float(no_obj) != 0:
        iva_tarifas.append(("Subtotal No Objeto de IVA", _format_amount(no_obj)))
    if exento and float(exento) != 0:
        iva_tarifas.append(("Subtotal Exento de IVA", _format_amount(exento)))

    # Construir tabla de totales
    totales_data = []

    # Subtotal sin impuestos
    totales_data.append([
        Paragraph("Subtotal sin Impuestos:", styles["RideTotalLabel"]),
        Paragraph(subtotal_sin_imp, styles["RideTotalValue"]),
    ])

    # Desglose IVA por tarifa
    for label, valor in iva_tarifas:
        totales_data.append([
            Paragraph(f"  {label}:", styles["RideTotalLabel"]),
            Paragraph(valor, styles["RideTotalValue"]),
        ])

    # Total IVA
    totales_data.append([
        Paragraph("Total IVA:", styles["RideTotalLabel"]),
        Paragraph(total_iva, styles["RideTotalValue"]),
    ])

    # Total ICE (solo si tiene valor)
    if total_ice and total_ice != "0.00":
        totales_data.append([
            Paragraph("Total ICE:", styles["RideTotalLabel"]),
            Paragraph(total_ice, styles["RideTotalValue"]),
        ])

    # Total Descuento (solo si tiene valor)
    if total_desc and total_desc != "0.00":
        totales_data.append([
            Paragraph("Total Descuento:", styles["RideTotalLabel"]),
            Paragraph(total_desc, styles["RideTotalValue"]),
        ])

    # Propina (siempre visible, igual que en el XML del SRI)
    propina = _format_amount(comprobante_data.get("propina", 0))
    totales_data.append([
        Paragraph("Propina:", styles["RideTotalLabel"]),
        Paragraph(propina, styles["RideTotalValue"]),
    ])

    # IRBPNR (Impuesto Redimible Botellas Plásticas No Retornables) - solo si tiene valor
    irbpnr = _format_amount(comprobante_data.get("total_irbpnr", 0))
    if irbpnr and irbpnr != "0.00":
        totales_data.append([
            Paragraph("IRBPNR:", styles["RideTotalLabel"]),
            Paragraph(irbpnr, styles["RideTotalValue"]),
        ])

    # Retenciones si aplican
    ret_iva_valor = comprobante_data.get("retencion_iva_valor")
    ret_renta_valor = comprobante_data.get("retencion_renta_valor")
    if ret_iva_valor and float(ret_iva_valor) != 0:
        totales_data.append([
            Paragraph("Retención IVA:", styles["RideTotalLabel"]),
            Paragraph(f"-{_format_amount(ret_iva_valor)}", styles["RideTotalValue"]),
        ])
    if ret_renta_valor and float(ret_renta_valor) != 0:
        totales_data.append([
            Paragraph("Retención Renta:", styles["RideTotalLabel"]),
            Paragraph(f"-{_format_amount(ret_renta_valor)}", styles["RideTotalValue"]),
        ])

    # Importe Total (destacado)
    totales_data.append([
        Paragraph("IMPORTE TOTAL:", styles["RideTotalLabel"]),
        Paragraph(f"USD {total_con_imp}", styles["RideTotalValue"]),
    ])

    # Crear tabla de totales
    totales_table = Table(totales_data, colWidths=(120 * mm, 60 * mm))

    style_commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        # Última fila (Importe Total) destacada
        ("BACKGROUND", (0, -1), (-1, -1), COLOR_HEADER_BG),
        ("BOX", (0, -1), (-1, -1), 1, COLOR_PRIMARY),
        ("LINEABOVE", (0, -1), (-1, -1), 1, COLOR_PRIMARY),
    ]

    totales_table.setStyle(TableStyle(style_commands))
    elements.append(totales_table)

    return elements


def _build_info_adicional_section(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de información adicional (campoAdicional del SRI).
    Muestra pares clave-valor en formato de tabla.
    """
    elements = []

    info_adicional_raw = comprobante_data.get("info_adicional")
    if not info_adicional_raw:
        return elements

    # Parsear info_adicional (puede ser JSON o string)
    try:
        if isinstance(info_adicional_raw, str):
            info_adicional = json.loads(info_adicional_raw)
        elif isinstance(info_adicional_raw, dict):
            info_adicional = info_adicional_raw
        else:
            return elements
    except (json.JSONDecodeError, TypeError):
        return elements

    if not info_adicional:
        return elements

    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("INFORMACIÓN ADICIONAL", styles["RideSectionTitle"]))

    # Construir tabla de info adicional
    info_data = []
    for key, value in info_adicional.items():
        info_data.append([
            Paragraph(f"<b>{key}:</b>", styles["RideValue"]),
            Paragraph(str(value), styles["RideValue"]),
        ])

    info_table = Table(info_data, colWidths=(50 * mm, 130 * mm))
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, COLOR_BORDER),
    ]))
    elements.append(info_table)

    return elements


def _build_sri_footer(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye el pie de página del RIDE con la leyenda del SRI:
    - Código de barras con número de autorización
    - Texto: "SRI - Número de Autorización: XXXXXXXXXX..."
    """
    elements = []

    elements.append(Spacer(1, 5 * mm))

    # Línea separadora
    elements.append(HRFlowable(
        width="100%", thickness=1, color=COLOR_PRIMARY,
        spaceBefore=1 * mm, spaceAfter=3 * mm,
    ))

    numero_autorizacion = comprobante_data.get("numero_autorizacion")

    if numero_autorizacion:
        # Código de barras con número de autorización
        try:
            barcode = code128.Code128(
                str(numero_autorizacion),
                barHeight=10 * mm,
                barWidth=0.35,
                quiet=0,
            )
            elements.append(barcode)
        except Exception as e:
            logger.warning(f"Error generando código de barras de autorización: {e}")

        # Leyenda SRI
        auth_str = str(numero_autorizacion)
        elements.append(Spacer(1, 2 * mm))
        elements.append(
            Paragraph(
                f"SRI - Número de Autorización: {auth_str}",
                styles["RideSRI"],
            )
        )
    else:
        elements.append(
            Paragraph(
                "SRI - Pendiente de Autorización",
                styles["RideSRI"],
            )
        )

    return elements


# ─────────────────────────────────────────────────────────────────────
# FUNCIONES PARA NOTAS DE CRÉDITO/DÉBITO
# ─────────────────────────────────────────────────────────────────────

def _build_documento_modificado_section(
    comprobante_data: dict,
    styles: dict,
) -> list:
    """
    Construye la sección de documento modificado para Notas de Crédito/Débito.
    """
    elements = []

    motivo = comprobante_data.get("motivo_modificacion")
    fecha_sustento = comprobante_data.get("fecha_emision_documento_sustento")

    if not motivo and not fecha_sustento:
        return elements

    elements.append(Paragraph("DOCUMENTO MODIFICADO", styles["RideSectionTitle"]))

    if motivo:
        elements.append(_build_label_value("Motivo", motivo, styles))

    if fecha_sustento:
        elements.append(_build_label_value(
            "Fecha Documento Sustento",
            _format_date(fecha_sustento),
            styles,
        ))

    # Línea separadora
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=COLOR_BORDER,
        spaceBefore=2 * mm, spaceAfter=2 * mm,
    ))

    return elements


# ─────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE GENERACIÓN
# ─────────────────────────────────────────────────────────────────────

def generate_ride_pdf(
    comprobante_data: dict,
    company_data: dict,
    detalles_data: list[dict] | None = None,
    output_path: str | None = None,
) -> bytes:
    """
    Genera un PDF del RIDE (Representación Impresa de Documento Electrónico)
    para un comprobante electrónico, conforme a las especificaciones del SRI.

    Args:
        comprobante_data: Diccionario con los campos del comprobante:
            - tipo_comprobante: Código de tipo (01, 03, 04, 05, 06, 07)
            - secuencial: Número secuencial (9 dígitos)
            - clave_acceso: Clave de acceso del SRI (49 dígitos, opcional)
            - numero_autorizacion: Número de autorización del SRI (opcional)
            - fecha_autorizacion: Fecha/hora de autorización (opcional)
            - fecha_emision: Fecha de emisión del comprobante
            - ambiente: "1" (Pruebas) o "2" (Producción)
            - tipo_emision: "1" (Normal)
            - cliente_tipo_identificacion: Tipo de ID del comprador
            - cliente_identificacion: Número de ID del comprador
            - cliente_razon_social: Razón social del comprador
            - cliente_direccion: Dirección del comprador
            - cliente_email: Email del comprador (opcional)
            - cliente_telefono: Teléfono del comprador (opcional)
            - subtotal_sin_impuestos: Subtotal sin impuestos
            - subtotal_iva_X: Subtotales por tarifa de IVA
            - total_iva: Total del IVA
            - total_ice: Total del ICE
            - total_descuento: Total de descuentos
            - total_con_impuestos: Importe total
            - retencion_iva_codigo/porcentaje/valor: Retención de IVA
            - retencion_renta_codigo/porcentaje/valor: Retención de Renta
            - motivo_modificacion: Motivo (para NC/ND)
            - fecha_emision_documento_sustento: Fecha doc sustento (para NC/ND)
            - info_adicional: JSON con pares clave-valor

        company_data: Diccionario con los campos de la empresa:
            - ruc: RUC de la empresa (13 dígitos)
            - razon_social: Razón social
            - nombre_comercial: Nombre comercial (opcional)
            - dir_matriz: Dirección de la matriz
            - dir_establecimiento: Dirección del establecimiento (opcional)
            - cod_establecimiento: Código del establecimiento (3 dígitos)
            - cod_punto_emision: Código del punto de emisión (3 dígitos)
            - obligado_contabilidad: "SI" o "NO"
            - contribuyente_especial: Número de resolución (opcional)
            - contribuyente_rimpe: Tipo RIMPE (opcional)
            - agente_retencion: Número de resolución (opcional)
            - logo_path: Ruta del logo de la empresa (opcional)

        detalles_data: Lista de diccionarios con los campos del detalle:
            - codigo_principal: Código del bien/servicio
            - descripcion: Descripción
            - cantidad: Cantidad
            - precio_unitario: Precio unitario sin impuestos
            - descuento: Monto de descuento
            - precio_total_sin_impuestos: Precio total sin impuestos
            - iva_codigo: Código de tarifa IVA
            - iva_porcentaje: Porcentaje de IVA

        output_path: Ruta opcional para guardar el PDF. Si es None, retorna bytes.

    Returns:
        Contenido del PDF como bytes
    """
    if detalles_data is None:
        detalles_data = []

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_LEFT * mm,
        rightMargin=MARGIN_RIGHT * mm,
        topMargin=MARGIN_TOP * mm,
        bottomMargin=MARGIN_BOTTOM * mm,
    )

    styles = _create_styles()
    elements = []

    tipo_codigo = comprobante_data.get("tipo_comprobante", "01")

    # ─── 1. ENCABEZADO ───
    elements.extend(_build_header(comprobante_data, company_data, styles))

    # ─── 2. CLAVE DE ACCESO + CÓDIGO DE BARRAS ───
    elements.extend(_build_clave_acceso_section(comprobante_data, styles))

    # ─── 3. INFORMACIÓN DEL EMISOR ───
    elements.extend(_build_emisor_section(company_data, styles))

    # ─── 4. INFORMACIÓN DEL COMPROBANTE ───
    elements.extend(_build_comprobante_section(comprobante_data, company_data, styles))

    # ─── 5. INFORMACIÓN DEL COMPRADOR ───
    elements.extend(_build_comprador_section(comprobante_data, styles))

    # ─── 6. DOCUMENTO MODIFICADO (solo NC/ND) ───
    if tipo_codigo in ("04", "05"):
        elements.extend(_build_documento_modificado_section(comprobante_data, styles))

    # ─── 7. DETALLE / RETENCIONES ───
    if tipo_codigo == "07":
        # Comprobante de Retención: tabla de retenciones
        elements.extend(_build_retenciones_table(comprobante_data, styles))
    else:
        # Otros comprobantes: tabla de detalle de bienes/servicios
        if detalles_data:
            elements.extend(_build_detalle_table(detalles_data, styles))
        else:
            elements.append(
                Paragraph("<i>Sin detalle de bienes y/o servicios</i>", styles["RideSmallCenter"])
            )

    # ─── 8. TOTALES ───
    elements.extend(_build_totales_section(comprobante_data, styles))

    # ─── 9. INFORMACIÓN ADICIONAL ───
    elements.extend(_build_info_adicional_section(comprobante_data, styles))

    # ─── 10. PIE DE PÁGINA SRI ───
    elements.extend(_build_sri_footer(comprobante_data, styles))

    # Construir el PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()

    # Guardar archivo si se especificó ruta
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        logger.info(f"RIDE PDF guardado en: {output_path}")

    return pdf_bytes


def generate_ride_from_model(
    comprobante: "Comprobante",  # noqa: F821
    output_path: str | None = None,
) -> bytes:
    """
    Genera un PDF del RIDE a partir de un modelo Comprobante de SQLAlchemy.
    Función de conveniencia que extrae los datos del modelo y llama a generate_ride_pdf.

    Args:
        comprobante: Instancia del modelo Comprobante con relaciones cargadas
            (company, client, detalles)
        output_path: Ruta opcional para guardar el PDF

    Returns:
        Contenido del PDF como bytes
    """
    # Extraer datos de la empresa
    company = comprobante.company
    company_data = {
        "ruc": company.ruc,
        "razon_social": company.razon_social,
        "nombre_comercial": company.nombre_comercial,
        "dir_matriz": company.dir_matriz,
        "dir_establecimiento": company.dir_establecimiento,
        "cod_establecimiento": company.cod_establecimiento,
        "cod_punto_emision": company.cod_punto_emision,
        "obligado_contabilidad": company.obligado_contabilidad,
        "contribuyente_especial": company.contribuyente_especial,
        "contribuyente_rimpe": company.contribuyente_rimpe,
        "agente_retencion": company.agente_retencion,
        "logo_path": company.logo_path,
    }

    # Extraer datos del comprobante
    comprobante_data = {
        "tipo_comprobante": comprobante.tipo_comprobante,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion,
        "fecha_emision": comprobante.fecha_emision,
        "ambiente": comprobante.ambiente,
        "tipo_emision": comprobante.tipo_emision,
        "cliente_tipo_identificacion": comprobante.cliente_tipo_identificacion,
        "cliente_identificacion": comprobante.cliente_identificacion,
        "cliente_razon_social": comprobante.cliente_razon_social,
        "cliente_direccion": comprobante.cliente_direccion,
        "cliente_email": comprobante.cliente_email,
        "cliente_telefono": comprobante.cliente_telefono,
        "subtotal_sin_impuestos": comprobante.subtotal_sin_impuestos,
        "subtotal_iva_0": comprobante.subtotal_iva_0,
        "subtotal_iva_5": comprobante.subtotal_iva_5,
        "subtotal_iva_8": comprobante.subtotal_iva_8,
        "subtotal_iva_12": comprobante.subtotal_iva_12,
        "subtotal_iva_13": comprobante.subtotal_iva_13,
        "subtotal_iva_14": comprobante.subtotal_iva_14,
        "subtotal_iva_15": comprobante.subtotal_iva_15,
        "subtotal_no_objeto_iva": comprobante.subtotal_no_objeto_iva,
        "subtotal_exento_iva": comprobante.subtotal_exento_iva,
        "subtotal_iva_diferenciado": comprobante.subtotal_iva_diferenciado,
        "total_iva": comprobante.total_iva,
        "total_ice": comprobante.total_ice,
        "total_descuento": comprobante.total_descuento,
        "propina": Decimal("0"),
        "total_irbpnr": Decimal("0"),
        "total_con_impuestos": comprobante.total_con_impuestos,
        "retencion_iva_codigo": comprobante.retencion_iva_codigo,
        "retencion_iva_porcentaje": comprobante.retencion_iva_porcentaje,
        "retencion_iva_valor": comprobante.retencion_iva_valor,
        "retencion_renta_codigo": comprobante.retencion_renta_codigo,
        "retencion_renta_porcentaje": comprobante.retencion_renta_porcentaje,
        "retencion_renta_valor": comprobante.retencion_renta_valor,
        "motivo_modificacion": comprobante.motivo_modificacion,
        "fecha_emision_documento_sustento": comprobante.fecha_emision_documento_sustento,
        "info_adicional": comprobante.info_adicional,
    }

    # Extraer datos de los detalles
    detalles_data = []
    for det in comprobante.detalles:
        detalles_data.append({
            "codigo_principal": det.codigo_principal,
            "codigo_auxiliar": det.codigo_auxiliar,
            "descripcion": det.descripcion,
            "cantidad": det.cantidad,
            "unidad_medida": det.unidad_medida,
            "precio_unitario": det.precio_unitario,
            "descuento": det.descuento,
            "precio_total_sin_impuestos": det.precio_total_sin_impuestos,
            "iva_codigo": det.iva_codigo,
            "iva_porcentaje": det.iva_porcentaje,
            "iva_valor": det.iva_valor,
            "ice_codigo": det.ice_codigo,
            "ice_porcentaje": det.ice_porcentaje,
            "ice_valor": det.ice_valor,
        })

    # Usar ride_pdf_path del comprobante si no se especifica output_path
    if output_path is None and comprobante.ride_pdf_path:
        output_path = comprobante.ride_pdf_path

    return generate_ride_pdf(
        comprobante_data=comprobante_data,
        company_data=company_data,
        detalles_data=detalles_data,
        output_path=output_path,
    )
