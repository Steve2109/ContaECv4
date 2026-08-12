"""
ContaEC - Esquemas Pydantic de Proyectos y Servicios
Schemas para proyectos, tareas, recursos, timesheets y costos
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Proyecto schemas
# ==========================================

class ProyectoCreate(BaseModel):
    """Esquema para crear un proyecto"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código del proyecto (ej: PRY-001)",
        examples=["PRY-001"],
    )
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre del proyecto",
        examples=["Implementación ERP"],
    )
    descripcion: str | None = Field(
        None,
        description="Descripción detallada del proyecto",
    )
    cliente_id: str | None = Field(
        None,
        description="ID del cliente asociado al proyecto",
    )
    cliente_nombre: str | None = Field(
        None,
        max_length=200,
        description="Nombre del cliente (denormalizado)",
    )
    estado: str | None = Field(
        None,
        description="Estado: planificacion, en_progreso, en_pausa, completado, cancelado",
        examples=["planificacion"],
    )
    fecha_inicio: datetime | None = Field(
        None,
        description="Fecha de inicio del proyecto",
    )
    fecha_fin_estimada: datetime | None = Field(
        None,
        description="Fecha de fin estimada del proyecto",
    )
    presupuesto: Decimal | None = Field(
        None,
        ge=0,
        description="Monto presupuestado del proyecto",
        examples=["50000.00"],
    )
    responsable: str | None = Field(
        None,
        max_length=200,
        description="Nombre del responsable / gerente del proyecto",
    )
    notas: str | None = Field(
        None,
        description="Notas adicionales del proyecto",
    )


class ProyectoUpdate(BaseModel):
    """Esquema para actualizar un proyecto"""
    codigo: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Código del proyecto",
    )
    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre del proyecto",
    )
    descripcion: str | None = Field(
        None,
        description="Descripción detallada del proyecto",
    )
    cliente_id: str | None = Field(
        None,
        description="ID del cliente asociado",
    )
    cliente_nombre: str | None = Field(
        None,
        max_length=200,
        description="Nombre del cliente",
    )
    estado: str | None = Field(
        None,
        description="Estado del proyecto",
    )
    fecha_inicio: datetime | None = Field(
        None,
        description="Fecha de inicio",
    )
    fecha_fin_estimada: datetime | None = Field(
        None,
        description="Fecha de fin estimada",
    )
    fecha_fin_real: datetime | None = Field(
        None,
        description="Fecha de fin real",
    )
    presupuesto: Decimal | None = Field(
        None,
        ge=0,
        description="Monto presupuestado",
    )
    ingreso: Decimal | None = Field(
        None,
        ge=0,
        description="Ingreso total del proyecto",
    )
    responsable: str | None = Field(
        None,
        max_length=200,
        description="Nombre del responsable",
    )
    notas: str | None = Field(
        None,
        description="Notas adicionales",
    )


