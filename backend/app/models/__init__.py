"""
ContaEC - Modelos de la base de datos
Importa todos los modelos para facilitar el acceso y asegurar
que SQLAlchemy los registre en Base.metadata
"""
from app.models.user import (
    EnvironmentMode,
    Language,
    LicenseType,
    SmtpProtocol,
    Theme,
    User,
    UserConfig,
)
from app.models.company import (
    Company,
    ContribuyenteRimpe,
    Establishment,
    ObligadoContabilidad,
    TipoAmbiente,
    TipoEmision,
)
from app.models.client import (
    Client,
    TipoIdentificacion,
)
from app.models.product import (
    Product,
    ProductoTipo,
)
from app.models.comprobante import (
    Comprobante,
    ComprobanteDetalle,
    ComprobanteEstado,
    ComprobanteTipo,
)
from app.models.proforma import (
    Proforma,
    ProformaDetalle,
    ProformaEstado,
)
from app.models.kardex import (
    Kardex,
    KardexTipoMovimiento,
)
from app.models.employee import (
    Employee,
    EstadoEmpleado,
    TipoContrato,
    TipoPago,
)
from app.models.payroll import (
    EstadoRol,
    RolPago,
    RolPagoDetalle,
)
from app.models.audit_log import (
    AuditLog,
)
from app.models.email_template import (
    EmailTemplate,
)
from app.models.email_log import (
    EmailLog,
    EmailLogEstado,
    EmailLogTipo,
)
from app.models.smtp_profile import (
    SMTPProfile,
    SmtpConnectionProtocol,
    SmtpProviderType,
)
from app.models.supplier import (
    Supplier,
)
from app.models.purchase import (
    CuentaPorPagar,
    OrdenCompra,
    OrdenCompraDetalle,
    RecepcionMercaderia,
    RecepcionMercaderiaDetalle,
    RetencionCompra,
)
from app.models.warehouse import (
    TransferEstado,
    Warehouse,
    WarehouseLocation,
    WarehouseTransfer,
    WarehouseTransferDetalle,
)
from app.models.pos import (
    ArqueoTipo,
    CajaEstado,
    POSArqueo,
    POSCashSession,
    POSTicket,
    POSTicketDetalle,
    TicketEstado,
    TipoVenta,
)
from app.models.budget import (
    PresupuestoAlerta,
    PresupuestoAnual,
    PresupuestoCuenta,
    PresupuestoEjecucionMensual,
    PresupuestoEstado,
    TipoAlertaPresupuesto,
    TipoCuenta,
)
from app.models.project import (
    Proyecto,
    ProyectoCosto,
    ProyectoEstado,
    ProyectoRecurso,
    ProyectoTarea,
    ProyectoTimesheet,
    TareaEstado,
    TareaPrioridad,
    TipoRecurso,
)
from app.models.integration import (
    BancoTipoCuenta,
    CuentaBancaria,
    ConciliacionEstado,
    ConnectorEstado,
    EcommerceConnector,
    EcommercePlataforma,
    EcommerceSyncLog,
    ExtractoBancario,
    ExtractoEstado,
    MovimientoBancario,
    MovimientoTipo,
    SyncEstado,
)
from app.models.ml_ai import (
    ChatbotEstado,
    FraudeEstado,
    FraudeSeveridad,
    MLAlertaFraude,
    MLCategoriaRegla,
    MLChatbotMensaje,
    MLChatbotSesion,
    MLPrediccion,
    MLRecomendacion,
    PrediccionEstado,
    PrediccionTipo,
    RecomendacionEstado,
    RecomendacionTipo,
)
from app.models.accounting import (
    AsientoContable,
    AsientoDetalle,
    AsientoEstado,
    CuentaContable,
    CuentaPorCobrar,
    CuentaPorCobrarEstado,
    NaturalezaCuenta,
    Pago,
    PagoEstado,
    PagoTipo,
    PeriodoFiscal,
    PeriodoFiscalEstado,
    TipoAsiento,
    TipoCuentaContable,
)
from app.models.user_company_role import (
    CompanyRole,
    Permission,
    UserCompanyRole,
)
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationType,
)
from app.models.hr_extended import (
    Anticipo,
    AnticipoEstado,
    Contrato,
    ContratoEstado,
    DecimoEstado,
    DecimoPago,
    DecimoTipo,
    RubroCategoria,
    RubroEmpleado,
    RubroTipo,
)
from app.models.crm import (
    ActivityStatus,
    ActivityType,
    AutomationTriggerType,
    CRMActivity,
    CRMAutomation,
    CRMContactSegment,
    CRMContactSegmentMember,
    CRMLead,
    CRMOpportunity,
    CRMPipeline,
    CRMPipelineStage,
    LeadSource,
    LeadStatus,
    OpportunityStatus,
    SegmentType,
)
from app.models.hr_extended2 import (
    Asistencia,
    AsistenciaTipo,
    CargaFamiliar,
    EvaluacionDesempeno,
    EvaluacionEstado,
    LiquidacionEstado,
    LiquidacionLaboral,
    LiquidacionTipo,
    ParentescoTipo,
    UtilidadesDetalle,
    UtilidadesEstado,
    UtilidadesParticipacion,
)
from app.models.hr_contract import (
    ContratoLaboral,
    ContratoEstado,
    ContratoTipo,
)
from app.models.hr_vacation import (
    VacacionesPeriodo,
    VacacionesSolicitud,
    VacacionesHistorial,
    VacacionesEstado,
)
from app.models.hr_loan import (
    PrestamoEmpleado,
    PrestamoDetalle,
    PrestamoEstado,
    PrestamoTipo,
)
from app.models.hr_history import (
    HistorialLaboral,
    MovimientoTipo,
    MovimientoEstado,
)
from app.models.hr_shift import (
    TurnoRotativo,
    TurnoAsignacion,
    TurnoEstado,
    TurnoTipo,
)

