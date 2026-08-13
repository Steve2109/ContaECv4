"""
ContaEC - Firmador de XML para comprobantes electrónicos del SRI
Firma XML con firma digital XAdES-BES según requerimientos del SRI

El SRI requiere:
- Formato de firma: XAdES-BES (XML Advanced Electronic Signatures)
- Tipo de firma: Enveloped (la firma va dentro del XML)
- Referencia: elemento comprobante (id="comprobante")
- Algoritmo de resumen: SHA-256
- Algoritmo de firma: RSA-SHA256

Flujo de firma:
1. Cargar el certificado .p12/.pfx con la contraseña
2. Parsear el XML del comprobante
3. Firmar con XAdES-BES usando signxml
4. Devolver el XML firmado
"""
import asyncio
import logging
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization.pkcs12 import (
    load_key_and_certificates,
)
from cryptography.x509 import Certificate
from lxml import etree
from signxml import XMLSigner
from signxml.xades import XAdESSigner, XAdESVerifier, XAdESSignatureConfiguration

logger = logging.getLogger(__name__)


# ==========================================
# Excepciones personalizadas
# ==========================================

class XMLSignerError(Exception):
    """Error durante el proceso de firma del XML"""

    pass


class XMLVerifierError(Exception):
    """Error durante la verificación de la firma del XML"""

    pass


# ==========================================
# Funciones auxiliares
# ==========================================

def _load_pkcs12(
    signature_path: str,
    password: str,
) -> tuple[Any, Certificate | None, list[Certificate]]:
    """
    Carga un archivo PKCS#12 (.p12/.pfx) y extrae la clave privada,
    el certificado y los certificados adicionales de la cadena.

    Args:
        signature_path: Ruta al archivo .p12/.pfx
        password: Contraseña del archivo PKCS#12

    Returns:
        Tupla (clave_privada, certificado, certificados_cadena)

    Raises:
        XMLSignerError: Si no se puede cargar el archivo o la contraseña es incorrecta
    """
    try:
        path = Path(signature_path)
        if not path.exists():
            raise XMLSignerError(
                f"El archivo de firma digital no existe: {signature_path}"
            )

        with open(path, "rb") as f:
            p12_data = f.read()

        # Cargar PKCS#12
        password_bytes = password.encode("utf-8") if password else None
        private_key, certificate, additional_certs = load_key_and_certificates(
            p12_data, password_bytes
        )

        if private_key is None:
            raise XMLSignerError(
                "No se encontró la clave privada en el archivo de firma digital. "
                "Verifique que el archivo .p12 sea válido."
            )

        if certificate is None:
            raise XMLSignerError(
                "No se encontró el certificado en el archivo de firma digital. "
                "Verifique que el archivo .p12 sea válido."
            )

        return private_key, certificate, additional_certs or []

    except XMLSignerError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "mac" in error_msg or "decrypt" in error_msg:
            raise XMLSignerError(
                "Contraseña incorrecta para el archivo de firma digital. "
                "Verifique la contraseña e intente de nuevo."
            )
        raise XMLSignerError(
            f"Error al cargar el archivo de firma digital: {e}"
        )


def _parse_xml(xml_content: str) -> etree._Element:
    """
    Parsea una cadena XML y devuelve el elemento raíz.

    Args:
        xml_content: Cadena XML válida

    Returns:
        Elemento raíz del XML

    Raises:
        XMLSignerError: Si el XML no es válido
    """
    try:
        # Remover declaración XML para parsear correctamente
        # Security: disable external entities and network access to prevent XXE attacks
        parser = etree.XMLParser(
            remove_blank_text=True,
            encoding="UTF-8",
            resolve_entities=False,
            no_network=True,
            dtd_validation=False,
            load_dtd=False,
        )
        root = etree.fromstring(xml_content.encode("utf-8"), parser=parser)
        return root
    except etree.XMLSyntaxError as e:
        raise XMLSignerError(f"XML inválido: {e}")
    except Exception as e:
        raise XMLSignerError(f"Error al parsear XML: {e}")


# ==========================================
# Funciones principales
# ==========================================

