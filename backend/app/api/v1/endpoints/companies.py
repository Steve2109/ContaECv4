"""
ContaEC - Endpoints de Empresas
CRUD de empresas, establecimientos, auto-completado RUC desde SRI
"""
import logging
import os
import re
import uuid
from typing import Optional
from uuid import UUID
from pathlib import Path
from datetime import datetime, timezone

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.company import Company, Establishment
from app.models.client import Client, TipoIdentificacion
from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    EstablishmentCreate,
    EstablishmentResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/companies", tags=["Empresas"])


# _ensure_consumidor_final movido a app.core.utils para evitar duplicación
from app.core.utils import ensure_consumidor_final


# ==========================================
# Validación de firma electrónica
# ==========================================

def _validate_signature_password(firma_path: str, password: str) -> None:
    """
    Valida que la contraseña ingresada corresponda al archivo .p12/.pfx de la firma.

    Reutiliza la misma lógica de validación PKCS#12 del comprobador de firmas
    (app/api/v1/endpoints/uploads.py: validate_digital_signature) para garantizar
    que la contraseña es la correcta antes de guardar la empresa.

    Raises:
        HTTPException 400: si la firma no existe, la contraseña es incorrecta,
        el archivo no es un PKCS#12 válido o el certificado está expirado.
    """
    # Seguridad: solo se aceptan rutas dentro del directorio de uploads/companies
    # con nombre generado por el servidor (uuid4 hex + .p12/.pfx). Evita path
    # traversal y lecturas arbitrarias de archivos del servidor.
    if not re.match(r"^/uploads/companies/[A-Za-z0-9_]+\.(p12|pfx)$", firma_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La ruta de la firma electrónica es inválida. Vuelva a subir el archivo.",
        )

    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    upload_dir = base_dir / "uploads" / "companies"
    abs_path = (upload_dir / Path(firma_path).name).resolve()

    # Verificación extra de contención (defensa en profundidad)
    if not abs_path.is_relative_to(upload_dir.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La ruta de la firma electrónica es inválida. Vuelva a subir el archivo.",
        )

    if not abs_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de firma electrónica no fue encontrado en el servidor. Vuelva a subirlo.",
        )

    content = abs_path.read_bytes()

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12

        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            content, password.encode()
        )

        if not certificate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontró certificado en el archivo PKCS#12.",
            )

        # Rechazar certificados expirados (misma validación que el comprobador
        # de firmas /v1/uploads/validate-signature usado por el frontend)
        now = datetime.now(timezone.utc)
        not_after = certificate.not_valid_after_utc
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        if not_after < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La firma electrónica ha EXPIRADO. Renueve su firma e intente nuevamente.",
            )
    except HTTPException:
        raise
    except ValueError as e:
        if "password" in str(e).lower() or "mac" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña no corresponde a la firma electrónica. Verifíquela e intente nuevamente.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo de firma electrónica inválido: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error validando firma electrónica al crear empresa: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo validar la firma electrónica: {str(e)}",
        )


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva empresa para el usuario actual"""
    # Verificar límite de empresas según licencia
    from app.core.utils import get_license_limits

    limits = get_license_limits(current_user)
    max_companies = limits['max_companies']

    # Contar empresas existentes del usuario
    result = await db.execute(
        select(func.count(Company.id)).where(
            Company.user_id == current_user.id,
            Company.is_active == True
        )
    )
    current_count = result.scalar() or 0

    if current_count >= max_companies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Límite de empresas alcanzado. Tu plan actual permite {max_companies} empresa(s). "
                   f"Contacta a soporte para actualizar tu licencia."
        )

    # Verificar que el RUC no exista ya para este usuario
    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.ruc == company_data.ruc
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tiene una empresa registrada con este RUC."
        )

    # Validar que la contraseña corresponde a la firma electrónica (.p12/.pfx)
    _validate_signature_password(
        company_data.firma_electronica_path,
        company_data.firma_electronica_password,
    )

    company = Company(
        user_id=current_user.id,
        **company_data.model_dump(),
    )
    db.add(company)
    await db.flush()

    # Crear cliente Consumidor Final por defecto
    await ensure_consumidor_final(db, str(company.id))

    logger.info(f"Nueva empresa creada: {company.ruc} - {company.razon_social}")
    return CompanyResponse.model_validate(company)


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar todas las empresas del usuario actual"""
    result = await db.execute(
        select(Company).where(Company.user_id == current_user.id)
    )
    companies = result.scalars().all()
    return [CompanyResponse.model_validate(c) for c in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalles de una empresa específica"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id,
        )
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return CompanyResponse.model_validate(company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company_data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar datos de una empresa"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id,
        )
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    update_data = company_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await db.flush()
    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar una empresa (eliminación lógica)"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id,
        )
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    company.is_active = False
    await db.flush()
    return {"message": "Empresa desactivada exitosamente."}


