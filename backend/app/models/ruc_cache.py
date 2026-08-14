"""
ContaEC - Modelo de caché de consultas RUC
Almacena localmente los datos devueltos por el SRI (o fuentes gratuitas) para
que las consultas repetidas de un mismo RUC no dependan de la disponibilidad
del servicio en línea y respondan de inmediato sin costo.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RucCache(Base):
    """Caché local de datos de contribuyentes consultados al SRI"""

    __tablename__ = "ruc_cache"

    ruc: Mapped[str] = mapped_column(
        String(13),
        primary_key=True,
        comment="RUC consultado (13 dígitos)",
    )
    razon_social: Mapped[str] = mapped_column(
        String(500),
        default="",
        comment="Razón social o nombre del contribuyente",
    )
    nombre_comercial: Mapped[str] = mapped_column(
        String(500),
        default="",
        comment="Nombre comercial",
    )
    dir_matriz: Mapped[str] = mapped_column(
        Text,
        default="",
        comment="Dirección de la matriz",
    )
    obligado_contabilidad: Mapped[str] = mapped_column(
        String(10),
        default="NO",
        comment="Obligado a llevar contabilidad (SI/NO)",
    )
    contribuyente_especial: Mapped[str] = mapped_column(
        String(50),
        default="",
        comment="Número de contribuyente especial",
    )
    agente_retencion: Mapped[str] = mapped_column(
        String(10),
        default="",
        comment="Agente de retención",
    )
    contribuyente_rimpe: Mapped[str] = mapped_column(
        String(50),
        default="",
        comment="Régimen RIMPE",
    )
    tipo_contribuyente: Mapped[str] = mapped_column(
        String(80),
        default="",
        comment="Tipo de contribuyente (persona natural, jurídica, etc.)",
    )
    provincia: Mapped[str] = mapped_column(
        String(80),
        default="",
        comment="Provincia según los dos primeros dígitos del RUC",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Última actualización del registro",
    )

    def __repr__(self) -> str:
        return f"<RucCache(ruc={self.ruc}, razon_social={self.razon_social[:40]})>"
