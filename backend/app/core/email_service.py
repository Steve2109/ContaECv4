"""
ContaEC - Servicio de Envío de Correos Electrónicos
Envío automático de comprobantes autorizados a clientes
con el XML adjunto y/o el RIDE en PDF

Soporta múltiples perfiles SMTP por usuario y modo sandbox.

NOTA: Todas las operaciones síncronas (smtplib) se ejecutan
en un executor para no bloquear el event loop de asyncio.
"""
import asyncio
import html
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.core.encryption import decrypt_field
from app.core.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailServiceError(Exception):
    """Error en el servicio de correo electrónico"""
    pass


def _get_smtp_connection(
    host: str,
    port: int,
    user: str,
    password: str,
    use_ssl: bool = True,
) -> smtplib.SMTP | smtplib.SMTP_SSL:
    """
    Establece conexión SMTP con el servidor de correo.
    
    Args:
        host: Servidor SMTP
        port: Puerto SMTP
        user: Usuario SMTP
        password: Contraseña SMTP (descifrada)
        use_ssl: Usar SSL/TLS
    
    Returns:
        Conexión SMTP autenticada
    """
    try:
        if use_ssl:
            # Conexión directa con SSL (puerto 465)
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            # Conexión sin SSL, intentar STARTTLS (puerto 587 o 25)
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except smtplib.SMTPNotSupportedError:
                # El servidor no soporta STARTTLS, continuar sin cifrado
                logger.warning(f"STARTTLS no soportado por {host}:{port}")
        
        server.login(user, password)
        return server
    
    except smtplib.SMTPAuthenticationError:
        raise EmailServiceError(
            f"Error de autenticación SMTP. Verifique usuario y contraseña."
        )
    except smtplib.SMTPConnectError as e:
        raise EmailServiceError(
            f"No se pudo conectar al servidor SMTP {host}:{port}. {str(e)}"
        )
    except Exception as e:
        raise EmailServiceError(
            f"Error al conectar al servidor SMTP: {str(e)}"
        )


def _send_email_sync(
    msg: MIMEMultipart,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_ssl: bool,
    to_email: str,
) -> dict:
    """Función síncrona para enviar correo (se ejecuta en executor)."""
    server = None
    try:
        server = _get_smtp_connection(
            host=smtp_host,
            port=smtp_port,
            user=smtp_user,
            password=smtp_password,
            use_ssl=smtp_ssl,
        )
        server.sendmail(smtp_user, to_email, msg.as_string())
        return {"success": True, "message": f"Comprobante enviado exitosamente a {to_email}"}
    except EmailServiceError:
        raise
    except Exception as e:
        raise EmailServiceError(f"Error al enviar correo: {str(e)}")
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


async def get_smtp_profile_connection(
    profile_id: str,
    db: "AsyncSession",
) -> dict:
    """
    Carga un perfil SMTP y prepara los parámetros de conexión.

    Args:
        profile_id: ID del perfil SMTP
        db: Sesión de base de datos asíncrona

    Returns:
        Diccionario con los parámetros de conexión SMTP:
        - smtp_host, smtp_port, smtp_user, smtp_password (descifrada),
          smtp_ssl, from_name, profile (objeto SMTPProfile)

    Raises:
        EmailServiceError: Si el perfil no existe, está inactivo,
            o no se puede descifrar la contraseña
    """
    from sqlalchemy import select
    from app.models.smtp_profile import SMTPProfile, SmtpConnectionProtocol

    result = await db.execute(
        select(SMTPProfile).where(SMTPProfile.id == profile_id)
    )
    profile = result.scalars().first()

    if not profile:
        raise EmailServiceError(f"Perfil SMTP no encontrado: {profile_id}")

    if not profile.is_active:
        raise EmailServiceError(
            f"El perfil SMTP '{profile.nombre}' está inactivo."
        )

    # Verificar límite diario
    if profile.sent_today >= profile.daily_limit:
        raise EmailServiceError(
            f"El perfil SMTP '{profile.nombre}' ha alcanzado el límite diario "
            f"de envíos ({profile.daily_limit}). Envíos hoy: {profile.sent_today}."
        )

    # Descifrar contraseña
    try:
        smtp_password = decrypt_field(profile.password, settings.ENCRYPTION_KEY)
    except Exception as e:
        raise EmailServiceError(
            f"No se pudo descifrar la contraseña del perfil '{profile.nombre}': {str(e)}"
        )

    # Determinar si se usa SSL según el protocolo
    if profile.protocol == SmtpConnectionProtocol.SMTP_SSL:
        use_ssl = True
    elif profile.protocol == SmtpConnectionProtocol.STARTTLS:
        use_ssl = False
    else:  # SMTP plain
        use_ssl = profile.use_ssl

    return {
        "smtp_host": profile.host,
        "smtp_port": profile.port,
        "smtp_user": profile.username,
        "smtp_password": smtp_password,
        "smtp_ssl": use_ssl,
        "from_name": profile.nombre,
        "profile": profile,
    }


