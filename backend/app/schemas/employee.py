"""
ContaEC - Esquemas Pydantic de Empleado
Schemas para creación, actualización, cese y respuesta de empleados
"""
from uuid import UUID
import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.hr_constants import (
    ESTADOS_EMPLEADO,
    GENEROS,
    TIPOS_CONTRATO,
    TIPOS_CUENTA,
    TIPOS_PAGO,
)


class EmployeeCreate(BaseModel):
    """Esquema para crear un nuevo empleado"""
    company_id: str = Field(
        ...,
        description="ID de la empresa a la que pertenece el empleado",
    )
    # Información personal
    cedula: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Número de cédula de identidad (10 dígitos)",
        examples=["1712345678"],
    )
    apellidos: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Apellidos del empleado",
        examples=["PÉREZ GONZÁLEZ"],
    )
    nombres: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombres del empleado",
        examples=["JUAN CARLOS"],
    )
    fecha_nacimiento: datetime | None = Field(
        None,
        description="Fecha de nacimiento del empleado",
    )
    genero: str | None = Field(
        None,
        max_length=1,
        description="Género: M=Masculino, F=Femenino",
    )
    estado_civil: str | None = Field(
        None,
        max_length=20,
        description="Estado civil del empleado",
    )
    direccion: str | None = Field(
        None,
        max_length=500,
        description="Dirección de domicilio",
    )
    telefono: str | None = Field(
        None,
        max_length=20,
        description="Número de teléfono",
    )
    email: EmailStr | None = Field(
        None,
        max_length=255,
        description="Correo electrónico del empleado",
    )
    # Información laboral
    cargo: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Cargo o puesto del empleado",
        examples=["Contador"],
    )
    departamento: str | None = Field(
        None,
        max_length=200,
        description="Departamento o área",
        examples=["Contabilidad"],
    )
    tipo_contrato: str = Field(
        ...,
        description="Tipo de contrato: indefinido, fijo, por_obra, temporal, pasantia",
        examples=["indefinido"],
    )
    fecha_ingreso: datetime = Field(
        ...,
        description="Fecha de ingreso a la empresa",
    )
    tipo_pago: str = Field(
        default="mensual",
        description="Tipo de pago: mensual, quincenal, semanal",
    )
    sueldo_mensual: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Sueldo mensual del empleado",
        examples=["460.00"],
    )
    horas_trabajo_semanal: Decimal = Field(
        default=Decimal("40.00"),
        decimal_places=2,
        description="Horas de trabajo semanal",
    )
    # Beneficios
    fondo_reserva: bool = Field(
        default=False,
        description="Indica si el empleado tiene fondo de reserva",
    )
    # IESS
    iess_afiliado: bool = Field(
        default=True,
        description="Indica si el empleado está afiliado al IESS",
    )
    iess_numero_seguro: str | None = Field(
        None,
        max_length=20,
        description="Número de seguro social IESS",
    )
    # Información bancaria
    banco: str | None = Field(
        None,
        max_length=100,
        description="Nombre del banco",
    )
    tipo_cuenta: str | None = Field(
        None,
        max_length=20,
        description="Tipo de cuenta: ahorro/corriente",
    )
    numero_cuenta: str | None = Field(
        None,
        max_length=30,
        description="Número de cuenta bancaria",
    )

    @field_validator("cedula")
    @classmethod
    def validate_cedula(cls, v: str) -> str:
        """Valida el formato de la cédula ecuatoriana (10 dígitos)"""
        if not re.match(r"^\d{10}$", v):
            raise ValueError("La cédula debe tener exactamente 10 dígitos numéricos")
        # Validación básica del dígito verificador
        provincia = int(v[:2])
        if provincia < 1 or provincia > 24:
            raise ValueError("Código de provincia de la cédula inválido (01-24)")
        return v

    @field_validator("tipo_contrato")
    @classmethod
    def validate_tipo_contrato(cls, v: str) -> str:
        """Valida que el tipo de contrato sea válido"""
        if v not in TIPOS_CONTRATO:
            raise ValueError(
                f"Tipo de contrato inválido: {v}. "
                f"Válidos: {', '.join(TIPOS_CONTRATO)}"
            )
        return v

    @field_validator("tipo_pago")
    @classmethod
    def validate_tipo_pago(cls, v: str) -> str:
        """Valida que el tipo de pago sea válido"""
        if v not in TIPOS_PAGO:
            raise ValueError(
                f"Tipo de pago inválido: {v}. "
                f"Válidos: {', '.join(TIPOS_PAGO)}"
            )
        return v

    @field_validator("genero")
    @classmethod
    def validate_genero(cls, v: str | None) -> str | None:
        """Valida que el género sea M o F"""
        if v is not None and v not in GENEROS:
            raise ValueError("Género inválido. Válidos: M (Masculino), F (Femenino)")
        return v

    @field_validator("tipo_cuenta")
    @classmethod
    def validate_tipo_cuenta(cls, v: str | None) -> str | None:
        """Valida que el tipo de cuenta sea válido"""
        if v is not None and v not in TIPOS_CUENTA:
            raise ValueError(
                f"Tipo de cuenta inválido: {v}. Válidos: {', '.join(TIPOS_CUENTA)}"
            )
        return v


