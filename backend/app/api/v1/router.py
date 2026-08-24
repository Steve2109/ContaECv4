"""
ContaEC - Router principal API v1
Agrupa todos los endpoints de la versión 1
"""
from fastapi import APIRouter, Depends

from app.api.v1.endpoints import auth, admin, companies, config, licenses, backup, uploads, comprobantes, products, clients, proformas, audit, email_templates, email_receiver, smtp_profiles, suppliers, purchases, warehouses, ubicaciones, pos, bi, budgets, projects, integrations, ml_ai, accounting, notifications, user_roles, crm, cuentas_pagar, employees, payroll, payroll_reports, payroll_exports, attendance, exports, imports, kardex, volatile, email_logs, subaccounts
from app.core.permissions import require_modules

api_router = APIRouter(prefix="/api/v1")

# Autenticación
api_router.include_router(auth.router)

# Administración
api_router.include_router(admin.router)

# Empresas
api_router.include_router(companies.router)

# Sub-Cuentas (cuentas de empleados con acceso limitado)
api_router.include_router(subaccounts.router, dependencies=[Depends(require_modules("configuracion"))])

# Configuración de usuario
api_router.include_router(config.router, dependencies=[Depends(require_modules("configuracion"))])

# Licencias
api_router.include_router(licenses.router)

# Backup y restauración
api_router.include_router(backup.router, dependencies=[Depends(require_modules("configuracion"))])

# Subida de archivos con escaneo de malware
api_router.include_router(uploads.router)

# Comprobantes electrónicos
api_router.include_router(comprobantes.router, dependencies=[Depends(require_modules("facturacion"))])

# Productos/Servicios
api_router.include_router(products.router, dependencies=[Depends(require_modules("inventario", "facturacion"))])

# Clientes
api_router.include_router(clients.router, dependencies=[Depends(require_modules("clientes", "facturacion"))])

# Proformas
api_router.include_router(proformas.router, dependencies=[Depends(require_modules("facturacion"))])

# Auditoría
api_router.include_router(audit.router)

# Plantillas de Correo
api_router.include_router(email_templates.router, dependencies=[Depends(require_modules("configuracion"))])

# Recepción de Correo
api_router.include_router(email_receiver.router, dependencies=[Depends(require_modules("configuracion"))])

# Perfiles SMTP
api_router.include_router(smtp_profiles.router, dependencies=[Depends(require_modules("configuracion"))])

# Proveedores
api_router.include_router(suppliers.router, dependencies=[Depends(require_modules("proveedores", "compras"))])

# Compras (Órdenes de compra, Recepciones, Cuentas por pagar, Retenciones)
api_router.include_router(purchases.router, dependencies=[Depends(require_modules("compras"))])

# Multi-Almacén y Logística
api_router.include_router(warehouses.router, dependencies=[Depends(require_modules("inventario"))])

# Ubicaciones Físicas de Almacén
api_router.include_router(ubicaciones.router, dependencies=[Depends(require_modules("inventario"))])

# Punto de Venta (POS)
api_router.include_router(pos.router, dependencies=[Depends(require_modules("pos", "facturacion"))])

# Business Intelligence y Dashboards
api_router.include_router(bi.router, dependencies=[Depends(require_modules("bi", "dashboard"))])

# Presupuestos y Control Presupuestario
api_router.include_router(budgets.router, dependencies=[Depends(require_modules("contabilidad", "presupuestos"))])

# Proyectos y Servicios
api_router.include_router(projects.router, dependencies=[Depends(require_modules("proyectos"))])

# Integraciones (Bancaria + E-Commerce)
api_router.include_router(integrations.router, dependencies=[Depends(require_modules("integraciones"))])

# Machine Learning / Inteligencia Artificial
api_router.include_router(ml_ai.router, dependencies=[Depends(require_modules("ml_ai"))])

# Contabilidad Core (Plan de Cuentas, Asientos, CxC, Pagos, Períodos Fiscales)
api_router.include_router(accounting.router, dependencies=[Depends(require_modules("contabilidad"))])

# Notificaciones del Sistema
api_router.include_router(notifications.router)

# Roles de Usuario por Empresa
api_router.include_router(user_roles.router)

# CRM Avanzado (Pipeline, Oportunidades, Seguimiento)
api_router.include_router(crm.router, dependencies=[Depends(require_modules("crm"))])

# Cuentas por Pagar (gestión de pagos, renegociación, exportación)
api_router.include_router(cuentas_pagar.router, dependencies=[Depends(require_modules("compras"))])

# Empleados (RRHH)
api_router.include_router(employees.router, dependencies=[Depends(require_modules("rh"))])

# Nómina / Rol de Pago
api_router.include_router(payroll.router, dependencies=[Depends(require_modules("rh"))])

# Nómina - Reportes SRI (RDEP, Anexos IESS, SUT XIII-XIV, IR)
api_router.include_router(payroll_reports.router, dependencies=[Depends(require_modules("rh"))])

# Nómina - Exportaciones (Bancos, PDF/Excel roles)
api_router.include_router(payroll_exports.router, dependencies=[Depends(require_modules("rh"))])

# Nómina - Asistencia y Turnos
api_router.include_router(attendance.router, dependencies=[Depends(require_modules("rh"))])

# Exportaciones
api_router.include_router(exports.router, dependencies=[Depends(require_modules("inventario"))])

# Importaciones
api_router.include_router(imports.router, dependencies=[Depends(require_modules("inventario"))])

# Kardex
api_router.include_router(kardex.router, dependencies=[Depends(require_modules("inventario"))])

# Almacenamiento Volátil
api_router.include_router(volatile.router)

# Logs de Correo
api_router.include_router(email_logs.router, dependencies=[Depends(require_modules("configuracion"))])
