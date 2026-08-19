'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
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
import { Textarea } from '@/components/ui/textarea';
import { NumericInput } from '@/components/ui/numeric-input';
import {
  Briefcase,
  FolderKanban,
  Users,
  Clock,
  TrendingUp,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Eye,
  Pencil,
  Filter,
  DollarSign,
  Calendar,
  CheckCircle2,
  BarChart3,
  UserCheck,
  Wrench,
  Calculator,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getProyectos,
  getProyecto,
  createProyecto,
  updateProyecto,
  deleteProyecto,
  getProyectoStats,
  recalcularProyecto,
  getProyectoTareas,
  createProyectoTarea,
  updateProyectoTarea,
  deleteProyectoTarea,
  getProyectoRecursos,
  createProyectoRecurso,
  updateProyectoRecurso,
  deleteProyectoRecurso,
  getProyectoTimesheets,
  createProyectoTimesheet,
  deleteProyectoTimesheet,
  getClients,
  type ProyectoResponse,
  type ProyectoTareaResponse,
  type ProyectoRecursoResponse,
  type ProyectoTimesheetResponse,
  type ProyectoStats,
  type Company,
  type User,
  type ClientResponse,
} from '@/lib/api';

function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('es-EC', { year: 'numeric', month: 'short', day: 'numeric' });
}

const ESTADOS_PROYECTO = [
  { key: 'planificacion', label: 'Planificación', badgeClass: 'bg-slate-500', color: 'text-slate-600 dark:text-slate-400' },
  { key: 'en_progreso', label: 'En Progreso', badgeClass: 'bg-sky-600', color: 'text-sky-600 dark:text-sky-400' },
  { key: 'en_pausa', label: 'En Pausa', badgeClass: 'bg-amber-500', color: 'text-amber-600 dark:text-amber-400' },
  { key: 'completado', label: 'Completado', badgeClass: 'bg-emerald-600', color: 'text-emerald-600 dark:text-emerald-400' },
  { key: 'cancelado', label: 'Cancelado', badgeClass: 'bg-red-600', color: 'text-red-600 dark:text-red-400' },
] as const;

const ESTADOS_TAREA = [
  { key: 'pendiente', label: 'Pendiente', badgeClass: 'bg-slate-400' },
  { key: 'en_progreso', label: 'En Progreso', badgeClass: 'bg-sky-500' },
  { key: 'completada', label: 'Completada', badgeClass: 'bg-emerald-600' },
  { key: 'cancelada', label: 'Cancelada', badgeClass: 'bg-red-500' },
] as const;

const PRIORIDADES = [
  { key: 'baja', label: 'Baja', badgeClass: 'bg-gray-400' },
  { key: 'media', label: 'Media', badgeClass: 'bg-sky-500' },
  { key: 'alta', label: 'Alta', badgeClass: 'bg-amber-500' },
  { key: 'critica', label: 'Crítica', badgeClass: 'bg-red-600' },
] as const;

const TIPOS_RECURSO = [
  { key: 'humano', label: 'Humano', icon: UserCheck },
  { key: 'material', label: 'Material', icon: Wrench },
  { key: 'equipo', label: 'Equipo', icon: Briefcase },
] as const;

function getEstadoBadge(estado: string) {
  const e = ESTADOS_PROYECTO.find((x) => x.key === estado);
  if (e) return <Badge className={`${e.badgeClass} text-white`}>{e.label}</Badge>;
  return <Badge variant="outline">{estado}</Badge>;
}

function getTareaEstadoBadge(estado: string) {
  const e = ESTADOS_TAREA.find((x) => x.key === estado);
  if (e) return <Badge className={`${e.badgeClass} text-white text-xs`}>{e.label}</Badge>;
  return <Badge variant="outline">{estado}</Badge>;
}

function getPrioridadBadge(prioridad: string) {
  const p = PRIORIDADES.find((x) => x.key === prioridad);
  if (p) return <Badge className={`${p.badgeClass} text-white text-xs`}>{p.label}</Badge>;
  return <Badge variant="outline">{prioridad}</Badge>;
}

function getTipoRecursoBadge(tipo: string) {
  const t = TIPOS_RECURSO.find((x) => x.key === tipo);
  if (t) return <Badge variant="outline" className="gap-1">{<t.icon className="h-3 w-3" />}{t.label}</Badge>;
  return <Badge variant="outline">{tipo}</Badge>;
}

interface ContaECProjectsProps {
  user: User;
  companies: Company[];
}

