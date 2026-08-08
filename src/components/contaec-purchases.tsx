'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
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
import { Textarea } from '@/components/ui/textarea';
import {
  ShoppingCart,
  Loader2,
  RefreshCw,
  Plus,
  DollarSign,
  FileText,
  CreditCard,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getOrdenesCompra,
  createOrdenCompra,
  getCuentasPorPagar,
  createCuentaPorPagar,
  registerPaymentCuentaPorPagar,
  getRetencionesCompra,
  createRetencionCompra,
  getSuppliers,
  type OrdenCompra,
  type CuentaPorPagar,
  type RetencionCompra,
  type Supplier,
  type User,
  type Company,
} from '@/lib/api';

function formatCurrency(amount: number): string {
  return amount.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface ContaECPurchasesProps {
  user: User;
  companies: Company[];
}

export function ContaECPurchases({ user: _user, companies }: ContaECPurchasesProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div><h2 className="text-2xl font-bold">Compras</h2><p className="text-muted-foreground">Ordenes de compra, cuentas por pagar y retenciones</p></div>
        <Card><CardContent className="py-12 text-center"><ShoppingCart className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin empresas</h3></CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Compras</h2>
          <p className="text-muted-foreground">Ordenes de compra, cuentas por pagar y retenciones</p>
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

      <Tabs defaultValue="ordenes" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="ordenes" className="gap-1.5"><ShoppingCart className="h-3.5 w-3.5" /><span className="hidden sm:inline">Ordenes de Compra</span></TabsTrigger>
          <TabsTrigger value="cuentas" className="gap-1.5"><CreditCard className="h-3.5 w-3.5" /><span className="hidden sm:inline">Cuentas por Pagar</span></TabsTrigger>
          <TabsTrigger value="retenciones" className="gap-1.5"><FileText className="h-3.5 w-3.5" /><span className="hidden sm:inline">Retenciones</span></TabsTrigger>
        </TabsList>
        <TabsContent value="ordenes"><OrdenesTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="cuentas"><CuentasTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="retenciones"><RetencionesTab companyId={selectedCompanyId} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Ordenes de Compra Tab ───────────────────────────────────

function OrdenesTab({ companyId }: { companyId: string }) {
  const [ordenes, setOrdenes] = useState<OrdenCompra[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ supplier_id: '', fecha_entrega_estimada: '', observaciones: '' });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [ords, sups] = await Promise.all([
        getOrdenesCompra({ company_id: companyId }),
        getSuppliers(companyId),
      ]);
      setOrdenes(ords);
      setSuppliers(sups);
    } catch {
      toast.error('Error al cargar ordenes');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCreate() {
    if (!form.supplier_id) { toast.error('Seleccione un proveedor'); return; }
    setCreating(true);
    try {
      await createOrdenCompra({
        company_id: companyId,
        supplier_id: form.supplier_id,
        fecha_entrega_estimada: form.fecha_entrega_estimada || undefined,
        observaciones: form.observaciones || undefined,
        detalles: [{ codigo_principal: 'PEND', descripcion: 'Producto pendiente de detalle', cantidad: 1, precio_unitario: 0.01, iva_codigo: '10', iva_porcentaje: 13 }],
      });
      toast.success('Orden de compra creada');
      setShowCreate(false);
      setForm({ supplier_id: '', fecha_entrega_estimada: '', observaciones: '' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear orden');
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nueva Orden</Button>
      </div>

      {ordenes.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Numero</TableHead>
                    <TableHead>Fecha Emision</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Subtotal</TableHead>
                    <TableHead className="text-right">IVA</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ordenes.map((oc) => (
                    <TableRow key={oc.id}>
                      <TableCell className="font-mono text-xs">{oc.numero}</TableCell>
                      <TableCell className="text-xs">{new Date(oc.fecha_emision).toLocaleDateString('es-EC')}</TableCell>
                      <TableCell>
                        <Badge variant={oc.estado === 'recibida' ? 'default' : oc.estado === 'enviada' ? 'secondary' : 'outline'}
                          className={oc.estado === 'recibida' ? 'bg-emerald-600' : ''}>
                          {oc.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">${formatCurrency(oc.subtotal_sin_impuestos)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(oc.total_iva)}</TableCell>
                      <TableCell className="text-right font-medium">${formatCurrency(oc.total_con_impuestos)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card><CardContent className="py-12 text-center"><ShoppingCart className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin ordenes de compra</h3></CardContent></Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Nueva Orden de Compra</DialogTitle><DialogDescription>Cree una nueva orden de compra</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Proveedor</Label><Select value={form.supplier_id} onValueChange={(v) => setForm({ ...form, supplier_id: v })}><SelectTrigger><SelectValue placeholder="Seleccione proveedor" /></SelectTrigger><SelectContent>{suppliers.map((s) => (<SelectItem key={s.id} value={s.id}>{s.razon_social}</SelectItem>))}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Fecha Entrega Estimada</Label><Input type="date" value={form.fecha_entrega_estimada} onChange={(e) => setForm({ ...form, fecha_entrega_estimada: e.target.value })} /></div>
            <div className="space-y-2"><Label>Observaciones</Label><Textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleCreate} disabled={creating}>{creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear Orden</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Cuentas por Pagar Tab ───────────────────────────────────

function CuentasTab({ companyId }: { companyId: string }) {
  const [cuentas, setCuentas] = useState<CuentaPorPagar[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPayment, setShowPayment] = useState<string | null>(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paying, setPaying] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [createForm, setCreateForm] = useState({ supplier_id: '', numero_factura: '', fecha_emision: '', monto_total: '', dias_credito: '0', observaciones: '' });
  const [creating, setCreating] = useState(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [cts, sups] = await Promise.all([getCuentasPorPagar({ company_id: companyId }), getSuppliers(companyId)]);
      setCuentas(cts);
      setSuppliers(sups);
    } catch {
      toast.error('Error al cargar cuentas por pagar');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handlePayment() {
    if (!showPayment || !paymentAmount) return;
    setPaying(true);
    try {
      await registerPaymentCuentaPorPagar(showPayment, { monto: Number(paymentAmount) });
      toast.success('Pago registrado');
      setShowPayment(null);
      setPaymentAmount('');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al registrar pago');
    } finally {
      setPaying(false);
    }
  }

  async function handleCreate() {
    if (!createForm.supplier_id || !createForm.monto_total) { toast.error('Complete los campos requeridos'); return; }
    setCreating(true);
    try {
      await createCuentaPorPagar({
        company_id: companyId, supplier_id: createForm.supplier_id,
        numero_factura: createForm.numero_factura || undefined,
        fecha_emision: createForm.fecha_emision || new Date().toISOString().slice(0, 10),
        monto_total: Number(createForm.monto_total), dias_credito: Number(createForm.dias_credito) || 0,
        observaciones: createForm.observaciones || undefined,
      });
      toast.success('Cuenta por pagar creada');
      setShowCreate(false);
      setCreateForm({ supplier_id: '', numero_factura: '', fecha_emision: '', monto_total: '', dias_credito: '0', observaciones: '' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear cuenta');
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nueva Cuenta</Button>
      </div>

      {cuentas.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Factura</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Pagado</TableHead>
                    <TableHead className="text-right">Pendiente</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cuentas.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-mono text-xs">{c.numero_factura || '-'}</TableCell>
                      <TableCell className="text-xs">{new Date(c.fecha_emision).toLocaleDateString('es-EC')}</TableCell>
                      <TableCell>
                        <Badge variant={c.estado === 'pagada' ? 'default' : c.estado === 'vencida' ? 'destructive' : 'secondary'}
                          className={c.estado === 'pagada' ? 'bg-emerald-600' : ''}>
                          {c.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">${formatCurrency(c.monto_total)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(c.monto_pagado)}</TableCell>
                      <TableCell className="text-right font-medium">${formatCurrency(c.monto_pendiente)}</TableCell>
                      <TableCell className="text-right">
                        {c.estado !== 'pagada' && (
                          <Button size="sm" variant="outline" onClick={() => { setShowPayment(c.id); setPaymentAmount(''); }}>
                            <DollarSign className="mr-1 h-3 w-3" /> Pagar
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
        <Card><CardContent className="py-12 text-center"><CreditCard className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin cuentas por pagar</h3></CardContent></Card>
      )}

      {/* Payment Dialog */}
      <Dialog open={!!showPayment} onOpenChange={(o) => !o && setShowPayment(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader><DialogTitle>Registrar Pago</DialogTitle><DialogDescription>Ingrese el monto del pago</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Monto ($)</Label><Input type="number" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowPayment(null)}>Cancelar</Button>
              <Button onClick={handlePayment} disabled={paying}>{paying ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Registrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Cuenta Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Nueva Cuenta por Pagar</DialogTitle><DialogDescription>Registre una nueva cuenta por pagar</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Proveedor</Label><Select value={createForm.supplier_id} onValueChange={(v) => setCreateForm({ ...createForm, supplier_id: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent>{suppliers.map((s) => (<SelectItem key={s.id} value={s.id}>{s.razon_social}</SelectItem>))}</SelectContent></Select></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Numero Factura</Label><Input value={createForm.numero_factura} onChange={(e) => setCreateForm({ ...createForm, numero_factura: e.target.value })} /></div>
              <div className="space-y-2"><Label>Fecha Emision</Label><Input type="date" value={createForm.fecha_emision} onChange={(e) => setCreateForm({ ...createForm, fecha_emision: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Monto Total ($)</Label><Input type="number" value={createForm.monto_total} onChange={(e) => setCreateForm({ ...createForm, monto_total: e.target.value })} /></div>
              <div className="space-y-2"><Label>Dias Credito</Label><Input type="number" value={createForm.dias_credito} onChange={(e) => setCreateForm({ ...createForm, dias_credito: e.target.value })} /></div>
            </div>
            <div className="space-y-2"><Label>Observaciones</Label><Textarea value={createForm.observaciones} onChange={(e) => setCreateForm({ ...createForm, observaciones: e.target.value })} rows={2} /></div>
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

// ─── Retenciones Tab ─────────────────────────────────────────

function RetencionesTab({ companyId }: { companyId: string }) {
  const [retenciones, setRetenciones] = useState<RetencionCompra[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    supplier_id: '', fecha_emision: new Date().toISOString().slice(0, 10),
    base_imponible_iva: '', retencion_iva_codigo: '1', retencion_iva_porcentaje: '30',
    base_imponible_renta: '', retencion_renta_codigo: '312', retencion_renta_porcentaje: '2',
    observaciones: '',
  });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [rets, sups] = await Promise.all([getRetencionesCompra({ company_id: companyId }), getSuppliers(companyId)]);
      setRetenciones(rets);
      setSuppliers(sups);
    } catch {
      toast.error('Error al cargar retenciones');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCreate() {
    if (!form.supplier_id) { toast.error('Seleccione un proveedor'); return; }
    setCreating(true);
    try {
      await createRetencionCompra({
        company_id: companyId, supplier_id: form.supplier_id,
        fecha_emision: form.fecha_emision,
        base_imponible_iva: Number(form.base_imponible_iva) || 0,
        retencion_iva_codigo: form.retencion_iva_codigo,
        retencion_iva_porcentaje: Number(form.retencion_iva_porcentaje) || 0,
        base_imponible_renta: Number(form.base_imponible_renta) || 0,
        retencion_renta_codigo: form.retencion_renta_codigo,
        retencion_renta_porcentaje: Number(form.retencion_renta_porcentaje) || 0,
        observaciones: form.observaciones || undefined,
      });
      toast.success('Retencion creada');
      setShowCreate(false);
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear retencion');
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> Nueva Retencion</Button>
      </div>

      {retenciones.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Numero</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Base IVA</TableHead>
                    <TableHead className="text-right">Ret. IVA</TableHead>
                    <TableHead className="text-right">Base Renta</TableHead>
                    <TableHead className="text-right">Ret. Renta</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {retenciones.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-mono text-xs">{r.numero_retencion || '-'}</TableCell>
                      <TableCell className="text-xs">{new Date(r.fecha_emision).toLocaleDateString('es-EC')}</TableCell>
                      <TableCell><Badge variant={r.estado === 'autorizado' ? 'default' : 'secondary'} className={r.estado === 'autorizado' ? 'bg-emerald-600' : ''}>{r.estado}</Badge></TableCell>
                      <TableCell className="text-right">${formatCurrency(r.base_imponible_iva)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(r.retencion_iva_valor)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(r.base_imponible_renta)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(r.retencion_renta_valor)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card><CardContent className="py-12 text-center"><FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin retenciones</h3></CardContent></Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Nueva Retencion de Compra</DialogTitle><DialogDescription>Cree una retencion en fuente para una compra</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Proveedor</Label><Select value={form.supplier_id} onValueChange={(v) => setForm({ ...form, supplier_id: v })}><SelectTrigger><SelectValue placeholder="Seleccione" /></SelectTrigger><SelectContent>{suppliers.map((s) => (<SelectItem key={s.id} value={s.id}>{s.razon_social}</SelectItem>))}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Fecha Emision</Label><Input type="date" value={form.fecha_emision} onChange={(e) => setForm({ ...form, fecha_emision: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Base Imponible IVA ($)</Label><Input type="number" value={form.base_imponible_iva} onChange={(e) => setForm({ ...form, base_imponible_iva: e.target.value })} /></div>
              <div className="space-y-2"><Label>% Retencion IVA</Label><Input type="number" value={form.retencion_iva_porcentaje} onChange={(e) => setForm({ ...form, retencion_iva_porcentaje: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Base Imponible Renta ($)</Label><Input type="number" value={form.base_imponible_renta} onChange={(e) => setForm({ ...form, base_imponible_renta: e.target.value })} /></div>
              <div className="space-y-2"><Label>% Retencion Renta</Label><Input type="number" value={form.retencion_renta_porcentaje} onChange={(e) => setForm({ ...form, retencion_renta_porcentaje: e.target.value })} /></div>
            </div>
            <div className="space-y-2"><Label>Observaciones</Label><Textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} /></div>
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