class EmployeeUpdate(BaseModel):
    """Esquema para actualizar datos de un empleado"""
    apellidos: str | None = Field(None, min_length=1, max_length=200)
    nombres: str | None = Field(None, min_length=1, max_length=200)
    fecha_nacimiento: datetime | None = None
    genero: str | None = Field(None, max_length=1)
    estado_civil: str | None = Field(None, max_length=20)
    direccion: str | None = Field(None, max_length=500)
    telefono: str | None = Field(None, max_length=20)
    email: EmailStr | None = Field(None, max_length=255)
    cargo: str | None = Field(None, min_length=1, max_length=200)
    departamento: str | None = Field(None, max_length=200)
    tipo_contrato: str | None = None
    tipo_pago: str | None = None
    sueldo_mensual: Decimal | None = Field(None, gt=0, decimal_places=2)
    horas_trabajo_semanal: Decimal | None = Field(None, decimal_places=2)
    fondo_reserva: bool | None = None
    iess_afiliado: bool | None = None
    iess_numero_seguro: str | None = Field(None, max_length=20)
    banco: str | None = Field(None, max_length=100)
    tipo_cuenta: str | None = Field(None, max_length=20)
    numero_cuenta: str | None = Field(None, max_length=30)
    is_active: bool | None = None

    @field_validator("tipo_contrato")
    @classmethod
    def validate_tipo_contrato(cls, v: str | None) -> str | None:
        if v is not None and v not in TIPOS_CONTRATO:
            raise ValueError(f"Tipo de contrato inválido. Válidos: {', '.join(TIPOS_CONTRATO)}")
        return v

    @field_validator("tipo_pago")
    @classmethod
    def validate_tipo_pago(cls, v: str | None) -> str | None:
        if v is not None and v not in TIPOS_PAGO:
            raise ValueError(f"Tipo de pago inválido. Válidos: {', '.join(TIPOS_PAGO)}")
        return v

    @field_validator("genero")
    @classmethod
    def validate_genero(cls, v: str | None) -> str | None:
        if v is not None and v not in GENEROS:
            raise ValueError("Género inválido. Válidos: M, F")
        return v

    @field_validator("tipo_cuenta")
    @classmethod
    def validate_tipo_cuenta(cls, v: str | None) -> str | None:
        if v is not None and v not in TIPOS_CUENTA:
            raise ValueError(f"Tipo de cuenta inválido. Válidos: {', '.join(TIPOS_CUENTA)}")
        return v


class EmployeeCese(BaseModel):
    """Esquema para registrar el cese de un empleado"""
    fecha_salida: datetime = Field(
        ...,
        description="Fecha de salida/cese del empleado",
    )
    motivo: str | None = Field(
        None,
        max_length=500,
        description="Motivo del cese",
    )


class EmployeeResponse(BaseModel):
    """Esquema de respuesta para un empleado"""
    id: UUID = Field(..., description="ID único del empleado")
    company_id: UUID = Field(..., description="ID de la empresa")
    user_id: UUID = Field(..., description="ID del usuario que creó el registro")
    # Personal
    cedula: str = Field(..., description="Número de cédula")
    apellidos: str = Field(..., description="Apellidos")
    nombres: str = Field(..., description="Nombres")
    fecha_nacimiento: datetime | None = Field(None, description="Fecha de nacimiento")
    genero: str | None = Field(None, description="Género")
    estado_civil: str | None = Field(None, description="Estado civil")
    direccion: str | None = Field(None, description="Dirección")
    telefono: str | None = Field(None, description="Teléfono")
    email: EmailStr | None = Field(None, description="Correo electrónico")
    # Laboral
    cargo: str = Field(..., description="Cargo")
    departamento: str | None = Field(None, description="Departamento")
    tipo_contrato: str = Field(..., description="Tipo de contrato")
    fecha_ingreso: datetime = Field(..., description="Fecha de ingreso")
    fecha_salida: datetime | None = Field(None, description="Fecha de salida")
    estado: str = Field(..., description="Estado del empleado")
    # Salarial
    tipo_pago: str = Field(..., description="Tipo de pago")
    sueldo_mensual: Decimal = Field(..., description="Sueldo mensual")
    sueldo_diario: Decimal | None = Field(None, description="Sueldo diario")
    horas_trabajo_semanal: Decimal = Field(..., description="Horas semanales")
    # Beneficios
    fondo_reserva: bool = Field(..., description="Tiene fondo de reserva")
    decimo_tercero_acumulado: Decimal = Field(..., description="Décimo tercero acumulado")
    decimo_cuarto_acumulado: Decimal = Field(..., description="Décimo cuarto acumulado")
    vacaciones_acumuladas_dias: Decimal = Field(..., description="Días vacaciones acumulados")
    fondos_reserva_acumulado: Decimal = Field(..., description="Fondos de reserva acumulados")
    # IESS
    iess_afiliado: bool = Field(..., description="Afiliado al IESS")
    iess_numero_seguro: str | None = Field(None, description="Número seguro IESS")
    # Bancaria
    banco: str | None = Field(None, description="Banco")
    tipo_cuenta: str | None = Field(None, description="Tipo de cuenta")
    numero_cuenta: str | None = Field(None, description="Número de cuenta")
    # Estado
    is_active: bool = Field(..., description="Activo en el sistema")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DepartmentResponse(BaseModel):
    """Esquema de respuesta para un departamento"""
    nombre: str = Field(..., description="Nombre del departamento")
    total_empleados: int = Field(..., description="Total de empleados en el departamento")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
