"""
ContaEC - Endpoints de Empleados (RRHH)
CRUD de empleados, cese y listado de departamentos
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import effective_owner_id
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.employee import Employee, EstadoEmpleado
from app.models.user import User
from app.schemas.employee import (
    DepartmentResponse,
    EmployeeCese,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employees", tags=["Empleados - RRHH"])


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


async def _get_employee_for_user(
    db: AsyncSession,
    employee_id: str,
    user_id: str,
) -> Employee:
    """
    Obtiene un empleado verificando que pertenezca a una empresa del usuario.

    Raises:
        HTTPException: Si el empleado no existe o no pertenece al usuario
    """
    result = await db.execute(
        select(Employee)
        .join(Company, Employee.company_id == Company.id)
        .where(
            Employee.id == employee_id,
            Company.user_id == user_id,
            Employee.is_active == True,
        )
    )
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado.",
        )
    return employee


# ==========================================
# Endpoints CRUD
# ==========================================

@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo empleado para una empresa del usuario.

    Verifica que la empresa pertenezca al usuario y que no exista
    otro empleado con la misma cédula en la empresa.

    Valida el límite de empleados según el plan de licencia.
    """
    data.company_id = validate_uuid(data.company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Validar límite de empleados según licencia
    from app.core.utils import get_license_limits

    limits = get_license_limits(current_user)
    max_employees = limits['max_employees']

    # Contar empleados activos en la empresa
    result = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.company_id == data.company_id,
            Employee.is_active == True
        )
    )
    current_count = result.scalar() or 0

    if current_count >= max_employees:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Límite de empleados alcanzado en esta empresa. Tu plan actual permite {max_employees} empleado(s). "
                   f"Contacta a soporte para actualizar tu licencia."
        )

    # Verificar que no exista un empleado con la misma cédula en la empresa
    result = await db.execute(
        select(Employee).where(
            Employee.company_id == data.company_id,
            Employee.cedula == data.cedula,
            Employee.is_active == True,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un empleado con la cédula '{data.cedula}' en esta empresa.",
        )

    # Calcular sueldo diario
    from decimal import Decimal
    sueldo_diario = (data.sueldo_mensual / Decimal("30.00")).quantize(Decimal("0.01"))

    # Crear empleado
    employee = Employee(
        company_id=data.company_id,
        user_id=current_user.id,
        cedula=data.cedula,
        apellidos=data.apellidos,
        nombres=data.nombres,
        fecha_nacimiento=data.fecha_nacimiento,
        genero=data.genero,
        estado_civil=data.estado_civil,
        direccion=data.direccion,
        telefono=data.telefono,
        email=data.email,
        cargo=data.cargo,
        departamento=data.departamento,
        tipo_contrato=data.tipo_contrato,
        fecha_ingreso=data.fecha_ingreso,
        tipo_pago=data.tipo_pago,
        sueldo_mensual=data.sueldo_mensual,
        sueldo_diario=sueldo_diario,
        horas_trabajo_semanal=data.horas_trabajo_semanal,
        fondo_reserva=data.fondo_reserva,
        iess_afiliado=data.iess_afiliado,
        iess_numero_seguro=data.iess_numero_seguro,
        banco=data.banco,
        tipo_cuenta=data.tipo_cuenta,
        numero_cuenta=data.numero_cuenta,
    )
    db.add(employee)
    await db.flush()

    logger.info(
        f"Empleado creado: cedula={data.cedula}, "
        f"empresa={data.company_id}"
    )

    return EmployeeResponse.model_validate(employee)


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(
    company_id: str | None = None,
    estado: str | None = None,
    departamento: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar empleados de las empresas del usuario.

    Opcionalmente filtrado por empresa, estado, departamento y estado activo.
    """
    company_id = clean_company_id(company_id)
    # Consulta base: empleados de empresas del usuario
    query = (
        select(Employee)
        .join(Company, Employee.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    # Filtro de empresa
    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(Employee.company_id == company_id)

    # Filtro de estado
    if estado:
        query = query.where(Employee.estado == estado)

    # Filtro de departamento
    if departamento:
        query = query.where(Employee.departamento == departamento)

    # Filtro de estado activo
    if is_active is not None:
        query = query.where(Employee.is_active == is_active)

    # Ordenar por apellidos y paginar
    query = query.order_by(Employee.apellidos, Employee.nombres).offset(skip).limit(limit)

    result = await db.execute(query)
    employees = result.scalars().all()

    return [EmployeeResponse.model_validate(e) for e in employees]


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar departamentos de una empresa con cantidad de empleados.

    Retorna los departamentos únicos con el número de empleados activos en cada uno.
    """
    company_id = validate_uuid(company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    # Consultar departamentos con conteo de empleados
    result = await db.execute(
        select(
            Employee.departamento,
            func.count(Employee.id).label("total_empleados"),
        )
        .where(
            Employee.company_id == company_id,
            Employee.is_active == True,
            Employee.estado == EstadoEmpleado.ACTIVO,
            Employee.departamento != None,
            Employee.departamento != "",
        )
        .group_by(Employee.departamento)
        .order_by(Employee.departamento)
    )

    departments = []
    for row in result:
        departments.append(DepartmentResponse(
            nombre=row.departamento,
            total_empleados=row.total_empleados,
        ))

    return departments


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un empleado específico por su ID"""
    employee_id = validate_uuid(employee_id, "employee_id")
    employee = await _get_employee_for_user(db, employee_id, current_user.id)
    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar datos de un empleado"""
    employee_id = validate_uuid(employee_id, "employee_id")
    employee = await _get_employee_for_user(db, employee_id, current_user.id)

    # Actualizar campos proporcionados
    update_data = data.model_dump(exclude_unset=True)

    # Si se actualiza el sueldo mensual, recalcular el diario
    from decimal import Decimal
    if "sueldo_mensual" in update_data:
        nuevo_sueldo = update_data["sueldo_mensual"]
        if nuevo_sueldo is not None:
            update_data["sueldo_diario"] = (Decimal(str(nuevo_sueldo)) / Decimal("30.00")).quantize(Decimal("0.01"))

    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.flush()

    logger.info(f"Empleado actualizado: cedula={employee.cedula}")

    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactivar un empleado (eliminación lógica).

    No elimina el registro, solo marca is_active=False y
    cambia el estado a 'cese'.
    """
    employee_id = validate_uuid(employee_id, "employee_id")
    employee = await _get_employee_for_user(db, employee_id, current_user.id)

    # Eliminación lógica
    employee.is_active = False
    employee.estado = EstadoEmpleado.CESE
    await db.flush()

    logger.info(f"Empleado desactivado: cedula={employee.cedula}")

    return {"message": "Empleado desactivado exitosamente."}


@router.post("/{employee_id}/cese", response_model=EmployeeResponse)
async def record_cese(
    employee_id: str,
    data: EmployeeCese,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registrar el cese de un empleado.

    Registra la fecha de salida y cambia el estado a 'cese'.
    Calcula las provisiones pendientes al momento del cese.
    """
    employee_id = validate_uuid(employee_id, "employee_id")
    employee = await _get_employee_for_user(db, employee_id, current_user.id)

    if employee.estado == EstadoEmpleado.CESE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El empleado ya se encuentra en estado de cese.",
        )

    # Registrar cese
    employee.fecha_salida = data.fecha_salida
    employee.estado = EstadoEmpleado.CESE
    employee.is_active = False

    await db.flush()

    logger.info(
        f"Cese registrado: cedula={employee.cedula}, "
        f"fecha_salida={data.fecha_salida}"
    )

    return EmployeeResponse.model_validate(employee)
