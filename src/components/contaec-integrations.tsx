'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
// Textarea removed (unused)
import { NumericInput } from '@/components/ui/numeric-input';
import {
  Landmark,
  ShoppingCart,
  Plus,
  Trash2,
  Loader2,
  Eye,
  CheckCircle2,
  XCircle,
  Pencil,
  DollarSign,
  Calendar,
  ArrowUpCircle,
  ArrowDownCircle,
  Play,
  AlertTriangle,
  Wifi,
  Clock,
  BarChart3,
  Package,
  Users,
  Globe,
  Zap,
  Settings,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getIntegrationStats,
  getCuentasBancarias,
  createCuentaBancaria,
  updateCuentaBancaria,
  deleteCuentaBancaria,
  getExtractosBancarios,
  importBankExtractFile,
  deleteExtractoBancario,
  getMovimientosBancarios,
  updateMovimientoBancario,
  getEcommerceConnectors,
  createEcommerceConnector,
  updateEcommerceConnector,
  deleteEcommerceConnector,
  testEcommerceConnection,
  // syncEcommerceConnector removed (unused)
  syncEcommerceProducts,
  syncEcommerceOrders,
  syncEcommerceInventory,
  getEcommerceSyncLogs,
  type User as UserType,
  type Company as CompanyType,
  type IntegrationStats,
  type CuentaBancariaResponse,
  type CuentaBancariaCreate,
  type ExtractoBancarioResponse,
  type ExtractoBancarioCreate,
  type MovimientoBancarioResponse,
  type MovimientoBancarioUpdate,
  type EcommerceConnectorResponse,
  type EcommerceConnectorCreate,
  type EcommerceConnectorUpdate,
  type EcommerceSyncLogResponse,
} from '@/lib/api';

interface ContaECIntegrationsProps {
  user: UserType;
  companies: CompanyType[];
}

// Platform labels and icons
const PLATAFORMAS: Record<string, { label: string; color: string }> = {
  shopify: { label: 'Shopify', color: 'bg-green-100 text-green-800' },
  woocommerce: { label: 'WooCommerce', color: 'bg-purple-100 text-purple-800' },
  opencart: { label: 'OpenCart', color: 'bg-blue-100 text-blue-800' },
  prestashop: { label: 'PrestaShop', color: 'bg-pink-100 text-pink-800' },
  magento: { label: 'Magento', color: 'bg-orange-100 text-orange-800' },
  meli: { label: 'Mercado Libre', color: 'bg-yellow-100 text-yellow-800' },
  otro: { label: 'Otro', color: 'bg-gray-100 text-gray-800' },
};

// Ecuadorian banks with SWIFT/BIC codes
const BANCOS_EC: Record<string, { swift_bic: string; manual: boolean }> = {
  'Banco Pichincha': { swift_bic: 'PICHECEQXXX', manual: false },
  'Produbanco': { swift_bic: 'PRODECEQXXX', manual: false },
  'Banco Bolivariano': { swift_bic: 'BBOLECEQXXX', manual: false },
  'Banco Internacional': { swift_bic: 'BACECEQXXX', manual: false },
  'Banco Austro': { swift_bic: 'AUSTECQX', manual: false },
  'Banco Guayaquil': { swift_bic: 'BPGUECEQXXX', manual: false },
  'Banco Ruminahui': { swift_bic: '', manual: true },
  'Banco del Pacifico': { swift_bic: '', manual: true },
  'Otro': { swift_bic: '', manual: true },
};

