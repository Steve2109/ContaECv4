"""
ContaEC - Modelo de Empleado
Employee: Información del empleado para nómina y RRHH
Incluye datos personales, laborales, salariales y beneficios sociales
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoContrato(str, enum.Enum):
    """Tipos de contrato laboral según Código del Trabajo Ecuador"""
    INDEFINIDO = "indefinido"
    FIJO = "fijo"
    POR_OBRA = "por_obra"
    TEMPORAL = "temporal"
    PASANTIA = "pasantia"


class TipoPago(str, enum.Enum):
    """Tipos de pago de remuneración"""
    MENSUAL = "mensual"
    QUINCENAL = "quincenal"
    SEMANAL = "semanal"


class EstadoEmpleado(str, enum.Enum):
    """Estados del empleado"""
    ACTIVO = "activo"
    VACACIONES = "vacaciones"
    LICENCIA = "licencia"
    SUSPENDIDO = "suspendido"
    CESE = "cese"


class Employee(Base):
    """
    Modelo de Empleado para nómina y recursos humanos.

    Almacena la información personal, laboral, salarial y de beneficios
    sociales de los empleados de una empresa, conforme a la legislación
    laboral ecuatoriana (Código del Trabajo, Ley de Seguridad Social).
    """
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    company_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la empresa a la que pertenece el empleado",
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del usuario que creó el registro",
    )

    # ==========================================
    # Información personal
    # ==========================================
    cedula: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
        comment="Número de cédula de identidad (10 dígitos)",
    )
    apellidos: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Apellidos del empleado",
    )
    nombres: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nombres del empleado",
    )
    fecha_nacimiento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de nacimiento del empleado",
    )
    genero: Mapped[str | None] = mapped_column(
        String(1),
        nullable=True,
        comment="Género del empleado: M=Masculino, F=Femenino",
    )
    estado_civil: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Estado civil del empleado",
    )
    direccion: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Dirección de domicilio del empleado",
    )
    telefono: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Número de teléfono del empleado",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Correo electrónico del empleado",
    )

    # ==========================================
    # Información laboral
    # ==========================================
    cargo: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Cargo o puesto del empleado",
    )
    departamento: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Departamento o área del empleado",
    )
    tipo_contrato: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Tipo de contrato: indefinido, fijo, por_obra, temporal, pasantia",
    )
    fecha_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha de ingreso del empleado a la empresa",
    )
    fecha_salida: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de salida/cese del empleado",
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=EstadoEmpleado.ACTIVO,
        nullable=False,
        comment="Estado del empleado: activo, vacaciones, licencia, suspendido, cese",
    )

    # ==========================================
    # Información salarial
    # ==========================================
    tipo_pago: Mapped[str] = mapped_column(
        String(20),
        default=TipoPago.MENSUAL,
        nullable=False,
        comment="Tipo de pago: mensual, quincenal, semanal",
    )
    sueldo_mensual: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Sueldo mensual del empleado",
    )
    sueldo_diario: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Sueldo diario calculado (sueldo_mensual / 30)",
    )
    horas_trabajo_semanal: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("40.00"),
        nullable=False,
        comment="Horas de trabajo semanal (por defecto 40)",
    )

    # ==========================================
    # Beneficios sociales
    # ==========================================
    fondo_reserva: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el empleado tiene derecho a fondo de reserva",
    )
    decimo_tercero_acumulado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Décimo tercero acumulado",
    )
    decimo_cuarto_acumulado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Décimo cuarto acumulado",
    )
    vacaciones_acumuladas_dias: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Días de vacaciones acumulados",
    )
    fondos_reserva_acumulado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Fondos de reserva acumulados",
    )

    # ==========================================
    # IESS - Instituto Ecuatoriano de Seguridad Social
    # ==========================================
    iess_afiliado: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el empleado está afiliado al IESS",
    )
    iess_numero_seguro: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Número de seguro social IESS",
    )

    # ==========================================
    # Información bancaria
    # ==========================================
    banco: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Nombre del banco del empleado",
    )
    tipo_cuenta: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Tipo de cuenta bancaria: ahorro/corriente",
    )
    numero_cuenta: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="Número de cuenta bancaria",
    )

    # ==========================================
    # Estado y auditoría
    # ==========================================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el empleado está activo en el sistema",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Fecha de creación del registro",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Fecha de última actualización",
    )

    # ==========================================
    # Relaciones
    # ==========================================
    company: Mapped["Company"] = relationship(  # noqa: F821
        "Company",
        back_populates="employees",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        lazy="selectin",
    )
    rol_detalles: Mapped[list["RolPagoDetalle"]] = relationship(  # noqa: F821
        "RolPagoDetalle",
        back_populates="employee",
        lazy="selectin",
    )
    contratos: Mapped[list["Contrato"]] = relationship(  # noqa: F821
        "Contrato",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    decimos_pagos: Mapped[list["DecimoPago"]] = relationship(  # noqa: F821
        "DecimoPago",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    anticipos: Mapped[list["Anticipo"]] = relationship(  # noqa: F821
        "Anticipo",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    rubros: Mapped[list["RubroEmpleado"]] = relationship(  # noqa: F821
        "RubroEmpleado",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    cargas_familiares: Mapped[list["CargaFamiliar"]] = relationship(  # noqa: F821
        "CargaFamiliar",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evaluaciones: Mapped[list["EvaluacionDesempeno"]] = relationship(  # noqa: F821
        "EvaluacionDesempeno",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    asistencias: Mapped[list["Asistencia"]] = relationship(  # noqa: F821
        "Asistencia",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    liquidaciones: Mapped[list["LiquidacionLaboral"]] = relationship(  # noqa: F821
        "LiquidacionLaboral",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Relaciones de nuevos modelos HR (Fase 1)
    contratos_laborales: Mapped[list["ContratoLaboral"]] = relationship(  # noqa: F821
        "ContratoLaboral",
        foreign_keys="ContratoLaboral.employee_id",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    vacaciones_periodos: Mapped[list["VacacionesPeriodo"]] = relationship(  # noqa: F821
        "VacacionesPeriodo",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    vacaciones_solicitudes: Mapped[list["VacacionesSolicitud"]] = relationship(  # noqa: F821
        "VacacionesSolicitud",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    prestamos: Mapped[list["PrestamoEmpleado"]] = relationship(  # noqa: F821
        "PrestamoEmpleado",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    historial_laboral: Mapped[list["HistorialLaboral"]] = relationship(  # noqa: F821
        "HistorialLaboral",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    turnos_asignaciones: Mapped[list["TurnoAsignacion"]] = relationship(  # noqa: F821
        "TurnoAsignacion",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Employee(id={self.id}, cedula={self.cedula}, "
            f"apellidos={self.apellidos}, nombres={self.nombres})>"
        )

    @property
    def nombre_completo(self) -> str:
        """Nombre completo del empleado"""
        return f"{self.apellidos} {self.nombres}"

    @property
    def calcular_sueldo_diario(self) -> Decimal:
        """Calcula el sueldo diario dividiendo el mensual entre 30"""
        if self.sueldo_mensual:
            return (self.sueldo_mensual / Decimal("30.00")).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def anios_servicio(self) -> int:
        """Calcula los años de servicio del empleado"""
        if not self.fecha_ingreso:
            return 0
        fecha_ref = self.fecha_salida if self.fecha_salida else datetime.now(timezone.utc)
        delta = fecha_ref - self.fecha_ingreso
        return delta.days // 365
