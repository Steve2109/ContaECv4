"""
ContaEC - Esquemas de Empresa y Establecimiento
Pydantic schemas para creación, actualización y respuesta de empresas
"""
from uuid import UUID
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Empresa (Company)
# ==========================================

class CompanyCreate(BaseModel):
    """Esquema para crear una nueva empresa"""
    ruc: str = Field(
        ...,
        min_length=13,
        max_length=13,
        description="Registro Único de Contribuyente (13 dígitos)",
        examples=["1790012345001"],
    )
    razon_social: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Razón social de la empresa (nombre legal)",
        examples=["DISTRIBUIDORA ABC S.A."],
    )
    nombre_comercial: str | None = Field(
        None,
        max_length=255,
        description="Nombre comercial de la empresa",
        examples=["ABC Distribuciones"],
    )
    dir_matriz: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Dirección de la matriz de la empresa",
        examples=["Av. Amazonas 1234 y Amazonas"],
    )
    dir_establecimiento: str | None = Field(
        None,
        max_length=500,
        description="Dirección del establecimiento principal",
    )
    cod_establecimiento: str = Field(
        default="001",
        min_length=3,
        max_length=3,
        description="Código del establecimiento (3 dígitos)",
        examples=["001"],
    )
    cod_punto_emision: str = Field(
        default="001",
        min_length=3,
        max_length=3,
        description="Código del punto de emisión (3 dígitos)",
        examples=["001"],
    )
    contribuyente_especial: str | None = Field(
        None,
        max_length=5,
        description="Número de resolución como contribuyente especial",
    )
    obligado_contabilidad: str = Field(
        default="NO",
        description="Obligado a llevar contabilidad (SI/NO)",
        examples=["SI"],
    )
    tipo_ambiente: str = Field(
        default="1",
        description="Tipo de ambiente: 1=Pruebas, 2=Producción",
        examples=["1"],
    )
    tipo_emision: str = Field(
        default="1",
        description="Tipo de emisión: 1=Normal",
        examples=["1"],
    )
    rise: str | None = Field(
        None,
        max_length=50,
        description="Régimen Simplificado RISE",
    )
    agente_retencion: str | None = Field(
        None,
        max_length=5,
        description="Número de resolución como agente de retención",
    )
    contribuyente_rimpe: str | None = Field(
        None,
        max_length=50,
        description="Tipo de contribuyente RIMPE",
        examples=["RIMPE Emprendedor"],
    )
    logo_path: str | None = Field(
        None,
        max_length=500,
        description="Ruta del logo de la empresa",
    )
    # Contacto
    correo: str | None = Field(
        None,
        max_length=255,
        description="Correo electronico de la empresa",
    )
    telefono: str | None = Field(
        None,
        max_length=20,
        description="Telefono de la empresa",
    )
    # Firma electronica (OBLIGATORIA para crear la empresa)
    firma_electronica_path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Ruta del archivo de firma electronica (.p12/.pfx) subido",
    )
    firma_electronica_password: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Contraseña de la firma electronica (.p12/.pfx)",
    )
    # Registro turistico
    registro_turistico: bool = Field(
        default=False,
        description="Registrado en el registro turistico",
    )
    # Operadora Transportista
    operadora_transportista_comercial: bool = Field(
        default=False,
        description="Es operadora transportista comercial",
    )
    operadora_transportista_ligera: bool = Field(
        default=False,
        description="Es operadora transportista ligera (cooperativas de taxis, etc.)",
    )
    ruc_operadora_comercial: str | None = Field(
        None,
        max_length=13,
        description="RUC de operadora transportista comercial (solo si socio transportista)",
    )
    ruc_operadora_transportista: str | None = Field(
        None,
        max_length=13,
        description="RUC de operadora transportista",
    )
    # Informacion adicional
    codigo_artesano: str | None = Field(
        None,
        max_length=50,
        description="Codigo de artesano",
    )
    nombre_recibos: str | None = Field(
        None,
        max_length=255,
        description="Nombre que aparece en los recibos",
    )
    # SMTP por empresa
    smtp_host: str | None = Field(
        None,
        max_length=255,
        description="Host del servidor SMTP",
    )
    smtp_port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Puerto SMTP",
    )
    smtp_user: str | None = Field(
        None,
        max_length=255,
        description="Usuario SMTP",
    )
    smtp_password: str | None = Field(
        None,
        max_length=500,
        description="Contraseña SMTP",
    )
    smtp_protocol: str | None = Field(
        None,
        max_length=10,
        description="Protocolo SMTP (TLS/SSL)",
    )
    smtp_ssl: bool = Field(
        default=True,
        description="Usar SSL para SMTP",
    )
    # Ambiente por empresa
    environment_mode: str = Field(
        default="sandbox",
        description="Modo de ambiente: sandbox/production",
    )
    # VirusTotal por empresa
    virustotal_enabled: bool = Field(
        default=False,
        description="Habilitar escaneo con VirusTotal",
    )

    @field_validator("ruc_operadora_comercial", "ruc_operadora_transportista")
    @classmethod
    def validate_ruc_optional(cls, v: str | None) -> str | None:
        """Valida el formato del RUC si esta presente"""
        if v is not None and v != "":
            if not re.match(r"^\d{13}$", v):
                raise ValueError("El RUC debe tener exactamente 13 dígitos numéricos")
            provincia = int(v[:2])
            if provincia < 1 or provincia > 24:
                raise ValueError("Código de provincia del RUC inválido (01-24)")
        return v

    @field_validator("ruc")
    @classmethod
    def validate_ruc(cls, v: str) -> str:
        """Valida el formato del RUC ecuatoriano (13 dígitos)"""
        if not re.match(r"^\d{13}$", v):
            raise ValueError("El RUC debe tener exactamente 13 dígitos numéricos")
        # Validación básica del dígito verificador
        provincia = int(v[:2])
        if provincia < 1 or provincia > 24:
            raise ValueError("Código de provincia del RUC inválido (01-24)")
        return v

    @field_validator("obligado_contabilidad")
    @classmethod
    def validate_obligado_contabilidad(cls, v: str) -> str:
        """Valida que el valor sea SI o NO"""
        if v not in ("SI", "NO"):
            raise ValueError("obligado_contabilidad debe ser 'SI' o 'NO'")
        return v

    @field_validator("tipo_ambiente")
    @classmethod
    def validate_tipo_ambiente(cls, v: str) -> str:
        """Valida que el tipo de ambiente sea 1 o 2"""
        if v not in ("1", "2"):
            raise ValueError("tipo_ambiente debe ser '1' (Pruebas) o '2' (Producción)")
        return v

    @field_validator("tipo_emision")
    @classmethod
    def validate_tipo_emision(cls, v: str) -> str:
        """Valida que el tipo de emisión sea 1"""
        if v != "1":
            raise ValueError("tipo_emision debe ser '1' (Normal)")
        return v

    @field_validator("cod_establecimiento", "cod_punto_emision")
    @classmethod
    def validate_codigo_3_digitos(cls, v: str) -> str:
        """Valida que el código tenga exactamente 3 dígitos"""
        if not re.match(r"^\d{3}$", v):
            raise ValueError("El código debe tener exactamente 3 dígitos numéricos (ej: 001)")
        return v

    @field_validator("contribuyente_rimpe")
    @classmethod
    def validate_contribuyente_rimpe(cls, v: str | None) -> str | None:
        """Valida que el tipo de contribuyente RIMPE sea válido"""
        if v is not None:
            valid_types = {"RIMPE Emprendedor", "RIMPE Negocio Popular", ""}
            if v not in valid_types:
                raise ValueError(
                    "Tipo de contribuyente RIMPE inválido. "
                    "Opciones: RIMPE Emprendedor, RIMPE Negocio Popular"
                )
        return v


