"""
ContaEC - Generador de XML para comprobantes electrónicos del SRI
Genera XML válidos según la Ficha Técnica v2.32 del SRI (Ecuador)

Tipos de comprobante soportados:
- 01: Factura
- 03: Liquidación de Compra
- 04: Nota de Crédito
- 05: Nota de Débito
- 06: Guía de Remisión
- 07: Comprobante de Retención

Reglas de formato del SRI:
- Fechas: DD/MM/YYYY
- Montos: 2 decimales con "." como separador
- Cantidades: hasta 6 decimales con "." como separador
- Moneda: siempre DOLAR
- IVA código: "2" (tipo de impuesto, no tarifa)
- ICE código: "3"
- claveAcceso: 49 dígitos con dígito verificador módulo 11
"""
import secrets
import re
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Optional

from lxml import etree

logger = logging.getLogger(__name__)

# SRI XSD schema directory and version configuration
# Version can be overridden via SRI_XML_VERSION env var (default: "1.1.0")
# Supported versions: "1.0.0", "1.1.0", "2.0.0", "2.1.0"
import os
_SRI_XML_VERSION = os.environ.get("SRI_XML_VERSION", "1.1.0")
_XSD_DIR = Path(__file__).parent.parent / "xsd"
_XSD_FILES = {
    "01": f"factura_V{_SRI_XML_VERSION}.xsd",
    "03": f"liquidacionCompra_V{_SRI_XML_VERSION}.xsd",
    "04": f"notaCredito_V{_SRI_XML_VERSION}.xsd",
    "05": f"notaDebito_V{_SRI_XML_VERSION}.xsd",
    "06": f"guiaRemision_V{_SRI_XML_VERSION}.xsd",
    "07": f"comprobanteRetencion_V{_SRI_XML_VERSION}.xsd",
}


def validate_xml_against_xsd(xml_string: str, tipo_comprobante: str) -> list[str]:
    """
    Validate generated XML against the SRI XSD schema for the given document type.

    Args:
        xml_string: The XML content to validate
        tipo_comprobante: SRI document type code (01, 03, 04, 05, 06, 07)

    Returns:
        List of validation error messages. Empty list means valid.
    """
    xsd_filename = _XSD_FILES.get(tipo_comprobante)
    if not xsd_filename:
        logger.warning(f"No XSD schema for document type: {tipo_comprobante}")
        return []

    xsd_path = _XSD_DIR / xsd_filename
    if not xsd_path.exists():
        logger.warning(f"XSD file not found: {xsd_path}. Skipping validation.")
        return []

    try:
        schema_doc = etree.parse(str(xsd_path))
        schema = etree.XMLSchema(schema_doc)
        xml_doc = etree.fromstring(xml_string.encode("utf-8"))
        schema.assertValid(xml_doc)
        return []
    except etree.XMLSchemaParseError as e:
        logger.error(f"XSD parse error for {xsd_filename}: {e}")
        return [f"XSD parse error: {str(e)}"]
    except etree.DocumentInvalid as e:
        errors = [str(err) for err in schema.error_log]
        logger.error(f"XML validation failed for {tipo_comprobante}: {errors}")
        return errors
    except Exception as e:
        logger.error(f"Unexpected XSD validation error: {e}")
        return [str(e)]


# ==========================================
# Constantes de mapeo de tipos de comprobante
# ==========================================

TIPO_COMPROBANTE_MAP: dict[str, str] = {
    "01": "factura",
    "03": "liquidacionCompra",
    "04": "notaCredito",
    "05": "notaDebito",
    "06": "guiaRemision",
    "07": "comprobanteRetencion",
}

# Versión del comprobante según SRI
COMPROBANTE_VERSION = _SRI_XML_VERSION


# ==========================================
# Funciones de formato y utilidades
# ==========================================

def format_date(fecha: date | str) -> str:
    """
    Formatea una fecha al formato DD/MM/YYYY requerido por el SRI.

    Args:
        fecha: Fecha como objeto date o cadena (YYYY-MM-DD o DD/MM/YYYY)

    Returns:
        Cadena con formato DD/MM/YYYY
    """
    if isinstance(fecha, date):
        return fecha.strftime("%d/%m/%Y")
    # Si ya está en formato DD/MM/YYYY, devolverla tal cual
    if re.match(r"^\d{2}/\d{2}/\d{4}$", fecha):
        return fecha
    # Intentar convertir de YYYY-MM-DD a DD/MM/YYYY
    try:
        partes = fecha.split("-")
        if len(partes) == 3:
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
    except (ValueError, IndexError):
        pass
    return fecha


def format_amount(valor: Decimal | float | int | str, decimals: int = 2) -> str:
    """
    Formatea un valor numérico con la cantidad de decimales especificada.
    Usa "." como separador decimal según estándar del SRI.

    Args:
        valor: Valor numérico a formatear
        decimals: Cantidad de decimales (2 para montos, 6 para cantidades)

    Returns:
        Cadena formateada con decimales fijos
    """
    if isinstance(valor, str):
        valor = valor.replace(",", ".")
    dec = Decimal(str(valor))
    quantize_str = "0." + "0" * decimals if decimals > 0 else "0"
    dec = dec.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
    return str(dec)


def format_quantity(cantidad: Decimal | float | int | str) -> str:
    """
    Formatea una cantidad con hasta 6 decimales para el SRI.
    Elimina ceros innecesarios a la derecha pero mantiene al menos 2 decimales.

    Args:
        cantidad: Cantidad a formatear

    Returns:
        Cadena formateada
    """
    formateado = format_amount(cantidad, decimals=6)
    # Eliminar ceros innecesarios pero mantener al menos 2 decimales
    partes = formateado.split(".")
    if len(partes) == 2:
        decimales = partes[1].rstrip("0")
        if len(decimales) < 2:
            decimales = decimales.ljust(2, "0")
        return f"{partes[0]}.{decimales}"
    return formateado


def _add_text_element(
    parent: etree._Element,
    tag: str,
    text: str | int | float | Decimal | None,
) -> etree._Element | None:
    """
    Agrega un elemento hijo con texto al padre.
    Solo lo agrega si el texto no es None ni vacío.

    Args:
        parent: Elemento padre XML
        tag: Nombre del tag
        text: Contenido de texto del elemento

    Returns:
        El elemento creado o None si no se agregó
    """
    if text is None or (isinstance(text, str) and text.strip() == ""):
        return None
    elem = etree.SubElement(parent, tag)
    elem.text = str(text)
    return elem


# ==========================================
# Generación de Clave de Acceso
# ==========================================

def _calculate_check_digit(clave_parcial: str) -> str:
    """
    Calcula el dígito verificador de la clave de acceso usando módulo 11.

    Algoritmo del SRI:
    1. Multiplicar cada dígito por los factores 2,3,4,5,6,7 (cíclicamente de derecha a izquierda)
    2. Sumar todos los productos
    3. Calcular: 11 - (suma % 11)
    4. Si el resultado es 11 -> dígito = 0
    5. Si el resultado es 10 -> dígito = 1
    6. En otro caso -> dígito = resultado

    Args:
        clave_parcial: Los primeros 48 dígitos de la clave de acceso

    Returns:
        Dígito verificador como cadena de 1 carácter
    """
    factores = [2, 3, 4, 5, 6, 7]
    suma = 0
    indice_factor = 0

    # Recorrer de derecha a izquierda
    for digito in reversed(clave_parcial):
        suma += int(digito) * factores[indice_factor]
        indice_factor = (indice_factor + 1) % len(factores)

    resto = suma % 11
    digito_verificador = 11 - resto

    if digito_verificador == 11:
        digito_verificador = 0
    elif digito_verificador == 10:
        digito_verificador = 1

    return str(digito_verificador)


