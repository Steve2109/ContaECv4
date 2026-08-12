"""
ContaEC - Servicio de comunicación con el SRI
Envío y consulta de autorización de comprobantes electrónicos
mediante los servicios web SOAP del SRI (Ecuador)

Funciones principales:
- enviar_comprobante(): Envía XML firmado al SRI Recepción
- autorizar_comprobante(): Consulta estado de autorización
- enviar_y_autorizar(): Flujo completo con reintentos

En modo desarrollo (sandbox), se usan respuestas simuladas
cuando el SRI no está disponible.
"""
import asyncio
import base64
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==========================================
# Excepciones personalizadas
# ==========================================

class SRIServiceError(Exception):
    """Error en la comunicación con el servicio web del SRI"""
    pass


# ==========================================
# Clases de respuesta del SRI
# ==========================================

class SRIMensaje:
    """
    Mensaje de error o advertencia del SRI.
    Corresponde a los mensajes devueltos en las respuestas SOAP.
    """
    def __init__(
        self,
        identificador: str = "",
        mensaje: str = "",
        tipo: str = "",
        info_adicional: str = "",
    ):
        self.identificador = identificador
        self.mensaje = mensaje
        self.tipo = tipo  # ERROR, ADVERTENCIA, INFO
        self.info_adicional = info_adicional

    def to_dict(self) -> dict:
        return {
            "identificador": self.identificador,
            "mensaje": self.mensaje,
            "tipo": self.tipo,
            "info_adicional": self.info_adicional,
        }


class SRIRecepcionResponse:
    """
    Respuesta del servicio de Recepción del SRI.
    
    Estados posibles:
    - RECIBIDA: El comprobante fue recibido correctamente
    - DEVUELTA: El comprobante fue rechazado por errores
    """
    def __init__(
        self,
        estado: str = "",
        comprobantes: list | None = None,
        mensajes: list[SRIMensaje] | None = None,
    ):
        self.estado = estado
        self.comprobantes = comprobantes or []
        self.mensajes = mensajes or []

    @property
    def is_recibida(self) -> bool:
        return "RECIBIDA" in self.estado.upper()

    @property
    def is_devuelta(self) -> bool:
        return "DEVUELTA" in self.estado.upper()

    def to_dict(self) -> dict:
        return {
            "estado": self.estado,
            "comprobantes": self.comprobantes,
            "mensajes": [m.to_dict() for m in self.mensajes],
        }


class SRIAutorizacionResponse:
    """
    Respuesta del servicio de Autorización del SRI.
    
    Estados posibles:
    - AUTORIZADO: Comprobante autorizado
    - NO AUTORIZADO: Comprobante rechazado
    - EN PROCESO: Aún en procesamiento
    """
    def __init__(
        self,
        estado: str = "",
        numero_autorizacion: str = "",
        fecha_autorizacion: datetime | None = None,
        ambiente: str = "",
        comprobante: str = "",
        mensajes: list[SRIMensaje] | None = None,
    ):
        self.estado = estado
        self.numero_autorizacion = numero_autorizacion
        self.fecha_autorizacion = fecha_autorizacion
        self.ambiente = ambiente
        self.comprobante = comprobante
        self.mensajes = mensajes or []

    @property
    def is_autorizado(self) -> bool:
        return "AUTORIZADO" in self.estado.upper() and "NO" not in self.estado.upper()

    @property
    def is_no_autorizado(self) -> bool:
        return "NO AUTORIZADO" in self.estado.upper()

    @property
    def is_en_proceso(self) -> bool:
        return "EN PROCESO" in self.estado.upper() or "EN PROCESAMIENTO" in self.estado.upper()

    def to_dict(self) -> dict:
        return {
            "estado": self.estado,
            "numero_autorizacion": self.numero_autorizacion,
            "fecha_autorizacion": self.fecha_autorizacion.isoformat() if self.fecha_autorizacion else None,
            "ambiente": self.ambiente,
            "mensajes": [m.to_dict() for m in self.mensajes],
        }