class CompanyUpdate(BaseModel):
    """Esquema para actualizar datos de una empresa"""
    razon_social: str | None = Field(
        None,
        min_length=2,
        max_length=255,
        description="Razón social de la empresa",
    )
    nombre_comercial: str | None = Field(
        None,
        max_length=255,
        description="Nombre comercial de la empresa",
    )
    dir_matriz: str | None = Field(
        None,
        min_length=5,
        max_length=500,
        description="Dirección de la matriz",
    )
    dir_establecimiento: str | None = Field(
        None,
        max_length=500,
        description="Dirección del establecimiento",
    )
    cod_establecimiento: str | None = Field(None, max_length=3)
    cod_punto_emision: str | None = Field(None, max_length=3)
    contribuyente_especial: str | None = Field(None, max_length=5)
    obligado_contabilidad: str | None = Field(None)
    tipo_ambiente: str | None = Field(None)
    tipo_emision: str | None = Field(None)
    rise: str | None = Field(None, max_length=50)
    agente_retencion: str | None = Field(None, max_length=5)
    contribuyente_rimpe: str | None = Field(None, max_length=50)
    logo_path: str | None = Field(None, max_length=500)
    is_active: bool | None = Field(None, description="Estado activo de la empresa")
    # Contacto
    correo: str | None = Field(None, max_length=255)
    telefono: str | None = Field(None, max_length=20)
    firma_electronica_password: str | None = Field(None, max_length=500)
    # Registro turistico
    registro_turistico: bool | None = Field(None)
    # Operadora Transportista
    operadora_transportista_comercial: bool | None = Field(None)
    operadora_transportista_ligera: bool | None = Field(None)
    ruc_operadora_comercial: str | None = Field(None, max_length=13)
    ruc_operadora_transportista: str | None = Field(None, max_length=13)
    # Informacion adicional
    codigo_artesano: str | None = Field(None, max_length=50)
    nombre_recibos: str | None = Field(None, max_length=255)
    # SMTP por empresa
    smtp_host: str | None = Field(None, max_length=255)
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_user: str | None = Field(None, max_length=255)
    smtp_password: str | None = Field(None, max_length=500)
    smtp_protocol: str | None = Field(None, max_length=10)
    smtp_ssl: bool | None = Field(None)
    # Ambiente por empresa
    environment_mode: str | None = Field(None)
    # VirusTotal por empresa
    virustotal_enabled: bool | None = Field(None)

    @field_validator("obligado_contabilidad")
    @classmethod
    def validate_obligado_contabilidad(cls, v: str | None) -> str | None:
        """Valida que el valor sea SI o NO"""
        if v is not None and v not in ("SI", "NO"):
            raise ValueError("obligado_contabilidad debe ser 'SI' o 'NO'")
        return v

    @field_validator("tipo_ambiente")
    @classmethod
    def validate_tipo_ambiente(cls, v: str | None) -> str | None:
        """Valida que el tipo de ambiente sea 1 o 2"""
        if v is not None and v not in ("1", "2"):
            raise ValueError("tipo_ambiente debe ser '1' (Pruebas) o '2' (Producción)")
        return v