def generate_clave_acceso(
    fecha_emision: date,
    tipo_comprobante: str,
    ruc: str,
    ambiente: str,
    establecimiento: str,
    punto_emision: str,
    secuencial: str,
    codigo_numerico: str | None = None,
    tipo_emision: str = "1",
) -> str:
    """
    Genera la clave de acceso de 49 dígitos del SRI con dígito verificador (módulo 11).

    Estructura de la clave de acceso (49 dígitos):
    - DDMMYYYY: Fecha de emisión (8 dígitos)
    - Tipo comprobante: 2 dígitos (01, 03, 04, 05, 06, 07)
    - RUC: 13 dígitos
    - Ambiente: 1 dígito (1=pruebas, 2=producción)
    - Tipo de emisión: 1 dígito (1=normal, 2=indisponibilidad)
    - Establecimiento: 3 dígitos
    - Punto de emisión: 3 dígitos
    - Secuencial: 9 dígitos
    - Código numérico: 8 dígitos (aleatorio)
    - Dígito verificador: 1 dígito (módulo 11)

    Args:
        fecha_emision: Fecha de emisión del comprobante
        tipo_comprobante: Código del tipo de comprobante (01, 03, 04, 05, 06, 07)
        ruc: RUC del emisor (13 dígitos)
        ambiente: Ambiente del SRI (1=pruebas, 2=producción)
        establecimiento: Código del establecimiento (3 dígitos)
        punto_emision: Código del punto de emisión (3 dígitos)
        secuencial: Número secuencial del comprobante (9 dígitos)
        codigo_numerico: Código numérico aleatorio de 8 dígitos (se genera si no se proporciona)
        tipo_emision: Tipo de emisión (1=normal, 2=por indisponibilidad del sistema)

    Returns:
        Clave de acceso de 49 dígitos

    Raises:
        ValueError: Si los parámetros no tienen el formato correcto
    """
    # Validar tipo de comprobante
    if tipo_comprobante not in TIPO_COMPROBANTE_MAP:
        raise ValueError(
            f"Tipo de comprobante inválido: {tipo_comprobante}. "
            f"Válidos: {list(TIPO_COMPROBANTE_MAP.keys())}"
        )

    # Formatear fecha: DDMMYYYY
    fecha_str = fecha_emision.strftime("%d%m%Y")

    # Validar y formatear RUC (13 dígitos)
    ruc = ruc.strip()
    if not ruc.isdigit() or len(ruc) != 13:
        raise ValueError(f"RUC inválido: debe tener 13 dígitos, recibido: {ruc}")

    # Validar ambiente
    if ambiente not in ("1", "2"):
        raise ValueError(f"Ambiente inválido: debe ser '1' o '2', recibido: {ambiente}")

    # Validar tipo de emisión
    if tipo_emision not in ("1", "2"):
        raise ValueError(
            f"Tipo de emisión inválido: debe ser '1' o '2', recibido: {tipo_emision}"
        )

    # Formatear establecimiento (3 dígitos con ceros a la izquierda)
    establecimiento = establecimiento.strip().zfill(3)
    if len(establecimiento) != 3 or not establecimiento.isdigit():
        raise ValueError(
            f"Establecimiento inválido: debe tener hasta 3 dígitos, "
            f"recibido: {establecimiento}"
        )

    # Formatear punto de emisión (3 dígitos con ceros a la izquierda)
    punto_emision = punto_emision.strip().zfill(3)
    if len(punto_emision) != 3 or not punto_emision.isdigit():
        raise ValueError(
            f"Punto de emisión inválido: debe tener hasta 3 dígitos, "
            f"recibido: {punto_emision}"
        )

    # Formatear secuencial (9 dígitos con ceros a la izquierda)
    secuencial = secuencial.strip().zfill(9)
    if len(secuencial) != 9 or not secuencial.isdigit():
        raise ValueError(
            f"Secuencial inválido: debe tener hasta 9 dígitos, "
            f"recibido: {secuencial}"
        )

    # Generar código numérico aleatorio de 8 dígitos si no se proporciona
    if codigo_numerico is None:
        codigo_numerico = str(secrets.randbelow(90000000) + 10000000)
    else:
        codigo_numerico = codigo_numerico.strip().zfill(8)
        if len(codigo_numerico) != 8 or not codigo_numerico.isdigit():
            raise ValueError(
                f"Código numérico inválido: debe tener 8 dígitos, "
                f"recibido: {codigo_numerico}"
            )

    # Construir clave parcial (48 dígitos)
    clave_parcial = (
        fecha_str
        + tipo_comprobante
        + ruc
        + ambiente
        + tipo_emision
        + establecimiento
        + punto_emision
        + secuencial
        + codigo_numerico
    )

    # Verificar longitud de la clave parcial (48 dígitos)
    if len(clave_parcial) != 48:
        raise ValueError(
            f"La clave parcial debe tener 48 dígitos, tiene {len(clave_parcial)}"
        )

    # Calcular dígito verificador
    digito_verificador = _calculate_check_digit(clave_parcial)

    # Construir clave completa (49 dígitos)
    clave_acceso = clave_parcial + digito_verificador

    return clave_acceso


# ==========================================
# Constructores de secciones XML
# ==========================================

def _build_info_tributaria(
    comprobante_data: dict,
    clave_acceso: str,
) -> etree._Element:
    """
    Construye la sección <infoTributaria> del comprobante electrónico.

    Campos obligatorios:
    - ambiente, tipoEmision, razonSocial, nombreComercial, ruc
    - claveAcceso, codDoc, estab, ptoEmi, secuencial, dirMatriz

    Campos opcionales:
    - agenteRetencion, contribuyenteEspecial, obligadoContabilidad
    - regimenMicroempresas, regimenRimpe

    Args:
        comprobante_data: Datos del comprobante (ambiente, tipoEmision, etc.)
        clave_acceso: Clave de acceso de 49 dígitos

    Returns:
        Elemento XML <infoTributaria>
    """
    info_trib = etree.Element("infoTributaria")

    # Campos obligatorios
    _add_text_element(info_trib, "ambiente", comprobante_data.get("ambiente"))
    _add_text_element(info_trib, "tipoEmision", comprobante_data.get("tipo_emision", "1"))
    _add_text_element(info_trib, "razonSocial", comprobante_data.get("razon_social"))
    _add_text_element(info_trib, "nombreComercial", comprobante_data.get("nombre_comercial"))
    _add_text_element(info_trib, "ruc", comprobante_data.get("ruc"))
    _add_text_element(info_trib, "claveAcceso", clave_acceso)
    _add_text_element(info_trib, "codDoc", comprobante_data.get("cod_doc"))
    _add_text_element(info_trib, "estab", comprobante_data.get("estab"))
    _add_text_element(info_trib, "ptoEmi", comprobante_data.get("pto_emi"))
    _add_text_element(info_trib, "secuencial", comprobante_data.get("secuencial"))
    _add_text_element(info_trib, "dirMatriz", comprobante_data.get("dir_matriz"))

    # Campos opcionales
    _add_text_element(info_trib, "agenteRetencion", comprobante_data.get("agente_retencion"))
    _add_text_element(info_trib, "contribuyenteEspecial", comprobante_data.get("contribuyente_especial"))
    _add_text_element(info_trib, "obligadoContabilidad", comprobante_data.get("obligado_contabilidad"))
    _add_text_element(info_trib, "regimenMicroempresas", comprobante_data.get("regimen_microempresas"))
    _add_text_element(info_trib, "regimenRimpe", comprobante_data.get("regimen_rimpe"))

    return info_trib


