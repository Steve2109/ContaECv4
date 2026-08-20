'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { NumericInput } from '@/components/ui/numeric-input';
import { useToast } from '@/hooks/use-toast';
import {
  getContabilidadStats, getCuentasContables, createCuentaContable, deleteCuentaContable, seedPlanCuentasDefault, getCatalogoOficial,
  getAsientosContables, createAsientoContable, aprobarAsiento, anularAsiento,
  getCuentasPorCobrar, createCuentaPorCobrar, getEnvejecimientoCartera,
  getPagos, createPago, confirmarPago, anularPago,
  getPeriodosFiscales, createPeriodoFiscal, cerrarPeriodoFiscal, reabrirPeriodoFiscal,
  getBalanceComprobacion,
  type CuentaContable, type CuentaContableCreate,
  type AsientoContable, type AsientoContableCreate,
  type CuentaPorCobrar, type CuentaPorCobrarCreate,
  type Pago, type PagoCreate,
  type PeriodoFiscal, type PeriodoFiscalCreate,
  type ContabilidadStats, type BalanceComprobacionResponse, type EnvejecimientoCarteraResponse,
} from '@/lib/api';
import {
  Loader2, Plus, RefreshCw, Trash2, CheckCircle2, XCircle, AlertTriangle,
  BookOpen, FileText, DollarSign, Clock, Calendar, BarChart3, Users,
} from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────