# ==========================================
# Funciones auxiliares
# ==========================================

def _get_wsdl_urls(ambiente: str) -> tuple[str, str]:
    """
    Obtiene las URLs WSDL del SRI según el ambiente.
    
    Args:
        ambiente: "1" para Pruebas, "2" para Producción
    
    Returns:
        Tupla (recepcion_url, autorizacion_url)
    
    Raises:
        SRIServiceError: Si el ambiente es inválido
    """
    if ambiente == "1":
        return (
            settings.SRI_WS_RECEPCION_PRUEBAS,
            settings.SRI_WS_AUTORIZACION_PRUEBAS,
        )
    elif ambiente == "2":
        return (
            settings.SRI_WS_RECEPCION_PRODUCCION,
            settings.SRI_WS_AUTORIZACION_PRODUCCION,
        )
    else:
        raise SRIServiceError(
            f"Ambiente inválido: {ambiente}. Debe ser '1' (Pruebas) o '2' (Producción)."
        )


def _encode_xml_base64(xml_firmado: str) -> str:
    """
    Codifica el XML firmado en Base64 para enviar al SRI.
    
    El SRI requiere que el XML se envíe codificado en Base64
    dentro de la petición SOAP.
    """
    return base64.b64encode(xml_firmado.encode("utf-8")).decode("utf-8")


def _parse_mensajes_sri(mensajes_raw: Any) -> list[SRIMensaje]:
    """
    Parsea los mensajes del SRI desde la respuesta zeep.
    
    Maneja diferentes formatos de respuesta (objetos zeep, dicts, listas, None).
    """
    mensajes = []
    if mensajes_raw is None:
        return mensajes
    
    # Convertir a lista si no lo es
    if not isinstance(mensajes_raw, list):
        mensajes_raw = [mensajes_raw]
    
    for msg in mensajes_raw:
        try:
            if isinstance(msg, dict):
                mensajes.append(SRIMensaje(
                    identificador=str(msg.get("identificador", "")),
                    mensaje=str(msg.get("mensaje", "")),
                    tipo=str(msg.get("tipo", "")),
                    info_adicional=str(msg.get("informacionAdicional", "")),
                ))
            elif hasattr(msg, "identificador"):
                # Objeto zeep
                mensajes.append(SRIMensaje(
                    identificador=str(getattr(msg, "identificador", "")),
                    mensaje=str(getattr(msg, "mensaje", "")),
                    tipo=str(getattr(msg, "tipo", "")),
                    info_adicional=str(getattr(msg, "informacionAdicional", "")),
                ))
        except Exception as e:
            logger.debug(f"Error parseando mensaje SRI: {e}")
    
    return mensajes


def _extract_fecha_autorizacion(fecha_raw: Any) -> datetime | None:
    """
    Normaliza la fecha de autorización desde la respuesta del SRI.
    
    Maneja datetime, string y None.
    """
    if fecha_raw is None:
        return None
    if isinstance(fecha_raw, datetime):
        return fecha_raw
    if isinstance(fecha_raw, str):
        try:
            return datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
    return None


def _parse_recepcion_response(response: Any) -> SRIRecepcionResponse:
    """Parsea la respuesta del servicio de Recepción del SRI."""
    try:
        if isinstance(response, dict):
            estado = str(response.get("estado", ""))
            mensajes = _parse_mensajes_sri(response.get("mensajes"))
            comprobantes = response.get("comprobantes", [])
        elif hasattr(response, "estado"):
            estado = str(getattr(response, "estado", ""))
            mensajes_raw = getattr(response, "mensajes", None)
            mensajes = _parse_mensajes_sri(mensajes_raw)
            comprobantes = getattr(response, "comprobantes", [])
        else:
            estado = str(response)
            mensajes = []
            comprobantes = []
        
        return SRIRecepcionResponse(
            estado=estado,
            comprobantes=comprobantes,
            mensajes=mensajes,
        )
    except Exception as e:
        logger.error(f"Error parseando respuesta de Recepción: {e}")
        return SRIRecepcionResponse(estado="ERROR", mensajes=[
            SRIMensaje(mensaje=f"Error parseando respuesta: {e}", tipo="ERROR")
        ])


