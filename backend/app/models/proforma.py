"""
ContaEC - Modelos de Proforma
Proforma: Cotización/Presupuesto que puede convertirse en Factura
ProformaDetalle: Detalle de líneas de la proforma
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProformaEstado(str, enum.Enum):
    """Estado de la proforma en su ciclo de vida"""
    BORRADOR = "borrador"      # Borrador - aún no finalizada
    CERRADA = "cerrada"        # Proforma realizada/cerrada (creada desde el wizard)
    ENVIADA = "enviada"        # Enviada al cliente, pendiente respuesta
    ACEPTADA = "aceptada"      # Aceptada por el cliente
    RECHAZADA = "rechazada"    # Rechazada por el cliente
    CONVERTIDA = "convertida"  # Convertida a Factura electrónica


class Proforma(Base):
    """
    Modelo de Proforma / Cotización.

    Similar a un comprobante pero sin valor fiscal ante el SRI.
    Puede ser enviada al cliente como cotización y convertida
    en una Factura electrónica cuando el cliente la acepte.
    """
    __tablename__ = "proformas"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # Llaves foráneas
    company_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la empresa emisora de la proforma",
    )
    client_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID del cliente (opcional, puede ser Consumidor Final)",
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="ID del usuario que creó la proforma",
    )

    # === Identificación ===
    secuencial: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        comment="Número secuencial de la proforma (PRO-XXXXXX)",
    )
    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha y hora de emisión de la proforma",
    )
    fecha_validez: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de validez de la proforma",
    )

    # === Estado ===
    estado: Mapped[str] = mapped_column(
        String(20),
        default=ProformaEstado.BORRADOR,
        nullable=False,
        index=True,
        comment="Estado actual de la proforma",
    )

    # === Información del Cliente (desnormalizada) ===
    cliente_tipo_identificacion: Mapped[str] = mapped_column(
        String(2),
        default="07",
        nullable=False,
        comment="Tipo de identificación del cliente",
    )
    cliente_identificacion: Mapped[str] = mapped_column(
        String(20),
        default="9999999999999",
        nullable=False,
        comment="Número de identificación del cliente",
    )
    cliente_razon_social: Mapped[str] = mapped_column(
        String(255),
        default="CONSUMIDOR FINAL",
        nullable=False,
        comment="Razón social o nombre del cliente",
    )
    cliente_direccion: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Dirección del cliente",
    )
    cliente_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Correo electrónico del cliente",
    )
    cliente_telefono: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Número de teléfono del cliente",
    )

    # === Totales ===
    subtotal_sin_impuestos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_0: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_5: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_8: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_12: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_13: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_14: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_15: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_no_objeto_iva: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_exento_iva: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    subtotal_iva_diferenciado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Subtotal con IVA diferenciado (código 9 - Tabla 16 SRI)",
    )
    total_iva: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    total_ice: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    total_descuento: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    total_con_impuestos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    # === Campos adicionales ===
    forma_pago: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        comment="Código de forma de pago",
    )
    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones o notas de la proforma",
    )
    info_adicional: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Información adicional en formato JSON",
    )

    # === Referencia a comprobante convertido ===
    comprobante_convertido_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("comprobantes.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID del comprobante creado al convertir esta proforma",
    )

    # Estado
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relaciones
    company: Mapped["Company"] = relationship(  # noqa: F821
        "Company",
        back_populates="proformas",
        lazy="selectin",
    )
    client: Mapped["Client | None"] = relationship(  # noqa: F821
        "Client",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="proformas",
        lazy="selectin",
    )
    detalles: Mapped[list["ProformaDetalle"]] = relationship(
        "ProformaDetalle",
        back_populates="proforma",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Proforma(id={self.id}, secuencial={self.secuencial}, "
            f"estado={self.estado})>"
        )


class ProformaDetalle(Base):
    """
    Modelo de Detalle de Proforma.

    Cada línea de la proforma representa un bien o servicio con su
    cantidad, precio, descuentos e impuestos aplicables.
    """
    __tablename__ = "proforma_detalles"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    proforma_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("proformas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )

    # === Detalle del bien/servicio ===
    codigo_principal: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_auxiliar: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unidad_medida: Mapped[str] = mapped_column(String(50), default="Unidad", nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    descuento: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    precio_total_sin_impuestos: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # === Impuestos ===
    iva_codigo: Mapped[str] = mapped_column(String(2), nullable=False)
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    iva_valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    ice_codigo: Mapped[str | None] = mapped_column(String(3), nullable=True)
    ice_porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    ice_valor: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True, default=Decimal("0"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relaciones
    proforma: Mapped["Proforma"] = relationship(
        "Proforma",
        back_populates="detalles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ProformaDetalle(id={self.id}, descripcion={self.descripcion}, "
            f"cantidad={self.cantidad})>"
        )
