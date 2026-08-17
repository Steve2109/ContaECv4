'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
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
import {
  Users,
  Loader2,
  RefreshCw,
  Plus,
  Pencil,
  Trash2,
  DollarSign,
  FileText,
  Shield,
  Baby,
  Clock,
  Calculator,
  TrendingUp,
  CheckCircle2,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getEmployees,
  createEmployee,
  updateEmployee,
  deactivateEmployee,
  getPayrolls,
  generatePayroll,
  approvePayroll,
  payPayroll,
  calculateDecimoTercero,
  calculateDecimoCuarto,
  getIESSReport,
  createCargaFamiliar,
  getCargasFamiliares,
  deleteCargaFamiliar,
  createAsistencia,
  getAsistencia,
  calcularLiquidacion,
  getLiquidaciones,
  aprobarLiquidacion,
  calcularUtilidades,
  getUtilidades,
  type Employee,
  type RolPago,
  type CargaFamiliar,
  type AsistenciaRecord,
  type Liquidacion,
  type UtilidadRecord,
  type User,
  type Company,
} from '@/lib/api';

function formatCurrency(amount: number): string {
  return amount.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

interface ContaECHRProps {
  user: User;
  companies: Company[];
}

export function ContaECHR({ user: _user, companies }: ContaECHRProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Recursos Humanos</h2>
          <p className="text-muted-foreground">Gestion de empleados, nominas y beneficios</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin empresas registradas</h3>
            <p className="text-muted-foreground text-sm mt-1">Registre una empresa para gestionar RRHH.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Recursos Humanos</h2>
          <p className="text-muted-foreground">Gestion de empleados, nominas y beneficios</p>
        </div>
        {companies.length > 1 && (
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">Empresa:</Label>
            <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
              <SelectTrigger className="w-[220px]"><SelectValue placeholder="Empresa" /></SelectTrigger>
              <SelectContent>
                {companies.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <Tabs defaultValue="empleados" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="empleados" className="gap-1.5"><Users className="h-3.5 w-3.5" /><span className="hidden sm:inline">Empleados</span></TabsTrigger>
          <TabsTrigger value="roles" className="gap-1.5"><DollarSign className="h-3.5 w-3.5" /><span className="hidden sm:inline">Roles de Pago</span></TabsTrigger>
          <TabsTrigger value="decimos" className="gap-1.5"><FileText className="h-3.5 w-3.5" /><span className="hidden sm:inline">Decimos</span></TabsTrigger>
          <TabsTrigger value="iess" className="gap-1.5"><Shield className="h-3.5 w-3.5" /><span className="hidden sm:inline">IESS</span></TabsTrigger>
          <TabsTrigger value="cargas" className="gap-1.5"><Baby className="h-3.5 w-3.5" /><span className="hidden sm:inline">Cargas</span></TabsTrigger>
          <TabsTrigger value="asistencia" className="gap-1.5"><Clock className="h-3.5 w-3.5" /><span className="hidden sm:inline">Asistencia</span></TabsTrigger>
          <TabsTrigger value="liquidaciones" className="gap-1.5"><Calculator className="h-3.5 w-3.5" /><span className="hidden sm:inline">Liquidaciones</span></TabsTrigger>
          <TabsTrigger value="utilidades" className="gap-1.5"><TrendingUp className="h-3.5 w-3.5" /><span className="hidden sm:inline">Utilidades</span></TabsTrigger>
        </TabsList>

        <TabsContent value="empleados"><EmpleadosTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="roles"><RolesPagoTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="decimos"><DecimosTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="iess"><IESSTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="cargas"><CargasFamiliaresTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="asistencia"><AsistenciaTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="liquidaciones"><LiquidacionesTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="utilidades"><UtilidadesTab companyId={selectedCompanyId} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Empleados Tab ───────────────────────────────────────────

function EmpleadosTab({ companyId }: { companyId: string }) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    cedula: '', apellidos: '', nombres: '', cargo: '', departamento: '',
    tipo_contrato: 'indefinido', fecha_ingreso: '', sueldo_mensual: '',
    tipo_pago: 'mensual', email: '', telefono: '', genero: '', banco: '',
  });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getEmployees({ company_id: companyId });
      setEmployees(data);
    } catch {
      toast.error('Error al cargar empleados');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  function openCreate() {
    setEditingEmployee(null);
    setForm({ cedula: '', apellidos: '', nombres: '', cargo: '', departamento: '', tipo_contrato: 'indefinido', fecha_ingreso: new Date().toISOString().slice(0, 10), sueldo_mensual: '', tipo_pago: 'mensual', email: '', telefono: '', genero: '', banco: '' });
    setShowDialog(true);
  }

  function openEdit(emp: Employee) {
    setEditingEmployee(emp);
    setForm({
      cedula: emp.cedula, apellidos: emp.apellidos, nombres: emp.nombres,
      cargo: emp.cargo, departamento: emp.departamento || '',
      tipo_contrato: emp.tipo_contrato, fecha_ingreso: emp.fecha_ingreso.slice(0, 10),
      sueldo_mensual: String(emp.sueldo_mensual), tipo_pago: emp.tipo_pago,
      email: emp.email || '', telefono: emp.telefono || '', genero: emp.genero || '',
      banco: emp.banco || '',
    });
    setShowDialog(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (editingEmployee) {
        await updateEmployee(editingEmployee.id, {
          apellidos: form.apellidos, nombres: form.nombres, cargo: form.cargo,
          departamento: form.departamento || undefined, tipo_contrato: form.tipo_contrato,
          sueldo_mensual: Number(form.sueldo_mensual), tipo_pago: form.tipo_pago,
          email: form.email || undefined, telefono: form.telefono || undefined,
          genero: form.genero || undefined, banco: form.banco || undefined,
        });
        toast.success('Empleado actualizado');
      } else {
        await createEmployee({
          company_id: companyId, cedula: form.cedula, apellidos: form.apellidos,
          nombres: form.nombres, cargo: form.cargo,
          departamento: form.departamento || undefined, tipo_contrato: form.tipo_contrato,
          fecha_ingreso: form.fecha_ingreso, sueldo_mensual: Number(form.sueldo_mensual),
          tipo_pago: form.tipo_pago, email: form.email || undefined,
          telefono: form.telefono || undefined, genero: form.genero || undefined,
          banco: form.banco || undefined,
        });
        toast.success('Empleado creado');
      }
      setShowDialog(false);
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(id: string) {
    try {
      await deactivateEmployee(id);
      toast.success('Empleado desactivado');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al desactivar');
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" /> Nuevo Empleado</Button>
      </div>

      {employees.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cédula</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Cargo</TableHead>
                    <TableHead>Departamento</TableHead>
                    <TableHead className="text-right">Sueldo</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {employees.map((emp) => (
                    <TableRow key={emp.id}>
                      <TableCell className="font-mono text-xs">{emp.cedula}</TableCell>
                      <TableCell>{emp.apellidos} {emp.nombres}</TableCell>
                      <TableCell>{emp.cargo}</TableCell>
                      <TableCell>{emp.departamento || '-'}</TableCell>
                      <TableCell className="text-right">${formatCurrency(emp.sueldo_mensual)}</TableCell>
                      <TableCell><Badge variant={emp.is_active ? 'default' : 'secondary'} className={emp.is_active ? 'bg-emerald-600' : ''}>{emp.is_active ? 'Activo' : 'Inactivo'}</Badge></TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(emp)}><Pencil className="h-3.5 w-3.5" /></Button>
                          {emp.is_active && (
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDeactivate(emp.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                          )}
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
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin empleados</h3>
            <p className="text-muted-foreground text-sm mt-1">Agregue empleados para comenzar</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingEmployee ? 'Editar Empleado' : 'Nuevo Empleado'}</DialogTitle>
            <DialogDescription>{editingEmployee ? 'Modifique los datos del empleado' : 'Registre un nuevo empleado'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Cédula</Label><Input value={form.cedula} onChange={(e) => setForm({ ...form, cedula: e.target.value })} maxLength={10} disabled={!!editingEmployee} /></div>
              <div className="space-y-2"><Label>Genero</Label><Select value={form.genero} onValueChange={(v) => setForm({ ...form, genero: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent><SelectItem value="M">Masculino</SelectItem><SelectItem value="F">Femenino</SelectItem></SelectContent></Select></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Apellidos</Label><Input value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} /></div>
              <div className="space-y-2"><Label>Nombres</Label><Input value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Cargo</Label><Input value={form.cargo} onChange={(e) => setForm({ ...form, cargo: e.target.value })} /></div>
              <div className="space-y-2"><Label>Departamento</Label><Input value={form.departamento} onChange={(e) => setForm({ ...form, departamento: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Tipo Contrato</Label><Select value={form.tipo_contrato} onValueChange={(v) => setForm({ ...form, tipo_contrato: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent><SelectItem value="indefinido">Indefinido</SelectItem><SelectItem value="fijo">Fijo</SelectItem><SelectItem value="por_obra">Por Obra</SelectItem><SelectItem value="temporal">Temporal</SelectItem><SelectItem value="pasantia">Pasantia</SelectItem></SelectContent></Select></div>
              <div className="space-y-2"><Label>Fecha Ingreso</Label><Input type="date" value={form.fecha_ingreso} onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Sueldo Mensual ($)</Label><Input type="number" value={form.sueldo_mensual} onChange={(e) => setForm({ ...form, sueldo_mensual: e.target.value })} /></div>
              <div className="space-y-2"><Label>Tipo Pago</Label><Select value={form.tipo_pago} onValueChange={(v) => setForm({ ...form, tipo_pago: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent><SelectItem value="mensual">Mensual</SelectItem><SelectItem value="quincenal">Quincenal</SelectItem><SelectItem value="semanal">Semanal</SelectItem></SelectContent></Select></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div className="space-y-2"><Label>Teléfono</Label><Input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} /></div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowDialog(false)}>Cancelar</Button>
              <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}{editingEmployee ? 'Guardar' : 'Crear'}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Roles de Pago Tab ───────────────────────────────────────

function RolesPagoTab({ companyId }: { companyId: string }) {
  const [payrolls, setPayrolls] = useState<RolPago[]>([]);
  const [loading, setLoading] = useState(true);
  const [showGenerate, setShowGenerate] = useState(false);
  const [genForm, setGenForm] = useState({ mes: String(new Date().getMonth() + 1), anio: String(new Date().getFullYear()) });
  const [genLoading, setGenLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getPayrolls({ company_id: companyId });
      setPayrolls(data);
    } catch {
      toast.error('Error al cargar roles de pago');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleGenerate() {
    setGenLoading(true);
    try {
      await generatePayroll({ company_id: companyId, periodo_mes: Number(genForm.mes), periodo_anio: Number(genForm.anio) });
      toast.success('Rol de pago generado');
      setShowGenerate(false);
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al generar rol');
    } finally {
      setGenLoading(false);
    }
  }

  async function handleAction(action: string, id: string) {
    setActionLoading(id);
    try {
      if (action === 'approve') { await approvePayroll(id); toast.success('Rol aprobado'); }
      if (action === 'pay') { await payPayroll(id); toast.success('Rol pagado'); }
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error en la operacion');
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowGenerate(true)}><Plus className="mr-2 h-4 w-4" /> Generar Rol</Button>
      </div>

      {payrolls.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Período</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Remuneraciones</TableHead>
                    <TableHead className="text-right">Descuentos</TableHead>
                    <TableHead className="text-right">Liquido</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payrolls.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{MESES[r.periodo_mes - 1]} {r.periodo_anio}</TableCell>
                      <TableCell>
                        <Badge variant={r.estado === 'pagado' ? 'default' : r.estado === 'aprobado' ? 'secondary' : 'outline'}
                          className={r.estado === 'pagado' ? 'bg-emerald-600' : r.estado === 'aprobado' ? 'bg-sky-600' : ''}>
                          {r.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">${formatCurrency(r.total_remuneraciones)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(r.total_descuentos)}</TableCell>
                      <TableCell className="text-right font-medium">${formatCurrency(r.total_liquido)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {r.estado === 'borrador' && (
                            <Button size="sm" variant="outline" onClick={() => handleAction('approve', r.id)} disabled={!!actionLoading}>
                              {actionLoading === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Aprobar'}
                            </Button>
                          )}
                          {r.estado === 'aprobado' && (
                            <Button size="sm" variant="outline" onClick={() => handleAction('pay', r.id)} disabled={!!actionLoading}>
                              {actionLoading === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Pagar'}
                            </Button>
                          )}
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
            <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin roles de pago</h3>
            <p className="text-muted-foreground text-sm mt-1">Genere un rol de pago para comenzar</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showGenerate} onOpenChange={setShowGenerate}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Generar Rol de Pago</DialogTitle>
            <DialogDescription>Seleccione el periodo para generar el rol</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Mes</Label><Select value={genForm.mes} onValueChange={(v) => setGenForm({ ...genForm, mes: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent>{MESES.map((m, i) => (<SelectItem key={i} value={String(i + 1)}>{m}</SelectItem>))}</SelectContent></Select></div>
              <div className="space-y-2"><Label>Año</Label><Input type="number" value={genForm.anio} onChange={(e) => setGenForm({ ...genForm, anio: e.target.value })} /></div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowGenerate(false)}>Cancelar</Button>
              <Button onClick={handleGenerate} disabled={genLoading}>{genLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Generar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Decimos Tab ─────────────────────────────────────────────

function DecimosTab({ companyId }: { companyId: string }) {
  const [decimoType, setDecimoType] = useState<'tercero' | 'cuarto'>('tercero');
  const [anio, setAnio] = useState(String(new Date().getFullYear()));
  const [region, setRegion] = useState('sierra');
  const [results, setResults] = useState<unknown[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleCalculate() {
    setLoading(true);
    try {
      if (decimoType === 'tercero') {
        const data = await calculateDecimoTercero({ company_id: companyId, periodo_anio: Number(anio) });
        setResults(Array.isArray(data) ? data : []);
      } else {
        const data = await calculateDecimoCuarto({ company_id: companyId, periodo_anio: Number(anio), region });
        setResults(Array.isArray(data) ? data : []);
      }
      toast.success('Cálculo realizado');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al calcular');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cálculo de Decimos</CardTitle>
          <CardDescription>Calcule el decimo tercero y cuarto para sus empleados</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3 items-center">
            <Select value={decimoType} onValueChange={(v) => setDecimoType(v as 'tercero' | 'cuarto')}>
              <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="tercero">Decimo Tercero</SelectItem>
                <SelectItem value="cuarto">Decimo Cuarto</SelectItem>
              </SelectContent>
            </Select>
            <div className="space-y-0"><Label className="sr-only">Año</Label><Input type="number" value={anio} onChange={(e) => setAnio(e.target.value)} className="w-24" /></div>
            {decimoType === 'cuarto' && (
              <Select value={region} onValueChange={setRegion}>
                <SelectTrigger className="w-[140px]"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="sierra">Sierra</SelectItem><SelectItem value="costa">Costa</SelectItem></SelectContent>
              </Select>
            )}
            <Button onClick={handleCalculate} disabled={loading}>{loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Calcular</Button>
          </div>

          {results && Array.isArray(results) && results.length > 0 && (
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Cédula</TableHead>
                        <TableHead>Nombre</TableHead>
                        <TableHead className="text-right">Sueldo</TableHead>
                        <TableHead className="text-right">Meses</TableHead>
                        <TableHead className="text-right">Valor</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.map((r, i) => {
                        const row = r as Record<string, unknown>;
                        return (
                          <TableRow key={i}>
                            <TableCell className="font-mono text-xs">{String(row.cedula || '')}</TableCell>
                            <TableCell>{String(row.nombre_completo || '')}</TableCell>
                            <TableCell className="text-right">${formatCurrency(Number(row.sueldo_mensual || 0))}</TableCell>
                            <TableCell className="text-right">{String(row.meses_trabajados || 0)}</TableCell>
                            <TableCell className="text-right font-medium">${formatCurrency(Number(row.valor_decimo || 0))}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── IESS Tab ────────────────────────────────────────────────

function IESSTab({ companyId }: { companyId: string }) {
  const [mes, setMes] = useState(String(new Date().getMonth() + 1));
  const [anio, setAnio] = useState(String(new Date().getFullYear()));
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLoadReport() {
    setLoading(true);
    try {
      const data = await getIESSReport({ company_id: companyId, periodo_mes: Number(mes), periodo_anio: Number(anio) });
      setReport(data as Record<string, unknown>);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al cargar reporte IESS');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reporte de Aportes IESS</CardTitle>
          <CardDescription>Aportes personales y patronales al IESS</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3 items-center">
            <Select value={mes} onValueChange={setMes}>
              <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
              <SelectContent>{MESES.map((m, i) => (<SelectItem key={i} value={String(i + 1)}>{m}</SelectItem>))}</SelectContent>
            </Select>
            <Input type="number" value={anio} onChange={(e) => setAnio(e.target.value)} className="w-24" />
            <Button onClick={handleLoadReport} disabled={loading}>{loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Consultar</Button>
          </div>

          {report && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <Card className="p-4"><div className="text-center"><div className="text-lg font-bold">{String(report.total_empleados ?? 0)}</div><p className="text-xs text-muted-foreground">Empleados</p></div></Card>
              <Card className="p-4"><div className="text-center"><div className="text-lg font-bold">${formatCurrency(Number(report.total_aporte_personal ?? 0))}</div><p className="text-xs text-muted-foreground">Aporte Personal 9.45%</p></div></Card>
              <Card className="p-4"><div className="text-center"><div className="text-lg font-bold">${formatCurrency(Number(report.total_aporte_patronal ?? 0))}</div><p className="text-xs text-muted-foreground">Aporte Patronal 11.15%</p></div></Card>
              <Card className="p-4"><div className="text-center"><div className="text-lg font-bold">${formatCurrency(Number(report.total_aporte_iee ?? 0))}</div><p className="text-xs text-muted-foreground">IEE Riesgos 0.5%</p></div></Card>
              <Card className="p-4"><div className="text-center"><div className="text-lg font-bold">${formatCurrency(Number(report.total_aporte_secap ?? 0))}</div><p className="text-xs text-muted-foreground">SECAP 0.2%</p></div></Card>
              <Card className="p-4"><div className="text-center"><div className="text-lg font-bold">${formatCurrency(Number(report.total_general ?? 0))}</div><p className="text-xs text-muted-foreground">Total General</p></div></Card>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Cargas Familiares Tab ───────────────────────────────────

function CargasFamiliaresTab({ companyId }: { companyId: string }) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState<string>('');
  const [cargas, setCargas] = useState<CargaFamiliar[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    nombres: '', apellidos: '', parentesco: 'hijo', fecha_nacimiento: '',
    genero: '', discapacidad: false, porcentaje_discapacidad: '', tipo_discapacidad: '',
  });

  const loadEmployees = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getEmployees({ company_id: companyId });
      setEmployees(data);
      if (data.length > 0 && !selectedEmployee) {
        setSelectedEmployee(data[0].id);
      }
    } catch {
      toast.error('Error al cargar empleados');
    } finally {
      setLoading(false);
    }
  }, [companyId, selectedEmployee]);

  const loadCargas = useCallback(async () => {
    if (!selectedEmployee) return;
    try {
      const data = await getCargasFamiliares(selectedEmployee);
      setCargas(data);
    } catch {
      setCargas([]);
    }
  }, [selectedEmployee]);

  useEffect(() => { loadEmployees(); }, [loadEmployees]);
  useEffect(() => { loadCargas(); }, [loadCargas]);

  async function handleAdd() {
    if (!form.nombres || !form.apellidos) { toast.error('Complete nombres y apellidos'); return; }
    setSaving(true);
    try {
      await createCargaFamiliar({
        employee_id: selectedEmployee,
        nombres: form.nombres,
        apellidos: form.apellidos,
        parentesco: form.parentesco,
        fecha_nacimiento: form.fecha_nacimiento || undefined,
        discapacidad: form.discapacidad,
        porcentaje_discapacidad: form.discapacidad && form.porcentaje_discapacidad ? Number(form.porcentaje_discapacidad) : undefined,
        tipo_discapacidad: form.discapacidad && form.tipo_discapacidad ? form.tipo_discapacidad : undefined,
      });
      toast.success('Carga familiar agregada');
      setShowAdd(false);
      setForm({ nombres: '', apellidos: '', parentesco: 'hijo', fecha_nacimiento: '', genero: '', discapacidad: false, porcentaje_discapacidad: '', tipo_discapacidad: '' });
      loadCargas();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al agregar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('¿Eliminar esta carga familiar?')) return;
    try {
      await deleteCargaFamiliar(id);
      toast.success('Carga familiar eliminada');
      loadCargas();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    }
  }

  const PARENTESCOS = [
    { key: 'hijo', label: 'Hijo/a' },
    { key: 'conyuge', label: 'Cónyuge' },
    { key: 'padre', label: 'Padre' },
    { key: 'madre', label: 'Madre' },
    { key: 'hermano', label: 'Hermano/a' },
    { key: 'otro', label: 'Otro' },
  ];

  const TIPOS_DISCAPACIDAD = [
    { key: 'fisica', label: 'Física' },
    { key: 'auditiva', label: 'Auditiva' },
    { key: 'visual', label: 'Visual' },
    { key: 'intelectual', label: 'Intelectual' },
    { key: 'mental', label: 'Mental / Psicosocial' },
    { key: 'paraplejica', label: 'Paraplejía' },
    { key: 'motora', label: 'Motora' },
    { key: 'lenguaje', label: 'Lenguaje' },
    { key: 'multiple', label: 'Múltiple' },
    { key: 'otra', label: 'Otra' },
  ];

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
          <SelectTrigger className="w-[260px]"><SelectValue placeholder="Seleccione empleado" /></SelectTrigger>
          <SelectContent>
            {employees.map((e) => (<SelectItem key={e.id} value={e.id}>{e.apellidos} {e.nombres}</SelectItem>))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadCargas}><RefreshCw className="h-4 w-4" /></Button>
        <div className="flex-1" />
        <Button onClick={() => setShowAdd(true)} disabled={!selectedEmployee}><Plus className="mr-2 h-4 w-4" /> Agregar Carga</Button>
      </div>

      {cargas.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Parentesco</TableHead>
                    <TableHead>Fecha Nacimiento</TableHead>
                    <TableHead>Tipo Discapacidad</TableHead>
                    <TableHead>Discapacidad</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cargas.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium">{c.apellidos} {c.nombres}</TableCell>
                      <TableCell><Badge variant="outline">{PARENTESCOS.find((p) => p.key === c.parentesco)?.label || c.parentesco}</Badge></TableCell>
                      <TableCell className="text-sm">{c.fecha_nacimiento ? String(c.fecha_nacimiento).slice(0, 10) : '-'}</TableCell>
                      <TableCell className="text-sm">{c.tipo_discapacidad ? TIPOS_DISCAPACIDAD.find((t) => t.key === c.tipo_discapacidad)?.label || c.tipo_discapacidad : '-'}</TableCell>
                      <TableCell>{c.discapacidad ? <Badge className="bg-amber-500 text-white text-xs">{c.porcentaje_discapacidad ? `${c.porcentaje_discapacidad}%` : 'Sí'}</Badge> : <Badge variant="secondary" className="text-xs">No</Badge>}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(c.id)}>
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
            <Baby className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin cargas familiares</h3>
            <p className="text-muted-foreground text-sm mt-1">Agregue cargas familiares para el empleado</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Agregar Carga Familiar</DialogTitle>
            <DialogDescription>Registre una carga familiar para el empleado</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Nombres *</Label><Input value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} placeholder="Nombres" /></div>
              <div className="space-y-2"><Label>Apellidos *</Label><Input value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} placeholder="Apellidos" /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Parentesco</Label><Select value={form.parentesco} onValueChange={(v) => setForm({ ...form, parentesco: v })}><SelectTrigger><SelectValue placeholder="Seleccione parentesco" /></SelectTrigger><SelectContent>{PARENTESCOS.map((p) => (<SelectItem key={p.key} value={p.key}>{p.label}</SelectItem>))}</SelectContent></Select></div>
              <div className="space-y-2"><Label>Género</Label><Select value={form.genero} onValueChange={(v) => setForm({ ...form, genero: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent><SelectItem value="M">Masculino</SelectItem><SelectItem value="F">Femenino</SelectItem></SelectContent></Select></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Fecha Nacimiento</Label><Input type="date" value={form.fecha_nacimiento} onChange={(e) => setForm({ ...form, fecha_nacimiento: e.target.value })} /></div>
              <div className="space-y-2 flex items-end"><label className="flex items-center gap-2"><input type="checkbox" checked={form.discapacidad} onChange={(e) => setForm({ ...form, discapacidad: e.target.checked })} className="rounded" /><Label>Discapacidad</Label></label></div>
            </div>
            {form.discapacidad && (
              <div className="grid grid-cols-2 gap-4 rounded-md border p-3 bg-muted/30">
                <div className="space-y-2"><Label>% de Discapacidad</Label><Input type="number" min="0" max="100" value={form.porcentaje_discapacidad} onChange={(e) => setForm({ ...form, porcentaje_discapacidad: e.target.value })} placeholder="0-100" /></div>
                <div className="space-y-2"><Label>Tipo de Discapacidad</Label><Select value={form.tipo_discapacidad} onValueChange={(v) => setForm({ ...form, tipo_discapacidad: v })}><SelectTrigger><SelectValue placeholder="Seleccione tipo" /></SelectTrigger><SelectContent>{TIPOS_DISCAPACIDAD.map((t) => (<SelectItem key={t.key} value={t.key}>{t.label}</SelectItem>))}</SelectContent></Select></div>
              </div>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowAdd(false)}>Cancelar</Button>
              <Button onClick={handleAdd} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Agregar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Asistencia Tab ──────────────────────────────────────────

function AsistenciaTab({ companyId }: { companyId: string }) {
  const [records, setRecords] = useState<AsistenciaRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ employee_id: '', fecha: new Date().toISOString().slice(0, 10), hora_entrada: '08:00', hora_salida: '17:00', tipo: 'normal', observacion: '' });
  const [employees, setEmployees] = useState<Employee[]>([]);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [asistData, empData] = await Promise.all([
        getAsistencia(companyId),
        getEmployees({ company_id: companyId }),
      ]);
      setRecords(asistData);
      setEmployees(empData);
    } catch {
      toast.error('Error al cargar asistencia');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCreate() {
    if (!form.employee_id || !form.fecha) { toast.error('Complete los campos requeridos'); return; }
    setSaving(true);
    try {
      await createAsistencia({
        company_id: companyId,
        employee_id: form.employee_id,
        fecha: form.fecha,
        hora_entrada: form.hora_entrada || undefined,
        hora_salida: form.hora_salida || undefined,
        tipo: form.tipo,
        observacion: form.observacion || undefined,
      });
      toast.success('Registro de asistencia creado');
      setShowCreate(false);
      setForm({ employee_id: '', fecha: new Date().toISOString().slice(0, 10), hora_entrada: '08:00', hora_salida: '17:00', tipo: 'normal', observacion: '' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear registro');
    } finally {
      setSaving(false);
    }
  }

  const TIPOS_ASISTENCIA = [
    { key: 'normal', label: 'Normal' },
    { key: 'atraso', label: 'Atraso' },
    { key: 'falta', label: 'Falta' },
    { key: 'permiso', label: 'Permiso' },
    { key: 'vacacion', label: 'Vacación' },
    { key: 'feriado', label: 'Feriado' },
  ];

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Registrar Asistencia</Button>
      </div>

      {records.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Empleado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Entrada</TableHead>
                    <TableHead>Salida</TableHead>
                    <TableHead className="text-right">Horas</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Observación</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {records.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium">{r.employee_name || r.employee_id}</TableCell>
                      <TableCell className="text-sm">{r.fecha}</TableCell>
                      <TableCell className="text-sm">{r.hora_entrada || '-'}</TableCell>
                      <TableCell className="text-sm">{r.hora_salida || '-'}</TableCell>
                      <TableCell className="text-right">{r.horas_trabajadas.toFixed(1)}h</TableCell>
                      <TableCell><Badge variant="outline" className="text-xs">{TIPOS_ASISTENCIA.find((t) => t.key === r.tipo)?.label || r.tipo}</Badge></TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">{r.observacion || '-'}</TableCell>
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
            <h3 className="text-lg font-medium">Sin registros de asistencia</h3>
            <p className="text-muted-foreground text-sm mt-1">Registre la asistencia de sus empleados</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Registrar Asistencia</DialogTitle>
            <DialogDescription>Registre la asistencia de un empleado</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Empleado *</Label><Select value={form.employee_id} onValueChange={(v) => setForm({ ...form, employee_id: v })}><SelectTrigger><SelectValue placeholder="Seleccionar empleado" /></SelectTrigger><SelectContent>{employees.map((e) => (<SelectItem key={e.id} value={e.id}>{e.apellidos} {e.nombres}</SelectItem>))}</SelectContent></Select></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Fecha *</Label><Input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></div>
              <div className="space-y-2"><Label>Tipo</Label><Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}><SelectTrigger><SelectValue placeholder="Seleccione tipo" /></SelectTrigger><SelectContent>{TIPOS_ASISTENCIA.map((t) => (<SelectItem key={t.key} value={t.key}>{t.label}</SelectItem>))}</SelectContent></Select></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Hora Entrada</Label><Input type="time" value={form.hora_entrada} onChange={(e) => setForm({ ...form, hora_entrada: e.target.value })} /></div>
              <div className="space-y-2"><Label>Hora Salida</Label><Input type="time" value={form.hora_salida} onChange={(e) => setForm({ ...form, hora_salida: e.target.value })} /></div>
            </div>
            <div className="space-y-2"><Label>Observación</Label><Input value={form.observacion} onChange={(e) => setForm({ ...form, observacion: e.target.value })} placeholder="Observación (opcional)" /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Registrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Liquidaciones Tab ───────────────────────────────────────

function LiquidacionesTab({ companyId }: { companyId: string }) {
  const [liquidaciones, setLiquidaciones] = useState<Liquidacion[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCalculate, setShowCalculate] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [approving, setApproving] = useState<string | null>(null);
  const [form, setForm] = useState({ employee_ids: [] as string[], fecha_salida: '', motivo: 'renuncia_voluntaria' });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [liqData, empData] = await Promise.all([
        getLiquidaciones(companyId),
        getEmployees({ company_id: companyId }),
      ]);
      setLiquidaciones(liqData);
      setEmployees(empData);
    } catch {
      toast.error('Error al cargar liquidaciones');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCalculate() {
    if (form.employee_ids.length === 0 || !form.fecha_salida) { toast.error('Seleccione al menos un empleado y la fecha de salida'); return; }
    setCalculating(true);
    try {
      let successCount = 0;
      let errorCount = 0;
      for (const empId of form.employee_ids) {
        try {
          await calcularLiquidacion({
            company_id: companyId,
            employee_id: empId,
            tipo: form.motivo,
            fecha_fin: form.fecha_salida,
          });
          successCount++;
        } catch {
          errorCount++;
        }
      }
      if (successCount > 0) toast.success(`${successCount} liquidacion(es) calculadas`);
      if (errorCount > 0) toast.error(`${errorCount} liquidacion(es) con error`);
      setShowCalculate(false);
      setForm({ employee_ids: [], fecha_salida: '', motivo: 'renuncia_voluntaria' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al calcular liquidación');
    } finally {
      setCalculating(false);
    }
  }

  async function handleApprove(id: string) {
    setApproving(id);
    try {
      await aprobarLiquidacion(id);
      toast.success('Liquidación aprobada');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al aprobar');
    } finally {
      setApproving(null);
    }
  }

  const MOTIVOS = [
    { key: 'renuncia_voluntaria', label: 'Renuncia voluntaria' },
    { key: 'despido', label: 'Despido' },
    { key: 'finiquito', label: 'Finiquito' },
    { key: 'liquidacion', label: 'Liquidación' },
  ];

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCalculate(true)}><Calculator className="mr-2 h-4 w-4" /> Calcular Liquidación</Button>
      </div>

      {liquidaciones.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Empleado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Motivo</TableHead>
                    <TableHead className="text-right">Ingresos</TableHead>
                    <TableHead className="text-right">Descuentos</TableHead>
                    <TableHead className="text-right">Líquido</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {liquidaciones.map((l) => (
                    <TableRow key={l.id}>
                      <TableCell className="font-medium">{l.employee_name || l.employee_id}</TableCell>
                      <TableCell className="text-sm">{l.fecha}</TableCell>
                      <TableCell><Badge variant="outline" className="text-xs">{MOTIVOS.find((m) => m.key === l.motivo)?.label || l.motivo}</Badge></TableCell>
                      <TableCell className="text-right text-emerald-600">${formatCurrency(l.total_ingresos)}</TableCell>
                      <TableCell className="text-right text-red-600">${formatCurrency(l.total_descuentos)}</TableCell>
                      <TableCell className="text-right font-medium">${formatCurrency(l.liquido_recibir)}</TableCell>
                      <TableCell>
                        <Badge variant={l.estado === 'pagada' ? 'default' : l.estado === 'aprobada' ? 'secondary' : 'outline'}
                          className={l.estado === 'pagada' ? 'bg-emerald-600' : l.estado === 'aprobada' ? 'bg-sky-600' : ''}>
                          {l.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {l.estado === 'borrador' && (
                          <Button size="sm" variant="outline" onClick={() => handleApprove(l.id)} disabled={!!approving}>
                            {approving === l.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
                            Aprobar
                          </Button>
                        )}
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
            <Calculator className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin liquidaciones</h3>
            <p className="text-muted-foreground text-sm mt-1">Calcule una liquidación para comenzar</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCalculate} onOpenChange={setShowCalculate}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Calcular Liquidación</DialogTitle>
            <DialogDescription>Calcule la liquidación de uno o más empleados</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Empleados *</Label>
              <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-1">
                {employees.map((e) => (
                  <label key={e.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.employee_ids.includes(e.id)}
                      onChange={(ev) => {
                        if (ev.target.checked) {
                          setForm({ ...form, employee_ids: [...form.employee_ids, e.id] });
                        } else {
                          setForm({ ...form, employee_ids: form.employee_ids.filter((id) => id !== e.id) });
                        }
                      }}
                      className="rounded"
                    />
                    <span className="text-sm">{e.apellidos} {e.nombres}</span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{form.employee_ids.length} seleccionado(s)</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Fecha Salida *</Label><Input type="date" value={form.fecha_salida} onChange={(e) => setForm({ ...form, fecha_salida: e.target.value })} /></div>
              <div className="space-y-2"><Label>Motivo</Label><Select value={form.motivo} onValueChange={(v) => setForm({ ...form, motivo: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent>{MOTIVOS.map((m) => (<SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>))}</SelectContent></Select></div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCalculate(false)}>Cancelar</Button>
              <Button onClick={handleCalculate} disabled={calculating}>{calculating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Calcular</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Utilidades Tab ──────────────────────────────────────────

function UtilidadesTab({ companyId }: { companyId: string }) {
  const [utilidades, setUtilidades] = useState<UtilidadRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [anio, setAnio] = useState(String(new Date().getFullYear()));
  const [totalUtilidades, setTotalUtilidades] = useState('');

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getUtilidades(companyId);
      setUtilidades(data);
    } catch {
      toast.error('Error al cargar utilidades');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCalculate() {
    if (!totalUtilidades || Number(totalUtilidades) <= 0) {
      toast.error('Ingrese el total de utilidades de la empresa');
      return;
    }
    setCalculating(true);
    try {
      const data = await calcularUtilidades({
        company_id: companyId,
        anio: Number(anio),
        total_utilidades: Number(totalUtilidades),
      });
      setUtilidades(data);
      toast.success('Utilidades calculadas');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al calcular utilidades');
    } finally {
      setCalculating(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Utilidades (Participación de Trabajadores)</CardTitle>
          <CardDescription>Cálculo del 15% de utilidades para empleados (12% trabajadores + 3% INSEC)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3 items-center">
            <Input type="number" value={anio} onChange={(e) => setAnio(e.target.value)} className="w-28" placeholder="Año" />
            <Input type="number" min="0" step="0.01" value={totalUtilidades} onChange={(e) => setTotalUtilidades(e.target.value)} className="w-44" placeholder="Total utilidades ($)" />
            <Button onClick={handleCalculate} disabled={calculating}>
              {calculating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Calcular Utilidades
            </Button>
            <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
          </div>
        </CardContent>
      </Card>

      {utilidades.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Empleado</TableHead>
                    <TableHead>Período</TableHead>
                    <TableHead className="text-right">Utilidad Total</TableHead>
                    <TableHead className="text-right">Días Trabajados</TableHead>
                    <TableHead className="text-right">Valor Recibido</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {utilidades.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell className="font-medium">{u.employee_name || u.employee_id}</TableCell>
                      <TableCell className="text-sm">{u.periodo_anio}</TableCell>
                      <TableCell className="text-right">${formatCurrency(u.utilidad_total)}</TableCell>
                      <TableCell className="text-right">{u.dias_trabajados}</TableCell>
                      <TableCell className="text-right font-medium text-emerald-600">${formatCurrency(u.valor_recibido)}</TableCell>
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
            <TrendingUp className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin registros de utilidades</h3>
            <p className="text-muted-foreground text-sm mt-1">Calcule las utilidades anuales para sus empleados</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
