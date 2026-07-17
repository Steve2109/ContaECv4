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
  Database,
  Loader2,
  RefreshCw,
  Upload,
  Download,
  AlertTriangle,
  Package,
  Plus,
  ArrowUpDown,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getKardexMovements,
  getProductSaldo,
  createKardexAjuste,
  getProducts,
  importProductsExcel,
  importProductsCSV,
  exportProductsExcel,
  exportProductsCSV,
  type KardexMovement,
  type KardexSaldo,
  type ProductResponse,
  type User,
  type Company,
} from '@/lib/api';

function formatCurrency(amount: number): string {
  return amount.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface ContaECInventoryProps {
  user: User;
  companies: Company[];
}

export function ContaECInventory({ user: _user, companies }: ContaECInventoryProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Inventario</h2>
          <p className="text-muted-foreground">Kardex, stock y movimientos de inventario</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin empresas registradas</h3>
            <p className="text-muted-foreground text-sm mt-1">
              Registre una empresa para gestionar el inventario.
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
          <h2 className="text-2xl font-bold">Inventario</h2>
          <p className="text-muted-foreground">Kardex, stock y movimientos de inventario</p>
        </div>
        {companies.length > 1 && (
          <div className="flex items-center gap-2">
            <Label htmlFor="inv-company-select" className="text-sm whitespace-nowrap">Empresa:</Label>
            <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
              <SelectTrigger id="inv-company-select" className="w-[220px]">
                <SelectValue placeholder="Seleccione empresa" />
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

      <Tabs defaultValue="kardex" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="kardex" className="gap-1.5">
            <ArrowUpDown className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Kardex</span>
          </TabsTrigger>
          <TabsTrigger value="stock" className="gap-1.5">
            <Package className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Stock</span>
          </TabsTrigger>
          <TabsTrigger value="import-export" className="gap-1.5">
            <Upload className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Importar/Exportar</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="kardex">
          <KardexTab companyId={selectedCompanyId} />
        </TabsContent>
        <TabsContent value="stock">
          <StockTab companyId={selectedCompanyId} />
        </TabsContent>
        <TabsContent value="import-export">
          <ImportExportTab companyId={selectedCompanyId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Kardex Tab ──────────────────────────────────────────────

function KardexTab({ companyId }: { companyId: string }) {
  const [movements, setMovements] = useState<KardexMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState<string>('all');
  const [filterProductId, setFilterProductId] = useState<string>('all');
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [showAjuste, setShowAjuste] = useState(false);
  const [ajusteForm, setAjusteForm] = useState({ product_id: '', cantidad_ajuste: '0', costo_unitario: '0', detalle: '' });
  const [ajusteLoading, setAjusteLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [movs, prods] = await Promise.all([
        getKardexMovements({
          company_id: companyId,
          tipo_movimiento: filterTipo !== 'all' ? filterTipo : undefined,
          product_id: filterProductId !== 'all' ? filterProductId : undefined,
        }),
        getProducts(companyId),
      ]);
      setMovements(movs);
      setProducts(prods);
    } catch {
      toast.error('Error al cargar movimientos de kardex');
    } finally {
      setLoading(false);
    }
  }, [companyId, filterTipo, filterProductId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleCreateAjuste() {
    setAjusteLoading(true);
    try {
      await createKardexAjuste({
        company_id: companyId,
        product_id: ajusteForm.product_id,
        tipo_ajuste: Number(ajusteForm.cantidad_ajuste) >= 0 ? 'positivo' : 'negativo',
        cantidad: Math.abs(Number(ajusteForm.cantidad_ajuste)),
        costo_unitario: Number(ajusteForm.costo_unitario),
        detalle: ajusteForm.detalle,
      });
      toast.success('Ajuste de inventario registrado');
      setShowAjuste(false);
      setAjusteForm({ product_id: '', cantidad_ajuste: '0', costo_unitario: '0', detalle: '' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear ajuste');
    } finally {
      setAjusteLoading(false);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterTipo} onValueChange={setFilterTipo}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Tipo movimiento" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="entrada">Entrada</SelectItem>
            <SelectItem value="salida">Salida</SelectItem>
            <SelectItem value="ajuste">Ajuste</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterProductId} onValueChange={setFilterProductId}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Producto" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los productos</SelectItem>
            {products.map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.descripcion}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button onClick={() => setShowAjuste(true)}>
          <Plus className="mr-2 h-4 w-4" /> Ajuste
        </Button>
      </div>

      {movements.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Producto</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                    <TableHead className="text-right">Costo Unit.</TableHead>
                    <TableHead className="text-right">Costo Total</TableHead>
                    <TableHead className="text-right">Saldo Cant.</TableHead>
                    <TableHead>Detalle</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movements.map((m) => {
                    const prod = products.find((p) => p.id === m.product_id);
                    return (
                      <TableRow key={m.id}>
                        <TableCell className="text-xs">{new Date(m.fecha_movimiento).toLocaleDateString('es-EC')}</TableCell>
                        <TableCell>
                          <Badge variant={m.tipo_movimiento === 'entrada' ? 'default' : m.tipo_movimiento === 'salida' ? 'destructive' : 'secondary'}
                            className={m.tipo_movimiento === 'entrada' ? 'bg-emerald-600' : ''}>
                            {m.tipo_movimiento}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[150px] truncate">{prod?.descripcion || m.product_id}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{m.cantidad}</TableCell>
                        <TableCell className="text-right font-mono text-xs">${formatCurrency(m.costo_unitario)}</TableCell>
                        <TableCell className="text-right font-mono text-xs">${formatCurrency(m.costo_total)}</TableCell>
                        <TableCell className="text-right font-mono text-xs font-medium">{m.saldo_cantidad}</TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate">{m.detalle || '-'}</TableCell>
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
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin movimientos</h3>
            <p className="text-muted-foreground text-sm mt-1">No hay movimientos de kardex registrados</p>
          </CardContent>
        </Card>
      )}

      {/* Ajuste Dialog */}
      <Dialog open={showAjuste} onOpenChange={setShowAjuste}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ajuste de Inventario</DialogTitle>
            <DialogDescription>Registre un ajuste positivo o negativo al inventario</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Producto</Label>
              <Select value={ajusteForm.product_id} onValueChange={(v) => setAjusteForm({ ...ajusteForm, product_id: v })}>
                <SelectTrigger><SelectValue placeholder="Seleccione producto" /></SelectTrigger>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.descripcion}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Cantidad (negativo = decrementar)</Label>
                <Input type="number" value={ajusteForm.cantidad_ajuste} onChange={(e) => setAjusteForm({ ...ajusteForm, cantidad_ajuste: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Costo Unitario</Label>
                <Input type="number" value={ajusteForm.costo_unitario} onChange={(e) => setAjusteForm({ ...ajusteForm, costo_unitario: e.target.value })} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Motivo del ajuste</Label>
              <Input value={ajusteForm.detalle} onChange={(e) => setAjusteForm({ ...ajusteForm, detalle: e.target.value })} placeholder="Conteo fisico, merma, etc." />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowAjuste(false)}>Cancelar</Button>
              <Button onClick={handleCreateAjuste} disabled={ajusteLoading}>
                {ajusteLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Registrar Ajuste
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Stock Tab ───────────────────────────────────────────────

function StockTab({ companyId }: { companyId: string }) {
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [saldos, setSaldos] = useState<Record<string, KardexSaldo>>({});
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const prods = await getProducts(companyId);
      setProducts(prods);
      const saldoMap: Record<string, KardexSaldo> = {};
      await Promise.all(
        prods.map(async (p) => {
          try {
            const saldo = await getProductSaldo(p.id);
            saldoMap[p.id] = saldo;
          } catch {
            // Product may not have kardex entries
          }
        })
      );
      setSaldos(saldoMap);
    } catch {
      toast.error('Error al cargar stock');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {products.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Codigo</TableHead>
                    <TableHead>Descripcion</TableHead>
                    <TableHead className="text-right">Precio Unit.</TableHead>
                    <TableHead className="text-right">Stock</TableHead>
                    <TableHead className="text-right">Valor Stock</TableHead>
                    <TableHead className="text-right">Costo Prom.</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.map((p) => {
                    const saldo = saldos[p.id];
                    const lowStock = saldo && saldo.saldo_cantidad <= 0;
                    return (
                      <TableRow key={p.id}>
                        <TableCell className="font-mono text-xs">{p.codigo_principal}</TableCell>
                        <TableCell className="max-w-[200px] truncate">{p.descripcion}</TableCell>
                        <TableCell className="text-right">${formatCurrency(p.precio_unitario)}</TableCell>
                        <TableCell className="text-right font-medium">{saldo?.saldo_cantidad ?? 0}</TableCell>
                        <TableCell className="text-right">${saldo ? formatCurrency(saldo.saldo_valor) : '0.00'}</TableCell>
                        <TableCell className="text-right">${saldo ? formatCurrency(saldo.costo_promedio) : '0.00'}</TableCell>
                        <TableCell>
                          {lowStock ? (
                            <Badge variant="destructive" className="gap-1"><AlertTriangle className="h-3 w-3" /> Sin stock</Badge>
                          ) : (
                            <Badge variant="secondary">En stock</Badge>
                          )}
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
            <Package className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin productos</h3>
            <p className="text-muted-foreground text-sm mt-1">Agregue productos para ver el stock</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Import/Export Tab ───────────────────────────────────────

function ImportExportTab({ companyId }: { companyId: string }) {
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function handleImportExcel(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importProductsExcel(companyId, file);
      toast.success(`Importacion completada: ${result.success} productos procesados`);
      if (result.errors > 0) {
        toast.warning(`${result.errors} errores encontrados`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al importar');
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  }

  async function handleImportCSV(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importProductsCSV(companyId, file);
      toast.success(`Importacion completada: ${result.success} productos procesados`);
      if (result.errors > 0) {
        toast.warning(`${result.errors} errores encontrados`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al importar CSV');
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  }

  async function handleExportExcel() {
    setExporting(true);
    try {
      const blob = await exportProductsExcel(companyId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'productos.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Productos exportados a Excel');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al exportar');
    } finally {
      setExporting(false);
    }
  }

  async function handleExportCSV() {
    setExporting(true);
    try {
      const blob = await exportProductsCSV(companyId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'productos.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Productos exportados a CSV');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al exportar');
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Import Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="h-4 w-4 text-primary" /> Importar Productos
          </CardTitle>
          <CardDescription>Cargue productos desde archivos Excel o CSV</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Archivo Excel (.xlsx)</Label>
            <Input type="file" accept=".xlsx,.xls" onChange={handleImportExcel} disabled={importing} />
          </div>
          <div className="space-y-2">
            <Label>Archivo CSV (.csv)</Label>
            <Input type="file" accept=".csv" onChange={handleImportCSV} disabled={importing} />
          </div>
          {importing && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Importando...
            </div>
          )}
        </CardContent>
      </Card>

      {/* Export Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="h-4 w-4 text-primary" /> Exportar Productos
          </CardTitle>
          <CardDescription>Descargue productos en diferentes formatos</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button variant="outline" className="w-full justify-start gap-2" onClick={handleExportExcel} disabled={exporting}>
            <Download className="h-4 w-4" /> Exportar Excel (.xlsx)
          </Button>
          <Button variant="outline" className="w-full justify-start gap-2" onClick={handleExportCSV} disabled={exporting}>
            <Download className="h-4 w-4" /> Exportar CSV (.csv)
          </Button>
          {exporting && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Exportando...
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