async def sign_xml(
    xml_content: str,
    signature_path: str,
    signature_password: str,
) -> str:
    """
    Firma un XML de comprobante electrónico con la firma digital del usuario.
    Utiliza firma XAdES-BES enveloped según requerimientos del SRI.

    El proceso:
    1. Cargar el certificado .p12/.pfx con la contraseña
    2. Parsear el XML del comprobante
    3. Firmar con XAdES-BES usando signxml
    4. Devolver el XML firmado como cadena

    Args:
        xml_content: Cadena XML sin firmar del comprobante
        signature_path: Ruta al archivo .p12/.pfx de la firma digital
        signature_password: Contraseña de la firma digital (ya descifrada)

    Returns:
        Cadena XML firmada

    Raises:
        XMLSignerError: Si hay algún error durante el proceso de firma

    Example:
        >>> signed = await sign_xml(
        ...     xml_content=unsigned_xml,
        ...     signature_path="/path/to/certificate.p12",
        ...     signature_password="my_password",
        ... )
    """
    try:
        # Cargar PKCS#12 en hilo separado para no bloquear el event loop
        loop = asyncio.get_event_loop()
        private_key, certificate, additional_certs = await loop.run_in_executor(
            None, _load_pkcs12, signature_path, signature_password
        )

        # Parsear XML
        root = _parse_xml(xml_content)

        # Preparar certificados adicionales para la cadena de confianza
        # El SRI puede requerir la cadena completa de certificados CA
        cert_chain = []
        if additional_certs:
            for cert in additional_certs:
                cert_chain.append(cert)

        # Firmar con XAdES-BES
        # El SRI requiere firma enveloped (la firma se inserta dentro del XML)
        # Se referencia el elemento con id="comprobante"
        signer = XAdESSigner(
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )

        # Preparar lista de certificados: cert del firmante + cadena CA
        all_certs = [certificate] + cert_chain

        # Firmar el XML
        # reference_uri="#comprobante" para que la firma referencie el elemento comprobante
        signed_root = signer.sign(
            root,
            key=private_key,
            cert=all_certs,
            reference_uri="#comprobante",
        )

        # Convertir a cadena XML con declaración.
        # IMPORTANTE: NO usar pretty_print=True aqui. La firma XAdES se calcula sobre el
        # arbol en memoria (compacto); si se agrega indentacion al serializar, los nodos
        # de texto con espacios en blanco alteran la canonicalizacion del SignedInfo y de
        # la referencia, y el SRI rechazaria el comprobante por firma invalida.
        signed_xml = etree.tostring(
            signed_root,
            xml_declaration=True,
            encoding="UTF-8",
        ).decode("utf-8")

        logger.info(
            "XML firmado exitosamente con XAdES-BES. "
            "Certificado: %s",
            certificate.subject.rfc4514_string(),
        )

        return signed_xml

    except XMLSignerError:
        raise
    except Exception as e:
        logger.error("Error al firmar XML: %s", str(e))
        raise XMLSignerError(f"Error al firmar el XML: {e}")


def sign_xml_sync(
    xml_content: str,
    signature_path: str,
    signature_password: str,
) -> str:
    """
    Versión síncrona de sign_xml para uso en contextos sin async/await.

    Firma un XML de comprobante electrónico con la firma digital del usuario.
    Utiliza firma XAdES-BES enveloped según requerimientos del SRI.

    Args:
        xml_content: Cadena XML sin firmar del comprobante
        signature_path: Ruta al archivo .p12/.pfx de la firma digital
        signature_password: Contraseña de la firma digital (ya descifrada)

    Returns:
        Cadena XML firmada

    Raises:
        XMLSignerError: Si hay algún error durante el proceso de firma
    """
    try:
        # Cargar PKCS#12
        private_key, certificate, additional_certs = _load_pkcs12(
            signature_path, signature_password
        )

        # Parsear XML
        root = _parse_xml(xml_content)

        # Preparar certificados adicionales
        cert_chain = []
        if additional_certs:
            for cert in additional_certs:
                cert_chain.append(cert)

        # Firmar con XAdES-BES
        signer = XAdESSigner(
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )

        # Preparar lista de certificados
        all_certs = [certificate] + cert_chain

        # Firmar
        signed_root = signer.sign(
            root,
            key=private_key,
            cert=all_certs,
            reference_uri="#comprobante",
        )

        # Convertir a cadena XML (sin pretty_print, ver nota en sign_xml)
        signed_xml = etree.tostring(
            signed_root,
            xml_declaration=True,
            encoding="UTF-8",
        ).decode("utf-8")

        logger.info(
            "XML firmado exitosamente (síncrono) con XAdES-BES. "
            "Certificado: %s",
            certificate.subject.rfc4514_string(),
        )

        return signed_xml

    except XMLSignerError:
        raise
    except Exception as e:
        logger.error("Error al firmar XML (síncrono): %s", str(e))
        raise XMLSignerError(f"Error al firmar el XML: {e}")