async def send_comprobante_email(
    to_email: str,
    cliente_razon_social: str,
    tipo_comprobante: str,
    secuencial: str,
    clave_acceso: str,
    numero_autorizacion: str,
    fecha_autorizacion: str,
    empresa_razon_social: str,
    empresa_ruc: str,
    total_con_impuestos: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password_encrypted: str,
    smtp_ssl: bool = True,
    xml_content: Optional[str] = None,
    pdf_content: Optional[bytes] = None,
    from_name: Optional[str] = None,
    smtp_profile_id: Optional[str] = None,
    db: Optional["AsyncSession"] = None,
    environment_mode: Optional[str] = None,
) -> dict:
    """
    Envía un comprobante autorizado por correo electrónico al cliente.
    Ejecuta el envío SMTP en un executor para no bloquear el event loop.

    Soporta múltiples perfiles SMTP: si se proporciona smtp_profile_id y db,
    se carga el perfil correspondiente y se usa su configuración en lugar
    de los parámetros individuales.

    Modo Sandbox: si environment_mode es 'sandbox', se registra el correo
    pero NO se envía realmente. Se retorna una respuesta simulada de éxito.
    """
    if not to_email:
        return {"success": False, "message": "El cliente no tiene correo electrónico configurado."}

    # Si se proporciona un perfil SMTP, usar su configuración
    smtp_profile = None
    if smtp_profile_id and db:
        try:
            profile_conn = await get_smtp_profile_connection(smtp_profile_id, db)
            smtp_host = profile_conn["smtp_host"]
            smtp_port = profile_conn["smtp_port"]
            smtp_user = profile_conn["smtp_user"]
            smtp_password = profile_conn["smtp_password"]
            smtp_ssl = profile_conn["smtp_ssl"]
            from_name = from_name or profile_conn["from_name"]
            smtp_profile = profile_conn["profile"]
        except EmailServiceError:
            raise
    else:
        # Descifrar contraseña SMTP (modo legacy: UserConfig)
        try:
            smtp_password = decrypt_field(smtp_password_encrypted, settings.ENCRYPTION_KEY)
        except Exception as e:
            raise EmailServiceError(f"No se pudo descifrar la contraseña SMTP: {str(e)}")

    # ========================================
    # MODO SANDBOX: No enviar correo real
    # ========================================
    if environment_mode and environment_mode.lower() == "sandbox":
        tipo_nombres = {
            "01": "Factura",
            "03": "Liquidación de Compra",
            "04": "Nota de Crédito",
            "05": "Nota de Débito",
            "06": "Guía de Remisión",
            "07": "Comprobante de Retención",
        }
        tipo_nombre = tipo_nombres.get(tipo_comprobante, "Comprobante")
        secuencial_fmt = secuencial.zfill(9)

        logger.info(
            f"[SANDBOX] Correo simulado - Comprobante {tipo_nombre} #{secuencial_fmt} "
            f"a {to_email} via {smtp_user}@{smtp_host}:{smtp_port}"
        )
        return {
            "success": True,
            "message": (
                f"[SANDBOX] Correo simulado para {to_email}. "
                f"Comprobante {tipo_nombre} #{secuencial_fmt} no enviado (modo sandbox)."
            ),
            "sandbox": True,
        }

    # Nombres de tipos de comprobante
    tipo_nombres = {
        "01": "Factura",
        "03": "Liquidación de Compra",
        "04": "Nota de Crédito",
        "05": "Nota de Débito",
        "06": "Guía de Remisión",
        "07": "Comprobante de Retención",
    }
    tipo_nombre = tipo_nombres.get(tipo_comprobante, "Comprobante")
    
    # Formatear número de comprobante
    secuencial_fmt = secuencial.zfill(9)
    
    # Crear mensaje (esto es rápido, no necesita executor)
    msg = MIMEMultipart()
    msg['From'] = f"{from_name or empresa_razon_social} <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = f"{tipo_nombre} Electrónica #{secuencial_fmt} - {empresa_razon_social}"
    
    # Cuerpo del correo en HTML
    # Security: escape all user-controlled variables to prevent XSS/HTML injection
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #1B5E20; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">{html.escape(tipo_nombre)} Electrónica</h2>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">{html.escape(empresa_razon_social)} - RUC: {html.escape(empresa_ruc)}</p>
        </div>
        <div style="background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd;">
            <p>Estimado/a <strong>{html.escape(cliente_razon_social)}</strong>,</p>
            <p>Se ha emitido y autorizado electrónicamente el siguiente comprobante:</p>

            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #E8F5E9;">
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-weight: bold; width: 40%;">Tipo de Comprobante:</td>
                    <td style="padding: 8px 12px; border: 1px solid #ddd;">{html.escape(tipo_nombre)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-weight: bold;">Número:</td>
                    <td style="padding: 8px 12px; border: 1px solid #ddd;">{html.escape(secuencial_fmt)}</td>
                </tr>
                <tr style="background-color: #E8F5E9;">
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-weight: bold;">Total:</td>
                    <td style="padding: 8px 12px; border: 1px solid #ddd;">USD {html.escape(total_con_impuestos)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-weight: bold;">Clave de Acceso:</td>
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-size: 11px; word-break: break-all;">{html.escape(clave_acceso)}</td>
                </tr>
                <tr style="background-color: #E8F5E9;">
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-weight: bold;">Autorización SRI:</td>
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-size: 11px; word-break: break-all;">{html.escape(numero_autorizacion)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 12px; border: 1px solid #ddd; font-weight: bold;">Fecha Autorización:</td>
                    <td style="padding: 8px 12px; border: 1px solid #ddd;">{html.escape(fecha_autorizacion)}</td>
                </tr>
            </table>

            <p>Los archivos adjuntos contienen el comprobante electrónico en formato XML y su representación impresa (RIDE) en PDF.</p>

            <div style="background-color: #FFF3E0; border-left: 4px solid #FF9800; padding: 10px 15px; margin: 15px 0;">
                <p style="margin: 0; font-size: 13px;"><strong>Nota:</strong> Puede verificar la autenticidad de este comprobante en el portal del SRI:
                <a href="https://consultas.sri.gob.ec" style="color: #1B5E20;">https://consultas.sri.gob.ec</a></p>
            </div>
        </div>
        <div style="background-color: #1B5E20; color: white; padding: 12px 20px; border-radius: 0 0 8px 8px; font-size: 12px; text-align: center;">
            <p style="margin: 0;">Generado por ContaEC - T&M Technology Ec</p>
            <p style="margin: 3px 0 0 0; opacity: 0.8;">info@tymtechnology.shop | 0960068866</p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Adjuntar XML
    if xml_content:
        xml_attachment = MIMEApplication(
            xml_content.encode('utf-8'),
            Name=f"{tipo_nombre}_{secuencial_fmt}.xml"
        )
        xml_attachment['Content-Disposition'] = f'attachment; filename="{tipo_nombre}_{secuencial_fmt}.xml"'
        msg.attach(xml_attachment)
    
    # Adjuntar PDF (RIDE)
    if pdf_content:
        pdf_attachment = MIMEApplication(
            pdf_content,
            Name=f"{tipo_nombre}_{secuencial_fmt}.pdf"
        )
        pdf_attachment['Content-Disposition'] = f'attachment; filename="{tipo_nombre}_{secuencial_fmt}.pdf"'
        msg.attach(pdf_attachment)
    
    # Enviar correo en executor para no bloquear el event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        partial(
            _send_email_sync,
            msg=msg,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_ssl=smtp_ssl,
            to_email=to_email,
        )
    )
    logger.info(f"Comprobante {secuencial_fmt} enviado a {to_email}")

    # Actualizar contador del perfil SMTP si se usó un perfil
    if smtp_profile and db:
        smtp_profile.sent_today = (smtp_profile.sent_today or 0) + 1
        smtp_profile.last_sent_at = datetime.now(timezone.utc)
        # Flush sin commit (el commit lo maneja get_db)
        await db.flush()

    return result