__all__ = [
    # Usuario
    "User",
    "UserConfig",
    "LicenseType",
    "Language",
    "Theme",
    "EnvironmentMode",
    "SmtpProtocol",
    # Empresa
    "Company",
    "Establishment",
    "TipoAmbiente",
    "TipoEmision",
    "ObligadoContabilidad",
    "ContribuyenteRimpe",
    # Cliente
    "Client",
    "TipoIdentificacion",
    # Producto/Servicio
    "Product",
    "ProductoTipo",
    # Comprobante Electrónico
    "Comprobante",
    "ComprobanteDetalle",
    "ComprobanteEstado",
    "ComprobanteTipo",
    # Proforma
    "Proforma",
    "ProformaDetalle",
    "ProformaEstado",
    # Kardex / Inventario
    "Kardex",
    "KardexTipoMovimiento",
    # Recursos Humanos
    "Employee",
    "EstadoEmpleado",
    "TipoContrato",
    "TipoPago",
    # Nómina / Rol de Pago
    "RolPago",
    "RolPagoDetalle",
    "EstadoRol",
    # Auditoría
    "AuditLog",
    # Plantillas de Correo
    "EmailTemplate",
    "EmailLog",
    "EmailLogTipo",
    "EmailLogEstado",
    # Perfiles SMTP
    "SMTPProfile",
    "SmtpProviderType",
    "SmtpConnectionProtocol",
    # Proveedor
    "Supplier",
    # Compras
    "OrdenCompra",
    "OrdenCompraDetalle",
    "RecepcionMercaderia",
    "RecepcionMercaderiaDetalle",
    "CuentaPorPagar",
    "RetencionCompra",
    # Multi-Almacén y Logística
    "Warehouse",
    "WarehouseLocation",
    "WarehouseTransfer",
    "WarehouseTransferDetalle",
    "TransferEstado",
    # Punto de Venta (POS)
    "POSCashSession",
    "POSTicket",
    "POSTicketDetalle",
    "POSArqueo",
    "CajaEstado",
    "TicketEstado",
    "TipoVenta",
    "ArqueoTipo",
    # Presupuestos y Control Presupuestario
    "PresupuestoAnual",
    "PresupuestoCuenta",
    "PresupuestoEjecucionMensual",
    "PresupuestoAlerta",
    "PresupuestoEstado",
    "TipoCuenta",
    "TipoAlertaPresupuesto",
    # Proyectos y Servicios
    "Proyecto",
    "ProyectoTarea",
    "ProyectoRecurso",
    "ProyectoTimesheet",
    "ProyectoCosto",
    "ProyectoEstado",
    "TareaEstado",
    "TareaPrioridad",
    "TipoRecurso",
    # Integraciones
    "CuentaBancaria",
    "ExtractoBancario",
    "MovimientoBancario",
    "BancoTipoCuenta",
    "ExtractoEstado",
    "MovimientoTipo",
    "ConciliacionEstado",
    "EcommerceConnector",
    "EcommerceSyncLog",
    "EcommercePlataforma",
    "ConnectorEstado",
    "SyncEstado",
    # Machine Learning / IA
    "MLPrediccion",
    "PrediccionTipo",
    "PrediccionEstado",
    "MLAlertaFraude",
    "FraudeSeveridad",
    "FraudeEstado",
    "MLChatbotSesion",
    "MLChatbotMensaje",
    "ChatbotEstado",
    "MLRecomendacion",
    "RecomendacionTipo",
    "RecomendacionEstado",
    "MLCategoriaRegla",
    # RRHH Extendido
    "Contrato",
    "ContratoEstado",
    "DecimoPago",
    "DecimoTipo",
    "DecimoEstado",
    "Anticipo",
    "AnticipoEstado",
    "RubroEmpleado",
    "RubroTipo",
    "RubroCategoria",
    # Contabilidad Core
    "CuentaContable",
    "TipoCuentaContable",
    "NaturalezaCuenta",
    "AsientoContable",
    "AsientoDetalle",
    "AsientoEstado",
    "TipoAsiento",
    "CuentaPorCobrar",
    "CuentaPorCobrarEstado",
    "Pago",
    "PagoTipo",
    "PagoEstado",
    "PeriodoFiscal",
    "PeriodoFiscalEstado",
    # Notificaciones del Sistema
    "Notification",
    "NotificationType",
    "NotificationCategory",
    "NotificationPriority",
    # Roles por Empresa
    "UserCompanyRole",
    "CompanyRole",
    "Permission",
    # CRM Avanzado
    "CRMPipeline",
    "CRMPipelineStage",
    "CRMLead",
    "LeadSource",
    "LeadStatus",
    "CRMOpportunity",
    "OpportunityStatus",
    "CRMActivity",
    "ActivityType",
    "ActivityStatus",
    "CRMContactSegment",
    "CRMContactSegmentMember",
    "SegmentType",
    "CRMAutomation",
    "AutomationTriggerType",
    # RRHH Extendido Fase 5
    "CargaFamiliar",
    "ParentescoTipo",
    "EvaluacionDesempeno",
    "EvaluacionEstado",
    "Asistencia",
    "AsistenciaTipo",
    "LiquidacionLaboral",
    "LiquidacionTipo",
    "LiquidacionEstado",
    "UtilidadesParticipacion",
    "UtilidadesEstado",
    "UtilidadesDetalle",
    # RRHH Fase 1 - Contratos, Vacaciones, Préstamos, Historial, Turnos
    "ContratoLaboral",
    "ContratoEstado",
    "ContratoTipo",
    "VacacionesPeriodo",
    "VacacionesSolicitud",
    "VacacionesHistorial",
    "VacacionesEstado",
    "PrestamoEmpleado",
    "PrestamoDetalle",
    "PrestamoEstado",
    "PrestamoTipo",
    "HistorialLaboral",
    "MovimientoTipo",
    "MovimientoEstado",
    "TurnoRotativo",
    "TurnoAsignacion",
    "TurnoEstado",
    "TurnoTipo",
]
