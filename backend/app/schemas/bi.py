"""
ContaEC - Schemas de Business Intelligence (BI)
Modelos de respuesta para dashboards de KPIs, métricas y alertas
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# KPIs - Real-time metrics
# ==========================================

class KPIResponse(BaseModel):
    """Respuesta con KPIs en tiempo real del negocio"""
    ventas_totales: Decimal = Field(default=Decimal("0"), description="Ventas totales del período (comprobantes AUTORIZADO)")
    ventas_mes_anterior: Decimal = Field(default=Decimal("0"), description="Ventas del mes anterior para comparación")
    variacion_ventas: Decimal | None = Field(default=None, description="% variación de ventas vs mes anterior")
    comprobantes_emitidos: int = Field(default=0, description="Total comprobantes emitidos")
    comprobantes_autorizados: int = Field(default=0, description="Total comprobantes autorizados por SRI")
    comprobantes_rechazados: int = Field(default=0, description="Total comprobantes rechazados por SRI")
    tasa_aprobacion: Decimal | None = Field(default=None, description="Tasa de aprobación SRI (%)")
    ticket_promedio: Decimal = Field(default=Decimal("0"), description="Valor promedio por comprobante autorizado")
    iva_recaudado: Decimal = Field(default=Decimal("0"), description="Total IVA recaudado en el período")
    clientes_activos: int = Field(default=0, description="Número de clientes activos")
    productos_vendidos: Decimal = Field(default=Decimal("0"), description="Total productos vendidos (cantidad)")
    cuentas_por_cobrar: Decimal = Field(default=Decimal("0"), description="Total cuentas por cobrar pendientes")
    cuentas_por_pagar: Decimal = Field(default=Decimal("0"), description="Total cuentas por pagar pendientes")
    inventario_valor: Decimal = Field(default=Decimal("0"), description="Valor total del inventario")
    empleados_activos: int = Field(default=0, description="Número de empleados activos")
    nomina_total: Decimal = Field(default=Decimal("0"), description="Total nómina del período")
    pos_ventas_hoy: Decimal = Field(default=Decimal("0"), description="Ventas POS de hoy")
    pos_tickets_hoy: int = Field(default=0, description="Tickets POS de hoy")


# ==========================================
# Ventas Mensuales
# ==========================================

class VentaMensual(BaseModel):
    """Datos de ventas por mes para gráficos"""
    mes: int = Field(..., description="Número de mes (1-12)")
    nombre_mes: str = Field(..., description="Nombre del mes en español")
    total_ventas: Decimal = Field(default=Decimal("0"), description="Total ventas del mes")
    total_iva: Decimal = Field(default=Decimal("0"), description="Total IVA del mes")
    cantidad_comprobantes: int = Field(default=0, description="Cantidad de comprobantes autorizados")


# ==========================================
# Ventas por Tipo de Comprobante
# ==========================================

class VentaPorTipo(BaseModel):
    """Ventas agrupadas por tipo de comprobante"""
    tipo_comprobante: str = Field(..., description="Código de tipo de comprobante (01, 04, 05, 07, etc.)")
    descripcion: str = Field(..., description="Descripción del tipo de comprobante")
    total: Decimal = Field(default=Decimal("0"), description="Total ventas de este tipo")
    cantidad: int = Field(default=0, description="Cantidad de comprobantes de este tipo")


# ==========================================
# Top Productos
# ==========================================

class TopProducto(BaseModel):
    """Producto más vendido"""
    product_id: str = Field(..., description="ID del producto")
    codigo: str = Field(..., description="Código principal del producto")
    descripcion: str = Field(..., description="Descripción del producto")
    cantidad_vendida: Decimal = Field(default=Decimal("0"), description="Cantidad total vendida")
    total_venta: Decimal = Field(default=Decimal("0"), description="Total de ventas del producto")


# ==========================================
# Top Clientes
# ==========================================

class TopCliente(BaseModel):
    """Cliente con mayor volumen de compras"""
    client_id: str = Field(..., description="ID del cliente")
    identificacion: str = Field(..., description="Número de identificación del cliente")
    razon_social: str = Field(..., description="Razón social o nombre del cliente")
    total_compras: Decimal = Field(default=Decimal("0"), description="Total de compras del cliente")
    cantidad_comprobantes: int = Field(default=0, description="Cantidad de comprobantes del cliente")


# ==========================================
# Flujo de Efectivo
# ==========================================

class FlujoEfectivoMensual(BaseModel):
    """Flujo de efectivo mensual"""
    mes: int = Field(..., description="Número de mes (1-12)")
    ingresos: Decimal = Field(default=Decimal("0"), description="Total ingresos del mes")
    egresos: Decimal = Field(default=Decimal("0"), description="Total egresos del mes")
    flujo_neto: Decimal = Field(default=Decimal("0"), description="Flujo neto (ingresos - egresos)")


# ==========================================
# Alertas
# ==========================================

class AlertaBI(BaseModel):
    """Alerta inteligente del sistema BI"""
    id: str = Field(..., description="ID único de la alerta")
    tipo: str = Field(..., description="Tipo de alerta: warning, danger, info, success")
    titulo: str = Field(..., description="Título de la alerta")
    mensaje: str = Field(..., description="Mensaje descriptivo de la alerta")
    fecha: datetime = Field(..., description="Fecha de generación de la alerta")
    categoria: str = Field(..., description="Categoría: comprobantes, firmas, licencia, inventario, cuentas, iva, pos")


# ==========================================
# Cuadro de Mando (Executive Dashboard)
# ==========================================

class KPIsResumen(BaseModel):
    """Resumen de KPIs financieros clave"""
    ventas_mes: Decimal = Field(default=Decimal("0"))
    variacion_ventas: Decimal | None = Field(default=None)
    ticket_promedio: Decimal = Field(default=Decimal("0"))
    iva_recaudado: Decimal = Field(default=Decimal("0"))
    cuentas_por_cobrar: Decimal = Field(default=Decimal("0"))
    cuentas_por_pagar: Decimal = Field(default=Decimal("0"))
    flujo_neto_mes: Decimal = Field(default=Decimal("0"))
    nomina_total: Decimal = Field(default=Decimal("0"))


class IndicadorCumplimiento(BaseModel):
    """Indicador de cumplimiento normativo"""
    nombre: str = Field(..., description="Nombre del indicador")
    valor: Decimal = Field(default=Decimal("0"), description="Valor del indicador (%)")
    estado: str = Field(..., description="Estado: optimo, aceptable, critico")


class TendenciaMensual(BaseModel):
    """Datos de tendencia para comparación mensual"""
    mes: int = Field(..., description="Número de mes")
    nombre_mes: str = Field(..., description="Nombre del mes")
    ventas: Decimal = Field(default=Decimal("0"))
    comprobantes: int = Field(default=0)
    ticket_promedio: Decimal = Field(default=Decimal("0"))


class CuadroMandoResponse(BaseModel):
    """Respuesta del Cuadro de Mando ejecutivo"""
    kpis_resumen: KPIsResumen = Field(..., description="Resumen de KPIs financieros")
    indicadores_cumplimiento: list[IndicadorCumplimiento] = Field(
        default_factory=list,
        description="Indicadores de cumplimiento SRI y normativo"
    )
    tendencias: list[TendenciaMensual] = Field(
        default_factory=list,
        description="Tendencias de los últimos 3 meses"
    )
    estado_general: int = Field(
        default=0,
        description="Salud general del negocio (0-100)",
        ge=0,
        le=100,
    )


# ==========================================
# Power BI Export
# ==========================================

class FactVentaRow(BaseModel):
    """Fila de la tabla de hechos de ventas para Power BI"""
    comprobante_id: UUID
    tipo_comprobante: str
    secuencial: str
    fecha_emision: str
    estado: str
    cliente_id: UUID | None = None
    product_id: UUID | None = None
    cantidad: Decimal | None = None
    precio_unitario: Decimal | None = None
    subtotal_sin_impuestos: Decimal
    total_iva: Decimal
    total_con_impuestos: Decimal
    iva_porcentaje: Decimal | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DimProducto(BaseModel):
    """Dimensión de producto para Power BI"""
    product_id: UUID
    codigo_principal: str
    codigo_auxiliar: str | None = None
    descripcion: str
    tipo: str
    precio_unitario: Decimal
    iva_porcentaje: Decimal
    stock: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DimCliente(BaseModel):
    """Dimensión de cliente para Power BI"""
    client_id: UUID
    tipo_identificacion: str
    identificacion: str
    razon_social: str
    email: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DimTiempo(BaseModel):
    """Dimensión de tiempo para Power BI"""
    fecha: str
    anio: int
    mes: int
    dia: int
    nombre_mes: str
    trimestre: int
    semana: int
    dia_semana: int
    nombre_dia: str
    es_fin_semana: bool

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class FactInventarioRow(BaseModel):
    """Fila de la tabla de hechos de inventario para Power BI"""
    product_id: UUID
    codigo_principal: str
    descripcion: str
    stock: Decimal
    stock_minimo: Decimal
    valor_inventario: Decimal
    ubicacion: str | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class PowerBIExport(BaseModel):
    """Exportación de datos compatible con Power BI"""
    fact_ventas: list[FactVentaRow] = Field(default_factory=list)
    dim_productos: list[DimProducto] = Field(default_factory=list)
    dim_clientes: list[DimCliente] = Field(default_factory=list)
    dim_tiempo: list[DimTiempo] = Field(default_factory=list)
    fact_inventario: list[FactInventarioRow] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