class ProyectoTareaResponse(BaseModel):
    """Esquema de respuesta para tarea de proyecto"""
    id: UUID = Field(..., description="ID único de la tarea")
    proyecto_id: UUID = Field(..., description="ID del proyecto")
    titulo: str = Field(..., description="Título de la tarea")
    descripcion: str | None = Field(None, description="Descripción de la tarea")
    estado: str = Field(..., description="Estado de la tarea")
    prioridad: str = Field(..., description="Prioridad de la tarea")
    fase: str | None = Field(None, description="Fase del proyecto")
    asignado_a: str | None = Field(None, description="Persona asignada")
    employee_id: UUID | None = Field(None, description="ID del empleado asignado")
    fecha_inicio: datetime | None = Field(None, description="Fecha de inicio")
    fecha_fin_estimada: datetime | None = Field(None, description="Fecha de fin estimada")
    fecha_fin_real: datetime | None = Field(None, description="Fecha de fin real")
    horas_estimadas: Decimal = Field(..., description="Horas estimadas")
    horas_reales: Decimal = Field(..., description="Horas reales trabajadas")
    progreso: Decimal = Field(..., description="Porcentaje de progreso")
    orden: int = Field(..., description="Orden de la tarea")
    is_active: bool = Field(..., description="Está activa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProyectoRecursoResponse(BaseModel):
    """Esquema de respuesta para recurso de proyecto"""
    id: UUID = Field(..., description="ID único del recurso")
    proyecto_id: UUID = Field(..., description="ID del proyecto")
    tipo_recurso: str = Field(..., description="Tipo de recurso")
    nombre: str = Field(..., description="Nombre del recurso")
    descripcion: str | None = Field(None, description="Descripción del recurso")
    employee_id: UUID | None = Field(None, description="ID del empleado (si es humano)")
    costo_unitario: Decimal = Field(..., description="Costo unitario del recurso")
    cantidad: Decimal = Field(..., description="Cantidad del recurso")
    costo_total: Decimal = Field(..., description="Costo total del recurso")
    fecha_asignacion: datetime | None = Field(None, description="Fecha de asignación")
    fecha_liberacion: datetime | None = Field(None, description="Fecha de liberación")
    is_active: bool = Field(..., description="Está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProyectoTimesheetResponse(BaseModel):
    """Esquema de respuesta para timesheet de proyecto"""
    id: UUID = Field(..., description="ID único del timesheet")
    company_id: UUID = Field(..., description="ID de la empresa")
    proyecto_id: UUID = Field(..., description="ID del proyecto")
    tarea_id: UUID | None = Field(None, description="ID de la tarea asociada")
    employee_id: UUID | None = Field(None, description="ID del empleado")
    empleado_nombre: str = Field(..., description="Nombre del empleado")
    fecha: datetime = Field(..., description="Fecha del trabajo")
    horas: Decimal = Field(..., description="Horas trabajadas")
    tarifa_hora: Decimal = Field(..., description="Tarifa por hora")
    costo_total: Decimal = Field(..., description="Costo total (horas * tarifa)")
    descripcion: str | None = Field(None, description="Descripción del trabajo")
    es_facturable: bool = Field(..., description="Si las horas son facturables")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProyectoCostoResponse(BaseModel):
    """Esquema de respuesta para costo de proyecto"""
    id: UUID = Field(..., description="ID único del costo")
    proyecto_id: UUID = Field(..., description="ID del proyecto")
    concepto: str = Field(..., description="Concepto del costo")
    descripcion: str | None = Field(None, description="Descripción del costo")
    monto: Decimal = Field(..., description="Monto del costo")
    fecha: datetime = Field(..., description="Fecha del costo")
    categoria: str | None = Field(None, description="Categoría del costo")
    es_facturable: bool = Field(..., description="Si el costo es facturable")
    comprobante_id: UUID | None = Field(None, description="ID del comprobante vinculado")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProyectoResponse(BaseModel):
    """Esquema de respuesta para proyecto"""
    id: UUID = Field(..., description="ID único del proyecto")
    company_id: UUID = Field(..., description="ID de la empresa")
    user_id: UUID = Field(..., description="ID del usuario creador")
    codigo: str = Field(..., description="Código del proyecto")
    nombre: str = Field(..., description="Nombre del proyecto")
    descripcion: str | None = Field(None, description="Descripción")
    cliente_id: UUID | None = Field(None, description="ID del cliente")
    cliente_nombre: str | None = Field(None, description="Nombre del cliente")
    estado: str = Field(..., description="Estado del proyecto")
    fecha_inicio: datetime | None = Field(None, description="Fecha de inicio")
    fecha_fin_estimada: datetime | None = Field(None, description="Fecha de fin estimada")
    fecha_fin_real: datetime | None = Field(None, description="Fecha de fin real")
    presupuesto: Decimal = Field(..., description="Monto presupuestado")
    costo_real: Decimal = Field(..., description="Costo real acumulado")
    ingreso: Decimal = Field(..., description="Ingreso total")
    margen: Decimal = Field(..., description="Margen del proyecto")
    margen_porcentaje: Decimal = Field(..., description="Porcentaje de margen")
    progreso: Decimal = Field(..., description="Porcentaje de progreso")
    responsable: str | None = Field(None, description="Responsable del proyecto")
    notas: str | None = Field(None, description="Notas adicionales")
    is_active: bool = Field(..., description="Está activo")
    tareas: list[ProyectoTareaResponse] = Field(
        default_factory=list,
        description="Tareas del proyecto",
    )
    recursos: list[ProyectoRecursoResponse] = Field(
        default_factory=list,
        description="Recursos del proyecto",
    )
    timesheets: list[ProyectoTimesheetResponse] = Field(
        default_factory=list,
        description="Timesheets del proyecto",
    )
    costos: list[ProyectoCostoResponse] = Field(
        default_factory=list,
        description="Costos del proyecto",
    )
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# ProyectoTarea schemas (Create / Update)
# ==========================================

class ProyectoTareaCreate(BaseModel):
    """Esquema para crear una tarea de proyecto"""
    titulo: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Título de la tarea",
        examples=["Diseño de base de datos"],
    )
    descripcion: str | None = Field(
        None,
        description="Descripción detallada de la tarea",
    )
    estado: str | None = Field(
        None,
        description="Estado: pendiente, en_progreso, completada, cancelada",
        examples=["pendiente"],
    )
    prioridad: str | None = Field(
        None,
        description="Prioridad: baja, media, alta, critica",
        examples=["media"],
    )
    fase: str | None = Field(
        None,
        max_length=100,
        description="Nombre de la fase del proyecto",
    )
    asignado_a: str | None = Field(
        None,
        max_length=200,
        description="Nombre de la persona asignada",
    )
    employee_id: str | None = Field(
        None,
        description="ID del empleado asignado",
    )
    fecha_inicio: datetime | None = Field(
        None,
        description="Fecha de inicio de la tarea",
    )
    fecha_fin_estimada: datetime | None = Field(
        None,
        description="Fecha de fin estimada",
    )
    horas_estimadas: Decimal | None = Field(
        None,
        ge=0,
        description="Horas estimadas para completar la tarea",
        examples=["40.00"],
    )
    orden: int | None = Field(
        None,
        ge=0,
        description="Orden de la tarea dentro del proyecto",
    )


class ProyectoTareaUpdate(BaseModel):
    """Esquema para actualizar una tarea de proyecto"""
    titulo: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Título de la tarea",
    )
    descripcion: str | None = Field(
        None,
        description="Descripción de la tarea",
    )
    estado: str | None = Field(
        None,
        description="Estado de la tarea",
    )
    prioridad: str | None = Field(
        None,
        description="Prioridad de la tarea",
    )
    fase: str | None = Field(
        None,
        max_length=100,
        description="Fase del proyecto",
    )
    asignado_a: str | None = Field(
        None,
        max_length=200,
        description="Persona asignada",
    )
    employee_id: str | None = Field(
        None,
        description="ID del empleado asignado",
    )
    fecha_inicio: datetime | None = Field(
        None,
        description="Fecha de inicio",
    )
    fecha_fin_estimada: datetime | None = Field(
        None,
        description="Fecha de fin estimada",
    )
    fecha_fin_real: datetime | None = Field(
        None,
        description="Fecha de fin real",
    )
    horas_estimadas: Decimal | None = Field(
        None,
        ge=0,
        description="Horas estimadas",
    )
    horas_reales: Decimal | None = Field(
        None,
        ge=0,
        description="Horas reales trabajadas",
    )
    progreso: Decimal | None = Field(
        None,
        ge=0,
        le=100,
        description="Porcentaje de progreso (0-100)",
    )
    orden: int | None = Field(
        None,
        ge=0,
        description="Orden de la tarea",
    )