def _build_total_con_impuestos(totales_impuestos: list[dict]) -> etree._Element:
    """
    Construye la sección <totalConImpuestos> con los totales de impuestos.

    Cada dict de totales_impuestos debe tener:
    - codigo: Código del impuesto (2=IVA, 3=ICE)
    - codigo_porcentaje: Código de la tarifa (10=13%, 0=0%, etc.)
    - base_imponible: Base imponible
    - valor: Valor del impuesto

    Args:
        totales_impuestos: Lista de diccionarios con datos de impuestos

    Returns:
        Elemento XML <totalConImpuestos>
    """
    total_con_imp = etree.Element("totalConImpuestos")

    for imp_data in totales_impuestos:
        total_imp = etree.SubElement(total_con_imp, "totalImpuesto")
        _add_text_element(total_imp, "codigo", imp_data.get("codigo"))
        _add_text_element(
            total_imp, "codigoPorcentaje", imp_data.get("codigo_porcentaje")
        )
        _add_text_element(
            total_imp,
            "baseImponible",
            format_amount(imp_data.get("base_imponible", 0)),
        )
        # Tarifa del impuesto (ej: 15.00) - requerida por el SRI en el total
        _add_text_element(
            total_imp,
            "tarifa",
            format_amount(
                imp_data.get("tarifa", imp_data.get("porcentaje", 0))
            ),
        )
        _add_text_element(
            total_imp, "valor", format_amount(imp_data.get("valor", 0))
        )

    return total_con_imp


def _build_pagos(pagos: list[dict]) -> etree._Element:
    """
    Construye la sección <pagos> con las formas de pago.

    Cada dict de pagos debe tener:
    - forma_pago: Código de la forma de pago (Tabla 23)
    - total: Total pagado con esa forma
    - plazo: Plazo en días (opcional, para crédito)
    - unidad_tiempo: Unidad de tiempo del plazo (opcional)

    Args:
        pagos: Lista de diccionarios con datos de pago

    Returns:
        Elemento XML <pagos>
    """
    pagos_elem = etree.Element("pagos")

    for pago_data in pagos:
        pago = etree.SubElement(pagos_elem, "pago")
        _add_text_element(pago, "formaPago", pago_data.get("forma_pago"))
        _add_text_element(
            pago, "total", format_amount(pago_data.get("total", 0))
        )
        _add_text_element(pago, "plazo", pago_data.get("plazo"))
        _add_text_element(pago, "unidadTiempo", pago_data.get("unidad_tiempo"))

    return pagos_elem


def _build_impuestos_detalle(impuestos: list[dict]) -> etree._Element:
    """
    Construye la sección <impuestos> dentro de un <detalle>.

    Cada dict de impuestos debe tener:
    - codigo: Código del impuesto (2=IVA, 3=ICE)
    - codigo_porcentaje: Código de la tarifa
    - tarifa: Porcentaje de la tarifa
    - base_imponible: Base imponible
    - valor: Valor del impuesto

    Args:
        impuestos: Lista de diccionarios con datos de impuestos del detalle

    Returns:
        Elemento XML <impuestos>
    """
    impuestos_elem = etree.Element("impuestos")

    for imp_data in impuestos:
        impuesto = etree.SubElement(impuestos_elem, "impuesto")
        _add_text_element(impuesto, "codigo", imp_data.get("codigo"))
        _add_text_element(
            impuesto, "codigoPorcentaje", imp_data.get("codigo_porcentaje")
        )
        _add_text_element(
            impuesto, "tarifa", format_amount(imp_data.get("tarifa", 0))
        )
        _add_text_element(
            impuesto,
            "baseImponible",
            format_amount(imp_data.get("base_imponible", 0)),
        )
        _add_text_element(
            impuesto, "valor", format_amount(imp_data.get("valor", 0))
        )

    return impuestos_elem


def _build_detalles(detalles_data: list[dict]) -> etree._Element:
    """
    Construye la sección <detalles> con los detalles (líneas) del comprobante.

    Cada dict de detalles_data debe tener:
    - codigo_principal: Código principal del producto
    - codigo_auxiliar: Código auxiliar (opcional)
    - descripcion: Descripción del producto/servicio
    - cantidad: Cantidad
    - precio_unitario: Precio unitario
    - descuento: Descuento
    - precio_total_sin_impuesto: Precio total sin impuesto
    - impuestos: Lista de dict con datos de impuestos (ver _build_impuestos_detalle)

    Args:
        detalles_data: Lista de diccionarios con datos de los detalles

    Returns:
        Elemento XML <detalles>
    """
    detalles = etree.Element("detalles")

    for det_data in detalles_data:
        detalle = etree.SubElement(detalles, "detalle")
        _add_text_element(detalle, "codigoPrincipal", det_data.get("codigo_principal"))
        _add_text_element(detalle, "codigoAuxiliar", det_data.get("codigo_auxiliar"))
        _add_text_element(detalle, "descripcion", det_data.get("descripcion"))
        _add_text_element(
            detalle,
            "cantidad",
            format_quantity(det_data.get("cantidad", 0)),
        )
        _add_text_element(
            detalle,
            "precioUnitario",
            format_quantity(det_data.get("precio_unitario", 0)),
        )
        _add_text_element(
            detalle,
            "descuento",
            format_amount(det_data.get("descuento", 0)),
        )
        _add_text_element(
            detalle,
            "precioTotalSinImpuesto",
            format_amount(det_data.get("precio_total_sin_impuesto", 0)),
        )

        # Impuestos del detalle
        impuestos_detalle = det_data.get("impuestos", [])
        if impuestos_detalle:
            detalle.append(_build_impuestos_detalle(impuestos_detalle))

    return detalles


def _build_info_adicional(info_adicional: dict | None) -> etree._Element | None:
    """
    Construye la sección <infoAdicional> con campos adicionales.

    Args:
        info_adicional: Diccionario con pares nombre-valor para campos adicionales
                       Ejemplo: {"email": "cliente@email.com", "telefono": "0991234567"}

    Returns:
        Elemento XML <infoAdicional> o None si no hay datos
    """
    if not info_adicional:
        return None

    info_adic = etree.Element("infoAdicional")

    for nombre, valor in info_adicional.items():
        if valor is not None and str(valor).strip():
            campo = etree.SubElement(info_adic, "campoAdicional")
            campo.set("nombre", nombre)
            campo.text = str(valor)

    # Si no se agregó ningún campo, devolver None
    if len(info_adic) == 0:
        return None

    return info_adic