PROVINCIAS_EC = {
    "01": "Azuay", "02": "Bolívar", "03": "Cañar", "04": "Carchi", "05": "Cotopaxi",
    "06": "Chimborazo", "07": "El Oro", "08": "Esmeraldas", "09": "Guayas", "10": "Imbabura",
    "11": "Loja", "12": "Los Ríos", "13": "Manabí", "14": "Morona Santiago", "15": "Napo",
    "16": "Pastaza", "17": "Pichincha", "18": "Tungurahua", "19": "Zamora Chinchipe", "20": "Galápagos",
    "21": "Sucumbíos", "22": "Orellana", "23": "Santo Domingo de los Tsáchilas", "24": "Santa Elena",
    "30": "Zona no delimitada",
}


def _validar_ruc_local(ruc: str) -> tuple[bool, str, str]:
    """
    Valida el dígito verificador de un RUC ecuatoriano y deriva tipo/provincia.
    Retorna (valido, tipo_contribuyente, provincia).
    """
    if not (ruc.isdigit() and len(ruc) == 13):
        return False, "Formato inválido", ""

    provincia = PROVINCIAS_EC.get(ruc[:2], "")
    tercer = int(ruc[2])

    if tercer in (0, 1, 2, 3, 4, 5):
        # Persona natural - módulo 10
        coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        tipo = "Persona Natural"
        modulo = 10
    elif tercer == 6:
        # Sector público - módulo 11
        coef = [3, 2, 7, 6, 5, 4, 3, 2]
        tipo = "Sector Público"
        modulo = 11
    elif tercer in (7, 8):
        # Sociedad / persona jurídica - módulo 11
        coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        tipo = "Sociedad / Persona Jurídica"
        modulo = 11
    elif tercer == 9:
        # Persona natural extranjera - módulo 11
        coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        tipo = "Persona Natural Extranjera"
        modulo = 11
    else:
        return False, "RUC inválido", provincia

    suma = 0
    for i, c in enumerate(coef):
        val = int(ruc[i]) * c
        # Reducción de dígitos solo en el módulo 10 (cédula / persona natural)
        if modulo == 10 and val >= 10:
            val -= 9
        suma += val

    residuo = suma % modulo
    check = modulo - residuo if residuo != 0 else 0
    if check == 10:
        check = 0

    return check == int(ruc[9]), tipo, provincia


