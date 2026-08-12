"""
ContaEC - Esquemas Pydantic de Multi-Almacén y Logística
Schemas para almacenes, ubicaciones, transferencias y stock
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Almacén (Warehouse)
# ==========================================

class WarehouseCreate(BaseModel):
    """Esquema para crear un nuevo almacén"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre del almacén",
        examples=["Bodega Principal"],
    )
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Código del almacén (ej: BOD-001), único por empresa",
        examples=["BOD-001"],
    )
    direccion: str | None = Field(
        None,
        max_length=500,
        description="Dirección del almacén",
    )
    ciudad: str | None = Field(
        None,
        max_length=100,
        description="Ciudad donde se ubica el almacén",
    )
    responsable: str | None = Field(
        None,
        max_length=200,
        description="Persona responsable del almacén",
    )
    telefono: str | None = Field(
        None,
        max_length=50,
        description="Teléfono del almacén",
    )
    is_principal: bool = Field(
        default=False,
        description="Indica si es el almacén principal (solo uno por empresa)",
    )


class WarehouseUpdate(BaseModel):
    """Esquema para actualizar un almacén"""
    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre del almacén",
    )
    codigo: str | None = Field(
        None,
        min_length=1,
        max_length=20,
        description="Código del almacén",
    )
    direccion: str | None = Field(
        None,
        max_length=500,
        description="Dirección del almacén",
    )
    ciudad: str | None = Field(
        None,
        max_length=100,
        description="Ciudad",
    )
    responsable: str | None = Field(
        None,
        max_length=200,
        description="Responsable",
    )
    telefono: str | None = Field(
        None,
        max_length=50,
        description="Teléfono",
    )
    is_principal: bool | None = Field(
        None,
        description="¿Es almacén principal?",
    )


class WarehouseResponse(BaseModel):
    """Esquema de respuesta para un almacén"""
    id: UUID = Field(..., description="ID único del almacén")
    company_id: UUID = Field(..., description="ID de la empresa")
    nombre: str = Field(..., description="Nombre del almacén")
    codigo: str = Field(..., description="Código del almacén")
    direccion: str | None = Field(None, description="Dirección")
    ciudad: str | None = Field(None, description="Ciudad")
    responsable: str | None = Field(None, description="Responsable")
    telefono: str | None = Field(None, description="Teléfono")
    is_principal: bool = Field(..., description="¿Es almacén principal?")
    is_active: bool = Field(..., description="¿Está activo?")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Ubicación de Almacén (WarehouseLocation)
# ==========================================

class WarehouseLocationCreate(BaseModel):
    """Esquema para crear una ubicación dentro de un almacén"""
    producto_id: str | None = Field(
        None,
        description="ID del producto asignado a esta ubicación (opcional)",
    )
    zona: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Zona del almacén (ej: A, B, C, Refrigerados)",
        examples=["A"],
    )
    pasillo: str | None = Field(
        None,
        max_length=50,
        description="Pasillo o corredor dentro de la zona",
        examples=["3"],
    )
    rack: str | None = Field(
        None,
        max_length=50,
        description="Rack o estante dentro del pasillo (ej: R1, R2, B)",
        examples=["R1"],
    )
    estante: str | None = Field(
        None,
        max_length=50,
        description="Nivel del rack o estante (ej: E1, E2, 2)",
        examples=["E1"],
    )
    nivel: str | None = Field(
        None,
        max_length=50,
        description="Posición dentro del estante/bin (opcional)",
    )
    capacidad_maxima: int | None = Field(
        None,
        ge=1,
        description="Capacidad máxima en unidades",
    )
    capacidad_actual: int = Field(
        default=0,
        ge=0,
        description="Ocupación actual en unidades",
    )

    @field_validator("capacidad_actual")
    @classmethod
    def validate_capacidad_actual(cls, v: int, values) -> int:
        """Valida que capacidad_actual no exceda capacidad_maxima si está definida"""
        max_cap = values.data.get("capacidad_maxima")
        if max_cap is not None and v > max_cap:
            raise ValueError(
                f"La ocupación actual ({v}) no puede exceder la capacidad máxima ({max_cap})"
            )
        return v