def verify_xml_signature(xml_content: str) -> dict:
    """
    Verifica la firma digital de un XML de comprobante electrónico.

    Verifica que:
    - La firma XAdES-BES sea válida
    - El certificado del firmante sea válido
    - El XML no haya sido modificado después de la firma

    Args:
        xml_content: Cadena XML firmada del comprobante

    Returns:
        Diccionario con el resultado de la verificación:
        {
            "valid": bool,
            "certificado": {
                "sujeto": str,
                "emisor": str,
                "serial": str,
                "fecha_inicio": str,
                "fecha_fin": str,
                "vigente": bool,
            },
            "error": str | None,
        }

    Example:
        >>> result = verify_xml_signature(signed_xml)
        >>> result["valid"]
        True
    """
    result: dict[str, Any] = {
        "valid": False,
        "certificado": None,
        "error": None,
    }

    try:
        # Parsear XML
        root = _parse_xml(xml_content)

        # Contar referencias firmadas para pasar el config correcto al verificador
        # (el XAdES generado por sign_xml tiene 3: comprobante, SignedProperties y
        # certificado; el default de signxml es 1 y fallaria con 'Expected to find
        # 1 references, but found N')
        ds_ns = "http://www.w3.org/2000/09/xmldsig#"
        refs = root.findall(f".//{{{ds_ns}}}SignedInfo/{{{ds_ns}}}Reference")
        expect_config = XAdESSignatureConfiguration(expect_references=len(refs))

        # Verificar firma con XAdESVerifier
        verifier = XAdESVerifier()
        verify_result = verifier.verify(root, expect_config=expect_config)

        # Si la verificación pasa, extraer información del certificado
        result["valid"] = True

        # Intentar extraer información del certificado desde el resultado
        if verify_result:
            # XAdES verify returns a list of XAdESVerifyResult
            verify_info = verify_result[0] if isinstance(verify_result, list) else verify_result

            # Extraer certificado si está disponible
            cert_info = _extract_cert_info(verify_info)
            if cert_info:
                result["certificado"] = cert_info

        logger.info("Verificación de firma XML exitosa")

    except Exception as e:
        error_msg = str(e)
        result["valid"] = False
        result["error"] = error_msg

        # Intentar dar mensajes de error más descriptivos
        error_lower = error_msg.lower()
        if "signature" in error_lower and "invalid" in error_lower:
            result["error"] = "La firma digital no es válida. El XML puede haber sido modificado."
        elif "certificate" in error_lower or "cert" in error_lower:
            result["error"] = f"Error con el certificado: {error_msg}"
        elif "not found" in error_lower or "no signature" in error_lower:
            result["error"] = "No se encontró una firma digital en el XML proporcionado."

        logger.warning("Verificación de firma XML fallida: %s", error_msg)

    return result


def _extract_cert_info(verify_result: Any) -> dict | None:
    """
    Extrae información del certificado del resultado de verificación.

    Args:
        verify_result: Resultado de la verificación XAdES

    Returns:
        Diccionario con información del certificado o None
    """
    try:
        # Intentar obtener el certificado del resultado de verificación
        cert = None
        if hasattr(verify_result, "signed_xml"):
            pass
        if hasattr(verify_result, "signing_cert"):
            cert = verify_result.signing_cert
        # Verificar si tiene atributo de certificado
        if cert is None and hasattr(verify_result, "certificate"):
            cert = verify_result.certificate

        if cert is not None and hasattr(cert, "subject"):
            from datetime import datetime, timezone

            return {
                "sujeto": cert.subject.rfc4514_string(),
                "emisor": cert.issuer.rfc4514_string(),
                "serial": str(cert.serial_number),
                "fecha_inicio": cert.not_valid_before_utc.isoformat()
                if hasattr(cert, "not_valid_before_utc")
                else str(cert.not_valid_before),
                "fecha_fin": cert.not_valid_after_utc.isoformat()
                if hasattr(cert, "not_valid_after_utc")
                else str(cert.not_valid_after),
                "vigente": (
                    cert.not_valid_before_utc
                    <= datetime.now(timezone.utc)
                    <= cert.not_valid_after_utc
                    if hasattr(cert, "not_valid_before_utc")
                    else cert.not_valid_before
                    <= datetime.now()
                    <= cert.not_valid_after
                ),
            }
    except Exception as e:
        logger.debug("No se pudo extraer información del certificado: %s", e)

    return None


# ==========================================
# Función alternativa de firma con XMLSigner básico (fallback)
# ==========================================

def sign_xml_basic(
    xml_content: str,
    signature_path: str,
    signature_password: str,
) -> str:
    """
    Firma un XML usando XMLSigner básico (sin XAdES).
    Se usa como fallback si XAdES-BES no funciona con ciertos certificados.

    El SRI acepta tanto firmas XAdES-BES como XMLDSig básico,
    pero se recomienda usar XAdES-BES (función sign_xml).

    Args:
        xml_content: Cadena XML sin firmar
        signature_path: Ruta al archivo .p12/.pfx
        signature_password: Contraseña del archivo (ya descifrada)

    Returns:
        Cadena XML firmada

    Raises:
        XMLSignerError: Si hay error en el proceso de firma
    """
    try:
        # Cargar PKCS#12
        private_key, certificate, additional_certs = _load_pkcs12(
            signature_path, signature_password
        )

        # Parsear XML
        root = _parse_xml(xml_content)

        # Firmar con XMLSigner básico (enveloped)
        signer = XMLSigner(
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )

        # Preparar certificados
        cert_chain = [certificate]
        if additional_certs:
            cert_chain.extend(additional_certs)

        # Firmar
        signed_root = signer.sign(
            root,
            key=private_key,
            cert=cert_chain,
            reference_uri="#comprobante",
        )

        # Convertir a cadena XML (sin pretty_print, ver nota en sign_xml)
        signed_xml = etree.tostring(
            signed_root,
            xml_declaration=True,
            encoding="UTF-8",
        ).decode("utf-8")

        logger.info("XML firmado exitosamente con XMLDSig básico (fallback)")

        return signed_xml

    except XMLSignerError:
        raise
    except Exception as e:
        logger.error("Error al firmar XML (básico): %s", str(e))
        raise XMLSignerError(f"Error al firmar el XML (básico): {e}")
