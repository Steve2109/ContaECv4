'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
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
  ScanLine,
  ShoppingCart,
  Loader2,
  RefreshCw,
  Plus,
  Minus,
  X,
  DollarSign,
  CreditCard,
  Banknote,
  Receipt,
  Printer,
  Copy,
  Settings,
  Store,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  FileText,
  XCircle,
  Eye,
  Ban,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  openPOSSession,
  getPOSSessions,
  closePOSSession,
  getPOSSessionResumen,
  createPOSArqueo,
  createPOSTicket,
  getPOSTickets,
  getPOSTicket,
  voidPOSTicket,
  getPOSTicketPrintData,
  searchProductByBarcode,
  getProducts,
  type POSCashSession,
  type POSCashSessionOpen,
  type POSTicket,
  type POSTicketCreate,
  type POSArqueoCreate,
  type POSProductSearchResult,
  type POSTicketPrintData,
  type POSCashSessionResumen,
  type ProductResponse,
  type Company,
  type User,
} from '@/lib/api';

// ─── Helpers ─────────────────────────────────────────────────

function formatCurrency(amount: number): string {
  return amount.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es-EC', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

function getTicketEstadoBadge(estado: string) {
  const map: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; className: string }> = {
    pagado: { variant: 'default', className: 'bg-emerald-600' },
    pendiente: { variant: 'secondary', className: '' },
    anulado: { variant: 'destructive', className: '' },
    devuelto: { variant: 'outline', className: 'text-amber-600 border-amber-300' },
  };
  const b = map[estado] || { variant: 'secondary' as const, className: '' };
  return <Badge variant={b.variant} className={b.className}>{estado.toUpperCase()}</Badge>;
}

