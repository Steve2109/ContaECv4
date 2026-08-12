"""
ContaEC - Configuración de la aplicación
Lee las variables de entorno desde el archivo .env usando pydantic-settings
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env file path relative to this config file's directory
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE_PATH = _CONFIG_DIR / ".env"


class Settings(BaseSettings):
    """
    Configuración principal de la aplicación ContaEC.
    Todas las variables se cargan desde el archivo .env
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================
    # Aplicación
    # ==========================================
    APP_NAME: str = "ContaEC"
    APP_VERSION: str = "5.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = ""
    ENCRYPTION_KEY: str = ""

    # ==========================================
    # Base de datos
    # ==========================================
    DATABASE_URL: str = "sqlite+aiosqlite:///./contaec.db"

    # PostgreSQL (producción)
    POSTGRES_USER: str = "contaec_user"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "contaec_db"

    # ==========================================
    # Autenticación JWT
    # ==========================================
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==========================================
    # Credenciales Admin (pre-configuradas)
    # ==========================================
    ADMIN_EMAIL: str = "steve.mejia@tymtechnology.shop"
    ADMIN_PASSWORD: str = ""  # Must be set via ADMIN_PASSWORD env var

    # ==========================================
    # Servicios Web del SRI - Pruebas (Testing)
    # ==========================================
    SRI_WS_RECEPCION_PRUEBAS: str = (
        "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"
    )
    SRI_WS_AUTORIZACION_PRUEBAS: str = (
        "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
    )

    # ==========================================
    # Servicios Web del SRI - Producción
    # ==========================================
    SRI_WS_RECEPCION_PRODUCCION: str = (
        "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"
    )
    SRI_WS_AUTORIZACION_PRODUCCION: str = (
        "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
    )

    # ==========================================
    # Servicios Web de Consulta del SRI - Pruebas
    # ==========================================
    SRI_WS_CONSULTA_PRUEBAS: str = (
        "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/ConsultaComprobante?wsdl"
    )
    SRI_WS_CONSULTA_FACTURA_PRUEBAS: str = (
        "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/ConsultaFactura?wsdl"
    )

    # ==========================================
    # Servicios Web de Consulta del SRI - Producción
    # ==========================================
    SRI_WS_CONSULTA_PRODUCCION: str = (
        "https://cel.sri.gob.ec/comprobantes-electronicos-ws/ConsultaComprobante?wsdl"
    )
    SRI_WS_CONSULTA_FACTURA_PRODUCCION: str = (
        "https://cel.sri.gob.ec/comprobantes-electronicos-ws/ConsultaFactura?wsdl"
    )

    # ==========================================
    # Configuración de Respaldos
    # ==========================================
    BACKUP_DIR: str = "./backups"
    BACKUP_ENCRYPTION_KEY: str = ""

    # ==========================================
    # ClamAV (Antivirus)
    # ==========================================
    CLAMAV_ENABLED: bool = False
    CLAMAV_SOCKET: str = "/var/run/clamav/clamd.ctl"
    CLAMAV_HOST: str = "127.0.0.1"
    CLAMAV_PORT: int = 3310

    # ==========================================
    # VirusTotal
    # ==========================================
    VIRUSTOTAL_ENABLED: bool = False
    VIRUSTOTAL_API_KEY: str = ""

    # ==========================================
    # SRI RUC Lookup
    # ==========================================
    # Set to True to use mock data for RUC lookup (development only)
    # This is useful when the SRI service is unavailable or timing out
    SRI_RUC_SANDBOX: bool = False

    # ==========================================
    # CORS
    # ==========================================
    CORS_ORIGINS: str = "http://localhost:3000,https://conta.tymtechnology.shop"

    # ==========================================
    # Rate Limiting
    # ==========================================
    RATE_LIMIT_PER_MINUTE: int = 60

    # ==========================================
    # Servidor
    # ==========================================
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # ==========================================
    # SMTP del Sistema (correos automáticos: bienvenida, notificaciones)
    # Este buzón es del SISTEMA (ej: info@tymtechnology.shop), distinto
    # del SMTP que cada usuario configura para sus comprobantes.
    # SMTP_SSL=True -> puerto 465 (SSL directo) | SMTP_SSL=False -> STARTTLS (587)
    # ==========================================
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SSL: bool = False
    SMTP_FROM_NAME: str = "ContaEC"

    # ==========================================
    # Almacenamiento Volátil
    # ==========================================
    TEMP_DIR: str = "./temp"
    UPLOAD_DIR: str = "./uploads"
    SIGNATURES_DIR: str = "./signatures"  # Outside public uploads directory

    # ==========================================
    # Propiedades derivadas
    # ==========================================
    @property
    def is_production(self) -> bool:
        """Indica si el ambiente es producción"""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Indica si el ambiente es desarrollo"""
        return self.APP_ENV.lower() == "development"

    # Allowed JWT algorithms - prevent "none" algorithm attack
    _ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}

    @model_validator(mode="after")
    def validate_jwt_algorithm(self) -> "Settings":
        """Ensure JWT_ALGORITHM is not set to an insecure value like 'none'."""
        if self.JWT_ALGORITHM not in self._ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"JWT_ALGORITHM must be one of {self._ALLOWED_JWT_ALGORITHMS}, "
                f"got '{self.JWT_ALGORITHM}'. The 'none' algorithm is NOT allowed."
            )
        return self

    @property
    def sri_ws_recepcion(self) -> str:
        """URL del servicio web de recepción del SRI según el ambiente"""
        if self.is_production:
            return self.SRI_WS_RECEPCION_PRODUCCION
        return self.SRI_WS_RECEPCION_PRUEBAS

    @property
    def sri_ws_autorizacion(self) -> str:
        """URL del servicio web de autorización del SRI según el ambiente"""
        if self.is_production:
            return self.SRI_WS_AUTORIZACION_PRODUCCION
        return self.SRI_WS_AUTORIZACION_PRUEBAS

    @property
    def sri_ws_consulta(self) -> str:
        """URL del servicio web de consulta del SRI según el ambiente"""
        if self.is_production:
            return self.SRI_WS_CONSULTA_PRODUCCION
        return self.SRI_WS_CONSULTA_PRUEBAS

    @property
    def sri_ws_consulta_factura(self) -> str:
        """URL del servicio web de consulta de factura del SRI según el ambiente"""
        if self.is_production:
            return self.SRI_WS_CONSULTA_FACTURA_PRODUCCION
        return self.SRI_WS_CONSULTA_FACTURA_PRUEBAS

    @property
    def database_url_async(self) -> str:
        """
        URL asíncrona de la base de datos (PostgreSQL obligatorio).

        Prioridad:
        1. Si DATABASE_URL está configurada con PostgreSQL -> usar directamente
        2. Si DATABASE_URL tiene PostgreSQL sincrónico -> convertir a asyncpg
        3. Si POSTGRES_HOST/POSTGRES_DB están configuradas -> construir URL
        4. Error si no hay configuración PostgreSQL
        """
        url = self.DATABASE_URL

        # Si es PostgreSQL sincrónico, convertir a asíncrono
        if url.startswith("postgresql://") and "asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        # Si ya tiene asyncpg, usarla directamente
        elif url.startswith("postgresql+asyncpg://"):
            pass  # Ya está en el formato correcto
        # Si no tiene protocolo pero parece PostgreSQL, construir desde variables
        elif self.POSTGRES_HOST and self.POSTGRES_DB:
            url = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            raise RuntimeError(
                "⛔ PostgreSQL es la única base de datos soportada. "
                "Configure DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname "
                "o las variables POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD."
            )

        return url

    @property
    def cors_origins_list(self) -> list[str]:
        """Lista de orígenes CORS permitidos"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def validate_production_secrets(self) -> list[str]:
        """
        Valida que los secrets no tengan valores por defecto en producción.
        Retorna una lista de advertencias (vacía si todo está bien).
        """
        warnings = []

        # Check for empty or missing secrets
        if not self.SECRET_KEY:
            warnings.append(
                "⚠️  SECRET_KEY no configurada. Configure la variable de entorno SECRET_KEY "
                "con un valor seguro (ej: python -c 'import secrets; print(secrets.token_urlsafe())')."
            )

        if not self.ENCRYPTION_KEY:
            warnings.append(
                "⚠️  ENCRYPTION_KEY no configurada. Configure la variable de entorno ENCRYPTION_KEY "
                "con un valor seguro de 32 bytes."
            )

        if not self.JWT_SECRET_KEY:
            warnings.append(
                "⚠️  JWT_SECRET_KEY no configurada. Configure la variable de entorno JWT_SECRET_KEY "
                "con un valor seguro."
            )

        if not self.ADMIN_PASSWORD:
            warnings.append(
                "⚠️  ADMIN_PASSWORD no configurada. Configure la variable de entorno "
                "ADMIN_PASSWORD con la contraseña del administrador."
            )

        if not self.BACKUP_ENCRYPTION_KEY:
            warnings.append(
                "⚠️  BACKUP_ENCRYPTION_KEY no configurada. Los respaldos no estarán cifrados."
            )

        if not self.POSTGRES_PASSWORD:
            warnings.append(
                "⚠️  POSTGRES_PASSWORD no configurada. No se podrá conectar a PostgreSQL."
            )

        return warnings


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración de la aplicación (caché en memoria).
    Se utiliza como dependencia en FastAPI.
    """
    return Settings()