async def _consultar_sri_ruc(client: httpx.AsyncClient, ruc: str) -> Optional[dict]:
    """
    Intenta consultar el RUC en los servicios públicos del SRI.
    Retorna el dict parseado o None si el servicio no responde.
    """
    endpoints = [
        # 1. API clásica (retirada por el SRI en 2023+, se mantiene por si vuelve)
        (
            "https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest/ConsultaRuc/obtenerDatosRuc",
            {"params": {"ruc": ruc}},
        ),
        # 2. API de la app móvil SRI (funciona con headers de app móvil)
        (
            f"https://srienlinea.sri.gob.ec/movil-servicios/api/v1.0/ruc/{ruc}",
            {},
        ),
    ]

    mobile_headers = {
        "User-Agent": "okhttp/4.9.0",
        "Accept": "application/json",
        "Accept-Language": "es",
    }

    for url, extra in endpoints:
        try:
            headers = mobile_headers if "movil-servicios" in url else {"User-Agent": "ContaEC/4.0"}
            response = await client.get(url, headers=headers, **extra)
            if response.status_code != 200:
                logger.warning(f"SRI respondió {response.status_code} para RUC {ruc} en {url.split('/')[-1]}")
                continue
            try:
                data = response.json()
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            # La API clásica usa camelCase; la móvil puede variar.
            razon = data.get("razonSocial") or data.get("razon_social") or data.get("nombre") or ""
            if razon:
                return {
                    "razon_social": razon,
                    "nombre_comercial": data.get("nombreComercial") or data.get("nombre_comercial") or "",
                    "dir_matriz": data.get("dirMatriz") or data.get("dir_matriz") or data.get("direccion") or "",
                    "obligado_contabilidad": data.get("obligadoContabilidad") or data.get("obligado_contabilidad") or "NO",
                    "contribuyente_especial": data.get("contribuyenteEspecial") or data.get("contribuyente_especial") or "",
                    "agente_retencion": data.get("agenteRetencion") or data.get("agente_retencion") or "",
                    "contribuyente_rimpe": data.get("contribuyenteRimpe") or data.get("contribuyente_rimpe") or "",
                }
        except httpx.TimeoutException:
            logger.warning(f"SRI timeout consultando RUC {ruc}")
        except httpx.ConnectError:
            logger.warning(f"SRI connection error consultando RUC {ruc}")
        except Exception as e:
            logger.warning(f"Error consultando RUC {ruc}: {e}")

    return None