function fmtMoney(n: number): string {
  return `$${n.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null): string {
  if (!d) return '-';
  const dt = new Date(d);
  return dt.toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

const TIPOS_CUENTA = ['activo', 'pasivo', 'patrimonio', 'ingreso', 'gasto', 'costo'];
const TIPOS_ASIENTO = ['ordinario', 'apertura', 'cierre', 'ajuste'];
const TIPOS_PAGO = ['cobro', 'pago'];

// Catálogo se carga dinámicamente desde el backend (3,633 cuentas del MEF)
// El tipo CatalogoItem se define dentro de PlanCuentasTab


const NIVEL_OPTIONS = [
  { value: 1, label: 'Nivel 1 - Grupo' },
  { value: 2, label: 'Nivel 2 - Subgrupo' },
  { value: 3, label: 'Nivel 3 - Cuenta' },
  { value: 4, label: 'Nivel 4 - Subcuenta' },
  { value: 5, label: 'Nivel 5 - Auxiliar' },
  { value: 6, label: 'Nivel 6 - Detalle' },
];

function tipoCuentaColor(tipo: string): string {
  switch (tipo) {
    case 'activo': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    case 'pasivo': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    case 'patrimonio': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
    case 'ingreso': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200';
    case 'gasto': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
    case 'costo': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    default: return 'bg-gray-100 text-gray-800';
  }
}

function asientoStatusBadge(estado: string) {
  switch (estado) {
    case 'borrador': return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">{estado}</Badge>;
    case 'aprobado': return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">{estado}</Badge>;
    case 'anulado': return <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">{estado}</Badge>;
    default: return <Badge variant="secondary">{estado}</Badge>;
  }
}

function cxcStatusBadge(estado: string) {
  switch (estado) {
    case 'pendiente': return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">{estado}</Badge>;
    case 'vencida': return <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">{estado}</Badge>;
    case 'pagada': return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">{estado}</Badge>;
    case 'parcial': return <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">{estado}</Badge>;
    default: return <Badge variant="secondary">{estado}</Badge>;
  }
}

function pagoTipoBadge(tipo: string) {
  if (tipo === 'cobro') return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">{tipo}</Badge>;
  return <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200">{tipo}</Badge>;
}

function pagoStatusBadge(estado: string) {
  switch (estado) {
    case 'pendiente': return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">{estado}</Badge>;
    case 'confirmado': return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">{estado}</Badge>;
    case 'anulado': return <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">{estado}</Badge>;
    default: return <Badge variant="secondary">{estado}</Badge>;
  }
}

function periodoStatusBadge(estado: string) {
  switch (estado) {
    case 'abierto': return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">{estado}</Badge>;
    case 'cerrado': return <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">{estado}</Badge>;
    case 'en_cierre': return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">{estado}</Badge>;
    default: return <Badge variant="secondary">{estado}</Badge>;
  }
}

// ─── Main Component ─────────────────────────────────────────────

interface ContaECAccountingProps {
  companyId: string;
}

export function ContaECAccounting({ companyId }: ContaECAccountingProps) {
  const { toast } = useToast();
  const [stats, setStats] = useState<ContabilidadStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  const loadStats = useCallback(async () => {
    if (!companyId) return;
    setLoadingStats(true);
    try {
      const s = await getContabilidadStats(companyId);
      setStats(s);
    } catch {
      toast({ title: 'Error', description: 'No se pudieron cargar las estadísticas', variant: 'destructive' });
    } finally {
      setLoadingStats(false);
    }
  }, [companyId, toast]);

  useEffect(() => { loadStats(); }, [loadStats]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Contabilidad</h2>
          <p className="text-muted-foreground">Plan de cuentas, asientos, CxC y reportes contables</p>
        </div>
      </div>

      {/* Stats Cards */}
      {loadingStats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}><CardContent className="p-4 animate-pulse"><div className="h-12 bg-muted rounded" /></CardContent></Card>
          ))}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Cuentas</span>
                <div className="rounded-md bg-emerald-100 p-1.5 dark:bg-emerald-900"><BookOpen className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /></div>
              </div>
              <div className="text-2xl font-bold">{stats.total_cuentas_activas}</div>
              <p className="text-xs text-muted-foreground">de {stats.total_cuentas} total</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Asientos</span>
                <div className="rounded-md bg-blue-100 p-1.5 dark:bg-blue-900"><FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" /></div>
              </div>
              <div className="text-2xl font-bold">{stats.total_asientos_aprobados}</div>
              <p className="text-xs text-muted-foreground">de {stats.total_asientos} total</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">CxC Pendiente</span>
                <div className="rounded-md bg-amber-100 p-1.5 dark:bg-amber-900"><DollarSign className="h-4 w-4 text-amber-600 dark:text-amber-400" /></div>
              </div>
              <div className="text-2xl font-bold">{fmtMoney(stats.total_cxc_pendiente)}</div>
              <p className="text-xs text-muted-foreground">{stats.total_cxc} cuentas</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Períodos</span>
                <div className="rounded-md bg-purple-100 p-1.5 dark:bg-purple-900"><Calendar className="h-4 w-4 text-purple-600 dark:text-purple-400" /></div>
              </div>
              <div className="text-2xl font-bold">{stats.periodos_abiertos}</div>
              <p className="text-xs text-muted-foreground">{stats.periodo_actual || 'Sin período'}</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <Tabs defaultValue="plan-cuentas" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="plan-cuentas" className="gap-1.5"><BookOpen className="h-3.5 w-3.5" /><span className="hidden sm:inline">Plan de Cuentas</span></TabsTrigger>
          <TabsTrigger value="asientos" className="gap-1.5"><FileText className="h-3.5 w-3.5" /><span className="hidden sm:inline">Asientos</span></TabsTrigger>
          <TabsTrigger value="cxc" className="gap-1.5"><DollarSign className="h-3.5 w-3.5" /><span className="hidden sm:inline">CxC</span></TabsTrigger>
          <TabsTrigger value="pagos" className="gap-1.5"><Clock className="h-3.5 w-3.5" /><span className="hidden sm:inline">Pagos</span></TabsTrigger>
          <TabsTrigger value="periodos" className="gap-1.5"><Calendar className="h-3.5 w-3.5" /><span className="hidden sm:inline">Períodos</span></TabsTrigger>
          <TabsTrigger value="balance" className="gap-1.5"><BarChart3 className="h-3.5 w-3.5" /><span className="hidden sm:inline">Balance</span></TabsTrigger>
          <TabsTrigger value="envejecimiento" className="gap-1.5"><Users className="h-3.5 w-3.5" /><span className="hidden sm:inline">Cartera</span></TabsTrigger>
        </TabsList>

        <TabsContent value="plan-cuentas"><PlanCuentasTab companyId={companyId} onRefresh={loadStats} /></TabsContent>
        <TabsContent value="asientos"><AsientosTab companyId={companyId} onRefresh={loadStats} /></TabsContent>
        <TabsContent value="cxc"><CxCTab companyId={companyId} /></TabsContent>
        <TabsContent value="pagos"><PagosTab companyId={companyId} /></TabsContent>
        <TabsContent value="periodos"><PeriodosTab companyId={companyId} /></TabsContent>
        <TabsContent value="balance"><BalanceTab companyId={companyId} /></TabsContent>
        <TabsContent value="envejecimiento"><EnvejecimientoTab companyId={companyId} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ─── 1. Plan de Cuentas ─────────────────────────────────────────

function PlanCuentasTab({ companyId, onRefresh }: { companyId: string; onRefresh: () => void }) {
  const { toast } = useToast();
  const [cuentas, setCuentas] = useState<CuentaContable[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterTipo, setFilterTipo] = useState<string>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [creating, setCreating] = useState(false);
  const [codeSearchQuery, setCodeSearchQuery] = useState('');
  const [showCodeSelector, setShowCodeSelector] = useState(false);
  type CatalogoItem = { code: string; name: string; tipo: string; naturaleza: string; level: number };
  const [catalogo, setCatalogo] = useState<CatalogoItem[]>([]);
  const [_loadingCatalogo, setLoadingCatalogo] = useState(true);
  const [form, setForm] = useState<CuentaContableCreate>({
    codigo: '', nombre: '', tipo: 'activo', naturaleza: 'deudora', nivel: 1, es_cuenta_movimiento: true, es_imputable: true, saldo_inicial: 0, notas: '',
  });

  const loadCatalogo = useCallback(async () => {
    try {
      const data = await getCatalogoOficial();
      setCatalogo(data);
    } catch {
      // Fallback vacío si falla
      setCatalogo([]);
    } finally {
      setLoadingCatalogo(false);
    }
  }, []);

  useEffect(() => { loadCatalogo(); }, [loadCatalogo]);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getCuentasContables(companyId, filterTipo !== 'all' ? filterTipo : undefined, search || undefined);
      setCuentas(data.sort((a, b) => a.codigo.localeCompare(b.codigo)));
    } catch {
      toast({ title: 'Error', description: 'No se pudieron cargar las cuentas', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, filterTipo, search, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleSeed() {
    setSeeding(true);
    try {
      await seedPlanCuentasDefault(companyId);
      toast({ title: 'Plan generado', description: 'Plan de cuentas por defecto creado exitosamente' });
      loadData();
      onRefresh();
    } catch (err) {
      toast({ title: 'Error al generar plan', description: err instanceof Error ? err.message : 'No se pudo generar el plan. Intente de nuevo.', variant: 'destructive' });
    } finally {
      setSeeding(false);
    }
  }

  async function handleCreate() {
    if (!form.codigo.trim()) { toast({ title: 'Validacion', description: 'El codigo es obligatorio', variant: 'destructive' }); return; }
    if (!form.nombre.trim()) { toast({ title: 'Validacion', description: 'El nombre es obligatorio', variant: 'destructive' }); return; }
    setCreating(true);
    try {
      await createCuentaContable(form, companyId);
      toast({ title: 'Cuenta creada', description: `${form.codigo} - ${form.nombre}` });
      setShowCreate(false);
      setForm({ codigo: '', nombre: '', tipo: 'activo', naturaleza: 'deudora', nivel: 1, es_cuenta_movimiento: true, es_imputable: true, saldo_inicial: 0, notas: '' });
      loadData();
      onRefresh();
    } catch (err) {
      toast({ title: 'Error al crear cuenta', description: err instanceof Error ? err.message : 'No se pudo crear la cuenta. Verifique los datos e intente de nuevo.', variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteCuentaContable(id);
      toast({ title: 'Cuenta eliminada' });
      loadData();
      onRefresh();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo eliminar', variant: 'destructive' });
    }
  }

  function selectCode(item: CatalogoItem) {
    const nivel = item.level || item.code.split('.').length;
    setForm({ ...form, codigo: item.code, nombre: item.name, tipo: (item.tipo || 'activo') as typeof form.tipo, naturaleza: (item.naturaleza || 'deudora') as typeof form.naturaleza, nivel });
    setShowCodeSelector(false);
    setCodeSearchQuery('');
  }

  const filteredCodes = catalogo.filter(c =>
    codeSearchQuery === '' ||
    c.code.toLowerCase().includes(codeSearchQuery.toLowerCase()) ||
    c.name.toLowerCase().includes(codeSearchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Input placeholder="Buscar cuenta..." value={search} onChange={e => setSearch(e.target.value)} className="w-[200px]" />
        <Select value={filterTipo} onValueChange={setFilterTipo}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Tipo" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            {TIPOS_CUENTA.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nueva Cuenta</Button>
        <Button variant="outline" onClick={handleSeed} disabled={seeding} className="border-primary/30">
          {seeding ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
          Generar Plan por Defecto
        </Button>
      </div>
      {cuentas.length > 0 && (
        <p className="text-xs text-muted-foreground">El plan por defecto solo se genera cuando la empresa no tiene cuentas.</p>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : cuentas.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Codigo</th>
                    <th className="px-4 py-2 text-left font-medium">Nombre</th>
                    <th className="px-4 py-2 text-left font-medium">Tipo</th>
                    <th className="px-4 py-2 text-center font-medium">Naturaleza</th>
                    <th className="px-4 py-2 text-center font-medium">Nivel</th>
                    <th className="px-4 py-2 text-right font-medium">Saldo Actual</th>
                    <th className="px-4 py-2 text-right font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {cuentas.map(c => (
                    <tr key={c.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => { setForm({ codigo: c.codigo, nombre: c.nombre, tipo: c.tipo, naturaleza: c.naturaleza, nivel: c.nivel, es_cuenta_movimiento: c.es_cuenta_movimiento, es_imputable: c.es_imputable, saldo_inicial: c.saldo_inicial, notas: c.notas || '', descripcion: c.descripcion }); setShowCreate(true); }}>
                      <td className="px-4 py-2 font-mono text-xs">{c.codigo}</td>
                      <td className="px-4 py-2">{c.nombre}</td>
                      <td className="px-4 py-2"><Badge className={tipoCuentaColor(c.tipo)}>{c.tipo}</Badge></td>
                      <td className="px-4 py-2 text-center text-xs capitalize">{c.naturaleza}</td>
                      <td className="px-4 py-2 text-center">{c.nivel}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(c.saldo_actual)}</td>
                      <td className="px-4 py-2 text-right">
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={(e) => { e.stopPropagation(); handleDelete(c.id); }}><Trash2 className="h-3.5 w-3.5" /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <BookOpen className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin cuentas contables</h3>
            <p className="text-muted-foreground text-sm mt-1">Genere el plan por defecto o cree cuentas manualmente</p>
          </CardContent>
        </Card>
      )}

      {/* Code Selector Dialog */}
      <Dialog open={showCodeSelector} onOpenChange={setShowCodeSelector}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Seleccionar Codigo del Plan de Cuentas</DialogTitle>
          </DialogHeader>
          <Input
            placeholder="Buscar por codigo o nombre..."
            value={codeSearchQuery}
            onChange={e => setCodeSearchQuery(e.target.value)}
            autoFocus
          />
          <div className="flex-1 overflow-y-auto max-h-[60vh] border rounded-md">
            {filteredCodes.length > 0 ? (
              <div className="divide-y">
                {filteredCodes.map((item, idx) => {
                  const depth = (item.level || item.code.split('.').length);
                  return (
                    <button
                      key={idx}
                      className="w-full text-left px-4 py-2 hover:bg-muted/50 transition-colors flex items-center gap-3"
                      style={{ paddingLeft: `${12 + depth * 16}px` }}
                      onClick={() => selectCode(item)}
                    >
                      <span className="font-mono text-xs text-primary font-medium min-w-[80px]">{item.code}</span>
                      <span className="text-sm flex-1">{item.name}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {NIVEL_OPTIONS.find(n => n.value === (item.level || depth))?.label || `Nivel ${item.level || depth}`}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-sm">No se encontraron cuentas con ese criterio</div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Nueva Cuenta Contable</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Codigo</Label>
                <div className="flex gap-2">
                  <Input value={form.codigo} onChange={e => setForm({ ...form, codigo: e.target.value })} placeholder="1.1.01" className="flex-1" />
                  <Button variant="outline" type="button" onClick={() => setShowCodeSelector(true)} className="shrink-0">
                    <BookOpen className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Nivel</Label>
                <Select value={String(form.nivel || 1)} onValueChange={v => setForm({ ...form, nivel: Number(v) })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {NIVEL_OPTIONS.map(n => <SelectItem key={n.value} value={String(n.value)}>{n.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2"><Label>Nombre</Label><Input value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} placeholder="Caja General" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={form.tipo} onValueChange={v => setForm({ ...form, tipo: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TIPOS_CUENTA.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Naturaleza</Label>
                <Select value={form.naturaleza} onValueChange={v => setForm({ ...form, naturaleza: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="deudora">Deudora</SelectItem>
                    <SelectItem value="acreedora">Acreedora</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2"><Label>Descripcion</Label><Input value={form.descripcion || ''} onChange={e => setForm({ ...form, descripcion: e.target.value })} placeholder="Descripcion de la cuenta" /></div>
            <div className="space-y-2"><Label>Notas</Label><textarea className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" value={form.notas || ''} onChange={e => setForm({ ...form, notas: e.target.value })} placeholder="Notas adicionales..." /></div>
            <div className="space-y-2"><Label>Saldo Inicial</Label><NumericInput value={form.saldo_inicial || 0} onChange={e => setForm({ ...form, saldo_inicial: Number(e.target.value) })} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}


// ─── 2. Asientos Contables ──────────────────────────────────────

function AsientosTab({ companyId, onRefresh }: { companyId: string; onRefresh: () => void }) {
  const { toast } = useToast();
  const [asientos, setAsientos] = useState<AsientoContable[]>([]);
  const [cuentas, setCuentas] = useState<CuentaContable[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [filterEstado, setFilterEstado] = useState<string>('all');
  const [form, setForm] = useState({ fecha: new Date().toISOString().slice(0, 10), tipo: 'ordinario', concepto: '' });
  const [detalles, setDetalles] = useState<Array<{ cuenta_contable_id: string; debito: string; credito: string }>>([
    { cuenta_contable_id: '', debito: '0', credito: '0' },
    { cuenta_contable_id: '', debito: '0', credito: '0' },
  ]);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [as, cu] = await Promise.all([
        getAsientosContables(companyId, filterEstado !== 'all' ? filterEstado : undefined),
        getCuentasContables(companyId),
      ]);
      setAsientos(as);
      setCuentas(cu.sort((a, b) => a.codigo.localeCompare(b.codigo)));
    } catch {
      toast({ title: 'Error', description: 'No se pudieron cargar asientos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, filterEstado, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  const totalDebitos = detalles.reduce((s, d) => s + (Number(d.debito) || 0), 0);
  const totalCreditos = detalles.reduce((s, d) => s + (Number(d.credito) || 0), 0);
  const cuadrado = Math.abs(totalDebitos - totalCreditos) < 0.01;

  function addLine() { setDetalles([...detalles, { cuenta_contable_id: '', debito: '0', credito: '0' }]); }
  function removeLine(i: number) { setDetalles(detalles.filter((_, idx) => idx !== i)); }
  function updateLine(i: number, field: 'cuenta_contable_id' | 'debito' | 'credito', value: string) {
    const updated = [...detalles];
    updated[i] = { ...updated[i], [field]: value };
    setDetalles(updated);
  }

  async function handleCreate() {
    if (!form.concepto.trim()) { toast({ title: 'Validación', description: 'Ingrese un concepto', variant: 'destructive' }); return; }
    if (!cuadrado) { toast({ title: 'Validación', description: 'Débitos y créditos deben ser iguales', variant: 'destructive' }); return; }
    const lineasValidas = detalles.filter(d => d.cuenta_contable_id && (Number(d.debito) > 0 || Number(d.credito) > 0));
    if (lineasValidas.length < 2) { toast({ title: 'Validación', description: 'Mínimo 2 líneas de detalle', variant: 'destructive' }); return; }

    setCreating(true);
    try {
      const data: AsientoContableCreate = {
        fecha: form.fecha,
        tipo: form.tipo,
        concepto: form.concepto,
        detalles: lineasValidas.map(d => ({
          cuenta_contable_id: d.cuenta_contable_id,
          debito: Number(d.debito) || 0,
          credito: Number(d.credito) || 0,
        })),
      };
      await createAsientoContable(data, companyId);
      toast({ title: 'Asiento creado', description: `Concepto: ${form.concepto}` });
      setShowCreate(false);
      setForm({ fecha: new Date().toISOString().slice(0, 10), tipo: 'ordinario', concepto: '' });
      setDetalles([{ cuenta_contable_id: '', debito: '0', credito: '0' }, { cuenta_contable_id: '', debito: '0', credito: '0' }]);
      loadData();
      onRefresh();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo crear el asiento', variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  }

  async function handleAprobar(id: string) {
    try {
      await aprobarAsiento(id);
      toast({ title: 'Asiento aprobado' });
      loadData();
      onRefresh();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo aprobar', variant: 'destructive' });
    }
  }

  async function handleAnular(id: string) {
    try {
      await anularAsiento(id);
      toast({ title: 'Asiento anulado' });
      loadData();
      onRefresh();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo anular', variant: 'destructive' });
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterEstado} onValueChange={setFilterEstado}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="borrador">Borrador</SelectItem>
            <SelectItem value="aprobado">Aprobado</SelectItem>
            <SelectItem value="anulado">Anulado</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nuevo Asiento</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : asientos.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Número</th>
                    <th className="px-4 py-2 text-left font-medium">Fecha</th>
                    <th className="px-4 py-2 text-left font-medium">Concepto</th>
                    <th className="px-4 py-2 text-center font-medium">Tipo</th>
                    <th className="px-4 py-2 text-center font-medium">Estado</th>
                    <th className="px-4 py-2 text-right font-medium">Débitos</th>
                    <th className="px-4 py-2 text-right font-medium">Créditos</th>
                    <th className="px-4 py-2 text-right font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {asientos.map(a => (
                    <tr key={a.id} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs">{a.numero}</td>
                      <td className="px-4 py-2 text-xs">{fmtDate(a.fecha)}</td>
                      <td className="px-4 py-2 max-w-[200px] truncate">{a.concepto}</td>
                      <td className="px-4 py-2 text-center text-xs capitalize">{a.tipo}</td>
                      <td className="px-4 py-2 text-center">{asientoStatusBadge(a.estado)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(a.total_debitos)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(a.total_creditos)}</td>
                      <td className="px-4 py-2 text-right">
                        <div className="flex justify-end gap-1">
                          {a.estado === 'borrador' && (
                            <Button variant="ghost" size="sm" className="h-7 text-emerald-600" onClick={() => handleAprobar(a.id)}>
                              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />Aprobar
                            </Button>
                          )}
                          {a.estado !== 'anulado' && (
                            <Button variant="ghost" size="sm" className="h-7 text-destructive" onClick={() => handleAnular(a.id)}>
                              <XCircle className="h-3.5 w-3.5 mr-1" />Anular
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin asientos contables</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree un nuevo asiento para comenzar</p>
          </CardContent>
        </Card>
      )}

      {/* Create Asiento Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Nuevo Asiento Contable</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2"><Label>Fecha</Label><Input type="date" value={form.fecha} onChange={e => setForm({ ...form, fecha: e.target.value })} /></div>
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={form.tipo} onValueChange={v => setForm({ ...form, tipo: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TIPOS_ASIENTO.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2 col-span-1"><Label>Concepto</Label><Input value={form.concepto} onChange={e => setForm({ ...form, concepto: e.target.value })} placeholder="Descripción del asiento" /></div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Detalle del Asiento</Label>
                <Button variant="outline" size="sm" onClick={addLine}><Plus className="h-3.5 w-3.5 mr-1" />Línea</Button>
              </div>
              <div className="space-y-2">
                {detalles.map((d, i) => (
                  <div key={i} className="grid grid-cols-[1fr_100px_100px_32px] gap-2 items-end">
                    <div>
                      {i === 0 && <span className="text-xs text-muted-foreground">Cuenta</span>}
                      <Select value={d.cuenta_contable_id} onValueChange={v => updateLine(i, 'cuenta_contable_id', v)}>
                        <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Seleccione cuenta" /></SelectTrigger>
                        <SelectContent>
                          {cuentas.filter(c => c.es_cuenta_movimiento || c.es_imputable).map(c => (
                            <SelectItem key={c.id} value={c.id}>{c.codigo} - {c.nombre}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      {i === 0 && <span className="text-xs text-muted-foreground">Débito</span>}
 <NumericInput className="h-8 text-xs" value={d.debito} onChange={e => updateLine(i, 'debito', e.target.value)} />
                    </div>
                    <div>
                      {i === 0 && <span className="text-xs text-muted-foreground">Crédito</span>}
 <NumericInput className="h-8 text-xs" value={d.credito} onChange={e => updateLine(i, 'credito', e.target.value)} />
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => removeLine(i)} disabled={detalles.length <= 2}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between pt-2 border-t">
                <span className="text-sm font-medium">Totales:</span>
                <div className="flex gap-6">
                  <span className="text-sm">Débitos: <span className="font-mono font-bold">{fmtMoney(totalDebitos)}</span></span>
                  <span className="text-sm">Créditos: <span className="font-mono font-bold">{fmtMoney(totalCreditos)}</span></span>
                  {cuadrado ? (
                    <Badge className="bg-emerald-100 text-emerald-800"><CheckCircle2 className="h-3 w-3 mr-1" />Cuadrado</Badge>
                  ) : (
                    <Badge variant="destructive"><AlertTriangle className="h-3 w-3 mr-1" />Diferencia: {fmtMoney(Math.abs(totalDebitos - totalCreditos))}</Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={creating || !cuadrado}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear Asiento</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── 3. Cuentas por Cobrar ──────────────────────────────────────

function CxCTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const [cxc, setCxc] = useState<CuentaPorCobrar[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEstado, setFilterEstado] = useState<string>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<CuentaPorCobrarCreate>({
    fecha_emision: new Date().toISOString().slice(0, 10), monto_total: 0, dias_credito: 30,
  });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getCuentasPorCobrar(companyId, filterEstado !== 'all' ? filterEstado : undefined);
      setCxc(data);
    } catch {
      toast({ title: 'Error', description: 'No se pudieron cargar CxC', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, filterEstado, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  const totalPendiente = cxc.filter(c => c.estado !== 'pagada').reduce((s, c) => s + c.monto_pendiente, 0);
  const totalVencida = cxc.filter(c => c.estado === 'vencida').reduce((s, c) => s + c.monto_pendiente, 0);
  const totalPagada = cxc.filter(c => c.estado === 'pagada').reduce((s, c) => s + c.monto_pagado, 0);

  async function handleCreate() {
    if (!form.monto_total || form.monto_total <= 0) { toast({ title: 'Validación', description: 'Monto total requerido', variant: 'destructive' }); return; }
    setCreating(true);
    try {
      await createCuentaPorCobrar(form, companyId);
      toast({ title: 'CxC creada', description: fmtMoney(form.monto_total) });
      setShowCreate(false);
      setForm({ fecha_emision: new Date().toISOString().slice(0, 10), monto_total: 0, dias_credito: 30 });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo crear', variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Aging Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Pendiente</p><p className="text-xl font-bold text-amber-600">{fmtMoney(totalPendiente)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Vencida</p><p className="text-xl font-bold text-red-600">{fmtMoney(totalVencida)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Cobrada</p><p className="text-xl font-bold text-emerald-600">{fmtMoney(totalPagada)}</p></CardContent></Card>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterEstado} onValueChange={setFilterEstado}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="pendiente">Pendiente</SelectItem>
            <SelectItem value="vencida">Vencida</SelectItem>
            <SelectItem value="pagada">Pagada</SelectItem>
            <SelectItem value="parcial">Parcial</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nueva CxC</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : cxc.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Factura</th>
                    <th className="px-4 py-2 text-left font-medium">Cliente</th>
                    <th className="px-4 py-2 text-left font-medium">Emisión</th>
                    <th className="px-4 py-2 text-left font-medium">Vencimiento</th>
                    <th className="px-4 py-2 text-right font-medium">Total</th>
                    <th className="px-4 py-2 text-right font-medium">Pagado</th>
                    <th className="px-4 py-2 text-right font-medium">Pendiente</th>
                    <th className="px-4 py-2 text-center font-medium">Días Venc.</th>
                    <th className="px-4 py-2 text-center font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {cxc.map(c => (
                    <tr key={c.id} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs">{c.numero_factura || '-'}</td>
                      <td className="px-4 py-2">{c.cliente_nombre || c.cliente_identificacion || '-'}</td>
                      <td className="px-4 py-2 text-xs">{fmtDate(c.fecha_emision)}</td>
                      <td className="px-4 py-2 text-xs">{fmtDate(c.fecha_vencimiento)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(c.monto_total)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(c.monto_pagado)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs font-medium">{fmtMoney(c.monto_pendiente)}</td>
                      <td className="px-4 py-2 text-center text-xs">{c.dias_vencida > 0 ? c.dias_vencida : '-'}</td>
                      <td className="px-4 py-2 text-center">{cxcStatusBadge(c.estado)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin cuentas por cobrar</h3>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>Nueva Cuenta por Cobrar</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Fecha Emisión</Label><Input type="date" value={form.fecha_emision} onChange={e => setForm({ ...form, fecha_emision: e.target.value })} /></div>
              <div className="space-y-2"><Label>Fecha Vencimiento</Label><Input type="date" value={form.fecha_vencimiento || ''} onChange={e => setForm({ ...form, fecha_vencimiento: e.target.value || undefined })} /></div>
            </div>
            <div className="space-y-2"><Label>Cliente</Label><Input value={form.cliente_nombre || ''} onChange={e => setForm({ ...form, cliente_nombre: e.target.value })} placeholder="Nombre del cliente" /></div>
            <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2"><Label>Monto Total</Label><NumericInput value={form.monto_total || ''} onChange={e => setForm({ ...form, monto_total: Number(e.target.value) })} /></div>
 <div className="space-y-2"><Label>Días Crédito</Label><NumericInput value={form.dias_credito || 30} onChange={e => setForm({ ...form, dias_credito: Number(e.target.value) })} /></div>
            </div>
            <div className="space-y-2"><Label>Observaciones</Label><Input value={form.observaciones || ''} onChange={e => setForm({ ...form, observaciones: e.target.value })} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── 4. Pagos / Cobros ──────────────────────────────────────────

function PagosTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const [pagos, setPagos] = useState<Pago[]>([]);
  const [cxc, setCxc] = useState<CuentaPorCobrar[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [filterTipo, setFilterTipo] = useState<string>('all');
  const [form, setForm] = useState<PagoCreate>({ tipo: 'cobro', fecha: new Date().toISOString().slice(0, 10), monto: 0, forma_pago: 'efectivo' });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [p, c] = await Promise.all([
        getPagos(companyId, filterTipo !== 'all' ? filterTipo : undefined),
        getCuentasPorCobrar(companyId),
      ]);
      setPagos(p);
      setCxc(c.filter(x => x.estado !== 'pagada'));
    } catch {
      toast({ title: 'Error', description: 'No se pudieron cargar pagos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, filterTipo, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCreate() {
    if (!form.monto || form.monto <= 0) { toast({ title: 'Validación', description: 'Monto requerido', variant: 'destructive' }); return; }
    setCreating(true);
    try {
      await createPago(form, companyId);
      toast({ title: 'Pago registrado', description: `${form.tipo === 'cobro' ? 'Cobro' : 'Pago'} por ${fmtMoney(form.monto)}` });
      setShowCreate(false);
      setForm({ tipo: 'cobro', fecha: new Date().toISOString().slice(0, 10), monto: 0, forma_pago: 'efectivo' });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo registrar', variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  }

  async function handleConfirmar(id: string) {
    try {
      await confirmarPago(id);
      toast({ title: 'Pago confirmado' });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo confirmar', variant: 'destructive' });
    }
  }

  async function handleAnular(id: string) {
    try {
      await anularPago(id);
      toast({ title: 'Pago anulado' });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo anular', variant: 'destructive' });
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterTipo} onValueChange={setFilterTipo}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="Tipo" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="cobro">Cobros</SelectItem>
            <SelectItem value="pago">Pagos</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nuevo Pago</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : pagos.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Número</th>
                    <th className="px-4 py-2 text-left font-medium">Fecha</th>
                    <th className="px-4 py-2 text-center font-medium">Tipo</th>
                    <th className="px-4 py-2 text-left font-medium">Tercero</th>
                    <th className="px-4 py-2 text-right font-medium">Monto</th>
                    <th className="px-4 py-2 text-center font-medium">Forma Pago</th>
                    <th className="px-4 py-2 text-center font-medium">Estado</th>
                    <th className="px-4 py-2 text-right font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {pagos.map(p => (
                    <tr key={p.id} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs">{p.numero}</td>
                      <td className="px-4 py-2 text-xs">{fmtDate(p.fecha)}</td>
                      <td className="px-4 py-2 text-center">{pagoTipoBadge(p.tipo)}</td>
                      <td className="px-4 py-2">{p.tercero_nombre || '-'}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(p.monto)}</td>
                      <td className="px-4 py-2 text-center text-xs capitalize">{p.forma_pago}</td>
                      <td className="px-4 py-2 text-center">{pagoStatusBadge(p.estado)}</td>
                      <td className="px-4 py-2 text-right">
                        <div className="flex justify-end gap-1">
                          {p.estado === 'pendiente' && (
                            <Button variant="ghost" size="sm" className="h-7 text-emerald-600" onClick={() => handleConfirmar(p.id)}>
                              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />Confirmar
                            </Button>
                          )}
                          {p.estado !== 'anulado' && (
                            <Button variant="ghost" size="sm" className="h-7 text-destructive" onClick={() => handleAnular(p.id)}>
                              <XCircle className="h-3.5 w-3.5 mr-1" />Anular
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin pagos registrados</h3>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>Registrar Pago / Cobro</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={form.tipo} onValueChange={v => setForm({ ...form, tipo: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TIPOS_PAGO.map(t => <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Fecha</Label><Input type="date" value={form.fecha} onChange={e => setForm({ ...form, fecha: e.target.value })} /></div>
            </div>
            <div className="space-y-2">
              <Label>Cuenta por Cobrar (opcional)</Label>
              <Select value={form.cuenta_por_cobrar_id || 'none'} onValueChange={v => setForm({ ...form, cuenta_por_cobrar_id: v === 'none' ? undefined : v })}>
                <SelectTrigger><SelectValue placeholder="Seleccionar CxC" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Ninguna</SelectItem>
                  {cxc.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.cliente_nombre || c.numero_factura || c.id.slice(0, 8)} - {fmtMoney(c.monto_pendiente)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label>Tercero</Label><Input value={form.tercero_nombre || ''} onChange={e => setForm({ ...form, tercero_nombre: e.target.value })} placeholder="Nombre del tercero" /></div>
            <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2"><Label>Monto</Label><NumericInput value={form.monto || ''} onChange={e => setForm({ ...form, monto: Number(e.target.value) })} /></div>
              <div className="space-y-2">
                <Label>Forma de Pago</Label>
                <Select value={form.forma_pago || 'efectivo'} onValueChange={v => setForm({ ...form, forma_pago: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    <SelectItem value="cheque">Cheque</SelectItem>
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2"><Label>Referencia</Label><Input value={form.referencia || ''} onChange={e => setForm({ ...form, referencia: e.target.value })} placeholder="# cheque, transferencia, etc." /></div>
            <div className="space-y-2"><Label>Observaciones</Label><Input value={form.observaciones || ''} onChange={e => setForm({ ...form, observaciones: e.target.value })} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Registrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── 5. Períodos Fiscales ───────────────────────────────────────

function PeriodosTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const [periodos, setPeriodos] = useState<PeriodoFiscal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [filterEstado, setFilterEstado] = useState<string>('all');
  const [form, setForm] = useState<PeriodoFiscalCreate>({
    nombre: '', anio: new Date().getFullYear(), mes: new Date().getMonth() + 1,
    fecha_inicio: '', fecha_fin: '',
  });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getPeriodosFiscales(companyId, filterEstado !== 'all' ? filterEstado : undefined);
      setPeriodos(data);
    } catch {
      toast({ title: 'Error', description: 'No se pudieron cargar períodos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, filterEstado, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCreate() {
    if (!form.nombre || !form.fecha_inicio || !form.fecha_fin) {
      toast({ title: 'Validación', description: 'Complete todos los campos', variant: 'destructive' }); return;
    }
    setCreating(true);
    try {
      await createPeriodoFiscal(form, companyId);
      toast({ title: 'Período creado', description: form.nombre });
      setShowCreate(false);
      setForm({ nombre: '', anio: new Date().getFullYear(), mes: new Date().getMonth() + 1, fecha_inicio: '', fecha_fin: '' });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo crear', variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  }

  async function handleCerrar(id: string) {
    try {
      await cerrarPeriodoFiscal(id);
      toast({ title: 'Período cerrado' });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo cerrar', variant: 'destructive' });
    }
  }

  async function handleReabrir(id: string) {
    try {
      await reabrirPeriodoFiscal(id);
      toast({ title: 'Período reabierto' });
      loadData();
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'No se pudo reabrir', variant: 'destructive' });
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterEstado} onValueChange={setFilterEstado}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="abierto">Abierto</SelectItem>
            <SelectItem value="cerrado">Cerrado</SelectItem>
            <SelectItem value="en_cierre">En Cierre</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nuevo Período</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : periodos.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Nombre</th>
                    <th className="px-4 py-2 text-center font-medium">Año</th>
                    <th className="px-4 py-2 text-center font-medium">Mes</th>
                    <th className="px-4 py-2 text-left font-medium">Inicio</th>
                    <th className="px-4 py-2 text-left font-medium">Fin</th>
                    <th className="px-4 py-2 text-center font-medium">Estado</th>
                    <th className="px-4 py-2 text-right font-medium">Asientos</th>
                    <th className="px-4 py-2 text-right font-medium">Débitos</th>
                    <th className="px-4 py-2 text-right font-medium">Créditos</th>
                    <th className="px-4 py-2 text-right font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {periodos.map(p => (
                    <tr key={p.id} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2 font-medium">{p.nombre}</td>
                      <td className="px-4 py-2 text-center">{p.anio}</td>
                      <td className="px-4 py-2 text-center">{p.mes || '-'}</td>
                      <td className="px-4 py-2 text-xs">{fmtDate(p.fecha_inicio)}</td>
                      <td className="px-4 py-2 text-xs">{fmtDate(p.fecha_fin)}</td>
                      <td className="px-4 py-2 text-center">{periodoStatusBadge(p.estado)}</td>
                      <td className="px-4 py-2 text-right">{p.total_asientos}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(p.total_debitos)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(p.total_creditos)}</td>
                      <td className="px-4 py-2 text-right">
                        <div className="flex justify-end gap-1">
                          {p.estado === 'abierto' && (
                            <Button variant="ghost" size="sm" className="h-7 text-amber-600" onClick={() => handleCerrar(p.id)}>
                              <XCircle className="h-3.5 w-3.5 mr-1" />Cerrar
                            </Button>
                          )}
                          {p.estado === 'cerrado' && (
                            <Button variant="ghost" size="sm" className="h-7 text-emerald-600" onClick={() => handleReabrir(p.id)}>
                              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />Reabrir
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin períodos fiscales</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree un período para comenzar a registrar asientos</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>Nuevo Período Fiscal</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Nombre</Label><Input value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} placeholder="Enero 2025" /></div>
            <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2"><Label>Año</Label><NumericInput value={form.anio} onChange={e => setForm({ ...form, anio: Number(e.target.value) })} /></div>
 <div className="space-y-2"><Label>Mes</Label><NumericInput min={1} max={12} value={form.mes || ''} onChange={e => setForm({ ...form, mes: Number(e.target.value) || null })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Fecha Inicio</Label><Input type="date" value={form.fecha_inicio} onChange={e => setForm({ ...form, fecha_inicio: e.target.value })} /></div>
              <div className="space-y-2"><Label>Fecha Fin</Label><Input type="date" value={form.fecha_fin} onChange={e => setForm({ ...form, fecha_fin: e.target.value })} /></div>
            </div>
            <div className="space-y-2"><Label>Observaciones</Label><Input value={form.observaciones || ''} onChange={e => setForm({ ...form, observaciones: e.target.value })} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── 6. Balance de Comprobación ─────────────────────────────────

function BalanceTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const [balance, setBalance] = useState<BalanceComprobacionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [anio, setAnio] = useState(new Date().getFullYear());

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getBalanceComprobacion(companyId, anio);
      setBalance(data);
    } catch {
      toast({ title: 'Error', description: 'No se pudo cargar el balance', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, anio, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <Label>Año:</Label>
 <NumericInput value={anio} onChange={e => setAnio(Number(e.target.value))} className="w-[100px]" />
        </div>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : balance && balance.items.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Código</th>
                    <th className="px-4 py-2 text-left font-medium">Nombre</th>
                    <th className="px-4 py-2 text-center font-medium">Tipo</th>
                    <th className="px-4 py-2 text-right font-medium">Débitos</th>
                    <th className="px-4 py-2 text-right font-medium">Créditos</th>
                    <th className="px-4 py-2 text-right font-medium">Saldo Deudor</th>
                    <th className="px-4 py-2 text-right font-medium">Saldo Acreedor</th>
                  </tr>
                </thead>
                <tbody>
                  {balance.items.map((item, i) => (
                    <tr key={i} className={`border-t hover:bg-muted/30 ${item.nivel === 1 ? 'font-semibold bg-muted/20' : ''}`}>
                      <td className="px-4 py-2 font-mono text-xs">{item.codigo}</td>
                      <td className="px-4 py-2" style={{ paddingLeft: `${item.nivel * 12 + 16}px` }}>{item.nombre}</td>
                      <td className="px-4 py-2 text-center"><Badge className={tipoCuentaColor(item.tipo)} variant="secondary">{item.tipo}</Badge></td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(item.total_debitos)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{fmtMoney(item.total_creditos)}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{item.saldo_deudor > 0 ? fmtMoney(item.saldo_deudor) : '-'}</td>
                      <td className="px-4 py-2 text-right font-mono text-xs">{item.saldo_acreedor > 0 ? fmtMoney(item.saldo_acreedor) : '-'}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-muted/50 sticky bottom-0 font-bold">
                  <tr>
                    <td className="px-4 py-3" colSpan={3}>TOTALES</td>
                    <td className="px-4 py-3 text-right font-mono">{fmtMoney(balance.total_debitos)}</td>
                    <td className="px-4 py-3 text-right font-mono">{fmtMoney(balance.total_creditos)}</td>
                    <td className="px-4 py-3 text-right font-mono">{fmtMoney(balance.total_saldo_deudor)}</td>
                    <td className="px-4 py-3 text-right font-mono">{fmtMoney(balance.total_saldo_acreedor)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin datos de balance</h3>
            <p className="text-muted-foreground text-sm mt-1">Registre asientos contables para generar el balance</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── 7. Envejecimiento de Cartera ───────────────────────────────

function EnvejecimientoTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const [data, setData] = useState<EnvejecimientoCarteraResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const resp = await getEnvejecimientoCartera(companyId);
      setData(resp);
    } catch {
      toast({ title: 'Error', description: 'No se pudo cargar envejecimiento', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [companyId, toast]);

  useEffect(() => { loadData(); }, [loadData]);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : data && data.items.length > 0 ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-4 sm:grid-cols-7 gap-3">
            <Card><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">Vigente</p><p className="text-sm font-bold text-emerald-600">{fmtMoney(data.total_vigente)}</p></CardContent></Card>
            <Card><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">1-30 días</p><p className="text-sm font-bold text-blue-600">{fmtMoney(data.total_1_30)}</p></CardContent></Card>
            <Card><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">31-60 días</p><p className="text-sm font-bold text-amber-600">{fmtMoney(data.total_31_60)}</p></CardContent></Card>
            <Card><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">61-90 días</p><p className="text-sm font-bold text-orange-600">{fmtMoney(data.total_61_90)}</p></CardContent></Card>
            <Card><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">91-180 días</p><p className="text-sm font-bold text-red-600">{fmtMoney(data.total_91_180)}</p></CardContent></Card>
            <Card><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">180+ días</p><p className="text-sm font-bold text-red-800">{fmtMoney(data.total_mas_180)}</p></CardContent></Card>
            <Card className="border-emerald-200 dark:border-emerald-800"><CardContent className="p-3"><p className="text-[10px] text-muted-foreground">Total</p><p className="text-sm font-bold">{fmtMoney(data.total_general)}</p></CardContent></Card>
          </div>

          {/* Detail Table */}
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">Cliente</th>
                      <th className="px-4 py-2 text-left font-medium">Identificación</th>
                      <th className="px-4 py-2 text-right font-medium">Total</th>
                      <th className="px-4 py-2 text-right font-medium">Vigente</th>
                      <th className="px-4 py-2 text-right font-medium">1-30</th>
                      <th className="px-4 py-2 text-right font-medium">31-60</th>
                      <th className="px-4 py-2 text-right font-medium">61-90</th>
                      <th className="px-4 py-2 text-right font-medium">91-180</th>
                      <th className="px-4 py-2 text-right font-medium">180+</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item, i) => (
                      <tr key={i} className="border-t hover:bg-muted/30">
                        <td className="px-4 py-2 font-medium">{item.cliente_nombre}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">{item.cliente_identificacion || '-'}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs font-bold">{fmtMoney(item.total)}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{item.vigente > 0 ? fmtMoney(item.vigente) : '-'}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{item.dias_1_30 > 0 ? fmtMoney(item.dias_1_30) : '-'}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{item.dias_31_60 > 0 ? fmtMoney(item.dias_31_60) : '-'}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{item.dias_61_90 > 0 ? fmtMoney(item.dias_61_90) : '-'}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{item.dias_91_180 > 0 ? fmtMoney(item.dias_91_180) : '-'}</td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{item.dias_mas_180 > 0 ? fmtMoney(item.dias_mas_180) : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-muted/50 sticky bottom-0 font-bold">
                    <tr>
                      <td className="px-4 py-3" colSpan={2}>TOTALES</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_general)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_vigente)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_1_30)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_31_60)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_61_90)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_91_180)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmtMoney(data.total_mas_180)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin datos de cartera</h3>
            <p className="text-muted-foreground text-sm mt-1">Registre cuentas por cobrar para ver el envejecimiento</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