function getTipoVentaBadge(tipo: string) {
  const map: Record<string, { icon: React.ReactNode; className: string }> = {
    efectivo: { icon: <Banknote className="h-3 w-3" />, className: 'bg-emerald-100 text-emerald-700' },
    tarjeta: { icon: <CreditCard className="h-3 w-3" />, className: 'bg-blue-100 text-blue-700' },
    credito: { icon: <Clock className="h-3 w-3" />, className: 'bg-amber-100 text-amber-700' },
    mixto: { icon: <DollarSign className="h-3 w-3" />, className: 'bg-purple-100 text-purple-700' },
    otro: { icon: <DollarSign className="h-3 w-3" />, className: 'bg-gray-100 text-gray-700' },
  };
  const m = map[tipo] || map.otro;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${m.className}`}>
      {m.icon} {tipo.toUpperCase()}
    </span>
  );
}

// ─── Cart Item Type ──────────────────────────────────────────

interface CartItem {
  productId: string;
  codigoPrincipal: string;
  descripcion: string;
  cantidad: number;
  precioUnitario: number;
  descuento: number;
  ivaCodigo: string;
  ivaPorcentaje: number;
  stock: number;
}

// ─── Props ───────────────────────────────────────────────────

interface ContaECPOSProps {
  user: User;
  companies: Company[];
}

// ─── Main Component ──────────────────────────────────────────

export function ContaECPOS({ user, companies }: ContaECPOSProps) {
  const [view, setView] = useState<'terminal' | 'admin'>('terminal');
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
    companies.length > 0 ? companies[0].id : ''
  );

  if (companies.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Punto de Venta</h2>
          <p className="text-muted-foreground">Terminal de venta y gestion de caja</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Store className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin empresas</h3>
            <p className="text-sm text-muted-foreground">Cree una empresa primero para usar el POS</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Store className="h-6 w-6 text-emerald-600" />
          <div>
            <h2 className="text-2xl font-bold">Punto de Venta</h2>
            <p className="text-sm text-muted-foreground">Terminal de venta y gestion de caja</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {companies.length > 1 && (
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
          )}
          <div className="flex rounded-lg border overflow-hidden">
            <Button
              variant={view === 'terminal' ? 'default' : 'ghost'}
              className={`rounded-none ${view === 'terminal' ? 'bg-emerald-600 hover:bg-emerald-700' : ''}`}
              onClick={() => setView('terminal')}
            >
              <ShoppingCart className="mr-2 h-4 w-4" /> Terminal
            </Button>
            <Button
              variant={view === 'admin' ? 'default' : 'ghost'}
              className={`rounded-none ${view === 'admin' ? 'bg-emerald-600 hover:bg-emerald-700' : ''}`}
              onClick={() => setView('admin')}
            >
              <Settings className="mr-2 h-4 w-4" /> Admin
            </Button>
          </div>
        </div>
      </div>

      {/* Views */}
      {view === 'terminal' ? (
        <POSTerminalView user={user} companyId={selectedCompanyId} companies={companies} />
      ) : (
        <POSAdminView user={user} companyId={selectedCompanyId} companies={companies} />
      )}
    </div>
  );
}

// ═════════════════════════════════════════════════════════════
// VIEW 1: POS TERMINAL
// ═════════════════════════════════════════════════════════════

function POSTerminalView({
  user: _user,
  companyId,
  companies,
}: {
  user: User;
  companyId: string;
  companies: Company[];
}) {
  const [activeSession, setActiveSession] = useState<POSCashSession | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [showOpenSession, setShowOpenSession] = useState(false);
  const [opening, setOpening] = useState(false);

  // Cart state
  const [cart, setCart] = useState<CartItem[]>([]);
  const [tipoVenta, setTipoVenta] = useState<'efectivo' | 'tarjeta' | 'credito' | 'mixto'>('efectivo');
  const [montoRecibido, setMontoRecibido] = useState('');
  const [montoTarjeta, setMontoTarjeta] = useState('');
  const [montoEfectivoMixto, setMontoEfectivoMixto] = useState('');
  const [last4Digits, setLast4Digits] = useState('');
  const [propina, setPropina] = useState('');
  const [useCustomClient, setUseCustomClient] = useState(false);
  const [clientNombre, setClientNombre] = useState('');
  const [clientId, setClientId] = useState('');
  const [creating, setCreating] = useState(false);
  const [lastTicket, setLastTicket] = useState<POSTicket | null>(null);
  const [showChangeDialog, setShowChangeDialog] = useState(false);

  // Product search
  const [barcodeInput, setBarcodeInput] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [products, setProducts] = useState<POSProductSearchResult[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const barcodeRef = useRef<HTMLInputElement>(null);

  // Session form
  const [sessionForm, setSessionForm] = useState<{ numero_caja: string; monto_apertura: string }>({
    numero_caja: 'CAJA-001',
    monto_apertura: '0.00',
  });

  // Load active session
  const loadActiveSession = useCallback(async () => {
    if (!companyId) return;
    setLoadingSession(true);
    try {
      const sessions = await getPOSSessions({ company_id: companyId, estado: 'abierta' });
      if (sessions.length > 0) {
        setActiveSession(sessions[0]);
      } else {
        setActiveSession(null);
      }
    } catch {
      toast.error('Error al cargar sesion de caja');
    } finally {
      setLoadingSession(false);
    }
  }, [companyId]);

  // Load products
  const loadProducts = useCallback(async () => {
    if (!companyId) return;
    setLoadingProducts(true);
    try {
      const prods = await getProducts(companyId);
      // Convert ProductResponse to POSProductSearchResult-like objects
      const mapped: POSProductSearchResult[] = prods.map((p: ProductResponse) => ({
        id: p.id,
        codigo_principal: p.codigo_principal,
        codigo_auxiliar: p.codigo_auxiliar,
        codigo_barras: null,
        descripcion: p.descripcion,
        tipo: p.tipo,
        precio_unitario: p.precio_unitario,
        iva_codigo: p.iva_codigo,
        iva_porcentaje: p.iva_porcentaje,
        stock: 0,
        unidad_medida: p.unidad_medida,
      }));
      setProducts(mapped);
    } catch {
      toast.error('Error al cargar productos');
    } finally {
      setLoadingProducts(false);
    }
  }, [companyId]);

  useEffect(() => { loadActiveSession(); }, [loadActiveSession]);
  useEffect(() => { loadProducts(); }, [loadProducts]);

  // Barcode scan handler
  async function handleBarcodeScan() {
    if (!barcodeInput.trim()) return;
    try {
      const results = await searchProductByBarcode(barcodeInput.trim(), companyId);
      if (results.length > 0) {
        const p = results[0];
        addToCart(p);
        toast.success(`Producto agregado: ${p.descripcion}`);
      } else {
        toast.error('Producto no encontrado');
      }
    } catch {
      toast.error('Error al buscar producto');
    }
    setBarcodeInput('');
    barcodeRef.current?.focus();
  }

  // Name search handler
  async function handleNameSearch() {
    if (!searchInput.trim()) {
      loadProducts();
      return;
    }
    try {
      const results = await searchProductByBarcode(searchInput.trim(), companyId);
      setProducts(results);
    } catch {
      toast.error('Error al buscar');
    }
  }

  // Add to cart
  function addToCart(product: POSProductSearchResult) {
    setCart((prev) => {
      const existing = prev.find((i) => i.productId === product.id);
      if (existing) {
        return prev.map((i) =>
          i.productId === product.id ? { ...i, cantidad: i.cantidad + 1 } : i
        );
      }
      return [
        ...prev,
        {
          productId: product.id,
          codigoPrincipal: product.codigo_principal,
          descripcion: product.descripcion,
          cantidad: 1,
          precioUnitario: product.precio_unitario,
          descuento: 0,
          ivaCodigo: product.iva_codigo,
          ivaPorcentaje: product.iva_porcentaje,
          stock: product.stock,
        },
      ];
    });
  }

  function updateCartItemQty(productId: string, delta: number) {
    setCart((prev) =>
      prev
        .map((i) => (i.productId === productId ? { ...i, cantidad: Math.max(0, i.cantidad + delta) } : i))
        .filter((i) => i.cantidad > 0)
    );
  }

  function updateCartItemDiscount(productId: string, discount: number) {
    setCart((prev) =>
      prev.map((i) => (i.productId === productId ? { ...i, descuento: discount } : i))
    );
  }

  function removeCartItem(productId: string) {
    setCart((prev) => prev.filter((i) => i.productId !== productId));
  }

  function clearCart() {
    setCart([]);
    setMontoRecibido('');
    setMontoTarjeta('');
    setMontoEfectivoMixto('');
    setLast4Digits('');
    setPropina('');
    setUseCustomClient(false);
    setClientNombre('');
    setClientId('');
  }

  // Cart calculations
  const subtotalSinImpuestos = cart.reduce(
    (sum, i) => sum + i.cantidad * i.precioUnitario * (1 - i.descuento / 100), 0
  );
  const totalIva = cart.reduce(
    (sum, i) => {
      const lineSubtotal = i.cantidad * i.precioUnitario * (1 - i.descuento / 100);
      return sum + lineSubtotal * (i.ivaPorcentaje / 100);
    }, 0
  );
  const totalDescuento = cart.reduce(
    (sum, i) => sum + i.cantidad * i.precioUnitario * (i.descuento / 100), 0
  );
  const totalConImpuestos = subtotalSinImpuestos + totalIva;
  const propinaVal = Number(propina) || 0;
  const totalAPagar = totalConImpuestos + propinaVal;

  // Change calculation
  const montoRecibidoVal = Number(montoRecibido) || 0;
  const cambio = tipoVenta === 'efectivo' ? montoRecibidoVal - totalAPagar : 0;

  // Open session
  async function handleOpenSession() {
    if (!sessionForm.numero_caja || !sessionForm.monto_apertura) {
      toast.error('Complete todos los campos');
      return;
    }
    setOpening(true);
    try {
      const data: POSCashSessionOpen = {
        company_id: companyId,
        numero_caja: sessionForm.numero_caja,
        monto_apertura: Number(sessionForm.monto_apertura),
      };
      const session = await openPOSSession(data);
      setActiveSession(session);
      setShowOpenSession(false);
      toast.success(`Caja ${session.numero_caja} abierta`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al abrir caja');
    } finally {
      setOpening(false);
    }
  }

  // Create ticket (COBRAR)
  async function handleCobrar() {
    if (cart.length === 0) {
      toast.error('Agregue productos al carrito');
      return;
    }
    if (!activeSession) {
      toast.error('No hay sesion de caja abierta');
      return;
    }
    if (tipoVenta === 'efectivo' && montoRecibidoVal < totalAPagar) {
      toast.error('El monto recibido es menor al total');
      return;
    }
    if (tipoVenta === 'tarjeta' && !last4Digits) {
      toast.error('Ingrese los ultimos 4 digitos de la tarjeta');
      return;
    }
    if (tipoVenta === 'mixto') {
      const efectivoMixto = Number(montoEfectivoMixto) || 0;
      const tarjetaMixto = Number(montoTarjeta) || 0;
      if (efectivoMixto + tarjetaMixto < totalAPagar) {
        toast.error('Los montos no cubren el total');
        return;
      }
    }

    setCreating(true);
    try {
      const ticketData: POSTicketCreate = {
        company_id: companyId,
        cash_session_id: activeSession.id,
        tipo_venta: tipoVenta,
        cliente_nombre: useCustomClient ? clientNombre || 'CONSUMIDOR FINAL' : 'CONSUMIDOR FINAL',
        cliente_identificacion: useCustomClient ? clientId || '9999999999999' : '9999999999999',
        cliente_tipo_identificacion: useCustomClient && clientId ? '05' : '07',
        detalles: cart.map((i) => ({
          product_id: i.productId,
          codigo_principal: i.codigoPrincipal,
          descripcion: i.descripcion,
          cantidad: i.cantidad,
          precio_unitario: i.precioUnitario,
          descuento: i.descuento,
          iva_codigo: i.ivaCodigo,
          iva_porcentaje: i.ivaPorcentaje,
        })),
        propina: propinaVal > 0 ? propinaVal : undefined,
        numero_tarjeta: tipoVenta === 'tarjeta' || tipoVenta === 'mixto' ? last4Digits : undefined,
      };

      if (tipoVenta === 'efectivo') {
        ticketData.monto_efectivo = totalAPagar;
      } else if (tipoVenta === 'tarjeta') {
        ticketData.monto_tarjeta = totalAPagar;
      } else if (tipoVenta === 'credito') {
        ticketData.monto_credito = totalAPagar;
      } else if (tipoVenta === 'mixto') {
        ticketData.monto_efectivo = Number(montoEfectivoMixto) || 0;
        ticketData.monto_tarjeta = Number(montoTarjeta) || 0;
      }

      const ticket = await createPOSTicket(ticketData);
      setLastTicket(ticket);
      setShowChangeDialog(true);
      toast.success(`Ticket creado: ${ticket.numero_ticket}`);
      clearCart();
      // Refresh session to update totals
      loadActiveSession();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear ticket');
    } finally {
      setCreating(false);
    }
  }

  // No active session
  if (loadingSession) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-10 w-10 animate-spin text-emerald-600" />
      </div>
    );
  }

  if (!activeSession) {
    return (
      <div className="space-y-4">
        <Card className="border-amber-300 bg-amber-50">
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-14 w-14 mx-auto text-amber-500 mb-4" />
            <h3 className="text-xl font-bold text-amber-800 mb-2">No hay caja abierta</h3>
            <p className="text-amber-700 mb-6">Debe abrir una sesion de caja antes de realizar ventas</p>
            <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700 min-h-[48px] text-base" onClick={() => setShowOpenSession(true)}>
              <Banknote className="mr-2 h-5 w-5" /> Abrir Caja
            </Button>
          </CardContent>
        </Card>

        <Dialog open={showOpenSession} onOpenChange={setShowOpenSession}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Abrir Caja</DialogTitle>
              <DialogDescription>Inicie una nueva sesion de caja</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Empresa</Label>
                <Select value={companyId} disabled>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {companies.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Numero de Caja</Label>
                <Input
                  value={sessionForm.numero_caja}
                  onChange={(e) => setSessionForm({ ...sessionForm, numero_caja: e.target.value })}
                  placeholder="CAJA-001"
                />
              </div>
              <div className="space-y-2">
                <Label>Monto de Apertura ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={sessionForm.monto_apertura}
                  onChange={(e) => setSessionForm({ ...sessionForm, monto_apertura: e.target.value })}
                  placeholder="0.00"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowOpenSession(false)}>Cancelar</Button>
                <Button onClick={handleOpenSession} disabled={opening} className="bg-emerald-600 hover:bg-emerald-700">
                  {opening ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Banknote className="mr-2 h-4 w-4" />}
                  Abrir Caja
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Change Dialog */}
        <ChangeDialog
          open={showChangeDialog}
          onOpenChange={setShowChangeDialog}
          ticket={lastTicket}
          cambio={tipoVenta === 'efectivo' ? cambio : 0}
          company={companies.find((c) => c.id === companyId)}
        />
      </div>
    );
  }

  // ─── POS TERMINAL LAYOUT ────────────────────────────────────
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4" style={{ minHeight: 'calc(100vh - 200px)' }}>
        {/* LEFT PANEL - Products (60%) */}
        <div className="lg:col-span-3 space-y-3">
          {/* Barcode Scanner */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <ScanLine className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-emerald-600" />
              <Input
                ref={barcodeRef}
                className="pl-10 h-12 text-base"
                placeholder="Escanear codigo de barras..."
                value={barcodeInput}
                onChange={(e) => setBarcodeInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleBarcodeScan(); }}
                autoFocus
              />
            </div>
            <Button size="lg" className="h-12 bg-emerald-600 hover:bg-emerald-700 min-w-[80px]" onClick={handleBarcodeScan}>
              <ScanLine className="h-5 w-5" />
            </Button>
          </div>

          {/* Quick Search */}
          <div className="flex gap-2">
            <Input
              className="h-10"
              placeholder="Buscar producto por nombre o codigo..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleNameSearch(); }}
            />
            <Button variant="outline" onClick={handleNameSearch}>Buscar</Button>
            <Button variant="ghost" onClick={() => { setSearchInput(''); loadProducts(); }}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Product Grid */}
          <ScrollArea className="h-[calc(100vh-380px)]">
            {loadingProducts ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : products.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2 pr-2">
                {products.map((p) => (
                  <button
                    key={p.id}
                    className={`flex flex-col p-3 rounded-lg border text-left transition-colors min-h-[90px] ${
                      p.stock === 0
                        ? 'bg-gray-100 border-gray-200 opacity-60 cursor-not-allowed'
                        : 'bg-white border-gray-200 hover:border-emerald-400 hover:bg-emerald-50 active:bg-emerald-100 cursor-pointer'
                    }`}
                    onClick={() => p.stock !== 0 && addToCart(p)}
                    disabled={p.stock === 0}
                  >
                    <span className="text-sm font-medium line-clamp-2 leading-tight">{p.descripcion}</span>
                    <span className="text-xs text-muted-foreground mt-1">{p.codigo_principal}</span>
                    <div className="mt-auto flex items-end justify-between pt-1">
                      <span className="text-base font-bold text-emerald-700">${formatCurrency(p.precio_unitario)}</span>
                      {p.stock > 0 ? (
                        <span className="text-xs text-muted-foreground">Stock: {p.stock}</span>
                      ) : (
                        <Badge variant="destructive" className="text-[10px] px-1 py-0">Agotado</Badge>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <ShoppingCart className="h-10 w-10 mx-auto mb-2" />
                <p>No se encontraron productos</p>
              </div>
            )}
          </ScrollArea>
        </div>

        {/* RIGHT PANEL - Cart & Checkout (40%) */}
        <div className="lg:col-span-2">
          <Card className="h-full flex flex-col">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Nueva Venta</CardTitle>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    {activeSession.numero_caja} | {activeSession.user_nombre}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Desde: {formatDateTime(activeSession.fecha_apertura)}
                  </p>
                </div>
              </div>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col gap-3 overflow-hidden">
              {/* Cart Items */}
              <ScrollArea className="flex-1 max-h-[240px]">
                {cart.length > 0 ? (
                  <div className="space-y-2 pr-1">
                    {cart.map((item) => (
                      <div key={item.productId} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium line-clamp-1">{item.descripcion}</p>
                          <p className="text-xs text-muted-foreground">
                            ${formatCurrency(item.precioUnitario)} c/u
                            {item.descuento > 0 && <span className="text-red-500 ml-1">-{item.descuento}%</span>}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <Button size="icon" variant="outline" className="h-7 w-7" onClick={() => updateCartItemQty(item.productId, -1)}>
                              <Minus className="h-3 w-3" />
                            </Button>
                            <span className="text-sm font-medium w-6 text-center">{item.cantidad}</span>
                            <Button size="icon" variant="outline" className="h-7 w-7" onClick={() => updateCartItemQty(item.productId, 1)}>
                              <Plus className="h-3 w-3" />
                            </Button>
                            <Input
                              className="h-7 w-16 text-xs"
                              type="number"
                              placeholder="Desc%"
                              value={item.descuento || ''}
                              onChange={(e) => updateCartItemDiscount(item.productId, Number(e.target.value) || 0)}
                            />
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold">
                            ${formatCurrency(item.cantidad * item.precioUnitario * (1 - item.descuento / 100))}
                          </p>
                          <Button size="icon" variant="ghost" className="h-6 w-6 text-red-500" onClick={() => removeCartItem(item.productId)}>
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <ShoppingCart className="h-8 w-8 mx-auto mb-2" />
                    <p className="text-sm">Carrito vacio</p>
                  </div>
                )}
              </ScrollArea>

              <Separator />

              {/* Totals */}
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal s/imp:</span>
                  <span>${formatCurrency(subtotalSinImpuestos)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">IVA:</span>
                  <span>${formatCurrency(totalIva)}</span>
                </div>
                {totalDescuento > 0 && (
                  <div className="flex justify-between text-sm text-red-600">
                    <span>Descuento:</span>
                    <span>-${formatCurrency(totalDescuento)}</span>
                  </div>
                )}
                <Separator />
                <div className="flex justify-between text-lg font-bold">
                  <span>TOTAL:</span>
                  <span className="text-emerald-700">${formatCurrency(totalConImpuestos)}</span>
                </div>
              </div>

              {/* Client */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Switch checked={useCustomClient} onCheckedChange={setUseCustomClient} />
                  <Label className="text-sm">Cliente personalizado</Label>
                </div>
                {useCustomClient && (
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      className="h-9 text-sm"
                      placeholder="Nombre"
                      value={clientNombre}
                      onChange={(e) => setClientNombre(e.target.value)}
                    />
                    <Input
                      className="h-9 text-sm"
                      placeholder="RUC/CI"
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                    />
                  </div>
                )}
              </div>

              {/* Payment */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Tipo de Venta</Label>
                <div className="grid grid-cols-4 gap-1">
                  {(['efectivo', 'tarjeta', 'credito', 'mixto'] as const).map((tipo) => (
                    <Button
                      key={tipo}
                      size="sm"
                      variant={tipoVenta === tipo ? 'default' : 'outline'}
                      className={`h-10 text-xs ${tipoVenta === tipo ? 'bg-emerald-600 hover:bg-emerald-700' : ''}`}
                      onClick={() => setTipoVenta(tipo)}
                    >
                      {tipo === 'efectivo' && <Banknote className="mr-1 h-3 w-3" />}
                      {tipo === 'tarjeta' && <CreditCard className="mr-1 h-3 w-3" />}
                      {tipo === 'credito' && <Clock className="mr-1 h-3 w-3" />}
                      {tipo === 'mixto' && <DollarSign className="mr-1 h-3 w-3" />}
                      {tipo.charAt(0).toUpperCase() + tipo.slice(1)}
                    </Button>
                  ))}
                </div>

                {tipoVenta === 'efectivo' && (
                  <div className="space-y-1">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs">Efectivo recibido</Label>
                        <Input
                          type="number"
                          step="0.01"
                          className="h-10 text-base"
                          value={montoRecibido}
                          onChange={(e) => setMontoRecibido(e.target.value)}
                          placeholder="0.00"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Cambio</Label>
                        <div className={`h-10 flex items-center px-3 rounded-md border text-base font-bold ${
                          cambio >= 0 && montoRecibidoVal > 0 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-gray-50 text-gray-500'
                        }`}>
                          ${montoRecibidoVal > 0 ? formatCurrency(cambio) : '0.00'}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {tipoVenta === 'tarjeta' && (
                  <div>
                    <Label className="text-xs">Ultimos 4 digitos</Label>
                    <Input
                      maxLength={4}
                      className="h-10"
                      value={last4Digits}
                      onChange={(e) => setLast4Digits(e.target.value.replace(/\D/g, ''))}
                      placeholder="0000"
                    />
                  </div>
                )}

                {tipoVenta === 'mixto' && (
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs">Efectivo</Label>
                      <Input type="number" step="0.01" className="h-10" value={montoEfectivoMixto} onChange={(e) => setMontoEfectivoMixto(e.target.value)} placeholder="0.00" />
                    </div>
                    <div>
                      <Label className="text-xs">Tarjeta</Label>
                      <Input type="number" step="0.01" className="h-10" value={montoTarjeta} onChange={(e) => setMontoTarjeta(e.target.value)} placeholder="0.00" />
                    </div>
                  </div>
                )}

                <div>
                  <Label className="text-xs">Propina ($)</Label>
                  <Input type="number" step="0.01" className="h-9 text-sm" value={propina} onChange={(e) => setPropina(e.target.value)} placeholder="0.00" />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2 pt-2">
                <Button
                  className="w-full h-14 text-lg font-bold bg-emerald-600 hover:bg-emerald-700 min-h-[48px]"
                  disabled={creating || cart.length === 0}
                  onClick={handleCobrar}
                >
                  {creating ? (
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  ) : (
                    <DollarSign className="mr-2 h-5 w-5" />
                  )}
                  COBRAR ${formatCurrency(totalAPagar)}
                </Button>
                <Button variant="outline" className="w-full min-h-[44px]" onClick={clearCart} disabled={cart.length === 0}>
                  <XCircle className="mr-2 h-4 w-4" /> LIMPIAR
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Open Session Dialog (when session is active but want to open new one) */}
      <Dialog open={showOpenSession} onOpenChange={setShowOpenSession}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Abrir Caja</DialogTitle>
            <DialogDescription>Inicie una nueva sesion de caja</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Empresa</Label>
              <Select value={companyId} disabled>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {companies.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Numero de Caja</Label>
              <Input value={sessionForm.numero_caja} onChange={(e) => setSessionForm({ ...sessionForm, numero_caja: e.target.value })} placeholder="CAJA-001" />
            </div>
            <div className="space-y-2">
              <Label>Monto de Apertura ($)</Label>
              <Input type="number" step="0.01" value={sessionForm.monto_apertura} onChange={(e) => setSessionForm({ ...sessionForm, monto_apertura: e.target.value })} placeholder="0.00" />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowOpenSession(false)}>Cancelar</Button>
              <Button onClick={handleOpenSession} disabled={opening} className="bg-emerald-600 hover:bg-emerald-700">
                {opening ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Banknote className="mr-2 h-4 w-4" />}
                Abrir Caja
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Dialog */}
      <ChangeDialog
        open={showChangeDialog}
        onOpenChange={setShowChangeDialog}
        ticket={lastTicket}
        cambio={tipoVenta === 'efectivo' ? cambio : 0}
        company={companies.find((c) => c.id === companyId)}
      />
    </div>
  );
}

// ─── Change/Success Dialog ───────────────────────────────────

function ChangeDialog({
  open,
  onOpenChange,
  ticket,
  cambio,
  company: _company,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ticket: POSTicket | null;
  cambio: number;
  company: Company | undefined;
}) {
  const [showReceipt, setShowReceipt] = useState(false);
  const [receiptText, setReceiptText] = useState('');
  const [loadingReceipt, setLoadingReceipt] = useState(false);

  async function handlePrint() {
    if (!ticket) return;
    setLoadingReceipt(true);
    try {
      const data = await getPOSTicketPrintData(ticket.id);
      const text = formatReceipt(data);
      setReceiptText(text);
      setShowReceipt(true);
    } catch {
      toast.error('Error al obtener datos de impresion');
    } finally {
      setLoadingReceipt(false);
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(receiptText);
    toast.success('Recibo copiado al portapapeles');
  }

  function handleWindowPrint() {
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      // HTML-encode receiptText to prevent XSS from product descriptions, client names, etc.
      const encoded = receiptText
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
      printWindow.document.write(`<pre style="font-family:monospace;font-size:12px;">${encoded}</pre>`);
      printWindow.document.close();
      printWindow.print();
    }
  }

  if (!ticket) return null;

  return (
    <>
      <Dialog open={open && !showReceipt} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-sm text-center">
          <DialogHeader>
            <DialogTitle className="text-emerald-700 flex items-center justify-center gap-2">
              <CheckCircle2 className="h-6 w-6" /> Venta Exitosa
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-lg font-bold">Ticket: {ticket.numero_ticket}</p>
            <p className="text-2xl font-bold text-emerald-700">
              Total: ${formatCurrency(ticket.total_con_impuestos)}
            </p>
            {cambio > 0 && (
              <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                <p className="text-sm text-emerald-600">Cambio</p>
                <p className="text-3xl font-bold text-emerald-700">${formatCurrency(cambio)}</p>
              </div>
            )}
            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={handlePrint} disabled={loadingReceipt}>
                {loadingReceipt ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Printer className="mr-2 h-4 w-4" />}
                Imprimir
              </Button>
              <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Receipt Preview Dialog */}
      <Dialog open={showReceipt} onOpenChange={setShowReceipt}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Vista Previa del Ticket</DialogTitle>
            <DialogDescription>Recibo para impresora termica</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <ScrollArea className="max-h-[400px]">
              <pre className="text-xs font-mono bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">{receiptText}</pre>
            </ScrollArea>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={handleCopy}>
                <Copy className="mr-2 h-4 w-4" /> Copiar
              </Button>
              <Button onClick={handleWindowPrint}>
                <Printer className="mr-2 h-4 w-4" /> Imprimir
              </Button>
              <Button variant="ghost" onClick={() => setShowReceipt(false)}>Cerrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ─── Receipt Formatter ───────────────────────────────────────

function formatReceipt(data: POSTicketPrintData): string {
  const { ticket, company } = data;
  const line = '================================';
  const dash = '--------------------------------';
  const pad = (str: string, len: number, align: 'left' | 'right' = 'left') => {
    const s = str.substring(0, len);
    if (align === 'right') return s.padStart(len);
    return s.padEnd(len);
  };

  let r = '';
  r += line + '\n';
  r += pad(company.nombre_comercial || company.razon_social, 32, 'left').padStart(32 + Math.floor((32 - (company.nombre_comercial || company.razon_social).length) / 2)) + '\n';
  r += pad(`RUC: ${company.ruc}`, 32, 'left') + '\n';
  r += pad(company.dir_matriz.substring(0, 32), 32, 'left') + '\n';
  r += dash + '\n';
  r += `TICKET: ${ticket.numero_ticket}\n`;
  r += `Fecha: ${formatDateTime(ticket.created_at)}\n`;
  r += `Caja: ${ticket.cash_session_id.substring(0, 8)}\n`;
  r += dash + '\n';
  r += `Cliente: ${ticket.cliente_nombre}\n`;
  r += `RUC/CI: ${ticket.cliente_identificacion}\n`;
  r += dash + '\n';
  r += pad('Cant', 4) + pad('Descripcion', 16) + pad('P.Unit', 6, 'right') + pad('Total', 6, 'right') + '\n';
  r += dash + '\n';

  for (const d of ticket.detalles) {
    r += pad(String(d.cantidad), 4);
    r += pad(d.descripcion.substring(0, 16), 16);
    r += pad(d.precio_unitario.toFixed(2), 6, 'right');
    r += pad(d.precio_total_sin_impuestos.toFixed(2), 6, 'right');
    r += '\n';
  }

  r += dash + '\n';
  r += pad('Subtotal:', 24) + pad(ticket.subtotal_sin_impuestos.toFixed(2), 8, 'right') + '\n';
  r += pad(`IVA:`, 24) + pad(ticket.total_iva.toFixed(2), 8, 'right') + '\n';
  if (ticket.total_descuento > 0) {
    r += pad('Descuento:', 24) + pad(ticket.total_descuento.toFixed(2), 8, 'right') + '\n';
  }
  r += dash + '\n';
  r += pad('TOTAL:', 24) + pad(ticket.total_con_impuestos.toFixed(2), 8, 'right') + '\n';
  r += dash + '\n';

  if (ticket.tipo_venta === 'efectivo' || ticket.tipo_venta === 'mixto') {
    r += pad('Efectivo:', 24) + pad(ticket.monto_efectivo.toFixed(2), 8, 'right') + '\n';
    if (ticket.cambio > 0) {
      r += pad('Cambio:', 24) + pad(ticket.cambio.toFixed(2), 8, 'right') + '\n';
    }
  }
  if (ticket.tipo_venta === 'tarjeta' || ticket.tipo_venta === 'mixto') {
    r += pad('Tarjeta:', 24) + pad(ticket.monto_tarjeta.toFixed(2), 8, 'right') + '\n';
    if (ticket.numero_tarjeta) {
      r += pad(`Tarj: ****${ticket.numero_tarjeta}`, 32) + '\n';
    }
  }
  if (ticket.propina > 0) {
    r += pad('Propina:', 24) + pad(ticket.propina.toFixed(2), 8, 'right') + '\n';
  }

  r += line + '\n';
  r += pad('Gracias por su compra!', 32, 'left').padStart(32 + 5) + '\n';
  r += line + '\n';

  return r;
}

// ═════════════════════════════════════════════════════════════
// VIEW 2: ADMIN
// ═════════════════════════════════════════════════════════════

function POSAdminView({
  user: _user,
  companyId,
  companies,
}: {
  user: User;
  companyId: string;
  companies: Company[];
}) {
  return (
    <Tabs defaultValue="sesiones" className="space-y-4">
      <TabsList className="flex flex-wrap h-auto gap-1">
        <TabsTrigger value="sesiones" className="gap-1.5">
          <Banknote className="h-3.5 w-3.5" /><span className="hidden sm:inline">Sesiones de Caja</span>
        </TabsTrigger>
        <TabsTrigger value="arqueo" className="gap-1.5">
          <Receipt className="h-3.5 w-3.5" /><span className="hidden sm:inline">Arqueo de Caja</span>
        </TabsTrigger>
        <TabsTrigger value="tickets" className="gap-1.5">
          <FileText className="h-3.5 w-3.5" /><span className="hidden sm:inline">Tickets</span>
        </TabsTrigger>
        <TabsTrigger value="historial" className="gap-1.5">
          <Clock className="h-3.5 w-3.5" /><span className="hidden sm:inline">Historial</span>
        </TabsTrigger>
      </TabsList>
      <TabsContent value="sesiones"><SesionesTab companyId={companyId} companies={companies} /></TabsContent>
      <TabsContent value="arqueo"><ArqueoTab companyId={companyId} /></TabsContent>
      <TabsContent value="tickets"><TicketsTab companyId={companyId} /></TabsContent>
      <TabsContent value="historial"><HistorialTab companyId={companyId} /></TabsContent>
    </Tabs>
  );
}

// ─── Tab 1: Sesiones de Caja ────────────────────────────────

function SesionesTab({ companyId, companies }: { companyId: string; companies: Company[] }) {
  const [sessions, setSessions] = useState<POSCashSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOpenDialog, setShowOpenDialog] = useState(false);
  const [showCloseDialog, setShowCloseDialog] = useState<POSCashSession | null>(null);
  const [showDetailDialog, setShowDetailDialog] = useState<POSCashSessionResumen | null>(null);
  const [opening, setOpening] = useState(false);
  const [closing, setClosing] = useState(false);
  const [sessionForm, setSessionForm] = useState({ numero_caja: 'CAJA-001', monto_apertura: '0.00' });
  const [closeForm, setCloseForm] = useState({ monto_cierre_efectivo: '', observaciones_cierre: '' });
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getPOSSessions({ company_id: companyId });
      setSessions(data);
    } catch {
      toast.error('Error al cargar sesiones');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleOpen() {
    if (!sessionForm.numero_caja || !sessionForm.monto_apertura) {
      toast.error('Complete todos los campos');
      return;
    }
    setOpening(true);
    try {
      await openPOSSession({
        company_id: companyId,
        numero_caja: sessionForm.numero_caja,
        monto_apertura: Number(sessionForm.monto_apertura),
      });
      toast.success('Caja abierta');
      setShowOpenDialog(false);
      setSessionForm({ numero_caja: 'CAJA-001', monto_apertura: '0.00' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al abrir caja');
    } finally {
      setOpening(false);
    }
  }

  async function handleClose() {
    if (!showCloseDialog || !closeForm.monto_cierre_efectivo) {
      toast.error('Ingrese el monto de cierre');
      return;
    }
    setClosing(true);
    try {
      await closePOSSession(showCloseDialog.id, {
        monto_cierre_efectivo: Number(closeForm.monto_cierre_efectivo),
        observaciones_cierre: closeForm.observaciones_cierre || undefined,
      });
      toast.success('Caja cerrada');
      setShowCloseDialog(null);
      setCloseForm({ monto_cierre_efectivo: '', observaciones_cierre: '' });
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al cerrar caja');
    } finally {
      setClosing(false);
    }
  }

  async function handleViewDetail(sessionId: string) {
    setLoadingDetail(true);
    try {
      const resumen = await getPOSSessionResumen(sessionId);
      setShowDetailDialog(resumen);
    } catch {
      toast.error('Error al cargar detalle');
    } finally {
      setLoadingDetail(false);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => setShowOpenDialog(true)}>
          <Plus className="mr-2 h-4 w-4" /> Abrir Caja
        </Button>
      </div>

      {sessions.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Caja</TableHead>
                    <TableHead>Cajero</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Apertura</TableHead>
                    <TableHead className="text-right">Monto Apertura</TableHead>
                    <TableHead className="text-right">Total Ventas</TableHead>
                    <TableHead>Cierre</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-mono text-xs">{s.numero_caja}</TableCell>
                      <TableCell className="text-xs">{s.user_nombre}</TableCell>
                      <TableCell>
                        <Badge variant={s.estado === 'abierta' ? 'default' : 'secondary'} className={s.estado === 'abierta' ? 'bg-emerald-600' : ''}>
                          {s.estado.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">{formatDateTime(s.fecha_apertura)}</TableCell>
                      <TableCell className="text-right">${formatCurrency(s.monto_apertura)}</TableCell>
                      <TableCell className="text-right font-medium">${formatCurrency(s.total_ventas)}</TableCell>
                      <TableCell className="text-xs">{s.fecha_cierre ? formatDateTime(s.fecha_cierre) : '-'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="outline" onClick={() => handleViewDetail(s.id)} disabled={loadingDetail}>
                            <Eye className="h-3 w-3" />
                          </Button>
                          {s.estado === 'abierta' && (
                            <Button size="sm" variant="outline" className="text-red-600" onClick={() => { setShowCloseDialog(s); setCloseForm({ monto_cierre_efectivo: '', observaciones_cierre: '' }); }}>
                              Cerrar
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
            <Banknote className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin sesiones de caja</h3>
          </CardContent>
        </Card>
      )}

      {/* Open Session Dialog */}
      <Dialog open={showOpenDialog} onOpenChange={setShowOpenDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Abrir Caja</DialogTitle>
            <DialogDescription>Inicie una nueva sesion de caja</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Empresa</Label>
              <Select value={companyId} disabled>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {companies.map((c) => (<SelectItem key={c.id} value={c.id}>{c.razon_social}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Numero de Caja</Label>
              <Input value={sessionForm.numero_caja} onChange={(e) => setSessionForm({ ...sessionForm, numero_caja: e.target.value })} placeholder="CAJA-001" />
            </div>
            <div className="space-y-2">
              <Label>Monto de Apertura ($)</Label>
              <Input type="number" step="0.01" value={sessionForm.monto_apertura} onChange={(e) => setSessionForm({ ...sessionForm, monto_apertura: e.target.value })} placeholder="0.00" />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowOpenDialog(false)}>Cancelar</Button>
              <Button onClick={handleOpen} disabled={opening} className="bg-emerald-600 hover:bg-emerald-700">
                {opening ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Banknote className="mr-2 h-4 w-4" />}
                Abrir Caja
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Close Session Dialog */}
      <Dialog open={!!showCloseDialog} onOpenChange={(o) => !o && setShowCloseDialog(null)}>
        <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Cerrar Caja</DialogTitle>
            <DialogDescription>
              Cerrar sesion {showCloseDialog?.numero_caja}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {showCloseDialog && (
              <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                <div className="flex justify-between"><span>Total ventas:</span><span className="font-medium">${formatCurrency(showCloseDialog.total_ventas)}</span></div>
                <div className="flex justify-between"><span>Ventas efectivo:</span><span>${formatCurrency(showCloseDialog.total_ventas_efectivo)}</span></div>
                <div className="flex justify-between"><span>Ventas tarjeta:</span><span>${formatCurrency(showCloseDialog.total_ventas_tarjeta)}</span></div>
                <div className="flex justify-between"><span>Propinas:</span><span>${formatCurrency(showCloseDialog.total_propina)}</span></div>
              </div>
            )}
            <div className="space-y-2">
              <Label>Monto de Cierre - Efectivo Contado ($)</Label>
              <Input type="number" step="0.01" value={closeForm.monto_cierre_efectivo} onChange={(e) => setCloseForm({ ...closeForm, monto_cierre_efectivo: e.target.value })} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <Label>Observaciones</Label>
              <Textarea value={closeForm.observaciones_cierre} onChange={(e) => setCloseForm({ ...closeForm, observaciones_cierre: e.target.value })} rows={2} />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCloseDialog(null)}>Cancelar</Button>
              <Button onClick={handleClose} disabled={closing} variant="destructive">
                {closing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <XCircle className="mr-2 h-4 w-4" />}
                Cerrar Caja
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Session Detail Dialog */}
      <Dialog open={!!showDetailDialog} onOpenChange={(o) => !o && setShowDetailDialog(null)}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Detalle de Sesion</DialogTitle>
          </DialogHeader>
          {showDetailDialog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Caja:</span> <span className="font-medium">{showDetailDialog.session.numero_caja}</span></div>
                <div><span className="text-muted-foreground">Cajero:</span> <span className="font-medium">{showDetailDialog.session.user_nombre}</span></div>
                <div><span className="text-muted-foreground">Apertura:</span> <span className="font-medium">{formatDateTime(showDetailDialog.session.fecha_apertura)}</span></div>
                <div><span className="text-muted-foreground">Monto Apertura:</span> <span className="font-medium">${formatCurrency(showDetailDialog.session.monto_apertura)}</span></div>
                <div><span className="text-muted-foreground">Total Ventas:</span> <span className="font-medium">${formatCurrency(showDetailDialog.session.total_ventas)}</span></div>
                <div><span className="text-muted-foreground">Total Tickets:</span> <span className="font-medium">{showDetailDialog.total_tickets}</span></div>
              </div>

              {Object.keys(showDetailDialog.tickets_por_tipo).length > 0 && (
                <div>
                  <Label className="text-sm">Ventas por Tipo</Label>
                  <div className="flex gap-2 mt-1">
                    {Object.entries(showDetailDialog.tickets_por_tipo).map(([tipo, count]) => (
                      <Badge key={tipo} variant="secondary">{tipo}: {count as number}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {showDetailDialog.ultimos_tickets.length > 0 && (
                <div>
                  <Label className="text-sm mb-2 block">Ultimos Tickets</Label>
                  <div className="space-y-1">
                    {showDetailDialog.ultimos_tickets.map((t) => (
                      <div key={t.id} className="flex justify-between items-center text-sm bg-gray-50 rounded px-2 py-1">
                        <span className="font-mono text-xs">{t.numero_ticket}</span>
                        {getTipoVentaBadge(t.tipo_venta)}
                        <span className="font-medium">${formatCurrency(t.total_con_impuestos)}</span>
                        {getTicketEstadoBadge(t.estado)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Tab 2: Arqueo de Caja ──────────────────────────────────

function ArqueoTab({ companyId }: { companyId: string }) {
  const [openSessions, setOpenSessions] = useState<POSCashSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Denomination counters
  const BILLETES = [100, 50, 20, 10, 5, 1];
  const MONEDAS = [1.0, 0.5, 0.25, 0.10, 0.05, 0.01];

  const [billeteCounts, setBilleteCounts] = useState<Record<string, number>>({});
  const [monedaCounts, setMonedaCounts] = useState<Record<string, number>>({});
  const [observaciones, setObservaciones] = useState('');
  const [montoCierreEfectivo, setMontoCierreEfectivo] = useState('');

  const totalBilletes = BILLETES.reduce((sum, den) => sum + (billeteCounts[String(den)] || 0) * den, 0);
  const totalMonedas = MONEDAS.reduce((sum, den) => sum + (monedaCounts[String(den)] || 0) * den, 0);
  const totalEfectivoContado = totalBilletes + totalMonedas;

  const selectedSession = openSessions.find((s) => s.id === selectedSessionId);
  const totalEfectivoCalculado = selectedSession?.total_ventas_efectivo || 0;
  const diferencia = totalEfectivoContado - totalEfectivoCalculado;

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getPOSSessions({ company_id: companyId, estado: 'abierta' });
      setOpenSessions(data);
      if (data.length > 0 && !selectedSessionId) {
        setSelectedSessionId(data[0].id);
      }
    } catch {
      toast.error('Error al cargar sesiones');
    } finally {
      setLoading(false);
    }
  }, [companyId, selectedSessionId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleArqueo(tipo: 'parcial' | 'final') {
    if (!selectedSessionId) {
      toast.error('Seleccione una sesion');
      return;
    }
    setSaving(true);
    try {
      const arqueoData: POSArqueoCreate = {
        cash_session_id: selectedSessionId,
        tipo,
        billetes: billeteCounts,
        monedas: monedaCounts,
        total_efectivo_contado: totalEfectivoContado,
        observaciones: observaciones || undefined,
      };
      if (tipo === 'final') {
        arqueoData.monto_cierre_efectivo = Number(montoCierreEfectivo) || totalEfectivoContado;
        arqueoData.observaciones_cierre = observaciones || undefined;
      }
      await createPOSArqueo(arqueoData);
      toast.success(tipo === 'parcial' ? 'Arqueo parcial guardado' : 'Caja cerrada con arqueo final');
      setBilleteCounts({});
      setMonedaCounts({});
      setObservaciones('');
      setMontoCierreEfectivo('');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al guardar arqueo');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  if (openSessions.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Receipt className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
          <h3 className="text-lg font-medium">No hay cajas abiertas</h3>
          <p className="text-sm text-muted-foreground">Abra una caja primero para realizar arqueos</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Session Selector */}
      <div className="flex items-center gap-3">
        <Label>Sesion de Caja:</Label>
        <Select value={selectedSessionId} onValueChange={setSelectedSessionId}>
          <SelectTrigger className="w-[250px]">
            <SelectValue placeholder="Seleccione sesion" />
          </SelectTrigger>
          <SelectContent>
            {openSessions.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.numero_caja} - {s.user_nombre}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedSession && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Billetes */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Billetes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {BILLETES.map((den) => (
                <div key={den} className="flex items-center gap-3">
                  <span className="w-16 text-sm font-medium">${den}</span>
                  <span className="text-muted-foreground text-sm">x</span>
                  <Input
                    type="number"
                    min="0"
                    className="h-9 w-20"
                    value={billeteCounts[String(den)] || ''}
                    onChange={(e) => setBilleteCounts({ ...billeteCounts, [String(den)]: Number(e.target.value) || 0 })}
                  />
                  <span className="text-sm text-muted-foreground w-20 text-right">
                    = ${formatCurrency((billeteCounts[String(den)] || 0) * den)}
                  </span>
                </div>
              ))}
              <Separator />
              <div className="flex justify-between font-medium">
                <span>Total Billetes:</span>
                <span>${formatCurrency(totalBilletes)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Monedas */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Monedas</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {MONEDAS.map((den) => (
                <div key={den} className="flex items-center gap-3">
                  <span className="w-16 text-sm font-medium">${den.toFixed(2)}</span>
                  <span className="text-muted-foreground text-sm">x</span>
                  <Input
                    type="number"
                    min="0"
                    className="h-9 w-20"
                    value={monedaCounts[String(den)] || ''}
                    onChange={(e) => setMonedaCounts({ ...monedaCounts, [String(den)]: Number(e.target.value) || 0 })}
                  />
                  <span className="text-sm text-muted-foreground w-20 text-right">
                    = ${formatCurrency((monedaCounts[String(den)] || 0) * den)}
                  </span>
                </div>
              ))}
              <Separator />
              <div className="flex justify-between font-medium">
                <span>Total Monedas:</span>
                <span>${formatCurrency(totalMonedas)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Resumen */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Resumen del Arqueo</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span>Total Billetes:</span>
                  <span>${formatCurrency(totalBilletes)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Monedas:</span>
                  <span>${formatCurrency(totalMonedas)}</span>
                </div>
                <Separator />
                <div className="flex justify-between font-medium">
                  <span>Efectivo Contado:</span>
                  <span>${formatCurrency(totalEfectivoContado)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Efectivo Calculado (Sistema):</span>
                  <span>${formatCurrency(totalEfectivoCalculado)}</span>
                </div>
                <Separator />
                <div className={`flex justify-between font-bold text-base ${diferencia >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  <span>{diferencia >= 0 ? 'Sobrante:' : 'Faltante:'}</span>
                  <span>${formatCurrency(Math.abs(diferencia))}</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-sm">Observaciones</Label>
                <Textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} rows={2} />
              </div>

              <div className="space-y-2">
                <Label className="text-sm">Monto Cierre Efectivo ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={montoCierreEfectivo}
                  onChange={(e) => setMontoCierreEfectivo(e.target.value)}
                  placeholder={totalEfectivoContado.toFixed(2)}
                />
              </div>

              <div className="flex gap-2">
                <Button variant="outline" className="flex-1 min-h-[44px]" onClick={() => handleArqueo('parcial')} disabled={saving}>
                  {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Arqueo Parcial
                </Button>
                <Button className="flex-1 bg-emerald-600 hover:bg-emerald-700 min-h-[44px]" onClick={() => handleArqueo('final')} disabled={saving}>
                  {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Cerrar Caja
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─── Tab 3: Tickets ─────────────────────────────────────────

function TicketsTab({ companyId }: { companyId: string }) {
  const [tickets, setTickets] = useState<POSTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEstado, setFilterEstado] = useState<string>('all');
  const [filterSession, setFilterSession] = useState<string>('all');
  const [sessions, setSessions] = useState<POSCashSession[]>([]);
  const [showDetail, setShowDetail] = useState<POSTicket | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showReceipt, setShowReceipt] = useState(false);
  const [receiptText, setReceiptText] = useState('');
  const [loadingReceipt, setLoadingReceipt] = useState(false);
  const [voiding, setVoiding] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [tData, sData] = await Promise.all([
        getPOSTickets({ company_id: companyId }),
        getPOSSessions({ company_id: companyId }),
      ]);
      setTickets(tData);
      setSessions(sData);
    } catch {
      toast.error('Error al cargar tickets');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleViewDetail(ticketId: string) {
    setLoadingDetail(true);
    try {
      const ticket = await getPOSTicket(ticketId);
      setShowDetail(ticket);
    } catch {
      toast.error('Error al cargar detalle');
    } finally {
      setLoadingDetail(false);
    }
  }

  async function handleVoid(ticketId: string) {
    setVoiding(ticketId);
    try {
      await voidPOSTicket(ticketId);
      toast.success('Ticket anulado');
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al anular ticket');
    } finally {
      setVoiding(null);
    }
  }

  async function handlePrint(ticketId: string) {
    setLoadingReceipt(true);
    try {
      const data = await getPOSTicketPrintData(ticketId);
      const text = formatReceipt(data);
      setReceiptText(text);
      setShowReceipt(true);
    } catch {
      toast.error('Error al obtener datos de impresion');
    } finally {
      setLoadingReceipt(false);
    }
  }

  function handleCopyReceipt() {
    navigator.clipboard.writeText(receiptText);
    toast.success('Recibo copiado');
  }

  function handleWindowPrint() {
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      // HTML-encode receiptText to prevent XSS from product descriptions, client names, etc.
      const encoded = receiptText
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
      printWindow.document.write(`<pre style="font-family:monospace;font-size:12px;">${encoded}</pre>`);
      printWindow.document.close();
      printWindow.print();
    }
  }

  const filteredTickets = tickets.filter((t) => {
    if (filterEstado !== 'all' && t.estado !== filterEstado) return false;
    if (filterSession !== 'all' && t.cash_session_id !== filterSession) return false;
    return true;
  });

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
        <Select value={filterEstado} onValueChange={setFilterEstado}>
          <SelectTrigger className="w-[150px]"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="pagado">Pagado</SelectItem>
            <SelectItem value="pendiente">Pendiente</SelectItem>
            <SelectItem value="anulado">Anulado</SelectItem>
            <SelectItem value="devuelto">Devuelto</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterSession} onValueChange={setFilterSession}>
          <SelectTrigger className="w-[200px]"><SelectValue placeholder="Sesion" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las sesiones</SelectItem>
            {sessions.map((s) => (
              <SelectItem key={s.id} value={s.id}>{s.numero_caja} - {s.user_nombre}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {filteredTickets.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ticket</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Tipo Venta</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTickets.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="font-mono text-xs">{t.numero_ticket}</TableCell>
                      <TableCell className="text-xs">{t.cliente_nombre}</TableCell>
                      <TableCell>{getTipoVentaBadge(t.tipo_venta)}</TableCell>
                      <TableCell className="text-right font-medium">${formatCurrency(t.total_con_impuestos)}</TableCell>
                      <TableCell>{getTicketEstadoBadge(t.estado)}</TableCell>
                      <TableCell className="text-xs">{formatDateTime(t.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="outline" onClick={() => handleViewDetail(t.id)} disabled={loadingDetail}>
                            <Eye className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handlePrint(t.id)} disabled={loadingReceipt}>
                            <Printer className="h-3 w-3" />
                          </Button>
                          {t.estado === 'pagado' && (
                            <Button size="sm" variant="outline" className="text-red-600" onClick={() => handleVoid(t.id)} disabled={voiding === t.id}>
                              {voiding === t.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Ban className="h-3 w-3" />}
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
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin tickets</h3>
          </CardContent>
        </Card>
      )}

      {/* Ticket Detail Dialog */}
      <Dialog open={!!showDetail} onOpenChange={(o) => !o && setShowDetail(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Detalle del Ticket {showDetail?.numero_ticket}</DialogTitle>
          </DialogHeader>
          {showDetail && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-muted-foreground">Cliente:</span> {showDetail.cliente_nombre}</div>
                <div><span className="text-muted-foreground">Identificacion:</span> {showDetail.cliente_identificacion}</div>
                <div><span className="text-muted-foreground">Tipo Venta:</span> {getTipoVentaBadge(showDetail.tipo_venta)}</div>
                <div><span className="text-muted-foreground">Estado:</span> {getTicketEstadoBadge(showDetail.estado)}</div>
                <div><span className="text-muted-foreground">Fecha:</span> {formatDateTime(showDetail.created_at)}</div>
                {showDetail.numero_tarjeta && (
                  <div><span className="text-muted-foreground">Tarjeta:</span> ****{showDetail.numero_tarjeta}</div>
                )}
              </div>

              <div>
                <Label className="text-sm mb-2 block">Items</Label>
                <div className="space-y-1">
                  {showDetail.detalles.map((d) => (
                    <div key={d.id} className="flex justify-between text-sm bg-gray-50 rounded px-2 py-1">
                      <span>{d.cantidad}x {d.descripcion}</span>
                      <span className="font-medium">${formatCurrency(d.precio_total_sin_impuestos + d.iva_valor)}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span>Subtotal:</span><span>${formatCurrency(showDetail.subtotal_sin_impuestos)}</span></div>
                <div className="flex justify-between"><span>IVA:</span><span>${formatCurrency(showDetail.total_iva)}</span></div>
                {showDetail.total_descuento > 0 && (
                  <div className="flex justify-between text-red-600"><span>Descuento:</span><span>-${formatCurrency(showDetail.total_descuento)}</span></div>
                )}
                <Separator />
                <div className="flex justify-between font-bold text-base"><span>TOTAL:</span><span className="text-emerald-700">${formatCurrency(showDetail.total_con_impuestos)}</span></div>
                {showDetail.propina > 0 && (
                  <div className="flex justify-between"><span>Propina:</span><span>${formatCurrency(showDetail.propina)}</span></div>
                )}
                {showDetail.cambio > 0 && (
                  <div className="flex justify-between"><span>Cambio:</span><span>${formatCurrency(showDetail.cambio)}</span></div>
                )}
              </div>

              {showDetail.observaciones && (
                <div className="text-sm"><span className="text-muted-foreground">Observaciones:</span> {showDetail.observaciones}</div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Receipt Preview Dialog */}
      <Dialog open={showReceipt} onOpenChange={setShowReceipt}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Vista Previa del Ticket</DialogTitle>
            <DialogDescription>Recibo para impresora termica</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <ScrollArea className="max-h-[400px]">
              <pre className="text-xs font-mono bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">{receiptText}</pre>
            </ScrollArea>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={handleCopyReceipt}>
                <Copy className="mr-2 h-4 w-4" /> Copiar
              </Button>
              <Button onClick={handleWindowPrint}>
                <Printer className="mr-2 h-4 w-4" /> Imprimir
              </Button>
              <Button variant="ghost" onClick={() => setShowReceipt(false)}>Cerrar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Tab 4: Historial ───────────────────────────────────────

function HistorialTab({ companyId }: { companyId: string }) {
  const [sessions, setSessions] = useState<POSCashSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [sessionTickets, setSessionTickets] = useState<POSTicket[]>([]);
  const [loadingTickets, setLoadingTickets] = useState(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const data = await getPOSSessions({ company_id: companyId });
      // Show closed sessions first, then open
      setSessions(data.sort((a, b) => {
        if (a.estado === 'cerrada' && b.estado === 'abierta') return -1;
        if (a.estado === 'abierta' && b.estado === 'cerrada') return 1;
        return new Date(b.fecha_apertura).getTime() - new Date(a.fecha_apertura).getTime();
      }));
    } catch {
      toast.error('Error al cargar historial');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleExpand(sessionId: string) {
    if (expandedSession === sessionId) {
      setExpandedSession(null);
      return;
    }
    setExpandedSession(sessionId);
    setLoadingTickets(true);
    try {
      const tickets = await getPOSTickets({ session_id: sessionId });
      setSessionTickets(tickets);
    } catch {
      toast.error('Error al cargar tickets');
    } finally {
      setLoadingTickets(false);
    }
  }

  const closedSessions = sessions.filter((s) => s.estado === 'cerrada');
  const openSessions = sessions.filter((s) => s.estado === 'abierta');

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* Open Sessions Summary */}
      {openSessions.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-emerald-700 mb-2">Sesiones Abiertas</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {openSessions.map((s) => (
              <Card key={s.id} className="border-emerald-200">
                <CardContent className="p-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{s.numero_caja}</p>
                      <p className="text-xs text-muted-foreground">{s.user_nombre}</p>
                      <p className="text-xs text-muted-foreground">Desde: {formatDateTime(s.fecha_apertura)}</p>
                    </div>
                    <div className="text-right">
                      <Badge className="bg-emerald-600">ABIERTA</Badge>
                      <p className="text-sm font-bold mt-1">${formatCurrency(s.total_ventas)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Closed Sessions */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Sesiones Cerradas</h3>
        {closedSessions.length > 0 ? (
          <div className="space-y-2">
            {closedSessions.map((s) => (
              <Card key={s.id}>
                <CardContent className="p-0">
                  <button
                    className="w-full p-3 flex items-center justify-between text-left"
                    onClick={() => handleExpand(s.id)}
                  >
                    <div>
                      <p className="font-medium">{s.numero_caja} - {s.user_nombre}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(s.fecha_apertura)} → {s.fecha_cierre ? formatDateTime(s.fecha_cierre) : '-'}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="text-sm font-bold">${formatCurrency(s.total_ventas)}</p>
                        {s.monto_diferencia !== null && s.monto_diferencia !== 0 && (
                          <p className={`text-xs font-medium ${s.monto_diferencia >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            Dif: ${formatCurrency(s.monto_diferencia)}
                          </p>
                        )}
                      </div>
                      {expandedSession === s.id ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </div>
                  </button>
                  {expandedSession === s.id && (
                    <div className="border-t p-3 bg-gray-50">
                      {loadingTickets ? (
                        <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin" /></div>
                      ) : sessionTickets.length > 0 ? (
                        <div className="space-y-1">
                          <div className="grid grid-cols-4 gap-2 text-xs font-medium text-muted-foreground mb-1">
                            <span>Ticket</span>
                            <span>Tipo</span>
                            <span className="text-right">Total</span>
                            <span>Estado</span>
                          </div>
                          {sessionTickets.map((t) => (
                            <div key={t.id} className="grid grid-cols-4 gap-2 text-sm">
                              <span className="font-mono text-xs">{t.numero_ticket}</span>
                              <span>{getTipoVentaBadge(t.tipo_venta)}</span>
                              <span className="text-right font-medium">${formatCurrency(t.total_con_impuestos)}</span>
                              <span>{getTicketEstadoBadge(t.estado)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center">Sin tickets</p>
                      )}

                      {/* Session summary */}
                      <div className="mt-3 pt-3 border-t text-sm space-y-1">
                        <div className="flex justify-between"><span>Ventas efectivo:</span><span>${formatCurrency(s.total_ventas_efectivo)}</span></div>
                        <div className="flex justify-between"><span>Ventas tarjeta:</span><span>${formatCurrency(s.total_ventas_tarjeta)}</span></div>
                        <div className="flex justify-between"><span>Ventas credito:</span><span>${formatCurrency(s.total_ventas_credito)}</span></div>
                        <div className="flex justify-between"><span>Propinas:</span><span>${formatCurrency(s.total_propina)}</span></div>
                        <div className="flex justify-between font-medium"><span>Total:</span><span>${formatCurrency(s.total_ventas)}</span></div>
                        {s.monto_cierre_efectivo !== null && (
                          <div className="flex justify-between"><span>Cierre efectivo:</span><span>${formatCurrency(s.monto_cierre_efectivo)}</span></div>
                        )}
                        {s.monto_diferencia !== null && s.monto_diferencia !== 0 && (
                          <div className={`flex justify-between font-medium ${s.monto_diferencia >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            <span>{s.monto_diferencia >= 0 ? 'Sobrante' : 'Faltante'}:</span>
                            <span>${formatCurrency(Math.abs(s.monto_diferencia))}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <h3 className="text-lg font-medium">Sin historial</h3>
              <p className="text-sm text-muted-foreground">Las sesiones cerradas apareceran aqui</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