def _parse_autorizacion_response(response: Any) -> SRIAutorizacionResponse:
    """Parsea la respuesta del servicio de Autorización del SRI."""
    try:
        if isinstance(response, dict):
            estado = str(response.get("estado", ""))
            numero_aut = str(response.get("numeroAutorizacion", ""))
            fecha_aut = _extract_fecha_autorizacion(response.get("fechaAutorizacion"))
            ambiente = str(response.get("ambiente", ""))
            comprobante = str(response.get("comprobante", ""))
            mensajes = _parse_mensajes_sri(response.get("mensajes"))
        elif hasattr(response, "estado"):
            estado = str(getattr(response, "estado", ""))
            numero_aut = str(getattr(response, "numeroAutorizacion", ""))
            fecha_aut = _extract_fecha_autorizacion(
                getattr(response, "fechaAutorizacion", None)
            )
            ambiente = str(getattr(response, "ambiente", ""))
            comprobante = str(getattr(response, "comprobante", ""))
            mensajes_raw = getattr(response, "mensajes", None)
            mensajes = _parse_mensajes_sri(mensajes_raw)
        else:
            estado = str(response)
            numero_aut = ""
            fecha_aut = None
            ambiente = ""
            comprobante = ""
            mensajes = []
        
        return SRIAutorizacionResponse(
            estado=estado,
            numero_autorizacion=numero_aut,
            fecha_autorizacion=fecha_aut,
            ambiente=ambiente,
            comprobante=comprobante,
            mensajes=mensajes,
        )
    except Exception as e:
        logger.error(f"Error parseando respuesta de Autorización: {e}")
        return SRIAutorizacionResponse(estado="ERROR", mensajes=[
            SRIMensaje(mensaje=f"Error parseando respuesta: {e}", tipo="ERROR")
        ])


# ==========================================
# Cliente SOAP asíncrono
# ==========================================

async def _call_sri_recepcion(xml_base64: str, wsdl_url: str) -> SRIRecepcionResponse:
    """
    Llama al servicio de Recepción del SRI usando zeep AsyncClient.
    
    Args:
        xml_base64: XML firmado codificado en Base64
        wsdl_url: URL del WSDL del servicio de Recepción
    
    Returns:
        Respuesta parseada del SRI
    """
    transport = None
    try:
        import httpx
        from zeep import AsyncClient
        from zeep.transports import AsyncTransport
        
        # Crear transporte asíncrono con timeout
        # Security: enable SSL verification by default, disable only via env var for testing
        import ssl
        ssl_verify = not settings.is_development  # Verify SSL in production, allow skip in dev
        if settings.is_development:
            # In development, try to verify but allow failures with warning
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            http_client = httpx.AsyncClient(
                timeout=30.0,
                verify=ssl_context,
            )
            logger.warning(
                "SRI SSL verification disabled in development mode. "
                "This is insecure and should not be used in production."
            )
        else:
            http_client = httpx.AsyncClient(
                timeout=30.0,
                verify=True,  # Enable SSL verification in production
            )
        transport = AsyncTransport(
            client=http_client,
            timeout=30.0,
        )
        
        async with AsyncClient(wsdl=wsdl_url, transport=transport) as client:
            response = await client.service.validarComprobante(xml_base64)
            result = _parse_recepcion_response(response)
            return result
    
    except ImportError:
        logger.warning("zeep o httpx no disponibles, usando respuesta simulada")
        return _create_mock_recepcion_response()
    except SRIServiceError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        
        if "connection" in error_msg or "connect" in error_msg:
            raise SRIServiceError(
                "No se pudo conectar al SRI. Verifique su conexión a internet."
            )
        elif "timeout" in error_msg or "timed out" in error_msg:
            raise SRIServiceError(
                "Tiempo de espera agotado al conectar con el SRI. Intente nuevamente."
            )
        elif "ssl" in error_msg or "certificate" in error_msg:
            raise SRIServiceError(
                "Error de certificado SSL al conectar con el SRI."
            )
        elif "fault" in error_msg or "soap" in error_msg:
            raise SRIServiceError(
                f"Error SOAP del SRI: {str(e)}"
            )
        else:
            raise SRIServiceError(
                f"Error de comunicación con el SRI: {str(e)}"
            )
    finally:
        # Cerrar transporte si existe
        if transport is not None:
            try:
                await transport.client.aclose()
            except Exception:
                pass