class WarehouseLocationUpdate(BaseModel):
    """Esquema para actualizar una ubicación de almacén"""
    producto_id: str | None = Field(
        None,
        description="ID del producto asignado",
    )
    zona: str | None = Field(
        None,
        max_length=50,
        description="Zona del almacén",
    )
    pasillo: str | None = Field(
        None,
        max_length=50,
        description="Pasillo o corredor",
    )
    rack: str | None = Field(
        None,
        max_length=50,
        description="Rack",
    )
    estante: str | None = Field(
        None,
        max_length=50,
        description="Estante",
    )
    nivel: str | None = Field(
        None,
        max_length=50,
        description="Nivel/posición",
    )
    capacidad_maxima: int | None = Field(
        None,
        ge=1,
        description="Capacidad máxima en unidades",
    )
    capacidad_actual: int | None = Field(
        None,
        ge=0,
        description="Ocupación actual en unidades",
    )


class WarehouseLocationResponse(BaseModel):
    """Esquema de respuesta para una ubicación de almacén"""
    id: UUID = Field(..., description="ID único de la ubicación")
    warehouse_id: UUID = Field(..., description="ID del almacén")
    producto_id: UUID | None = Field(None, description="ID del producto")
    zona: str = Field(..., description="Zona")
    pasillo: str | None = Field(None, description="Pasillo o corredor")
    rack: str | None = Field(None, description="Rack o estante")
    estante: str | None = Field(None, description="Nivel del rack o estante")
    nivel: str | None = Field(None, description="Nivel/posición dentro del estante")
    codigo_ubicacion: str = Field(..., description="Código de ubicación (ej: A-P3-RB-E2)")
    ubicacion_completa: str = Field(..., description="Descripción completa (ej: ZonaA-Pasillo3-RackB-Estante2)")
    capacidad_maxima: int | None = Field(None, description="Capacidad máxima en unidades")
    capacidad_actual: int = Field(..., description="Ocupación actual en unidades")
    is_active: bool = Field(..., description="¿Está activa?")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class WarehouseLocationStockResponse(BaseModel):
    """Esquema de respuesta para el stock en una ubicación específica"""
    product_id: str = Field(..., description="ID del producto")
    product_codigo: str = Field(..., description="Código del producto")
    product_descripcion: str = Field(..., description="Descripción del producto")
    cantidad: Decimal = Field(..., description="Cantidad del producto en esta ubicación")


class WarehouseLocationMapResponse(BaseModel):
    """Esquema de respuesta para el mapa visual de un almacén"""
    warehouse_id: UUID = Field(..., description="ID del almacén")
    warehouse_nombre: str = Field(..., description="Nombre del almacén")
    zonas: dict[str, list[WarehouseLocationResponse]] = Field(
        ...,
        description="Ubicaciones agrupadas por zona",
    )
    total_ubicaciones: int = Field(..., description="Total de ubicaciones en el almacén")
    ubicaciones_disponibles: int = Field(..., description="Ubicaciones sin producto asignado")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Transferencia entre Almacenes
# ==========================================

class WarehouseTransferDetalleCreate(BaseModel):
    """Esquema para crear una línea de detalle de transferencia"""
    product_id: str = Field(
        ...,
        description="ID del producto a transferir",
    )
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad a transferir",
    )
    costo_unitario: Decimal = Field(
        ...,
        ge=0,
        description="Costo unitario del producto",
    )
    ubicacion_origen_id: str | None = Field(
        None,
        description="ID de la ubicación de origen dentro del almacén origen",
    )
    ubicacion_destino_id: str | None = Field(
        None,
        description="ID de la ubicación de destino dentro del almacén destino",
    )