def _build_info_factura(
    comprobante_data: dict,
    client_data: dict,
) -> etree._Element:
    """
    Construye la sección <infoFactura> para Factura (tipo 01).

    Args:
        comprobante_data: Datos del comprobante (fecha, totales, etc.)
        client_data: Datos del cliente/comprador

    Returns:
        Elemento XML <infoFactura>
    """
    info_fact = etree.Element("infoFactura")

    # Fecha de emisión
    _add_text_element(
        info_fact,
        "fechaEmision",
        format_date(comprobante_data.get("fecha_emision", date.today())),
    )

    # Dirección del establecimiento (opcional)
    _add_text_element(
        info_fact,
        "dirEstablecimiento",
        comprobante_data.get("dir_establecimiento"),
    )

    # Obligado a llevar contabilidad (opcional, puede ir en infoTributaria)
    _add_text_element(
        info_fact,
        "obligadoContabilidad",
        comprobante_data.get("obligado_contabilidad"),
    )

    # Tipo de identificación del comprador
    _add_text_element(
        info_fact,
        "tipoIdentificacionComprador",
        client_data.get("tipo_identificacion", "07"),
    )

    # Razón social del comprador
    _add_text_element(
        info_fact,
        "razonSocialComprador",
        client_data.get("razon_social", "CONSUMIDOR FINAL"),
    )

    # Identificación del comprador
    _add_text_element(
        info_fact,
        "identificacionComprador",
        client_data.get("identificacion", "9999999999999"),
    )

    # Total sin impuestos
    _add_text_element(
        info_fact,
        "totalSinImpuestos",
        format_amount(comprobante_data.get("total_sin_impuestos", 0)),
    )

    # Total descuento
    _add_text_element(
        info_fact,
        "totalDescuento",
        format_amount(comprobante_data.get("total_descuento", 0)),
    )

    # Total con impuestos
    totales_impuestos = comprobante_data.get("totales_impuestos", [])
    if totales_impuestos:
        info_fact.append(_build_total_con_impuestos(totales_impuestos))

    # Propina
    _add_text_element(
        info_fact,
        "propina",
        format_amount(comprobante_data.get("propina", 0)),
    )

    # Importe total
    _add_text_element(
        info_fact,
        "importeTotal",
        format_amount(comprobante_data.get("importe_total", 0)),
    )

    # Moneda (siempre DOLAR para Ecuador)
    _add_text_element(info_fact, "moneda", "DOLAR")

    # Pagos
    pagos = comprobante_data.get("pagos", [])
    if pagos:
        info_fact.append(_build_pagos(pagos))

    return info_fact


# ==========================================
# Generadores de XML por tipo de comprobante
# ==========================================

def _build_xml_base(
    tag_root: str,
    info_tributaria: etree._Element,
) -> etree._Element:
    """
    Construye el elemento raíz del XML con los atributos del SRI.

    Args:
        tag_root: Tag raíz según tipo de comprobante (factura, notaCredito, etc.)
        info_tributaria: Elemento <infoTributaria> ya construido

    Returns:
        Elemento raíz XML con infoTributaria agregada
    """
    root = etree.Element(tag_root, id="comprobante", version=COMPROBANTE_VERSION)
    root.append(info_tributaria)
    return root


def _xml_to_string(root: etree._Element) -> str:
    """
    Convierte un elemento XML a cadena con declaración XML y codificación UTF-8.

    Args:
        root: Elemento raíz del XML

    Returns:
        Cadena XML con declaración y codificación UTF-8
    """
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


def generate_factura_xml(
    comprobante_data: dict,
    company_data: dict,
    client_data: dict,
    detalles_data: list[dict],
    clave_acceso: str | None = None,
) -> str:
    """
    Genera el XML completo de una Factura electrónica (tipo 01).

    Estructura:
    <factura id="comprobante" version="1.1.0">
      <infoTributaria>...</infoTributaria>
      <infoFactura>...</infoFactura>
      <detalles>...</detalles>
      <infoAdicional>...</infoAdicional>
    </factura>

    Args:
        comprobante_data: Datos del comprobante con claves:
            - ambiente, tipo_emision, razon_social, nombre_comercial, ruc
            - cod_doc, estab, pto_emi, secuencial, dir_matriz
            - fecha_emision, dir_establecimiento, obligado_contabilidad
            - total_sin_impuestos, total_descuento, importe_total, propina
            - totales_impuestos: lista de dict con codigo, codigo_porcentaje, base_imponible, valor
            - pagos: lista de dict con forma_pago, total, plazo, unidad_tiempo
            - agente_retencion, contribuyente_especial, regimen_rimpe (opcionales)
        company_data: Datos de la empresa emisora (se usan para infoTributaria)
        client_data: Datos del cliente/comprador con claves:
            - tipo_identificacion, razon_social, identificacion
        detalles_data: Lista de detalles (productos/servicios)
        clave_acceso: Clave de acceso de 49 dígitos ya generada. Si es None, se genera una nueva.

    Returns:
        Cadena XML de la factura electrónica
    """
    # Combinar datos de empresa en comprobante_data para infoTributaria
    trib_data = {**comprobante_data}
    if company_data:
        # Los datos de empresa pueden venir en company_data si no están en comprobante_data
        for key in [
            "razon_social", "nombre_comercial", "ruc",
            "dir_matriz", "agente_retencion",
            "contribuyente_especial", "obligado_contabilidad",
            "regimen_rimpe", "regimen_microempresas",
        ]:
            if key not in trib_data and key in company_data:
                trib_data[key] = company_data[key]

    # Usar clave de acceso proporcionada o generar una nueva
    if clave_acceso is None:
        clave_acceso = generate_clave_acceso(
            fecha_emision=comprobante_data.get("fecha_emision", date.today()),
            tipo_comprobante=comprobante_data.get("cod_doc", "01"),
            ruc=trib_data.get("ruc", ""),
            ambiente=comprobante_data.get("ambiente", "1"),
            establecimiento=comprobante_data.get("estab", "001"),
            punto_emision=comprobante_data.get("pto_emi", "001"),
            secuencial=comprobante_data.get("secuencial", "000000001"),
            codigo_numerico=comprobante_data.get("codigo_numerico"),
            tipo_emision=comprobante_data.get("tipo_emision", "1"),
        )

    # Construir secciones del XML
    info_tributaria = _build_info_tributaria(trib_data, clave_acceso)
    root = _build_xml_base("factura", info_tributaria)

    # InfoFactura
    info_factura = _build_info_factura(comprobante_data, client_data)
    root.append(info_factura)

    # Detalles
    if detalles_data:
        root.append(_build_detalles(detalles_data))

    # InfoAdicional
    info_adicional = comprobante_data.get("info_adicional")
    info_adic_elem = _build_info_adicional(info_adicional)
    if info_adic_elem is not None:
        root.append(info_adic_elem)

    return _xml_to_string(root)