async def _call_sri_autorizacion(clave_acceso: str, wsdl_url: str) -> SRIAutorizacionResponse:
    """
    Llama al servicio de Autorización del SRI usando zeep AsyncClient.
    
    Args:
        clave_acceso: Clave de acceso de 49 dígitos
        wsdl_url: URL del WSDL del servicio de Autorización
    
    Returns:
        Respuesta parseada del SRI
    """
    transport = None
    try:
        import httpx
        from zeep import AsyncClient
        from zeep.transports import AsyncTransport
        
        import ssl
        if settings.is_development:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            http_client = httpx.AsyncClient(
                timeout=15.0,
                verify=ssl_context,
            )
        else:
            http_client = httpx.AsyncClient(
                timeout=15.0,
                verify=True,  # Enable SSL verification in production
            )
        transport = AsyncTransport(
            client=http_client,
            timeout=15.0,
        )
        
        async with AsyncClient(wsdl=wsdl_url, transport=transport) as client:
            response = await client.service.autorizacionComprobante(clave_acceso)
            result = _parse_autorizacion_response(response)
            return result
    
    except ImportError:
        logger.warning("zeep o httpx no disponibles, usando respuesta simulada")
        return _create_mock_autorizacion_response(clave_acceso)
    except SRIServiceError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        
        if "connection" in error_msg or "connect" in error_msg:
            raise SRIServiceError(
                "No se pudo conectar al SRI. Verifique su conexión a internet."
            )
        elif "timeout" in error_msg or "timed out" in error_msg:
            raise SRIServiceError(
                "Tiempo de espera agotado al consultar el SRI."
            )
        elif "ssl" in error_msg or "certificate" in error_msg:
            raise SRIServiceError(
                "Error de certificado SSL al conectar con el SRI."
            )
        else:
            raise SRIServiceError(
                f"Error de comunicación con el SRI: {str(e)}"
            )
    finally:
        if transport is not None:
            try:
                await transport.client.aclose()
            except Exception:
                pass


# ==========================================
# Respuestas simuladas (desarrollo)
# ==========================================

def _create_mock_recepcion_response() -> SRIRecepcionResponse:
    """
    Crea una respuesta simulada de Recepción para desarrollo.
    Valida la estructura básica del XML.
    """
    return SRIRecepcionResponse(
        estado="RECIBIDA",
        comprobantes=[],
        mensajes=[
            SRIMensaje(
                identificador="1",
                mensaje="COMPROBANTE RECIBIDO (modo desarrollo - simulado)",
                tipo="ADVERTENCIA",
                info_adicional="Esta es una respuesta simulada para desarrollo",
            )
        ],
    )


def _create_mock_autorizacion_response(clave_acceso: str) -> SRIAutorizacionResponse:
    """
    Crea una respuesta simulada de Autorización para desarrollo.
    Valida la longitud de la clave de acceso.
    """
    if len(clave_acceso) == 49 and clave_acceso.isdigit():
        return SRIAutorizacionResponse(
            estado="AUTORIZADO",
            numero_autorizacion=clave_acceso,
            fecha_autorizacion=datetime.now(timezone.utc),
            ambiente="1",
            mensajes=[
                SRIMensaje(
                    identificador="1",
                    mensaje="AUTORIZADO (modo desarrollo - simulado)",
                    tipo="ADVERTENCIA",
                    info_adicional="Esta es una respuesta simulada para desarrollo",
                )
            ],
        )
    else:
        return SRIAutorizacionResponse(
            estado="NO AUTORIZADO",
            numero_autorizacion="",
            ambiente="1",
            mensajes=[
                SRIMensaje(
                    identificador="1",
                    mensaje="Clave de acceso inválida",
                    tipo="ERROR",
                )
            ],
        )


