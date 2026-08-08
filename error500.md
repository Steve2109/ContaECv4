# Solución y Corrección: Error 500 Internal Server Error en GET /api/v1/clients

**Fecha:** 2026-08-04  
**Endpoint afectado:** `GET /api/v1/clients?company_id=...`  
**Estado:** 🛠️ Solución documentada y lista para aplicar  

---

## 📌 1. Diagnóstico y Archivos Involucrados

| Componente | Archivo | Líneas | Descripción |
|------------|---------|--------|-------------|
| **Backend Endpoint** | [`backend/app/api/v1/endpoints/clients.py`](file:///Users/nestorvillon/Documents/ContaECv4/backend/app/api/v1/endpoints/clients.py) | L155-L235 | Manejo de la consulta, filtro de `company_id` y creación de `Consumidor Final` |
| **Backend Schema** | [`backend/app/schemas/client.py`](file:///Users/nestorvillon/Documents/ContaECv4/backend/app/schemas/client.py) | L140-L156 | Esquema Pydantic `ClientResponse` |
| **Frontend API Client** | [`src/lib/api.ts`](file:///Users/nestorvillon/Documents/ContaECv4/src/lib/api.ts) | L1126-L1128 | Función `getClients(companyId)` |

---

## 🔍 2. Causas Raíz

1. **`company_id` no válido o string `"undefined"` / `"null"` / `""`:**
   - Al llamar `GET /api/v1/clients?company_id=undefined`, PostgreSQL falla intentando comparar un string no válido contra una columna tipo UUID (`Company.id == company_id`), generando un `DataError`. Al no ser un `HTTPException`, FastAPI devuelve `500 Internal Server Error`.
2. **Estado de Transacción Abortado en `_ensure_consumidor_final`:**
   - Si `_ensure_consumidor_final` falla durante `await db.flush()`, la excepción se captura en un `try...except` sin realizar `await db.rollback()`. En SQLAlchemy `AsyncSession`, esto invalida la sesión y provoca que la siguiente consulta (`await db.execute(query)`) falle con `PendingRollbackError` (500).
3. **Fallo de Conversión UUID en Fallback de `ClientResponse`:**
   - Si falla la serialización de un cliente y se entra al bloque `except` de fallback, los valores `c.id` y `c.company_id` son instancias `uuid.UUID` y no `str`, lo que provoca que Pydantic falle al instanciar `ClientResponse(...)` devolviendo 500.

---

## 🛠️ 3. Correcciones de Código

### A. Backend: `backend/app/api/v1/endpoints/clients.py`

Reemplazar la función `list_clients` por la versión corregida:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ... (resto de imports)

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
    """
    try:
        # 1. Validar formato de company_id si es proporcionado
        if company_id:
            cleaned_id = company_id.strip()
            if cleaned_id in ("", "undefined", "null"):
                return []
            try:
                uuid.UUID(cleaned_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El parámetro company_id debe ser un UUID válido.",
                )
            company_id = cleaned_id

        # 2. Consulta base: clientes de empresas del usuario
        query = (
            select(Client)
            .join(Company, Client.company_id == Company.id)
            .where(Company.user_id == current_user.id)
        )

        # 3. Filtro de empresa
        if company_id:
            await _get_company_for_user(db, company_id, current_user.id)
            query = query.where(Client.company_id == company_id)

            # Asegurar que exista Consumidor Final para la empresa (non-blocking)
            try:
                await _ensure_consumidor_final(db, company_id)
            except Exception:
                await db.rollback()  # Previene abortar la sesión SQLAlchemy
                logger.warning(f"Could not ensure Consumidor Final for company {company_id}", exc_info=True)

        # 4. Filtro de tipo de identificación
        if tipo_identificacion:
            query = query.where(Client.tipo_identificacion == tipo_identificacion)

        # 5. Filtro de estado activo
        if is_active is not None:
            query = query.where(Client.is_active == is_active)

        # 6. Ordenar por razón social y paginar
        query = query.order_by(Client.razon_social).offset(skip).limit(limit)

        result = await db.execute(query)
        clients = result.scalars().all()

        # 7. Serialización segura de respuesta
        response_clients = []
        for c in clients:
            try:
                response_clients.append(ClientResponse.model_validate(c))
            except Exception:
                logger.warning(f"Could not serialize client {c.id}", exc_info=True)
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
```

---

### B. Frontend: `src/lib/api.ts`

Actualizar `getClients` para evitar llamadas innecesarias o erróneas cuando `companyId` no esté listo:

```typescript
async function getClients(companyId: string): Promise<ClientResponse[]> {
  if (!companyId || companyId === 'undefined' || companyId === 'null' || !companyId.trim()) {
    return [];
  }
  return apiGet<ClientResponse[]>(`/v1/clients?company_id=${encodeURIComponent(companyId.trim())}`);
}
```

---

## 📋 4. Pasos para Aplicar y Verificar

1. Copiar las modificaciones a los archivos locales `backend/app/api/v1/endpoints/clients.py` y `src/lib/api.ts`.
2. Transferir los archivos corregidos al servidor de producción vía `scp`.
3. Reiniciar el servicio backend en producción (`systemctl restart contaec-backend`).
4. Probar en el navegador / Postman:
   - `GET /api/v1/clients` (sin `company_id`) -> Retorna array de clientes o `[]` (HTTP 200).
   - `GET /api/v1/clients?company_id=undefined` -> Retorna `[]` (HTTP 200).
   - `GET /api/v1/clients?company_id=UUID_VALIDO` -> Retorna la lista de clientes (HTTP 200).