export function ContaECIntegrations({ user: _user, companies }: ContaECIntegrationsProps) {
  const selectedCompany = companies[0];
  const companyId = selectedCompany?.id || '';

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<IntegrationStats | null>(null);
  const [cuentas, setCuentas] = useState<CuentaBancariaResponse[]>([]);
  const [extractos, setExtractos] = useState<ExtractoBancarioResponse[]>([]);
  const [movimientos, setMovimientos] = useState<MovimientoBancarioResponse[]>([]);
  const [connectors, setConnectors] = useState<EcommerceConnectorResponse[]>([]);
  const [syncLogs, setSyncLogs] = useState<EcommerceSyncLogResponse[]>([]);

  // Dialogs
  const [showCuentaDialog, setShowCuentaDialog] = useState(false);
  const [showExtractoDialog, setShowExtractoDialog] = useState(false);
  const [showConnectorDialog, setShowConnectorDialog] = useState(false);
  const [showMovimientoDetail, setShowMovimientoDetail] = useState(false);
  const [selectedMovimiento, setSelectedMovimiento] = useState<MovimientoBancarioResponse | null>(null);

  // Editing
  const [editingCuenta, setEditingCuenta] = useState<CuentaBancariaResponse | null>(null);
  const [editingConnector, setEditingConnector] = useState<EcommerceConnectorResponse | null>(null);

  // Selected extracto for viewing movements
  const [selectedExtractoId, setSelectedExtractoId] = useState<string | null>(null);

  // Form states
  const [cuentaForm, setCuentaForm] = useState<CuentaBancariaCreate>({
    company_id: companyId,
    nombre_banco: '',
    tipo_cuenta: 'corriente',
    numero_cuenta: '',
    titular: '',
    moneda: 'USD',
    saldo_inicial: 0,
    formato_extracto: 'csv',
  });
  const [bancoSeleccionado, setBancoSeleccionado] = useState<string>('');

  const [extractoForm, setExtractoForm] = useState<ExtractoBancarioCreate>({
    company_id: companyId,
    cuenta_bancaria_id: '',
    fecha_desde: new Date().toISOString().split('T')[0],
    fecha_hasta: new Date().toISOString().split('T')[0],
    saldo_inicial: 0,
    saldo_final: 0,
    total_debitos: 0,
    total_creditos: 0,
    numero_movimientos: 0,
  });

  const [connectorForm, setConnectorForm] = useState<EcommerceConnectorCreate>({
    company_id: companyId,
    nombre: '',
    plataforma: 'shopify',
    url_tienda: '',
    api_key: '',
    api_secret: '',
    sync_productos: true,
    sync_ordenes: true,
    sync_clientes: true,
    sync_inventario: true,
  });

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        getIntegrationStats(companyId),
        getCuentasBancarias(companyId),
        getExtractosBancarios({ company_id: companyId }),
        getEcommerceConnectors(companyId),
        getEcommerceSyncLogs({ company_id: companyId }),
      ]);
      if (results[0].status === 'fulfilled') setStats(results[0].value);
      if (results[1].status === 'fulfilled') setCuentas(results[1].value);
      if (results[2].status === 'fulfilled') setExtractos(results[2].value);
      if (results[3].status === 'fulfilled') setConnectors(results[3].value);
      if (results[4].status === 'fulfilled') setSyncLogs(results[4].value);
    } catch {
      toast.error('Error al cargar datos de integraciones');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load movements when extracto is selected
  useEffect(() => {
    if (selectedExtractoId) {
      getMovimientosBancarios({ extracto_id: selectedExtractoId }).then(setMovimientos).catch(() => {});
    }
  }, [selectedExtractoId]);

  // ---- Bank Account CRUD ----
  const handleSaveCuenta = async () => {
    if (!cuentaForm.nombre_banco || !cuentaForm.numero_cuenta || !cuentaForm.titular) {
      toast.error('Complete los campos obligatorios');
      return;
    }
    setSaving(true);
    try {
      if (editingCuenta) {
        await updateCuentaBancaria(editingCuenta.id, {
          nombre_banco: cuentaForm.nombre_banco,
          tipo_cuenta: cuentaForm.tipo_cuenta,
          numero_cuenta: cuentaForm.numero_cuenta,
          titular: cuentaForm.titular,
          moneda: cuentaForm.moneda,
          formato_extracto: cuentaForm.formato_extracto,
          swift_bic: cuentaForm.swift_bic,
        });
        toast.success('Cuenta bancaria actualizada');
      } else {
        await createCuentaBancaria({ ...cuentaForm, company_id: companyId });
        toast.success('Cuenta bancaria creada');
      }
      setShowCuentaDialog(false);
      setEditingCuenta(null);
      setBancoSeleccionado('');
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar cuenta');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCuenta = async (id: string) => {
    if (!confirm('¿Desactivar esta cuenta bancaria?')) return;
    try {
      await deleteCuentaBancaria(id);
      toast.success('Cuenta desactivada');
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al desactivar');
    }
  };

  // ---- Extracto CRUD ----
  const [extractoFile, setExtractoFile] = useState<File | null>(null);

  const handleImportExtracto = async () => {
    if (!extractoForm.cuenta_bancaria_id) {
      toast.error('Seleccione una cuenta bancaria');
      return;
    }
    if (!extractoFile) {
      toast.error('Seleccione el archivo del extracto (CSV)');
      return;
    }
    setSaving(true);
    try {
      const result = await importBankExtractFile(extractoForm.cuenta_bancaria_id, companyId, extractoFile);
      toast.success(result.message || 'Extracto importado');
      setShowExtractoDialog(false);
      setExtractoFile(null);
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al importar extracto');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteExtracto = async (id: string) => {
    if (!confirm('¿Eliminar este extracto y sus movimientos?')) return;
    try {
      await deleteExtractoBancario(id);
      toast.success('Extracto eliminado');
      if (selectedExtractoId === id) setSelectedExtractoId(null);
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    }
  };

  // ---- Movimiento Conciliacion ----
  const handleConciliar = async (movId: string, estado: string) => {
    try {
      const data: MovimientoBancarioUpdate = { conciliacion_estado: estado };
      await updateMovimientoBancario(movId, data);
      toast.success(estado === 'conciliado' ? 'Movimiento conciliado' : 'Movimiento ignorado');
      if (selectedExtractoId) {
        const movs = await getMovimientosBancarios({ extracto_id: selectedExtractoId });
        setMovimientos(movs);
      }
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al conciliar');
    }
  };

  // ---- E-Commerce Connector CRUD ----
  const handleSaveConnector = async () => {
    if (!connectorForm.nombre || !connectorForm.url_tienda) {
      toast.error('Complete los campos obligatorios');
      return;
    }
    setSaving(true);
    try {
      if (editingConnector) {
        const updateData: EcommerceConnectorUpdate = {
          nombre: connectorForm.nombre,
          url_tienda: connectorForm.url_tienda,
          api_key: connectorForm.api_key || undefined,
          api_secret: connectorForm.api_secret || undefined,
          sync_productos: connectorForm.sync_productos,
          sync_ordenes: connectorForm.sync_ordenes,
          sync_clientes: connectorForm.sync_clientes,
          sync_inventario: connectorForm.sync_inventario,
        };
        await updateEcommerceConnector(editingConnector.id, updateData);
        toast.success('Conector actualizado');
      } else {
        await createEcommerceConnector({ ...connectorForm, company_id: companyId });
        toast.success('Conector creado');
      }
      setShowConnectorDialog(false);
      setEditingConnector(null);
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar conector');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConnector = async (id: string) => {
    if (!confirm('¿Desactivar este conector?')) return;
    try {
      await deleteEcommerceConnector(id);
      toast.success('Conector desactivado');
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al desactivar');
    }
  };

  const handleTestConnection = async (id: string) => {
    setTesting(id);
    try {
      const result = await testEcommerceConnection(id);
      toast.success(result.message);
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al probar conexion');
    } finally {
      setTesting(null);
    }
  };

  const handleSync = async (id: string, tipoSync: string = 'completo') => {
    setSyncing(id);
    try {
      if (tipoSync === 'productos') {
        const r = await syncEcommerceProducts(id);
        toast.success(`Productos sincronizados: ${r.total_creados} creados, ${r.total_actualizados} actualizados${r.total_errores ? `, ${r.total_errores} errores` : ''}`);
      } else if (tipoSync === 'ordenes') {
        const r = await syncEcommerceOrders(id);
        toast.success(`Órdenes sincronizadas: ${r.total_creados} creadas, ${r.total_actualizados} actualizadas${r.total_errores ? `, ${r.total_errores} errores` : ''}`);
      } else if (tipoSync === 'inventario') {
        const r = await syncEcommerceInventory(id);
        toast.success(`Inventario sincronizado: ${r.total_actualizados} productos actualizados${r.total_errores ? `, ${r.total_errores} errores` : ''}`);
      } else {
        // Completo: ejecuta productos + órdenes + inventario
        const [p, o, i] = await Promise.allSettled([
          syncEcommerceProducts(id),
          syncEcommerceOrders(id),
          syncEcommerceInventory(id),
        ]);
        let creados = 0; let actualizados = 0; let errores = 0;
        for (const res of [p, o, i]) {
          if (res.status === 'fulfilled') {
            const r = res.value as unknown as Record<string, unknown>;
            creados += Number(r.total_creados ?? 0);
            actualizados += Number(r.total_actualizados ?? 0);
            errores += Number(r.total_errores ?? 0);
          } else {
            errores += 1;
          }
        }
        toast.success(`Sincronización completa: ${creados} creados, ${actualizados} actualizados${errores ? `, ${errores} errores` : ''}`);
      }
      loadData();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al sincronizar');
    } finally {
      setSyncing(null);
    }
  };

  // ---- Helpers ----
  const formatCurrency = (val: number) => `$${val.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const formatDate = (d: string) => new Date(d).toLocaleDateString('es-EC');
  const formatDateTime = (d: string) => new Date(d).toLocaleString('es-EC');

  const getEstadoBadge = (estado: string) => {
    const map: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
      importado: { variant: 'secondary', label: 'Importado' },
      en_conciliacion: { variant: 'default', label: 'En Conciliacion' },
      conciliado: { variant: 'default', label: 'Conciliado' },
      con_error: { variant: 'destructive', label: 'Con Error' },
      pendiente: { variant: 'outline', label: 'Pendiente' },
      ignorado: { variant: 'secondary', label: 'Ignorado' },
      configurado: { variant: 'outline', label: 'Configurado' },
      conectado: { variant: 'default', label: 'Conectado' },
      sincronizando: { variant: 'default', label: 'Sincronizando' },
      error: { variant: 'destructive', label: 'Error' },
      desactivado: { variant: 'secondary', label: 'Desactivado' },
      completada: { variant: 'default', label: 'Completada' },
      en_progreso: { variant: 'default', label: 'En Progreso' },
    };
    const info = map[estado] || { variant: 'outline' as const, label: estado };
    return <Badge variant={info.variant}>{info.label}</Badge>;
  };

  if (!companyId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Seleccione una empresa para ver integraciones</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cuentas Bancarias</CardTitle>
            <Landmark className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.cuentas_activas || 0}</div>
            <p className="text-xs text-muted-foreground">
              Saldo total: {formatCurrency(Number(stats?.saldo_total_cuentas || 0))}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pend. Conciliacion</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.movimientos_pendientes_conciliar || 0}</div>
            <p className="text-xs text-muted-foreground">
              Conciliados: {stats?.movimientos_conciliados || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conectores E-Commerce</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.connectors_activos || 0}</div>
            <p className="text-xs text-muted-foreground">
              Total: {stats?.total_connectors || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sync Hoy</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.sync_logs_hoy || 0}</div>
            <p className="text-xs text-muted-foreground">
              Total historial: {stats?.total_sync_logs || 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="bank" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="bank" className="flex items-center gap-2">
            <Landmark className="h-4 w-4" />
            <span className="hidden sm:inline">Integracion Bancaria</span>
            <span className="sm:hidden">Banco</span>
          </TabsTrigger>
          <TabsTrigger value="ecommerce" className="flex items-center gap-2">
            <ShoppingCart className="h-4 w-4" />
            <span className="hidden sm:inline">E-Commerce</span>
            <span className="sm:hidden">E-Com</span>
          </TabsTrigger>
          <TabsTrigger value="sync-logs" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Historial Sync</span>
            <span className="sm:hidden">Sync</span>
          </TabsTrigger>
        </TabsList>

        {/* ============================================ */}
        {/* TAB: INTEGRACION BANCARIA */}
        {/* ============================================ */}
        <TabsContent value="bank" className="space-y-4">
          {/* Cuentas Bancarias */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Landmark className="h-5 w-5" />
                  Cuentas Bancarias
                </CardTitle>
                <CardDescription>Registre sus cuentas bancarias para importar extractos</CardDescription>
              </div>
              <Button
                onClick={() => {
                  setEditingCuenta(null);
                  setBancoSeleccionado('');
                  setCuentaForm({
                    company_id: companyId,
                    nombre_banco: '',
                    tipo_cuenta: 'corriente',
                    numero_cuenta: '',
                    titular: '',
                    moneda: 'USD',
                    saldo_inicial: 0,
                    formato_extracto: 'csv',
                    swift_bic: '',
                  });
                  setShowCuentaDialog(true);
                }}
              >
                <Plus className="h-4 w-4 mr-1" /> Nueva Cuenta
              </Button>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
              ) : cuentas.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No hay cuentas bancarias registradas</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Banco</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Nro. Cuenta</TableHead>
                        <TableHead>Titular</TableHead>
                        <TableHead className="text-right">Saldo Actual</TableHead>
                        <TableHead>Moneda</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {cuentas.map((c) => (
                        <TableRow key={c.id}>
                          <TableCell className="font-medium">{c.nombre_banco}</TableCell>
                          <TableCell className="capitalize">{c.tipo_cuenta}</TableCell>
                          <TableCell className="font-mono text-xs">{c.numero_cuenta}</TableCell>
                          <TableCell>{c.titular}</TableCell>
                          <TableCell className="text-right font-semibold">{formatCurrency(Number(c.saldo_actual))}</TableCell>
                          <TableCell>{c.moneda}</TableCell>
                          <TableCell>
                            <Badge variant={c.is_active ? 'default' : 'secondary'}>
                              {c.is_active ? 'Activa' : 'Inactiva'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditingCuenta(c);
                                  setBancoSeleccionado('');
                                  setCuentaForm({
                                    company_id: c.company_id,
                                    nombre_banco: c.nombre_banco,
                                    tipo_cuenta: c.tipo_cuenta,
                                    numero_cuenta: c.numero_cuenta,
                                    titular: c.titular,
                                    moneda: c.moneda,
                                    saldo_inicial: Number(c.saldo_inicial),
                                    formato_extracto: c.formato_extracto,
                                    swift_bic: c.swift_bic || '',
                                  });
                                  setShowCuentaDialog(true);
                                }}
                              >
                                <Pencil className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive"
                                onClick={() => handleDeleteCuenta(c.id)}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Extractos Bancarios */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Extractos Bancarios
                </CardTitle>
                <CardDescription>Importe y concilie sus extractos bancarios</CardDescription>
              </div>
              <Button
                onClick={() => {
                  setExtractoForm({
                    company_id: companyId,
                    cuenta_bancaria_id: cuentas[0]?.id || '',
                    fecha_desde: new Date().toISOString().split('T')[0],
                    fecha_hasta: new Date().toISOString().split('T')[0],
                    saldo_inicial: 0,
                    saldo_final: 0,
                    total_debitos: 0,
                    total_creditos: 0,
                    numero_movimientos: 0,
                  });
                  setShowExtractoDialog(true);
                }}
                disabled={cuentas.length === 0}
              >
                <Plus className="h-4 w-4 mr-1" /> Importar Extracto
              </Button>
            </CardHeader>
            <CardContent>
              {extractos.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No hay extractos importados</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Banco</TableHead>
                        <TableHead>Período</TableHead>
                        <TableHead className="text-right">Debitos</TableHead>
                        <TableHead className="text-right">Créditos</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Conciliacion</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {extractos.map((e) => (
                        <TableRow key={e.id} className={selectedExtractoId === e.id ? 'bg-muted' : ''}>
                          <TableCell>
                            <div className="font-medium">{e.banco_nombre || '-'}</div>
                            <div className="text-xs text-muted-foreground font-mono">{e.cuenta_numero || '-'}</div>
                          </TableCell>
                          <TableCell>
                            {formatDate(e.fecha_desde)} - {formatDate(e.fecha_hasta)}
                          </TableCell>
                          <TableCell className="text-right text-red-600">
                            {formatCurrency(Number(e.total_debitos))}
                          </TableCell>
                          <TableCell className="text-right text-green-600">
                            {formatCurrency(Number(e.total_creditos))}
                          </TableCell>
                          <TableCell>{getEstadoBadge(e.estado)}</TableCell>
                          <TableCell>
                            <span className="text-sm">{e.movimientos_conciliados}/{e.numero_movimientos}</span>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectedExtractoId(selectedExtractoId === e.id ? null : e.id)}
                              >
                                <Eye className="h-3 w-3 mr-1" />
                                Movimientos
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive"
                                onClick={() => handleDeleteExtracto(e.id)}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Movimientos del Extracto Seleccionado */}
          {selectedExtractoId && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Movimientos del Extracto
                </CardTitle>
                <CardDescription>Concilie los movimientos bancarios con sus comprobantes</CardDescription>
              </CardHeader>
              <CardContent>
                {movimientos.length === 0 ? (
                  <p className="text-center text-muted-foreground py-4">No hay movimientos en este extracto</p>
                ) : (
                  <ScrollArea className="max-h-96">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Fecha</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead className="text-right">Monto</TableHead>
                          <TableHead>Descripción</TableHead>
                          <TableHead>Referencia</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {movimientos.map((m) => (
                          <TableRow key={m.id}>
                            <TableCell className="text-xs">{formatDate(m.fecha)}</TableCell>
                            <TableCell>
                              {m.tipo === 'credito' ? (
                                <Badge className="bg-green-100 text-green-800">
                                  <ArrowUpCircle className="h-3 w-3 mr-1" /> Crédito
                                </Badge>
                              ) : (
                                <Badge className="bg-red-100 text-red-800">
                                  <ArrowDownCircle className="h-3 w-3 mr-1" /> Débito
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className={`text-right font-semibold ${m.tipo === 'credito' ? 'text-green-600' : 'text-red-600'}`}>
                              {m.tipo === 'debito' ? '-' : '+'}{formatCurrency(Number(m.monto))}
                            </TableCell>
                            <TableCell className="max-w-48 truncate text-xs">{m.descripcion || m.beneficiario || '-'}</TableCell>
                            <TableCell className="text-xs font-mono">{m.referencia || '-'}</TableCell>
                            <TableCell>{getEstadoBadge(m.conciliacion_estado)}</TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                {m.conciliacion_estado === 'pendiente' && (
                                  <>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      className="text-green-600"
                                      onClick={() => handleConciliar(m.id, 'conciliado')}
                                    >
                                      <CheckCircle2 className="h-3 w-3" />
                                    </Button>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      className="text-gray-500"
                                      onClick={() => handleConciliar(m.id, 'ignorado')}
                                    >
                                      <XCircle className="h-3 w-3" />
                                    </Button>
                                  </>
                                )}
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => { setSelectedMovimiento(m); setShowMovimientoDetail(true); }}
                                >
                                  <Eye className="h-3 w-3" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ============================================ */}
        {/* TAB: E-COMMERCE */}
        {/* ============================================ */}
        <TabsContent value="ecommerce" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <ShoppingCart className="h-5 w-5" />
                  Conectores E-Commerce
                </CardTitle>
                <CardDescription>
                  Conecte con Shopify, WooCommerce, OpenCart, PrestaShop, Magento y mas
                </CardDescription>
              </div>
              <Button
                onClick={() => {
                  setEditingConnector(null);
                  setConnectorForm({
                    company_id: companyId,
                    nombre: '',
                    plataforma: 'shopify',
                    url_tienda: '',
                    api_key: '',
                    api_secret: '',
                    sync_productos: true,
                    sync_ordenes: true,
                    sync_clientes: true,
                    sync_inventario: true,
                  });
                  setShowConnectorDialog(true);
                }}
              >
                <Plus className="h-4 w-4 mr-1" /> Nuevo Conector
              </Button>
            </CardHeader>
            <CardContent>
              {connectors.length === 0 ? (
                <div className="text-center py-12">
                  <Globe className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No hay conectores e-commerce configurados</p>
                  <p className="text-sm text-muted-foreground mt-1">Agregue un conector para sincronizar productos, ordenes y clientes</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {connectors.map((c) => {
                    const plataforma = PLATAFORMAS[c.plataforma] || PLATAFORMAS.otro;
                    return (
                      <Card key={c.id} className="relative">
                        <CardHeader className="pb-3">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                              <Badge className={plataforma.color}>{plataforma.label}</Badge>
                              {getEstadoBadge(c.estado)}
                            </div>
                            <div className="flex gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditingConnector(c);
                                  setConnectorForm({
                                    company_id: c.company_id,
                                    nombre: c.nombre,
                                    plataforma: c.plataforma,
                                    url_tienda: c.url_tienda,
                                    api_key: c.api_key || '',
                                    api_secret: '',
                                    sync_productos: c.sync_productos,
                                    sync_ordenes: c.sync_ordenes,
                                    sync_clientes: c.sync_clientes,
                                    sync_inventario: c.sync_inventario,
                                  });
                                  setShowConnectorDialog(true);
                                }}
                              >
                                <Settings className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive"
                                onClick={() => handleDeleteConnector(c.id)}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                          <CardTitle className="text-base">{c.nombre}</CardTitle>
                          <CardDescription className="text-xs truncate">{c.url_tienda}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {/* Sync options */}
                          <div className="flex flex-wrap gap-1">
                            {c.sync_productos && <Badge variant="outline" className="text-xs"><Package className="h-2 w-2 mr-1" />Productos</Badge>}
                            {c.sync_ordenes && <Badge variant="outline" className="text-xs"><ShoppingCart className="h-2 w-2 mr-1" />Ordenes</Badge>}
                            {c.sync_clientes && <Badge variant="outline" className="text-xs"><Users className="h-2 w-2 mr-1" />Clientes</Badge>}
                            {c.sync_inventario && <Badge variant="outline" className="text-xs"><BarChart3 className="h-2 w-2 mr-1" />Inventario</Badge>}
                          </div>

                          {/* Stats */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="text-muted-foreground">
                              Productos: <span className="font-semibold text-foreground">{c.total_productos_sync}</span>
                            </div>
                            <div className="text-muted-foreground">
                              Ordenes: <span className="font-semibold text-foreground">{c.total_ordenes_sync}</span>
                            </div>
                          </div>

                          {c.ultimo_error && (
                            <div className="flex items-start gap-1 text-xs text-destructive">
                              <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                              <span className="truncate">{c.ultimo_error}</span>
                            </div>
                          )}

                          {c.ultima_sincronizacion && (
                            <div className="text-xs text-muted-foreground flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              Última sync: {formatDateTime(c.ultima_sincronizacion)}
                            </div>
                          )}

                          <Separator />

                          {/* Actions */}
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1"
                              onClick={() => handleTestConnection(c.id)}
                              disabled={testing === c.id}
                            >
                              {testing === c.id ? (
                                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                              ) : (
                                <Wifi className="h-3 w-3 mr-1" />
                              )}
                              Probar
                            </Button>
                            <Button
                              size="sm"
                              className="flex-1"
                              onClick={() => handleSync(c.id, 'completo')}
                              disabled={syncing === c.id || c.estado === 'desactivado'}
                            >
                              {syncing === c.id ? (
                                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                              ) : (
                                <Play className="h-3 w-3 mr-1" />
                              )}
                              Sincronizar
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* TAB: SYNC LOGS */}
        {/* ============================================ */}
        <TabsContent value="sync-logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Historial de Sincronizaciones
              </CardTitle>
              <CardDescription>Registro de todas las sincronizaciones e-commerce</CardDescription>
            </CardHeader>
            <CardContent>
              {syncLogs.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No hay registros de sincronizacion</p>
              ) : (
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Fecha</TableHead>
                        <TableHead>Conector</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="text-right">Procesados</TableHead>
                        <TableHead className="text-right">Creados</TableHead>
                        <TableHead className="text-right">Actualizados</TableHead>
                        <TableHead className="text-right">Errores</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {syncLogs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell className="text-xs">{formatDateTime(log.fecha_inicio)}</TableCell>
                          <TableCell>
                            <div className="font-medium">{log.connector_nombre || '-'}</div>
                            <div className="text-xs text-muted-foreground">{log.connector_plataforma || '-'}</div>
                          </TableCell>
                          <TableCell className="capitalize">{log.tipo_sync}</TableCell>
                          <TableCell>{getEstadoBadge(log.estado)}</TableCell>
                          <TableCell className="text-right">{log.registros_procesados}</TableCell>
                          <TableCell className="text-right text-green-600">{log.registros_creados}</TableCell>
                          <TableCell className="text-right text-blue-600">{log.registros_actualizados}</TableCell>
                          <TableCell className="text-right text-red-600">{log.registros_errores}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ============================================ */}
      {/* DIALOGS */}
      {/* ============================================ */}

      {/* Dialog: Cuenta Bancaria */}
      <Dialog open={showCuentaDialog} onOpenChange={setShowCuentaDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingCuenta ? 'Editar Cuenta Bancaria' : 'Nueva Cuenta Bancaria'}</DialogTitle>
            <DialogDescription>
              {editingCuenta ? 'Modifique los datos de la cuenta bancaria' : 'Registre una nueva cuenta bancaria para importar extractos'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre del Banco *</Label>
                <NumericInput placeholder="Banco Pichincha"
 value={cuentaForm.nombre_banco}
 onChange={(e) => setCuentaForm({ ...cuentaForm, nombre_banco: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>Tipo de Cuenta</Label>
 <Select
 value={cuentaForm.tipo_cuenta}
 onValueChange={(v) => setCuentaForm({ ...cuentaForm, tipo_cuenta: v })}
 >
 <SelectTrigger><SelectValue /></SelectTrigger>
 <SelectContent>
 <SelectItem value="corriente">Corriente</SelectItem>
 <SelectItem value="ahorros">Ahorros</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Número de Cuenta *</Label>
 <Input
 placeholder="2200001234"
 value={cuentaForm.numero_cuenta}
 onChange={(e) => setCuentaForm({ ...cuentaForm, numero_cuenta: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>SWIFT/BIC</Label>
 <Input
 placeholder="PICHECEQXXX"
 value={cuentaForm.swift_bic || ''}
 onChange={(e) => setCuentaForm({ ...cuentaForm, swift_bic: e.target.value })}
 />
 </div>
 </div>
 <div className="space-y-2">
 <Label>Banco (Ecuador) - auto-rellena SWIFT/BIC</Label>
 <Select
 value={bancoSeleccionado}
 onValueChange={(v) => {
 setBancoSeleccionado(v);
 const banco = BANCOS_EC[v];
 if (banco) {
 setCuentaForm((prev) => ({
 ...prev,
 nombre_banco: v,
 swift_bic: banco.swift_bic || prev.swift_bic || '',
 }));
 }
 }}
 >
 <SelectTrigger><SelectValue placeholder="Seleccione un banco" /></SelectTrigger>
 <SelectContent>
 {Object.keys(BANCOS_EC).map((b) => (
 <SelectItem key={b} value={b}>
 {b} {BANCOS_EC[b].manual ? '(ingresar SWIFT/BIC manual)' : ''}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Titular *</Label>
 <Input
 placeholder="Nombre del titular"
 value={cuentaForm.titular}
 onChange={(e) => setCuentaForm({ ...cuentaForm, titular: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>Moneda</Label>
 <Select
 value={cuentaForm.moneda}
 onValueChange={(v) => setCuentaForm({ ...cuentaForm, moneda: v })}
 >
 <SelectTrigger><SelectValue /></SelectTrigger>
 <SelectContent>
 <SelectItem value="USD">USD - Dolar</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Saldo Inicial</Label>
 <Input
 
 value={cuentaForm.saldo_inicial}
 onChange={(e) => setCuentaForm({ ...cuentaForm, saldo_inicial: parseFloat(e.target.value) || 0 })} />
              </div>
              <div className="space-y-2">
                <Label>Formato Extracto</Label>
                <Select
                  value={cuentaForm.formato_extracto}
                  onValueChange={(v) => setCuentaForm({ ...cuentaForm, formato_extracto: v })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="excel">Excel</SelectItem>
                    <SelectItem value="ofx">OFX</SelectItem>
                    <SelectItem value="mt940">MT940</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowCuentaDialog(false)}>Cancelar</Button>
            <Button onClick={handleSaveCuenta} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
              {editingCuenta ? 'Actualizar' : 'Crear'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog: Importar Extracto (subir archivo del banco) */}
      <Dialog open={showExtractoDialog} onOpenChange={setShowExtractoDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Importar Extracto Bancario</DialogTitle>
            <DialogDescription>Suba el archivo CSV descargado del banco para importar los movimientos automáticamente</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Cuenta Bancaria *</Label>
              <Select
                value={extractoForm.cuenta_bancaria_id}
                onValueChange={(v) => setExtractoForm({ ...extractoForm, cuenta_bancaria_id: v })}
              >
                <SelectTrigger><SelectValue placeholder="Seleccione una cuenta" /></SelectTrigger>
                <SelectContent>
                  {cuentas.filter(c => c.is_active).map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.nombre_banco} - {c.numero_cuenta}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Archivo del Extracto * (CSV)</Label>
              <Input
                type="file"
                accept=".csv,.txt"
                onChange={(e) => setExtractoFile(e.target.files?.[0] || null)}
              />
              <p className="text-xs text-muted-foreground">
                {extractoFile
                  ? `Archivo seleccionado: ${extractoFile.name}`
                  : 'El sistema detecta columnas como fecha, descripción, débito/crédito y saldo.'}
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => { setShowExtractoDialog(false); setExtractoFile(null); }}>Cancelar</Button>
            <Button onClick={handleImportExtracto} disabled={saving || !extractoFile}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
              Importar Extracto
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog: Conector E-Commerce */}
      <Dialog open={showConnectorDialog} onOpenChange={setShowConnectorDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingConnector ? 'Editar Conector' : 'Nuevo Conector E-Commerce'}</DialogTitle>
            <DialogDescription>
              {editingConnector ? 'Modifique la configuracion del conector' : 'Configure la conexion con su tienda online'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre *</Label>
                <Input
                  placeholder="Mi Tienda Shopify"
                  value={connectorForm.nombre}
                  onChange={(e) => setConnectorForm({ ...connectorForm, nombre: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Plataforma</Label>
                <Select
                  value={connectorForm.plataforma}
                  onValueChange={(v) => setConnectorForm({ ...connectorForm, plataforma: v })}
                  disabled={!!editingConnector}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="shopify">Shopify</SelectItem>
                    <SelectItem value="woocommerce">WooCommerce</SelectItem>
                    <SelectItem value="opencart">OpenCart</SelectItem>
                    <SelectItem value="prestashop">PrestaShop</SelectItem>
                    <SelectItem value="magento">Magento</SelectItem>
                    <SelectItem value="meli">Mercado Libre</SelectItem>
                    <SelectItem value="otro">Otro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>URL de la Tienda *</Label>
              <Input
                placeholder="https://mi-tienda.myshopify.com"
                value={connectorForm.url_tienda}
                onChange={(e) => setConnectorForm({ ...connectorForm, url_tienda: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>API Key</Label>
                <Input
                  type="password"
                  placeholder="API Key"
                  value={connectorForm.api_key || ''}
                  onChange={(e) => setConnectorForm({ ...connectorForm, api_key: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>API Secret</Label>
                <Input
                  type="password"
                  placeholder="API Secret"
                  value={connectorForm.api_secret || ''}
                  onChange={(e) => setConnectorForm({ ...connectorForm, api_secret: e.target.value })}
                />
              </div>
            </div>
            <Separator />
            <div>
              <Label className="mb-2 block">Opciones de Sincronización</Label>
              <div className="grid grid-cols-2 gap-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={connectorForm.sync_productos}
                    onChange={(e) => setConnectorForm({ ...connectorForm, sync_productos: e.target.checked })}
                    className="rounded"
                  />
                  <Package className="h-3 w-3" /> Productos
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={connectorForm.sync_ordenes}
                    onChange={(e) => setConnectorForm({ ...connectorForm, sync_ordenes: e.target.checked })}
                    className="rounded"
                  />
                  <ShoppingCart className="h-3 w-3" /> Ordenes
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={connectorForm.sync_clientes}
                    onChange={(e) => setConnectorForm({ ...connectorForm, sync_clientes: e.target.checked })}
                    className="rounded"
                  />
                  <Users className="h-3 w-3" /> Clientes
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={connectorForm.sync_inventario}
                    onChange={(e) => setConnectorForm({ ...connectorForm, sync_inventario: e.target.checked })}
                    className="rounded"
                  />
                  <BarChart3 className="h-3 w-3" /> Inventario
                </label>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowConnectorDialog(false)}>Cancelar</Button>
            <Button onClick={handleSaveConnector} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
              {editingConnector ? 'Actualizar' : 'Crear Conector'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog: Movimiento Detail */}
      <Dialog open={showMovimientoDetail} onOpenChange={setShowMovimientoDetail}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Detalle del Movimiento</DialogTitle>
          </DialogHeader>
          {selectedMovimiento && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-muted-foreground">Fecha:</span> {formatDate(selectedMovimiento.fecha)}</div>
                <div><span className="text-muted-foreground">Tipo:</span> {selectedMovimiento.tipo === 'credito' ? 'Crédito' : 'Débito'}</div>
                <div><span className="text-muted-foreground">Monto:</span> <span className="font-semibold">{formatCurrency(Number(selectedMovimiento.monto))}</span></div>
                <div><span className="text-muted-foreground">Saldo Posterior:</span> {selectedMovimiento.saldo_posterior ? formatCurrency(Number(selectedMovimiento.saldo_posterior)) : '-'}</div>
              </div>
              <Separator />
              <div className="space-y-1 text-sm">
                <div><span className="text-muted-foreground">Descripción:</span> {selectedMovimiento.descripcion || '-'}</div>
                <div><span className="text-muted-foreground">Beneficiario:</span> {selectedMovimiento.beneficiario || '-'}</div>
                <div><span className="text-muted-foreground">Referencia:</span> {selectedMovimiento.referencia || '-'}</div>
                <div><span className="text-muted-foreground">Documento:</span> {selectedMovimiento.documento || '-'}</div>
                <div><span className="text-muted-foreground">Categoria:</span> {selectedMovimiento.categoria || '-'}</div>
              </div>
              <Separator />
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Conciliacion:</span>
                  {getEstadoBadge(selectedMovimiento.conciliacion_estado)}
                </div>
                {selectedMovimiento.conciliacion_fecha && (
                  <div><span className="text-muted-foreground">Fecha Conciliacion:</span> {formatDateTime(selectedMovimiento.conciliacion_fecha)}</div>
                )}
                {selectedMovimiento.conciliacion_nota && (
                  <div><span className="text-muted-foreground">Nota:</span> {selectedMovimiento.conciliacion_nota}</div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
