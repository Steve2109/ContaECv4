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
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { NumericInput } from '@/components/ui/numeric-input';
import {
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  BarChart3,
  Target,
  Loader2,
  Eye,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getPresupuestos,
  getPresupuesto,
  createPresupuesto,
  deletePresupuesto,
  approvePresupuesto,
  closePresupuesto,
  getPresupuestoStats,
  recalcularPresupuesto,
  registerEjecucionMensual,
  getComparativoPresupuestario,
  getPresupuestoAlertas,
  markAlertaRead,
  markAlertaResolved,
  getAlertaSummary,
  getCuentasContables,
  type CuentaContable,
  type PresupuestoAnual,
  type PresupuestoStats,
  type ComparativoGeneral,
  type PresupuestoAlerta,
  type AlertaSummary,
  type PresupuestoCuentaCreate,
  type Company,
  type User,
} from '@/lib/api';

function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

function getEstadoBadge(estado: string) {
  switch (estado) {
    case 'borrador': return <Badge variant="secondary">Borrador</Badge>;
    case 'aprobado': return <Badge className="bg-emerald-600">Aprobado</Badge>;
    case 'cerrado': return <Badge variant="default">Cerrado</Badge>;
    case 'anulado': return <Badge variant="destructive">Anulado</Badge>;
    default: return <Badge variant="outline">{estado}</Badge>;
  }
}

function getAlertaTipoBadge(tipo: string) {
  switch (tipo) {
    case 'sobregiro': return <Badge variant="destructive">Sobregiro</Badge>;
    case '90_porciento': return <Badge className="bg-orange-500">90%</Badge>;
    case '75_porciento': return <Badge className="bg-amber-500">75%</Badge>;
    case '50_porciento': return <Badge className="bg-yellow-500 text-black">50%</Badge>;
    default: return <Badge variant="outline">{tipo}</Badge>;
  }
}

function _getEjecucionColor(porcentaje: number) {
  if (porcentaje > 100) return 'bg-red-800';
  if (porcentaje > 90) return 'bg-red-500';
  if (porcentaje > 75) return 'bg-orange-500';
  if (porcentaje > 50) return 'bg-yellow-500';
  return 'bg-emerald-500';
}

function getEjecucionTextColor(porcentaje: number) {
  if (porcentaje > 100) return 'text-red-800';
  if (porcentaje > 90) return 'text-red-500';
  if (porcentaje > 75) return 'text-orange-500';
  if (porcentaje > 50) return 'text-yellow-600';
  return 'text-emerald-600';
}

interface ContaECBudgetsProps {
  user: User;
  companies: Company[];
}