def generate_nota_credito_xml(
    comprobante_data: dict,
    company_data: dict,
    client_data: dict,
    detalles_data: list[dict],
    clave_acceso: str | None = None,
) -> str:
    """
    Genera el XML completo de una Nota de Crédito electrónica (tipo 04).

    Estructura:
    <notaCredito id="comprobante" version="1.1.0">
      <infoTributaria>...</infoTributaria>
      <infoNotaCredito>...</infoNotaCredito>
      <detalles>...</detalles>
      <infoAdicional>...</infoAdicional>
    </notaCredito>

    Args:
        comprobante_data: Datos del comprobante. Incluye además:
            - cod_doc_modificado: Tipo de comprobante modificado (01, 03, etc.)
            - num_doc_modificado: Número del documento modificado (estab-ptoEmi-secuencial)
            - fecha_emision_doc_sustento: Fecha del documento sustento
            - motivo: Motivo de la nota de crédito
            - rise: RISE (opcional)
            - valor_modificacion: Valor de la modificación
        company_data: Datos de la empresa emisora
        client_data: Datos del cliente/comprador
        detalles_data: Lista de detalles

    Returns:
        Cadena XML de la nota de crédito electrónica
    """
    # Combinar datos de empresa
    trib_data = {**comprobante_data}
    if company_data:
        for key in [
            "razon_social", "nombre_comercial", "ruc",
            "dir_matriz", "agente_retencion",
            "contribuyente_especial", "obligado_contabilidad",
            "regimen_rimpe", "regimen_microempresas",
        ]:
            if key not in trib_data and key in company_data:
                trib_data[key] = company_data[key]

    # Usar clave de acceso proporcionada o generar una nueva
    if clave_acceso is None:
        clave_acceso = generate_clave_acceso(
            fecha_emision=comprobante_data.get("fecha_emision", date.today()),
            tipo_comprobante="04",
            ruc=trib_data.get("ruc", ""),
            ambiente=comprobante_data.get("ambiente", "1"),
            establecimiento=comprobante_data.get("estab", "001"),
            punto_emision=comprobante_data.get("pto_emi", "001"),
            secuencial=comprobante_data.get("secuencial", "000000001"),
            codigo_numerico=comprobante_data.get("codigo_numerico"),
            tipo_emision=comprobante_data.get("tipo_emision", "1"),
        )

    info_tributaria = _build_info_tributaria(trib_data, clave_acceso)
    root = _build_xml_base("notaCredito", info_tributaria)

    # InfoNotaCredito
    info_nc = etree.Element("infoNotaCredito")

    _add_text_element(
        info_nc,
        "fechaEmision",
        format_date(comprobante_data.get("fecha_emision", date.today())),
    )
    _add_text_element(
        info_nc,
        "dirEstablecimiento",
        comprobante_data.get("dir_establecimiento"),
    )
    _add_text_element(
        info_nc,
        "tipoIdentificacionComprador",
        client_data.get("tipo_identificacion", "07"),
    )
    _add_text_element(
        info_nc,
        "razonSocialComprador",
        client_data.get("razon_social", "CONSUMIDOR FINAL"),
    )
    _add_text_element(
        info_nc,
        "identificacionComprador",
        client_data.get("identificacion", "9999999999999"),
    )
    _add_text_element(
        info_nc,
        "obligadoContabilidad",
        comprobante_data.get("obligado_contabilidad"),
    )
    _add_text_element(
        info_nc,
        "rise",
        comprobante_data.get("rise"),
    )
    _add_text_element(
        info_nc,
        "codDocModificado",
        comprobante_data.get("cod_doc_modificado"),
    )
    _add_text_element(
        info_nc,
        "numDocModificado",
        comprobante_data.get("num_doc_modificado"),
    )
    _add_text_element(
        info_nc,
        "fechaEmisionDocSustento",
        format_date(comprobante_data.get("fecha_emision_doc_sustento", date.today())),
    )
    _add_text_element(
        info_nc,
        "motivo",
        comprobante_data.get("motivo", "DEVOLUCIÓN"),
    )
    _add_text_element(
        info_nc,
        "valorModificacion",
        format_amount(comprobante_data.get("valor_modificacion", 0)),
    )

    # Total sin impuestos
    _add_text_element(
        info_nc,
        "totalSinImpuestos",
        format_amount(comprobante_data.get("total_sin_impuestos", 0)),
    )

    # Total descuento (opcional para NC)
    _add_text_element(
        info_nc,
        "totalDescuento",
        format_amount(comprobante_data.get("total_descuento", 0)),
    )

    # Total con impuestos
    totales_impuestos = comprobante_data.get("totales_impuestos", [])
    if totales_impuestos:
        info_nc.append(_build_total_con_impuestos(totales_impuestos))

    _add_text_element(
        info_nc,
        "propina",
        format_amount(comprobante_data.get("propina", 0)),
    )

    _add_text_element(
        info_nc,
        "importeTotal",
        format_amount(comprobante_data.get("importe_total", 0)),
    )

    _add_text_element(info_nc, "moneda", "DOLAR")

    root.append(info_nc)

    # Detalles
    if detalles_data:
        root.append(_build_detalles(detalles_data))

    # InfoAdicional
    info_adic_elem = _build_info_adicional(comprobante_data.get("info_adicional"))
    if info_adic_elem is not None:
        root.append(info_adic_elem)

    return _xml_to_string(root)


