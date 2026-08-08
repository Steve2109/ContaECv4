"""
ContaEC - Validaciones compartidas

Helpers de validación de UUID para endpoints.

Evitan el error 500 producido cuando un string no válido
(p.ej. "undefined", "null", "abc") se compara contra una columna
tipo UUID de PostgreSQL, lo que genera un DataError no controlado.
"""
import uuid

from fastapi import HTTPException, status


def validate_uuid(value: str | None, param_name: str) -> str:
    """
    Valida que un valor sea un UUID válido.

    Es seguro ante `None`/vacío: en lugar de fallar con un AttributeError
    (que generaría un 500), responde con un 400 claro.

    Raises:
        HTTPException: 400 si el valor no es un UUID válido
    """
    if not value or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El parámetro {param_name} debe ser un UUID válido.",
        )
    cleaned = value.strip()
    try:
        uuid.UUID(cleaned)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El parámetro {param_name} debe ser un UUID válido.",
        )
    return cleaned


def clean_uuid_param(value: str | None, param_name: str) -> str | None:
    """
    Normaliza un parámetro ID opcional (query filter o campo del body).

    - `None`, vacío, `"undefined"` o `"null"` -> devuelve `None`
      (el filtro/relación simplemente se omite).
    - UUID válido -> devuelve el string limpio (sin espacios).
    - Cualquier otro valor -> HTTPException 400 (en lugar de un DataError 500).

    Uso típico al inicio del endpoint:
        product_id = clean_uuid_param(product_id, "product_id")
        data.client_id = clean_uuid_param(data.client_id, "client_id")
    """
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned in ("", "undefined", "null"):
        return None
    return validate_uuid(cleaned, param_name)


def clean_company_id(company_id: str | None) -> str | None:
    """
    Normaliza el parámetro opcional `company_id` de los endpoints de listado.

    - `None`, vacío, `"undefined"` o `"null"` -> devuelve `None`
      (el filtro de empresa simplemente se omite).
    - UUID válido -> devuelve el string limpio (sin espacios).
    - Cualquier otro valor -> HTTPException 400 (en lugar de un DataError 500).

    Uso típico al inicio del endpoint:
        company_id = clean_company_id(company_id)
    """
    return clean_uuid_param(company_id, "company_id")
