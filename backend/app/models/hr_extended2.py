"""
ContaEC - Modelos extendidos de RRHH (Fase 5)
CargaFamiliar: Cargas familiares del empleado
EvaluacionDesempeno: Evaluaciones de desempeño
Asistencia: Registro de asistencia / control biométrico
LiquidacionLaboral: Liquidaciones laborales (finiquito/despido/renuncia)
UtilidadesParticipacion: Participación de utilidades (15% trabajadores)
UtilidadesDetalle: Detalle de utilidades por empleado
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ==========================================
# Enumeraciones
# ==========================================


class ParentescoTipo(str, enum.Enum):
    """Tipos de parentesco para carga familiar"""
    HIJO = "hijo"
    CONYUGE = "conyuge"
    OTRO = "otro"


class EvaluacionEstado(str, enum.Enum):
    """Estados de la evaluación de desempeño"""
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADA = "completada"


class AsistenciaTipo(str, enum.Enum):
    """Tipos de día de asistencia"""
    NORMAL = "normal"
    DESCANSO = "descanso"
    FESTIVO = "festivo"
    VACACION = "vacacion"
    PERMISO = "permiso"
    ENFERMEDAD = "enfermedad"


class LiquidacionTipo(str, enum.Enum):
    """Tipos de liquidación laboral"""
    FINIQUITO = "finiquito"
    LIQUIDACION = "liquidacion"
    DESPIDO = "despido"
    RENUNCIA_VOLUNTARIA = "renuncia_voluntaria"


class LiquidacionEstado(str, enum.Enum):
    """Estados de la liquidación laboral"""
    BORRADOR = "borrador"
    APROBADA = "aprobada"
    PAGADA = "pagada"


class UtilidadesEstado(str, enum.Enum):
    """Estados de la distribución de utilidades"""
    BORRADOR = "borrador"
    APROBADA = "aprobada"
    PAGADA = "pagada"


# ==========================================
# Modelos
# ==========================================


class CargaFamiliar(Base):
    """
    Modelo de Carga Familiar.

    Almacena las cargas familiares del empleado (hijos, cónyuge, otros)
    para efectos de cálculo de impuesto a la renta, décimo cuarto
    y otros beneficios conforme a la legislación ecuatoriana.
    """
    __tablename__ = "cargas_familiares"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del empleado al que pertenece la carga familiar",
    )

    # ==========================================
    # Información de la carga familiar
    # ==========================================
    nombres: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nombres de la carga familiar",
    )
    apellidos: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Apellidos de la carga familiar",
    )
    parentesco: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Parentesco: hijo, conyuge, otro",
    )
    fecha_nacimiento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de nacimiento de la carga familiar",
    )
    identificacion: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Número de identificación de la carga familiar",
    )
    discapacidad: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si la carga familiar tiene discapacidad",
    )
    porcentaje_discapacidad: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Porcentaje de discapacidad (0-100)",
    )
    tipo_discapacidad: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Tipo de discapacidad: auditiva, visual, mental, fisica, etc.",
    )
    es_estudiante: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si la carga familiar es estudiante",
    )

    # ==========================================
    # Auditoría
    # ==========================================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el registro está activo en el sistema",
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
    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee",
        back_populates="cargas_familiares",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<CargaFamiliar(id={self.id}, employee_id={self.employee_id}, "
            f"nombres={self.nombres}, parentesco={self.parentesco})>"
        )


class EvaluacionDesempeno(Base):
    """
    Modelo de Evaluación de Desempeño.

    Permite registrar evaluaciones de desempeño periódicas
    para los empleados, con puntaje, objetivos, fortalezas
    y áreas de mejora. Soporta períodos trimestrales.
    """
    __tablename__ = "evaluaciones_desempeno"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del empleado evaluado",
    )
    evaluador_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID del usuario que realiza la evaluación",
    )

    # ==========================================
    # Información de la evaluación
    # ==========================================
    periodo: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Período de evaluación (ej: 2024-Q1, 2024-Q2)",
    )
    puntaje: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Puntaje de la evaluación (0-100)",
    )
    objetivos: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Objetivos de la evaluación en formato JSON",
    )
    comentarios: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comentarios generales de la evaluación",
    )
    fortalezas: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Fortalezas identificadas del empleado",
    )
    areas_mejora: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Áreas de mejora identificadas",
    )
    plan_accion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Plan de acción para mejorar desempeño",
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=EvaluacionEstado.PENDIENTE,
        nullable=False,
        comment="Estado: pendiente, en_proceso, completada",
    )
    fecha_evaluacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha en que se realizó la evaluación",
    )

    # ==========================================
    # Auditoría
    # ==========================================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el registro está activo en el sistema",
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
    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee",
        back_populates="evaluaciones",
        lazy="selectin",
    )
    evaluador: Mapped["User"] = relationship(  # noqa: F821
        "User",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluacionDesempeno(id={self.id}, employee_id={self.employee_id}, "
            f"periodo={self.periodo}, puntaje={self.puntaje}, estado={self.estado})>"
        )


class Asistencia(Base):
    """
    Modelo de Asistencia.

    Registra la asistencia diaria de los empleados, incluyendo
    hora de entrada/salida, horas trabajadas/extras y tipo de día.
    Compatible con dispositivos biométricos.
    """
    __tablename__ = "asistencias"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del empleado",
    )

    # ==========================================
    # Información de asistencia
    # ==========================================
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Fecha de la asistencia",
    )
    hora_entrada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Hora de entrada registrada",
    )
    hora_salida: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Hora de salida registrada",
    )
    horas_trabajadas: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Horas trabajadas en el día",
    )
    horas_extras: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Horas extras trabajadas",
    )
    tipo: Mapped[str] = mapped_column(
        String(20),
        default=AsistenciaTipo.NORMAL,
        nullable=False,
        comment="Tipo de día: normal, descanso, festivo, vacacion, permiso, enfermedad",
    )
    dispositivo_entrada: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Dispositivo biométrico de entrada",
    )
    dispositivo_salida: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Dispositivo biométrico de salida",
    )
    observacion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones sobre la asistencia",
    )

    # ==========================================
    # Auditoría
    # ==========================================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el registro está activo en el sistema",
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
    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee",
        back_populates="asistencias",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Asistencia(id={self.id}, employee_id={self.employee_id}, "
            f"fecha={self.fecha}, tipo={self.tipo})>"
        )


class LiquidacionLaboral(Base):
    """
    Modelo de Liquidación Laboral.

    Calcula y almacena la liquidación laboral completa de un empleado
    al finalizar su relación laboral, conforme al Código del Trabajo
    ecuatoriano. Incluye sueldo pendiente, décimos, vacaciones,
    fondo de reserva, bono de desahucio e indemnización.
    """
    __tablename__ = "liquidaciones_laborales"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del empleado al que pertenece la liquidación",
    )
    company_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la empresa",
    )

    # ==========================================
    # Información de la liquidación
    # ==========================================
    tipo: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        comment="Tipo: finiquito, liquidacion, despido, renuncia_voluntaria",
    )
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha de inicio de la relación laboral",
    )
    fecha_fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha de fin de la relación laboral",
    )

    # ==========================================
    # Ingresos
    # ==========================================
    sueldo_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Sueldo pendiente por pagar",
    )
    decimo_tercero_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Décimo tercero pendiente acumulado",
    )
    decimo_cuarto_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Décimo cuarto pendiente acumulado",
    )
    vacaciones_pendientes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Vacaciones pendientes monetizadas",
    )
    fondo_reserva_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Fondo de reserva pendiente acumulado",
    )
    bono_desahucio: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Bono de desahucio (1 sueldo por cada año, si aplica)",
    )
    indemnizacion: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Indemnización por despido intempestivo",
    )
    otros_ingresos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Otros ingresos adicionales",
    )
    total_ingresos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total de ingresos de la liquidación",
    )

    # ==========================================
    # Descuentos
    # ==========================================
    iess_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Aporte IESS pendiente",
    )
    anticipos_pendientes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Anticipos de sueldo pendientes de descuento",
    )
    prestamos_pendientes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Préstamos pendientes de descuento",
    )
    otros_descuentos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Otros descuentos aplicables",
    )
    total_descuentos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total de descuentos de la liquidación",
    )

    # ==========================================
    # Total
    # ==========================================
    total_liquidacion: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total neto de la liquidación (ingresos - descuentos)",
    )

    # ==========================================
    # Estado y aprobación
    # ==========================================
    estado: Mapped[str] = mapped_column(
        String(20),
        default=LiquidacionEstado.BORRADOR,
        nullable=False,
        comment="Estado: borrador, aprobada, pagada",
    )
    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones adicionales de la liquidación",
    )
    aprobado_por: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID del usuario que aprobó la liquidación",
    )
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de aprobación de la liquidación",
    )

    # ==========================================
    # Auditoría
    # ==========================================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el registro está activo en el sistema",
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
    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee",
        back_populates="liquidaciones",
        lazy="selectin",
    )
    company: Mapped["Company"] = relationship(  # noqa: F821
        "Company",
        lazy="selectin",
    )
    aprobador: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[aprobado_por],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<LiquidacionLaboral(id={self.id}, employee_id={self.employee_id}, "
            f"tipo={self.tipo}, estado={self.estado})>"
        )


class UtilidadesParticipacion(Base):
    """
    Modelo de Participación de Utilidades.

    Registra la distribución del 15% de las utilidades de la empresa
    a los trabajadores, conforme al Art. 97 de la Ley de Compañías
    y el Código del Trabajo ecuatoriano. 10% se distribuye por igual
    y 5% en proporción a las cargas familiares.
    """
    __tablename__ = "utilidades_participacion"

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
        comment="ID de la empresa",
    )

    # ==========================================
    # Información de utilidades
    # ==========================================
    anio: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Año fiscal de las utilidades",
    )
    total_utilidades: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total de utilidades de la empresa en el año",
    )
    porcentaje_trabajadores: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("15.00"),
        nullable=False,
        comment="Porcentaje de utilidades para trabajadores (15% por defecto)",
    )
    numero_trabajadores: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de trabajadores que participan",
    )
    monto_distribuir: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Monto total a distribuir entre trabajadores",
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=UtilidadesEstado.BORRADOR,
        nullable=False,
        comment="Estado: borrador, aprobada, pagada",
    )

    # ==========================================
    # Auditoría
    # ==========================================
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
        lazy="selectin",
    )
    detalles: Mapped[list["UtilidadesDetalle"]] = relationship(  # noqa: F821
        "UtilidadesDetalle",
        back_populates="utilidad",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<UtilidadesParticipacion(id={self.id}, company_id={self.company_id}, "
            f"anio={self.anio}, estado={self.estado})>"
        )


class UtilidadesDetalle(Base):
    """
    Modelo de Detalle de Utilidades por Empleado.

    Desglosa la participación individual de cada empleado en la
    distribución de utilidades, basado en días trabajados y
    sueldo acumulado.
    """
    __tablename__ = "utilidades_detalle"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    utilidad_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("utilidades_participacion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la participación de utilidades",
    )
    employee_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del empleado",
    )

    # ==========================================
    # Información del detalle
    # ==========================================
    dias_trabajados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Días trabajados en el año",
    )
    sueldo_acumulado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Sueldo acumulado en el año",
    )
    porcentaje_participacion: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        default=Decimal("0.00"),
        nullable=False,
        comment="Porcentaje de participación del empleado",
    )
    monto_asignado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Monto de utilidades asignado al empleado",
    )

    # ==========================================
    # Auditoría
    # ==========================================
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
    utilidad: Mapped["UtilidadesParticipacion"] = relationship(  # noqa: F821
        "UtilidadesParticipacion",
        back_populates="detalles",
        lazy="selectin",
    )
    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<UtilidadesDetalle(id={self.id}, utilidad_id={self.utilidad_id}, "
            f"employee_id={self.employee_id}, monto_asignado={self.monto_asignado})>"
        )
