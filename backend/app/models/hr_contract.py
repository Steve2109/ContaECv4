"""
ContaEC - Modelo de Contrato Laboral
Contrato: Historial de contratos laborales por empleado
Conforme al Código del Trabajo ecuatoriano
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ContratoTipo(str, enum.Enum):
    """Tipos de contrato laboral según Código del Trabajo Ecuador"""
    INDEFINIDO = "indefinido"
    FIJO = "fijo"
    TEMPORAL = "temporal"
    OCASIONAL = "ocasional"
    POR_OBRA = "por_obra"
    PASANTIA = "pasantia"
    APRENDIZAJE = "aprendizaje"


class ContratoEstado(str, enum.Enum):
    """Estados del contrato laboral"""
    VIGENTE = "vigente"
    SUSPENDIDO = "suspendido"
    TERMINADO = "terminado"
    ANULADO = "anulado"


class ContratoLaboral(Base):
    """
    Modelo de Contrato Laboral.

    Almacena el historial completo de contratos laborales por empleado,
    permitiendo seguimiento de cambios de cargo, salario, y tipo de
    contrato conforme al Código del Trabajo ecuatoriano.

    Un empleado puede tener múltiples contratos en el tiempo, pero solo
    uno vigente a la vez.
    """
    __tablename__ = "contratos_laborales"

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
        comment="ID del empleado al que pertenece el contrato",
    )
    company_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la empresa",
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="ID del usuario que creó el contrato",
    )

    # ==========================================
    # Información del contrato
    # ==========================================
    tipo_contrato: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Tipo de contrato: indefinido, fijo, temporal, ocasional, por_obra, pasantia, aprendizaje",
    )
    cargo: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Cargo o puesto del empleado",
    )
    departamento: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Departamento o área",
    )
    jornada_horas_semanal: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("40.00"),
        nullable=False,
        comment="Horas de trabajo semanal",
    )
    es_jornada_parcial: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Si es True, jornada es menor a 35 horas semanales",
    )

    # ==========================================
    # Información salarial
    # ==========================================
    sueldo_base: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Sueldo base mensual del contrato",
    )
    complemento_salario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Complemento salarial (bonos fijos, etc.)",
    )
    forma_pago: Mapped[str] = mapped_column(
        String(20),
        default="mensual",
        nullable=False,
        comment="Forma de pago: mensual, quincenal, semanal",
    )

    # ==========================================
    # Vigencia del contrato
    # ==========================================
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha de inicio de vigencia del contrato",
    )
    fecha_fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de fin (para contratos temporales)",
    )
    fecha_prueba: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha fin período de prueba (máx 3 meses)",
    )

    # ==========================================
    # Lugar de trabajo
    # ==========================================
    lugar_trabajo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Lugar donde presta servicios (dirección)",
    )
    es_remoto: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Si es True, el trabajo es remoto/teletrabajo",
    )

    # ==========================================
    # Terminación del contrato
    # ==========================================
    causa_terminacion: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Causa de terminación: renuncia, despido, fin contrato, jubilación, etc.",
    )
    fecha_terminacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha efectiva de terminación",
    )
    tiene_liquidacion: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Si se generó liquidación al terminar",
    )

    # ==========================================
    # Estado y auditoría
    # ==========================================
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ContratoEstado.VIGENTE,
        nullable=False,
        index=True,
        comment="Estado: vigente, suspendido, terminado, anulado",
    )
    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones adicionales del contrato",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ==========================================
    # Relaciones
    # ==========================================
    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="contratos_laborales",
        lazy="selectin",
    )
    company: Mapped["Company"] = relationship(
        "Company",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Contrato(id={self.id}, employee_id={self.employee_id}, "
            f"tipo={self.tipo_contrato}, estado={self.estado})>"
        )

    @property
    def esta_vigente(self) -> bool:
        """Verifica si el contrato está vigente"""
        if self.estado != ContratoEstado.VIGENTE:
            return False
        now = datetime.now(timezone.utc)
        if self.fecha_fin and now > self.fecha_fin:
            return False
        return True

    @property
    def en_periodo_prueba(self) -> bool:
        """Verifica si está en período de prueba (máx 3 meses)"""
        if not self.fecha_prueba:
            return False
        return datetime.now(timezone.utc) <= self.fecha_prueba

    @property
    def anios_servicio(self) -> int:
        """Calcula años de servicio desde el primer contrato vigente"""
        if not self.fecha_inicio:
            return 0
        now = datetime.now(timezone.utc)
        fecha_ref = self.fecha_terminacion or now
        return (fecha_ref - self.fecha_inicio).days // 365