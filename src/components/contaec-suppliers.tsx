'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
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
  Truck,
  Loader2,
  RefreshCw,
  Plus,
  Pencil,
  Trash2,
  Mail,
  PlusCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getSuppliers,
  createSupplier,
  updateSupplier,
  deleteSupplier,
  getEmailTemplates,
  createEmailTemplate,
  type Supplier,
  type EmailTemplate,
  type User,
  type Company,
} from '@/lib/api';

interface ContaECSuppliersProps {
  user: User;
  companies: Company[];
}

export function ContaECSuppliers({ user: _user, companies }: ContaECSuppliersProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [saving, setSaving] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [emailTemplates, setEmailTemplates] = useState<EmailTemplate[]>([]);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templateForm, setTemplateForm] = useState({ nombre: '', tipo: 'general', asunto: '', cuerpo_html: '' });
  const [templateLoading, setTemplateLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const [form, setForm] = useState({
    tipo_identificacion: '04', identificacion: '', razon_social: '',
    nombre_comercial: '', direccion: '', email: '', telefono: '',
    contacto_nombre: '', contacto_telefono: '', forma_pago_habitual: '01',
    plazo_credito_dias: '0', retencion_iva_codigo: '', retencion_iva_porcentaje: '',
    retencion_renta_codigo: '', retencion_renta_porcentaje: '', observaciones: '',
  });

  const loadData = useCallback(async () => {
    if (!selectedCompanyId) return;
    setLoading(true);
    try {
      const data = await getSuppliers(selectedCompanyId);
      setSuppliers(data);
    } catch {
      toast.error('Error al cargar proveedores');
    } finally {
      setLoading(false);
    }
  }, [selectedCompanyId]);

  useEffect(() => { loadData(); }, [loadData]);

  function openCreate() {
    setEditingSupplier(null);
    setForm({ tipo_identificacion: '04', identificacion: '', razon_social: '', nombre_comercial: '', direccion: '', email: '', telefono: '', contacto_nombre: '', contacto_telefono: '', forma_pago_habitual: '01', plazo_credito_dias: '0', retencion_iva_codigo: '', retencion_iva_porcentaje: '', retencion_renta_codigo: '', retencion_renta_porcentaje: '', observaciones: '' });
    setShowDialog(true);
  }

  function openEdit(sup: Supplier) {
    setEditingSupplier(sup);
    setForm({
      tipo_identificacion: sup.tipo_identificacion, identificacion: sup.identificacion,
      razon_social: sup.razon_social, nombre_comercial: sup.nombre_comercial || '',
      direccion: sup.direccion || '', email: sup.email || '', telefono: sup.telefono || '',
      contacto_nombre: sup.contacto_nombre || '', contacto_telefono: sup.contacto_telefono || '',
      forma_pago_habitual: sup.forma_pago_habitual, plazo_credito_dias: String(sup.plazo_credito_dias),
      retencion_iva_codigo: sup.retencion_iva_codigo || '', retencion_iva_porcentaje: sup.retencion_iva_porcentaje ? String(sup.retencion_iva_porcentaje) : '',
      retencion_renta_codigo: sup.retencion_renta_codigo || '', retencion_renta_porcentaje: sup.retencion_renta_porcentaje ? String(sup.retencion_renta_porcentaje) : '',
      observaciones: sup.observaciones || '',
    });
    setShowDialog(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const data = {
        tipo_identificacion: form.tipo_identificacion, identificacion: form.identificacion,
        razon_social: form.razon_social, nombre_comercial: form.nombre_comercial || undefined,
        direccion: form.direccion || undefined, email: form.email || undefined,
        telefono: form.telefono || undefined, contacto_nombre: form.contacto_nombre || undefined,
        contacto_telefono: form.contacto_telefono || undefined,
        forma_pago_habitual: form.forma_pago_habitual,
        plazo_credito_dias: Number(form.plazo_credito_dias) || 0,
        retencion_iva_codigo: form.retencion_iva_codigo || undefined,
        retencion_iva_porcentaje: form.retencion_iva_porcentaje ? Number(form.retencion_iva_porcentaje) : undefined,
        retencion_renta_codigo: form.retencion_renta_codigo || undefined,
        retencion_renta_porcentaje: form.retencion_renta_porcentaje ? Number(form.retencion_renta_porcentaje) : undefined,
        observaciones: form.observaciones || undefined,
      };
      if (editingSupplier) {
        await updateSupplier(editingSupplier.id, data);
        toast.success('Proveedor actualizado');
      } else {
        await createSupplier({ ...data, company_id: selectedCompanyId });
        toast.success('Proveedor creado');
      }
      setShowDialog(false);
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteSupplier(id);
      toast.success('Proveedor eliminado');
      setDeleteConfirm(null);
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar');
    }
  }

  async function loadEmailTemplates() {
    try {
      const data = await getEmailTemplates();
      setEmailTemplates(data);
    } catch {
      toast.error('Error al cargar plantillas');
    }
    setShowTemplates(true);
  }

  async function handleCreateTemplate() {
    setTemplateLoading(true);
    try {
      await createEmailTemplate(templateForm);
      toast.success('Plantilla creada');
      setShowTemplateDialog(false);
      setTemplateForm({ nombre: '', tipo: 'general', asunto: '', cuerpo_html: '' });
      const data = await getEmailTemplates();
      setEmailTemplates(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear plantilla');
    } finally {
      setTemplateLoading(false);
    }
  }

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div><h2 className="text-2xl font-bold">Proveedores</h2><p className="text-muted-foreground">Gestion de proveedores y plantillas de correo</p></div>
        <Card><CardContent className="py-12 text-center"><Truck className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin empresas</h3></CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Proveedores</h2>
          <p className="text-muted-foreground">Gestion de proveedores y plantillas de correo</p>
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

      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button variant="outline" onClick={loadEmailTemplates}><Mail className="mr-2 h-4 w-4" />Plantillas Email</Button>
        <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" /> Nuevo Proveedor</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : suppliers.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Identificacion</TableHead>
                    <TableHead>Razon Social</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Telefono</TableHead>
                    <TableHead>Contacto</TableHead>
                    <TableHead>Plazo Credito</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suppliers.map((sup) => (
                    <TableRow key={sup.id}>
                      <TableCell className="font-mono text-xs">{sup.identificacion}</TableCell>
                      <TableCell className="font-medium">{sup.razon_social}</TableCell>
                      <TableCell className="text-xs">{sup.email || '-'}</TableCell>
                      <TableCell className="text-xs">{sup.telefono || '-'}</TableCell>
                      <TableCell className="text-xs">{sup.contacto_nombre || '-'}</TableCell>
                      <TableCell className="text-center">{sup.plazo_credito_dias} dias</TableCell>
                      <TableCell><Badge variant={sup.is_active ? 'default' : 'secondary'} className={sup.is_active ? 'bg-emerald-600' : ''}>{sup.is_active ? 'Activo' : 'Inactivo'}</Badge></TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(sup)}><Pencil className="h-3.5 w-3.5" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => setDeleteConfirm(sup.id)}><Trash2 className="h-3.5 w-3.5" /></Button>
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
        <Card><CardContent className="py-12 text-center"><Truck className="h-12 w-12 mx-auto text-muted-foreground mb-3" /><h3 className="text-lg font-medium">Sin proveedores</h3><p className="text-muted-foreground text-sm mt-1">Agregue proveedores para comenzar</p></CardContent></Card>
      )}

      {/* Supplier Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingSupplier ? 'Editar Proveedor' : 'Nuevo Proveedor'}</DialogTitle>
            <DialogDescription>{editingSupplier ? 'Modifique los datos del proveedor' : 'Registre un nuevo proveedor'}</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh]">
            <div className="space-y-4 pr-2">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Tipo Identificacion</Label><Select value={form.tipo_identificacion} onValueChange={(v) => setForm({ ...form, tipo_identificacion: v })}><SelectTrigger /><SelectContent><SelectItem value="04">RUC</SelectItem><SelectItem value="05">Cedula</SelectItem><SelectItem value="06">Pasaporte</SelectItem><SelectItem value="08">Exterior</SelectItem></SelectContent></Select></div>
                <div className="space-y-2"><Label>Identificacion</Label><Input value={form.identificacion} onChange={(e) => setForm({ ...form, identificacion: e.target.value })} /></div>
              </div>
              <div className="space-y-2"><Label>Razon Social</Label><Input value={form.razon_social} onChange={(e) => setForm({ ...form, razon_social: e.target.value })} /></div>
              <div className="space-y-2"><Label>Nombre Comercial</Label><Input value={form.nombre_comercial} onChange={(e) => setForm({ ...form, nombre_comercial: e.target.value })} /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                <div className="space-y-2"><Label>Telefono</Label><Input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Contacto Nombre</Label><Input value={form.contacto_nombre} onChange={(e) => setForm({ ...form, contacto_nombre: e.target.value })} /></div>
                <div className="space-y-2"><Label>Contacto Telefono</Label><Input value={form.contacto_telefono} onChange={(e) => setForm({ ...form, contacto_telefono: e.target.value })} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Plazo Credito (dias)</Label><Input type="number" value={form.plazo_credito_dias} onChange={(e) => setForm({ ...form, plazo_credito_dias: e.target.value })} /></div>
                <div className="space-y-2"><Label>Direccion</Label><Input value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} /></div>
              </div>
              <div className="space-y-2"><Label>Observaciones</Label><Textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} /></div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowDialog(false)}>Cancelar</Button>
                <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}{editingSupplier ? 'Guardar' : 'Crear'}</Button>
              </div>
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      <Dialog open={!!deleteConfirm} onOpenChange={(o) => !o && setDeleteConfirm(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader><DialogTitle>Eliminar Proveedor</DialogTitle><DialogDescription>Esta seguro de eliminar este proveedor?</DialogDescription></DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={() => deleteConfirm && handleDelete(deleteConfirm)}>Eliminar</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Email Templates Dialog */}
      <Dialog open={showTemplates} onOpenChange={setShowTemplates}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Plantillas de Correo</DialogTitle>
            <DialogDescription>Administre las plantillas de correo electronico</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button size="sm" onClick={() => setShowTemplateDialog(true)}><PlusCircle className="mr-2 h-4 w-4" /> Nueva Plantilla</Button>
            </div>
            {emailTemplates.length > 0 ? (
              <ScrollArea className="max-h-64">
                <Table>
                  <TableHeader><TableRow><TableHead>Nombre</TableHead><TableHead>Tipo</TableHead><TableHead>Asunto</TableHead><TableHead>Estado</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {emailTemplates.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell>{t.nombre}</TableCell>
                        <TableCell><Badge variant="outline">{t.tipo}</Badge></TableCell>
                        <TableCell className="max-w-[200px] truncate text-xs">{t.asunto}</TableCell>
                        <TableCell><Badge variant={t.is_active ? 'default' : 'secondary'}>{t.is_active ? 'Activa' : 'Inactiva'}</Badge></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">No hay plantillas de correo</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Template Create Dialog */}
      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Nueva Plantilla</DialogTitle><DialogDescription>Cree una plantilla de correo</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Nombre</Label><Input value={templateForm.nombre} onChange={(e) => setTemplateForm({ ...templateForm, nombre: e.target.value })} /></div>
            <div className="space-y-2"><Label>Tipo</Label><Select value={templateForm.tipo} onValueChange={(v) => setTemplateForm({ ...templateForm, tipo: v })}><SelectTrigger /><SelectContent><SelectItem value="factura">Factura</SelectItem><SelectItem value="nota_credito">Nota Credito</SelectItem><SelectItem value="nota_debito">Nota Debito</SelectItem><SelectItem value="proforma">Proforma</SelectItem><SelectItem value="general">General</SelectItem></SelectContent></Select></div>
            <div className="space-y-2"><Label>Asunto</Label><Input value={templateForm.asunto} onChange={(e) => setTemplateForm({ ...templateForm, asunto: e.target.value })} placeholder="Factura #{{secuencial}}" /></div>
            <div className="space-y-2"><Label>Cuerpo HTML</Label><Textarea value={templateForm.cuerpo_html} onChange={(e) => setTemplateForm({ ...templateForm, cuerpo_html: e.target.value })} rows={5} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowTemplateDialog(false)}>Cancelar</Button>
              <Button onClick={handleCreateTemplate} disabled={templateLoading}>{templateLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