# ==========================================
# ProyectoRecurso schemas (Create / Update)
# ==========================================

class ProyectoRecursoCreate(BaseModel):
    """Esquema para crear un recurso de proyecto"""
    tipo_recurso: str = Field(
        ...,
        description="Tipo de recurso: humano, material, equipo",
        examples=["humano"],
    )
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre del recurso",
        examples=["Juan Pérez"],
    )
    descripcion: str | None = Field(
        None,
        description="Descripción del recurso",
    )
    employee_id: str | None = Field(
        None,
        description="ID del empleado (si el recurso es humano)",
    )
    costo_unitario: Decimal | None = Field(
        None,
        ge=0,
        description="Costo unitario del recurso",
        examples=["25.00"],
    )
    cantidad: Decimal | None = Field(
        None,
        ge=0,
        description="Cantidad del recurso asignado",
        examples=["1.00"],
    )
    fecha_asignacion: datetime | None = Field(
        None,
        description="Fecha de asignación del recurso",
    )
    fecha_liberacion: datetime | None = Field(
        None,
        description="Fecha de liberación del recurso",
    )


class ProyectoRecursoUpdate(BaseModel):
    """Esquema para actualizar un recurso de proyecto"""
    tipo_recurso: str | None = Field(
        None,
        description="Tipo de recurso",
    )
    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre del recurso",
    )
    descripcion: str | None = Field(
        None,
        description="Descripción del recurso",
    )
    employee_id: str | None = Field(
        None,
        description="ID del empleado",
    )
    costo_unitario: Decimal | None = Field(
        None,
        ge=0,
        description="Costo unitario",
    )
    cantidad: Decimal | None = Field(
        None,
        ge=0,
        description="Cantidad",
    )
    fecha_asignacion: datetime | None = Field(
        None,
        description="Fecha de asignación",
    )
    fecha_liberacion: datetime | None = Field(
        None,
        description="Fecha de liberación",
    )