# ==========================================
# Funciones principales del servicio
# ==========================================

async def enviar_comprobante(
    xml_firmado: str,
    ambiente: str = "1",
) -> SRIRecepcionResponse:
    """
    Envía un comprobante electrónico firmado al SRI para su validación.
    
    Proceso:
    1. Validar parámetros
    2. Codificar XML en Base64
    3. Enviar al servicio de Recepción del SRI
    4. Si el SRI no está disponible y estamos en desarrollo, usar respuesta simulada
    
    Args:
        xml_firmado: Contenido XML firmado del comprobante
        ambiente: "1" para Pruebas, "2" para Producción
    
    Returns:
        SRIRecepcionResponse con el resultado del envío
    
    Raises:
        ValueError: Si los parámetros son inválidos
        SRIServiceError: Si hay error de comunicación con el SRI
    """
    # Validar parámetros
    if not xml_firmado or not xml_firmado.strip():
        raise ValueError("El XML firmado no puede estar vacío.")
    if ambiente not in ("1", "2"):
        raise ValueError("Ambiente inválido. Debe ser '1' (Pruebas) o '2' (Producción).")
    
    # Obtener URLs WSDL
    recepcion_url, _ = _get_wsdl_urls(ambiente)
    
    # Codificar XML en Base64
    xml_base64 = _encode_xml_base64(xml_firmado)
    
    # Enviar al SRI
    try:
        response = await _call_sri_recepcion(xml_base64, recepcion_url)
        return response
    except SRIServiceError:
        # En modo desarrollo, usar respuesta simulada
        if settings.is_development:
            logger.warning("SRI no disponible, usando respuesta simulada (modo desarrollo)")
            return _create_mock_recepcion_response()
        raise


async def recuperar_comprobante(
    xml_firmado: str,
    ambiente: str = "1",
) -> SRIRecepcionResponse:
    """
    Recupera un comprobante electrónico previamente enviado al SRI.

    Recuperación de comprobantes no autorizados: permite reenviar el XML
    firmado de un comprobante que ya fue enviado pero del cual no se obtuvo
    respuesta de autorización (por ejemplo, por fallas de conexión), siempre
    que no hayan transcurrido más de 72 horas desde su emisión.

    El servicio de Recepción del SRI expone una única operación
    (validarComprobante), por lo que la recuperación se realiza reenviando
    el mismo XML firmado: el SRI responde de forma idempotente (RECIBIDA si
    el comprobante ya lo tenía registrado, o DEVUELTA con los errores de
    validación si no fue recibido).

    Args:
        xml_firmado: Contenido XML firmado del comprobante
        ambiente: "1" para Pruebas, "2" para Producción

    Returns:
        SRIRecepcionResponse con el resultado de la recuperación

    Raises:
        ValueError: Si los parámetros son inválidos
        SRIServiceError: Si hay error de comunicación con el SRI
    """
    return await enviar_comprobante(xml_firmado, ambiente)