class WarehouseTransferDetalleResponse(BaseModel):
    """Esquema de respuesta para una línea de detalle de transferencia"""
    id: UUID = Field(..., description="ID único del detalle")
    transferencia_id: UUID = Field(..., description="ID de la transferencia")
    product_id: UUID = Field(..., description="ID del producto")
    cantidad: Decimal = Field(..., description="Cantidad transferida")
    costo_unitario: Decimal = Field(..., description="Costo unitario")
    costo_total: Decimal = Field(..., description="Costo total")
    ubicacion_origen_id: UUID | None = Field(None, description="ID ubicación origen")
    ubicacion_destino_id: UUID | None = Field(None, description="ID ubicación destino")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class WarehouseTransferCreate(BaseModel):
    """Esquema para crear una nueva transferencia entre almacenes"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    warehouse_origen_id: str = Field(
        ...,
        description="ID del almacén de origen",
    )
    warehouse_destino_id: str = Field(
        ...,
        description="ID del almacén de destino",
    )
    detalles: list[WarehouseTransferDetalleCreate] = Field(
        ...,
        min_length=1,
        description="Lista de líneas de detalle",
    )
    motivo: str | None = Field(
        None,
        max_length=500,
        description="Motivo de la transferencia",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )

    @field_validator("warehouse_destino_id")
    @classmethod
    def validate_destino_diferente(cls, v: str, values) -> str:
        """Valida que el almacén de destino sea diferente al de origen"""
        origen = values.data.get("warehouse_origen_id")
        if origen and v == origen:
            raise ValueError("El almacén de destino debe ser diferente al de origen")
        return v


class WarehouseTransferResponse(BaseModel):
    """Esquema de respuesta para una transferencia entre almacenes"""
    id: UUID = Field(..., description="ID único de la transferencia")
    company_id: UUID = Field(..., description="ID de la empresa")
    numero: str = Field(..., description="Número de transferencia")
    warehouse_origen_id: UUID = Field(..., description="ID almacén origen")
    warehouse_destino_id: UUID = Field(..., description="ID almacén destino")
    estado: str = Field(..., description="Estado: pendiente, en_transito, recibida, anulada")
    motivo: str | None = Field(None, description="Motivo")
    observaciones: str | None = Field(None, description="Observaciones")
    user_id: UUID = Field(..., description="ID del usuario creador")
    fecha_envio: datetime | None = Field(None, description="Fecha de envío")
    fecha_recepcion: datetime | None = Field(None, description="Fecha de recepción")
    detalles: list[WarehouseTransferDetalleResponse] = Field(
        default_factory=list,
        description="Líneas de detalle",
    )
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Stock de Almacén
# ==========================================

class WarehouseStockResponse(BaseModel):
    """Esquema de respuesta para el stock de un producto en un almacén"""
    product_id: UUID = Field(..., description="ID del producto")
    producto_codigo: str = Field(..., description="Código principal del producto")
    producto_descripcion: str = Field(..., description="Descripción del producto")
    saldo_cantidad: Decimal = Field(default=Decimal("0"), description="Cantidad en stock")
    saldo_valor: Decimal = Field(default=Decimal("0"), description="Valor en stock")
    costo_promedio: Decimal = Field(default=Decimal("0"), description="Costo promedio ponderado")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Kardex Detallado con información de almacén
# ==========================================

class KardexDetalladoResponse(BaseModel):
    """Esquema de respuesta para un movimiento de kardex con información de almacén"""
    id: UUID = Field(..., description="ID único del movimiento")
    company_id: UUID = Field(..., description="ID de la empresa")
    product_id: UUID = Field(..., description="ID del producto")
    warehouse_id: UUID | None = Field(None, description="ID del almacén")
    warehouse_nombre: str | None = Field(None, description="Nombre del almacén")
    tipo_movimiento: str = Field(..., description="Tipo de movimiento")
    cantidad: Decimal = Field(..., description="Cantidad del movimiento")
    costo_unitario: Decimal = Field(..., description="Costo unitario")
    costo_total: Decimal = Field(..., description="Costo total del movimiento")
    saldo_cantidad: Decimal = Field(..., description="Saldo de cantidad acumulado")
    saldo_valor: Decimal = Field(..., description="Saldo de valor acumulado")
    referencia_tipo: str | None = Field(None, description="Tipo de referencia")
    referencia_id: UUID | None = Field(None, description="ID de referencia")
    referencia_secuencial: str | None = Field(None, description="Secuencial de referencia")
    detalle: str | None = Field(None, description="Detalle del movimiento")
    fecha_movimiento: datetime = Field(..., description="Fecha del movimiento")
    user_id: UUID = Field(..., description="ID del usuario")
    is_active: bool = Field(..., description="¿Está activo?")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