@router.get("/ruc/{ruc}", response_model=dict)
async def lookup_ruc(
    ruc: str,
    current_user: User = Depends(get_current_user),
):
    """
    Consultar datos de una empresa por RUC desde el SRI.
    Auto-completa los campos de la empresa basado en la información del SRI.
    Si el SRI no responde, valida el RUC localmente (dígito verificador, tipo
    y provincia) para que el botón siempre devuelva información útil.
    """
    from app.core.config import get_settings
    settings = get_settings()

    # Validar formato de RUC (13 dígitos)
    if not ruc.isdigit() or len(ruc) != 13:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RUC inválido. Debe tener 13 dígitos numéricos."
        )

    # Modo sandbox: retornar datos simulados (solo desarrollo)
    if settings.SRI_RUC_SANDBOX and settings.is_development:
        logger.info(f"Sandbox mode: returning mock data for RUC {ruc}")
        return {
            "ruc": ruc,
            "razon_social": f"EMPRESA DE PRUEBA {ruc[-4:]} C.A.",
            "nombre_comercial": f"Comercial {ruc[-4:]}",
            "dir_matriz": "AV. PRINCIPAL 123 Y CALLE SECUNDARIA",
            "obligado_contabilidad": "SI",
            "contribuyente_especial": "",
            "agente_retencion": "",
            "contribuyente_rimpe": "REGIMEN RIMPE",
            "message": "Datos de prueba (sandbox). Verifique con el SRI.",
        }

    # Validación local siempre disponible (dígito verificador + tipo + provincia)
    valido, tipo, provincia = _validar_ruc_local(ruc)

    # Consultar al SRI (con reintentos)
    import httpx
    import asyncio
    last_error = None
    for attempt in range(2):
        try:
            timeout = httpx.Timeout(connect=8.0, read=15.0, total=20.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                data = await _consultar_sri_ruc(client, ruc)
            if data:
                return {
                    "ruc": ruc,
                    **data,
                    "tipo_contribuyente": tipo,
                    "provincia": provincia,
                }
            last_error = "El servicio del SRI no respondió"
        except Exception as e:
            last_error = str(e)
        if attempt == 0:
            await asyncio.sleep(1)

    logger.warning(f"No se pudo consultar RUC {ruc} en SRI: {last_error}")

    # Fallback: validación local + mensaje claro para completar datos manualmente
    message = (
        "RUC válido según dígito verificador. "
        if valido
        else "El RUC ingresado no pasa la validación del dígito verificador. Verifique el número. "
    )
    message += "El servicio en línea del SRI no está disponible en este momento. Complete los datos manualmente."

    return {
        "ruc": ruc,
        "razon_social": "",
        "nombre_comercial": "",
        "dir_matriz": "",
        "tipo_contribuyente": tipo,
        "provincia": provincia,
        "message": message,
    }


# ==================== ESTABLECIMIENTOS ====================

@router.post("/{company_id}/establishments", response_model=EstablishmentResponse, status_code=status.HTTP_201_CREATED)
async def create_establishment(
    company_id: UUID,
    establishment_data: EstablishmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un establecimiento para una empresa"""
    # Verificar que la empresa pertenece al usuario
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id,
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    establishment = Establishment(
        company_id=company_id,
        **establishment_data.model_dump(),
    )
    db.add(establishment)
    await db.flush()

    return EstablishmentResponse.model_validate(establishment)


@router.get("/{company_id}/establishments", response_model=list[EstablishmentResponse])
async def list_establishments(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar establecimientos de una empresa"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id,
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    result = await db.execute(
        select(Establishment).where(Establishment.company_id == company_id)
    )
    establishments = result.scalars().all()
    return [EstablishmentResponse.model_validate(e) for e in establishments]


# ==================== CLIENTES ====================

@router.get("/{company_id}/clients")
async def list_clients(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar clientes de una empresa"""
    # Verificar que la empresa pertenece al usuario
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id,
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    result = await db.execute(
        select(Client).where(Client.company_id == company_id)
    )
    clients = result.scalars().all()

    # Asegurar que exista Consumidor Final
    has_consumer = any(c.is_default_consumer for c in clients)
    if not has_consumer:
        consumer = await ensure_consumidor_final(db, str(company_id))
        clients = [consumer] + list(clients)

    return [
        {
            "id": str(c.id),
            "tipo_identificacion": c.tipo_identificacion,
            "identificacion": c.identificacion,
            "razon_social": c.razon_social,
            "direccion": c.direccion,
            "email": c.email,
            "telefono": c.telefono,
            "is_default_consumer": c.is_default_consumer,
            "is_active": c.is_active,
        }
        for c in clients
    ]


@router.post("/upload/{upload_type}")
async def upload_company_file(
    upload_type: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Subir archivos de empresa: logo o firma electronica.
    
    upload_type: "logo" o "firma"
    Retorna la ruta del archivo guardado.
    """
    if upload_type not in ("logo", "firma"):
        raise HTTPException(status_code=400, detail="Tipo de archivo invalido. Use 'logo' o 'firma'")

    # Resolve to absolute path relative to project root (backend/../uploads)
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    upload_dir = base_dir / "uploads" / "companies"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Validar extension
    filename = file.filename or ""
    if upload_type == "logo":
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            raise HTTPException(status_code=400, detail="Solo se permiten imagenes (png, jpg, jpeg, gif, svg, webp)")
    else:  # firma
        if not filename.lower().endswith((".p12", ".pfx")):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos .p12 o .pfx")

    # Generar nombre unico
    ext = Path(filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / unique_name

    content = await file.read()
    file_path.write_bytes(content)

    relative_path = f"/uploads/companies/{unique_name}"

    logger.info(f"Archivo {upload_type} subido por {current_user.email}: {relative_path}")

    return {
        "file_path": relative_path,
        "filename": filename,
        "upload_type": upload_type,
    }


# ==================== TIPOS DE CONTRIBUYENTE ====================

@router.get("/catalogos/contribuyentes")
async def listar_tipos_contribuyente():
    """
    Obtener catálogo de tipos de contribuyente del SRI.

    Retorna todos los tipos de contribuyente con sus obligaciones
    tributarias y umbrales de ingresos.
    """
    from app.schemas.sri import CONTRIBUYENTE_TIPOS
    return {
        "contribuyentes": [
            {
                "codigo": ct.codigo,
                "nombre": ct.nombre,
                "descripcion": ct.descripcion,
                "obligaciones": ct.obligaciones,
                "umbral_ingresos": float(ct.umbral_ingresos) if ct.umbral_ingresos else None,
            }
            for ct in CONTRIBUYENTE_TIPOS
        ],
    }


@router.get("/catalogos/regimenes")
async def listar_tipos_regimen():
    """
    Obtener catálogo de regímenes tributarios del SRI.

    Retorna todos los regímenes con sus umbrales de ingresos
    y declaraciones requeridas.
    """
    from app.schemas.sri import REGIMEN_TIPOS
    return {
        "regimenes": [
            {
                "codigo": rt.codigo,
                "nombre": rt.nombre,
                "descripcion": rt.descripcion,
                "declaraciones_requeridas": rt.declaraciones_requeridas,
                "umbral_minimo": float(rt.umbral_ingresos_minimo) if rt.umbral_ingresos_minimo else None,
                "umbral_maximo": float(rt.umbral_ingresos_maximo) if rt.umbral_ingresos_maximo else None,
            }
            for rt in REGIMEN_TIPOS
        ],
    }


@router.get("/catalogos/regimen/por-ingresos")
async def obtener_regimen_por_ingresos(
    ingresos: float = Query(..., description="Ingresos anuales brutos en USD"),
):
    """
    Determinar el régimen tributario aplicable según ingresos anuales.

    Args:
        ingresos: Ingresos brutos anuales en dólares

    Returns:
        Régimen tributario aplicable con sus detalles
    """
    from decimal import Decimal
    from app.schemas.sri import get_regimen_por_ingresos

    regimen = get_regimen_por_ingresos(Decimal(str(ingresos)))

    if not regimen:
        raise HTTPException(
            status_code=400,
            detail="No se pudo determinar el régimen tributario",
        )

    return {
        "codigo": regimen.codigo,
        "nombre": regimen.nombre,
        "descripcion": regimen.descripcion,
        "declaraciones_requeridas": regimen.declaraciones_requeridas,
        "umbral_minimo": float(regimen.umbral_ingresos_minimo) if regimen.umbral_ingresos_minimo else None,
        "umbral_maximo": float(regimen.umbral_ingresos_maximo) if regimen.umbral_ingresos_maximo else None,
    }


@router.get("/catalogos/contribuyente/{codigo}")
async def obtener_contribuyente_por_codigo(codigo: str):
    """
    Obtener información de un tipo de contribuyente por su código.

    Códigos válidos: OB, NOB, RIMPE_EMP, RIMPE_NPC, RIMPE_GEN, CON_ESP, AG_RET, SE_PUBLIC
    """
    from app.schemas.sri import get_contribuyente_by_codigo

    contribuyente = get_contribuyente_by_codigo(codigo)

    if not contribuyente:
        raise HTTPException(
            status_code=404,
            detail=f"Tipo de contribuyente '{codigo}' no encontrado",
        )

    return {
        "codigo": contribuyente.codigo,
        "nombre": contribuyente.nombre,
        "descripcion": contribuyente.descripcion,
        "obligaciones": contribuyente.obligaciones,
        "umbral_ingresos": float(contribuyente.umbral_ingresos) if contribuyente.umbral_ingresos else None,
        "requiere_contabilidad": contribuyente.codigo not in ("NOB", "RIMPE_NPC"),
        "es_rimpe": contribuyente.codigo.startswith("RIMPE"),
    }