export function ContaECProjects({ user: _user, companies }: ContaECProjectsProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Proyectos y Servicios</h2>
          <p className="text-muted-foreground">Gestión de proyectos, recursos y rentabilidad</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Briefcase className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin empresas</h3>
            <p className="text-muted-foreground text-sm mt-1">Registre una empresa para comenzar</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Proyectos y Servicios</h2>
          <p className="text-muted-foreground">Gestión de proyectos, recursos y rentabilidad</p>
        </div>
        {companies.length > 1 && (
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">Empresa:</Label>
            <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="Empresa" />
              </SelectTrigger>
              <SelectContent>
                {companies.map((c) => (
                  <SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <Tabs defaultValue="dashboard" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="dashboard" className="gap-1.5"><BarChart3 className="h-3.5 w-3.5" /><span className="hidden sm:inline">Dashboard</span></TabsTrigger>
          <TabsTrigger value="proyectos" className="gap-1.5"><FolderKanban className="h-3.5 w-3.5" /><span className="hidden sm:inline">Proyectos</span></TabsTrigger>
          <TabsTrigger value="tareas" className="gap-1.5"><CheckCircle2 className="h-3.5 w-3.5" /><span className="hidden sm:inline">Tareas</span></TabsTrigger>
          <TabsTrigger value="recursos" className="gap-1.5"><Users className="h-3.5 w-3.5" /><span className="hidden sm:inline">Recursos</span></TabsTrigger>
          <TabsTrigger value="timesheet" className="gap-1.5"><Clock className="h-3.5 w-3.5" /><span className="hidden sm:inline">Timesheet</span></TabsTrigger>
          <TabsTrigger value="rentabilidad" className="gap-1.5"><TrendingUp className="h-3.5 w-3.5" /><span className="hidden sm:inline">Rentabilidad</span></TabsTrigger>
        </TabsList>
        <TabsContent value="dashboard"><DashboardTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="proyectos"><ProyectosTab companyId={selectedCompanyId} companies={companies} /></TabsContent>
        <TabsContent value="tareas"><TareasTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="recursos"><RecursosTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="timesheet"><TimesheetTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="rentabilidad"><RentabilidadTab companyId={selectedCompanyId} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Dashboard Tab ───────────────────────────────────

function DashboardTab({ companyId }: { companyId: string }) {
  const [stats, setStats] = useState<ProyectoStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const st = await getProyectoStats(companyId);
      setStats(st);
    } catch {
      toast.error('Error al cargar estadísticas');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <FolderKanban className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Total Proyectos</p>
            </div>
            <p className="text-2xl font-bold">{stats?.total_proyectos ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-sky-500" />
              <p className="text-xs text-muted-foreground">En Progreso</p>
            </div>
            <p className="text-2xl font-bold text-sky-600">{stats?.en_progreso ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <p className="text-xs text-muted-foreground">Completados</p>
            </div>
            <p className="text-2xl font-bold text-emerald-600">{stats?.completados ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-4 w-4 text-amber-500" />
              <p className="text-xs text-muted-foreground">Presupuesto Total</p>
            </div>
            <p className="text-2xl font-bold">{formatCurrency(stats?.total_presupuesto ?? 0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-emerald-500" />
              <p className="text-xs text-muted-foreground">Margen Total</p>
            </div>
            <p className={`text-2xl font-bold ${(stats?.margen_total != null ? Number(stats.margen_total) : 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {formatCurrency(stats?.margen_total ?? 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Financial Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Resumen Financiero</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Presupuestado</span>
              <span className="font-medium">{formatCurrency(stats?.total_presupuesto ?? 0)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Costo Real</span>
              <span className="font-medium text-red-600">{formatCurrency(stats?.total_costo_real ?? 0)}</span>
            </div>
            <Separator />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Ingreso Total</span>
              <span className="font-medium text-emerald-600">{formatCurrency(stats?.total_ingreso ?? 0)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Margen</span>
              <span className={`font-bold ${(stats?.margen_total != null ? Number(stats.margen_total) : 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {formatCurrency(stats?.margen_total ?? 0)}
              </span>
            </div>
            {(stats?.total_ingreso ?? 0) > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">% Margen</span>
                <span className="font-medium">
                  {((stats?.margen_total ?? 0) / (stats?.total_ingreso ?? 1) * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Distribución por Estado</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {ESTADOS_PROYECTO.map((estado) => {
              const count = estado.key === 'planificacion' ? stats?.en_planificacion :
                estado.key === 'en_progreso' ? stats?.en_progreso :
                estado.key === 'completado' ? stats?.completados :
                estado.key === 'cancelado' ? stats?.cancelados : 0;
              const total = stats?.total_proyectos ?? 1;
              const pct = total > 0 ? ((count ?? 0) / total * 100) : 0;
              return (
                <div key={estado.key} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className={estado.color}>{estado.label}</span>
                    <span className="font-medium">{count ?? 0}</span>
                  </div>
                  <Progress value={pct} className="h-2" />
                </div>
              );
            })}
            <Separator />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Horas Registradas</span>
              <span className="font-medium">{Number(stats?.horas_totales ?? 0).toFixed(1)}h</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Proyectos Tab ───────────────────────────────────

function ProyectosTab({ companyId, companies: _companies }: { companyId: string; companies: Company[] }) {
  const [proyectos, setProyectos] = useState<ProyectoResponse[]>([]);
  const [clients, setClients] = useState<ClientResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editProyecto, setEditProyecto] = useState<ProyectoResponse | null>(null);
  const [viewProyecto, setViewProyecto] = useState<ProyectoResponse | null>(null);
  const [operating, setOperating] = useState(false);
  const [filterEstado, setFilterEstado] = useState<string>('all');
  const [showFilters, setShowFilters] = useState(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [proys, cls] = await Promise.all([
        getProyectos({ company_id: companyId }),
        getClients(companyId),
      ]);
      setProyectos(proys);
      setClients(cls);
    } catch {
      toast.error('Error al cargar proyectos');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleDelete(id: string) {
    if (!confirm('¿Está seguro de eliminar este proyecto?')) return;
    setOperating(true);
    try {
      await deleteProyecto(id);
      toast.success('Proyecto eliminado');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    } finally {
      setOperating(false);
    }
  }

  async function handleRecalcular(id: string) {
    setOperating(true);
    try {
      await recalcularProyecto(id);
      toast.success('Proyecto recalculado');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al recalcular');
    } finally {
      setOperating(false);
    }
  }

  const filteredProyectos = proyectos.filter((p) => {
    if (filterEstado !== 'all' && p.estado !== filterEstado) return false;
    return true;
  });

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      {/* Actions */}
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} className="gap-1.5">
          <Filter className="h-3.5 w-3.5" /> Filtros
        </Button>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <div className="flex-1" />
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nuevo Proyecto</Button>
      </div>

      {/* Filters */}
      {showFilters && (
        <Card>
          <CardContent className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label className="text-xs">Estado</Label>
                <Select value={filterEstado} onValueChange={setFilterEstado}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    {ESTADOS_PROYECTO.map((e) => (<SelectItem key={e.key} value={e.key}>{e.label}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      {filteredProyectos.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Presupuesto</TableHead>
                    <TableHead className="text-right">Costo Real</TableHead>
                    <TableHead className="text-right">Ingreso</TableHead>
                    <TableHead>Progreso</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProyectos.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-sm">{p.codigo}</TableCell>
                      <TableCell className="font-medium">{p.nombre}</TableCell>
                      <TableCell className="text-sm">{p.cliente_nombre || '-'}</TableCell>
                      <TableCell>{getEstadoBadge(p.estado)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(p.presupuesto)}</TableCell>
                      <TableCell className="text-right text-red-600">{formatCurrency(p.costo_real)}</TableCell>
                      <TableCell className="text-right text-emerald-600">{formatCurrency(p.ingreso)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={Number(p.progreso)} className="h-2 w-16" />
                          <span className="text-xs">{Number(p.progreso || 0).toFixed(0)}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setViewProyecto(p)} title="Ver detalle">
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setEditProyecto(p)} title="Editar">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleRecalcular(p.id)} title="Recalcular" disabled={operating}>
                            <Calculator className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(p.id)} disabled={operating}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
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
        <Card>
          <CardContent className="py-12 text-center">
            <FolderKanban className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin proyectos</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree un proyecto para comenzar</p>
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      <CreateProyectoDialog open={showCreate} onOpenChange={setShowCreate} companyId={companyId} clients={clients} onCreated={loadData} />

      {/* Edit Dialog */}
      {editProyecto && (
        <EditProyectoDialog proyecto={editProyecto} open={!!editProyecto} onOpenChange={(open) => { if (!open) setEditProyecto(null); }} clients={clients} onUpdated={loadData} />
      )}

      {/* View Detail Dialog */}
      {viewProyecto && (
        <ProyectoDetailDialog proyecto={viewProyecto} open={!!viewProyecto} onOpenChange={(open) => { if (!open) setViewProyecto(null); }} onRecalcular={async () => { await handleRecalcular(viewProyecto.id); setViewProyecto(null); }} />
      )}
    </div>
  );
}

// ─── Create Proyecto Dialog ───────────────────────────────

function CreateProyectoDialog({ open, onOpenChange, companyId, clients, onCreated }: {
  open: boolean; onOpenChange: (open: boolean) => void; companyId: string; clients: ClientResponse[]; onCreated: () => void;
}) {
  const [codigo, setCodigo] = useState('');
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [clienteId, setClienteId] = useState('');
  const [estado, setEstado] = useState('planificacion');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFinEstimada, setFechaFinEstimada] = useState('');
  const [presupuesto, setPresupuesto] = useState('');
  const [responsable, setResponsable] = useState('');
  const [notas, setNotas] = useState('');
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    if (!codigo || !nombre) {
      toast.error('Complete los campos requeridos (código, nombre)');
      return;
    }
    setCreating(true);
    try {
      const selectedClient = clients.find(c => c.id === clienteId);
      await createProyecto({
        company_id: companyId,
        codigo,
        nombre,
        descripcion: descripcion || undefined,
        cliente_id: clienteId || undefined,
        cliente_nombre: selectedClient?.razon_social || undefined,
        estado,
        fecha_inicio: fechaInicio || undefined,
        fecha_fin_estimada: fechaFinEstimada || undefined,
        presupuesto: presupuesto ? parseFloat(presupuesto) : undefined,
        responsable: responsable || undefined,
        notas: notas || undefined,
      });
      toast.success('Proyecto creado exitosamente');
      onOpenChange(false);
      setCodigo(''); setNombre(''); setDescripcion(''); setClienteId('');
      setEstado('planificacion'); setFechaInicio(''); setFechaFinEstimada('');
      setPresupuesto(''); setResponsable(''); setNotas('');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear proyecto');
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nuevo Proyecto</DialogTitle>
          <DialogDescription>Cree un nuevo proyecto para su empresa</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Código *</Label>
              <Input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="PRY-001" />
            </div>
            <div className="space-y-2">
              <Label>Nombre *</Label>
              <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre del proyecto" />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Descripción</Label>
              <Textarea value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2} placeholder="Descripción del proyecto" />
            </div>
            <div className="space-y-2">
              <Label>Cliente</Label>
              <Select value={clienteId} onValueChange={setClienteId}>
                <SelectTrigger><SelectValue placeholder="Seleccionar cliente" /></SelectTrigger>
                <SelectContent>
                  {clients.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Estado</Label>
              <Select value={estado} onValueChange={setEstado}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{ESTADOS_PROYECTO.map((e) => (<SelectItem key={e.key} value={e.key}>{e.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Fecha Inicio</Label>
              <Input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Fecha Fin Estimada</Label>
              <Input type="date" value={fechaFinEstimada} onChange={(e) => setFechaFinEstimada(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Presupuesto</Label>
 <NumericInput value={presupuesto} onChange={(e) => setPresupuesto(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <Label>Responsable</Label>
              <Input value={responsable} onChange={(e) => setResponsable(e.target.value)} placeholder="Gerente del proyecto" />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Notas</Label>
              <Textarea value={notas} onChange={(e) => setNotas(e.target.value)} rows={2} placeholder="Notas adicionales" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear Proyecto</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Proyecto Dialog ───────────────────────────────

function EditProyectoDialog({ proyecto, open, onOpenChange, clients, onUpdated }: {
  proyecto: ProyectoResponse; open: boolean; onOpenChange: (open: boolean) => void; clients: ClientResponse[]; onUpdated: () => void;
}) {
  const [codigo, setCodigo] = useState(proyecto.codigo);
  const [nombre, setNombre] = useState(proyecto.nombre);
  const [descripcion, setDescripcion] = useState(proyecto.descripcion || '');
  const [clienteId, setClienteId] = useState(proyecto.cliente_id || '');
  const [estado, setEstado] = useState(proyecto.estado);
  const [fechaInicio, setFechaInicio] = useState(proyecto.fecha_inicio?.split('T')[0] || '');
  const [fechaFinEstimada, setFechaFinEstimada] = useState(proyecto.fecha_fin_estimada?.split('T')[0] || '');
  const [presupuesto, setPresupuesto] = useState(proyecto.presupuesto.toString());
  const [ingreso, setIngreso] = useState(proyecto.ingreso.toString());
  const [responsable, setResponsable] = useState(proyecto.responsable || '');
  const [notas, setNotas] = useState(proyecto.notas || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setCodigo(proyecto.codigo);
    setNombre(proyecto.nombre);
    setDescripcion(proyecto.descripcion || '');
    setClienteId(proyecto.cliente_id || '');
    setEstado(proyecto.estado);
    setFechaInicio(proyecto.fecha_inicio?.split('T')[0] || '');
    setFechaFinEstimada(proyecto.fecha_fin_estimada?.split('T')[0] || '');
    setPresupuesto(proyecto.presupuesto.toString());
    setIngreso(proyecto.ingreso.toString());
    setResponsable(proyecto.responsable || '');
    setNotas(proyecto.notas || '');
  }, [proyecto]);

  async function handleSave() {
    if (!nombre) {
      toast.error('El nombre es requerido');
      return;
    }
    setSaving(true);
    try {
      const selectedClient = clients.find(c => c.id === clienteId);
      await updateProyecto(proyecto.id, {
        codigo: codigo || undefined,
        nombre,
        descripcion: descripcion || undefined,
        cliente_id: clienteId || undefined,
        cliente_nombre: selectedClient?.razon_social || undefined,
        estado,
        fecha_inicio: fechaInicio || undefined,
        fecha_fin_estimada: fechaFinEstimada || undefined,
        presupuesto: parseFloat(presupuesto) || undefined,
        ingreso: parseFloat(ingreso) || undefined,
        responsable: responsable || undefined,
        notas: notas || undefined,
      });
      toast.success('Proyecto actualizado');
      onOpenChange(false);
      onUpdated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al actualizar');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Proyecto</DialogTitle>
          <DialogDescription>Modifique los datos del proyecto</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Código</Label>
              <Input value={codigo} onChange={(e) => setCodigo(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Nombre *</Label>
              <Input value={nombre} onChange={(e) => setNombre(e.target.value)} />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Descripción</Label>
              <Textarea value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2} />
            </div>
            <div className="space-y-2">
              <Label>Cliente</Label>
              <Select value={clienteId} onValueChange={setClienteId}>
                <SelectTrigger><SelectValue placeholder="Seleccionar cliente" /></SelectTrigger>
                <SelectContent>
                  {clients.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Estado</Label>
              <Select value={estado} onValueChange={setEstado}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{ESTADOS_PROYECTO.map((e) => (<SelectItem key={e.key} value={e.key}>{e.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Fecha Inicio</Label>
              <Input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Fecha Fin Estimada</Label>
              <Input type="date" value={fechaFinEstimada} onChange={(e) => setFechaFinEstimada(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Presupuesto</Label>
 <NumericInput value={presupuesto} onChange={(e) => setPresupuesto(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Ingreso</Label>
 <NumericInput value={ingreso} onChange={(e) => setIngreso(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Responsable</Label>
              <Input value={responsable} onChange={(e) => setResponsable(e.target.value)} />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Notas</Label>
              <Textarea value={notas} onChange={(e) => setNotas(e.target.value)} rows={2} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Guardar</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Proyecto Detail Dialog ───────────────────────────────

function ProyectoDetailDialog({ proyecto, open, onOpenChange, onRecalcular }: {
  proyecto: ProyectoResponse; open: boolean; onOpenChange: (open: boolean) => void; onRecalcular: () => void;
}) {
  const [detail, setDetail] = useState<ProyectoResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!proyecto) return;
    setLoading(true);
    try {
      const data = await getProyecto(proyecto.id);
      setDetail(data);
    } catch {
      toast.error('Error al cargar detalle');
    } finally {
      setLoading(false);
    }
  }, [proyecto]);

  useEffect(() => {
    if (open && proyecto) {
      fetchDetail();
    }
  }, [open, proyecto, fetchDetail]);

  const p = detail || proyecto;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {p.codigo} - {p.nombre}
            {getEstadoBadge(p.estado)}
          </DialogTitle>
          <DialogDescription>
            {p.cliente_nombre && `Cliente: ${p.cliente_nombre}`}
            {p.responsable && ` | Responsable: ${p.responsable}`}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
        ) : (
          <div className="space-y-4">
            {/* Progress & Financial Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Progreso</p><div className="flex items-center gap-2"><Progress value={Number(p.progreso)} className="h-2 flex-1" /><span className="text-sm font-bold">{Number(p.progreso || 0).toFixed(0)}%</span></div></CardContent></Card>
              <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Presupuesto</p><p className="text-lg font-bold">{formatCurrency(p.presupuesto)}</p></CardContent></Card>
              <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Costo Real</p><p className="text-lg font-bold text-red-600">{formatCurrency(p.costo_real)}</p></CardContent></Card>
              <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Margen</p><p className={`text-lg font-bold ${p.margen >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{formatCurrency(p.margen)} ({Number(p.margen_porcentaje || 0).toFixed(1)}%)</p></CardContent></Card>
            </div>

            {/* Dates */}
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div><span className="text-muted-foreground">Inicio:</span> <span className="font-medium">{formatDate(p.fecha_inicio)}</span></div>
              <div><span className="text-muted-foreground">Fin Estimado:</span> <span className="font-medium">{formatDate(p.fecha_fin_estimada)}</span></div>
              <div><span className="text-muted-foreground">Fin Real:</span> <span className="font-medium">{formatDate(p.fecha_fin_real)}</span></div>
            </div>

            {/* Tareas */}
            <div>
              <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><CheckCircle2 className="h-4 w-4" /> Tareas ({p.tareas.length})</h4>
              {p.tareas.length > 0 ? (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {p.tareas.map((t) => (
                    <div key={t.id} className="flex items-center justify-between text-sm border rounded p-2">
                      <div className="flex items-center gap-2">
                        {getTareaEstadoBadge(t.estado)}
                        <span className="font-medium">{t.titulo}</span>
                        {getPrioridadBadge(t.prioridad)}
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-muted-foreground">{t.asignado_a || '-'}</span>
                        <div className="flex items-center gap-1">
                          <Progress value={Number(t.progreso)} className="h-1.5 w-12" />
                          <span className="text-xs">{Number(t.progreso || 0).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Sin tareas registradas</p>
              )}
            </div>

            {/* Recursos */}
            <div>
              <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><Users className="h-4 w-4" /> Recursos ({p.recursos.length})</h4>
              {p.recursos.length > 0 ? (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {p.recursos.filter(r => r.is_active).map((r) => (
                    <div key={r.id} className="flex items-center justify-between text-sm border rounded p-2">
                      <div className="flex items-center gap-2">
                        {getTipoRecursoBadge(r.tipo_recurso)}
                        <span className="font-medium">{r.nombre}</span>
                      </div>
                      <span className="text-sm">{formatCurrency(r.costo_total)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Sin recursos asignados</p>
              )}
            </div>

            {/* Timesheets Summary */}
            <div>
              <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><Clock className="h-4 w-4" /> Timesheets ({p.timesheets.length})</h4>
              {p.timesheets.length > 0 ? (
                <div className="text-sm">
                  <span className="text-muted-foreground">Total horas: </span>
                  <span className="font-medium">{p.timesheets.reduce((sum, t) => sum + Number(t.horas || 0), 0).toFixed(1)}h</span>
                  <span className="mx-2">|</span>
                  <span className="text-muted-foreground">Costo: </span>
                  <span className="font-medium text-red-600">{formatCurrency(p.timesheets.reduce((sum, t) => sum + Number(t.costo_total), 0))}</span>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Sin registros de horas</p>
              )}
            </div>

            {/* Costos */}
            <div>
              <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><DollarSign className="h-4 w-4" /> Costos ({p.costos.length})</h4>
              {p.costos.length > 0 ? (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {p.costos.map((c) => (
                    <div key={c.id} className="flex items-center justify-between text-sm border rounded p-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{c.concepto}</span>
                        {c.categoria && <Badge variant="outline" className="text-xs">{c.categoria}</Badge>}
                      </div>
                      <span className="text-sm text-red-600">{formatCurrency(c.monto)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Sin costos adicionales</p>
              )}
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onRecalcular}><Calculator className="mr-2 h-4 w-4" />Recalcular</Button>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Tareas Tab ───────────────────────────────────

function TareasTab({ companyId }: { companyId: string }) {
  const [proyectos, setProyectos] = useState<ProyectoResponse[]>([]);
  const [selectedProyectoId, setSelectedProyectoId] = useState<string>('');
  const [tareas, setTareas] = useState<ProyectoTareaResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editTarea, setEditTarea] = useState<ProyectoTareaResponse | null>(null);
  const [operating, setOperating] = useState(false);
  const isInitialLoadRef = useRef(true);

  const loadProyectos = useCallback(async () => {
    if (!companyId) return;
    try {
      const proys = await getProyectos({ company_id: companyId });
      setProyectos(proys);
      if (isInitialLoadRef.current && proys.length > 0 && !selectedProyectoId) {
        setSelectedProyectoId(proys[0].id);
        isInitialLoadRef.current = false;
      }
    } catch {
      toast.error('Error al cargar proyectos');
    }
  }, [companyId, selectedProyectoId]);

  const loadTareas = useCallback(async () => {
    if (!selectedProyectoId) { setLoading(false); return; }
    setLoading(true);
    try {
      const ts = await getProyectoTareas(selectedProyectoId);
      setTareas(ts);
    } catch {
      toast.error('Error al cargar tareas');
    } finally {
      setLoading(false);
    }
  }, [selectedProyectoId]);

  useEffect(() => { loadProyectos(); }, [loadProyectos]);
  useEffect(() => { loadTareas(); }, [loadTareas]);

  async function handleDelete(id: string) {
    if (!confirm('¿Eliminar esta tarea?')) return;
    setOperating(true);
    try {
      await deleteProyectoTarea(id);
      toast.success('Tarea eliminada');
      loadTareas();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    } finally {
      setOperating(false);
    }
  }

  async function handleToggleEstado(tarea: ProyectoTareaResponse) {
    setOperating(true);
    try {
      const newEstado = tarea.estado === 'completada' ? 'pendiente' : tarea.estado === 'pendiente' ? 'en_progreso' : 'completada';
      const newProgreso = newEstado === 'completada' ? 100 : tarea.progreso;
      await updateProyectoTarea(tarea.id, { estado: newEstado, progreso: newProgreso });
      toast.success(`Tarea marcada como ${newEstado.replace('_', ' ')}`);
      loadTareas();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al actualizar');
    } finally {
      setOperating(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={selectedProyectoId} onValueChange={setSelectedProyectoId}>
          <SelectTrigger className="w-[250px]">
            <SelectValue placeholder="Seleccionar proyecto" />
          </SelectTrigger>
          <SelectContent>
            {proyectos.map((p) => (<SelectItem key={p.id} value={p.id}>{p.codigo} - {p.nombre}</SelectItem>))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadTareas}><RefreshCw className="h-4 w-4" /></Button>
        <div className="flex-1" />
        {selectedProyectoId && (
          <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nueva Tarea</Button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : tareas.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Título</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Prioridad</TableHead>
                    <TableHead>Fase</TableHead>
                    <TableHead>Asignado</TableHead>
                    <TableHead className="text-right">H. Estimadas</TableHead>
                    <TableHead className="text-right">H. Reales</TableHead>
                    <TableHead>Progreso</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tareas.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="font-medium">{t.titulo}</TableCell>
                      <TableCell>{getTareaEstadoBadge(t.estado)}</TableCell>
                      <TableCell>{getPrioridadBadge(t.prioridad)}</TableCell>
                      <TableCell className="text-sm">{t.fase || '-'}</TableCell>
                      <TableCell className="text-sm">{t.asignado_a || '-'}</TableCell>
                      <TableCell className="text-right">{Number(t.horas_estimadas || 0).toFixed(1)}</TableCell>
                      <TableCell className="text-right">{Number(t.horas_reales || 0).toFixed(1)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={Number(t.progreso)} className="h-2 w-14" />
                          <span className="text-xs">{Number(t.progreso || 0).toFixed(0)}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleToggleEstado(t)} title="Cambiar estado" disabled={operating}>
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setEditTarea(t)}><Pencil className="h-3.5 w-3.5" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(t.id)} disabled={operating}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
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
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle2 className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin tareas</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {selectedProyectoId ? 'Cree una tarea para este proyecto' : 'Seleccione un proyecto para ver sus tareas'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Create Tarea Dialog */}
      {selectedProyectoId && (
        <CreateTareaDialog open={showCreate} onOpenChange={setShowCreate} proyectoId={selectedProyectoId} onCreated={loadTareas} />
      )}

      {/* Edit Tarea Dialog */}
      {editTarea && (
        <EditTareaDialog tarea={editTarea} open={!!editTarea} onOpenChange={(open) => { if (!open) setEditTarea(null); }} onUpdated={loadTareas} />
      )}
    </div>
  );
}

// ─── Create Tarea Dialog ───────────────────────────────

function CreateTareaDialog({ open, onOpenChange, proyectoId, onCreated }: {
  open: boolean; onOpenChange: (open: boolean) => void; proyectoId: string; onCreated: () => void;
}) {
  const [titulo, setTitulo] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [estado, setEstado] = useState('pendiente');
  const [prioridad, setPrioridad] = useState('media');
  const [fase, setFase] = useState('');
  const [asignadoA, setAsignadoA] = useState('');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFinEstimada, setFechaFinEstimada] = useState('');
  const [horasEstimadas, setHorasEstimadas] = useState('');
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    if (!titulo) {
      toast.error('El título es requerido');
      return;
    }
    setCreating(true);
    try {
      await createProyectoTarea(proyectoId, {
        titulo,
        descripcion: descripcion || undefined,
        estado,
        prioridad,
        fase: fase || undefined,
        asignado_a: asignadoA || undefined,
        fecha_inicio: fechaInicio || undefined,
        fecha_fin_estimada: fechaFinEstimada || undefined,
        horas_estimadas: horasEstimadas ? parseFloat(horasEstimadas) : undefined,
      });
      toast.success('Tarea creada exitosamente');
      onOpenChange(false);
      setTitulo(''); setDescripcion(''); setEstado('pendiente'); setPrioridad('media');
      setFase(''); setAsignadoA(''); setFechaInicio(''); setFechaFinEstimada(''); setHorasEstimadas('');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear tarea');
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva Tarea</DialogTitle>
          <DialogDescription>Agregue una tarea al proyecto</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2 col-span-2">
              <Label>Título *</Label>
              <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Título de la tarea" />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Descripción</Label>
              <Textarea value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2} />
            </div>
            <div className="space-y-2">
              <Label>Estado</Label>
              <Select value={estado} onValueChange={setEstado}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{ESTADOS_TAREA.map((e) => (<SelectItem key={e.key} value={e.key}>{e.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Prioridad</Label>
              <Select value={prioridad} onValueChange={setPrioridad}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{PRIORIDADES.map((p) => (<SelectItem key={p.key} value={p.key}>{p.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Fase</Label>
              <Input value={fase} onChange={(e) => setFase(e.target.value)} placeholder="Fase del proyecto" />
            </div>
            <div className="space-y-2">
              <Label>Asignado a</Label>
              <Input value={asignadoA} onChange={(e) => setAsignadoA(e.target.value)} placeholder="Nombre del responsable" />
            </div>
            <div className="space-y-2">
              <Label>Fecha Inicio</Label>
              <Input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Fecha Fin Estimada</Label>
              <Input type="date" value={fechaFinEstimada} onChange={(e) => setFechaFinEstimada(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Horas Estimadas</Label>
 <NumericInput value={horasEstimadas} onChange={(e) => setHorasEstimadas(e.target.value)} placeholder="0" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear Tarea</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Tarea Dialog ───────────────────────────────

function EditTareaDialog({ tarea, open, onOpenChange, onUpdated }: {
  tarea: ProyectoTareaResponse; open: boolean; onOpenChange: (open: boolean) => void; onUpdated: () => void;
}) {
  const [titulo, setTitulo] = useState(tarea.titulo);
  const [descripcion, setDescripcion] = useState(tarea.descripcion || '');
  const [estado, setEstado] = useState(tarea.estado);
  const [prioridad, setPrioridad] = useState(tarea.prioridad);
  const [fase, setFase] = useState(tarea.fase || '');
  const [asignadoA, setAsignadoA] = useState(tarea.asignado_a || '');
  const [horasEstimadas, setHorasEstimadas] = useState(tarea.horas_estimadas.toString());
  const [progreso, setProgreso] = useState(tarea.progreso.toString());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTitulo(tarea.titulo);
    setDescripcion(tarea.descripcion || '');
    setEstado(tarea.estado);
    setPrioridad(tarea.prioridad);
    setFase(tarea.fase || '');
    setAsignadoA(tarea.asignado_a || '');
    setHorasEstimadas(tarea.horas_estimadas.toString());
    setProgreso(tarea.progreso.toString());
  }, [tarea]);

  async function handleSave() {
    setSaving(true);
    try {
      await updateProyectoTarea(tarea.id, {
        titulo,
        descripcion: descripcion || undefined,
        estado,
        prioridad,
        fase: fase || undefined,
        asignado_a: asignadoA || undefined,
        horas_estimadas: parseFloat(horasEstimadas) || undefined,
        progreso: parseFloat(progreso) || undefined,
      });
      toast.success('Tarea actualizada');
      onOpenChange(false);
      onUpdated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al actualizar');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Tarea</DialogTitle>
          <DialogDescription>Modifique los datos de la tarea</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2 col-span-2">
              <Label>Título *</Label>
              <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Estado</Label>
              <Select value={estado} onValueChange={setEstado}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{ESTADOS_TAREA.map((e) => (<SelectItem key={e.key} value={e.key}>{e.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Prioridad</Label>
              <Select value={prioridad} onValueChange={setPrioridad}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{PRIORIDADES.map((p) => (<SelectItem key={p.key} value={p.key}>{p.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Progreso (%)</Label>
 <NumericInput value={progreso} onChange={(e) => setProgreso(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Horas Estimadas</Label>
 <NumericInput value={horasEstimadas} onChange={(e) => setHorasEstimadas(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Fase</Label>
              <Input value={fase} onChange={(e) => setFase(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Asignado a</Label>
              <Input value={asignadoA} onChange={(e) => setAsignadoA(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Guardar</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Recursos Tab ───────────────────────────────────

function RecursosTab({ companyId }: { companyId: string }) {
  const [proyectos, setProyectos] = useState<ProyectoResponse[]>([]);
  const [selectedProyectoId, setSelectedProyectoId] = useState<string>('');
  const [recursos, setRecursos] = useState<ProyectoRecursoResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [operating, setOperating] = useState(false);
  const isInitialLoadRef = useRef(true);

  const loadProyectos = useCallback(async () => {
    if (!companyId) return;
    try {
      const proys = await getProyectos({ company_id: companyId });
      setProyectos(proys);
      if (isInitialLoadRef.current && proys.length > 0 && !selectedProyectoId) {
        setSelectedProyectoId(proys[0].id);
        isInitialLoadRef.current = false;
      }
    } catch {
      toast.error('Error al cargar proyectos');
    }
  }, [companyId, selectedProyectoId]);

  const loadRecursos = useCallback(async () => {
    if (!selectedProyectoId) { setLoading(false); return; }
    setLoading(true);
    try {
      const rs = await getProyectoRecursos(selectedProyectoId);
      setRecursos(rs);
    } catch {
      toast.error('Error al cargar recursos');
    } finally {
      setLoading(false);
    }
  }, [selectedProyectoId]);

  useEffect(() => { loadProyectos(); }, [loadProyectos]);
  useEffect(() => { loadRecursos(); }, [loadRecursos]);

  async function handleDelete(id: string) {
    if (!confirm('¿Eliminar este recurso?')) return;
    setOperating(true);
    try {
      await deleteProyectoRecurso(id);
      toast.success('Recurso eliminado');
      loadRecursos();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    } finally {
      setOperating(false);
    }
  }

  async function handleLiberar(recurso: ProyectoRecursoResponse) {
    setOperating(true);
    try {
      await updateProyectoRecurso(recurso.id, {
        fecha_liberacion: new Date().toISOString(),
        is_active: false,
      });
      toast.success('Recurso liberado');
      loadRecursos();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al liberar recurso');
    } finally {
      setOperating(false);
    }
  }

  const totalCosto = recursos.filter(r => r.is_active).reduce((sum, r) => sum + Number(r.costo_total), 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={selectedProyectoId} onValueChange={setSelectedProyectoId}>
          <SelectTrigger className="w-[250px]">
            <SelectValue placeholder="Seleccionar proyecto" />
          </SelectTrigger>
          <SelectContent>
            {proyectos.map((p) => (<SelectItem key={p.id} value={p.id}>{p.codigo} - {p.nombre}</SelectItem>))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadRecursos}><RefreshCw className="h-4 w-4" /></Button>
        <div className="flex-1" />
        {selectedProyectoId && (
          <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Asignar Recurso</Button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : recursos.length > 0 ? (
        <>
          <Card>
            <CardContent className="p-0">
              <ScrollArea className="max-h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Costo Unit.</TableHead>
                      <TableHead>Cantidad</TableHead>
                      <TableHead className="text-right">Costo Total</TableHead>
                      <TableHead>Asignación</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recursos.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell>{getTipoRecursoBadge(r.tipo_recurso)}</TableCell>
                        <TableCell className="font-medium">{r.nombre}</TableCell>
                        <TableCell>{formatCurrency(r.costo_unitario)}</TableCell>
                        <TableCell>{Number(r.cantidad || 0).toFixed(0)}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(r.costo_total)}</TableCell>
                        <TableCell className="text-sm">
                          {r.fecha_asignacion ? formatDate(r.fecha_asignacion) : '-'}
                          {r.fecha_liberacion ? ` → ${formatDate(r.fecha_liberacion)}` : ''}
                        </TableCell>
                        <TableCell>
                          {r.is_active ? (
                            <Badge className="bg-emerald-500 text-white text-xs">Activo</Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs">Liberado</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            {r.is_active && (
                              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleLiberar(r)} title="Liberar recurso" disabled={operating}>
                                <Calendar className="h-3.5 w-3.5" />
                              </Button>
                            )}
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(r.id)} disabled={operating}>
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
          <div className="flex justify-end">
            <span className="text-sm text-muted-foreground">Total recursos activos: </span>
            <span className="text-sm font-bold ml-1">{formatCurrency(totalCosto)}</span>
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin recursos</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {selectedProyectoId ? 'Asigne recursos a este proyecto' : 'Seleccione un proyecto para ver sus recursos'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Create Recurso Dialog */}
      {selectedProyectoId && (
        <CreateRecursoDialog open={showCreate} onOpenChange={setShowCreate} proyectoId={selectedProyectoId} onCreated={loadRecursos} />
      )}
    </div>
  );
}

// ─── Create Recurso Dialog ───────────────────────────────

function CreateRecursoDialog({ open, onOpenChange, proyectoId, onCreated }: {
  open: boolean; onOpenChange: (open: boolean) => void; proyectoId: string; onCreated: () => void;
}) {
  const [tipoRecurso, setTipoRecurso] = useState('humano');
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [costoUnitario, setCostoUnitario] = useState('');
  const [cantidad, setCantidad] = useState('1');
  const [fechaAsignacion, setFechaAsignacion] = useState('');
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    if (!nombre) {
      toast.error('El nombre es requerido');
      return;
    }
    setCreating(true);
    try {
      await createProyectoRecurso(proyectoId, {
        tipo_recurso: tipoRecurso,
        nombre,
        descripcion: descripcion || undefined,
        costo_unitario: costoUnitario ? parseFloat(costoUnitario) : undefined,
        cantidad: cantidad ? parseFloat(cantidad) : undefined,
        fecha_asignacion: fechaAsignacion || undefined,
      });
      toast.success('Recurso asignado exitosamente');
      onOpenChange(false);
      setTipoRecurso('humano'); setNombre(''); setDescripcion('');
      setCostoUnitario(''); setCantidad('1'); setFechaAsignacion('');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al asignar recurso');
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Asignar Recurso</DialogTitle>
          <DialogDescription>Agregue un recurso al proyecto</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Tipo de Recurso</Label>
              <Select value={tipoRecurso} onValueChange={setTipoRecurso}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{TIPOS_RECURSO.map((t) => (<SelectItem key={t.key} value={t.key}>{t.label}</SelectItem>))}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Nombre *</Label>
              <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre del recurso" />
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Descripción</Label>
              <Input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Descripción del recurso" />
            </div>
            <div className="space-y-2">
              <Label>Costo Unitario</Label>
 <NumericInput value={costoUnitario} onChange={(e) => setCostoUnitario(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <Label>Cantidad</Label>
 <NumericInput value={cantidad} onChange={(e) => setCantidad(e.target.value)} placeholder="1" />
            </div>
            <div className="space-y-2">
              <Label>Fecha Asignación</Label>
              <Input type="date" value={fechaAsignacion} onChange={(e) => setFechaAsignacion(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Asignar Recurso</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Timesheet Tab ───────────────────────────────────

function TimesheetTab({ companyId }: { companyId: string }) {
  const [proyectos, setProyectos] = useState<ProyectoResponse[]>([]);
  const [selectedProyectoId, setSelectedProyectoId] = useState<string>('');
  const [timesheets, setTimesheets] = useState<ProyectoTimesheetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [operating, setOperating] = useState(false);
  const isInitialLoadRef = useRef(true);

  const loadProyectos = useCallback(async () => {
    if (!companyId) return;
    try {
      const proys = await getProyectos({ company_id: companyId });
      setProyectos(proys);
      if (isInitialLoadRef.current && proys.length > 0 && !selectedProyectoId) {
        setSelectedProyectoId(proys[0].id);
        isInitialLoadRef.current = false;
      }
    } catch {
      toast.error('Error al cargar proyectos');
    }
  }, [companyId, selectedProyectoId]);

  const loadTimesheets = useCallback(async () => {
    if (!selectedProyectoId) { setLoading(false); return; }
    setLoading(true);
    try {
      const ts = await getProyectoTimesheets(selectedProyectoId);
      setTimesheets(ts);
    } catch {
      toast.error('Error al cargar timesheets');
    } finally {
      setLoading(false);
    }
  }, [selectedProyectoId]);

  useEffect(() => { loadProyectos(); }, [loadProyectos]);
  useEffect(() => { loadTimesheets(); }, [loadTimesheets]);

  async function handleDelete(id: string) {
    if (!confirm('¿Eliminar este registro?')) return;
    setOperating(true);
    try {
      await deleteProyectoTimesheet(id);
      toast.success('Registro eliminado');
      loadTimesheets();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    } finally {
      setOperating(false);
    }
  }

  const totalHoras = timesheets.reduce((sum, t) => sum + Number(t.horas || 0), 0);
  const totalCosto = timesheets.reduce((sum, t) => sum + Number(t.costo_total), 0);
  const horasFacturables = timesheets.filter(t => t.es_facturable).reduce((sum, t) => sum + Number(t.horas || 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={selectedProyectoId} onValueChange={setSelectedProyectoId}>
          <SelectTrigger className="w-[250px]">
            <SelectValue placeholder="Seleccionar proyecto" />
          </SelectTrigger>
          <SelectContent>
            {proyectos.map((p) => (<SelectItem key={p.id} value={p.id}>{p.codigo} - {p.nombre}</SelectItem>))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadTimesheets}><RefreshCw className="h-4 w-4" /></Button>
        <div className="flex-1" />
        {selectedProyectoId && (
          <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Registrar Horas</Button>
        )}
      </div>

      {/* Summary */}
      {timesheets.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total Horas</p><p className="text-2xl font-bold">{totalHoras.toFixed(1)}h</p></CardContent></Card>
          <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Horas Facturables</p><p className="text-2xl font-bold text-emerald-600">{horasFacturables.toFixed(1)}h</p></CardContent></Card>
          <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Costo Total</p><p className="text-2xl font-bold text-red-600">{formatCurrency(totalCosto)}</p></CardContent></Card>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : timesheets.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[400px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Empleado</TableHead>
                    <TableHead className="text-right">Horas</TableHead>
                    <TableHead className="text-right">Tarifa/Hora</TableHead>
                    <TableHead className="text-right">Costo</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead>Facturable</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {timesheets.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="text-sm">{formatDate(t.fecha)}</TableCell>
                      <TableCell className="font-medium">{t.empleado_nombre}</TableCell>
                      <TableCell className="text-right">{Number(t.horas || 0).toFixed(1)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(t.tarifa_hora)}</TableCell>
                      <TableCell className="text-right font-medium">{formatCurrency(t.costo_total)}</TableCell>
                      <TableCell className="text-sm max-w-48 truncate">{t.descripcion || '-'}</TableCell>
                      <TableCell>
                        {t.es_facturable ? (
                          <Badge className="bg-emerald-500 text-white text-xs">Sí</Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs">No</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(t.id)} disabled={operating}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin registros de horas</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {selectedProyectoId ? 'Registre horas trabajadas en este proyecto' : 'Seleccione un proyecto para ver timesheets'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Create Timesheet Dialog */}
      {selectedProyectoId && (
        <CreateTimesheetDialog open={showCreate} onOpenChange={setShowCreate} proyectoId={selectedProyectoId} companyId={companyId} onCreated={loadTimesheets} />
      )}
    </div>
  );
}

// ─── Create Timesheet Dialog ───────────────────────────────

function CreateTimesheetDialog({ open, onOpenChange, proyectoId, companyId, onCreated }: {
  open: boolean; onOpenChange: (open: boolean) => void; proyectoId: string; companyId: string; onCreated: () => void;
}) {
  const [empleadoNombre, setEmpleadoNombre] = useState('');
  const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0]);
  const [horas, setHoras] = useState('');
  const [tarifaHora, setTarifaHora] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [esFacturable, setEsFacturable] = useState('si');
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    if (!empleadoNombre || !horas || !fecha) {
      toast.error('Complete los campos requeridos (empleado, fecha, horas)');
      return;
    }
    setCreating(true);
    try {
      await createProyectoTimesheet(proyectoId, {
        company_id: companyId,
        empleado_nombre: empleadoNombre,
        fecha,
        horas: parseFloat(horas),
        tarifa_hora: tarifaHora ? parseFloat(tarifaHora) : undefined,
        descripcion: descripcion || undefined,
        es_facturable: esFacturable === 'si',
      });
      toast.success('Horas registradas exitosamente');
      onOpenChange(false);
      setEmpleadoNombre(''); setFecha(new Date().toISOString().split('T')[0]);
      setHoras(''); setTarifaHora(''); setDescripcion(''); setEsFacturable('si');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al registrar horas');
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Registrar Horas</DialogTitle>
          <DialogDescription>Registre horas trabajadas en el proyecto</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2 col-span-2">
              <Label>Nombre del Empleado *</Label>
              <Input value={empleadoNombre} onChange={(e) => setEmpleadoNombre(e.target.value)} placeholder="Nombre del empleado" />
            </div>
            <div className="space-y-2">
              <Label>Fecha *</Label>
              <Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Horas *</Label>
 <NumericInput value={horas} onChange={(e) => setHoras(e.target.value)} placeholder="8" />
            </div>
            <div className="space-y-2">
              <Label>Tarifa por Hora</Label>
 <NumericInput value={tarifaHora} onChange={(e) => setTarifaHora(e.target.value)} placeholder="25.00" />
            </div>
            <div className="space-y-2">
              <Label>Facturable</Label>
              <Select value={esFacturable} onValueChange={setEsFacturable}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="si">Sí - Facturable</SelectItem>
                  <SelectItem value="no">No - No facturable</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 col-span-2">
              <Label>Descripción</Label>
              <Textarea value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2} placeholder="Descripción del trabajo realizado" />
            </div>
          </div>
          {horas && tarifaHora && (
            <div className="text-sm text-muted-foreground">
              Costo total: <span className="font-bold text-foreground">{formatCurrency(parseFloat(horas) * parseFloat(tarifaHora))}</span>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Registrar Horas</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Rentabilidad Tab ───────────────────────────────────

function RentabilidadTab({ companyId }: { companyId: string }) {
  const [proyectos, setProyectos] = useState<ProyectoResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const proys = await getProyectos({ company_id: companyId });
      setProyectos(proys);
    } catch {
      toast.error('Error al cargar proyectos');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  // Calculate aggregated stats
  const activeProjects = proyectos.filter(p => p.is_active);
  const totalPresupuesto = activeProjects.reduce((s, p) => s + Number(p.presupuesto), 0);
  const totalCostoReal = activeProjects.reduce((s, p) => s + Number(p.costo_real), 0);
  const totalIngreso = activeProjects.reduce((s, p) => s + Number(p.ingreso), 0);
  const totalMargen = activeProjects.reduce((s, p) => s + Number(p.margen), 0);
  const margenPct = totalIngreso > 0 ? (totalMargen / totalIngreso * 100) : 0;
  const desviacionPresupuesto = totalPresupuesto - totalCostoReal;

  // Sort by profitability
  const sortedByMargin = [...activeProjects].sort((a, b) => Number(b.margen_porcentaje) - Number(a.margen_porcentaje));
  const profitableProjects = activeProjects.filter(p => Number(p.margen) > 0);
  const lossProjects = activeProjects.filter(p => Number(p.margen) < 0);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* Overall KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Ingreso Total</p>
            <p className="text-2xl font-bold text-emerald-600">{formatCurrency(totalIngreso)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Costo Total</p>
            <p className="text-2xl font-bold text-red-600">{formatCurrency(totalCostoReal)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Margen Neto</p>
            <p className={`text-2xl font-bold ${totalMargen >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{formatCurrency(totalMargen)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">% Margen Global</p>
            <p className={`text-2xl font-bold ${margenPct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{Number(margenPct || 0).toFixed(1)}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Budget vs Actual */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4" /> Presupuesto vs Costo Real
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Presupuestado</span>
              <span className="font-medium">{formatCurrency(totalPresupuesto)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Costo Real</span>
              <span className="font-medium text-red-600">{formatCurrency(totalCostoReal)}</span>
            </div>
            <Separator />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Desviación</span>
              <span className={`font-bold ${desviacionPresupuesto >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {desviacionPresupuesto >= 0 ? '+' : ''}{formatCurrency(desviacionPresupuesto)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">% Ejecución</span>
              <span className="font-medium">
                {totalPresupuesto > 0 ? ((totalCostoReal / totalPresupuesto) * 100).toFixed(1) : 0}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" /> Resumen por Resultado
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Proyectos Rentables</span>
              <span className="font-medium text-emerald-600">{profitableProjects.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Proyectos en Pérdida</span>
              <span className="font-medium text-red-600">{lossProjects.length}</span>
            </div>
            <Separator />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Margen Rentables</span>
              <span className="font-medium text-emerald-600">{formatCurrency(profitableProjects.reduce((s, p) => s + Number(p.margen), 0))}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Pérdida</span>
              <span className="font-medium text-red-600">{formatCurrency(lossProjects.reduce((s, p) => s + Number(p.margen), 0))}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Profitability Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Rentabilidad por Proyecto</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="max-h-[400px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Proyecto</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Presupuesto</TableHead>
                  <TableHead className="text-right">Costo Real</TableHead>
                  <TableHead className="text-right">Ingreso</TableHead>
                  <TableHead className="text-right">Margen</TableHead>
                  <TableHead>% Margen</TableHead>
                  <TableHead>Progreso</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedByMargin.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <div>
                        <span className="font-mono text-xs text-muted-foreground">{p.codigo}</span>
                        <p className="font-medium text-sm">{p.nombre}</p>
                      </div>
                    </TableCell>
                    <TableCell>{getEstadoBadge(p.estado)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(p.presupuesto)}</TableCell>
                    <TableCell className="text-right text-red-600">{formatCurrency(p.costo_real)}</TableCell>
                    <TableCell className="text-right text-emerald-600">{formatCurrency(p.ingreso)}</TableCell>
                    <TableCell className={`text-right font-bold ${Number(p.margen) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {formatCurrency(p.margen)}
                    </TableCell>
                    <TableCell>
                      <Badge className={`${Number(p.margen_porcentaje) >= 20 ? 'bg-emerald-600' : Number(p.margen_porcentaje) >= 0 ? 'bg-amber-500' : 'bg-red-600'} text-white`}>
                        {Number(p.margen_porcentaje || 0).toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={Number(p.progreso)} className="h-2 w-14" />
                        <span className="text-xs">{Number(p.progreso || 0).toFixed(0)}%</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>

      {activeProjects.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <TrendingUp className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin datos de rentabilidad</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree proyectos y registre ingresos/costos para ver la rentabilidad</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
