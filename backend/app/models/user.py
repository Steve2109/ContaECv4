"""
ContaEC - Modelos de Usuario
User: Modelo principal del usuario del sistema
UserConfig: Configuración específica del usuario (firma digital, SMTP, etc.)
"""
import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LicenseType(str, enum.Enum):
    """Tipos de licencia disponibles"""
    MENSUAL = "monthly"
    TRIMESTRAL = "quarterly"
    SEMESTRAL = "semiannual"
    ANUAL = "annual"


class Language(str, enum.Enum):
    """Idiomas soportados"""
    ES_EC = "es_EC"
    EN_US = "en_US"


class Theme(str, enum.Enum):
    """Temas de la interfaz"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class EnvironmentMode(str, enum.Enum):
    """Modo de ambiente para facturación electrónica"""
    SANDBOX = "sandbox"       # Pruebas
    PRODUCTION = "production"  # Producción


class SmtpProtocol(str, enum.Enum):
    """Protocolos de correo electrónico"""
    IMAP = "IMAP"
    POP = "POP"
    SMTP = "SMTP"


class User(Base):
    """
    Modelo de usuario del sistema ContaEC.
    
    Almacena la información principal del usuario incluyendo
    datos de autenticación, preferencias y licencia.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Correo electrónico del usuario (único)",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre completo del usuario",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Contraseña hasheada con bcrypt",
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el usuario debe cambiar su contraseña en el próximo inicio de sesión (contraseña temporal)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el usuario está activo",
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el usuario es administrador",
    )
    # Sub-cuentas: cuentas creadas por otro usuario (owner) con acceso limitado
    parent_user_id: Mapped[str | None] = mapped_column(
        PG_UUID(),
        nullable=True,
        index=True,
        comment="ID del usuario que creó esta sub-cuenta (None si es cuenta principal)",
    )
    is_subaccount: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si esta cuenta es una sub-cuenta con acceso limitado",
    )
    allowed_modules: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON con los módulos permitidos para la sub-cuenta (ej: [\"facturacion\", \"clientes\"])",
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Número de teléfono del usuario",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default=Language.ES_EC,
        nullable=False,
        comment="Idioma preferido del usuario",
    )
    theme: Mapped[str] = mapped_column(
        String(10),
        default=Theme.LIGHT,
        nullable=False,
        comment="Tema de la interfaz del usuario",
    )
    backup_encryption_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Clave de cifrado de respaldos (cifrada con Fernet)",
    )
    license_type: Mapped[str] = mapped_column(
        String(20),
        default=LicenseType.MENSUAL,
        nullable=False,
        comment="Tipo de licencia del usuario",
    )
    license_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de inicio de la licencia",
    )
    license_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de expiración de la licencia",
    )
    # Trial period fields
    is_trial: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el usuario está en período de prueba",
    )
    trial_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de inicio del período de prueba",
    )
    trial_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de fin del período de prueba (15 días por defecto)",
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
    config: Mapped["UserConfig | None"] = relationship(
        "UserConfig",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    companies: Mapped[list["Company"]] = relationship(  # noqa: F821
        "Company",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    company_roles: Mapped[list["UserCompanyRole"]] = relationship(  # noqa: F821
        "UserCompanyRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    comprobantes: Mapped[list["Comprobante"]] = relationship(  # noqa: F821
        "Comprobante",
        back_populates="user",
        lazy="selectin",
    )
    proformas: Mapped[list["Proforma"]] = relationship(  # noqa: F821
        "Proforma",
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, full_name={self.full_name})>"

    @property
    def is_license_valid(self) -> bool:
        """Verifica si la licencia o el período de prueba del usuario está vigente"""
        # Check trial first
        if self.is_trial and self.trial_end_date:
            now = datetime.now(timezone.utc)
            trial_end = self.trial_end_date
            if trial_end.tzinfo is None:
                trial_end = trial_end.replace(tzinfo=timezone.utc)
            return now <= trial_end
        # Then check license
        if not self.license_end_date:
            return False
        return datetime.now(timezone.utc) <= self.license_end_date


class UserConfig(Base):
    """
    Configuración específica del usuario para facturación electrónica.
    
    Almacena datos sensibles como la firma digital, credenciales SMTP
    y preferencias de ambiente. Los campos sensibles se cifran con Fernet.
    """
    __tablename__ = "user_configs"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="ID del usuario al que pertenece la configuración",
    )
    # Firma digital
    digital_signature_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Ruta del archivo de firma digital (.p12/.pfx) - cifrado",
    )
    digital_signature_password: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Contraseña de la firma digital - cifrado",
    )
    signature_expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de expiración de la firma digital",
    )
    # Logo de la empresa
    company_logo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Ruta del logo de la empresa del usuario",
    )
    # Configuración SMTP (para envío de comprobantes)
    smtp_host: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Servidor SMTP para envío de correos",
    )
    smtp_port: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Puerto del servidor SMTP",
    )
    smtp_user: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Usuario del servidor SMTP",
    )
    smtp_password: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Contraseña del servidor SMTP - cifrado",
    )
    smtp_protocol: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Protocolo de correo (IMAP/POP/SMTP)",
    )
    smtp_ssl: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si se usa SSL/TLS para SMTP",
    )
    # Ambiente de facturación electrónica
    environment_mode: Mapped[str] = mapped_column(
        String(20),
        default=EnvironmentMode.SANDBOX,
        nullable=False,
        comment="Modo de ambiente: sandbox (pruebas) o production (producción)",
    )
    # VirusTotal (escaneo opcional en la nube)
    virustotal_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el usuario ha activado VirusTotal para escaneo de archivos",
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="config",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<UserConfig(id={self.id}, user_id={self.user_id})>"