export function ContaECBudgets({ user: _user, companies }: ContaECBudgetsProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div><h2 className="text-2xl font-bold">Presupuestos</h2><p className="text-muted-foreground">Control presupuestario y análisis comparativo</p></div>
        <Card><CardContent className="py-12 text-center"><PieChart className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin empresas</h3><p className="text-muted-foreground text-sm mt-1">Registre una empresa para comenzar</p></CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Presupuestos</h2>
          <p className="text-muted-foreground">Control presupuestario y análisis comparativo</p>
        </div>
        {companies.length > 1 && (
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">Empresa:</Label>
            <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
              <SelectTrigger className="w-[220px]"><SelectValue placeholder="Empresa" /></SelectTrigger>
              <SelectContent>{companies.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}</SelectContent>
            </Select>
          </div>
        )}
      </div>

      <Tabs defaultValue="presupuestos" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="presupuestos" className="gap-1.5"><PieChart className="h-3.5 w-3.5" /><span className="hidden sm:inline">Presupuestos</span></TabsTrigger>
          <TabsTrigger value="ejecucion" className="gap-1.5"><BarChart3 className="h-3.5 w-3.5" /><span className="hidden sm:inline">Ejecución</span></TabsTrigger>
          <TabsTrigger value="comparativo" className="gap-1.5"><Target className="h-3.5 w-3.5" /><span className="hidden sm:inline">Comparativo</span></TabsTrigger>
          <TabsTrigger value="alertas" className="gap-1.5"><AlertTriangle className="h-3.5 w-3.5" /><span className="hidden sm:inline">Alertas</span></TabsTrigger>
          <TabsTrigger value="cuadro" className="gap-1.5"><DollarSign className="h-3.5 w-3.5" /><span className="hidden sm:inline">Cuadro de Mando</span></TabsTrigger>
        </TabsList>
        <TabsContent value="presupuestos"><PresupuestosTab companyId={selectedCompanyId} companies={companies} /></TabsContent>
        <TabsContent value="ejecucion"><EjecucionTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="comparativo"><ComparativoTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="alertas"><AlertasTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="cuadro"><CuadroMandoTab companyId={selectedCompanyId} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Presupuestos Tab ───────────────────────────────────

function PresupuestosTab({ companyId, companies }: { companyId: string; companies: Company[] }) {
  const [presupuestos, setPresupuestos] = useState<PresupuestoAnual[]>([]);
  const [stats, setStats] = useState<PresupuestoStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [viewPresupuesto, setViewPresupuesto] = useState<PresupuestoAnual | null>(null);
  const [operating, setOperating] = useState(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [pres, st] = await Promise.all([
        getPresupuestos({ company_id: companyId }),
        getPresupuestoStats(companyId),
      ]);
      setPresupuestos(pres);
      setStats(st);
    } catch {
      toast.error('Error al cargar presupuestos');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleAction(id: string, action: string) {
    setOperating(true);
    try {
      switch (action) {
        case 'approve': await approvePresupuesto(id); toast.success('Presupuesto aprobado'); break;
        case 'close': await closePresupuesto(id); toast.success('Presupuesto cerrado'); break;
        case 'delete': await deletePresupuesto(id); toast.success('Presupuesto eliminado'); break;
        case 'recalcular': await recalcularPresupuesto(id); toast.success('Presupuesto recalculado'); break;
      }
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error en la operación');
    } finally {
      setOperating(false);
    }
  }

  async function handleView(id: string) {
    try {
      const p = await getPresupuesto(id);
      setViewPresupuesto(p);
    } catch {
      toast.error('Error al cargar presupuesto');
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total</p><p className="text-2xl font-bold">{stats?.total_presupuestos ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Borrador</p><p className="text-2xl font-bold">{stats?.presupuestos_borrador ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Aprobados</p><p className="text-2xl font-bold text-emerald-600">{stats?.presupuestos_aprobados ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Cerrados</p><p className="text-2xl font-bold">{stats?.presupuestos_cerrados ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Sobregiros</p><p className="text-2xl font-bold text-destructive">{stats?.total_sobregiros ?? 0}</p></CardContent></Card>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nuevo Presupuesto</Button>
      </div>

      {/* Table */}
      {presupuestos.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Año</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Ingresos Presup.</TableHead>
                    <TableHead className="text-right">Egresos Presup.</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {presupuestos.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-medium">{p.nombre}</TableCell>
                      <TableCell>{p.anio}</TableCell>
                      <TableCell>{getEstadoBadge(p.estado)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(p.total_ingresos_presupuestado)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(p.total_egresos_presupuestado)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleView(p.id)}><Eye className="h-3.5 w-3.5" /></Button>
                          {p.estado === 'borrador' && (
                            <>
                              <Button variant="ghost" size="icon" className="h-8 w-8 text-emerald-600" onClick={() => handleAction(p.id, 'approve')} disabled={operating}><CheckCircle2 className="h-3.5 w-3.5" /></Button>
                              <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleAction(p.id, 'delete')} disabled={operating}><Trash2 className="h-3.5 w-3.5" /></Button>
                            </>
                          )}
                          {p.estado === 'aprobado' && (
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleAction(p.id, 'close')} disabled={operating}><XCircle className="h-3.5 w-3.5" /></Button>
                          )}
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleAction(p.id, 'recalcular')} disabled={operating}><RefreshCw className="h-3.5 w-3.5" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card><CardContent className="py-12 text-center"><PieChart className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin presupuestos</h3><p className="text-muted-foreground text-sm mt-1">Cree un presupuesto para comenzar</p></CardContent></Card>
      )}

      {/* Create Dialog */}
      <CreatePresupuestoDialog open={showCreate} onOpenChange={setShowCreate} companyId={companyId} companies={companies} onCreated={loadData} />

      {/* View Dialog */}
      <Dialog open={!!viewPresupuesto} onOpenChange={(open) => { if (!open) setViewPresupuesto(null); }}>
        <DialogContent className="sm:max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Detalle del Presupuesto</DialogTitle>
            <DialogDescription>{viewPresupuesto?.nombre} - {viewPresupuesto?.anio}</DialogDescription>
          </DialogHeader>
          {viewPresupuesto && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div><p className="text-xs text-muted-foreground">Estado</p>{getEstadoBadge(viewPresupuesto.estado)}</div>
                <div><p className="text-xs text-muted-foreground">Ingresos Presup.</p><p className="font-medium">{formatCurrency(viewPresupuesto.total_ingresos_presupuestado)}</p></div>
                <div><p className="text-xs text-muted-foreground">Egresos Presup.</p><p className="font-medium">{formatCurrency(viewPresupuesto.total_egresos_presupuestado)}</p></div>
                <div><p className="text-xs text-muted-foreground">Ingresos Ejecutado</p><p className="font-medium text-emerald-600">{formatCurrency(viewPresupuesto.total_ingresos_ejecutado)}</p></div>
              </div>
              <Separator />
              <h4 className="font-medium">Cuentas Presupuestarias</h4>
              {viewPresupuesto.cuentas.length > 0 ? (
                <ScrollArea className="max-h-64">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Código</TableHead>
                        <TableHead>Cuenta</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead className="text-right">Anual</TableHead>
                        <TableHead className="text-right">Ejecutado</TableHead>
                        <TableHead className="text-right">%</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {viewPresupuesto.cuentas.map((c) => (
                        <TableRow key={c.id}>
                          <TableCell className="font-mono text-xs">{c.cuenta_codigo}</TableCell>
                          <TableCell>{c.cuenta_nombre}</TableCell>
                          <TableCell><Badge variant="outline">{c.cuenta_tipo}</Badge></TableCell>
                          <TableCell className="text-right">{formatCurrency(c.monto_anual)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(c.monto_ejecutado)}</TableCell>
                          <TableCell className={`text-right font-medium ${getEjecucionTextColor(c.porcentaje_ejecucion)}`}>{c.porcentaje_ejecucion.toFixed(1)}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : <p className="text-sm text-muted-foreground">Sin cuentas registradas</p>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Create Presupuesto Dialog ───────────────────────────────

function CreatePresupuestoDialog({ open, onOpenChange, companyId, companies, onCreated }: {
  open: boolean; onOpenChange: (open: boolean) => void; companyId: string; companies: Company[]; onCreated: () => void;
}) {
  const [nombre, setNombre] = useState('');
  const [anio, setAnio] = useState(new Date().getFullYear().toString());
  const [descripcion, setDescripcion] = useState('');
  const [selectedCompany, setSelectedCompany] = useState(companyId);
  const [cuentas, setCuentas] = useState<PresupuestoCuentaCreate[]>([
    { cuenta_codigo: '', cuenta_nombre: '', cuenta_tipo: 'ingreso', monto_anual: 0 },
  ]);
  const [cuentasContables, setCuentasContables] = useState<CuentaContable[]>([]);
  const [creating, setCreating] = useState(false);

  // Cargar el plan de cuentas contables para autocompletar código → nombre
  useEffect(() => {
    if (!selectedCompany) return;
    getCuentasContables(selectedCompany)
      .then((list) => setCuentasContables(list))
      .catch(() => setCuentasContables([]));
  }, [selectedCompany]);

  function selectCuentaContable(index: number, codigo: string) {
    const cuenta = cuentasContables.find((cc) => cc.codigo === codigo);
    const updated = [...cuentas];
    updated[index] = {
      ...updated[index],
      cuenta_codigo: codigo,
      cuenta_nombre: cuenta?.nombre || updated[index].cuenta_nombre,
      cuenta_tipo: (cuenta?.tipo === 'ingreso' || cuenta?.tipo === 'egreso') ? cuenta.tipo : updated[index].cuenta_tipo,
    };
    setCuentas(updated);
  }

  function addCuenta() {
    setCuentas([...cuentas, { cuenta_codigo: '', cuenta_nombre: '', cuenta_tipo: 'egreso', monto_anual: 0 }]);
  }

  function removeCuenta(index: number) {
    setCuentas(cuentas.filter((_, i) => i !== index));
  }

  function updateCuenta(index: number, field: keyof PresupuestoCuentaCreate, value: string | number) {
    const updated = [...cuentas];
    updated[index] = { ...updated[index], [field]: value };
    setCuentas(updated);
  }

  async function handleCreate() {
    if (!nombre || !anio || cuentas.length === 0) {
      toast.error('Complete los campos requeridos');
      return;
    }
    if (cuentas.some(c => !c.cuenta_codigo || !c.cuenta_nombre || c.monto_anual <= 0)) {
      toast.error('Complete todas las cuentas con datos válidos');
      return;
    }
    setCreating(true);
    try {
      await createPresupuesto({
        company_id: selectedCompany,
        anio: parseInt(anio),
        nombre,
        descripcion: descripcion || undefined,
        cuentas,
      });
      toast.success('Presupuesto creado exitosamente');
      onOpenChange(false);
      setNombre(''); setAnio(new Date().getFullYear().toString()); setDescripcion('');
      setCuentas([{ cuenta_codigo: '', cuenta_nombre: '', cuenta_tipo: 'ingreso', monto_anual: 0 }]);
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear presupuesto');
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nuevo Presupuesto</DialogTitle>
          <DialogDescription>Cree un presupuesto anual con cuentas presupuestarias</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Empresa</Label>
              <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{companies.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Año</Label>
 <NumericInput value={anio} onChange={(e) => setAnio(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Nombre</Label>
            <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Presupuesto Anual 2025" />
          </div>
          <div className="space-y-2">
            <Label>Descripción</Label>
            <Textarea value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2} placeholder="Descripción opcional" />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <Label className="text-base font-semibold">Cuentas Presupuestarias</Label>
            <Button type="button" variant="outline" size="sm" onClick={addCuenta}><Plus className="h-4 w-4 mr-1" /> Agregar Cuenta</Button>
          </div>
          <ScrollArea className="max-h-64">
            <div className="space-y-3">
              {cuentas.map((c, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-end border rounded-lg p-3">
                  <div className="col-span-2 space-y-1"><Label className="text-xs">Código</Label><Select value={c.cuenta_codigo} onValueChange={(v) => selectCuentaContable(i, v)}><SelectTrigger><SelectValue placeholder="Seleccione código" /></SelectTrigger><SelectContent className="max-h-64">{(cuentasContables.length > 0 ? cuentasContables : [{ id: '__', codigo: c.cuenta_codigo || '', nombre: c.cuenta_nombre }] as CuentaContable[]).map((cc) => (<SelectItem key={cc.codigo} value={cc.codigo}>{cc.codigo} - {cc.nombre}</SelectItem>))}</SelectContent></Select></div>
                  <div className="col-span-3 space-y-1"><Label className="text-xs">Nombre</Label><Input value={c.cuenta_nombre} onChange={(e) => updateCuenta(i, 'cuenta_nombre', e.target.value)} placeholder="Ventas" /></div>
                  <div className="col-span-3 space-y-1"><Label className="text-xs">Tipo</Label><Select value={c.cuenta_tipo} onValueChange={(v) => updateCuenta(i, 'cuenta_tipo', v)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ingreso">Ingreso</SelectItem><SelectItem value="egreso">Egreso</SelectItem></SelectContent></Select></div>
 <div className="col-span-3 space-y-1"><Label className="text-xs">Monto Anual</Label><NumericInput value={c.monto_anual || ''} onChange={(e) => updateCuenta(i, 'monto_anual', parseFloat(e.target.value) || 0)} /></div>
                  <div className="col-span-1">{cuentas.length > 1 && <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => removeCuenta(i)}><Trash2 className="h-3.5 w-3.5" /></Button>}</div>
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear Presupuesto</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Ejecución Tab ───────────────────────────────────

function EjecucionTab({ companyId }: { companyId: string }) {
  const [presupuestos, setPresupuestos] = useState<PresupuestoAnual[]>([]);
  const [selectedPresupuestoId, setSelectedPresupuestoId] = useState<string>('');
  const [presupuesto, setPresupuesto] = useState<PresupuestoAnual | null>(null);
  const [loading, setLoading] = useState(true);
  const [showEjecucion, setShowEjecucion] = useState<string | null>(null);
  const [ejecucionMes, setEjecucionMes] = useState('1');
  const [ejecucionMonto, setEjecucionMonto] = useState('');
  const [ejecucionObs, setEjecucionObs] = useState('');
  const [registering, setRegistering] = useState(false);

  const loadPresupuestos = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const pres = await getPresupuestos({ company_id: companyId, estado: 'aprobado' });
      setPresupuestos(pres);
      if (pres.length > 0 && !selectedPresupuestoId) {
        setSelectedPresupuestoId(pres[0].id);
      }
    } catch {
      toast.error('Error al cargar presupuestos');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  useEffect(() => { loadPresupuestos(); }, [loadPresupuestos]);

  const loadPresupuesto = useCallback(async () => {
    if (!selectedPresupuestoId) return;
    try {
      const p = await getPresupuesto(selectedPresupuestoId);
      setPresupuesto(p);
    } catch {
      toast.error('Error al cargar detalle');
    }
  }, [selectedPresupuestoId]);

  useEffect(() => { if (selectedPresupuestoId) loadPresupuesto(); }, [selectedPresupuestoId, loadPresupuesto]);

  async function handleRegisterEjecucion() {
    if (!showEjecucion || !ejecucionMonto) return;
    setRegistering(true);
    try {
      await registerEjecucionMensual(showEjecucion, {
        monto_ejecutado: parseFloat(ejecucionMonto),
        observaciones: ejecucionObs || undefined,
      });
      toast.success('Ejecución registrada');
      setShowEjecucion(null); setEjecucionMonto(''); setEjecucionObs('');
      loadPresupuesto();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al registrar ejecución');
    } finally {
      setRegistering(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Label>Presupuesto:</Label>
        <Select value={selectedPresupuestoId} onValueChange={setSelectedPresupuestoId}>
          <SelectTrigger className="w-[300px]"><SelectValue placeholder="Seleccione presupuesto" /></SelectTrigger>
          <SelectContent>{presupuestos.map((p) => (<SelectItem key={p.id} value={p.id}>{p.nombre} ({p.anio})</SelectItem>))}</SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadPresupuesto}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {presupuesto ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{presupuesto.nombre} - {presupuesto.anio}</CardTitle>
            <CardDescription>{presupuesto.cuentas.length} cuentas presupuestarias</CardDescription>
          </CardHeader>
          <CardContent>
            {presupuesto.cuentas.length > 0 ? (
              <ScrollArea className="max-h-96">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Código</TableHead>
                      <TableHead>Cuenta</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead className="text-right">Anual</TableHead>
                      <TableHead className="text-right">Ejecutado</TableHead>
                      <TableHead className="text-right">Disponible</TableHead>
                      <TableHead>% Ejecución</TableHead>
                      <TableHead className="text-right">Acción</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {presupuesto.cuentas.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell className="font-mono text-xs">{c.cuenta_codigo}</TableCell>
                        <TableCell>{c.cuenta_nombre}</TableCell>
                        <TableCell><Badge variant="outline">{c.cuenta_tipo}</Badge></TableCell>
                        <TableCell className="text-right">{formatCurrency(c.monto_anual)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(c.monto_ejecutado)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(c.monto_disponible)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={Math.min(c.porcentaje_ejecucion, 100)} className="w-16 h-2" />
                            <span className={`text-xs font-medium ${getEjecucionTextColor(c.porcentaje_ejecucion)}`}>{c.porcentaje_ejecucion.toFixed(1)}%</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          {presupuesto.estado === 'aprobado' && (
                            <Button size="sm" variant="outline" onClick={() => { setShowEjecucion(c.id); setEjecucionMes('1'); setEjecucionMonto(''); setEjecucionObs(''); }}>
                              <DollarSign className="mr-1 h-3 w-3" /> Registrar
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            ) : <p className="text-sm text-muted-foreground text-center py-8">Sin cuentas en este presupuesto</p>}
          </CardContent>
        </Card>
      ) : (
        <Card><CardContent className="py-12 text-center"><BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Seleccione un presupuesto aprobado</h3></CardContent></Card>
      )}

      {/* Ejecución Dialog */}
      <Dialog open={!!showEjecucion} onOpenChange={(open) => { if (!open) setShowEjecucion(null); }}>
        <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Registrar Ejecución Mensual</DialogTitle><DialogDescription>Ingrese el monto ejecutado para el mes seleccionado</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Mes</Label><Select value={ejecucionMes} onValueChange={setEjecucionMes}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{MESES.map((m, i) => (<SelectItem key={i} value={(i + 1).toString()}>{m}</SelectItem>))}</SelectContent></Select></div>
 <div className="space-y-2"><Label>Monto Ejecutado ($)</Label><NumericInput value={ejecucionMonto} onChange={(e) => setEjecucionMonto(e.target.value)} placeholder="0.00" /></div>
            <div className="space-y-2"><Label>Observaciones</Label><Textarea value={ejecucionObs} onChange={(e) => setEjecucionObs(e.target.value)} rows={2} placeholder="Opcional" /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowEjecucion(null)}>Cancelar</Button>
              <Button onClick={handleRegisterEjecucion} disabled={registering}>{registering ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Registrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Comparativo Tab ───────────────────────────────────

function ComparativoTab({ companyId }: { companyId: string }) {
  const [comparativo, setComparativo] = useState<ComparativoGeneral | null>(null);
  const [anio, setAnio] = useState(new Date().getFullYear().toString());
  const [loading, setLoading] = useState(false);

  const loadComparativo = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const comp = await getComparativoPresupuestario({ company_id: companyId, anio: parseInt(anio) });
      setComparativo(comp);
    } catch {
      toast.error('Error al cargar comparativo');
    } finally {
      setLoading(false);
    }
  }, [companyId, anio]);

  useEffect(() => { loadComparativo(); }, [loadComparativo]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Label>Año:</Label>
 <NumericInput value={anio} onChange={(e) => setAnio(e.target.value)} className="w-24" />
        <Button variant="outline" size="icon" onClick={loadComparativo}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {loading ? <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> : comparativo ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Ingresos</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">Presupuestado</span><span>{formatCurrency(comparativo.total_ingresos_presupuestado)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">Ejecutado</span><span className="text-emerald-600">{formatCurrency(comparativo.total_ingresos_ejecutado)}</span></div>
                  <div className="flex justify-between text-xs font-medium"><span>Variación</span><span className={comparativo.total_ingresos_presupuestado - comparativo.total_ingresos_ejecutado >= 0 ? 'text-emerald-600' : 'text-destructive'}>{formatCurrency(comparativo.total_ingresos_presupuestado - comparativo.total_ingresos_ejecutado)}</span></div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Egresos</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">Presupuestado</span><span>{formatCurrency(comparativo.total_egresos_presupuestado)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">Ejecutado</span><span className="text-destructive">{formatCurrency(comparativo.total_egresos_ejecutado)}</span></div>
                  <div className="flex justify-between text-xs font-medium"><span>Variación</span><span className={comparativo.total_egresos_presupuestado - comparativo.total_egresos_ejecutado >= 0 ? 'text-emerald-600' : 'text-destructive'}>{formatCurrency(comparativo.total_egresos_presupuestado - comparativo.total_egresos_ejecutado)}</span></div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Resultado</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">Presupuestario</span><span>{formatCurrency(comparativo.resultado_presupuestario)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">Real</span><span>{formatCurrency(comparativo.resultado_real)}</span></div>
                  <div className="flex justify-between text-xs font-medium"><span>Desviación</span><span className={comparativo.resultado_real - comparativo.resultado_presupuestario >= 0 ? 'text-emerald-600' : 'text-destructive'}>{formatCurrency(comparativo.resultado_real - comparativo.resultado_presupuestario)}</span></div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Table */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base">Comparativo Detallado por Cuenta</CardTitle></CardHeader>
            <CardContent>
              {comparativo.cuentas.length > 0 ? (
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Código</TableHead>
                        <TableHead>Cuenta</TableHead>
                        <TableHead className="text-right">Presup.</TableHead>
                        <TableHead className="text-right">Ejecutado</TableHead>
                        <TableHead className="text-right">Variación</TableHead>
                        <TableHead className="text-right">Var. %</TableHead>
                        <TableHead>Alerta</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {comparativo.cuentas.map((c, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-mono text-xs">{c.cuenta_codigo}</TableCell>
                          <TableCell>{c.cuenta_nombre}</TableCell>
                          <TableCell className="text-right">{formatCurrency(c.monto_presupuestado)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(c.monto_ejecutado)}</TableCell>
                          <TableCell className={`text-right ${c.variacion >= 0 ? 'text-emerald-600' : 'text-destructive'}`}>{formatCurrency(c.variacion)}</TableCell>
                          <TableCell className={`text-right ${c.variacion_porcentaje >= 0 ? 'text-emerald-600' : 'text-destructive'}`}>{c.variacion_porcentaje.toFixed(1)}%</TableCell>
                          <TableCell>{c.alerta_tipo ? getAlertaTipoBadge(c.alerta_tipo) : '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : <p className="text-sm text-muted-foreground text-center py-8">Sin datos comparativos</p>}
            </CardContent>
          </Card>
        </>
      ) : (
        <Card><CardContent className="py-12 text-center"><Target className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin datos comparativos</h3><p className="text-muted-foreground text-sm mt-1">Cree y apruebe presupuestos para ver el comparativo</p></CardContent></Card>
      )}
    </div>
  );
}

// ─── Alertas Tab ───────────────────────────────────

function AlertasTab({ companyId }: { companyId: string }) {
  const [alertas, setAlertas] = useState<PresupuestoAlerta[]>([]);
  const [summary, setSummary] = useState<AlertaSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState<string>('all');
  const [filterLeida, setFilterLeida] = useState<string>('all');

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [al, sm] = await Promise.all([
        getPresupuestoAlertas({ company_id: companyId }),
        getAlertaSummary(companyId),
      ]);
      setAlertas(al);
      setSummary(sm);
    } catch {
      toast.error('Error al cargar alertas');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleMarkRead(id: string) {
    try {
      await markAlertaRead(id);
      toast.success('Alerta marcada como leída');
      loadData();
    } catch {
      toast.error('Error al marcar alerta');
    }
  }

  async function handleMarkResolved(id: string) {
    try {
      await markAlertaResolved(id);
      toast.success('Alerta resuelta');
      loadData();
    } catch {
      toast.error('Error al resolver alerta');
    }
  }

  const filteredAlertas = alertas.filter((a) => {
    if (filterTipo !== 'all' && a.tipo_alerta !== filterTipo) return false;
    if (filterLeida === 'no_leidas' && a.is_leida) return false;
    if (filterLeida === 'leidas' && !a.is_leida) return false;
    return true;
  });

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total</p><p className="text-2xl font-bold">{summary?.total_alertas ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">No Leídas</p><p className="text-2xl font-bold text-amber-500">{summary?.alertas_no_leidas ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Sobregiros</p><p className="text-2xl font-bold text-destructive">{summary?.sobregiros_activos ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">90%</p><p className="text-2xl font-bold text-orange-500">{summary?.alertas_90 ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">75%</p><p className="text-2xl font-bold text-amber-500">{summary?.alertas_75 ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">50%</p><p className="text-2xl font-bold text-yellow-500">{summary?.alertas_50 ?? 0}</p></CardContent></Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Label className="text-sm">Tipo:</Label>
        <Select value={filterTipo} onValueChange={setFilterTipo}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="sobregiro">Sobregiro</SelectItem>
            <SelectItem value="90_porciento">90%</SelectItem>
            <SelectItem value="75_porciento">75%</SelectItem>
            <SelectItem value="50_porciento">50%</SelectItem>
          </SelectContent>
        </Select>
        <Label className="text-sm">Estado:</Label>
        <Select value={filterLeida} onValueChange={setFilterLeida}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            <SelectItem value="no_leidas">No leídas</SelectItem>
            <SelectItem value="leidas">Leídas</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* Alert List */}
      {filteredAlertas.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Mensaje</TableHead>
                    <TableHead className="text-right">Presupuestado</TableHead>
                    <TableHead className="text-right">Ejecutado</TableHead>
                    <TableHead className="text-right">% Ejec.</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAlertas.map((a) => (
                    <TableRow key={a.id} className={a.is_leida ? 'opacity-60' : ''}>
                      <TableCell>{getAlertaTipoBadge(a.tipo_alerta)}</TableCell>
                      <TableCell className="max-w-xs truncate">{a.mensaje}</TableCell>
                      <TableCell className="text-right">{formatCurrency(a.monto_presupuestado)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(a.monto_ejecutado)}</TableCell>
                      <TableCell className={`text-right font-medium ${getEjecucionTextColor(a.porcentaje_ejecucion)}`}>{a.porcentaje_ejecucion.toFixed(1)}%</TableCell>
                      <TableCell className="text-xs">{new Date(a.created_at).toLocaleDateString('es-EC')}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {!a.is_leida && <Button variant="ghost" size="sm" onClick={() => handleMarkRead(a.id)}>Leer</Button>}
                          {!a.is_resuelta && <Button variant="ghost" size="sm" className="text-emerald-600" onClick={() => handleMarkResolved(a.id)}>Resolver</Button>}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card><CardContent className="py-12 text-center"><CheckCircle2 className="h-12 w-12 mx-auto text-emerald-500 mb-3" /><h3 className="text-lg font-medium">Sin alertas</h3><p className="text-muted-foreground text-sm mt-1">No hay alertas presupuestarias activas</p></CardContent></Card>
      )}
    </div>
  );
}

// ─── Cuadro de Mando Tab ───────────────────────────────────

function CuadroMandoTab({ companyId }: { companyId: string }) {
  const [_stats, setStats] = useState<PresupuestoStats | null>(null);
  const [comparativo, setComparativo] = useState<ComparativoGeneral | null>(null);
  const [loading, setLoading] = useState(true);
  const [anio, setAnio] = useState(new Date().getFullYear().toString());

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [st, comp] = await Promise.all([
        getPresupuestoStats(companyId),
        getComparativoPresupuestario({ company_id: companyId, anio: parseInt(anio) }),
      ]);
      setStats(st);
      setComparativo(comp);
    } catch {
      toast.error('Error al cargar cuadro de mando');
    } finally {
      setLoading(false);
    }
  }, [companyId, anio]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  const topEjecucion = comparativo?.cuentas
    ? [...comparativo.cuentas].sort((a, b) => b.porcentaje_ejecucion - a.porcentaje_ejecucion).slice(0, 5)
    : [];

  const topSobregiro = comparativo?.cuentas
    ? [...comparativo.cuentas].filter(c => c.monto_ejecutado > c.monto_presupuestado).sort((a, b) => (b.monto_ejecutado - b.monto_presupuestado) - (a.monto_ejecutado - a.monto_presupuestado)).slice(0, 5)
    : [];

  const totalPresupuestado = (comparativo?.total_ingresos_presupuestado ?? 0) + (comparativo?.total_egresos_presupuestado ?? 0);
  const totalEjecutado = (comparativo?.total_ingresos_ejecutado ?? 0) + (comparativo?.total_egresos_ejecutado ?? 0);
  const overallPercentage = totalPresupuestado > 0 ? (totalEjecutado / totalPresupuestado) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Label>Año:</Label>
 <NumericInput value={anio} onChange={(e) => setAnio(e.target.value)} className="w-24" />
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* Scorecard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Ingresos */}
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><TrendingUp className="h-4 w-4 text-emerald-600" /> Ingresos</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Presupuestado</span><span>{formatCurrency(comparativo?.total_ingresos_presupuestado ?? 0)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Ejecutado</span><span className="text-emerald-600">{formatCurrency(comparativo?.total_ingresos_ejecutado ?? 0)}</span></div>
              <div className="flex justify-between text-xs font-medium"><span>% Cumplimiento</span><span className="text-emerald-600">{comparativo && comparativo.total_ingresos_presupuestado > 0 ? ((comparativo.total_ingresos_ejecutado / comparativo.total_ingresos_presupuestado) * 100).toFixed(1) : '0.0'}%</span></div>
            </div>
          </CardContent>
        </Card>
        {/* Egresos */}
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><TrendingDown className="h-4 w-4 text-destructive" /> Egresos</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Presupuestado</span><span>{formatCurrency(comparativo?.total_egresos_presupuestado ?? 0)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Ejecutado</span><span className="text-destructive">{formatCurrency(comparativo?.total_egresos_ejecutado ?? 0)}</span></div>
              <div className="flex justify-between text-xs font-medium"><span>% Cumplimiento</span><span className="text-destructive">{comparativo && comparativo.total_egresos_presupuestado > 0 ? ((comparativo.total_egresos_ejecutado / comparativo.total_egresos_presupuestado) * 100).toFixed(1) : '0.0'}%</span></div>
            </div>
          </CardContent>
        </Card>
        {/* Resultado */}
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><DollarSign className="h-4 w-4" /> Resultado</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Presupuestario</span><span>{formatCurrency(comparativo?.resultado_presupuestario ?? 0)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Real</span><span>{formatCurrency(comparativo?.resultado_real ?? 0)}</span></div>
              <div className="flex justify-between text-xs font-medium"><span>Desviación</span><span className={comparativo && comparativo.resultado_real - comparativo.resultado_presupuestario >= 0 ? 'text-emerald-600' : 'text-destructive'}>{formatCurrency(comparativo ? comparativo.resultado_real - comparativo.resultado_presupuestario : 0)}</span></div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Overall Execution */}
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Ejecución Global</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm"><span>Ejecución total presupuestaria</span><span className="font-bold">{overallPercentage.toFixed(1)}%</span></div>
            <Progress value={Math.min(overallPercentage, 100)} className="h-4" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{formatCurrency(totalEjecutado)} ejecutado</span>
              <span>{formatCurrency(totalPresupuestado)} presupuestado</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Top Cuentas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-sm">Top 5 Mayor Ejecución</CardTitle></CardHeader>
          <CardContent>
            {topEjecucion.length > 0 ? (
              <div className="space-y-2">
                {topEjecucion.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="truncate">{c.cuenta_nombre}</span>
                    <span className={`font-medium ${getEjecucionTextColor(c.porcentaje_ejecucion)}`}>{c.porcentaje_ejecucion.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground text-center">Sin datos</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-sm">Top 5 Mayor Sobregiro</CardTitle></CardHeader>
          <CardContent>
            {topSobregiro.length > 0 ? (
              <div className="space-y-2">
                {topSobregiro.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="truncate">{c.cuenta_nombre}</span>
                    <span className="font-medium text-destructive">{formatCurrency(c.monto_ejecutado - c.monto_presupuestado)}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground text-center">Sin sobregiros</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