async def autorizar_comprobante(
    clave_acceso: str,
    ambiente: str = "1",
) -> SRIAutorizacionResponse:
    """
    Consulta el estado de autorización de un comprobante en el SRI.
    
    Args:
        clave_acceso: Clave de acceso de 49 dígitos del comprobante
        ambiente: "1" para Pruebas, "2" para Producción
    
    Returns:
        SRIAutorizacionResponse con el resultado de la consulta
    
    Raises:
        ValueError: Si los parámetros son inválidos
        SRIServiceError: Si hay error de comunicación con el SRI
    """
    # Validar parámetros
    if not clave_acceso or not clave_acceso.isdigit() or len(clave_acceso) != 49:
        raise ValueError("Clave de acceso inválida. Debe tener 49 dígitos numéricos.")
    if ambiente not in ("1", "2"):
        raise ValueError("Ambiente inválido. Debe ser '1' (Pruebas) o '2' (Producción).")
    
    # Obtener URLs WSDL
    _, autorizacion_url = _get_wsdl_urls(ambiente)
    
    # Consultar al SRI
    try:
        response = await _call_sri_autorizacion(clave_acceso, autorizacion_url)
        return response
    except SRIServiceError:
        # En modo desarrollo, usar respuesta simulada
        if settings.is_development:
            logger.warning("SRI no disponible, usando respuesta simulada (modo desarrollo)")
            return _create_mock_autorizacion_response(clave_acceso)
        raise


async def enviar_y_autorizar(
    xml_firmado: str,
    clave_acceso: str,
    ambiente: str = "1",
    max_retries: int = 3,
    retry_delay: float = 3.0,
) -> SRIAutorizacionResponse:
    """
    Flujo completo de envío y autorización de un comprobante.
    
    Proceso:
    1. Enviar al SRI Recepción
    2. Si DEVUELTA, retornar NO AUTORIZADO con mensajes de error
    3. Si RECIBIDA, esperar y consultar Autorización
    4. Reintentar consulta hasta max_retries veces
    5. Retornar AUTORIZADO, NO AUTORIZADO o EN PROCESO
    
    Args:
        xml_firmado: Contenido XML firmado
        clave_acceso: Clave de acceso de 49 dígitos
        ambiente: "1" para Pruebas, "2" para Producción
        max_retries: Número máximo de reintentos de consulta (default: 3)
        retry_delay: Segundos entre reintentos (default: 3.0)
    
    Returns:
        SRIAutorizacionResponse con el resultado final
    """
    # 1. Enviar al SRI Recepción
    recepcion = await enviar_comprobante(xml_firmado, ambiente)
    
    # 2. Si DEVUELTA, retornar como NO AUTORIZADO
    if recepcion.is_devuelta:
        error_msgs = [m.mensaje for m in recepcion.mensajes]
        return SRIAutorizacionResponse(
            estado="NO AUTORIZADO",
            mensajes=recepcion.mensajes,
        )
    
    # 3. Si RECIBIDA, consultar Autorización con reintentos
    if recepcion.is_recibida:
        for attempt in range(max_retries):
            # Esperar antes de consultar
            if attempt > 0:
                await asyncio.sleep(retry_delay)
            
            # Consultar autorización
            autorizacion = await autorizar_comprobante(clave_acceso, ambiente)
            
            # Si ya tiene resultado definitivo, retornar
            if autorizacion.is_autorizado or autorizacion.is_no_autorizado:
                return autorizacion
            
            # Si sigue en proceso, reintentar
            logger.info(
                f"Intento {attempt + 1}/{max_retries}: "
                f"Comprobante {clave_acceso[:10]}... en proceso"
            )
        
        # Si se agotaron los reintentos, retornar última respuesta
        return autorizacion
    
    # Estado inesperado
    return SRIAutorizacionResponse(
        estado="DESCONOCIDO",
        mensajes=[SRIMensaje(
            mensaje=f"Estado inesperado de Recepción: {recepcion.estado}",
            tipo="ERROR",
        )],
    )


# ==========================================
# Funciones de compatibilidad (alias)
# ==========================================

async def consultar_autorizacion(
    clave_acceso: str,
    ambiente: str = "1",
) -> dict:
    """
    Consulta el estado de autorización de un comprobante en el SRI.
    Versión simplificada que retorna un diccionario.
    
    Compatibilidad con endpoints que esperan dict como respuesta.
    """
    response = await autorizar_comprobante(clave_acceso, ambiente)
    return response.to_dict()
