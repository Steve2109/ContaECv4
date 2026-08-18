"""
ContaEC - Modelos de Punto de Venta (POS)
POSCashSession: Sesión de caja (apertura/cierre)
POSTicket: Ticket de venta POS
POSTicketDetalle: Detalle de líneas del ticket
POSArqueo: Arqueo de caja (parcial/final)
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CajaEstado(str, enum.Enum):
    """
    Estado de una sesión de caja.
    abierta: Caja abierta y operando
    cerrada: Caja cerrada con arqueo final
    """
    ABIERTA = "abierta"
    CERRADA = "cerrada"


class TicketEstado(str, enum.Enum):
    """
    Estado de un ticket POS.
    pendiente: Ticket creado pero no pagado
    pagado: Ticket pagado
    anulado: Ticket anulado
    devuelto: Ticket con devolución
    """
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    ANULADO = "anulado"
    DEVUELTO = "devuelto"


class TipoVenta(str, enum.Enum):
    """
    Tipo de venta en POS.
    efectivo: Pago en efectivo
    tarjeta: Pago con tarjeta
    credito: Venta a crédito
    mixto: Combinación de formas de pago
    otro: Otra forma de pago
    """
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    CREDITO = "credito"
    MIXTO = "mixto"
    OTRO = "otro"


class ArqueoTipo(str, enum.Enum):
    """
    Tipo de arqueo de caja.
    parcial: Arqueo parcial durante el turno
    final: Arqueo final al cerrar la caja
    """
    PARCIAL = "parcial"
    FINAL = "final"


class POSCashSession(Base):
    """
    Modelo de Sesión de Caja POS.

    Registra la apertura y cierre de una caja con control de
    montos iniciales, ventas y arqueo final.
    """
    __tablename__ = "pos_cash_sessions"

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
    warehouse_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID del almacén desde el que vende el POS",
    )
    numero_caja: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número de caja (ej: CAJA-001)",
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="ID del cajero",
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=CajaEstado.ABIERTA.value,
        nullable=False,
        index=True,
        comment="Estado: abierta, cerrada",
    )
    fecha_apertura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fecha y hora de apertura de la caja",
    )
    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora de cierre de la caja",
    )
    monto_apertura: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Monto inicial de efectivo al abrir la caja",
    )
    monto_cierre_efectivo: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Efectivo contado al cerrar la caja",
    )
    monto_cierre_calculado: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Efectivo calculado por el sistema",
    )
    monto_diferencia: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        comment="Diferencia entre contado y calculado (sobrante/faltante)",
    )
    # Totales de ventas por forma de pago
    total_ventas_efectivo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de ventas en efectivo",
    )
    total_ventas_tarjeta: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de ventas con tarjeta",
    )
    total_ventas_credito: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de ventas a crédito",
    )
    total_ventas_otro: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de ventas con otra forma de pago",
    )
    total_ventas: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total general de ventas",
    )
    total_propina: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de propinas",
    )
    total_descuentos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de descuentos aplicados",
    )
    total_devoluciones: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de devoluciones",
    )
    observaciones_cierre: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones al cerrar la caja",
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

    # Relaciones
    tickets: Mapped[list["POSTicket"]] = relationship(
        "POSTicket",
        back_populates="cash_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    arqueos: Mapped[list["POSArqueo"]] = relationship(
        "POSArqueo",
        back_populates="cash_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    company: Mapped["Company"] = relationship(  # noqa: F821
        "Company",
        lazy="selectin",
    )
    warehouse: Mapped["Warehouse | None"] = relationship(  # noqa: F821
        "Warehouse",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<POSCashSession(id={self.id}, numero_caja={self.numero_caja}, "
            f"estado={self.estado})>"
        )


class POSTicket(Base):
    """
    Modelo de Ticket de Venta POS.

    Registra cada venta realizada en el punto de venta con
    detalle de productos, formas de pago e información del cliente.
    """
    __tablename__ = "pos_tickets"

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
    cash_session_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("pos_cash_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la sesión de caja",
    )
    comprobante_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("comprobantes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID del comprobante electrónico asociado (factura)",
    )
    numero_ticket: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número de ticket (ej: TCK-000001), único por empresa",
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        default=TicketEstado.PENDIENTE.value,
        nullable=False,
        index=True,
        comment="Estado: pendiente, pagado, anulado, devuelto",
    )
    tipo_venta: Mapped[str] = mapped_column(
        String(20),
        default=TipoVenta.EFECTIVO.value,
        nullable=False,
        comment="Tipo de venta: efectivo, tarjeta, credito, mixto, otro",
    )
    # Información del cliente
    cliente_nombre: Mapped[str] = mapped_column(
        String(200),
        default="CONSUMIDOR FINAL",
        nullable=False,
        comment="Nombre del cliente",
    )
    cliente_identificacion: Mapped[str] = mapped_column(
        String(20),
        default="9999999999999",
        nullable=False,
        comment="Número de identificación del cliente",
    )
    cliente_tipo_identificacion: Mapped[str] = mapped_column(
        String(2),
        default="07",
        nullable=False,
        comment="Tipo de identificación (07=consumidor final)",
    )
    cliente_direccion: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Dirección del cliente",
    )
    cliente_telefono: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="Teléfono del cliente",
    )
    cliente_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Correo electrónico del cliente",
    )
    # Información del pago con tarjeta
    tarjeta_tipo: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Tipo de tarjeta: debito o credito",
    )
    tarjeta_marca: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="Marca de la tarjeta: visa, mastercard, amex, diners, discover, otra",
    )
    tarjeta_banco: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Banco emisor de la tarjeta",
    )
    tarjeta_titular: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Nombre del titular de la tarjeta",
    )
    # Totales
    subtotal_sin_impuestos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Subtotal sin impuestos",
    )
    total_iva: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total del IVA",
    )
    total_descuento: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total de descuentos",
    )
    total_con_impuestos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total con impuestos",
    )
    # Montos por forma de pago
    monto_efectivo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Monto pagado en efectivo",
    )
    monto_tarjeta: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Monto pagado con tarjeta",
    )
    monto_credito: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Monto a crédito",
    )
    monto_otro: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Monto pagado con otra forma de pago",
    )
    cambio: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Cambio devuelto al cliente",
    )
    propina: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Propina del cliente",
    )
    # Información de tarjeta
    numero_tarjeta: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        comment="Últimos 4 dígitos de la tarjeta",
    )
    referencia_pago: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Referencia del pago (ej: número de autorización)",
    )
    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones adicionales",
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="ID del cajero que creó el ticket",
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

    # Relaciones
    detalles: Mapped[list["POSTicketDetalle"]] = relationship(
        "POSTicketDetalle",
        back_populates="ticket",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    cash_session: Mapped["POSCashSession"] = relationship(
        "POSCashSession",
        back_populates="tickets",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<POSTicket(id={self.id}, numero={self.numero_ticket}, "
            f"estado={self.estado}, total={self.total_con_impuestos})>"
        )


class POSTicketDetalle(Base):
    """
    Modelo de Detalle de Ticket POS.

    Cada línea del ticket con producto, cantidad, precio e IVA.
    """
    __tablename__ = "pos_ticket_detalles"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    ticket_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("pos_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID del ticket",
    )
    product_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID del producto (opcional para items manuales)",
    )
    codigo_principal: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Código principal del producto",
    )
    descripcion: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Descripción del producto o servicio",
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="Cantidad vendida",
    )
    unidad_medida: Mapped[str] = mapped_column(
        String(50),
        default="Unidad",
        nullable=False,
        comment="Unidad de medida",
    )
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Precio unitario sin impuestos",
    )
    descuento: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Descuento aplicado",
    )
    precio_total_sin_impuestos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Precio total sin impuestos (cantidad * precio_unitario - descuento)",
    )
    iva_codigo: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="Código de tarifa de IVA según Tabla 16 del SRI",
    )
    iva_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Porcentaje de IVA",
    )
    iva_valor: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Valor del IVA",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Fecha de creación del registro",
    )

    # Relaciones
    ticket: Mapped["POSTicket"] = relationship(
        "POSTicket",
        back_populates="detalles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<POSTicketDetalle(id={self.id}, descripcion={self.descripcion}, "
            f"cantidad={self.cantidad})>"
        )


class POSArqueo(Base):
    """
    Modelo de Arqueo de Caja POS.

    Registra el conteo de efectivo en caja, puede ser parcial
    (durante el turno) o final (al cerrar la caja).
    """
    __tablename__ = "pos_arqueos"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    cash_session_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("pos_cash_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la sesión de caja",
    )
    company_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID de la empresa",
    )
    tipo: Mapped[str] = mapped_column(
        String(20),
        default=ArqueoTipo.PARCIAL.value,
        nullable=False,
        comment="Tipo de arqueo: parcial, final",
    )
    billetes: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="JSON con conteo de billetes por denominación: {\"1\": 5, \"5\": 10, ...}",
    )
    monedas: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="JSON con conteo de monedas por denominación: {\"0.05\": 20, \"0.10\": 50, ...}",
    )
    total_billetes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total en billetes",
    )
    total_monedas: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Total en monedas",
    )
    total_efectivo_contado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total de efectivo contado (billetes + monedas)",
    )
    total_efectivo_calculado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Total de efectivo calculado por el sistema",
    )
    diferencia: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Diferencia: sobrante(+) o faltante(-)",
    )
    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones del arqueo",
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="ID del usuario que realizó el arqueo",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Fecha de creación del registro",
    )

    # Relaciones
    cash_session: Mapped["POSCashSession"] = relationship(
        "POSCashSession",
        back_populates="arqueos",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<POSArqueo(id={self.id}, tipo={self.tipo}, "
            f"diferencia={self.diferencia})>"
        )
