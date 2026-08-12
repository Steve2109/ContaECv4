"""
ContaEC - Schemas de Machine Learning / IA
Schemas para predicciones, fraude, chatbot, recomendaciones, categorización
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ========================================
# Predicciones ML
# ========================================

class PrediccionCreate(BaseModel):
    company_id: str
    tipo: str = Field(..., pattern="^(ventas|ingresos|gastos|flujo_caja)$")
    modelo_usado: str = Field(
        default="moving_average",
        pattern="^(moving_average|exponential_smoothing|linear_regression|arima)$",
    )
    periodo_desde: datetime
    periodo_hasta: datetime
    datos_entrada: str | None = None


class PrediccionUpdate(BaseModel):
    estado: str | None = Field(None, pattern="^(pendiente|completada|con_error)$")
    resultado: str | None = None
    metricas: str | None = None
    confianza: Decimal | None = Field(None, ge=0, le=100)


class PrediccionResponse(BaseModel):
    id: UUID
    company_id: UUID
    user_id: UUID
    tipo: str
    estado: str
    periodo_desde: datetime
    periodo_hasta: datetime
    datos_entrada: str | None
    resultado: str | None
    metricas: str | None
    modelo_usado: str
    confianza: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# Alertas de Fraude
# ========================================

class AlertaFraudeCreate(BaseModel):
    company_id: str
    comprobante_id: str | None = None
    tipo_deteccion: str = Field(
        ...,
        pattern="^(monto_anomalo|duplicado|patron_sospechoso|ruc_invalido|secuencia_anomala)$",
    )
    severidad: str = Field(
        default="media",
        pattern="^(baja|media|alta|critica)$",
    )
    puntuacion_fraude: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    descripcion: str = Field(..., min_length=1)
    evidencia: str | None = None


class AlertaFraudeUpdate(BaseModel):
    estado: str | None = Field(
        None, pattern="^(pendiente|confirmado|descartado|investigando)$"
    )
    severidad: str | None = Field(None, pattern="^(baja|media|alta|critica)$")
    resolucion_nota: str | None = None
    resuelto_por: str | None = None


class AlertaFraudeResponse(BaseModel):
    id: UUID
    company_id: UUID
    comprobante_id: UUID | None
    tipo_deteccion: str
    severidad: str
    estado: str
    puntuacion_fraude: Decimal
    descripcion: str
    evidencia: str | None
    resolucion_nota: str | None
    resolucion_fecha: datetime | None
    resuelto_por: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# Chatbot
# ========================================

class ChatbotSesionCreate(BaseModel):
    company_id: str
    titulo: str | None = None


class ChatbotSesionResponse(BaseModel):
    id: UUID
    company_id: UUID
    user_id: UUID
    estado: str
    titulo: str | None
    contexto: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotMensajeCreate(BaseModel):
    sesion_id: str
    contenido: str = Field(..., min_length=1)


class ChatbotMensajeResponse(BaseModel):
    id: UUID
    sesion_id: UUID
    rol: str
    contenido: str
    intencion_detectada: str | None
    entidades: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """Request para enviar un mensaje al chatbot"""
    sesion_id: str
    mensaje: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    """Response del chatbot con intención detectada y entidades"""
    mensaje_id: str
    respuesta: str
    sesion_id: str
    intencion_detectada: str | None = None
    entidades: dict | None = None


# ========================================
# Recomendaciones
# ========================================

class RecomendacionCreate(BaseModel):
    company_id: str
    tipo: str = Field(..., pattern="^(producto|cliente|precio|inventario|financiera)$")
    titulo: str = Field(..., min_length=1, max_length=200)
    descripcion: str = Field(..., min_length=1)
    datos_contexto: str | None = None
    impacto_estimado: str | None = None
    confianza: Decimal | None = Field(None, ge=0, le=100)


class RecomendacionUpdate(BaseModel):
    estado: str | None = Field(None, pattern="^(pendiente|aplicada|descartada)$")
    aplicada_por: str | None = None


class RecomendacionResponse(BaseModel):
    id: UUID
    company_id: UUID
    user_id: UUID
    tipo: str
    estado: str
    titulo: str
    descripcion: str
    datos_contexto: str | None
    impacto_estimado: str | None
    confianza: Decimal | None
    fecha_aplicacion: datetime | None
    aplicada_por: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# Categorización (Reglas)
# ========================================

class CategoriaReglaCreate(BaseModel):
    company_id: str
    categoria: str = Field(..., min_length=1, max_length=100)
    subcategoria: str | None = Field(None, max_length=100)
    palabras_clave: str = Field(
        ..., description="JSON con lista de palabras clave para matching"
    )
    patron_regex: str | None = Field(None, max_length=500)
    prioridad: int = Field(default=0, ge=0)
    es_activa: bool = True


class CategoriaReglaUpdate(BaseModel):
    categoria: str | None = Field(None, min_length=1, max_length=100)
    subcategoria: str | None = Field(None, max_length=100)
    palabras_clave: str | None = None
    patron_regex: str | None = Field(None, max_length=500)
    prioridad: int | None = Field(None, ge=0)
    es_activa: bool | None = None


class CategoriaReglaResponse(BaseModel):
    id: UUID
    company_id: UUID
    categoria: str
    subcategoria: str | None
    palabras_clave: str
    patron_regex: str | None
    prioridad: int
    es_activa: bool
    aplicaciones_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# Categorización (Endpoint)
# ========================================

class CategorizeRequest(BaseModel):
    """Request para categorizar una descripción"""
    company_id: str
    descripcion: str = Field(..., min_length=1)


class CategorizeResponse(BaseModel):
    """Response con la categoría detectada"""
    categoria: str | None = None
    subcategoria: str | None = None
    confianza: Decimal = Decimal("0")
    regla_aplicada_id: str | None = None
    todas_candidatas: list[dict] = []


# ========================================
# ML Stats
# ========================================

class MLStats(BaseModel):
    """Estadísticas generales de ML/IA"""
    # Predicciones
    total_predicciones: int = 0
    predicciones_completadas: int = 0
    predicciones_pendientes: int = 0
    # Fraude
    total_alertas_fraude: int = 0
    alertas_pendientes: int = 0
    alertas_confirmadas: int = 0
    alertas_criticas: int = 0
    # Chatbot
    total_sesiones_chat: int = 0
    sesiones_activas: int = 0
    total_mensajes: int = 0
    # Recomendaciones
    total_recomendaciones: int = 0
    recomendaciones_pendientes: int = 0
    recomendaciones_aplicadas: int = 0
    # Categorización
    total_reglas: int = 0
    reglas_activas: int = 0