def generate_nota_debito_xml(
    comprobante_data: dict,
    company_data: dict,
    client_data: dict,
    detalles_data: list[dict],
    clave_acceso: str | None = None,
) -> str:
    """
    Genera el XML completo de una Nota de Débito electrónica (tipo 05).

    Estructura:
    <notaDebito id="comprobante" version="1.1.0">
      <infoTributaria>...</infoTributaria>
      <infoNotaDebito>...</infoNotaDebito>
      <motivos>...</motivos>
      <infoAdicional>...</infoAdicional>
    </notaDebito>

    Args:
        comprobante_data: Datos del comprobante. Incluye además:
            - cod_doc_modificado: Tipo de comprobante modificado
            - num_doc_modificado: Número del documento modificado
            - fecha_emision_doc_sustento: Fecha del documento sustento
            - motivos: Lista de dict con razon, valor
        company_data: Datos de la empresa emisora
        client_data: Datos del cliente/comprador
        detalles_data: No se usa directamente; los motivos van en comprobante_data["motivos_nd"]

    Returns:
        Cadena XML de la nota de débito electrónica
    """
    # Combinar datos de empresa
    trib_data = {**comprobante_data}
    if company_data:
        for key in [
            "razon_social", "nombre_comercial", "ruc",
            "dir_matriz", "agente_retencion",
            "contribuyente_especial", "obligado_contabilidad",
            "regimen_rimpe", "regimen_microempresas",
        ]:
            if key not in trib_data and key in company_data:
                trib_data[key] = company_data[key]

    # Usar clave de acceso proporcionada o generar una nueva
    if clave_acceso is None:
        clave_acceso = generate_clave_acceso(
            fecha_emision=comprobante_data.get("fecha_emision", date.today()),
            tipo_comprobante="05",
            ruc=trib_data.get("ruc", ""),
            ambiente=comprobante_data.get("ambiente", "1"),
            establecimiento=comprobante_data.get("estab", "001"),
            punto_emision=comprobante_data.get("pto_emi", "001"),
            secuencial=comprobante_data.get("secuencial", "000000001"),
            codigo_numerico=comprobante_data.get("codigo_numerico"),
            tipo_emision=comprobante_data.get("tipo_emision", "1"),
        )

    info_tributaria = _build_info_tributaria(trib_data, clave_acceso)
    root = _build_xml_base("notaDebito", info_tributaria)

    # InfoNotaDebito
    info_nd = etree.Element("infoNotaDebito")

    _add_text_element(
        info_nd,
        "fechaEmision",
        format_date(comprobante_data.get("fecha_emision", date.today())),
    )
    _add_text_element(
        info_nd,
        "dirEstablecimiento",
        comprobante_data.get("dir_establecimiento"),
    )
    _add_text_element(
        info_nd,
        "tipoIdentificacionComprador",
        client_data.get("tipo_identificacion", "07"),
    )
    _add_text_element(
        info_nd,
        "razonSocialComprador",
        client_data.get("razon_social", "CONSUMIDOR FINAL"),
    )
    _add_text_element(
        info_nd,
        "identificacionComprador",
        client_data.get("identificacion", "9999999999999"),
    )
    _add_text_element(
        info_nd,
        "obligadoContabilidad",
        comprobante_data.get("obligado_contabilidad"),
    )
    _add_text_element(
        info_nd,
        "rise",
        comprobante_data.get("rise"),
    )
    _add_text_element(
        info_nd,
        "codDocModificado",
        comprobante_data.get("cod_doc_modificado"),
    )
    _add_text_element(
        info_nd,
        "numDocModificado",
        comprobante_data.get("num_doc_modificado"),
    )
    _add_text_element(
        info_nd,
        "fechaEmisionDocSustento",
        format_date(comprobante_data.get("fecha_emision_doc_sustento", date.today())),
    )
    _add_text_element(
        info_nd,
        "totalSinImpuestos",
        format_amount(comprobante_data.get("total_sin_impuestos", 0)),
    )

    # Total descuento (opcional para ND)
    _add_text_element(
        info_nd,
        "totalDescuento",
        format_amount(comprobante_data.get("total_descuento", 0)),
    )

    # Total con impuestos
    totales_impuestos = comprobante_data.get("totales_impuestos", [])
    if totales_impuestos:
        info_nd.append(_build_total_con_impuestos(totales_impuestos))

    _add_text_element(
        info_nd,
        "propina",
        format_amount(comprobante_data.get("propina", 0)),
    )

    _add_text_element(
        info_nd,
        "importeTotal",
        format_amount(comprobante_data.get("importe_total", 0)),
    )

    _add_text_element(info_nd, "moneda", "DOLAR")

    # Pagos (opcional para ND)
    pagos = comprobante_data.get("pagos", [])
    if pagos:
        info_nd.append(_build_pagos(pagos))

    root.append(info_nd)

    # Motivos (en ND se usan "motivos" en lugar de "detalles")
    motivos_data = comprobante_data.get("motivos_nd", [])
    if motivos_data:
        motivos_elem = etree.Element("motivos")
        for motivo_data in motivos_data:
            motivo = etree.SubElement(motivos_elem, "motivo")
            _add_text_element(motivo, "razon", motivo_data.get("razon"))
            _add_text_element(
                motivo,
                "valor",
                format_amount(motivo_data.get("valor", 0)),
            )
        root.append(motivos_elem)

    # InfoAdicional
    info_adic_elem = _build_info_adicional(comprobante_data.get("info_adicional"))
    if info_adic_elem is not None:
        root.append(info_adic_elem)

    return _xml_to_string(root)


def generate_comprobante_retencion_xml(
    comprobante_data: dict,
    company_data: dict,
    client_data: dict,
    clave_acceso: str | None = None,
) -> str:
    """
    Genera el XML completo de un Comprobante de Retención electrónico (tipo 07).

    Estructura:
    <comprobanteRetencion id="comprobante" version="1.1.0">
      <infoTributaria>...</infoTributaria>
      <infoCompRetencion>...</infoCompRetencion>
      <impuestos>...</impuestos>
      <infoAdicional>...</infoAdicional>
    </comprobanteRetencion>

    Args:
        comprobante_data: Datos del comprobante. Incluye:
            - fecha_emision: Fecha de emisión
            - periodo_fiscal: Período fiscal (MM/YYYY)
            - dir_establecimiento: Dirección del establecimiento (opcional)
            - obligado_contabilidad: SI/NO (opcional)
            - tipo_emision: Tipo de emisión
            - rise: RISE (opcional)
            - impuestos: Lista de dict con:
                - codigo: Código del impuesto (1=renta, 2=iva)
                - codigo_retencion: Código de retención
                - base_imponible: Base imponible
                - porcentaje_retener: Porcentaje a retener
                - valor_retenido: Valor retenido
                - cod_doc_sustento: Código del doc sustento (opcional)
                - num_doc_sustento: Número del doc sustento (opcional)
                - fecha_emision_doc_sustento: Fecha doc sustento (opcional)
        company_data: Datos de la empresa emisora
        client_data: Datos del sujeto retenido

    Returns:
        Cadena XML del comprobante de retención electrónica
    """
    # Combinar datos de empresa
    trib_data = {**comprobante_data}
    if company_data:
        for key in [
            "razon_social", "nombre_comercial", "ruc",
            "dir_matriz", "agente_retencion",
            "contribuyente_especial", "obligado_contabilidad",
            "regimen_rimpe", "regimen_microempresas",
        ]:
            if key not in trib_data and key in company_data:
                trib_data[key] = company_data[key]

    # Usar clave de acceso proporcionada o generar una nueva
    if clave_acceso is None:
        clave_acceso = generate_clave_acceso(
            fecha_emision=comprobante_data.get("fecha_emision", date.today()),
            tipo_comprobante="07",
            ruc=trib_data.get("ruc", ""),
            ambiente=comprobante_data.get("ambiente", "1"),
            establecimiento=comprobante_data.get("estab", "001"),
            punto_emision=comprobante_data.get("pto_emi", "001"),
            secuencial=comprobante_data.get("secuencial", "000000001"),
            codigo_numerico=comprobante_data.get("codigo_numerico"),
            tipo_emision=comprobante_data.get("tipo_emision", "1"),
        )

    info_tributaria = _build_info_tributaria(trib_data, clave_acceso)
    root = _build_xml_base("comprobanteRetencion", info_tributaria)

    # InfoCompRetencion
    info_cr = etree.Element("infoCompRetencion")

    _add_text_element(
        info_cr,
        "fechaEmision",
        format_date(comprobante_data.get("fecha_emision", date.today())),
    )
    _add_text_element(
        info_cr,
        "dirEstablecimiento",
        comprobante_data.get("dir_establecimiento"),
    )
    _add_text_element(
        info_cr,
        "obligadoContabilidad",
        comprobante_data.get("obligado_contabilidad"),
    )
    _add_text_element(
        info_cr,
        "tipoIdentificacionSujetoRetenido",
        client_data.get("tipo_identificacion", "04"),
    )
    _add_text_element(
        info_cr,
        "razonSocialSujetoRetenido",
        client_data.get("razon_social", "CONSUMIDOR FINAL"),
    )
    _add_text_element(
        info_cr,
        "identificacionSujetoRetenido",
        client_data.get("identificacion", "9999999999999"),
    )
    _add_text_element(
        info_cr,
        "periodoFiscal",
        comprobante_data.get("periodo_fiscal"),
    )

    root.append(info_cr)

    # Impuestos (retenciones)
    impuestos_data = comprobante_data.get("impuestos", [])
    if impuestos_data:
        impuestos_elem = etree.Element("impuestos")
        for imp_data in impuestos_data:
            impuesto = etree.SubElement(impuestos_elem, "impuesto")
            _add_text_element(impuesto, "codigo", imp_data.get("codigo"))
            _add_text_element(
                impuesto, "codigoRetencion", imp_data.get("codigo_retencion")
            )
            _add_text_element(
                impuesto,
                "baseImponible",
                format_amount(imp_data.get("base_imponible", 0)),
            )
            _add_text_element(
                impuesto,
                "porcentajeRetener",
                format_amount(imp_data.get("porcentaje_retener", 0)),
            )
            _add_text_element(
                impuesto,
                "valorRetenido",
                format_amount(imp_data.get("valor_retenido", 0)),
            )
            _add_text_element(
                impuesto, "codDocSustento", imp_data.get("cod_doc_sustento")
            )
            _add_text_element(
                impuesto, "numDocSustento", imp_data.get("num_doc_sustento")
            )
            _add_text_element(
                impuesto,
                "fechaEmisionDocSustento",
                format_date(imp_data["fecha_emision_doc_sustento"])
                if imp_data.get("fecha_emision_doc_sustento")
                else None,
            )
        root.append(impuestos_elem)

    # InfoAdicional
    info_adic_elem = _build_info_adicional(comprobante_data.get("info_adicional"))
    if info_adic_elem is not None:
        root.append(info_adic_elem)

    return _xml_to_string(root)