# ==========================================
# ProyectoTimesheet schemas (Create / Update)
# ==========================================

class ProyectoTimesheetCreate(BaseModel):
    """Esquema para crear un registro de timesheet"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    tarea_id: str | None = Field(
        None,
        description="ID de la tarea asociada",
    )
    employee_id: str | None = Field(
        None,
        description="ID del empleado",
    )
    empleado_nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre del empleado",
        examples=["Juan Pérez"],
    )
    fecha: datetime = Field(
        ...,
        description="Fecha del trabajo realizado",
    )
    horas: Decimal = Field(
        ...,
        gt=0,
        description="Horas trabajadas",
        examples=["8.00"],
    )
    tarifa_hora: Decimal | None = Field(
        None,
        ge=0,
        description="Tarifa por hora del empleado",
        examples=["25.00"],
    )
    descripcion: str | None = Field(
        None,
        description="Descripción del trabajo realizado",
    )
    es_facturable: bool | None = Field(
        None,
        description="Si las horas son facturables (default: true)",
    )


class ProyectoTimesheetUpdate(BaseModel):
    """Esquema para actualizar un registro de timesheet"""
    tarea_id: str | None = Field(
        None,
        description="ID de la tarea asociada",
    )
    employee_id: str | None = Field(
        None,
        description="ID del empleado",
    )
    empleado_nombre: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre del empleado",
    )
    fecha: datetime | None = Field(
        None,
        description="Fecha del trabajo",
    )
    horas: Decimal | None = Field(
        None,
        gt=0,
        description="Horas trabajadas",
    )
    tarifa_hora: Decimal | None = Field(
        None,
        ge=0,
        description="Tarifa por hora",
    )
    descripcion: str | None = Field(
        None,
        description="Descripción del trabajo",
    )
    es_facturable: bool | None = Field(
        None,
        description="Si las horas son facturables",
    )


# ==========================================
# ProyectoCosto schemas (Create / Update)
# ==========================================

class ProyectoCostoCreate(BaseModel):
    """Esquema para crear un costo de proyecto"""
    concepto: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Concepto del costo",
        examples=["Licencia de software"],
    )
    descripcion: str | None = Field(
        None,
        description="Descripción detallada del costo",
    )
    monto: Decimal = Field(
        ...,
        gt=0,
        description="Monto del costo",
        examples=["1500.00"],
    )
    fecha: datetime = Field(
        ...,
        description="Fecha del costo",
    )
    categoria: str | None = Field(
        None,
        max_length=100,
        description="Categoría del costo (ej: materiales, servicios, operativos)",
    )
    es_facturable: bool | None = Field(
        None,
        description="Si el costo es facturable al cliente (default: false)",
    )
    comprobante_id: str | None = Field(
        None,
        description="ID del comprobante vinculado al costo",
    )


class ProyectoCostoUpdate(BaseModel):
    """Esquema para actualizar un costo de proyecto"""
    concepto: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Concepto del costo",
    )
    descripcion: str | None = Field(
        None,
        description="Descripción del costo",
    )
    monto: Decimal | None = Field(
        None,
        gt=0,
        description="Monto del costo",
    )
    fecha: datetime | None = Field(
        None,
        description="Fecha del costo",
    )
    categoria: str | None = Field(
        None,
        max_length=100,
        description="Categoría del costo",
    )
    es_facturable: bool | None = Field(
        None,
        description="Si el costo es facturable",
    )
    comprobante_id: str | None = Field(
        None,
        description="ID del comprobante vinculado",
    )


# ==========================================
# Proyecto Stats schema
# ==========================================

class ProyectoStats(BaseModel):
    """Estadísticas generales de proyectos"""
    total_proyectos: int = Field(..., description="Total de proyectos")
    en_planificacion: int = Field(..., description="Proyectos en planificación")
    en_progreso: int = Field(..., description="Proyectos en progreso")
    completados: int = Field(..., description="Proyectos completados")
    cancelados: int = Field(..., description="Proyectos cancelados")
    total_presupuesto: Decimal = Field(..., description="Total presupuestado")
    total_costo_real: Decimal = Field(..., description="Total costo real")
    total_ingreso: Decimal = Field(..., description="Total ingreso")
    margen_total: Decimal = Field(..., description="Margen total")
    horas_totales: Decimal = Field(..., description="Total horas registradas en timesheets")
