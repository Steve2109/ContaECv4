# Graph Report - .  (2026-07-17)

## Corpus Check
- 253 files · ~390,015 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4861 nodes · 10923 edges · 261 communities (182 shown, 79 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1274 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- API Routes and Router
- SQLAlchemy Models Base
- Pydantic Schemas
- Accounting Module
- Comprobantes SRI Module
- HR Payroll Module
- HR Employee Models
- Auth and Security
- Inventory and Products
- CRM Module
- POS Module
- Email Templates and Logs
- Warehouse Management
- Projects Module
- Purchases and Suppliers
- Module Group 15
- Module Group 16
- Module Group 17
- Module Group 18
- Module Group 19
- Module Group 20
- Module Group 21
- Module Group 22
- Module Group 23
- Module Group 24
- Module Group 25
- Module Group 26
- Module Group 27
- Module Group 28
- Module Group 29
- Module Group 30
- Module Group 31
- Module Group 32
- Module Group 33
- Module Group 34
- Module Group 35
- Module Group 36
- Module Group 37
- Module Group 38
- Module Group 39
- Module Group 40
- Module Group 41
- Module Group 42
- Module Group 43
- Module Group 44
- Module Group 45
- Module Group 46
- Module Group 47
- Module Group 48
- Module Group 49
- Module Group 50
- Module Group 51
- Module Group 52
- Module Group 53
- Module Group 54
- Module Group 55
- Module Group 56
- Module Group 57
- Module Group 58
- Module Group 59
- Module Group 60
- Module Group 61
- Module Group 62
- Module Group 63
- Module Group 64
- Module Group 65
- Module Group 66
- Module Group 67
- Module Group 68
- Module Group 69
- Module Group 70
- Module Group 71
- Module Group 72
- Module Group 73
- Module Group 74
- Module Group 75
- Module Group 76
- Module Group 77
- Module Group 78
- Module Group 79
- Module Group 80
- Module Group 81
- Module Group 82
- Module Group 83
- Module Group 84
- Module Group 85
- Module Group 86
- Module Group 87
- Module Group 88
- Module Group 89
- Module Group 90
- Module Group 91
- Module Group 92
- Module Group 93
- Module Group 94
- Module Group 95
- Module Group 96
- Module Group 97
- Module Group 98
- Module Group 99
- Module Group 100
- Module Group 101
- Module Group 102
- Module Group 103
- Module Group 104
- Module Group 105
- Module Group 106
- Module Group 107
- Module Group 108
- Module Group 109
- Module Group 110
- Module Group 111
- Module Group 112
- Module Group 113
- Module Group 114
- Module Group 115
- Module Group 116
- Module Group 117
- Module Group 118
- Module Group 119
- Module Group 120
- Module Group 121
- Module Group 122
- Module Group 123
- Module Group 124
- Module Group 125
- Module Group 126
- Module Group 127
- Module Group 128
- Module Group 129
- Module Group 130
- Module Group 131
- Module Group 132
- Module Group 133
- Module Group 134
- Module Group 135
- Module Group 136
- Module Group 137
- Module Group 138
- Module Group 139
- Module Group 140
- Module Group 141
- Module Group 142
- Module Group 143
- Module Group 144
- Module Group 145
- Module Group 146
- Module Group 147
- Module Group 148
- Module Group 149
- Module Group 150
- Module Group 151
- Module Group 152
- Module Group 153
- Module Group 154
- Module Group 155
- Module Group 156
- Module Group 157
- Module Group 158
- Module Group 159
- Module Group 160
- Module Group 161
- Module Group 162
- Module Group 163
- Module Group 164
- Module Group 165
- Module Group 166
- Module Group 167
- Module Group 168
- Module Group 169
- Module Group 170
- Module Group 171
- Module Group 172
- Module Group 173
- Module Group 175
- Module Group 176
- Module Group 177
- Module Group 178
- Module Group 179
- Module Group 180
- Module Group 181
- Module Group 182
- Module Group 183
- Module Group 184
- Module Group 185
- Module Group 186
- Module Group 187
- Module Group 188
- Module Group 189
- Module Group 190
- Module Group 191
- Module Group 192
- Module Group 193
- Module Group 194
- Module Group 195
- Module Group 196
- Module Group 197
- Module Group 198
- Module Group 199
- Module Group 200
- Module Group 201
- Module Group 202
- Module Group 203
- Module Group 204
- Module Group 205
- Module Group 206
- Module Group 207
- Module Group 208
- Module Group 209
- Module Group 210
- Module Group 211
- Module Group 212
- Module Group 213
- Module Group 214
- Module Group 215
- Module Group 216
- Module Group 217
- Module Group 218
- Module Group 219
- Module Group 220
- Module Group 221
- Module Group 222
- Module Group 223
- Module Group 224
- Module Group 225
- Module Group 226
- Module Group 227
- Module Group 228
- Module Group 229
- Module Group 230
- Module Group 231
- Module Group 232
- Module Group 233
- Module Group 234
- Module Group 235
- Module Group 236
- Module Group 237
- Module Group 238
- Module Group 239
- Module Group 240
- Module Group 241
- Module Group 242
- Module Group 243
- Module Group 244
- Module Group 247
- Module Group 248
- Module Group 254
- Module Group 255
- Module Group 256
- Module Group 257
- Module Group 258
- Module Group 259
- Module Group 260

## God Nodes (most connected - your core abstractions)
1. `cn()` - 226 edges
2. `Base` - 181 edges
3. `Company` - 132 edges
4. `log_action()` - 130 edges
5. `apiGet()` - 125 edges
6. `apiPost()` - 100 edges
7. `apiPut()` - 47 edges
8. `_get_company_for_user()` - 44 edges
9. `Employee` - 43 edges
10. `apiDelete()` - 34 edges

## Surprising Connections (you probably didn't know these)
- `FastAPI + SQLAlchemy + Alembic + Pydantic` --conceptually_related_to--> `ContaEC - Sistema Contable y Facturacion Electronica del Ecuador`  [INFERRED]
  backend/requirements.txt → README.md
- `CalendarDayButton()` --references--> `react`  [EXTRACTED]
  src/components/ui/calendar.tsx → package.json
- `Carousel()` --references--> `react`  [EXTRACTED]
  src/components/ui/carousel.tsx → package.json
- `useCarousel()` --references--> `react`  [EXTRACTED]
  src/components/ui/carousel.tsx → package.json
- `ChartContainer()` --references--> `react`  [EXTRACTED]
  src/components/ui/chart.tsx → package.json

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **SRI Electronic Invoicing Subsystem** — upload_ficha_tecnica_sri_v232, upload_ficha_tecnica_xml_format, upload_ficha_tecnica_xades_bes, upload_ficha_tecnica_mod11, upload_ficha_tecnica_comprobant_types, upload_ficha_tecnica_sri_soap, upload_ficha_tecnica_ride_format [INFERRED 0.85]

## Communities (261 total, 79 thin omitted)

### Community 0 - "API Routes and Router"
Cohesion: 0.02
Nodes (183): ContaECMLAI(), ESTADO_ALERTA_COLORS, ESTADO_PREDICCION_COLORS, ESTADO_RECOMENDACION_COLORS, SEVERIDAD_COLORS, TIPO_PREDICCION_COLORS, TIPO_RECOMENDACION_COLORS, apiDelete() (+175 more)

### Community 1 - "SQLAlchemy Models Base"
Cohesion: 0.03
Nodes (117): ContaECAudit(), formatDate(), ContaECInventory(), formatCurrency(), KardexTab(), StockTab(), ContaECPurchases(), CuentasTab() (+109 more)

### Community 2 - "Pydantic Schemas"
Cohesion: 0.03
Nodes (83): AccordionContent(), AccordionItem(), AccordionTrigger(), AlertDialog(), AlertDialogAction(), AlertDialogCancel(), AlertDialogContent(), AlertDialogDescription() (+75 more)

### Community 3 - "Accounting Module"
Cohesion: 0.04
Nodes (81): Message, User, AppView, ContaECAdmin(), ContaECAdminProps, AdminDashboardView(), LicenseView(), NavItem (+73 more)

### Community 4 - "Comprobantes SRI Module"
Cohesion: 0.05
Nodes (101): list_employees(), Listar empleados de las empresas del usuario.      Opcionalmente filtrado por em, approve_liquidacion(), approve_payroll(), approve_utilidades(), _calcular_detalle_empleado(), calcular_impuesto_renta(), _calcular_valor_hora() (+93 more)

### Community 5 - "HR Payroll Module"
Cohesion: 0.04
Nodes (68): ComprobanteDetailView(), ComprobanteListado(), ContaECInvoices(), FORMAS_PAGO, formatCurrency(), getEstadoBadge(), getProformaEstadoBadge(), getTipoComprobanteLabel() (+60 more)

### Community 6 - "HR Employee Models"
Cohesion: 0.08
Nodes (58): cerrar_arqueo(), close_cash_session(), create_partial_arqueo(), create_ticket(), get_arqueo_pdf(), get_arqueo_reporte(), get_arqueos_resumen(), get_cash_session() (+50 more)

### Community 7 - "Auth and Security"
Cohesion: 0.08
Nodes (56): create_orden_compra(), create_recepcion_mercaderia(), create_retencion_compra(), delete_cuenta_por_pagar(), delete_orden_compra(), delete_recepcion(), delete_retencion(), _get_company_for_user() (+48 more)

### Community 8 - "Inventory and Products"
Cohesion: 0.05
Nodes (57): get_volatile_status(), AsyncSession, User, ContaEC - Endpoints de Almacenamiento Volátil Administración de limpieza de arch, Ejecutar limpieza inmediata de archivos temporales expirados.      Solo usuarios, Obtener estado actual del almacenamiento volátil.      Muestra cantidad de archi, trigger_cleanup(), cleanup_expired_files() (+49 more)

### Community 9 - "CRM Module"
Cohesion: 0.05
Nodes (56): _COLORS, ContaECBI(), CuadroMandoView(), formatCurrency(), formatNumber(), formatPercent(), KPICard(), KPIDashboard() (+48 more)

### Community 10 - "POS Module"
Cohesion: 0.07
Nodes (46): assign_role(), check_permission(), get_my_roles(), _get_user_role_in_company(), _is_owner_or_admin_in_company(), list_company_users(), AsyncSession, User (+38 more)

### Community 11 - "Email Templates and Logs"
Cohesion: 0.06
Nodes (55): AsientosTab(), asientoStatusBadge(), BalanceTab(), ContaECAccounting(), ContaECAccountingProps, cxcStatusBadge(), CxCTab(), EnvejecimientoTab() (+47 more)

### Community 12 - "Warehouse Management"
Cohesion: 0.08
Nodes (46): _calcular_totales(), consultar_comprobante_sri(), corregir_comprobante(), create_comprobante(), delete_comprobante(), download_ride_pdf(), enviar_comprobante_email(), enviar_comprobante_sri() (+38 more)

### Community 13 - "Projects Module"
Cohesion: 0.06
Nodes (41): create_employee(), delete_employee(), _get_company_for_user(), get_employee(), _get_employee_for_user(), list_departments(), AsyncSession, Company (+33 more)

### Community 14 - "Purchases and Suppliers"
Cohesion: 0.08
Nodes (51): export_rdep_pdf(), Exportar reporte RDEP (Relación de Deducciones del Empleado al Patrono)     en f, _build_clave_acceso_section(), _build_comprador_section(), _build_comprobante_section(), _build_detalle_table(), _build_documento_modificado_section(), _build_emisor_section() (+43 more)

### Community 15 - "Module Group 15"
Cohesion: 0.07
Nodes (40): autorizar_comprobante(), _call_sri_autorizacion(), _call_sri_recepcion(), consultar_autorizacion(), _create_mock_autorizacion_response(), _create_mock_recepcion_response(), _encode_xml_base64(), enviar_comprobante() (+32 more)

### Community 16 - "Module Group 16"
Cohesion: 0.11
Nodes (50): firmar_comprobante(), Firmar un comprobante con la firma digital del usuario.          Proceso:     1., _add_text_element(), _build_detalles(), _build_impuestos_detalle(), _build_info_adicional(), _build_info_factura(), _build_info_tributaria() (+42 more)

### Community 17 - "Module Group 17"
Cohesion: 0.09
Nodes (48): add_clients_to_segment(), create_automation(), create_segment(), delete_automation(), delete_segment(), get_activity(), get_automation(), _get_company_for_user() (+40 more)

### Community 18 - "Module Group 18"
Cohesion: 0.06
Nodes (40): ActividadesTab(), AutomatizacionesTab(), ContaECCRM(), ESTADOS_ACTIVIDAD, ESTADOS_LEAD, ETAPAS_PIPELINE, formatCurrency(), formatDate() (+32 more)

### Community 19 - "Module Group 19"
Cohesion: 0.09
Nodes (43): _calcular_ingresos_anuales(), _construir_rdep_xml(), generar_anexos_iess(), generar_rdep_xml(), generar_sut_decimos(), _get_company_for_user(), obtener_rdep_data(), AsyncSession (+35 more)

### Community 20 - "Module Group 20"
Cohesion: 0.09
Nodes (41): admin_dashboard(), delete_user(), end_user_trial(), get_license_prices(), get_user(), LicensePriceUpdate, list_trial_users(), list_users() (+33 more)

### Community 21 - "Module Group 21"
Cohesion: 0.08
Nodes (38): ClientesTab(), ContaECProjects(), CreateTimesheetDialog(), DashboardTab(), ESTADOS_PROYECTO, ESTADOS_TAREA, formatCurrency(), formatDate() (+30 more)

### Community 22 - "Module Group 22"
Cohesion: 0.08
Nodes (37): create_email_template(), delete_email_template(), get_email_template(), list_email_templates(), preview_email_template(), AsyncSession, Request, User (+29 more)

### Community 23 - "Module Group 23"
Cohesion: 0.07
Nodes (42): AsientoContableCreate, AsientoContableUpdate, AsientoDetalleCreate, AsientoDetalleResponse, BalanceComprobacionItem, BalanceComprobacionResponse, ContabilidadStats, CuentaContableCreate (+34 more)

### Community 24 - "Module Group 24"
Cohesion: 0.06
Nodes (36): AsistenciaResumenResponse, AsistenciaUpdate, BankPaymentExportRequest, BankPaymentExportResponse, CargaFamiliarCreate, CargaFamiliarResponse, CargaFamiliarUpdate, EvaluacionDesempenoCreate (+28 more)

### Community 25 - "Module Group 25"
Cohesion: 0.07
Nodes (40): CRMActivityCreate, CRMActivityUpdate, CRMAutomationCreate, CRMAutomationUpdate, CRMContactSegmentCreate, CRMContactSegmentMemberResponse, CRMContactSegmentUpdate, CRMLeadCreate (+32 more)

### Community 26 - "Module Group 26"
Cohesion: 0.10
Nodes (36): _build_user_notification_filter(), create_notification(), delete_notification(), _get_notification_or_404(), get_unread_count(), list_notifications(), mark_all_read(), mark_as_read() (+28 more)

### Community 27 - "Module Group 27"
Cohesion: 0.12
Nodes (37): cancel_transfer(), create_transfer(), deactivate_warehouse(), deactivate_warehouse_location(), _get_company_for_user(), get_kardex_detallado(), _get_next_number(), get_transfer() (+29 more)

### Community 28 - "Module Group 28"
Cohesion: 0.08
Nodes (31): geistMono, geistSans, metadata, ContaECDashboard(), PoliciesView(), Providers(), Toaster(), FeatureCheckResult (+23 more)

### Community 29 - "Module Group 29"
Cohesion: 0.09
Nodes (35): create_company(), create_establishment(), delete_company(), get_company(), list_clients(), list_companies(), list_establishments(), listar_tipos_contribuyente() (+27 more)

### Community 30 - "Module Group 30"
Cohesion: 0.07
Nodes (37): obtener_regimen_por_ingresos(), Determinar el régimen tributario aplicable según ingresos anuales.      Args:, es_agente_retencion(), es_contribuyente_especial(), es_rimpe(), EstadoComprobante, FormaPago, get_regimen_by_codigo() (+29 more)

### Community 31 - "Module Group 31"
Cohesion: 0.12
Nodes (35): _check_overdue(), export_cuentas_csv(), export_cuentas_excel(), _get_company_for_user(), _get_cuenta_or_404(), get_cuenta_por_pagar(), get_resumen_cuentas(), list_cuentas_por_pagar() (+27 more)

### Community 32 - "Module Group 32"
Cohesion: 0.09
Nodes (33): delete_email_log(), get_bulk_email_stats(), get_email_log(), get_email_logs_stats(), _get_log_or_404(), list_email_logs(), AsyncSession, datetime (+25 more)

### Community 33 - "Module Group 33"
Cohesion: 0.08
Nodes (36): CuentaPorPagarCreate, CuentaPorPagarPayment, CuentaPorPagarRenegotiation, CuentaPorPagarSummary, CuentaPorPagarUpdate, OrdenCompraCreate, OrdenCompraDetalleCreate, OrdenCompraDetalleResponse (+28 more)

### Community 34 - "Module Group 34"
Cohesion: 0.13
Nodes (35): close_presupuesto(), export_budget_to_excel(), get_alertas_summary(), get_budget_alertas_realtime(), get_budget_ejecucion_detail(), _get_company_for_user(), get_comparativo_general(), get_comparativo_presupuesto() (+27 more)

### Community 35 - "Module Group 35"
Cohesion: 0.11
Nodes (34): _build_codigo_ubicacion(), _build_ubicacion_completa(), create_ubicacion(), deactivate_ubicacion(), _get_location_for_user(), get_ubicacion(), get_ubicacion_stock(), _get_warehouse_for_user() (+26 more)

### Community 36 - "Module Group 36"
Cohesion: 0.08
Nodes (35): AlertaBI, CuadroMandoResponse, DimCliente, DimProducto, DimTiempo, FactInventarioRow, FactVentaRow, FlujoEfectivoMensual (+27 more)

### Community 37 - "Module Group 37"
Cohesion: 0.11
Nodes (32): asignar_turno(), _get_company_for_user(), get_resumen_asistencia(), get_turnos_semanal(), importar_asistencia_biometrico(), listar_faltas(), AsyncSession, Company (+24 more)

### Community 38 - "Module Group 38"
Cohesion: 0.13
Nodes (33): categorize_description(), chat_with_bot(), close_chatbot_session(), delete_category_rule(), delete_prediction(), delete_recommendation(), generate_recommendations(), _get_company_for_user() (+25 more)

### Community 39 - "Module Group 39"
Cohesion: 0.10
Nodes (28): ChatbotEstado, FraudeEstado, FraudeSeveridad, PrediccionEstado, PrediccionTipo, Enum, str, ContaEC - Modelos de Machine Learning / IA Predicciones, detección de fraude, c (+20 more)

### Community 40 - "Module Group 40"
Cohesion: 0.08
Nodes (33): POSArqueoCerrarRequest, POSArqueoCerrarResponse, POSArqueoCreate, POSArqueoReporteResponse, POSArqueoResponse, POSArqueoResumenItem, POSArqueoResumenResponse, POSCashSessionClose (+25 more)

### Community 41 - "Module Group 41"
Cohesion: 0.08
Nodes (34): ProyectoCostoCreate, ProyectoCostoResponse, ProyectoCostoUpdate, ProyectoCreate, ProyectoRecursoCreate, ProyectoRecursoResponse, ProyectoRecursoUpdate, ProyectoResponse (+26 more)

### Community 42 - "Module Group 42"
Cohesion: 0.08
Nodes (34): AsistenciaTab(), CargasFamiliaresTab(), ContaECHR(), DecimosTab(), EmpleadosTab(), formatCurrency(), IESSTab(), IRTab() (+26 more)

### Community 43 - "Module Group 43"
Cohesion: 0.11
Nodes (33): create_cuenta_bancaria(), delete_ecommerce_connector(), _get_company_for_user(), get_cuenta_bancaria(), get_ecommerce_connector(), get_extracto(), get_integration_stats(), import_bank_csv() (+25 more)

### Community 44 - "Module Group 44"
Cohesion: 0.10
Nodes (32): calcular_aportes_iess(), calcular_decimo_cuarto(), calcular_decimo_cuarto_mensualizado(), calcular_decimo_tercero(), calcular_decimo_tercero_mensualizado(), calcular_fondo_reserva(), calcular_fondo_reserva_mensual(), calcular_horas_extras() (+24 more)

### Community 45 - "Module Group 45"
Cohesion: 0.09
Nodes (32): BudgetAlertItem, BudgetAlertsResponse, BudgetExecutionDetailResponse, BudgetExecutionMonthDetail, BudgetExportResponse, ComparativoGeneralResponse, ComparativoPresupuestario, EjecucionMensualCreate (+24 more)

### Community 46 - "Module Group 46"
Cohesion: 0.10
Nodes (30): AlertasTab(), ComparativoTab(), ContaECBudgets(), CuadroMandoTab(), EjecucionTab(), formatCurrency(), getAlertaTipoBadge(), getEjecucionTextColor() (+22 more)

### Community 47 - "Module Group 47"
Cohesion: 0.11
Nodes (31): ArqueoTab(), CartItem, ChangeDialog(), ContaECPOS(), formatCurrency(), formatDateTime(), formatReceipt(), getTicketEstadoBadge() (+23 more)

### Community 48 - "Module Group 48"
Cohesion: 0.11
Nodes (29): anular_asiento(), aprobar_asiento(), balance_comprobacion(), cerrar_periodo_fiscal(), _check_company_access(), confirmar_pago(), contabilidad_stats(), crear_periodo_fiscal() (+21 more)

### Community 49 - "Module Group 49"
Cohesion: 0.15
Nodes (30): create_kardex_ajuste(), create_kardex_movement(), _get_company_for_user(), get_kardex_reporte(), _get_last_saldo(), _get_product_for_company(), get_product_kardex(), get_product_saldo() (+22 more)

### Community 50 - "Module Group 50"
Cohesion: 0.10
Nodes (31): BANCOS_EC, ContaECIntegrations(), PLATAFORMAS, createCuentaBancaria(), createEcommerceConnector(), createExtractoBancario(), CuentaBancariaCreate, CuentaBancariaResponse (+23 more)

### Community 51 - "Module Group 51"
Cohesion: 0.10
Nodes (29): _fetch_shopify_orders(), _fetch_shopify_products(), _fetch_woocommerce_orders(), _fetch_woocommerce_products(), _get_connector_for_user(), get_ecommerce_connector_status(), list_sync_logs(), _push_shopify_inventory() (+21 more)

### Community 52 - "Module Group 52"
Cohesion: 0.09
Nodes (26): Base, Clase base declarativa para todos los modelos SQLAlchemy, Anticipo, AnticipoEstado, Contrato, ContratoEstado, DecimoEstado, DecimoPago (+18 more)

### Community 53 - "Module Group 53"
Cohesion: 0.12
Nodes (30): get_license_limits(), User, Obtener límites aplicables para un usuario según su estado de licencia.     Prio, create_test_user(), AsyncSession, User, ContaEC - Pruebas de integración para límites de licencia  Ejecutar con:     cd, Prueba 2: Usuario con plan mensual (+22 more)

### Community 54 - "Module Group 54"
Cohesion: 0.08
Nodes (23): PasswordChange, BaseModel, ContaEC - Esquemas de autenticación Pydantic schemas para login, registro, token, Esquema de datos del payload del token JWT, Esquema para solicitud de refresco de token, Esquema de respuesta con datos del usuario (sin datos sensibles), Esquema para inicio de sesión, Esquema para actualización de datos del usuario (+15 more)

### Community 55 - "Module Group 55"
Cohesion: 0.08
Nodes (27): ComprobanteCreate, ComprobanteDetalleCreate, ComprobanteDetalleResponse, ComprobanteEstadoEnum, ComprobanteListResponse, ComprobanteResponse, ComprobanteStatsResponse, CorreccionRequest (+19 more)

### Community 56 - "Module Group 56"
Cohesion: 0.08
Nodes (29): Sidebar(), SidebarContent(), SidebarContext, SidebarContextProps, SidebarFooter(), SidebarGroup(), SidebarGroupAction(), SidebarGroupContent() (+21 more)

### Community 57 - "Module Group 57"
Cohesion: 0.09
Nodes (28): check_feature_access(), check_license_expiry(), check_license_limit(), get_license_options(), get_license_status(), get_license_tiers(), AsyncSession, User (+20 more)

### Community 58 - "Module Group 58"
Cohesion: 0.07
Nodes (28): close_db(), get_db(), init_db(), AsyncSession, ContaEC - Configuración de la base de datos Soporte asíncrono para PostgreSQL (a, Cierra la conexión a la base de datos.     Se debe llamar al detener la aplicaci, Dependencia de FastAPI que proporciona una sesión de base de datos asíncrona., # TODO: Remove implicit commit - requires auditing ~218 flush()-only endpoints (+20 more)

### Community 59 - "Module Group 59"
Cohesion: 0.12
Nodes (28): change_password(), get_me(), login(), logout(), AsyncSession, Request, User, ContaEC - Endpoints de Autenticación Registro, login, refresh token con rotación (+20 more)

### Community 60 - "Module Group 60"
Cohesion: 0.11
Nodes (27): create_category_rule(), list_category_rules(), Listar reglas de categorización, Crear una regla de categorización, Actualizar una regla de categorización, update_category_rule(), MLCategoriaRegla, Modelo de Regla de Categorización.     Registra las reglas para la categorizaci (+19 more)

### Community 61 - "Module Group 61"
Cohesion: 0.09
Nodes (26): KardexDetalladoResponse, BaseModel, ContaEC - Esquemas Pydantic de Multi-Almacén y Logística Schemas para almacenes,, Esquema para crear una ubicación dentro de un almacén, Esquema para crear un nuevo almacén, Valida que capacidad_actual no exceda capacidad_maxima si está definida, Esquema para actualizar una ubicación de almacén, Esquema de respuesta para el stock en una ubicación específica (+18 more)

### Community 62 - "Module Group 62"
Cohesion: 0.07
Nodes (29): @dnd-kit/utilities, input-otp, next-themes, dependencies, @dnd-kit/utilities, input-otp, next-themes, @radix-ui/react-accordion (+21 more)

### Community 63 - "Module Group 63"
Cohesion: 0.10
Nodes (17): get_clamav_status(), Verificar disponibilidad de ClamAV (con opcion de forzar re-chequeo), check_clamav_available(), ClamAVScanner, Escaneo síncrono de archivo con ClamAV (para ejecutar en executor)., Escanea un archivo con ClamAV.         Ejecuta el escaneo en un executor para no, Escaneo síncrono de bytes con ClamAV (para ejecutar en executor)., Escanea contenido en memoria con ClamAV.         Ejecuta el escaneo en un execut (+9 more)

### Community 64 - "Module Group 64"
Cohesion: 0.16
Nodes (26): _calcular_totales_proforma(), convertir_proforma(), create_proforma(), delete_proforma(), enviar_proforma(), _get_company_for_user(), get_proforma(), get_proforma_stats() (+18 more)

### Community 65 - "Module Group 65"
Cohesion: 0.16
Nodes (26): create_smtp_profile(), delete_smtp_profile(), _determine_use_ssl(), _get_profile_or_404(), list_smtp_profiles(), AsyncSession, Request, User (+18 more)

### Community 66 - "Module Group 66"
Cohesion: 0.07
Nodes (27): dom, dom.iterable, esnext, .next/dev/types/**/*.ts, next-env.d.ts, .next/types/**/*.ts, node_modules, **/*.ts (+19 more)

### Community 67 - "Module Group 67"
Cohesion: 0.13
Nodes (26): _check_clamav(), get_company_config(), get_signature_status(), _get_status_warnings(), get_user_config(), AsyncSession, User, UUID (+18 more)

### Community 68 - "Module Group 68"
Cohesion: 0.15
Nodes (25): export_powerbi(), export_powerbi_file(), get_alertas(), get_cuadro_mando(), get_flujo_efectivo(), get_kpis(), get_top_clientes(), get_top_productos() (+17 more)

### Community 69 - "Module Group 69"
Cohesion: 0.15
Nodes (23): create_supplier(), delete_supplier(), _get_company_for_user(), get_supplier(), list_suppliers(), AsyncSession, Company, Request (+15 more)

### Community 70 - "Module Group 70"
Cohesion: 0.13
Nodes (25): CuentaBancariaCreate, CuentaBancariaResponse, CuentaBancariaUpdate, EcommerceConnectorCreate, EcommerceConnectorResponse, EcommerceConnectorStatus, EcommerceConnectorUpdate, EcommerceSyncInventoryResponse (+17 more)

### Community 71 - "Module Group 71"
Cohesion: 0.11
Nodes (24): DecimoCuartoRequest, DecimoTerceroRequest, FondosReservaResponse, IESSReportResponse, PayrollDetalleExtras, PayrollGenerate, BaseModel, ContaEC - Esquemas Pydantic de Nómina (Rol de Pago) Schemas para generación, apr (+16 more)

### Community 72 - "Module Group 72"
Cohesion: 0.10
Nodes (25): categorizar(), chatbot_responder(), detectar_fraude(), detectar_intencion(), extraer_entidades(), generar_recomendaciones(), generar_respuesta_chatbot(), _generate_llm_response() (+17 more)

### Community 73 - "Module Group 73"
Cohesion: 0.13
Nodes (22): AsientoContableCreate, actualizar_asiento(), _check_periodo_abierto(), crear_asiento(), _get_company_id_for_user(), libro_diario(), listar_asientos(), listar_pagos() (+14 more)

### Community 74 - "Module Group 74"
Cohesion: 0.15
Nodes (22): create_client(), delete_client(), _ensure_consumidor_final(), get_client(), _get_company_for_user(), list_clients(), AsyncSession, Company (+14 more)

### Community 75 - "Module Group 75"
Cohesion: 0.11
Nodes (23): create_activity(), create_pipeline(), delete_activity(), delete_opportunity(), Request, Eliminar una oportunidad, Crear una nueva actividad, Actualizar una actividad (+15 more)

### Community 76 - "Module Group 76"
Cohesion: 0.16
Nodes (24): export_clients_excel(), export_comprobantes_excel(), export_comprobantes_xml_zip(), export_kardex_excel(), export_products_csv(), export_products_excel(), _get_company_for_user(), _get_csv_response() (+16 more)

### Community 77 - "Module Group 77"
Cohesion: 0.17
Nodes (24): get_column_mapping(), _get_company_for_user(), import_clients_csv(), import_clients_excel(), import_products_csv(), import_products_excel(), _map_row_to_dict(), AsyncSession (+16 more)

### Community 78 - "Module Group 78"
Cohesion: 0.08
Nodes (14): ContaEC - Configuración de la aplicación Lee las variables de entorno desde el a, Indica si el ambiente es producción, Indica si el ambiente es desarrollo, Ensure JWT_ALGORITHM is not set to an insecure value like 'none'., Configuración principal de la aplicación ContaEC.     Todas las variables se car, URL del servicio web de recepción del SRI según el ambiente, URL del servicio web de autorización del SRI según el ambiente, URL del servicio web de consulta del SRI según el ambiente (+6 more)

### Community 79 - "Module Group 79"
Cohesion: 0.12
Nodes (22): Toast, ToastAction, ToastActionElement, ToastClose, ToastDescription, ToastProps, ToastTitle, toastVariants (+14 more)

### Community 80 - "Module Group 80"
Cohesion: 0.14
Nodes (23): _extract_cert_info(), _load_pkcs12(), _parse_xml(), Any, _Element, Exception, ContaEC - Firmador de XML para comprobantes electrónicos del SRI Firma XML con f, Parsea una cadena XML y devuelve el elemento raíz.      Args:         xml_conten (+15 more)

### Community 81 - "Module Group 81"
Cohesion: 0.12
Nodes (19): export_audit_logs(), get_audit_stats(), list_audit_logs(), AsyncSession, datetime, User, ContaEC - Endpoints de Auditoría Consulta de registros de auditoría, estadística, Exportar registros de auditoría a CSV.      Solo disponible para administradores (+11 more)

### Community 82 - "Module Group 82"
Cohesion: 0.12
Nodes (21): create_backup(), create_backup_data(), _derive_fernet_from_user_key(), download_backup(), list_backups(), midnight_backup_task(), AsyncSession, Fernet (+13 more)

### Community 83 - "Module Group 83"
Cohesion: 0.19
Nodes (21): export_comprobantes_pdf(), Exportar comprobantes a PDF (lote).      Genera un PDF con un resumen/tabla de l, exportar_banco_guayaquil(), exportar_banco_pacifico(), exportar_csv_generico(), exportar_excel(), exportar_pichincha(), generar_rol_pago_pdf() (+13 more)

### Community 84 - "Module Group 84"
Cohesion: 0.11
Nodes (20): create_extracto(), create_movimiento(), delete_cuenta_bancaria(), delete_extracto(), delete_movimiento(), Request, Eliminar una cuenta bancaria (soft delete), Crear/importar un extracto bancario (+12 more)

### Community 85 - "Module Group 85"
Cohesion: 0.12
Nodes (20): convert_lead_to_opportunity(), create_opportunity(), get_opportunity(), list_opportunities(), move_opportunity_stage(), Actualizar una oportunidad, Mover una oportunidad a una etapa diferente del pipeline, Convertir un lead en oportunidad de venta (+12 more)

### Community 86 - "Module Group 86"
Cohesion: 0.18
Nodes (19): create_product(), delete_product(), _get_company_for_user(), get_product(), list_products(), AsyncSession, Company, User (+11 more)

### Community 87 - "Module Group 87"
Cohesion: 0.10
Nodes (11): ContaEC - Token Blacklist / Revocation Service In-memory token revocation list w, Remove expired entries from the revocation list.         Should be called period, In-memory token blacklist for JWT revocation.          Stores revoked token JTI, Number of currently revoked tokens, Number of tracked refresh token rotations, Add a token JTI to the revocation list.                  Args:             jti:, Check if a token JTI has been revoked.                  Args:             jti: J, Register a refresh token rotation (old JTI -> new JTI).         When a refresh t (+3 more)

### Community 88 - "Module Group 88"
Cohesion: 0.10
Nodes (21): FastAPI + SQLAlchemy + Alembic + Pydantic, ReportLab + QRCode + Pillow para RIDE PDF, Blueprint de Despliegue PostgreSQL en Produccion, Migracion de SQLite a PostgreSQL (Alembic/pgloader), Arquitectura: Caddy -> Next.js -> FastAPI -> PostgreSQL, ContaEC - Sistema Contable y Facturacion Electronica del Ecuador, Despliegue en servidor Debian/Ubuntu, Contabilidad de Doble Partida (+13 more)

### Community 89 - "Module Group 89"
Cohesion: 0.10
Nodes (21): bun-types, cross-env, eslint, eslint-config-next, devDependencies, bun-types, cross-env, eslint (+13 more)

### Community 90 - "Module Group 90"
Cohesion: 0.15
Nodes (19): _decode_header_value(), _decode_str(), download_attachment(), _download_attachment_sync(), EmailReceiverError, _extract_attachments(), Exception, ContaEC - Servicio de Recepción de Correos Electrónicos Recepción de correos vía (+11 more)

### Community 91 - "Module Group 91"
Cohesion: 0.17
Nodes (18): ActivityStatus, ActivityType, AutomationTriggerType, CRMContactSegmentMember, LeadSource, LeadStatus, OpportunityStatus, Enum (+10 more)

### Community 92 - "Module Group 92"
Cohesion: 0.14
Nodes (18): add_cuenta_to_presupuesto(), approve_presupuesto(), delete_cuenta(), delete_presupuesto(), Request, Eliminar una cuenta presupuestaria (solo en borrador), Actualizar un presupuesto anual (solo en estado borrador), Eliminar un presupuesto anual (solo en estado borrador) (+10 more)

### Community 93 - "Module Group 93"
Cohesion: 0.15
Nodes (12): InputSanitizationMiddleware, Request, RateLimitMiddleware, ContaEC - Middleware de seguridad Rate limiting, sanitización de entradas, y pro, Redact sensitive field values from a logged payload string., Valida un string contra todos los patrones peligrosos., Middleware de limitación de tasa por IP, Middleware para añadir headers de seguridad (+4 more)

### Community 94 - "Module Group 94"
Cohesion: 0.11
Nodes (13): Decimal, str, ContaEC - Modelo de Vacaciones Vacaciones: Gestión de días de vacaciones por emp, Total de días disponibles (pendientes + acumulados), Modelo de Solicitud de Vacaciones.      Registra cada solicitud de vacaciones po, Estados de la solicitud de vacaciones, Modelo de Período de Vacaciones.      Registra el acumulado de días de vacacione, Calcula duración en días entre fecha_inicio y fecha_fin (+5 more)

### Community 95 - "Module Group 95"
Cohesion: 0.12
Nodes (13): ClientCreate, ClientResponse, ClientUpdate, BaseModel, ContaEC - Esquemas Pydantic de Cliente Schemas para creación, actualización y re, Esquema para crear un nuevo cliente, Valida que el tipo de identificación sea válido, Validación básica del formato de correo electrónico (+5 more)

### Community 96 - "Module Group 96"
Cohesion: 0.12
Nodes (14): BaseModel, ContaEC - Esquemas Pydantic de Perfil SMTP Schemas para creación, actualización,, Valida que el tipo de proveedor sea válido, Valida que el protocolo sea válido, Esquema para actualizar un perfil SMTP, Esquema para crear un nuevo perfil SMTP, Valida que el tipo de proveedor sea válido, Valida que el protocolo sea válido (+6 more)

### Community 97 - "Module Group 97"
Cohesion: 0.20
Nodes (17): download_email_attachment(), get_inbox(), list_email_attachments(), AsyncSession, User, ContaEC - Endpoints de Recepción de Correos Electrónicos Recepción de correos ví, Listar correos en la bandeja de entrada.      Usa la configuración IMAP/POP3 del, Listar adjuntos de un correo electrónico específico (+9 more)

### Community 98 - "Module Group 98"
Cohesion: 0.18
Nodes (17): EmailServiceError, _get_smtp_connection(), get_smtp_profile_connection(), Exception, ContaEC - Servicio de Envío de Correos Electrónicos Envío automático de comproba, Carga un perfil SMTP y prepara los parámetros de conexión.      Args:         pr, Envía un comprobante autorizado por correo electrónico al cliente.     Ejecuta e, Error en el servicio de correo electrónico (+9 more)

### Community 99 - "Module Group 99"
Cohesion: 0.20
Nodes (17): BancoTipoCuenta, ConciliacionEstado, ConnectorEstado, EcommercePlataforma, ExtractoEstado, MovimientoTipo, Enum, str (+9 more)

### Community 100 - "Module Group 100"
Cohesion: 0.11
Nodes (17): aliases, components, hooks, lib, ui, utils, iconLibrary, rsc (+9 more)

### Community 101 - "Module Group 101"
Cohesion: 0.15
Nodes (15): create_stage(), delete_pipeline(), delete_stage(), list_stages(), Listar etapas de un pipeline, Crear una etapa en un pipeline, Actualizar una etapa de pipeline, Eliminar una etapa de pipeline (+7 more)

### Community 102 - "Module Group 102"
Cohesion: 0.18
Nodes (16): _compute_file_hash(), _get_file_extension(), _get_signature_warnings(), AsyncSession, UploadFile, User, ContaEC - Endpoints de Subida de Archivos Manejo seguro de uploads con escaneo d, Calcula el hash SHA-256 del archivo (+8 more)

### Community 103 - "Module Group 103"
Cohesion: 0.17
Nodes (16): AsientoEstado, CuentaPorCobrarEstado, NaturalezaCuenta, PagoEstado, PagoTipo, PeriodoFiscalEstado, str, ContaEC - Modelos Contables Core Plan de Cuentas, Asientos Contables, Cuentas p (+8 more)

### Community 104 - "Module Group 104"
Cohesion: 0.16
Nodes (16): ProformaCreate, ProformaDetalleCreate, ProformaDetalleResponse, ProformaListResponse, ProformaResponse, ProformaStatsResponse, ProformaUpdate, BaseModel (+8 more)

### Community 105 - "Module Group 105"
Cohesion: 0.12
Nodes (11): BaseModel, ContaEC - Esquemas Pydantic de Proveedor Schemas para creación, actualización y, Valida que el tipo de identificación sea válido según Tabla 7 del SRI, Validación básica del número de identificación, Validación básica del formato de correo electrónico, Esquema para actualizar un proveedor, Esquema para crear un nuevo proveedor, Valida que el tipo de identificación sea válido (+3 more)

### Community 106 - "Module Group 106"
Cohesion: 0.20
Nodes (17): ContaECBIProps, ContaECBudgetsProps, ContaECCRMProps, ContaECDashboardProps, ContaECHRProps, ContaECIntegrationsProps, ContaECInventoryProps, ContaECInvoicesProps (+9 more)

### Community 107 - "Module Group 107"
Cohesion: 0.14
Nodes (14): actualizar_cuenta_por_cobrar(), crear_cuenta_por_cobrar(), envejecimiento_cartera(), listar_cuentas_por_cobrar(), Lista cuentas por cobrar, Crea una cuenta por cobrar, Actualiza una cuenta por cobrar, Obtiene el envejecimiento de cartera (CxC agrupado por cliente y rango) (+6 more)

### Community 108 - "Module Group 108"
Cohesion: 0.16
Nodes (16): _check_alerts(), create_presupuesto(), Recalcular ejecutado/disponible para todas las cuentas de un presupuesto, Recalcula totales de una cuenta presupuestaria a partir de ejecuciones mensuales, Recalcula totales del presupuesto anual a partir de las cuentas, Crear un nuevo presupuesto anual con cuentas, Verifica umbrales de ejecución y genera alertas automáticas.     Umbrales: 50%,, recalcular_presupuesto() (+8 more)

### Community 109 - "Module Group 109"
Cohesion: 0.15
Nodes (15): create_recurso(), delete_recurso(), get_proyecto_stats(), list_recursos(), User, Obtener estadísticas generales de proyectos, Listar recursos de un proyecto, Crear un recurso en un proyecto (+7 more)

### Community 110 - "Module Group 110"
Cohesion: 0.17
Nodes (15): decrypt_user_config(), _derive_fernet_key(), encrypt_field(), encrypt_user_config(), generate_encryption_key(), _get_fernet(), Any, Fernet (+7 more)

### Community 111 - "Module Group 111"
Cohesion: 0.13
Nodes (11): Contrato, ContratoEstado, ContratoTipo, str, ContaEC - Modelo de Contrato Laboral Contrato: Historial de contratos laborales, Tipos de contrato laboral según Código del Trabajo Ecuador, Verifica si el contrato está vigente, Verifica si está en período de prueba (máx 3 meses) (+3 more)

### Community 112 - "Module Group 112"
Cohesion: 0.14
Nodes (11): PrestamoDetalle, PrestamoEmpleado, PrestamoEstado, PrestamoTipo, Decimal, str, ContaEC - Modelo de Préstamos Laborales Préstamo: Préstamos y anticipos a emplea, Porcentaje del préstamo ya pagado (+3 more)

### Community 113 - "Module Group 113"
Cohesion: 0.12
Nodes (9): CompanyCreate, Esquema para crear una nueva empresa, Valida el formato del RUC si esta presente, Valida el formato del RUC ecuatoriano (13 dígitos), Valida que el valor sea SI o NO, Valida que el tipo de ambiente sea 1 o 2, Valida que el tipo de emisión sea 1, Valida que el código tenga exactamente 3 dígitos (+1 more)

### Community 114 - "Module Group 114"
Cohesion: 0.16
Nodes (13): KardexAjuste, KardexCreate, KardexReporteResponse, KardexSaldoResponse, BaseModel, Decimal, ContaEC - Esquemas Pydantic de Kardex (Movimientos de Inventario) Schemas para c, Valida que la cantidad de ajuste no sea cero (+5 more)

### Community 115 - "Module Group 115"
Cohesion: 0.16
Nodes (14): create_lead(), delete_lead(), get_lead(), list_leads(), Listar leads con filtros, Obtener un lead por ID, update_lead(), CRMLead (+6 more)

### Community 116 - "Module Group 116"
Cohesion: 0.17
Nodes (13): create_proyecto(), _get_company_for_user(), list_proyectos(), Company, ContaEC - Endpoints de Proyectos y Servicios CRUD de proyectos, tareas, recursos, Recalcular costos, márgenes y progreso del proyecto.      - Suma todos los times, Crear un nuevo proyecto, Listar proyectos con filtros (+5 more)

### Community 117 - "Module Group 117"
Cohesion: 0.16
Nodes (14): create_warehouse(), get_warehouse(), list_warehouses(), Listar almacenes de la empresa, Crear un nuevo almacén, Obtener un almacén específico con sus ubicaciones, Actualizar un almacén, update_warehouse() (+6 more)

### Community 118 - "Module Group 118"
Cohesion: 0.14
Nodes (10): str, ContaEC - Modelo de Turnos Laborales Turnos: Gestión de turnos rotativos para em, Verifica si es turno nocturno (22:00 - 6:00), Verifica si tiene recargo nocturno o especial, Modelo de Asignación de Turno.      Asigna turnos específicos a empleados para f, Modelo de Turno Rotativo.      Define turnos de trabajo con horarios específicos, TurnoAsignacion, TurnoEstado (+2 more)

### Community 119 - "Module Group 119"
Cohesion: 0.19
Nodes (12): get_ejecucion_for_cuenta(), Registrar ejecución mensual para una cuenta presupuestaria, Obtener ejecución mensual de una cuenta presupuestaria, Actualizar monto de una ejecución mensual, register_ejecucion_mensual(), update_ejecucion(), PresupuestoCuenta, PresupuestoEjecucionMensual (+4 more)

### Community 120 - "Module Group 120"
Cohesion: 0.16
Nodes (13): create_timesheet(), delete_proyecto(), delete_timesheet(), Request, Eliminar un proyecto (soft delete), Crear un registro de timesheet en un proyecto, Actualizar un registro de timesheet, Eliminar un registro de timesheet (+5 more)

### Community 121 - "Module Group 121"
Cohesion: 0.20
Nodes (14): get_proyecto(), _get_proyecto_for_user(), list_costos(), list_tareas(), list_timesheets(), AsyncSession, Obtener un proyecto por ID con todas sus relaciones, Actualizar un proyecto (+6 more)

### Community 122 - "Module Group 122"
Cohesion: 0.15
Nodes (10): HistorialLaboral, MovimientoEstado, MovimientoTipo, str, ContaEC - Modelo de Historial Laboral Historial Laboral: Seguimiento de cambios, Tipos de movimiento laboral, Verifica si el movimiento es una promoción/ascenso, Verifica si hubo cambio salarial (+2 more)

### Community 123 - "Module Group 123"
Cohesion: 0.20
Nodes (13): Carousel(), CarouselApi, CarouselContent(), CarouselContext, CarouselContextProps, CarouselItem(), CarouselNext(), CarouselOptions (+5 more)

### Community 124 - "Module Group 124"
Cohesion: 0.18
Nodes (11): actualizar_cuenta_contable(), crear_cuenta_contable(), listar_cuentas_contables(), Lista las cuentas contables de la empresa, Crea una nueva cuenta contable, Actualiza una cuenta contable, CuentaContable, Plan de Cuentas Contable.      Catálogo de cuentas con estructura jerárquica p (+3 more)

### Community 125 - "Module Group 125"
Cohesion: 0.18
Nodes (12): get_current_active_admin(), get_current_user(), AsyncSession, ContaEC - Utilidades de seguridad Hashing de contraseñas con bcrypt, creación y, Verifica y decodifica un token JWT.     Comprueba que el token no esté revocado, Revoca un token JWT añadiendo su JTI a la blacklist.          Args:         payl, Dependencia de FastAPI que obtiene el usuario actual a partir del token JWT., Dependencia de FastAPI que verifica que el usuario actual sea administrador. (+4 more)

### Community 126 - "Module Group 126"
Cohesion: 0.22
Nodes (11): PresupuestoAlerta, PresupuestoEstado, Enum, str, ContaEC - Modelos de Presupuestos y Control Presupuestario PresupuestoAnual: Pr, Estado del presupuesto anual, Tipo de cuenta presupuestaria, Modelo de Alertas de Sobregiro y Control Presupuestario.      Genera alertas a (+3 more)

### Community 127 - "Module Group 127"
Cohesion: 0.15
Nodes (13): AsistenciaTipo, EvaluacionEstado, LiquidacionEstado, LiquidacionTipo, ParentescoTipo, str, Tipos de parentesco para carga familiar, Estados de la evaluación de desempeño (+5 more)

### Community 128 - "Module Group 128"
Cohesion: 0.17
Nodes (9): CompanyUpdate, EstablishmentCreate, BaseModel, ContaEC - Esquemas de Empresa y Establecimiento Pydantic schemas para creación,, Esquema para actualizar datos de una empresa, Valida que el valor sea SI o NO, Valida que el tipo de ambiente sea 1 o 2, Esquema para crear un nuevo establecimiento (+1 more)

### Community 129 - "Module Group 129"
Cohesion: 0.18
Nodes (10): ProductCreate, ProductResponse, ProductUpdate, BaseModel, ContaEC - Esquemas Pydantic de Producto/Servicio Schemas para creación, actualiz, Esquema para crear un nuevo producto o servicio, Valida que el tipo sea B (Bien) o S (Servicio), Esquema para actualizar un producto o servicio (+2 more)

### Community 130 - "Module Group 130"
Cohesion: 0.15
Nodes (12): name, private, scripts, build, db:generate, db:migrate, db:push, db:reset (+4 more)

### Community 131 - "Module Group 131"
Cohesion: 0.26
Nodes (11): backendDir, checkBackendHealth(), DELETE(), ensureBackend(), GET(), PATCH(), POST(), proxyRequest() (+3 more)

### Community 132 - "Module Group 132"
Cohesion: 0.21
Nodes (11): BackupKeyRequest, configure_smtp(), ProfileUpdateRequest, BaseModel, Esquema para configuración SMTP, Configurar SMTP para envío de correos, Esquema para actualización de perfil del usuario, Esquema para clave de encriptación de backups (+3 more)

### Community 133 - "Module Group 133"
Cohesion: 0.24
Nodes (10): UploadFile, Subir firma electrónica (.p12/.pfx) y su clave.          Proceso:     1. Escaneo, Subir logotipo de la empresa, upload_company_logo(), upload_digital_signature(), is_any_threat_found(), ContaEC - Módulo de escaneo de malware ClamAV (escaneo local vía clamd) + VirusT, Escanea un archivo subido con todos los escáneres disponibles.          Args: (+2 more)

### Community 134 - "Module Group 134"
Cohesion: 0.18
Nodes (10): create_ecommerce_connector(), Crear un conector e-commerce, Actualizar un conector e-commerce, Probar la conexion con la plataforma e-commerce, test_ecommerce_connection(), update_ecommerce_connector(), EcommerceConnector, Modelo de Conector E-Commerce.     Configura la conexion con plataformas de com (+2 more)

### Community 135 - "Module Group 135"
Cohesion: 0.22
Nodes (10): create_prediction(), get_prediction(), list_predictions(), Crear una predicción ML (ejecuta el algoritmo de predicción), Listar predicciones ML, Obtener una predicción por ID, MLPrediccion, Modelo de Predicción ML.     Registra predicciones de ventas, ingresos, gastos (+2 more)

### Community 136 - "Module Group 136"
Cohesion: 0.22
Nodes (10): get_fraud_alert(), list_fraud_alerts(), Listar alertas de fraude, Obtener una alerta de fraude por ID, Actualizar una alerta de fraude (resolver/investigar), update_fraud_alert(), MLAlertaFraude, Modelo de Alerta de Fraude.     Registra alertas de posibles fraudes detectados (+2 more)

### Community 137 - "Module Group 137"
Cohesion: 0.18
Nodes (10): create_tarea(), delete_tarea(), Crear una tarea en un proyecto, Actualizar una tarea de proyecto, Eliminar una tarea de proyecto (soft delete), update_tarea(), ProyectoTarea, Modelo de Tarea de Proyecto.      Cada tarea dentro de un proyecto con asignac (+2 more)

### Community 138 - "Module Group 138"
Cohesion: 0.24
Nodes (10): ContribuyenteRimpe, ObligadoContabilidad, str, ContaEC - Modelos de Empresa y Establecimiento Company: Información fiscal de l, Tipo de ambiente para facturación electrónica del SRI, Tipo de emisión de comprobantes electrónicos, Obligación de llevar contabilidad, Tipos de contribuyente RIMPE y regímenes fiscales (+2 more)

### Community 139 - "Module Group 139"
Cohesion: 0.22
Nodes (9): EstadoEmpleado, Decimal, str, ContaEC - Modelo de Empleado Employee: Información del empleado para nómina y R, Tipos de contrato laboral según Código del Trabajo Ecuador, Tipos de pago de remuneración, Calcula el sueldo diario dividiendo el mensual entre 30, TipoContrato (+1 more)

### Community 140 - "Module Group 140"
Cohesion: 0.18
Nodes (7): CargaFamiliar, EvaluacionDesempeno, ContaEC - Modelos extendidos de RRHH (Fase 5) CargaFamiliar: Cargas familiares, Modelo de Evaluación de Desempeño.      Permite registrar evaluaciones de dese, Modelo de Detalle de Utilidades por Empleado.      Desglosa la participación i, Modelo de Carga Familiar.      Almacena las cargas familiares del empleado (hi, UtilidadesDetalle

### Community 141 - "Module Group 141"
Cohesion: 0.31
Nodes (10): ProyectoEstado, Enum, str, ContaEC - Modelos de Proyectos y Servicios Proyecto: Gestión de proyectos con s, Estado de la tarea del proyecto, Prioridad de la tarea del proyecto, Tipo de recurso del proyecto, TareaEstado (+2 more)

### Community 142 - "Module Group 142"
Cohesion: 0.25
Nodes (9): FormControl(), FormDescription(), FormFieldContext, FormFieldContextValue, FormItemContext, FormItemContextValue, FormLabel(), FormMessage() (+1 more)

### Community 143 - "Module Group 143"
Cohesion: 0.18
Nodes (7): Sheet(), SheetContent(), SheetDescription(), SheetFooter(), SheetHeader(), SheetOverlay(), SheetTitle()

### Community 144 - "Module Group 144"
Cohesion: 0.22
Nodes (10): _build_codigo_ubicacion(), _build_ubicacion_completa(), create_warehouse_location(), WarehouseLocationCreate, WarehouseLocationUpdate, Construye la descripción completa de la ubicación., Crear una ubicación dentro de un almacén, Actualizar una ubicación de almacén (+2 more)

### Community 145 - "Module Group 145"
Cohesion: 0.31
Nodes (9): NotificationCategory, NotificationPriority, NotificationType, Enum, str, ContaEC - Modelo de Notificaciones del Sistema Notification: Notificaciones gen, Tipos de notificación, Categorías de notificación (+1 more)

### Community 146 - "Module Group 146"
Cohesion: 0.29
Nodes (8): ChartConfig, ChartContext, ChartContextProps, ChartLegendContent(), ChartTooltipContent(), getPayloadConfigFromPayload(), THEMES, useChart()

### Community 147 - "Module Group 147"
Cohesion: 0.27
Nodes (4): Locale, localeNames, locales, config

### Community 148 - "Module Group 148"
Cohesion: 0.25
Nodes (8): create_chatbot_session(), list_chatbot_sessions(), Crear una sesión de chatbot, Listar sesiones del chatbot, MLChatbotSesion, Modelo de Sesión del Chatbot.     Registra las sesiones de chat del asistente v, ChatbotSesionCreate, ChatbotSesionResponse

### Community 149 - "Module Group 149"
Cohesion: 0.22
Nodes (9): ArqueoTipo, CajaEstado, str, Estado de una sesión de caja.     abierta: Caja abierta y operando     cerrada, Estado de un ticket POS.     pendiente: Ticket creado pero no pagado     pagad, Tipo de venta en POS.     efectivo: Pago en efectivo     tarjeta: Pago con tar, Tipo de arqueo de caja.     parcial: Arqueo parcial durante el turno     final, TicketEstado (+1 more)

### Community 150 - "Module Group 150"
Cohesion: 0.31
Nodes (8): EnvironmentMode, Language, str, ContaEC - Modelos de Usuario User: Modelo principal del usuario del sistema Us, Modo de ambiente para facturación electrónica, Protocolos de correo electrónico, SmtpProtocol, Theme

### Community 151 - "Module Group 151"
Cohesion: 0.28
Nodes (8): createSystemMessage(), createUserMessage(), generateMessageId(), httpServer, io, Message, User, users

### Community 152 - "Module Group 152"
Cohesion: 0.25
Nodes (7): anular_pago(), crear_pago(), Registra un pago/cobro, Anula un pago/cobro y revierte montos, Pago, Modelo de Pago / Cobro.      Registra los pagos realizados (a proveedores) y l, PagoCreate

### Community 153 - "Module Group 153"
Cohesion: 0.25
Nodes (7): create_costo(), delete_costo(), Crear un costo en un proyecto, Eliminar un costo de proyecto, ProyectoCosto, Modelo de Costo de Proyecto.      Registra costos adicionales asociados a un p, ProyectoCostoCreate

### Community 154 - "Module Group 154"
Cohesion: 0.25
Nodes (6): ProformaDetalle, ProformaEstado, str, ContaEC - Modelos de Proforma Proforma: Cotización/Presupuesto que puede conver, Estado de la proforma en su ciclo de vida, Modelo de Detalle de Proforma.      Cada línea de la proforma representa un bi

### Community 155 - "Module Group 155"
Cohesion: 0.25
Nodes (5): OrdenCompraDetalle, ContaEC - Modelos de Compras OrdenCompra: Órdenes de compra a proveedores Orde, Modelo de Detalle de Orden de Compra.      Cada línea de la orden de compra co, Modelo de Detalle de Recepción de Mercadería.      Cada línea de la recepción, RecepcionMercaderiaDetalle

### Community 156 - "Module Group 156"
Cohesion: 0.25
Nodes (6): str, ContaEC - Modelos de Multi-Almacén y Logística Warehouse: Almacenes/bodegas de, Estado de una transferencia entre almacenes.     pendiente: Creada pero no envi, Modelo de Detalle de Transferencia entre Almacenes.      Cada línea de la tran, TransferEstado, WarehouseTransferDetalle

### Community 157 - "Module Group 157"
Cohesion: 0.33
Nodes (6): ComprobanteEstado, ComprobanteTipo, str, ContaEC - Modelos de Comprobante Electrónico Comprobante: Comprobante electróni, Estado del comprobante electrónico en el ciclo de vida.     Según los estados d, Tipo de comprobante electrónico según Tabla 1 del SRI.     Código de tipo de do

### Community 158 - "Module Group 158"
Cohesion: 0.33
Nodes (6): EmailLogEstado, EmailLogTipo, str, ContaEC - Modelo de Log de Envío de Correos EmailLog: Registro de todos los corr, Tipo de correo electrónico, Estado del envío de correo

### Community 159 - "Module Group 159"
Cohesion: 0.33
Nodes (6): str, ContaEC - Modelo de Perfil SMTP SMTPProfile: Perfiles SMTP múltiples por usuari, Tipos de proveedor SMTP, Protocolos de conexión SMTP, SmtpConnectionProtocol, SmtpProviderType

### Community 160 - "Module Group 160"
Cohesion: 0.29
Nodes (6): name, private, scripts, dev, start, version

### Community 161 - "Module Group 161"
Cohesion: 0.33
Nodes (6): react, react, FormItem(), SidebarMenuSkeleton(), SidebarProvider(), useIsMobile()

### Community 162 - "Module Group 162"
Cohesion: 0.43
Nodes (5): ToggleGroup(), ToggleGroupContext, ToggleGroupItem(), Toggle(), toggleVariants

### Community 163 - "Module Group 163"
Cohesion: 0.33
Nodes (5): libro_mayor(), Genera el Libro Mayor para una cuenta contable, AsientoDetalle, Detalle del Asiento Contable (línea de débito o crédito).      Cada detalle re, LibroMayorItem

### Community 164 - "Module Group 164"
Cohesion: 0.33
Nodes (6): obtener_contribuyente_por_codigo(), Obtener información de un tipo de contribuyente por su código.      Códigos váli, ContribuyenteTipo, get_contribuyente_by_codigo(), Tipo de contribuyente según clasificación del SRI.     Determina las obligacione, Obtiene información de un tipo de contribuyente por su código.      Args:

### Community 165 - "Module Group 165"
Cohesion: 0.33
Nodes (5): get_session_messages(), Obtener mensajes de una sesión del chatbot, MLChatbotMensaje, Modelo de Mensaje del Chatbot.     Registra cada mensaje dentro de una sesión d, ChatbotMensajeResponse

### Community 166 - "Module Group 166"
Cohesion: 0.33
Nodes (5): name, private, scripts, dev, version

### Community 167 - "Module Group 167"
Cohesion: 0.40
Nodes (4): ensure_consumidor_final(), AsyncSession, ContaEC - Utilidades compartidas Funciones de uso común entre múltiples módulos, Crea el cliente 'Consumidor Final' por defecto para una empresa.          Este c

### Community 168 - "Module Group 168"
Cohesion: 0.40
Nodes (4): str, ContaEC - Modelo de Cliente Client: Información del cliente para facturación el, Tipos de identificación según catálogo del SRI (Tabla 7).     Utilizados para i, TipoIdentificacion

### Community 169 - "Module Group 169"
Cohesion: 0.40
Nodes (4): KardexTipoMovimiento, str, ContaEC - Modelo de Kardex (Movimientos de Inventario) Kardex: Registro de movi, Tipo de movimiento de inventario.     ENTRADA: Compra, devolución, ajuste posit

### Community 170 - "Module Group 170"
Cohesion: 0.40
Nodes (3): ContaEC - Modelos de Nómina (Rol de Pago) RolPago: Cabecera del rol de pago men, Modelo de Detalle del Rol de Pago por empleado.      Contiene todos los ingres, RolPagoDetalle

### Community 171 - "Module Group 171"
Cohesion: 0.40
Nodes (4): ProductoTipo, str, ContaEC - Modelo de Producto/Servicio Product: Catálogo de productos y servicio, Tipo de producto según catálogo del SRI.     B = Bien (producto físico)     S

### Community 172 - "Module Group 172"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 173 - "Module Group 173"
Cohesion: 0.50
Nodes (4): _check_virustotal(), Verifica disponibilidad de VirusTotal con cache de 5 min, check_virustotal_available(), Verifica si VirusTotal esta disponible probando la API key.     Cachea el result

## Knowledge Gaps
- **308 isolated node(s):** `download_sri_xsd.sh script`, `name`, `version`, `private`, `dev` (+303 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **79 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Base` connect `Module Group 52` to `Comprobantes SRI Module`, `HR Employee Models`, `Auth and Security`, `POS Module`, `Warehouse Management`, `Module Group 17`, `Module Group 20`, `Module Group 22`, `Module Group 26`, `Module Group 27`, `Module Group 29`, `Module Group 31`, `Module Group 32`, `Module Group 35`, `Module Group 37`, `Module Group 38`, `Module Group 39`, `Module Group 43`, `Module Group 48`, `Module Group 49`, `Module Group 51`, `Module Group 57`, `Module Group 58`, `Module Group 60`, `Module Group 64`, `Module Group 65`, `Module Group 69`, `Module Group 73`, `Module Group 74`, `Module Group 75`, `Module Group 81`, `Module Group 84`, `Module Group 85`, `Module Group 86`, `Module Group 91`, `Module Group 92`, `Module Group 94`, `Module Group 99`, `Module Group 101`, `Module Group 103`, `Module Group 107`, `Module Group 109`, `Module Group 111`, `Module Group 112`, `Module Group 115`, `Module Group 116`, `Module Group 117`, `Module Group 118`, `Module Group 119`, `Module Group 120`, `Module Group 122`, `Module Group 124`, `Module Group 126`, `Module Group 127`, `Module Group 132`, `Module Group 134`, `Module Group 135`, `Module Group 136`, `Module Group 137`, `Module Group 138`, `Module Group 139`, `Module Group 140`, `Module Group 141`, `Module Group 145`, `Module Group 148`, `Module Group 149`, `Module Group 150`, `Module Group 152`, `Module Group 153`, `Module Group 154`, `Module Group 155`, `Module Group 156`, `Module Group 157`, `Module Group 158`, `Module Group 159`, `Module Group 163`, `Module Group 165`, `Module Group 168`, `Module Group 169`, `Module Group 170`, `Module Group 171`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `Company` connect `Comprobantes SRI Module` to `Module Group 132`, `HR Employee Models`, `Module Group 135`, `Module Group 136`, `Auth and Security`, `POS Module`, `Module Group 138`, `Warehouse Management`, `Projects Module`, `Module Group 17`, `Module Group 19`, `Module Group 20`, `Module Group 148`, `Module Group 152`, `Module Group 26`, `Module Group 27`, `Module Group 29`, `Module Group 31`, `Module Group 34`, `Module Group 35`, `Module Group 37`, `Module Group 38`, `Module Group 43`, `Module Group 49`, `Module Group 51`, `Module Group 52`, `Module Group 53`, `Module Group 182`, `Module Group 183`, `Module Group 184`, `Module Group 185`, `Module Group 186`, `Module Group 64`, `Module Group 67`, `Module Group 69`, `Module Group 73`, `Module Group 74`, `Module Group 76`, `Module Group 77`, `Module Group 82`, `Module Group 83`, `Module Group 85`, `Module Group 86`, `Module Group 115`, `Module Group 116`, `Module Group 117`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Why does `log_action()` connect `Module Group 75` to `Module Group 134`, `Module Group 135`, `Module Group 136`, `HR Employee Models`, `Module Group 137`, `Auth and Security`, `Module Group 144`, `Module Group 17`, `Module Group 148`, `Module Group 22`, `Module Group 153`, `Module Group 26`, `Module Group 27`, `Module Group 31`, `Module Group 34`, `Module Group 35`, `Module Group 38`, `Module Group 43`, `Module Group 51`, `Module Group 60`, `Module Group 65`, `Module Group 69`, `Module Group 81`, `Module Group 84`, `Module Group 85`, `Module Group 92`, `Module Group 101`, `Module Group 108`, `Module Group 109`, `Module Group 115`, `Module Group 116`, `Module Group 117`, `Module Group 119`, `Module Group 120`, `Module Group 121`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 178 inferred relationships involving `Base` (e.g. with `AsientoContable` and `AsientoDetalle`) actually correct?**
  _`Base` has 178 INFERRED edges - model-reasoned connections that need verification._
- **Are the 126 inferred relationships involving `Company` (e.g. with `crear_asiento()` and `crear_pago()`) actually correct?**
  _`Company` has 126 INFERRED edges - model-reasoned connections that need verification._
- **Are the 126 inferred relationships involving `log_action()` (e.g. with `add_cuenta_to_presupuesto()` and `approve_presupuesto()`) actually correct?**
  _`log_action()` has 126 INFERRED edges - model-reasoned connections that need verification._
- **What connects `download_sri_xsd.sh script`, `name`, `version` to the rest of the system?**
  _308 weakly-connected nodes found - possible documentation gaps or missing edges._