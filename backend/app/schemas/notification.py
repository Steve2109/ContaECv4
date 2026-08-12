"""
ContaEC - Esquemas Pydantic de Notificaciones del Sistema
Schemas para creación, actualización y respuesta de notificaciones generales
"""
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Notification Create
# ==========================================

class NotificationCreate(BaseModel):
    """Esquema para crear una nueva notificación"""
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Título de la notificación",
        examples=["Nueva actualización disponible"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Mensaje detallado de la notificación",
        examples=["Se ha publicado la versión 2.0 del sistema."],
    )
    type: str = Field(
        default="info",
        description="Tipo de notificación: info, warning, error, success, system",
        examples=["info"],
    )
    category: str = Field(
        default="general",
        description="Categoría: general, billing, accounting, hr, license, security, system",
        examples=["general"],
    )
    priority: str = Field(
        default="normal",
        description="Prioridad: low, normal, high, urgent",
        examples=["normal"],
    )
    user_id: str | None = Field(
        None,
        description="ID del usuario destinatario (null = todos los usuarios de la empresa)",
    )
    company_id: str | None = Field(
        None,
        description="ID de la empresa (null = notificación global)",
    )
    action_url: str | None = Field(
        None,
        max_length=500,
        description="URL de navegación al hacer clic en la notificación",
    )
    action_label: str | None = Field(
        None,
        max_length=100,
        description="Etiqueta para el botón de acción",
    )
    expires_at: datetime | None = Field(
        None,
        description="Fecha de expiración para auto-ocultar la notificación",
    )


# ==========================================
# Notification Update
# ==========================================

class NotificationUpdate(BaseModel):
    """Esquema para actualizar una notificación"""
    is_read: bool | None = Field(
        None,
        description="Marca la notificación como leída o no leída",
    )
    is_active: bool | None = Field(
        None,
        description="Activa o desactiva la notificación",
    )


# ==========================================
# Notification Response
# ==========================================

class NotificationResponse(BaseModel):
    """Esquema de respuesta para una notificación"""
    id: UUID = Field(..., description="ID único de la notificación")
    company_id: UUID | None = Field(None, description="ID de la empresa (null = global)")
    user_id: UUID | None = Field(None, description="ID del usuario destinatario (null = todos)")
    type: str = Field(..., description="Tipo de notificación")
    category: str = Field(..., description="Categoría de la notificación")
    title: str = Field(..., description="Título de la notificación")
    message: str = Field(..., description="Mensaje de la notificación")
    is_read: bool = Field(..., description="Si la notificación ha sido leída")
    action_url: str | None = Field(None, description="URL de acción")
    action_label: str | None = Field(None, description="Etiqueta del botón de acción")
    priority: str = Field(..., description="Prioridad de la notificación")
    expires_at: datetime | None = Field(None, description="Fecha de expiración")
    is_active: bool = Field(..., description="Si la notificación está activa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Notification List Response
# ==========================================

class NotificationListResponse(BaseModel):
    """Esquema de respuesta para lista de notificaciones con conteo"""
    notifications: list[NotificationResponse] = Field(
        default_factory=list,
        description="Lista de notificaciones",
    )
    unread_count: int = Field(
        ...,
        description="Cantidad de notificaciones no leídas",
    )
