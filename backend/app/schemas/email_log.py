"""
ContaEC - Esquemas Pydantic de Log de Envío de Correos
Schemas para registro, consulta y tracking de logs de email
"""
from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EmailLogCreate(BaseModel):
    """Esquema para crear un nuevo log de envío de correo"""
    tipo: str = Field(
        ...,
        max_length=50,
        description="Tipo de correo: comprobante, proforma, notificacion, marketing, otro",
        examples=["comprobante"],
    )
    destinatario_principal: str = Field(
        ...,
        max_length=255,
        description="Correo del destinatario principal",
        examples=["cliente@empresa.com"],
    )
    destinatarios_cc: str | None = Field(
        None,
        description="Destinatarios en copia (separados por coma)",
    )
    destinatarios_cco: str | None = Field(
        None,
        description="Destinatarios en copia oculta (separados por coma)",
    )
    asunto: str = Field(
        ...,
        max_length=500,
        description="Asunto del correo",
    )
    cuerpo_html: str | None = Field(
        None,
        description="Cuerpo del correo en formato HTML",
    )
    cuerpo_texto: str | None = Field(
        None,
        description="Cuerpo del correo en texto plano",
    )
    estado: str = Field(
        default="pendiente",
        max_length=20,
        description="Estado: pendiente, enviado, fallido, reintentando, cancelado",
    )
    max_intentos: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Máximo número de intentos permitidos",
    )
    email_template_id: str | None = Field(
        None,
        description="ID de la plantilla utilizada",
    )
    comprobante_id: str | None = Field(
        None,
        description="ID del comprobante asociado",
    )
    smtp_profile_id: str | None = Field(
        None,
        description="ID del perfil SMTP utilizado",
    )
    adjuntos: str | None = Field(
        None,
        description="Lista de archivos adjuntos (JSON o ruta)",
    )


class EmailLogUpdate(BaseModel):
    """Esquema para actualizar un log de envío"""
    estado: str | None = Field(
        None,
        max_length=20,
        description="Estado del envío",
    )
    intentos: int | None = Field(
        None,
        ge=0,
        description="Número de intentos de envío",
    )
    max_intentos: int | None = Field(
        None,
        ge=1,
        le=10,
        description="Máximo número de intentos",
    )
    proximo_intento: datetime | None = Field(
        None,
        description="Fecha programada para próximo reintento",
    )
    respuesta_smtp: str | None = Field(
        None,
        description="Respuesta del servidor SMTP",
    )
    error_mensaje: str | None = Field(
        None,
        description="Mensaje de error",
    )
    fecha_envio: datetime | None = Field(
        None,
        description="Fecha de envío exitoso",
    )


class EmailLogResponse(BaseModel):
    """Esquema de respuesta para un log de correo"""
    id: UUID = Field(..., description="ID único del log")
    user_id: UUID | None = Field(None, description="ID del usuario propietario")
    tipo: str = Field(..., description="Tipo de correo")
    destinatario_principal: str = Field(..., description="Correo del destinatario")
    destinatarios_cc: str | None = Field(None, description="Destinatarios CC")
    destinatarios_cco: str | None = Field(None, description="Destinatarios CCO")
    asunto: str = Field(..., description="Asunto del correo")
    cuerpo_html: str | None = Field(None, description="Cuerpo HTML")
    cuerpo_texto: str | None = Field(None, description="Cuerpo texto plano")
    estado: str = Field(..., description="Estado del envío")
    intentos: int = Field(..., description="Número de intentos")
    max_intentos: int = Field(..., description="Máximo de intentos")
    proximo_intento: datetime | None = Field(None, description="Próximo reintento")
    respuesta_smtp: str | None = Field(None, description="Respuesta SMTP")
    error_mensaje: str | None = Field(None, description="Mensaje de error")
    email_template_id: UUID | None = Field(None, description="ID plantilla")
    comprobante_id: UUID | None = Field(None, description="ID comprobante")
    smtp_profile_id: UUID | None = Field(None, description="ID perfil SMTP")
    adjuntos: str | None = Field(None, description="Archivos adjuntos")
    fecha_envio: datetime | None = Field(None, description="Fecha de envío")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class EmailLogStats(BaseModel):
    """Estadísticas de envío de correos"""
    total: int = Field(..., description="Total de correos")
    enviados: int = Field(..., description="Correos enviados exitosamente")
    fallidos: int = Field(..., description="Correos fallidos")
    pendientes: int = Field(..., description="Correos pendientes")
    tasa_exito: float = Field(..., description="Tasa de éxito (%)")


class EmailLogRetryRequest(BaseModel):
    """Esquema para solicitar reintento de envío"""
    max_intentos_adicional: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Número adicional de intentos",
    )