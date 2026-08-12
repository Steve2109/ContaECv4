"""
ContaEC - Esquemas Pydantic de Producto/Servicio
Schemas para creación, actualización y respuesta de productos
con impuestos según catálogos del SRI (Tabla 16 IVA, Tabla 18 ICE)
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    """Esquema para crear un nuevo producto o servicio"""
    company_id: str = Field(
        ...,
        description="ID de la empresa a la que pertenece el producto",
    )
    codigo_principal: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código principal del producto (SKU)",
        examples=["PROD001"],
    )
    codigo_auxiliar: str | None = Field(
        None,
        max_length=50,
        description="Código auxiliar del producto",
    )
    descripcion: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Descripción del producto o servicio",
        examples=["Servicio de consultoría informática"],
    )
    tipo: str = Field(
        ...,
        description="Tipo de producto: B=Bien, S=Servicio",
        examples=["B"],
    )
    precio_unitario: Decimal = Field(
        ...,
        gt=0,
        description="Precio unitario del producto (sin impuestos)",
        examples=["100.00"],
    )
    iva_codigo: str = Field(
        default="4",
        max_length=2,
        description="Código de tarifa de IVA según Tabla 16 del SRI (4=15% default, 10=13%, 2=12%, etc)",
        examples=["4"],
    )
    iva_porcentaje: Decimal = Field(
        default=Decimal("15.00"),
        ge=0,
        description="Porcentaje de IVA (default 15%, también: 0, 5, 8, 12, 13, 14)",
        examples=["15.00"],
    )
    iva_incluido: bool | None = Field(
        None,
        description="Indica si el IVA está incluido en el precio unitario",
    )
    ice_codigo: str | None = Field(
        None,
        max_length=3,
        description="Código de tarifa de ICE según Tabla 18 del SRI",
    )
    ice_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de ICE (si aplica)",
    )
    valor_ice_unitario: Decimal | None = Field(
        None,
        ge=0,
        description="Valor ICE unitario en moneda",
    )
    valor_irbpnr: Decimal | None = Field(
        None,
        ge=0,
        description="Valor del impuesto IRBP_NR por unidad",
    )
    subsidio: Decimal | None = Field(
        None,
        ge=0,
        description="Subsidio aplicable al producto",
    )
    categoria: str | None = Field(
        None,
        max_length=100,
        description="Categoría del producto",
    )
    detalle: str | None = Field(
        None,
        max_length=500,
        description="Detalle adicional del producto",
    )
    imagen: str | None = Field(
        None,
        max_length=500,
        description="Ruta o URL de la imagen del producto",
    )
    unidad_medida: str = Field(
        default="Unidad",
        max_length=50,
        description="Unidad de medida (ej: Unidad, Kilogramo, Litro)",
    )
    descuento: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        description="Porcentaje de descuento por defecto",
    )
    codigo_barras: str | None = Field(
        None,
        max_length=50,
        description="Código de barras EAN/UPC del producto",
    )
    stock: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Cantidad actual en stock",
    )
    stock_minimo: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Nivel mínimo de stock para alertas",
    )
    ubicacion: str | None = Field(
        None,
        max_length=100,
        description="Ubicación física en bodega/almacén",
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        """Valida que el tipo sea B (Bien) o S (Servicio)"""
        if v not in ("B", "S"):
            raise ValueError("El tipo debe ser 'B' (Bien) o 'S' (Servicio)")
        return v


class ProductUpdate(BaseModel):
    """Esquema para actualizar un producto o servicio"""
    codigo_principal: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Código principal del producto (SKU)",
    )
    codigo_auxiliar: str | None = Field(
        None,
        max_length=50,
        description="Código auxiliar del producto",
    )
    descripcion: str | None = Field(
        None,
        min_length=1,
        max_length=500,
        description="Descripción del producto o servicio",
    )
    tipo: str | None = Field(
        None,
        description="Tipo de producto: B=Bien, S=Servicio",
    )
    precio_unitario: Decimal | None = Field(
        None,
        gt=0,
        description="Precio unitario (sin impuestos)",
    )
    iva_codigo: str | None = Field(
        None,
        max_length=2,
        description="Código de tarifa de IVA",
    )
    iva_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de IVA",
    )
    ice_codigo: str | None = Field(
        None,
        max_length=3,
        description="Código de tarifa de ICE",
    )
    ice_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de ICE",
    )
    valor_ice_unitario: Decimal | None = Field(
        None,
        ge=0,
        description="Valor ICE unitario",
    )
    valor_irbpnr: Decimal | None = Field(
        None,
        ge=0,
        description="Valor IRBP_NR",
    )
    iva_incluido: bool | None = Field(
        None,
        description="IVA incluido en precio",
    )
    subsidio: Decimal | None = Field(
        None,
        ge=0,
        description="Subsidio",
    )
    categoria: str | None = Field(
        None,
        max_length=100,
        description="Categoría",
    )
    detalle: str | None = Field(
        None,
        max_length=500,
        description="Detalle",
    )
    imagen: str | None = Field(
        None,
        max_length=500,
        description="Imagen",
    )
    unidad_medida: str | None = Field(
        None,
        max_length=50,
        description="Unidad de medida",
    )
    descuento: Decimal | None = Field(
        None,
        ge=0,
        le=100,
        description="Porcentaje de descuento por defecto",
    )
    codigo_barras: str | None = Field(
        None,
        max_length=50,
        description="Código de barras EAN/UPC",
    )
    stock: Decimal | None = Field(
        None,
        ge=0,
        description="Cantidad en stock",
    )
    stock_minimo: Decimal | None = Field(
        None,
        ge=0,
        description="Nivel mínimo de stock",
    )
    ubicacion: str | None = Field(
        None,
        max_length=100,
        description="Ubicación física en bodega",
    )
    is_active: bool | None = Field(
        None,
        description="Indica si el producto está activo",
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str | None) -> str | None:
        """Valida que el tipo sea B (Bien) o S (Servicio)"""
        if v is not None and v not in ("B", "S"):
            raise ValueError("El tipo debe ser 'B' (Bien) o 'S' (Servicio)")
        return v


class ProductResponse(BaseModel):
    """Esquema de respuesta para un producto o servicio"""
    id: UUID = Field(..., description="ID único del producto")
    company_id: UUID = Field(..., description="ID de la empresa")
    codigo_principal: str = Field(..., description="Código principal (SKU)")
    codigo_auxiliar: str | None = Field(None, description="Código auxiliar")
    descripcion: str = Field(..., description="Descripción")
    tipo: str = Field(..., description="Tipo: B=Bien, S=Servicio")
    precio_unitario: Decimal = Field(..., description="Precio unitario sin impuestos")
    iva_codigo: str = Field(..., description="Código de tarifa IVA")
    iva_porcentaje: Decimal = Field(..., description="Porcentaje de IVA")
    iva_incluido: bool | None = Field(None, description="Indica si el IVA está incluido en el precio")
    ice_codigo: str | None = Field(None, description="Código de tarifa ICE")
    ice_porcentaje: Decimal | None = Field(None, description="Porcentaje de ICE")
    valor_ice_unitario: Decimal | None = Field(None, description="Valor ICE unitario")
    valor_irbpnr: Decimal | None = Field(None, description="Valor IRBP_NR (impuesto a vehículos)")
    subsidio: Decimal | None = Field(None, description="Subsidio aplicable")
    categoria: str | None = Field(None, description="Categoría del producto")
    detalle: str | None = Field(None, description="Detalle adicional del producto")
    imagen: str | None = Field(None, description="Ruta de la imagen del producto")
    unidad_medida: str = Field(..., description="Unidad de medida")
    descuento: Decimal = Field(..., description="Porcentaje de descuento")
    codigo_barras: str | None = Field(None, description="Código de barras EAN/UPC")
    stock: Decimal = Field(..., description="Cantidad actual en stock")
    stock_minimo: Decimal = Field(..., description="Nivel mínimo de stock para alertas")
    ubicacion: str | None = Field(None, description="Ubicación física en bodega")
    is_active: bool = Field(..., description="Indica si está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
