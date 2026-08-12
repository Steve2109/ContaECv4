"""
ContaEC - Esquemas Pydantic de Registro de Auditoría
Schemas para consulta y respuesta de registros de auditoría
"""
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Esquema de respuesta para un registro de auditoría"""
    id: UUID = Field(..., description="ID único del registro")
    user_id: UUID | None = Field(None, description="ID del usuario")
    user_email: str | None = Field(None, description="Correo del usuario")
    action: str = Field(..., description="Acción realizada")
    entity_type: str = Field(..., description="Tipo de entidad afectada")
    entity_id: UUID | None = Field(None, description="ID de la entidad afectada")
    description: str = Field(..., description="Descripción de la acción")
    ip_address: str | None = Field(None, description="Dirección IP")
    user_agent: str | None = Field(None, description="User-Agent del cliente")
    old_values: str | None = Field(None, description="Valores anteriores (JSON)")
    new_values: str | None = Field(None, description="Valores nuevos (JSON)")
    created_at: datetime = Field(..., description="Fecha y hora de la acción")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class AuditStatsResponse(BaseModel):
    """Estadísticas del registro de auditoría"""
    total_actions: int = Field(..., description="Total de acciones registradas")
    actions_by_type: dict[str, int] = Field(
        ..., description="Acciones agrupadas por tipo"
    )
    actions_by_entity: dict[str, int] = Field(
        ..., description="Acciones agrupadas por tipo de entidad"
    )
    recent_logins: int = Field(..., description="Logins en las últimas 24 horas")
