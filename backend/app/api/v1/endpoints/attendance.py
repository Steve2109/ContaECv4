"""
ContaEC - Endpoints de Asistencia Laboral
Asistencia: Registro biométrico, importación, reportes, turnos
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import effective_owner_id
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.employee import Employee
from app.models.hr_extended2 import Asistencia, AsistenciaTipo
from app.models.hr_shift import TurnoRotativo, TurnoAsignacion
from app.models.user import User
from app.schemas.hr_extended2 import AsistenciaCreate, AsistenciaResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Nómina - Asistencia"])


# ==========================================
# Registro de Asistencia
# ==========================================


@router.post("/registro", response_model=AsistenciaCreate, status_code=status.HTTP_201_CREATED)
async def registrar_asistencia(
    data: AsistenciaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registrar entrada/salida de empleado (manual o biométrico).

    **Parámetros:**
    - `employee_id`: ID del empleado
    - `fecha`: Fecha del registro
    - `hora_entrada`: Hora de entrada (opcional)
    - `hora_salida`: Hora de salida (opcional)
    - `tipo`: Tipo de día (normal, descanso, festivo, etc.)

    **Retorna:**
    - Registro de asistencia creado
    """
    data.employee_id = clean_uuid_param(data.employee_id, "employee_id")
    # Verificar empleado
    result = await db.execute(
        select(Employee)
        .join(Company, Employee.company_id == Company.id)
        .where(
            Employee.id == data.employee_id,
            Company.user_id == effective_owner_id(current_user),
            Employee.is_active == True,
        )
    )
    empleado = result.scalars().first()
    if not empleado:
        raise HTTPException(404, "Empleado no encontrado")

    # Verificar duplicado
    existing = await db.execute(
        select(Asistencia).where(
            Asistencia.employee_id == data.employee_id,
            func.date(Asistencia.fecha) == func.date(data.fecha),
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe registro de asistencia para esta fecha",
        )

    # Crear registro
    asistencia = Asistencia(**data.model_dump())
    db.add(asistencia)
    await db.commit()
    await db.refresh(asistencia)

    return asistencia


@router.put("/registro/{asistencia_id}/salida")
async def registrar_salida(
    asistencia_id: str,
    hora_salida: datetime = Query(..., description="Hora de salida"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registrar hora de salida para un registro existente.

    **Parámetros:**
    - `asistencia_id`: ID del registro de asistencia
    - `hora_salida`: Hora de salida

    **Retorna:**
    - Registro actualizado con horas trabajadas calculadas
    """
    asistencia_id = validate_uuid(asistencia_id, "asistencia_id")
    result = await db.execute(
        select(Asistencia)
        .join(Employee, Asistencia.employee_id == Employee.id)
        .join(Company, Employee.company_id == Company.id)
        .where(
            Asistencia.id == asistencia_id,
            Company.user_id == effective_owner_id(current_user),
        )
    )
    asistencia = result.scalars().first()
    if not asistencia:
        raise HTTPException(404, "Registro no encontrado")

    # Actualizar hora de salida
    asistencia.hora_salida = hora_salida

    # Calcular horas trabajadas
    if asistencia.hora_entrada and asistencia.hora_salida:
        delta = asistencia.hora_salida - asistencia.hora_entrada
        horas_trabajadas = Decimal(str(delta.total_seconds() / 3600))

        # Descontar tiempo de descanso si aplica (1 hora default)
        descanso_minutes = 60
        if horas_trabajadas > Decimal(str(descanso_minutes / 60)):
            horas_trabajadas -= Decimal(str(descanso_minutes / 60))

        asistencia.horas_trabajadas = horas_trabajadas.quantize(Decimal("0.01"))

        # Calcular horas extras (si supera jornada normal)
        empleado = await db.get(Employee, asistencia.employee_id)
        jornada_normal = empleado.horas_trabajo_semanal / Decimal("5")  # Horas diarias

        if horas_trabajadas > jornada_normal:
            asistencia.horas_extras = (horas_trabajadas - jornada_normal).quantize(Decimal("0.01"))

    await db.commit()
    await db.refresh(asistencia)

    return {"message": "Salida registrada", "asistencia": asistencia}


# ==========================================
# Importación desde Dispositivo Biométrico
# ==========================================


@router.post("/import/biometrico")
async def importar_asistencia_biometrico(
    file: UploadFile = File(..., description="Archivo CSV/JSON del dispositivo biométrico"),
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Importar registros de asistencia desde dispositivo biométrico.

    Formatos soportados:
    - CSV: Cédula,Fecha,Hora_Entrada,Hora_Salida
    - JSON: [{"cedula": "...", "entradas": [...], "salidas": [...]}]

    **Parámetros:**
    - `file`: Archivo con datos del biométrico
    - `company_id`: ID de la empresa

    **Retorna:**
    - Resumen de importación (registros creados, actualizados, errores)
    """
    company_id = validate_uuid(company_id, "company_id")
    # Verificar empresa
    company = await _get_company_for_user(db, company_id, effective_owner_id(current_user))
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Leer archivo
    content = await file.read()
    file_content = content.decode("utf-8")

    registros_procesados = 0
    registros_creados = 0
    registros_error = 0
    errores = []

    # Parsear CSV (formato simple)
    lines = file_content.strip().split("\n")
    headers = lines[0].split(",") if lines else []

    for i, line in enumerate(lines[1:], start=1):
        try:
            values = line.split(",")
            if len(values) < 3:
                registros_error += 1
                errores.append(f"Línea {i}: Formato inválido")
                continue

            cedula = values[0].strip()
            fecha_str = values[1].strip()
            hora_entrada_str = values[2].strip() if len(values) > 2 else None
            hora_salida_str = values[3].strip() if len(values) > 3 else None

            # Buscar empleado por cédula
            emp_result = await db.execute(
                select(Employee).where(
                    Employee.cedula == cedula,
                    Employee.company_id == company_id,
                    Employee.is_active == True,
                )
            )
            empleado = emp_result.scalars().first()

            if not empleado:
                registros_error += 1
                errores.append(f"Línea {i}: Empleado con cédula {cedula} no encontrado")
                continue

            # Parsear fecha
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                registros_error += 1
                errores.append(f"Línea {i}: Fecha inválida {fecha_str}")
                continue

            # Verificar duplicado
            existing = await db.execute(
                select(Asistencia).where(
                    Asistencia.employee_id == empleado.id,
                    func.date(Asistencia.fecha) == func.date(fecha),
                )
            )
            if existing.scalars().first():
                registros_procesados += 1
                continue  # Saltar duplicados

            # Crear registro
            hora_entrada = None
            hora_salida = None

            if hora_entrada_str:
                try:
                    hora_entrada = datetime.strptime(
                        f"{fecha_str} {hora_entrada_str}", "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            if hora_salida_str:
                try:
                    hora_salida = datetime.strptime(
                        f"{fecha_str} {hora_salida_str}", "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            asistencia = Asistencia(
                employee_id=empleado.id,
                fecha=fecha,
                hora_entrada=hora_entrada,
                hora_salida=hora_salida,
                tipo=AsistenciaTipo.NORMAL,
            )

            # Calcular horas si hay entrada y salida
            if hora_entrada and hora_salida:
                delta = hora_salida - hora_entrada
                asistencia.horas_trabajadas = Decimal(
                    str(delta.total_seconds() / 3600)
                ).quantize(Decimal("0.01"))

            db.add(asistencia)
            registros_creados += 1
            registros_procesados += 1

        except Exception as e:
            registros_error += 1
            errores.append(f"Línea {i}: {str(e)}")

    await db.commit()

    return {
        "total_procesados": registros_procesados,
        "creados": registros_creados,
        "errores": registros_error,
        "detalle_errores": errores[:10],  # Máximo 10 errores
    }


# ==========================================
# Reportes de Asistencia
# ==========================================


@router.get("/resumen")
async def get_resumen_asistencia(
    company_id: str = Query(..., description="ID de la empresa"),
    employee_id: Optional[str] = Query(None, description="ID del empleado"),
    fecha_desde: datetime = Query(..., description="Fecha de inicio"),
    fecha_hasta: datetime = Query(..., description="Fecha de fin"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener resumen de asistencia por empleado en período.

    **Parámetros:**
    - `company_id`: ID de la empresa
    - `employee_id`: Filtrar por empleado (opcional)
    - `fecha_desde`: Fecha de inicio
    - `fecha_hasta`: Fecha de fin

    **Retorna:**
    - Resumen de días trabajados, horas, faltas, tardanzas
    """
    employee_id = clean_uuid_param(employee_id, "employee_id")
    company_id = validate_uuid(company_id, "company_id")
    company = await _get_company_for_user(db, company_id, effective_owner_id(current_user))
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Query base
    query = select(Asistencia).where(
        Asistencia.fecha >= fecha_desde,
        Asistencia.fecha <= fecha_hasta,
    )

    if employee_id:
        query = query.where(Asistencia.employee_id == employee_id)
    else:
        query = query.join(Employee).where(Employee.company_id == company_id)

    result = await db.execute(query)
    asistencias = result.scalars().all()

    # Agrupar por empleado
    resumen_por_empleado = {}
    for asistencia in asistencias:
        emp_id = asistencia.employee_id
        if emp_id not in resumen_por_empleado:
            resumen_por_empleado[emp_id] = {
                "empleado_id": emp_id,
                "dias_trabajados": 0,
                "dias_falta": 0,
                "dias_vacacion": 0,
                "dias_permiso": 0,
                "dias_enfermedad": 0,
                "horas_normales": Decimal("0.00"),
                "horas_extras": Decimal("0.00"),
                "tardanzas": 0,
            }

        resumen = resumen_por_empleado[emp_id]

        # Contar por tipo
        if asistencia.tipo == AsistenciaTipo.NORMAL:
            resumen["dias_trabajados"] += 1
        elif asistencia.tipo == AsistenciaTipo.VACACION:
            resumen["dias_vacacion"] += 1
        elif asistencia.tipo == AsistenciaTipo.PERMISO:
            resumen["dias_permiso"] += 1
        elif asistencia.tipo == AsistenciaTipo.ENFERMEDAD:
            resumen["dias_enfermedad"] += 1

        # Sumar horas
        resumen["horas_normales"] += asistencia.horas_trabajadas or Decimal("0.00")
        resumen["horas_extras"] += asistencia.horas_extras or Decimal("0.00")

        # Verificar tardanzas (si hay hora_entrada programada)
        if asistencia.hora_entrada:
            # Asumir hora máxima de entrada 8:00 AM (configurable)
            hora_maxima_entrada = asistencia.fecha.replace(hour=8, minute=15)
            if asistencia.hora_entrada > hora_maxima_entrada:
                resumen["tardanzas"] += 1

    return {
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "total_empleados": len(resumen_por_empleado),
        "resumen": list(resumen_por_empleado.values()),
    }


@router.get("/faltas")
async def listar_faltas(
    company_id: str = Query(..., description="ID de la empresa"),
    periodo_mes: int = Query(..., ge=1, le=12, description="Mes del período"),
    periodo_anio: int = Query(..., ge=2020, le=2100, description="Año del período"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar empleados con faltas injustificadas en el período.

    **Retorna:**
    - Lista de empleados con días de falta
    """
    company_id = validate_uuid(company_id, "company_id")
    company = await _get_company_for_user(db, company_id, effective_owner_id(current_user))
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Calcular rango de fechas del mes
    fecha_inicio = datetime(periodo_anio, periodo_mes, 1, tzinfo=timezone.utc)
    if periodo_mes == 12:
        fecha_fin = datetime(periodo_anio + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
    else:
        fecha_fin = datetime(periodo_anio, periodo_mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)

    # Obtener todos los empleados activos
    result = await db.execute(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.is_active == True,
        )
    )
    empleados = result.scalars().all()

    faltas = []
    for empleado in empleados:
        # Obtener asistencias del mes
        asist_result = await db.execute(
            select(Asistencia).where(
                Asistencia.employee_id == empleado.id,
                Asistencia.fecha >= fecha_inicio,
                Asistencia.fecha <= fecha_fin,
            )
        )
        asistencias = asist_result.scalars().all()

        # Días con registro
        dias_registrados = len(asistencias)

        # Días laborables estimados (lunes a viernes)
        dias_laborables = 0
        current = fecha_inicio
        while current <= fecha_fin:
            if current.weekday() < 5:  # Lunes=0, Viernes=4
                dias_laborables += 1
            current += timedelta(days=1)

        # Faltas = días laborables - días registrados
        faltas_count = dias_laborables - dias_registrados

        if faltas_count > 0:
            faltas.append({
                "empleado_id": empleado.id,
                "cedula": empleado.cedula,
                "nombre": empleado.nombre_completo,
                "departamento": empleado.departamento,
                "dias_laborables": dias_laborables,
                "dias_registrados": dias_registrados,
                "faltas": faltas_count,
            })

    return {
        "periodo": f"{periodo_mes:02d}/{periodo_anio}",
        "total_empleados": len(empleados),
        "empleados_con_faltas": len(faltas),
        "faltas": faltas,
    }


# ==========================================
# Turnos
# ==========================================


@router.post("/turnos/asignar")
async def asignar_turno(
    employee_id: str = Query(..., description="ID del empleado"),
    turno_id: str = Query(..., description="ID del turno"),
    fecha_asignacion: datetime = Query(..., description="Fecha de asignación"),
    es_recurrente: bool = Query(False, description="Si es turno recurrente"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Asignar turno rotativo a empleado.

    **Parámetros:**
    - `employee_id`: ID del empleado
    - `turno_id`: ID del turno rotativo
    - `fecha_asignacion`: Fecha de asignación
    - `es_recurrente`: Si el turno se repite

    **Retorna:**
    - Asignación creada
    """
    # Verificar empleado y turno
    employee = await db.get(Employee, employee_id)
    if not employee or employee.company_id != (
        await _get_company_for_user(db, employee.company_id, effective_owner_id(current_user))
    ).id:
        raise HTTPException(404, "Empleado no encontrado")

    turno = await db.get(TurnoRotativo, turno_id)
    if not turno:
        raise HTTPException(404, "Turno no encontrado")

    # Crear asignación
    asignacion = TurnoAsignacion(
        employee_id=employee_id,
        turno_id=turno_id,
        company_id=employee.company_id,
        user_id=current_user.id,
        fecha_asignacion=fecha_asignacion,
        es_recurrente=es_recurrente,
    )

    db.add(asignacion)
    await db.commit()
    await db.refresh(asignacion)

    return asignacion


@router.get("/turnos/semanal")
async def get_turnos_semanal(
    company_id: str = Query(..., description="ID de la empresa"),
    fecha_inicio: datetime = Query(..., description="Fecha de inicio de semana"),
    employee_id: Optional[str] = Query(None, description="ID del empleado"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener turnos asignados para la semana.

    **Retorna:**
    - Lista de asignaciones de turnos por día
    """
    employee_id = clean_uuid_param(employee_id, "employee_id")
    company_id = validate_uuid(company_id, "company_id")
    company = await _get_company_for_user(db, company_id, effective_owner_id(current_user))
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Calcular fin de semana (7 días)
    fecha_fin = fecha_inicio + timedelta(days=6)

    # Query
    query = select(TurnoAsignacion).where(
        TurnoAsignacion.company_id == company_id,
        TurnoAsignacion.fecha_asignacion >= fecha_inicio,
        TurnoAsignacion.fecha_asignacion <= fecha_fin,
    )

    if employee_id:
        query = query.where(TurnoAsignacion.employee_id == employee_id)

    result = await db.execute(query)
    asignaciones = result.scalars().all()

    # Formatear respuesta
    turnos_semanal = []
    for asignacion in asignaciones:
        turno = await db.get(TurnoRotativo, asignacion.turno_id)
        turnos_semanal.append({
            "fecha": asignacion.fecha_asignacion.isoformat(),
            "empleado_id": asignacion.employee_id,
            "empleado_nombre": asignacion.employee.nombre_completo,
            "turno_id": asignacion.turno_id,
            "turno_nombre": turno.nombre if turno else "N/A",
            "hora_entrada": turno.hora_entrada if turno else None,
            "hora_salida": turno.hora_salida if turno else None,
            "estado": asignacion.estado,
        })

    return {
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat(),
        "total_asignaciones": len(turnos_semanal),
        "asignaciones": turnos_semanal,
    }


# ==========================================
# Funciones auxiliares
# ==========================================


async def _get_company_for_user(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> Optional[Company]:
    """Obtiene una empresa verificando que pertenezca al usuario"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
            Company.is_active == True,
        )
    )
    return result.scalars().first()