def generate_guia_remision_xml(
    comprobante_data: dict,
    company_data: dict,
    client_data: dict,
    clave_acceso: str | None = None,
) -> str:
    """
    Genera el XML completo de una Guía de Remisión electrónica (tipo 06).

    Estructura:
    <guiaRemision id="comprobante" version="1.1.0">
      <infoTributaria>...</infoTributaria>
      <infoGuiaRemision>...</infoGuiaRemision>
      <destinatarios>...</destinatarios>
      <infoAdicional>...</infoAdicional>
    </guiaRemision>

    Args:
        comprobante_data: Datos del comprobante. Incluye:
            - dir_establecimiento: Dirección del establecimiento
            - dir_partida: Dirección de partida
            - raz_soc_transportista: Razón social del transportista
            - tipo_ident_transportista: Tipo identificación transportista
            - ruc_transportista: RUC del transportista
            - rise: RISE (opcional)
            - obligado_contabilidad: SI/NO (opcional)
            - fecha_ini_transporte: Fecha inicio transporte
            - fecha_fin_transporte: Fecha fin transporte
            - placa: Placa del vehículo (opcional)
            - destinatarios: Lista de dict con:
                - identificacion_destinatario: Identificación del destinatario
                - razon_social_destinatario: Razón social del destinatario
                - dir_destinatario: Dirección del destinatario
                - motivo_traslado: Motivo del traslado
                - doc_aduanero: Documento aduanero (opcional)
                - cod_estab_destino: Código establecimiento destino (opcional)
                - ruta: Ruta de transporte (opcional)
                - cod_doc_sustento: Código doc sustento (opcional)
                - num_doc_sustento: Número doc sustento (opcional)
                - num_aut_doc_sustento: Número autorización doc sustento (opcional)
                - fecha_emision_doc_sustento: Fecha doc sustento (opcional)
                - detalles: Lista de dict con codigo_interno, descripcion, cantidad
        company_data: Datos de la empresa emisora
        client_data: No se usa directamente en guía de remisión

    Returns:
        Cadena XML de la guía de remisión electrónica
    """
    # Combinar datos de empresa
    trib_data = {**comprobante_data}
    if company_data:
        for key in [
            "razon_social", "nombre_comercial", "ruc",
            "dir_matriz", "agente_retencion",
            "contribuyente_especial", "obligado_contabilidad",
            "regimen_rimpe", "regimen_microempresas",
        ]:
            if key not in trib_data and key in company_data:
                trib_data[key] = company_data[key]

    # Usar clave de acceso proporcionada o generar una nueva
    if clave_acceso is None:
        clave_acceso = generate_clave_acceso(
            fecha_emision=comprobante_data.get("fecha_emision", date.today()),
            tipo_comprobante="06",
            ruc=trib_data.get("ruc", ""),
            ambiente=comprobante_data.get("ambiente", "1"),
            establecimiento=comprobante_data.get("estab", "001"),
            punto_emision=comprobante_data.get("pto_emi", "001"),
            secuencial=comprobante_data.get("secuencial", "000000001"),
            codigo_numerico=comprobante_data.get("codigo_numerico"),
            tipo_emision=comprobante_data.get("tipo_emision", "1"),
        )

    info_tributaria = _build_info_tributaria(trib_data, clave_acceso)
    root = _build_xml_base("guiaRemision", info_tributaria)

    # InfoGuiaRemision
    info_gr = etree.Element("infoGuiaRemision")

    _add_text_element(
        info_gr,
        "fechaEmision",
        format_date(comprobante_data.get("fecha_emision", date.today())),
    )
    _add_text_element(
        info_gr,
        "dirEstablecimiento",
        comprobante_data.get("dir_establecimiento"),
    )
    _add_text_element(
        info_gr,
        "dirPartida",
        comprobante_data.get("dir_partida"),
    )
    _add_text_element(
        info_gr,
        "razonSocialTransportista",
        comprobante_data.get("raz_soc_transportista"),
    )
    _add_text_element(
        info_gr,
        "tipoIdentificacionTransportista",
        comprobante_data.get("tipo_ident_transportista"),
    )
    _add_text_element(
        info_gr,
        "rucTransportista",
        comprobante_data.get("ruc_transportista"),
    )
    _add_text_element(
        info_gr,
        "rise",
        comprobante_data.get("rise"),
    )
    _add_text_element(
        info_gr,
        "obligadoContabilidad",
        comprobante_data.get("obligado_contabilidad"),
    )
    _add_text_element(
        info_gr,
        "fechaIniTransporte",
        format_date(comprobante_data.get("fecha_ini_transporte", date.today())),
    )
    _add_text_element(
        info_gr,
        "fechaFinTransporte",
        format_date(comprobante_data.get("fecha_fin_transporte", date.today())),
    )
    _add_text_element(
        info_gr,
        "placa",
        comprobante_data.get("placa"),
    )

    root.append(info_gr)

    # Destinatarios
    destinatarios_data = comprobante_data.get("destinatarios", [])
    if destinatarios_data:
        destinatarios_elem = etree.Element("destinatarios")
        for dest_data in destinatarios_data:
            destinatario = etree.SubElement(destinatarios_elem, "destinatario")
            _add_text_element(
                destinatario,
                "identificacionDestinatario",
                dest_data.get("identificacion_destinatario"),
            )
            _add_text_element(
                destinatario,
                "razonSocialDestinatario",
                dest_data.get("razon_social_destinatario"),
            )
            _add_text_element(
                destinatario,
                "dirDestinatario",
                dest_data.get("dir_destinatario"),
            )
            _add_text_element(
                destinatario,
                "motivoTraslado",
                dest_data.get("motivo_traslado"),
            )
            _add_text_element(
                destinatario,
                "docAduanero",
                dest_data.get("doc_aduanero"),
            )
            _add_text_element(
                destinatario,
                "codEstabDestino",
                dest_data.get("cod_estab_destino"),
            )
            _add_text_element(
                destinatario,
                "ruta",
                dest_data.get("ruta"),
            )
            _add_text_element(
                destinatario,
                "codDocSustento",
                dest_data.get("cod_doc_sustento"),
            )
            _add_text_element(
                destinatario,
                "numDocSustento",
                dest_data.get("num_doc_sustento"),
            )
            _add_text_element(
                destinatario,
                "numAutDocSustento",
                dest_data.get("num_aut_doc_sustento"),
            )
            _add_text_element(
                destinatario,
                "fechaEmisionDocSustento",
                format_date(dest_data["fecha_emision_doc_sustento"])
                if dest_data.get("fecha_emision_doc_sustento")
                else None,
            )

            # Detalles dentro del destinatario
            detalles_dest = dest_data.get("detalles", [])
            if detalles_dest:
                detalles_elem = etree.SubElement(destinatario, "detalles")
                for det_data in detalles_dest:
                    detalle = etree.SubElement(detalles_elem, "detalle")
                    _add_text_element(
                        detalle,
                        "codigoInterno",
                        det_data.get("codigo_interno"),
                    )
                    _add_text_element(
                        detalle,
                        "descripcion",
                        det_data.get("descripcion"),
                    )
                    _add_text_element(
                        detalle,
                        "cantidad",
                        format_quantity(det_data.get("cantidad", 0)),
                    )

        root.append(destinatarios_elem)

    # InfoAdicional
    info_adic_elem = _build_info_adicional(comprobante_data.get("info_adicional"))
    if info_adic_elem is not None:
        root.append(info_adic_elem)

    return _xml_to_string(root)


