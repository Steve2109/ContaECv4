"""
ContaEC - Endpoints de Clientes
CRUD de clientes para facturación electrónica
con tipos de identificación según catálogos del SRI (Tabla 7)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import effective_owner_id
from app.core.security import get_current_user
from app.core.validation import validate_uuid
from app.models.client import Client, TipoIdentificacion
from app.models.company import Company
from app.models.user import User
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["Clientes"])


# ==========================================
# Funciones auxiliares
# ==========================================

async def _get_company_for_user(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> Company:
    """
    Obtiene una empresa verificando que pertenezca al usuario actual.
    
    Raises:
        HTTPException: Si la empresa no existe o no pertenece al usuario
    """
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
            Company.is_active == True,
        )
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada o no pertenece al usuario actual.",
        )
    return company


async def _ensure_consumidor_final(
    db: AsyncSession,
    company_id: str,
) -> Client:
    """
    Crea el cliente 'Consumidor Final' por defecto para una empresa.
    
    Este cliente es obligatorio según el SRI para facturas donde
    el comprador no se identifica (ventas al público en general).
    Tipo de identificación: 07 (Consumidor Final)
    Número de identificación: 9999999999999 (13 veces 9)
    """
    # Verificar si ya existe
    result = await db.execute(
        select(Client).where(
            Client.company_id == company_id,
            Client.is_default_consumer == True,
        )
    )
    existing = result.scalars().first()
    if existing:
        return existing

    # Crear Consumidor Final
    consumer = Client(
        company_id=company_id,
        tipo_identificacion=TipoIdentificacion.CONSUMIDOR_FINAL.value,
        identificacion="9999999999999",
        razon_social="CONSUMIDOR FINAL",
        is_default_consumer=True,
        is_active=True,
    )
    db.add(consumer)
    await db.flush()

    logger.info(f"Cliente 'Consumidor Final' creado para empresa {company_id}")
    return consumer


# ==========================================
# Endpoints CRUD
# ==========================================

@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo cliente para una empresa del usuario.
    
    Verifica que la empresa pertenezca al usuario antes de crear el cliente.
    No se puede crear otro cliente Consumidor Final (tipo 07) ya que es automático.
    """
    # Validar que company_id sea un UUID válido antes de consultar la base de datos
    data.company_id = validate_uuid(data.company_id, "company_id")
    
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))
    
    # No permitir crear clientes Consumidor Final manualmente
    if data.tipo_identificacion == TipoIdentificacion.CONSUMIDOR_FINAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede crear un cliente Consumidor Final manualmente. "
                   "Este se crea automáticamente para cada empresa.",
        )
    
    # Verificar que no exista un cliente con la misma identificación en la empresa
    result = await db.execute(
        select(Client).where(
            Client.company_id == data.company_id,
            Client.identificacion == data.identificacion,
            Client.is_active == True,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un cliente con la identificación '{data.identificacion}' en esta empresa.",
        )
    
    # Crear cliente
    client = Client(
        company_id=data.company_id,
        tipo_identificacion=data.tipo_identificacion,
        identificacion=data.identificacion,
        razon_social=data.razon_social,
        direccion=data.direccion,
        email=data.email,
        telefono=data.telefono,
    )
    db.add(client)
    await db.flush()
    
    logger.info(
        f"Cliente creado: identificación={data.identificacion}, "
        f"empresa={data.company_id}"
    )
    
    return ClientResponse.model_validate(client)


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    company_id: str | None = None,
    tipo_identificacion: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar clientes de las empresas del usuario.

    Opcionalmente filtrado por empresa, tipo de identificación y estado activo.
    Incluye el cliente Consumidor Final por defecto si no existe.
    """
    try:
        # 1. Validar formato de company_id si es proporcionado
        if company_id:
            cleaned_id = company_id.strip()
            if cleaned_id in ("", "undefined", "null"):
                return []
            company_id = validate_uuid(cleaned_id, "company_id")

        # 2. Consulta base: clientes de empresas del usuario
        query = (
            select(Client)
            .join(Company, Client.company_id == Company.id)
            .where(Company.user_id == effective_owner_id(current_user))
        )

        # 3. Filtro de empresa
        if company_id:
            await _get_company_for_user(db, company_id, effective_owner_id(current_user))
            query = query.where(Client.company_id == company_id)

            # Asegurar que exista Consumidor Final para la empresa (non-blocking)
            try:
                await _ensure_consumidor_final(db, company_id)
            except Exception:
                await db.rollback()  # Previene abortar la sesión SQLAlchemy
                logger.warning(f"Could not ensure Consumidor Final for company {company_id}", exc_info=True)

        # Filtro de tipo de identificación
        if tipo_identificacion:
            query = query.where(Client.tipo_identificacion == tipo_identificacion)

        # Filtro de estado activo
        if is_active is not None:
            query = query.where(Client.is_active == is_active)

        # Ordenar por razón social y paginar
        query = query.order_by(Client.razon_social).offset(skip).limit(limit)

        result = await db.execute(query)
        clients = result.scalars().all()

        response_clients = []
        for c in clients:
            try:
                response_clients.append(ClientResponse.model_validate(c))
            except Exception:
                logger.warning(f"Could not serialize client {c.id}", exc_info=True)
                # Still include client with nulls for problematic fields
                response_clients.append(ClientResponse(
                    id=str(c.id),
                    company_id=str(c.company_id),
                    tipo_identificacion=c.tipo_identificacion,
                    identificacion=c.identificacion,
                    razon_social=c.razon_social,
                    direccion=c.direccion,
                    email=None,
                    telefono=c.telefono,
                    is_default_consumer=c.is_default_consumer,
                    is_active=c.is_active,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                ))

        return response_clients
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing clients: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar clientes: {str(e)}",
        )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un cliente específico por su ID"""
    client_id = validate_uuid(client_id, "client_id")
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalars().first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, client.company_id, effective_owner_id(current_user))
    
    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    data: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar datos de un cliente"""
    client_id = validate_uuid(client_id, "client_id")
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalars().first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, client.company_id, effective_owner_id(current_user))
    
    # No permitir modificar el tipo de identificación del Consumidor Final
    if client.is_default_consumer and data.tipo_identificacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar el tipo de identificación del Consumidor Final.",
        )
    
    # Si se cambia la identificación, verificar que no exista otro con la misma
    if data.identificacion and data.identificacion != client.identificacion:
        existing = await db.execute(
            select(Client).where(
                Client.company_id == client.company_id,
                Client.identificacion == data.identificacion,
                Client.id != client_id,
                Client.is_active == True,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un cliente con la identificación '{data.identificacion}' en esta empresa.",
            )
    
    # Actualizar campos proporcionados
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    await db.flush()
    
    logger.info(f"Cliente actualizado: identificación={client.identificacion}")
    
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactivar un cliente (eliminación lógica).
    
    No se puede desactivar el cliente Consumidor Final ya que es
    obligatorio según el SRI para facturas sin identificación.
    """
    client_id = validate_uuid(client_id, "client_id")
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalars().first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, client.company_id, effective_owner_id(current_user))
    
    # No permitir eliminar Consumidor Final
    if client.is_default_consumer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el cliente Consumidor Final. Es obligatorio según el SRI.",
        )
    
    # Eliminación lógica
    client.is_active = False
    await db.flush()
    
    logger.info(f"Cliente desactivado: identificación={client.identificacion}")
    
    return {"message": "Cliente desactivado exitosamente."}