async def send_test_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_ssl: bool = True,
    to_email: Optional[str] = None,
) -> dict:
    """
    Envía un correo de prueba para verificar la configuración SMTP.
    Ejecuta el envío en un executor para no bloquear el event loop.
    """
    if not to_email:
        to_email = smtp_user
    
    msg = MIMEMultipart()
    msg['From'] = f"ContaEC <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = "ContaEC - Prueba de Configuración SMTP"
    
    html_body = """
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="background-color: #1B5E20; color: white; padding: 15px; border-radius: 8px;">
            <h2 style="margin: 0;">✅ Configuración SMTP Exitosa</h2>
        </div>
        <div style="padding: 15px;">
            <p>Su configuración de correo electrónico está funcionando correctamente.</p>
            <p>Los comprobantes electrónicos autorizados se enviarán automáticamente a sus clientes.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
            <p style="font-size: 12px; color: #666;">ContaEC - T&M Technology Ec</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Enviar en executor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        partial(
            _send_email_sync,
            msg=msg,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_ssl=smtp_ssl,
            to_email=to_email,
        )
    )
    return result


async def send_welcome_email(
    to_email: str,
    full_name: str = "",
    trial_end_date=None,
) -> dict:
    """
    Envía el correo de bienvenida/confirmación de cuenta al nuevo usuario
    usando el SMTP del SISTEMA (configurado en variables de entorno).

    Este correo NO usa el SMTP del usuario (aún no existe al registrarse),
    sino el buzón de la plataforma (SMTP_HOST/SMTP_USER del .env).

    La función NUNCA lanza excepciones: si el SMTP no está configurado o
    el envío falla, se registra en el log y se retorna success=False.
    Esto permite llamarla en segundo plano sin romper el registro.

    Args:
        to_email: Correo del nuevo usuario
        full_name: Nombre completo del usuario
        trial_end_date: Fecha fin del período de prueba (opcional)

    Returns:
        dict: {"success": bool, "message": str}
    """
    # Validar configuración SMTP del sistema
    if not settings.SMTP_ENABLED or not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning(
            f"Correo de bienvenida NO enviado a {to_email}: "
            "SMTP del sistema no configurado (SMTP_ENABLED/SMTP_HOST/SMTP_USER)."
        )
        return {"success": False, "message": "SMTP del sistema no configurado."}

    try:
        nombre = html.escape(full_name or to_email)
        trial_text = ""
        if trial_end_date:
            try:
                fecha = trial_end_date.strftime("%d/%m/%Y")
            except Exception:
                fecha = str(trial_end_date)
            trial_text = (
                "<p>Tu cuenta incluye un <strong>período de prueba de 15 días</strong> "
                f"válido hasta el <strong>{html.escape(fecha)}</strong>, para que explores "
                "todas las funcionalidades de ContaEC.</p>"
            )

        # Crear mensaje
        from email.header import Header

        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME or 'ContaEC'} <{settings.SMTP_USER}>"
        msg['To'] = to_email
        # Header() codifica el asunto (emoji y acentos) según RFC 2047
        msg['Subject'] = str(Header("🎉 ¡Tu cuenta en ContaEC ha sido creada!", "utf-8"))

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1B5E20; color: white; padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 22px;">🎉 ¡Bienvenido a ContaEC!</h2>
                <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">Tu cuenta fue creada exitosamente</p>
            </div>
            <div style="background-color: #f9f9f9; padding: 24px; border: 1px solid #ddd;">
                <p>Estimado/a <strong>{nombre}</strong>,</p>
                <p>¡Felicitaciones! Tu cuenta en <strong>ContaEC</strong> ha sido creada correctamente.</p>
                <p>Ya puedes iniciar sesión y comenzar a usar el sistema de contabilidad y facturación electrónica.</p>
                {trial_text}
                <div style="background-color: #E8F5E9; border-left: 4px solid #1B5E20; padding: 12px 16px; margin: 16px 0;">
                    <p style="margin: 0; font-size: 14px;"><strong>Acceso:</strong> <a href="https://conta.tymtechnology.shop" style="color: #1B5E20;">https://conta.tymtechnology.shop</a></p>
                </div>
                <p style="font-size: 14px;">Si necesitas ayuda, responde este correo o contáctanos al <strong>0960068866</strong>.</p>
            </div>
            <div style="background-color: #1B5E20; color: white; padding: 14px 24px; border-radius: 0 0 8px 8px; font-size: 12px; text-align: center;">
                <p style="margin: 0;">ContaEC - T&M Technology Ec</p>
                <p style="margin: 3px 0 0 0; opacity: 0.8;">info@tymtechnology.shop | 0960068866</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Enviar en executor para no bloquear el event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                _send_email_sync,
                msg=msg,
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
                smtp_ssl=settings.SMTP_SSL,
                to_email=to_email,
            )
        )
        logger.info(f"Correo de bienvenida enviado a {to_email}")
        return result
    except Exception as e:
        logger.error(f"Error al enviar correo de bienvenida a {to_email}: {e}")
        return {"success": False, "message": f"Error al enviar correo: {str(e)}"}