def generate_liquidacion_compra_xml(
    comprobante_data: dict,
    company_data: dict,
    client_data: dict,
    detalles_data: list[dict],
    clave_acceso: str | None = None,
) -> str:
    """
    Genera el XML completo de una Liquidación de Compra electrónica (tipo 03).

    Estructura:
    <liquidacionCompra id="comprobante" version="1.1.0">
      <infoTributaria>...</infoTributaria>
      <infoLiquidacionCompra>...</infoLiquidacionCompra>
      <detalles>...</detalles>
      <infoAdicional>...</infoAdicional>
    </liquidacionCompra>

    Args:
        comprobante_data: Datos del comprobante. Incluye:
            - dir_establecimiento: Dirección del establecimiento
            - obligado_contabilidad: SI/NO (opcional)
            - total_sin_impuestos, total_descuento, importe_total, propina
            - totales_impuestos: Lista de dict con datos de impuestos
            - pagos: Lista de dict con formas de pago
            - rise: RISE (opcional)
        company_data: Datos de la empresa emisora
        client_data: Datos del vendedor/proveedor
        detalles_data: Lista de detalles (productos/servicios)

    Returns:
        Cadena XML de la liquidación de compra electrónica
    """
    # Combinar datos de empresa
    trib_data = {**comprobante_data}
    if company_data:
        for key in [
            "razon_social", "nombre_comercial", "ruc",
            "dir_matriz", "agente_retencion",
            "contribuyente_especial", "obligado_contabilidad",
            "regimen_rimpe", "regimen_microempresas",
        ]:
            if key not in trib_data and key in company_data:
                trib_data[key] = company_data[key]

    # Usar clave de acceso proporcionada o generar una nueva
    if clave_acceso is None:
        clave_acceso = generate_clave_acceso(
            fecha_emision=comprobante_data.get("fecha_emision", date.today()),
            tipo_comprobante="03",
            ruc=trib_data.get("ruc", ""),
            ambiente=comprobante_data.get("ambiente", "1"),
            establecimiento=comprobante_data.get("estab", "001"),
            punto_emision=comprobante_data.get("pto_emi", "001"),
            secuencial=comprobante_data.get("secuencial", "000000001"),
            codigo_numerico=comprobante_data.get("codigo_numerico"),
            tipo_emision=comprobante_data.get("tipo_emision", "1"),
        )

    info_tributaria = _build_info_tributaria(trib_data, clave_acceso)
    root = _build_xml_base("liquidacionCompra", info_tributaria)

    # InfoLiquidacionCompra
    info_lc = etree.Element("infoLiquidacionCompra")

    _add_text_element(
        info_lc,
        "fechaEmision",
        format_date(comprobante_data.get("fecha_emision", date.today())),
    )
    _add_text_element(
        info_lc,
        "dirEstablecimiento",
        comprobante_data.get("dir_establecimiento"),
    )
    _add_text_element(
        info_lc,
        "obligadoContabilidad",
        comprobante_data.get("obligado_contabilidad"),
    )
    _add_text_element(
        info_lc,
        "tipoIdentificacionVendedor",
        client_data.get("tipo_identificacion", "04"),
    )
    _add_text_element(
        info_lc,
        "razonSocialVendedor",
        client_data.get("razon_social"),
    )
    _add_text_element(
        info_lc,
        "identificacionVendedor",
        client_data.get("identificacion"),
    )
    _add_text_element(
        info_lc,
        "rise",
        comprobante_data.get("rise"),
    )
    _add_text_element(
        info_lc,
        "totalSinImpuestos",
        format_amount(comprobante_data.get("total_sin_impuestos", 0)),
    )
    _add_text_element(
        info_lc,
        "totalDescuento",
        format_amount(comprobante_data.get("total_descuento", 0)),
    )

    # Total con impuestos
    totales_impuestos = comprobante_data.get("totales_impuestos", [])
    if totales_impuestos:
        info_lc.append(_build_total_con_impuestos(totales_impuestos))

    _add_text_element(
        info_lc,
        "propina",
        format_amount(comprobante_data.get("propina", 0)),
    )
    _add_text_element(
        info_lc,
        "importeTotal",
        format_amount(comprobante_data.get("importe_total", 0)),
    )
    _add_text_element(info_lc, "moneda", "DOLAR")

    # Pagos
    pagos = comprobante_data.get("pagos", [])
    if pagos:
        info_lc.append(_build_pagos(pagos))

    root.append(info_lc)

    # Detalles
    if detalles_data:
        root.append(_build_detalles(detalles_data))

    # InfoAdicional
    info_adic_elem = _build_info_adicional(comprobante_data.get("info_adicional"))
    if info_adic_elem is not None:
        root.append(info_adic_elem)

    return _xml_to_string(root)