class CompanyResponse(BaseModel):
    """Esquema de respuesta con datos de la empresa"""
    id: UUID = Field(..., description="ID único de la empresa")
    user_id: UUID = Field(..., description="ID del usuario propietario")
    ruc: str = Field(..., description="RUC de la empresa")
    razon_social: str = Field(..., description="Razón social")
    nombre_comercial: str | None = Field(None, description="Nombre comercial")
    dir_matriz: str = Field(..., description="Dirección de la matriz")
    dir_establecimiento: str | None = Field(None, description="Dirección del establecimiento")
    cod_establecimiento: str = Field(..., description="Código del establecimiento")
    cod_punto_emision: str = Field(..., description="Código del punto de emisión")
    contribuyente_especial: str | None = Field(None, description="Contribuyente especial")
    obligado_contabilidad: str = Field(..., description="Obligado a llevar contabilidad")
    tipo_ambiente: str = Field(..., description="Tipo de ambiente")
    tipo_emision: str = Field(..., description="Tipo de emisión")
    rise: str | None = Field(None, description="RISE")
    agente_retencion: str | None = Field(None, description="Agente de retención")
    contribuyente_rimpe: str | None = Field(None, description="Contribuyente RIMPE")
    logo_path: str | None = Field(None, description="Ruta del logo")
    # Contacto
    correo: str | None = Field(None, description="Correo electronico")
    telefono: str | None = Field(None, description="Telefono")
    # Firma electronica (solo path, nunca la contraseña)
    firma_electronica_path: str | None = Field(None, description="Ruta del archivo de firma electronica")
    # Registro turistico
    registro_turistico: bool = Field(..., description="Registrado en el registro turistico")
    # Operadora Transportista
    operadora_transportista_comercial: bool = Field(..., description="Es operadora transportista comercial")
    operadora_transportista_ligera: bool = Field(..., description="Es operadora transportista ligera")
    ruc_operadora_comercial: str | None = Field(None, description="RUC operadora transportista comercial")
    ruc_operadora_transportista: str | None = Field(None, description="RUC operadora transportista")
    # Informacion adicional
    codigo_artesano: str | None = Field(None, description="Codigo de artesano")
    nombre_recibos: str | None = Field(None, description="Nombre que aparece en los recibos")
    # SMTP por empresa
    smtp_host: str | None = Field(None, description="Host del servidor SMTP")
    smtp_port: int | None = Field(None, description="Puerto SMTP")
    smtp_user: str | None = Field(None, description="Usuario SMTP")
    smtp_protocol: str | None = Field(None, description="Protocolo SMTP")
    smtp_ssl: bool = Field(..., description="Usar SSL para SMTP")
    # Ambiente por empresa
    environment_mode: str = Field(..., description="Modo de ambiente: sandbox/production")
    # VirusTotal por empresa
    virustotal_enabled: bool = Field(..., description="Habilitar escaneo con VirusTotal")
    # Estado
    is_active: bool = Field(..., description="Estado activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if hasattr(v, '__str__') and not isinstance(v, str):
            return str(v)
        return v


# ==========================================
# Establecimiento (Establishment)
# ==========================================

class EstablishmentCreate(BaseModel):
    """Esquema para crear un nuevo establecimiento"""
    codigo: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Código del establecimiento (3 dígitos)",
        examples=["002"],
    )
    direccion: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Dirección del establecimiento",
        examples=["Av. 9 de Octubre 567 y Colón"],
    )

    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, v: str) -> str:
        """Valida que el código tenga exactamente 3 dígitos"""
        if not re.match(r"^\d{3}$", v):
            raise ValueError("El código debe tener exactamente 3 dígitos numéricos (ej: 001)")
        return v


class EstablishmentResponse(BaseModel):
    """Esquema de respuesta con datos del establecimiento"""
    id: UUID = Field(..., description="ID único del establecimiento")
    company_id: UUID = Field(..., description="ID de la empresa")
    codigo: str = Field(..., description="Código del establecimiento")
    direccion: str = Field(..., description="Dirección del establecimiento")
    is_active: bool = Field(..., description="Estado activo")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
