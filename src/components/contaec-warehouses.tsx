'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Warehouse as WarehouseIcon,
  Loader2,
  RefreshCw,
  Plus,
  MapPin,
  ArrowRightLeft,
  ClipboardList,
  Pencil,
  Power,
  Search,
  ChevronRight,
  ChevronLeft,
  Download,
  Star,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getWarehouses,
  createWarehouse,
  updateWarehouse,
  getWarehouseLocations,
  createWarehouseLocation,
  updateWarehouseLocation,
  deleteWarehouseLocation,
  createWarehouseTransfer,
  getWarehouseTransfers,
  getWarehouseTransfer,
  sendWarehouseTransfer,
  receiveWarehouseTransfer,
  cancelWarehouseTransfer,
  getDetailedKardex,
  getProducts,
  type Warehouse,
  type WarehouseCreate,
  type WarehouseUpdate,
  type WarehouseLocation,
  type WarehouseLocationCreate,
  type WarehouseLocationUpdate,
  type WarehouseTransfer,
  type WarehouseTransferCreate,
  type WarehouseKardexDetalle,
  type ProductResponse,
  type User,
  type Company,
} from '@/lib/api';

function formatCurrency(amount: number): string {
  return amount.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface ContaECWarehousesProps {
  user: User;
  companies: Company[];
}

export function ContaECWarehouses({ user: _user, companies }: ContaECWarehousesProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Almacenes</h2>
          <p className="text-muted-foreground">Multi-almacen y logistica</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <WarehouseIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin empresas registradas</h3>
            <p className="text-muted-foreground text-sm mt-1">
              Registre una empresa para gestionar almacenes.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Almacenes</h2>
          <p className="text-muted-foreground">Multi-almacen y logistica</p>
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

      <Tabs defaultValue="bodegas" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="bodegas" className="gap-1.5"><WarehouseIcon className="h-3.5 w-3.5" /><span className="hidden sm:inline">Bodegas</span></TabsTrigger>
          <TabsTrigger value="ubicaciones" className="gap-1.5"><MapPin className="h-3.5 w-3.5" /><span className="hidden sm:inline">Ubicaciones</span></TabsTrigger>
          <TabsTrigger value="transferencias" className="gap-1.5"><ArrowRightLeft className="h-3.5 w-3.5" /><span className="hidden sm:inline">Transferencias</span></TabsTrigger>
          <TabsTrigger value="kardex" className="gap-1.5"><ClipboardList className="h-3.5 w-3.5" /><span className="hidden sm:inline">Kardex Detallado</span></TabsTrigger>
        </TabsList>
        <TabsContent value="bodegas"><BodegasTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="ubicaciones"><UbicacionesTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="transferencias"><TransferenciasTab companyId={selectedCompanyId} /></TabsContent>
        <TabsContent value="kardex"><KardexDetalladoTab companyId={selectedCompanyId} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Tab 1: Bodegas ──────────────────────────────────────────

function BodegasTab({ companyId }: { companyId: string }) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    nombre: '', codigo: '', direccion: '', ciudad: '', responsable: '', telefono: '', is_principal: false,
  });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getWarehouses(companyId);
      setWarehouses(data);
    } catch {
      toast.error('Error al cargar bodegas');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  function openCreate() {
    setForm({ nombre: '', codigo: '', direccion: '', ciudad: '', responsable: '', telefono: '', is_principal: false });
    setEditingWarehouse(null);
    setShowCreate(true);
  }

  function openEdit(wh: Warehouse) {
    setForm({
      nombre: wh.nombre, codigo: wh.codigo, direccion: wh.direccion || '', ciudad: wh.ciudad || '',
      responsable: wh.responsable || '', telefono: wh.telefono || '', is_principal: wh.is_principal,
    });
    setEditingWarehouse(wh);
    setShowCreate(true);
  }

  async function handleSave() {
    if (!form.nombre) { toast.error('El nombre es requerido'); return; }
    setSaving(true);
    try {
      if (editingWarehouse) {
        const data: WarehouseUpdate = {
          nombre: form.nombre,
          direccion: form.direccion || undefined,
          ciudad: form.ciudad || undefined,
          responsable: form.responsable || undefined,
          telefono: form.telefono || undefined,
          is_principal: form.is_principal,
        };
        await updateWarehouse(editingWarehouse.id, data);
        toast.success('Bodega actualizada');
      } else {
        const data: WarehouseCreate = {
          company_id: companyId,
          nombre: form.nombre,
          codigo: form.codigo || undefined,
          direccion: form.direccion || undefined,
          ciudad: form.ciudad || undefined,
          responsable: form.responsable || undefined,
          telefono: form.telefono || undefined,
          is_principal: form.is_principal,
        };
        await createWarehouse(data);
        toast.success('Bodega creada');
      }
      setShowCreate(false);
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar bodega');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(wh: Warehouse) {
    try {
      await updateWarehouse(wh.id, { is_active: !wh.is_active });
      toast.success(wh.is_active ? 'Bodega desactivada' : 'Bodega activada');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al cambiar estado');
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" /> Nueva Bodega</Button>
      </div>

      {warehouses.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {warehouses.map((wh) => (
            <Card key={wh.id} className={!wh.is_active ? 'opacity-60' : ''}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      {wh.nombre}
                      {wh.is_principal && <Badge className="bg-amber-500 text-white text-[10px]"><Star className="h-3 w-3 mr-0.5" /> Principal</Badge>}
                    </CardTitle>
                    <CardDescription className="font-mono text-xs">{wh.codigo}</CardDescription>
                  </div>
                  <Badge variant={wh.is_active ? 'default' : 'secondary'} className={wh.is_active ? 'bg-emerald-600' : ''}>
                    {wh.is_active ? 'Activa' : 'Inactiva'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-0 space-y-2">
                {wh.ciudad && <p className="text-sm text-muted-foreground">Ciudad: {wh.ciudad}</p>}
                {wh.direccion && <p className="text-sm text-muted-foreground">Dir: {wh.direccion}</p>}
                {wh.responsable && <p className="text-sm text-muted-foreground">Responsable: {wh.responsable}</p>}
                {wh.telefono && <p className="text-sm text-muted-foreground">Tel: {wh.telefono}</p>}
                <Separator />
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => openEdit(wh)}><Pencil className="mr-1 h-3 w-3" /> Editar</Button>
                  <Button size="sm" variant={wh.is_active ? 'secondary' : 'default'} onClick={() => handleDeactivate(wh)}>
                    <Power className="mr-1 h-3 w-3" /> {wh.is_active ? 'Desactivar' : 'Activar'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <WarehouseIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin bodegas</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree una bodega para comenzar</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingWarehouse ? 'Editar Bodega' : 'Nueva Bodega'}</DialogTitle>
            <DialogDescription>{editingWarehouse ? 'Modifique los datos de la bodega' : 'Cree una nueva bodega'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre *</Label>
                <Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Bodega Principal" />
              </div>
              <div className="space-y-2">
                <Label>Codigo</Label>
                <Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="BOD-001" disabled={!!editingWarehouse} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Direccion</Label>
              <Input value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} placeholder="Av. Amazonas 123" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Ciudad</Label>
                <Input value={form.ciudad} onChange={(e) => setForm({ ...form, ciudad: e.target.value })} placeholder="Quito" />
              </div>
              <div className="space-y-2">
                <Label>Responsable</Label>
                <Input value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })} placeholder="Juan Perez" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Telefono</Label>
                <Input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} placeholder="0991234567" />
              </div>
              <div className="flex items-center gap-2 pt-6">
                <Checkbox id="is_principal" checked={form.is_principal} onCheckedChange={(checked) => setForm({ ...form, is_principal: !!checked })} />
                <Label htmlFor="is_principal" className="text-sm">Bodega principal</Label>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}{editingWarehouse ? 'Guardar' : 'Crear'}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Tab 2: Ubicaciones ──────────────────────────────────────

const ZONAS = ['A', 'B', 'C', 'D', 'E', 'F'];

function UbicacionesTab({ companyId }: { companyId: string }) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>('');
  const [locations, setLocations] = useState<WarehouseLocation[]>([]);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingLocation, setEditingLocation] = useState<WarehouseLocation | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    zona: 'A', rack: '', estante: '', nivel: '', capacidad_maxima: '', producto_id: '',
  });

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [whs, prods] = await Promise.all([getWarehouses(companyId), getProducts(companyId)]);
      setWarehouses(whs);
      setProducts(prods);
      if (whs.length > 0 && !selectedWarehouseId) {
        setSelectedWarehouseId(whs[0].id);
      }
    } catch {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  }, [companyId, selectedWarehouseId]);

  const loadLocations = useCallback(async () => {
    if (!selectedWarehouseId) return;
    try {
      const locs = await getWarehouseLocations(selectedWarehouseId);
      setLocations(locs);
    } catch {
      toast.error('Error al cargar ubicaciones');
    }
  }, [selectedWarehouseId]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadLocations(); }, [loadLocations]);

  function generateCodigoUbicacion(): string {
    const parts = [form.zona];
    if (form.rack) parts.push(`R${form.rack}`);
    if (form.estante) parts.push(`E${form.estante}`);
    if (form.nivel) parts.push(`N${form.nivel}`);
    return parts.join('-');
  }

  function openCreate() {
    setForm({ zona: 'A', rack: '', estante: '', nivel: '', capacidad_maxima: '', producto_id: '' });
    setEditingLocation(null);
    setShowCreate(true);
  }

  function openEdit(loc: WarehouseLocation) {
    setForm({
      zona: loc.zona, rack: loc.rack, estante: loc.estante, nivel: loc.nivel || '',
      capacidad_maxima: loc.capacidad_maxima?.toString() || '', producto_id: loc.producto_id || '',
    });
    setEditingLocation(loc);
    setShowCreate(true);
  }

  async function handleSave() {
    if (!form.rack || !form.estante) { toast.error('Rack y estante son requeridos'); return; }
    setSaving(true);
    try {
      if (editingLocation) {
        const data: WarehouseLocationUpdate = {
          zona: form.zona,
          rack: form.rack,
          estante: form.estante,
          nivel: form.nivel || undefined,
          capacidad_maxima: form.capacidad_maxima ? Number(form.capacidad_maxima) : undefined,
        };
        await updateWarehouseLocation(editingLocation.id, data);
        toast.success('Ubicacion actualizada');
      } else {
        const data: WarehouseLocationCreate = {
          warehouse_id: selectedWarehouseId,
          zona: form.zona,
          rack: form.rack,
          estante: form.estante,
          nivel: form.nivel || undefined,
          capacidad_maxima: form.capacidad_maxima ? Number(form.capacidad_maxima) : undefined,
          producto_id: form.producto_id || undefined,
        };
        await createWarehouseLocation(data);
        toast.success('Ubicacion creada');
      }
      setShowCreate(false);
      loadLocations();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar ubicacion');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteWarehouseLocation(id);
      toast.success('Ubicacion eliminada');
      loadLocations();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar ubicacion');
    }
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={selectedWarehouseId} onValueChange={setSelectedWarehouseId}>
          <SelectTrigger className="w-[220px]"><SelectValue placeholder="Seleccione bodega" /></SelectTrigger>
          <SelectContent>{warehouses.map((w) => (<SelectItem key={w.id} value={w.id}>{w.nombre}</SelectItem>))}</SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadLocations}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={openCreate} disabled={!selectedWarehouseId}><Plus className="mr-2 h-4 w-4" /> Nueva Ubicacion</Button>
      </div>

      {locations.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Codigo</TableHead>
                    <TableHead>Zona</TableHead>
                    <TableHead>Rack</TableHead>
                    <TableHead>Estante</TableHead>
                    <TableHead>Nivel</TableHead>
                    <TableHead>Producto</TableHead>
                    <TableHead className="text-right">Cant./Cap.</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {locations.map((loc) => {
                    const prod = products.find((p) => p.id === loc.producto_id);
                    return (
                      <TableRow key={loc.id}>
                        <TableCell className="font-mono text-xs font-medium">{loc.codigo_ubicacion}</TableCell>
                        <TableCell>{loc.zona}</TableCell>
                        <TableCell>{loc.rack}</TableCell>
                        <TableCell>{loc.estante}</TableCell>
                        <TableCell>{loc.nivel || '-'}</TableCell>
                        <TableCell className="max-w-[150px] truncate">{prod?.descripcion || '-'}</TableCell>
                        <TableCell className="text-right text-xs">
                          {loc.cantidad_actual}{loc.capacidad_maxima ? `/${loc.capacidad_maxima}` : ''}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button size="sm" variant="ghost" onClick={() => openEdit(loc)}><Pencil className="h-3 w-3" /></Button>
                            <Button size="sm" variant="ghost" className="text-destructive" onClick={() => handleDelete(loc.id)}>X</Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <MapPin className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin ubicaciones</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree ubicaciones fisicas para la bodega seleccionada</p>
          </CardContent>
        </Card>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingLocation ? 'Editar Ubicacion' : 'Nueva Ubicacion'}</DialogTitle>
            <DialogDescription>{editingLocation ? 'Modifique los datos de la ubicacion' : 'Cree una nueva ubicacion fisica'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Zona *</Label>
                <Select value={form.zona} onValueChange={(v) => setForm({ ...form, zona: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{ZONAS.map((z) => (<SelectItem key={z} value={z}>Zona {z}</SelectItem>))}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Rack *</Label>
                <Input value={form.rack} onChange={(e) => setForm({ ...form, rack: e.target.value })} placeholder="1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Estante *</Label>
                <Input value={form.estante} onChange={(e) => setForm({ ...form, estante: e.target.value })} placeholder="1" />
              </div>
              <div className="space-y-2">
                <Label>Nivel</Label>
                <Input value={form.nivel} onChange={(e) => setForm({ ...form, nivel: e.target.value })} placeholder="1" />
              </div>
            </div>
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm"><span className="font-medium">Codigo generado:</span> {generateCodigoUbicacion()}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Capacidad Maxima</Label>
                <Input type="number" value={form.capacidad_maxima} onChange={(e) => setForm({ ...form, capacidad_maxima: e.target.value })} placeholder="100" />
              </div>
              <div className="space-y-2">
                <Label>Producto (opcional)</Label>
                <Select value={form.producto_id} onValueChange={(v) => setForm({ ...form, producto_id: v })}>
                  <SelectTrigger><SelectValue placeholder="Sin asignar" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">Sin asignar</SelectItem>
                    {products.map((p) => (<SelectItem key={p.id} value={p.id}>{p.descripcion}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancelar</Button>
              <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}{editingLocation ? 'Guardar' : 'Crear'}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Tab 3: Transferencias ───────────────────────────────────

type TransferEstado = WarehouseTransfer['estado'];

function getEstadoBadge(estado: TransferEstado) {
  const map: Record<TransferEstado, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; className: string; label: string }> = {
    pendiente: { variant: 'secondary', className: 'bg-amber-100 text-amber-800 border-amber-300', label: 'Pendiente' },
    en_transito: { variant: 'secondary', className: 'bg-sky-100 text-sky-800 border-sky-300', label: 'En Transito' },
    recibida: { variant: 'secondary', className: 'bg-emerald-100 text-emerald-800 border-emerald-300', label: 'Recibida' },
    anulada: { variant: 'secondary', className: 'bg-gray-100 text-gray-600 border-gray-300', label: 'Anulada' },
  };
  const cfg = map[estado];
  return <Badge variant={cfg.variant} className={cfg.className}>{cfg.label}</Badge>;
}

interface TransferItemForm {
  product_id: string;
  cantidad: string;
  costo_unitario: string;
}

function TransferenciasTab({ companyId }: { companyId: string }) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [transfers, setTransfers] = useState<WarehouseTransfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEstado, setFilterEstado] = useState<string>('todas');
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [detailTransfer, setDetailTransfer] = useState<WarehouseTransfer | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Wizard form
  const [wOrigen, setWOrigen] = useState('');
  const [wDestino, setWDestino] = useState('');
  const [wItems, setWItems] = useState<TransferItemForm[]>([]);
  const [wMotivo, setWMotivo] = useState('');
  const [wObservaciones, setWObservaciones] = useState('');
  const [productSearch, setProductSearch] = useState('');

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [whs, prods] = await Promise.all([getWarehouses(companyId), getProducts(companyId)]);
      setWarehouses(whs);
      setProducts(prods);
      const params: { company_id: string; estado?: string } = { company_id: companyId };
      if (filterEstado !== 'todas') params.estado = filterEstado;
      const trans = await getWarehouseTransfers(params);
      setTransfers(trans);
    } catch {
      toast.error('Error al cargar transferencias');
    } finally {
      setLoading(false);
    }
  }, [companyId, filterEstado]);

  useEffect(() => { loadData(); }, [loadData]);

  function resetWizard() {
    setWOrigen(''); setWDestino(''); setWItems([]); setWMotivo(''); setWObservaciones('');
    setProductSearch(''); setWizardStep(1);
  }

  function updateWizardItem(index: number, field: keyof TransferItemForm, value: string) {
    const updated = [...wItems];
    updated[index] = { ...updated[index], [field]: value };
    setWItems(updated);
  }

  function removeWizardItem(index: number) {
    setWItems(wItems.filter((_, i) => i !== index));
  }

  async function handleCreateTransfer() {
    if (!wOrigen || !wDestino) { toast.error('Seleccione bodegas de origen y destino'); return; }
    if (wOrigen === wDestino) { toast.error('Las bodegas de origen y destino deben ser diferentes'); return; }
    if (wItems.length === 0) { toast.error('Agregue al menos un producto'); return; }
    const invalidItem = wItems.find((it) => !it.product_id || Number(it.cantidad) <= 0);
    if (invalidItem) { toast.error('Complete todos los items con cantidad mayor a 0'); return; }
    setSaving(true);
    try {
      const data: WarehouseTransferCreate = {
        company_id: companyId,
        warehouse_origen_id: wOrigen,
        warehouse_destino_id: wDestino,
        motivo: wMotivo || undefined,
        observaciones: wObservaciones || undefined,
        detalles: wItems.map((it) => ({
          product_id: it.product_id,
          cantidad: Number(it.cantidad),
          costo_unitario: Number(it.costo_unitario),
        })),
      };
      await createWarehouseTransfer(data);
      toast.success('Transferencia creada');
      setShowWizard(false);
      resetWizard();
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear transferencia');
    } finally {
      setSaving(false);
    }
  }

  async function handleAction(transferId: string, action: 'enviar' | 'recibir' | 'anular') {
    try {
      if (action === 'enviar') {
        await sendWarehouseTransfer(transferId);
        toast.success('Transferencia enviada');
      } else if (action === 'recibir') {
        await receiveWarehouseTransfer(transferId);
        toast.success('Transferencia recibida');
      } else if (action === 'anular') {
        await cancelWarehouseTransfer(transferId);
        toast.success('Transferencia anulada');
      }
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Error al ${action} transferencia`);
    }
  }

  async function viewDetail(transferId: string) {
    setLoadingDetail(true);
    try {
      const data = await getWarehouseTransfer(transferId);
      setDetailTransfer(data);
    } catch {
      toast.error('Error al cargar detalle');
    } finally {
      setLoadingDetail(false);
    }
  }

  const filteredProducts = productSearch
    ? products.filter((p) =>
        p.descripcion.toLowerCase().includes(productSearch.toLowerCase()) ||
        p.codigo_principal.toLowerCase().includes(productSearch.toLowerCase())
      )
    : products;

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterEstado} onValueChange={setFilterEstado}>
          <SelectTrigger className="w-[180px]"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todas</SelectItem>
            <SelectItem value="pendiente">Pendiente</SelectItem>
            <SelectItem value="en_transito">En Transito</SelectItem>
            <SelectItem value="recibida">Recibida</SelectItem>
            <SelectItem value="anulada">Anulada</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => { resetWizard(); setShowWizard(true); }}><Plus className="mr-2 h-4 w-4" /> Nueva Transferencia</Button>
      </div>

      {transfers.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Numero</TableHead>
                    <TableHead>Origen</TableHead>
                    <TableHead>Destino</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-center">Items</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transfers.map((tr) => (
                    <TableRow key={tr.id}>
                      <TableCell className="font-mono text-xs">{tr.numero}</TableCell>
                      <TableCell className="text-xs">{tr.warehouse_origen_nombre}</TableCell>
                      <TableCell className="text-xs">{tr.warehouse_destino_nombre}</TableCell>
                      <TableCell>{getEstadoBadge(tr.estado)}</TableCell>
                      <TableCell className="text-xs">{new Date(tr.created_at).toLocaleDateString('es-EC')}</TableCell>
                      <TableCell className="text-center">{tr.detalles?.length ?? 0}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => viewDetail(tr.id)} disabled={loadingDetail}>
                            <Search className="h-3 w-3" />
                          </Button>
                          {tr.estado === 'pendiente' && (
                            <>
                              <Button size="sm" variant="outline" className="text-sky-600" onClick={() => handleAction(tr.id, 'enviar')}>Enviar</Button>
                              <Button size="sm" variant="outline" className="text-destructive" onClick={() => handleAction(tr.id, 'anular')}>Anular</Button>
                            </>
                          )}
                          {tr.estado === 'en_transito' && (
                            <Button size="sm" variant="outline" className="text-emerald-600" onClick={() => handleAction(tr.id, 'recibir')}>Recibir</Button>
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
            <ArrowRightLeft className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin transferencias</h3>
            <p className="text-muted-foreground text-sm mt-1">Cree una transferencia entre bodegas</p>
          </CardContent>
        </Card>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!detailTransfer} onOpenChange={(o) => !o && setDetailTransfer(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Detalle Transferencia {detailTransfer?.numero}</DialogTitle>
            <DialogDescription>{detailTransfer && getEstadoBadge(detailTransfer.estado)}</DialogDescription>
          </DialogHeader>
          {detailTransfer && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-muted-foreground">Origen:</span> <span className="font-medium">{detailTransfer.warehouse_origen_nombre}</span></div>
                <div><span className="text-muted-foreground">Destino:</span> <span className="font-medium">{detailTransfer.warehouse_destino_nombre}</span></div>
                <div><span className="text-muted-foreground">Motivo:</span> {detailTransfer.motivo || '-'}</div>
                <div><span className="text-muted-foreground">Observaciones:</span> {detailTransfer.observaciones || '-'}</div>
                {detailTransfer.fecha_envio && <div><span className="text-muted-foreground">Fecha Envio:</span> {new Date(detailTransfer.fecha_envio).toLocaleDateString('es-EC')}</div>}
                {detailTransfer.fecha_recepcion && <div><span className="text-muted-foreground">Fecha Recepcion:</span> {new Date(detailTransfer.fecha_recepcion).toLocaleDateString('es-EC')}</div>}
              </div>
              <Separator />
              <ScrollArea className="max-h-48">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead className="text-right">Cantidad</TableHead>
                      <TableHead className="text-right">Costo Unit.</TableHead>
                      <TableHead className="text-right">Costo Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detailTransfer.detalles?.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell className="text-xs">{d.product_descripcion}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{d.cantidad}</TableCell>
                        <TableCell className="text-right font-mono text-xs">${formatCurrency(d.costo_unitario)}</TableCell>
                        <TableCell className="text-right font-mono text-xs">${formatCurrency(d.costo_total)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Wizard Dialog */}
      <Dialog open={showWizard} onOpenChange={(o) => { if (!o) resetWizard(); setShowWizard(o); }}>
        <DialogContent className="sm:max-w-xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nueva Transferencia</DialogTitle>
            <DialogDescription>Paso {wizardStep} de 3</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Step indicators */}
            <div className="flex items-center gap-2">
              {[1, 2, 3].map((step) => (
                <div key={step} className="flex items-center gap-2">
                  <div className={`h-2 w-8 rounded-full ${step <= wizardStep ? 'bg-primary' : 'bg-muted'}`} />
                  <span className="text-xs text-muted-foreground">
                    {step === 1 ? 'Bodegas' : step === 2 ? 'Productos' : 'Resumen'}
                  </span>
                </div>
              ))}
            </div>

            {wizardStep === 1 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Bodega Origen *</Label>
                  <Select value={wOrigen} onValueChange={setWOrigen}>
                    <SelectTrigger><SelectValue placeholder="Seleccione bodega origen" /></SelectTrigger>
                    <SelectContent>{warehouses.filter((w) => w.is_active).map((w) => (<SelectItem key={w.id} value={w.id}>{w.nombre}</SelectItem>))}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Bodega Destino *</Label>
                  <Select value={wDestino} onValueChange={setWDestino}>
                    <SelectTrigger><SelectValue placeholder="Seleccione bodega destino" /></SelectTrigger>
                    <SelectContent>{warehouses.filter((w) => w.is_active && w.id !== wOrigen).map((w) => (<SelectItem key={w.id} value={w.id}>{w.nombre}</SelectItem>))}</SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Buscar Producto</Label>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input className="pl-9" value={productSearch} onChange={(e) => setProductSearch(e.target.value)} placeholder="Buscar por nombre o codigo..." />
                  </div>
                </div>
                {wItems.length > 0 && (
                  <ScrollArea className="max-h-48">
                    <div className="space-y-2">
                      {wItems.map((item, idx) => {
                        const prod = products.find((p) => p.id === item.product_id);
                        return (
                          <div key={idx} className="flex items-end gap-2 p-2 border rounded-md">
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium truncate">{prod?.descripcion || 'Seleccione producto'}</p>
                            </div>
                            <div className="w-20">
                              <Label className="text-[10px]">Cantidad</Label>
                              <Input type="number" value={item.cantidad} onChange={(e) => updateWizardItem(idx, 'cantidad', e.target.value)} className="h-8 text-xs" />
                            </div>
                            <div className="w-24">
                              <Label className="text-[10px]">Costo Unit.</Label>
                              <Input type="number" value={item.costo_unitario} onChange={(e) => updateWizardItem(idx, 'costo_unitario', e.target.value)} className="h-8 text-xs" />
                            </div>
                            <Button size="sm" variant="ghost" className="text-destructive h-8" onClick={() => removeWizardItem(idx)}>X</Button>
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
                <Select onValueChange={(v) => {
                  const existing = wItems.find((it) => it.product_id === v);
                  if (!existing) {
                    const prod = products.find((p) => p.id === v);
                    setWItems([...wItems, { product_id: v, cantidad: '1', costo_unitario: prod?.precio_unitario?.toString() || '0' }]);
                  }
                }}>
                  <SelectTrigger><SelectValue placeholder="Agregar producto..." /></SelectTrigger>
                  <SelectContent>
                    {filteredProducts.filter((p) => !wItems.some((it) => it.product_id === p.id)).map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.codigo_principal} - {p.descripcion}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {wizardStep === 3 && (
              <div className="space-y-4">
                <div className="p-3 bg-muted rounded-md text-sm space-y-1">
                  <p><span className="text-muted-foreground">Origen:</span> {warehouses.find((w) => w.id === wOrigen)?.nombre}</p>
                  <p><span className="text-muted-foreground">Destino:</span> {warehouses.find((w) => w.id === wDestino)?.nombre}</p>
                  <p><span className="text-muted-foreground">Items:</span> {wItems.length}</p>
                </div>
                {wItems.length > 0 && (
                  <ScrollArea className="max-h-32">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Producto</TableHead>
                          <TableHead className="text-right">Cantidad</TableHead>
                          <TableHead className="text-right">Costo Unit.</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {wItems.map((it, idx) => {
                          const prod = products.find((p) => p.id === it.product_id);
                          return (
                            <TableRow key={idx}>
                              <TableCell className="text-xs">{prod?.descripcion || '-'}</TableCell>
                              <TableCell className="text-right text-xs">{it.cantidad}</TableCell>
                              <TableCell className="text-right text-xs">${formatCurrency(Number(it.costo_unitario))}</TableCell>
                              <TableCell className="text-right text-xs font-medium">${formatCurrency(Number(it.cantidad) * Number(it.costo_unitario))}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                )}
                <div className="space-y-2">
                  <Label>Motivo</Label>
                  <Input value={wMotivo} onChange={(e) => setWMotivo(e.target.value)} placeholder="Razon de la transferencia" />
                </div>
                <div className="space-y-2">
                  <Label>Observaciones</Label>
                  <Textarea value={wObservaciones} onChange={(e) => setWObservaciones(e.target.value)} rows={2} placeholder="Notas adicionales" />
                </div>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => wizardStep > 1 ? setWizardStep(wizardStep - 1) : (() => { resetWizard(); setShowWizard(false); })()}>
                {wizardStep > 1 ? <><ChevronLeft className="mr-1 h-4 w-4" /> Atras</> : 'Cancelar'}
              </Button>
              {wizardStep < 3 ? (
                <Button onClick={() => setWizardStep(wizardStep + 1)} disabled={wizardStep === 1 && (!wOrigen || !wDestino)}>
                  Siguiente <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={handleCreateTransfer} disabled={saving}>
                  {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Crear Transferencia
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Tab 4: Kardex Detallado ─────────────────────────────────

function KardexDetalladoTab({ companyId }: { companyId: string }) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [kardexData, setKardexData] = useState<WarehouseKardexDetalle[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [filterWarehouse, setFilterWarehouse] = useState<string>('all');
  const [filterProduct, setFilterProduct] = useState<string>('all');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [whs, prods] = await Promise.all([getWarehouses(companyId), getProducts(companyId)]);
      setWarehouses(whs);
      setProducts(prods);
    } catch {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleSearch() {
    setSearching(true);
    try {
      const params: { company_id: string; warehouse_id?: string; product_id?: string; fecha_desde?: string; fecha_hasta?: string } = {
        company_id: companyId,
      };
      if (filterWarehouse !== 'all') params.warehouse_id = filterWarehouse;
      if (filterProduct !== 'all') params.product_id = filterProduct;
      if (fechaDesde) params.fecha_desde = fechaDesde;
      if (fechaHasta) params.fecha_hasta = fechaHasta;
      const data = await getDetailedKardex(params);
      setKardexData(data);
    } catch {
      toast.error('Error al consultar kardex detallado');
    } finally {
      setSearching(false);
    }
  }

  function getTipoMovimientoBadge(tipo: string) {
    if (tipo === 'entrada') return <Badge variant="secondary" className="bg-emerald-100 text-emerald-800">Entrada</Badge>;
    if (tipo === 'salida') return <Badge variant="secondary" className="bg-red-100 text-red-800">Salida</Badge>;
    if (tipo === 'ajuste') return <Badge variant="secondary" className="bg-amber-100 text-amber-800">Ajuste</Badge>;
    return <Badge variant="outline">{tipo}</Badge>;
  }

  if (loading) return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label>Bodega</Label>
              <Select value={filterWarehouse} onValueChange={setFilterWarehouse}>
                <SelectTrigger><SelectValue placeholder="Todas" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las bodegas</SelectItem>
                  {warehouses.map((w) => (<SelectItem key={w.id} value={w.id}>{w.nombre}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Producto</Label>
              <Select value={filterProduct} onValueChange={setFilterProduct}>
                <SelectTrigger><SelectValue placeholder="Todos" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los productos</SelectItem>
                  {products.map((p) => (<SelectItem key={p.id} value={p.id}>{p.descripcion}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Fecha Desde</Label>
              <Input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Fecha Hasta</Label>
              <Input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={handleSearch} disabled={searching} className="flex-1">
                {searching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />} Consultar
              </Button>
              <Button variant="outline" size="icon" onClick={() => toast.info('Funcionalidad de exportacion proximamente')}>
                <Download className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {kardexData.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Bodega</TableHead>
                    <TableHead>Codigo</TableHead>
                    <TableHead>Producto</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                    <TableHead className="text-right">Costo Unit.</TableHead>
                    <TableHead className="text-right">Costo Total</TableHead>
                    <TableHead className="text-right">Saldo Cant.</TableHead>
                    <TableHead className="text-right">Saldo Valor</TableHead>
                    <TableHead>Referencia</TableHead>
                    <TableHead>Detalle</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {kardexData.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="text-xs">{new Date(row.fecha_movimiento).toLocaleDateString('es-EC')}</TableCell>
                      <TableCell className="text-xs">{row.warehouse_nombre}</TableCell>
                      <TableCell className="font-mono text-xs">{row.product_codigo}</TableCell>
                      <TableCell className="max-w-[120px] truncate text-xs">{row.product_descripcion}</TableCell>
                      <TableCell>{getTipoMovimientoBadge(row.tipo_movimiento)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{row.cantidad}</TableCell>
                      <TableCell className="text-right font-mono text-xs">${formatCurrency(row.costo_unitario)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">${formatCurrency(row.costo_total)}</TableCell>
                      <TableCell className="text-right font-mono text-xs font-medium">{row.saldo_cantidad}</TableCell>
                      <TableCell className="text-right font-mono text-xs">${formatCurrency(row.saldo_valor)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{row.referencia_tipo ? `${row.referencia_tipo}-${row.referencia_secuencial}` : '-'}</TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[100px] truncate">{row.detalle || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : !loading && !searching ? (
        <Card>
          <CardContent className="py-12 text-center">
            <ClipboardList className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin datos de kardex</h3>
            <p className="text-muted-foreground text-sm mt-1">Aplique filtros y consulte el kardex detallado</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
