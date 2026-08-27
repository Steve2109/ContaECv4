'use client';

import { Component, useState, useEffect, useCallback, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
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
  Receipt,
  Plus,
  Loader2,
  RefreshCw,
  Trash2,
  Pencil,
  Search,
  Package,
  Users,
  FileText,
  Check,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Send,
  Eye,
  FileDown,
  AlertTriangle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Shield,
  X,
  Info,
  Mail,
  Zap,
  Download,
  ArrowRightLeft,
  History,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getComprobantes,
  getComprobante,
  createComprobante,
  firmarComprobante,
  enviarComprobanteSRI,
  consultarComprobanteSRI,
  recuperarComprobanteSRI,
  getComprobanteXML,
  deleteComprobante,
  getComprobanteStats,
  downloadRIDE,
  enviarComprobanteEmail,
  procesarComprobante,
  validarComprobante,
  corregirComprobante,
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  getClients,
  createClient,
  updateClient,
  deleteClient,
  getSRICatalogs,
  getProformas,
  getProforma,
  createProforma,
  deleteProforma,
  getProformaStats,
  enviarProforma,
  convertirProforma,
  downloadProformaPDF,
  type ComprobanteDetalleCreate,
  type ComprobanteCreate,
  type ComprobanteListResponse,
  type ComprobanteStatsResponse,
  type ComprobanteResponse,
  type ProductResponse,
  type ProductCreate,
  type ClientResponse,
  type ClientCreate,
  type Company,
  type SRICatalog,
  type ValidationResult,
  type ProformaDetalleCreate,
  type ProformaCreate,
  type ProformaResponse,
  type ProformaListResponse,
  type ProformaStatsResponse,
} from '@/lib/api';

// ─── SRI Reference Data ─────────────────────────────────────────

const TIPOS_COMPROBANTE: { codigo: string; descripcion: string }[] = [
  { codigo: '01', descripcion: 'Factura' },
  { codigo: '03', descripcion: 'Liquidación de Compra' },
  { codigo: '04', descripcion: 'Nota de Crédito' },
  { codigo: '05', descripcion: 'Nota de Débito' },
  { codigo: '06', descripcion: 'Guia de Remision' },
  { codigo: '07', descripcion: 'Comprobante de Retención' },
];

const TIPOS_IDENTIFICACION: { codigo: string; descripcion: string }[] = [
  { codigo: '04', descripcion: 'RUC' },
  { codigo: '05', descripcion: 'Cédula' },
  { codigo: '06', descripcion: 'Pasaporte' },
  { codigo: '07', descripcion: 'Consumidor Final' },
  { codigo: '08', descripcion: 'Identificación Exterior' },
];

// Tabla 23 del SRI - Formas de pago válidas (01, 15-21). Los códigos 02-06 no existen
// en el SRI y provocaban el error "Código de forma de pago inválido: '05'" al validar.
const FORMAS_PAGO: { codigo: string; descripcion: string }[] = [
  { codigo: '01', descripcion: 'Sin utilización del sistema financiero' },
  { codigo: '15', descripcion: 'Compensación de deudas' },
  { codigo: '16', descripcion: 'Tarjeta de débito' },
  { codigo: '17', descripcion: 'Dinero electrónico' },
  { codigo: '18', descripcion: 'Tarjeta prepago' },
  { codigo: '19', descripcion: 'Tarjeta de crédito' },
  { codigo: '20', descripcion: 'Otros con utilización del sistema financiero' },
  { codigo: '21', descripcion: 'Endoso de títulos' },
];

const IVA_RATES: { codigo: string; porcentaje: number; descripcion: string }[] = [
  { codigo: '0', porcentaje: 0, descripcion: '0%' },
  { codigo: '5', porcentaje: 5, descripcion: '5%' },
  { codigo: '8', porcentaje: 8, descripcion: '8%' },
  { codigo: '2', porcentaje: 12, descripcion: '12%' },
  { codigo: '10', porcentaje: 13, descripcion: '13%' },
  { codigo: '3', porcentaje: 14, descripcion: '14%' },
  { codigo: '4', porcentaje: 15, descripcion: '15%' },
  { codigo: '6', porcentaje: 0, descripcion: 'No objeto de IVA' },
  { codigo: '7', porcentaje: 0, descripcion: 'Exento de IVA' },
];

function getTipoComprobanteLabel(codigo: string): string {
  return TIPOS_COMPROBANTE.find((t) => t.codigo === codigo)?.descripcion || codigo;
}

function getEstadoBadge(estado: string) {
  switch (estado.toUpperCase()) {
    case 'BORRADOR':
      return <Badge variant="secondary">Borrador</Badge>;
    case 'FIRMADO':
      return <Badge className="bg-sky-600 hover:bg-sky-700">Firmado</Badge>;
    case 'ENVIADO':
      return <Badge className="bg-amber-500 hover:bg-amber-600">Enviado</Badge>;
    case 'AUTORIZADO':
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">Autorizado</Badge>;
    case 'RECHAZADO':
      return <Badge variant="destructive">Rechazado</Badge>;
    case 'CONTINGENCIA':
      return <Badge className="bg-orange-500 hover:bg-orange-600">Contingencia</Badge>;
    default:
      return <Badge variant="outline">{estado}</Badge>;
  }
}

function formatCurrency(amount: number | null | undefined): string {
  return (Number(amount) || 0).toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Formatea un valor numérico como texto editable: separador de miles con punto
 * y decimales con coma (formato es-EC). Ej: 5863 → "5.863,00"
 */
function formatPriceDisplay(value: number): string {
  if (value === null || value === undefined || isNaN(value)) return '';
  return value.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Input de precio que acepta punto O coma como separador decimal y coloca
 * automáticamente el punto de miles. Almacena el valor numérico real.
 */
function PriceInput({
  value,
  onChange,
  placeholder,
  className,
  disabled,
}: {
  value: number;
  onChange: (v: number) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}) {
  const [text, setText] = useState<string>('');

  // Sincronizar el texto cuando el valor cambia externamente
  useEffect(() => {
    setText(value ? formatPriceDisplay(value) : '');
  }, [value]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    let raw = e.target.value;
    // Punto → coma (separador decimal): el usuario puede escribir punto o coma
    raw = raw.replace(/\./g, ',').replace(/[^\d,]/g, '');
    // Permitir solo una coma (decimales)
    const firstComma = raw.indexOf(',');
    if (firstComma !== -1) {
      raw = raw.slice(0, firstComma + 1) + raw.slice(firstComma + 1).replace(/,/g, '');
    }
    // Punto de miles automático (cada 3 dígitos en la parte entera)
    const [intPart, decPart] = raw.split(',');
    const groupedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    const display = decPart !== undefined ? `${groupedInt},${decPart}` : groupedInt;
    setText(display);
    // Valor numérico: quitar puntos de miles, coma → punto decimal
    const normalized = display.replace(/\./g, '').replace(',', '.');
    onChange(parseFloat(normalized) || 0);
  }

  return (
    <Input
      inputMode="decimal"
      type="text"
      value={text}
      onChange={handleChange}
      placeholder={placeholder ?? '0,00'}
      className={className}
      disabled={disabled}
    />
  );
}

type DescuentoTipo = 'porcentaje' | 'dolares';

type DetalleConDescuento = {
 cantidad: number;
 precio_unitario: number;
 descuento?: number;
 descuento_tipo?: DescuentoTipo;
 descuento_valor?: number;
 iva_codigo?: string;
 iva_porcentaje: number;
 ice_porcentaje?: number | null;
 irbpnr_valor?: number;
};

/**
 * Calcula el monto de descuento EFECTIVO de una línea:
 * - 'porcentaje': % del total de la línea (cantidad * precio_unitario)
 * - 'dolares' (o sin tipo): monto fijo
 */
function getItemDiscount(item: DetalleConDescuento): number {
 if (item.descuento_tipo === 'porcentaje' && item.descuento_valor != null && item.descuento_valor > 0) {
 return (item.cantidad * item.precio_unitario * item.descuento_valor) / 100;
 }
 return item.descuento || 0;
}

function getItemSubtotal(item: DetalleConDescuento): number {
 return item.cantidad * item.precio_unitario - getItemDiscount(item);
}

/**
 * Calcula el desglose completo de totales de un documento en formato SRI:
 * subtotales por tarifa de IVA, descuento, IVA, ICE, IRBPNR, propina y valor total.
 */
function computeTotales(items: DetalleConDescuento[]) {
 let subtotal_sin_impuestos = 0;
 let subtotal_iva_0 = 0, subtotal_iva_5 = 0, subtotal_iva_8 = 0, subtotal_iva_12 = 0;
 let subtotal_iva_13 = 0, subtotal_iva_14 = 0, subtotal_iva_15 = 0;
 let subtotal_no_objeto_iva = 0, subtotal_exento_iva = 0;
 let total_iva = 0, total_ice = 0, total_descuento = 0, total_irbpnr = 0;

 for (const item of items) {
 const totalSinImp = getItemSubtotal(item);
 subtotal_sin_impuestos += totalSinImp;
 total_iva += totalSinImp * (item.iva_porcentaje / 100);
 if (item.ice_porcentaje) total_ice += (totalSinImp * item.ice_porcentaje) / 100;
 total_descuento += getItemDiscount(item);
 total_irbpnr += (item.irbpnr_valor || 0) * item.cantidad;

 const porc = item.iva_porcentaje;
 if (porc === 0) {
 if (item.iva_codigo === '6') subtotal_no_objeto_iva += totalSinImp;
 else if (item.iva_codigo === '7') subtotal_exento_iva += totalSinImp;
 else subtotal_iva_0 += totalSinImp;
 } else if (porc === 5) subtotal_iva_5 += totalSinImp;
 else if (porc === 8) subtotal_iva_8 += totalSinImp;
 else if (porc === 12) subtotal_iva_12 += totalSinImp;
 else if (porc === 13) subtotal_iva_13 += totalSinImp;
 else if (porc === 14) subtotal_iva_14 += totalSinImp;
 else if (porc === 15) subtotal_iva_15 += totalSinImp;
 else subtotal_iva_0 += totalSinImp;
 }

 const propina = 0;
 const total = subtotal_sin_impuestos + total_iva + total_ice + total_irbpnr + propina;

 return {
 subtotal_sin_impuestos,
 subtotal_iva_0,
 subtotal_iva_5,
 subtotal_iva_8,
 subtotal_iva_12,
 subtotal_iva_13,
 subtotal_iva_14,
 subtotal_iva_15,
 subtotal_no_objeto_iva,
 subtotal_exento_iva,
 total_iva,
 total_ice,
 total_descuento,
 total_irbpnr,
 propina,
 total,
 };
}

type TotalesSRI = ReturnType<typeof computeTotales>;

/**
 * Renderiza el desglose de totales en el formato que exige el SRI:
 * SUBTOTAL IVA 15%, SUBTOTAL IVA 0%, No objeto, Exento, SUBTOTAL SIN IMPUESTOS,
 * TOTAL DE DESCUENTO, IVA 15%, ICE, IRBPNR, PROPINA, VALOR TOTAL.
 */
/**
 * Etiqueta del IVA: si solo se usa UNA tarifa positiva, muestra esa tarifa
 * (ej: "IVA 8%") en lugar de fijar 15% aunque el cálculo sea de otra tarifa.
 */
function ivaLabel(totals: TotalesSRI): string {
 const positive: { label: string; value: number }[] = [
 { label: '5%', value: totals.subtotal_iva_5 },
 { label: '8%', value: totals.subtotal_iva_8 },
 { label: '12%', value: totals.subtotal_iva_12 },
 { label: '13%', value: totals.subtotal_iva_13 },
 { label: '14%', value: totals.subtotal_iva_14 },
 { label: '15%', value: totals.subtotal_iva_15 },
 ];
 const used = positive.filter((p) => p.value > 0);
 if (used.length === 1) return `IVA ${used[0].label}`;
 return 'IVA';
}

function TotalesSRI({ totals, propinaOverride }: { totals: TotalesSRI; propinaOverride?: number }) {
 const propina = propinaOverride ?? totals.propina ?? 0;
 const rows = [
 { label: 'Subtotal IVA 15%', value: totals.subtotal_iva_15 },
 { label: 'Subtotal IVA 0%', value: totals.subtotal_iva_0 },
 { label: 'Subtotal No Objeto de IVA', value: totals.subtotal_no_objeto_iva },
 { label: 'Subtotal Exento de IVA', value: totals.subtotal_exento_iva },
 ...(totals.subtotal_iva_5 ? [{ label: 'Subtotal IVA 5%', value: totals.subtotal_iva_5 }] : []),
 ...(totals.subtotal_iva_8 ? [{ label: 'Subtotal IVA 8%', value: totals.subtotal_iva_8 }] : []),
 ...(totals.subtotal_iva_12 ? [{ label: 'Subtotal IVA 12%', value: totals.subtotal_iva_12 }] : []),
 ...(totals.subtotal_iva_13 ? [{ label: 'Subtotal IVA 13%', value: totals.subtotal_iva_13 }] : []),
 ...(totals.subtotal_iva_14 ? [{ label: 'Subtotal IVA 14%', value: totals.subtotal_iva_14 }] : []),
 { label: 'Subtotal sin impuestos', value: totals.subtotal_sin_impuestos },
 { label: 'Total de descuento', value: totals.total_descuento },
 { label: ivaLabel(totals), value: totals.total_iva },
 { label: 'ICE', value: totals.total_ice },
 { label: 'IRBPNR', value: totals.total_irbpnr },
 ...(propina > 0 ? [{ label: 'Propina', value: propina }] : []),
 ];
 const total = totals.total + (propinaOverride ? propinaOverride - (totals.propina ?? 0) : 0);
 return (
 <div className="space-y-1.5">
 {rows.map((r) => (
 <div key={r.label} className="flex justify-between text-sm">
 <span className="text-muted-foreground">{r.label}</span>
 <span>${formatCurrency(r.value)}</span>
 </div>
 ))}
 <Separator />
 <div className="flex justify-between font-bold text-base">
 <span>VALOR TOTAL</span>
 <span>${formatCurrency(total)}</span>
 </div>
 </div>
 );
}

/**
 * Adapta los totales calculados por el backend (ComprobanteResponse / ProformaResponse)
 * al desglose SRI para reutilizar TotalesSRI en vistas de detalle.
 */
function totalesFromResponse(d: {
 subtotal_iva_0: number;
 subtotal_iva_5: number;
 subtotal_iva_8: number;
 subtotal_iva_12: number;
 subtotal_iva_13: number;
 subtotal_iva_14: number;
 subtotal_iva_15: number;
 subtotal_no_objeto_iva: number;
 subtotal_exento_iva: number;
 subtotal_sin_impuestos: number;
 total_iva: number;
 total_ice: number;
 total_descuento: number;
 total_con_impuestos: number;
 propina?: number;
}): TotalesSRI {
 const propina = d.propina ?? 0;
 return {
 subtotal_sin_impuestos: d.subtotal_sin_impuestos,
 subtotal_iva_0: d.subtotal_iva_0,
 subtotal_iva_5: d.subtotal_iva_5,
 subtotal_iva_8: d.subtotal_iva_8,
 subtotal_iva_12: d.subtotal_iva_12,
 subtotal_iva_13: d.subtotal_iva_13,
 subtotal_iva_14: d.subtotal_iva_14,
 subtotal_iva_15: d.subtotal_iva_15,
 subtotal_no_objeto_iva: d.subtotal_no_objeto_iva,
 subtotal_exento_iva: d.subtotal_exento_iva,
 total_iva: d.total_iva,
 total_ice: d.total_ice,
 total_descuento: d.total_descuento,
 total_irbpnr: 0,
 propina,
 total: d.total_con_impuestos,
 };
}

// ─── Main Component ─────────────────────────────────────────────

interface ContaECInvoicesProps {
 user: {
 id: string;
 email: string;
 full_name: string;
 is_active: boolean;
 is_admin: boolean;
 phone?: string | null;
 language?: string;
 theme?: string;
 license_type?: string;
 };
 companies: Company[];
 initialTab?: InvoiceTab;
}

type InvoiceTab = 'listado' | 'nueva' | 'proformas' | 'nueva-proforma' | 'productos' | 'clientes';

/**
 * Captura errores de renderizado de la sección para evitar la pantalla
 * "Application error" de Next.js y mostrar un fallback amigable.
 */
class InvoicesErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
 state = { hasError: false };

 static getDerivedStateFromError() {
 return { hasError: true };
 }

 componentDidCatch(error: Error, info: unknown) {
 console.error('ContaECInvoices render error:', error, info);
 }

 render() {
 if (this.state.hasError) {
 return (
 <div className="flex flex-col items-center justify-center p-12 text-center space-y-4">
 <div className="text-5xl">⚠️</div>
 <h3 className="text-xl font-bold">Ocurrió un error al cargar esta sección</h3>
 <p className="text-muted-foreground max-w-md text-sm">
 Se produjo un error inesperado al renderizar los comprobantes. Recargue la página
 o contacte a soporte si el problema persiste.
 </p>
 <Button onClick={() => this.setState({ hasError: false })}>Reintentar</Button>
 </div>
 );
 }
 return this.props.children;
 }
}

function ContaECInvoicesInner({ user: _user, companies, initialTab }: ContaECInvoicesProps) {
 const [activeTab, setActiveTab] = useState<InvoiceTab>(initialTab || 'listado');
 const [selectedCompanyId, setSelectedCompanyId] = useState<string>(() =>
 companies.length > 0 ? companies[0].id : ''
 );

 if (companies.length === 0) {
 return (
 <div className="space-y-6">
 <div>
 <h2 className="text-2xl font-bold">Comprobantes Electrónicos</h2>
 <p className="text-muted-foreground">
 Gestione sus comprobantes, productos y clientes
 </p>
 </div>
 <Card>
 <CardContent className="py-12 text-center">
 <Building2Icon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
 <h3 className="text-lg font-medium">Sin empresas registradas</h3>
 <p className="text-muted-foreground text-sm mt-1">
 Registre una empresa en el panel de Empresas antes de emitir comprobantes electronicos.
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
 <h2 className="text-2xl font-bold">Comprobantes Electrónicos</h2>
 <p className="text-muted-foreground">
 Gestione sus comprobantes, productos y clientes
 </p>
 </div>
 {companies.length > 1 && (
 <div className="flex items-center gap-2">
 <Label htmlFor="company-select" className="text-sm whitespace-nowrap">Empresa:</Label>
 <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
 <SelectTrigger id="company-select" className="w-[220px]">
 <SelectValue placeholder="Seleccione empresa" />
 </SelectTrigger>
 <SelectContent>
 {companies.map((c) => (
 <SelectItem key={c.id} value={c.id}>
 {c.razon_social}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 )}
 </div>

 <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as InvoiceTab)} className="space-y-4">
 <TabsList className="flex flex-wrap h-auto gap-1">
 <TabsTrigger value="listado" className="gap-1.5">
 <Receipt className="h-3.5 w-3.5" />
 <span className="hidden sm:inline">Listado</span>
 </TabsTrigger>
 <TabsTrigger value="nueva" className="gap-1.5">
 <Plus className="h-3.5 w-3.5" />
 <span className="hidden sm:inline">Nueva Factura</span>
 </TabsTrigger>
 <TabsTrigger value="proformas" className="gap-1.5">
 <FileText className="h-3.5 w-3.5" />
 <span className="hidden sm:inline">Proformas</span>
 </TabsTrigger>
 <TabsTrigger value="productos" className="gap-1.5">
 <Package className="h-3.5 w-3.5" />
 <span className="hidden sm:inline">Productos</span>
 </TabsTrigger>
 <TabsTrigger value="clientes" className="gap-1.5">
 <Users className="h-3.5 w-3.5" />
 <span className="hidden sm:inline">Clientes</span>
 </TabsTrigger>
 </TabsList>

 <TabsContent value="listado">
 <ComprobanteListado companyId={selectedCompanyId} />
 </TabsContent>

 <TabsContent value="nueva">
 <NuevaFacturaWizard
 companyId={selectedCompanyId}
 onCreated={() => setActiveTab('listado')}
 companies={companies}
 />
 </TabsContent>

 <TabsContent value="proformas">
 <ProformasTab
 companyId={selectedCompanyId}
 onNewProforma={() => setActiveTab('nueva-proforma')}
 />
 </TabsContent>

 <TabsContent value="nueva-proforma">
 <NuevaProformaWizard
 companyId={selectedCompanyId}
 onCreated={() => setActiveTab('proformas')}
 />
 </TabsContent>

 <TabsContent value="productos">
 <ProductosTab companyId={selectedCompanyId} />
 </TabsContent>

 <TabsContent value="clientes">
 <ClientesTab companyId={selectedCompanyId} />
 </TabsContent>
 </Tabs>
 </div>
 );
}

export function ContaECInvoices(props: ContaECInvoicesProps) {
 return (
 <InvoicesErrorBoundary>
 <ContaECInvoicesInner {...props} />
 </InvoicesErrorBoundary>
 );
}

function Building2Icon({ className }: { className?: string }) {
 return (
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
 <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" />
 <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
 <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2" />
 <path d="M10 6h4" />
 <path d="M10 10h4" />
 <path d="M10 14h4" />
 <path d="M10 18h4" />
 </svg>
 );
}

// ─── Comprobante Listado ────────────────────────────────────────

function ComprobanteListado({ companyId }: { companyId: string }) {
 const [comprobantes, setComprobantes] = useState<ComprobanteListResponse[]>([]);
 const [stats, setStats] = useState<ComprobanteStatsResponse | null>(null);
 const [loading, setLoading] = useState(true);
 const [filterTipo, setFilterTipo] = useState<string>('all');
 const [filterEstado, setFilterEstado] = useState<string>('all');
 const [actionLoading, setActionLoading] = useState<string | null>(null);
 const [xmlDialog, setXmlDialog] = useState<{ open: boolean; xml: string }>({ open: false, xml: '' });
 const [detailDialog, setDetailDialog] = useState<{ open: boolean; data: ComprobanteResponse | null }>({ open: false, data: null });
 const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
 const [detailLoading, setDetailLoading] = useState(false);
 const [validationDialog, setValidationDialog] = useState<{ open: boolean; result: ValidationResult | null; comprobanteId: string }>({ open: false, result: null, comprobanteId: '' });
 const [rechazadoDialog, setRechazadoDialog] = useState<{ open: boolean; comprobanteId: string; sriMensaje: string; sriMensajeDetallado: string }>({ open: false, comprobanteId: '', sriMensaje: '', sriMensajeDetallado: '' });
 // Edición de comprobante (borrador con errores o rechazado)
 const [editDialog, setEditDialog] = useState<{ open: boolean; comprobanteId: string | null }>({ open: false, comprobanteId: null });

 const loadData = useCallback(async () => {
 if (!companyId) return;
 setLoading(true);
 try {
 const [comps, st] = await Promise.all([
 getComprobantes({
 company_id: companyId,
 tipo_comprobante: filterTipo !== 'all' ? filterTipo : undefined,
 estado: filterEstado !== 'all' ? filterEstado : undefined,
 }),
 getComprobanteStats(companyId),
 ]);
 setComprobantes(Array.isArray(comps) ? comps : []);
 setStats(st);
 } catch {
 toast.error('Error al cargar comprobantes');
 } finally {
 setLoading(false);
 }
 }, [companyId, filterTipo, filterEstado]);

 useEffect(() => {
 loadData();
 }, [loadData]);

 async function handleAction(action: string, id: string) {
 setActionLoading(id + action);
 try {
 switch (action) {
 case 'firmar':
 await firmarComprobante(id);
 toast.success('Comprobante firmado exitosamente');
 break;
 case 'enviar': {
 const result = (await enviarComprobanteSRI(id)) as { estado?: string; sri_mensaje?: string } | undefined;
 if (result && result.estado === 'RECHAZADO') {
 // Mostrar el motivo real del rechazo del SRI
 setRechazadoDialog({
 open: true,
 comprobanteId: id,
 sriMensaje: result.sri_mensaje || 'El SRI rechazó el comprobante. Verifique los datos.',
 sriMensajeDetallado: '',
 });
 toast.error('Comprobante rechazado por el SRI');
 } else if (result && result.estado === 'AUTORIZADO') {
 toast.success('Comprobante autorizado por el SRI');
 } else {
 toast.success('Comprobante enviado al SRI');
 }
 break;
 }
 case 'consultar':
 await consultarComprobanteSRI(id);
 toast.success('Consulta al SRI realizada');
 break;
 case 'recuperar': {
 const result = await recuperarComprobanteSRI(id);
 if (result.estado === 'AUTORIZADO') {
 toast.success('Comprobante recuperado y autorizado por el SRI');
 } else if (result.estado === 'RECHAZADO') {
 toast.error(`Comprobante rechazado: ${result.sri_mensaje || 'Verifique los datos'}`);
 } else {
 toast.info(result.sri_mensaje || result.message);
 }
 break;
 }
 case 'procesar': {
 toast.info('Procesando comprobante... Esto puede tardar unos segundos.');
 const result = await procesarComprobante(id);
 if (result.estado === 'AUTORIZADO') {
 toast.success('Comprobante autorizado por el SRI');
 } else if (result.estado === 'RECHAZADO') {
 toast.error(`Comprobante rechazado: ${result.sri_mensaje || 'Verifique los datos'}`);
 } else {
 toast.info(result.sri_mensaje || result.message);
 }
 break;
 }
 case 'xml': {
 const result = await getComprobanteXML(id);
 setXmlDialog({ open: true, xml: result.xml_content || result.message || 'Sin contenido XML' });
 setActionLoading(null);
 return;
 }
 case 'download-ride': {
 const blob = await downloadRIDE(id);
 const url = window.URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = `RIDE_${id}.pdf`;
 document.body.appendChild(a);
 a.click();
 document.body.removeChild(a);
 window.URL.revokeObjectURL(url);
 toast.success('RIDE PDF descargado');
 break;
 }
 case 'download-xml': {
 const xmlResult = await getComprobanteXML(id);
 if (xmlResult.xml_content) {
 const xmlBlob = new Blob([xmlResult.xml_content], { type: 'application/xml' });
 const xmlUrl = window.URL.createObjectURL(xmlBlob);
 const xmlA = document.createElement('a');
 xmlA.href = xmlUrl;
 xmlA.download = `comprobante_${xmlResult.secuencial || id}.xml`;
 document.body.appendChild(xmlA);
 xmlA.click();
 document.body.removeChild(xmlA);
 window.URL.revokeObjectURL(xmlUrl);
 toast.success('XML descargado');
 } else {
 toast.error('No hay XML disponible para este comprobante');
 }
 break;
 }
 case 'enviar-email': {
 const emailResult = await enviarComprobanteEmail(id);
 toast.success(emailResult.message || 'Comprobante enviado por correo');
 break;
 }
 case 'validar': {
 const valResult = await validarComprobante(id);
 setValidationDialog({ open: true, result: valResult, comprobanteId: id });
 setActionLoading(null);
 return;
 }
 case 'corregir': {
 const comp = await getComprobante(id);
 setRechazadoDialog({
 open: true,
 comprobanteId: id,
 sriMensaje: comp.sri_mensaje || 'Sin mensaje del SRI',
 sriMensajeDetallado: '',
 });
 setActionLoading(null);
 return;
 }
 case 'editar': {
 setEditDialog({ open: true, comprobanteId: id });
 setActionLoading(null);
 return;
 }
 case 'detalle': {
 setDetailLoading(true);
 const comp = await getComprobante(id);
 setDetailDialog({ open: true, data: comp });
 setActionLoading(null);
 setDetailLoading(false);
 return;
 }
 }
 loadData();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error en la operacion');
 } finally {
 setActionLoading(null);
 setDetailLoading(false);
 }
 }

 async function handleDelete(id: string) {
 try {
 await deleteComprobante(id);
 toast.success('Comprobante eliminado');
 setDeleteConfirm(null);
 loadData();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al eliminar');
 }
 }

 if (loading) {
 return (
 <div className="flex items-center justify-center h-48">
 <Loader2 className="h-8 w-8 animate-spin text-primary" />
 </div>
 );
 }

 return (
 <div className="space-y-4">
 {/* Stats Cards */}
 {stats && (
 <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold">{stats.total}</div>
 <p className="text-xs text-muted-foreground">Total</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold">{stats.borrador}</div>
 <p className="text-xs text-muted-foreground">Borradores</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-sky-600">{stats.firmado}</div>
 <p className="text-xs text-muted-foreground">Firmados</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-amber-500">{stats.enviado}</div>
 <p className="text-xs text-muted-foreground">Enviados</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-emerald-600">{stats.autorizado}</div>
 <p className="text-xs text-muted-foreground">Autorizados</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-destructive">{stats.rechazado}</div>
 <p className="text-xs text-muted-foreground">Rechazados</p>
 </div>
 </Card>
 </div>
 )}

 {/* Filters */}
 <div className="flex flex-wrap gap-3 items-center">
 <Select value={filterTipo} onValueChange={setFilterTipo}>
 <SelectTrigger className="w-[200px]">
 <SelectValue placeholder="Tipo comprobante" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">Todos los tipos</SelectItem>
 {TIPOS_COMPROBANTE.map((t) => (
 <SelectItem key={t.codigo} value={t.codigo}>
 {t.codigo} - {t.descripcion}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>

 <Select value={filterEstado} onValueChange={setFilterEstado}>
 <SelectTrigger className="w-[180px]">
 <SelectValue placeholder="Estado" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">Todos los estados</SelectItem>
 <SelectItem value="BORRADOR">Borrador</SelectItem>
 <SelectItem value="FIRMADO">Firmado</SelectItem>
 <SelectItem value="ENVIADO">Enviado</SelectItem>
 <SelectItem value="AUTORIZADO">Autorizado</SelectItem>
 <SelectItem value="RECHAZADO">Rechazado</SelectItem>
 </SelectContent>
 </Select>

 <Button variant="outline" size="icon" onClick={loadData}>
 <RefreshCw className="h-4 w-4" />
 </Button>
 </div>

 {/* Table */}
 {comprobantes.length > 0 ? (
 <Card>
 <CardContent className="p-0">
 <ScrollArea className="max-h-[500px]">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Tipo</TableHead>
 <TableHead>Secuencial</TableHead>
 <TableHead>Cliente</TableHead>
 <TableHead>Fecha</TableHead>
 <TableHead className="text-right">Total</TableHead>
 <TableHead>Estado</TableHead>
 <TableHead className="text-right">Acciones</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {comprobantes.map((comp) => (
 <TableRow key={comp.id}>
 <TableCell>
 <Badge variant="outline" className="text-xs font-mono">
 {comp.tipo_comprobante}
 </Badge>
 </TableCell>
 <TableCell className="font-mono text-xs">{comp.secuencial}</TableCell>
 <TableCell className="max-w-[150px] truncate">{comp.cliente_razon_social}</TableCell>
 <TableCell className="text-xs">
 {new Date(comp.fecha_emision).toLocaleDateString('es-EC')}
 </TableCell>
 <TableCell className="text-right font-medium">
 ${formatCurrency(comp.total_con_impuestos)}
 </TableCell>
 <TableCell>{getEstadoBadge(comp.estado)}</TableCell>
 <TableCell className="text-right">
 <div className="flex justify-end gap-1">
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7"
 onClick={() => handleAction('detalle', comp.id)}
 disabled={!!actionLoading || detailLoading}
 title="Ver detalle"
 >
 {detailLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
 </Button> {comp.estado.toUpperCase() === 'BORRADOR' && (
 <>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7"
 onClick={() => handleAction('editar', comp.id)}
 disabled={!!actionLoading}
 title="Editar comprobante"
 >
 {actionLoading === comp.id + 'editar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Pencil className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('validar', comp.id)}
 disabled={!!actionLoading}
 title="Validar"
 >
 {actionLoading === comp.id + 'validar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <CheckCircle2 className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-sky-600"
 onClick={() => handleAction('firmar', comp.id)}
 disabled={!!actionLoading}
 title="Firmar"
 >
 {actionLoading === comp.id + 'firmar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Shield className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-destructive"
 onClick={() => setDeleteConfirm(comp.id)}
 disabled={!!actionLoading}
 title="Eliminar"
 >
 <Trash2 className="h-3.5 w-3.5" />
 </Button>
 </>
 )}
 {comp.estado.toUpperCase() === 'RECHAZADO' && (
 <>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-amber-500"
 onClick={() => handleAction('corregir', comp.id)}
 disabled={!!actionLoading}
 title="Ver motivo del rechazo"
 >
 {actionLoading === comp.id + 'corregir' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <AlertTriangle className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7"
 onClick={() => handleAction('editar', comp.id)}
 disabled={!!actionLoading}
 title="Editar y corregir"
 >
 {actionLoading === comp.id + 'editar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Pencil className="h-3.5 w-3.5" />
 )}
 </Button>
 </>
 )}
 {comp.estado.toUpperCase() === 'FIRMADO' && (
 <>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-amber-500"
 onClick={() => handleAction('enviar', comp.id)}
 disabled={!!actionLoading}
 title="Enviar al SRI"
 >
 {actionLoading === comp.id + 'enviar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Send className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('procesar', comp.id)}
 disabled={!!actionLoading}
 title="Procesar (1 clic: Enviar + Consultar)"
 >
 {actionLoading === comp.id + 'procesar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Zap className="h-3.5 w-3.5" />
 )}
 </Button>
 </>
 )}
 {comp.estado.toUpperCase() === 'ENVIADO' && (
 <>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-sky-600"
 onClick={() => handleAction('recuperar', comp.id)}
 disabled={!!actionLoading}
 title="Recuperar del SRI (máx. 72h desde la emisión)"
 >
 {actionLoading === comp.id + 'recuperar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <History className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-amber-500"
 onClick={() => handleAction('consultar', comp.id)}
 disabled={!!actionLoading}
 title="Consultar SRI"
 >
 {actionLoading === comp.id + 'consultar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <RefreshCw className="h-3.5 w-3.5" />
 )}
 </Button>
 </>
 )}
 {comp.estado.toUpperCase() === 'AUTORIZADO' && (
 <>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('download-ride', comp.id)}
 disabled={!!actionLoading}
 title="Descargar RIDE PDF"
 >
 {actionLoading === comp.id + 'download-ride' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Download className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('download-xml', comp.id)}
 disabled={!!actionLoading}
 title="Descargar XML"
 >
 {actionLoading === comp.id + 'download-xml' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <FileDown className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('enviar-email', comp.id)}
 disabled={!!actionLoading}
 title="Enviar por correo"
 >
 {actionLoading === comp.id + 'enviar-email' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Mail className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('xml', comp.id)}
 disabled={!!actionLoading}
 title="Ver XML"
 >
 {actionLoading === comp.id + 'xml' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <FileText className="h-3.5 w-3.5" />
 )}
 </Button>
 </>
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
 <Receipt className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
 <h3 className="text-lg font-medium">Sin comprobantes</h3>
 <p className="text-muted-foreground text-sm mt-1">
 Cree su primera factura para comenzar
 </p>
 </CardContent>
 </Card>
 )}

 {/* XML Dialog */}
 <Dialog open={xmlDialog.open} onOpenChange={(o) => setXmlDialog({ ...xmlDialog, open: o })}>
 <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
 <DialogHeader>
 <DialogTitle>XML del Comprobante</DialogTitle>
 <DialogDescription>Contenido XML firmado del comprobante</DialogDescription>
 </DialogHeader>
 <ScrollArea className="max-h-[60vh]">
 <pre className="text-xs bg-muted p-4 rounded-md overflow-x-auto whitespace-pre-wrap break-all">
 {xmlDialog.xml || 'Sin contenido XML'}
 </pre>
 </ScrollArea>
 </DialogContent>
 </Dialog>

 {/* Detail Dialog */}
 <Dialog open={detailDialog.open} onOpenChange={(o) => setDetailDialog({ ...detailDialog, open: o })}>
 <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
 <DialogHeader>
 <DialogTitle>Detalle del Comprobante</DialogTitle>
 <DialogDescription>
 {detailDialog.data ? `${getTipoComprobanteLabel(detailDialog.data.tipo_comprobante)} #${detailDialog.data.secuencial}` : ''}
 </DialogDescription>
 </DialogHeader>
 {detailDialog.data && <ComprobanteDetailView comp={detailDialog.data} />}
 </DialogContent>
 </Dialog>

 {/* Delete Confirmation */}
 <AlertDialog open={!!deleteConfirm} onOpenChange={(o) => !o && setDeleteConfirm(null)}>
 <AlertDialogContent>
 <AlertDialogHeader>
 <AlertDialogTitle>Eliminar comprobante</AlertDialogTitle>
 <AlertDialogDescription>
 Esta seguro de que desea eliminar este comprobante? Solo se pueden eliminar comprobantes en estado Borrador.
 </AlertDialogDescription>
 </AlertDialogHeader>
 <AlertDialogFooter>
 <AlertDialogCancel>Cancelar</AlertDialogCancel>
 <AlertDialogAction
 className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
 onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
 >
 Eliminar
 </AlertDialogAction>
 </AlertDialogFooter>
 </AlertDialogContent>
 </AlertDialog>

 {/* Validation Results Dialog */}
 <Dialog open={validationDialog.open} onOpenChange={(o) => setValidationDialog({ ...validationDialog, open: o })}>
 <DialogContent className="sm:max-w-lg">
 <DialogHeader>
 <DialogTitle>Resultado de Validación SRI</DialogTitle>
 <DialogDescription>
 Resultado de la pre-validación del comprobante antes de enviar al SRI
 </DialogDescription>
 </DialogHeader>
 {validationDialog.result && (
 <div className="space-y-4">
 {validationDialog.result.valid ? (
 <div className="flex items-center gap-3 p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
 <CheckCircle2 className="h-8 w-8 text-emerald-600 shrink-0" />
 <div>
 <p className="font-semibold text-emerald-800 dark:text-emerald-200">Comprobante válido para envío al SRI</p>
 <p className="text-sm text-emerald-600 dark:text-emerald-400">No se encontraron errores que impidan el envío</p>
 </div>
 </div>
 ) : (
 <div className="space-y-3">
 <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
 <XCircle className="h-8 w-8 text-red-600 shrink-0" />
 <div>
 <p className="font-semibold text-red-800 dark:text-red-200">Comprobante con errores</p>
 <p className="text-sm text-red-600 dark:text-red-400">{validationDialog.result.errors.length} error(es) encontrado(s)</p>
 </div>
 </div>
 <div className="space-y-2 max-h-48 overflow-y-auto">
 {validationDialog.result.errors.map((err, i) => (
 <div key={i} className="flex items-start gap-2 p-2 rounded border bg-red-50/50 dark:bg-red-950/20 text-sm">
 <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
 <div>
 <span className="font-mono text-xs text-red-600 dark:text-red-400">{err.field}</span>
 <p className="text-red-700 dark:text-red-300">{err.message}</p>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}
 {validationDialog.result.warnings.length > 0 && (
 <div className="space-y-2">
 <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
 <AlertTriangle className="h-4 w-4" />
 <span className="font-medium text-sm">Advertencias ({validationDialog.result.warnings.length})</span>
 </div>
 <div className="space-y-1.5 max-h-32 overflow-y-auto">
 {validationDialog.result.warnings.map((warn, i) => (
 <div key={i} className="flex items-start gap-2 p-2 rounded border bg-amber-50/50 dark:bg-amber-950/20 text-sm">
 <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
 <div>
 <span className="font-mono text-xs text-amber-600 dark:text-amber-400">{warn.field}</span>
 <p className="text-amber-700 dark:text-amber-300">{warn.message}</p>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}
 <DialogFooter>
 {!validationDialog.result.valid && (
 <Button
 variant="outline"
 onClick={() => {
 setValidationDialog({ ...validationDialog, open: false });
 setEditDialog({ open: true, comprobanteId: validationDialog.comprobanteId });
 }}
 >
 <Pencil className="h-4 w-4 mr-2" />
 Editar factura
 </Button>
 )}
 {!validationDialog.result.valid && validationDialog.result.warnings.length > 0 && (
 <Button
 variant="outline"
 onClick={() => {
 setValidationDialog({ ...validationDialog, open: false });
 handleAction('firmar', validationDialog.comprobanteId);
 }}
 >
 Firmar de todas formas
 </Button>
 )}
 {validationDialog.result.valid && (
 <Button
 onClick={() => {
 setValidationDialog({ ...validationDialog, open: false });
 handleAction('firmar', validationDialog.comprobanteId);
 }}
 >
 <Shield className="h-4 w-4 mr-2" />
 Firmar comprobante
 </Button>
 )}
 <Button variant="outline" onClick={() => setValidationDialog({ ...validationDialog, open: false })}>
 Cerrar
 </Button>
 </DialogFooter>
 </div>
 )}
 </DialogContent>
 </Dialog>

 {/* Rechazado Dialog - Show SRI message and option to corregir */}
 <Dialog open={rechazadoDialog.open} onOpenChange={(o) => setRechazadoDialog({ ...rechazadoDialog, open: o })}>
 <DialogContent className="sm:max-w-lg">
 <DialogHeader>
 <DialogTitle>Comprobante Rechazado por el SRI</DialogTitle>
 <DialogDescription>
 El SRI ha rechazado este comprobante. Revise los motivos antes de corregir.
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
 <XCircle className="h-6 w-6 text-red-600 shrink-0 mt-0.5" />
 <div className="space-y-1">
 <p className="font-medium text-red-800 dark:text-red-200">Motivo del rechazo:</p>
 <p className="text-sm text-red-700 dark:text-red-300">{rechazadoDialog.sriMensaje}</p>
 </div>
 </div>
 <p className="text-sm text-muted-foreground">
 Al corregir, el comprobante se reiniciará a estado Borrador, permitiéndole modificar los datos y reenviarlo al SRI.
 </p>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setRechazadoDialog({ ...rechazadoDialog, open: false })}>
 Cancelar
 </Button>
 <Button
 onClick={() => {
 setRechazadoDialog({ ...rechazadoDialog, open: false });
 setEditDialog({ open: true, comprobanteId: rechazadoDialog.comprobanteId });
 }}
 >
 <Pencil className="h-4 w-4 mr-2" />
 Editar y Corregir
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* Edición de comprobante (BORRADOR con errores o RECHAZADO) */}
 <EditarComprobanteDialog
 open={editDialog.open}
 comprobanteId={editDialog.comprobanteId}
 onClose={() => setEditDialog({ open: false, comprobanteId: null })}
 onSaved={() => { setEditDialog({ open: false, comprobanteId: null }); loadData(); }}
 onValidate={(result) => {
 setEditDialog({ open: false, comprobanteId: null });
 setValidationDialog({ open: true, result, comprobanteId: editDialog.comprobanteId || '' });
 }}
 />
 </div>
 );
}

// ─── Editar Comprobante Dialog ───────────────────────────────────

/**
 * Dialog para editar un comprobante en estado BORRADOR (con errores de
 * validación) o RECHAZADO. Permite corregir cliente, forma de pago e items,
 * guardar y validar de nuevo (mostrando los errores reales del SRI).
 */
function EditarComprobanteDialog({
 open,
 comprobanteId,
 onClose,
 onSaved,
 onValidate,
}: {
 open: boolean;
 comprobanteId: string | null;
 onClose: () => void;
 onSaved: () => void;
 onValidate: (result: ValidationResult) => void;
}) {
 const [loading, setLoading] = useState(false);
 const [saving, setSaving] = useState(false);
 const [validating, setValidating] = useState(false);
 const [error, setError] = useState<string | null>(null);
 const [formaPago, setFormaPago] = useState('01');
 const [items, setItems] = useState<
 {
 codigo_principal: string;
 descripcion: string;
 cantidad: number;
 precio_unitario: number;
 iva_codigo: string;
 iva_porcentaje: number;
 descuento?: number;
 }[]
 >([]);

 // Cargar el comprobante cuando se abre el dialog
 useEffect(() => {
 if (!open || !comprobanteId) return;
 setLoading(true);
 setError(null);
 getComprobante(comprobanteId)
 .then((comp) => {
 setFormaPago(comp.forma_pago || '01');
 setItems(
 (comp.detalles || []).map((d) => ({
 codigo_principal: d.codigo_principal,
 descripcion: d.descripcion,
 cantidad: Number(d.cantidad),
 precio_unitario: Number(d.precio_unitario),
 iva_codigo: d.iva_codigo || '4',
 iva_porcentaje: Number(d.iva_porcentaje || 15),
 descuento: Number(d.descuento || 0),
 }))
 );
 })
 .catch((err) => setError(err instanceof Error ? err.message : 'Error al cargar el comprobante'))
 .finally(() => setLoading(false));
 }, [open, comprobanteId]);

 function updateItem(index: number, updates: Partial<(typeof items)[number]>) {
 setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...updates } : it)));
 }

 function removeItem(index: number) {
 setItems((prev) => prev.filter((_, i) => i !== index));
 }

 function addItem() {
 setItems((prev) => [
 ...prev,
 { codigo_principal: '', descripcion: '', cantidad: 1, precio_unitario: 0, iva_codigo: '4', iva_porcentaje: 15 },
 ]);
 }

 async function handleSave() {
 if (!comprobanteId) return;
 if (items.length === 0) {
 setError('Debe existir al menos un item');
 return;
 }
 setSaving(true);
 setError(null);
 try {
 await corregirComprobante(comprobanteId, {
 detalles: items.map((it) => ({
 codigo_principal: it.codigo_principal,
 descripcion: it.descripcion,
 cantidad: it.cantidad,
 precio_unitario: it.precio_unitario,
 iva_codigo: it.iva_codigo,
 iva_porcentaje: it.iva_porcentaje,
 descuento: it.descuento || undefined,
 })),
 forma_pago: formaPago,
 });
 toast.success('Comprobante actualizado correctamente');
 onSaved();
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Error al guardar el comprobante');
 } finally {
 setSaving(false);
 }
 }

 async function handleValidate() {
 if (!comprobanteId) return;
 setValidating(true);
 setError(null);
 try {
 const result = await validarComprobante(comprobanteId);
 onValidate(result);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Error al validar');
 } finally {
 setValidating(false);
 }
 }

 return (
 <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
 <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
 <DialogHeader>
 <DialogTitle>Editar Comprobante</DialogTitle>
 <DialogDescription>
 Corrija los datos y guarde, o valide de nuevo para ver los errores del SRI.
 </DialogDescription>
 </DialogHeader>
 {loading ? (
 <div className="flex items-center justify-center h-40">
 <Loader2 className="h-8 w-8 animate-spin text-primary" />
 </div>
 ) : (
 <div className="space-y-4">
 {error && (
 <Alert variant="destructive">
 <AlertCircle className="h-4 w-4" />
 <AlertDescription>{error}</AlertDescription>
 </Alert>
 )}
 <div className="space-y-2">
 <Label>Forma de Pago</Label>
 <Select value={formaPago} onValueChange={setFormaPago}>
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {FORMAS_PAGO.map((fp) => (
 <SelectItem key={fp.codigo} value={fp.codigo}>
 {fp.codigo} - {fp.descripcion}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>

 <Separator />

 <div className="flex items-center justify-between">
 <h4 className="text-sm font-medium">Items ({items.length})</h4>
 <Button variant="outline" size="sm" onClick={addItem}>
 <Plus className="mr-1 h-3.5 w-3.5" />
 Agregar item
 </Button>
 </div>
 <div className="space-y-3">
 {items.map((item, i) => (
 <div key={i} className="rounded-md border p-3 space-y-2">
 <div className="flex items-center justify-between">
 <span className="text-xs font-medium text-muted-foreground">Item {i + 1}</span>
 <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => removeItem(i)}>
 <X className="h-3.5 w-3.5" />
 </Button>
 </div>
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
 <div className="space-y-1">
 <Label className="text-xs">Código</Label>
 <Input
 className="h-8 text-sm"
 value={item.codigo_principal}
 onChange={(e) => updateItem(i, { codigo_principal: e.target.value })}
 />
 </div>
 <div className="space-y-1 sm:col-span-2">
 <Label className="text-xs">Descripción</Label>
 <Input
 className="h-8 text-sm"
 value={item.descripcion}
 onChange={(e) => updateItem(i, { descripcion: e.target.value })}
 />
 </div>
 <div className="space-y-1">
 <Label className="text-xs">Cantidad</Label>
 <NumericInput integer className="h-8 text-sm"
 
 value={item.cantidad}
 onChange={(e) => updateItem(i, { cantidad: parseFloat(e.target.value) || 0 })} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Precio Unitario</Label>
                      <PriceInput
                        className="h-8 text-sm"
                        value={item.precio_unitario}
                        onChange={(v) => updateItem(i, { precio_unitario: v })}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">IVA</Label>
                      <Select
                        value={item.iva_codigo}
                        onValueChange={(v) => {
                          const rate = IVA_RATES.find((r) => r.codigo === v);
                          updateItem(i, { iva_codigo: v, iva_porcentaje: rate?.porcentaje ?? 0 });
                        }}
                      >
                        <SelectTrigger className="h-8 text-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {IVA_RATES.map((r) => (
                            <SelectItem key={r.codigo} value={r.codigo}>
                              {r.descripcion} ({r.porcentaje}%)
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Descuento ($)</Label>
                      <NumericInput className="h-8 text-sm"
 
 value={item.descuento ?? ''}
 onChange={(e) => updateItem(i, { descuento: parseFloat(e.target.value) || undefined })} />
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    Subtotal: ${formatCurrency(getItemSubtotal(item))}
                    {item.iva_porcentaje > 0 && (
                      <span> + IVA ${formatCurrency(getItemSubtotal(item) * item.iva_porcentaje / 100)}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <Separator />

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button variant="outline" onClick={handleValidate} disabled={validating}>
                {validating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                Validar
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
                Guardar cambios
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Comprobante Detail ──────────────────────────────────────────

function ComprobanteDetailView({ comp }: { comp: ComprobanteResponse }) {
  return (
    <ScrollArea className="max-h-[65vh]">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Estado</span>
            <div className="mt-1">{getEstadoBadge(comp.estado)}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Ambiente</span>
            <div className="mt-1">
              <Badge variant="outline">{comp.ambiente === '1' ? 'Pruebas' : 'Producción'}</Badge>
            </div>
          </div>
          <div>
            <span className="text-muted-foreground">Cliente</span>
            <div className="font-medium mt-1">{comp.cliente_razon_social}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Identificación</span>
            <div className="font-mono text-xs mt-1">{comp.cliente_identificacion}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Clave de Acceso</span>
            <div className="font-mono text-xs mt-1 break-all">{comp.clave_acceso || '-'}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Fecha Emisión</span>
            <div className="mt-1">{new Date(comp.fecha_emision).toLocaleString('es-EC')}</div>
          </div>
        </div>

        <Separator />

        {/* Totales en formato SRI */}
        <TotalesSRI totals={totalesFromResponse(comp)} />

        <Separator />

        {/* Detalles */}
        <div>
          <h4 className="text-sm font-medium mb-2">Detalles</h4>
          <div className="space-y-2">
            {comp.detalles.map((det, i) => (
              <div key={det.id || i} className="rounded-md border p-3 text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="font-medium">{det.descripcion}</span>
                  <span className="font-medium">${formatCurrency(det.precio_total_sin_impuestos)}</span>
                </div>
                <div className="flex gap-4 text-muted-foreground">
                  <span>Cod: {det.codigo_principal}</span>
                  <span>Cant: {det.cantidad}</span>
                  <span>P.Unit: ${formatCurrency(det.precio_unitario)}</span>
                  <span>IVA: {det.iva_porcentaje}%</span>
                  {det.ice_porcentaje && <span>ICE: {det.ice_porcentaje}%</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {comp.sri_mensaje && (
          <>
            <Separator />
            <div className="text-xs">
              <span className="text-muted-foreground">Mensaje SRI: </span>
              <span className="text-amber-600">{comp.sri_mensaje}</span>
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
}

// ─── Nueva Factura Wizard ────────────────────────────────────────

type WizardStep = 1 | 2 | 3 | 4 | 5;

function NuevaFacturaWizard({ companyId, onCreated, companies }: { companyId: string; onCreated: () => void; companies: Company[] }) {
  const [step, setStep] = useState<WizardStep>(1);
  const [creating, setCreating] = useState(false);

  // Step 1: Company already selected via companyId
  // Step 2: Client
  const [clientId, setClientId] = useState<string>('');
  const [clients, setClients] = useState<ClientResponse[]>([]);

  // Step 3: Items
  const [items, setItems] = useState<ComprobanteDetalleCreate[]>([]);
  const [products, setProducts] = useState<ProductResponse[]>([]);

  // Step 4: Additional info
  const [formaPago, setFormaPago] = useState<string>('01');
  const [tipoComprobante, setTipoComprobante] = useState<string>('01');
  const [infoAdicional, setInfoAdicional] = useState<Record<string, string>>({});
  const [newInfoKey, setNewInfoKey] = useState('');
  const [newInfoValue, setNewInfoValue] = useState('');

  // Nota de Crédito/Débito fields
  const [comprobanteModificadoId, setComprobanteModificadoId] = useState<string>('');
  const [motivoModificacion, setMotivoModificacion] = useState<string>('');
  const [autorizados, setAutorizados] = useState<ComprobanteListResponse[]>([]);

  // Retención fields (tipo 07)
  const [periodoFiscal, setPeriodoFiscal] = useState<string>('');
  const [retencionIvaCodigo, setRetencionIvaCodigo] = useState<string>('');
  const [retencionIvaPorcentaje, setRetencionIvaPorcentaje] = useState<number>(0);
  const [retencionRentaCodigo, setRetencionRentaCodigo] = useState<string>('');
  const [retencionRentaPorcentaje, setRetencionRentaPorcentaje] = useState<number>(0);
  const [baseImponible, setBaseImponible] = useState<number>(0);
  const [sriCatalogs, setSriCatalogs] = useState<{ retencion_iva: SRICatalog[]; retencion_renta: SRICatalog[] } | null>(null);

  // Load clients and products
  useEffect(() => {
    if (!companyId) return;
    async function load() {
      try {
        const [cls, prods] = await Promise.all([
          getClients(companyId),
          getProducts(companyId),
        ]);
        // Guard defensivo: evitar que respuestas no-array rompan el render
        setClients(Array.isArray(cls) ? cls : []);
        setProducts(Array.isArray(prods) ? prods : []);
      } catch {
        toast.error('Error al cargar datos');
      }
    }
    load();
  }, [companyId]);

  // Load autorizados for NC/ND when tipo changes to 04 or 05
  useEffect(() => {
    if ((tipoComprobante === '04' || tipoComprobante === '05') && companyId) {
      getComprobantes({ company_id: companyId, estado: 'AUTORIZADO' })
        .then(setAutorizados)
        .catch(() => toast.error('Error al cargar comprobantes autorizados'));
    }
  }, [tipoComprobante, companyId]);

  // Load SRI catalogs for retención
  useEffect(() => {
    if (tipoComprobante === '07') {
      getSRICatalogs()
        .then((catalogs) => setSriCatalogs({ retencion_iva: catalogs.retencion_iva, retencion_renta: catalogs.retencion_renta }))
        .catch(() => toast.error('Error al cargar catálogos SRI'));
    }
  }, [tipoComprobante]);

  // Add info adicional
  function addInfoAdicional() {
    if (newInfoKey.trim() && newInfoValue.trim()) {
      setInfoAdicional({ ...infoAdicional, [newInfoKey.trim()]: newInfoValue.trim() });
      setNewInfoKey('');
      setNewInfoValue('');
    }
  }

  function removeInfoAdicional(key: string) {
    const copy = { ...infoAdicional };
    delete copy[key];
    setInfoAdicional(copy);
  }

  // Calculate totals (desglose completo estilo SRI)
  const totals = computeTotales(items);

  // Validate step
  function canProceed(): boolean {
    switch (step) {
      case 1: return !!companyId;
      case 2: return !!clientId;
      case 3: {
        if (tipoComprobante === '07') return baseImponible > 0;
        return items.length > 0;
      }
      case 4: {
        if (tipoComprobante === '04' || tipoComprobante === '05') {
          return !!formaPago && !!comprobanteModificadoId && !!motivoModificacion.trim();
        }
        return !!formaPago;
      }
      case 5: return true;
    }
  }

  async function handleCreate() {
    setCreating(true);
    try {
      const detalles: ComprobanteDetalleCreate[] =
        tipoComprobante === '07'
          ? [{
              codigo_principal: 'RET',
              descripcion: 'Comprobante de Retención',
              cantidad: 1,
              precio_unitario: baseImponible,
              iva_codigo: '0',
              iva_porcentaje: 0,
            }]
          : items.map((item) => ({
              ...item,
              // Enviar el monto de descuento efectivo calculado (dólares)
              descuento: getItemDiscount(item) || undefined,
              descuento_tipo: item.descuento_tipo || undefined,
              descuento_valor: item.descuento_valor ?? undefined,
            }));

      const comprobanteData: ComprobanteCreate = {
        company_id: companyId,
        client_id: clientId,
        tipo_comprobante: tipoComprobante,
        forma_pago: formaPago,
        detalles,
        info_adicional: Object.keys(infoAdicional).length > 0 ? infoAdicional : undefined,
      };

      // NC/ND fields
      if (tipoComprobante === '04' || tipoComprobante === '05') {
        comprobanteData.comprobante_modificado_id = comprobanteModificadoId;
        comprobanteData.motivo_modificacion = motivoModificacion;
      }

      // Retención fields
      if (tipoComprobante === '07') {
        if (retencionIvaCodigo) {
          comprobanteData.retencion_iva_codigo = retencionIvaCodigo;
          comprobanteData.retencion_iva_porcentaje = retencionIvaPorcentaje;
        }
        if (retencionRentaCodigo) {
          comprobanteData.retencion_renta_codigo = retencionRentaCodigo;
          comprobanteData.retencion_renta_porcentaje = retencionRentaPorcentaje;
        }
      }

      await createComprobante(comprobanteData);
      toast.success('Comprobante creado exitosamente');
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al crear comprobante');
    } finally {
      setCreating(false);
    }
  }

  const steps = [
    { num: 1, label: 'Empresa' },
    { num: 2, label: 'Cliente' },
    { num: 3, label: 'Items' },
    { num: 4, label: 'Adicional' },
    { num: 5, label: 'Revisar' },
  ];

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {steps.map((s, i) => (
          <div key={s.num} className="flex items-center">
            <button
              onClick={() => s.num <= step && setStep(s.num as WizardStep)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                step === s.num
                  ? 'bg-primary text-primary-foreground'
                  : step > s.num
                  ? 'bg-primary/20 text-primary'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              <span className="h-5 w-5 rounded-full flex items-center justify-center border text-[10px]">
                {step > s.num ? <CheckCircle2 className="h-3 w-3" /> : s.num}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </button>
            {i < steps.length - 1 && <ChevronRight className="h-3 w-3 text-muted-foreground mx-1" />}
          </div>
        ))}
      </div>

      {/* Step Content */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Receipt className="h-4 w-4 text-primary" />
              Seleccionar Empresa y Tipo
            </CardTitle>
            <CardDescription>Seleccione la empresa emisora y el tipo de comprobante</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Empresa</Label>
                <div className="rounded-md border px-3 py-2 bg-muted text-sm">
                  {companies.find((c) => c.id === companyId)?.razon_social || 'Sin empresa'}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="tipo-comp">Tipo de Comprobante</Label>
                <Select value={tipoComprobante} onValueChange={setTipoComprobante}>
                  <SelectTrigger id="tipo-comp">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPOS_COMPROBANTE.map((t) => (
                      <SelectItem key={t.codigo} value={t.codigo}>
                        {t.codigo} - {t.descripcion}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <ClientSelector
          companyId={companyId}
          clients={clients}
          selectedClientId={clientId}
          onSelect={setClientId}
          onClientsUpdate={setClients}
        />
      )}

      {step === 3 && tipoComprobante === '07' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Receipt className="h-4 w-4 text-primary" />
              Datos de Retención
            </CardTitle>
            <CardDescription>Configure las retenciones y el período fiscal</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="periodo-fiscal">Período Fiscal (MM/YYYY)</Label>
                <NumericInput id="periodo-fiscal"
 placeholder="01/2025"
 value={periodoFiscal}
 onChange={(e) => setPeriodoFiscal(e.target.value)}
 />
 </div>
 <div className="space-y-2">
 <Label htmlFor="base-imponible">Base Imponible</Label>
 <NumericInput
 id="base-imponible"
 
 placeholder="0.00"
 value={baseImponible || ''}
 onChange={(e) => setBaseImponible(parseFloat(e.target.value) || 0)} />
              </div>
            </div>

            <Separator />

            <div>
              <h4 className="text-sm font-medium mb-3">Retención de IVA</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Código Retención IVA</Label>
                  <Select value={retencionIvaCodigo} onValueChange={(v) => { setRetencionIvaCodigo(v); const cat = sriCatalogs?.retencion_iva?.find(c => c.codigo === v); if (cat) { /* try to extract porcentaje from description */ const match = cat.descripcion.match(/(\d+)[%.]/); if (match) setRetencionIvaPorcentaje(parseFloat(match[1])); } }}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccione código" />
                    </SelectTrigger>
                    <SelectContent>
                      {sriCatalogs?.retencion_iva?.map((cat) => (
                        <SelectItem key={cat.codigo} value={cat.codigo}>
                          {cat.codigo} - {cat.descripcion}
                        </SelectItem>
                      )) || <SelectItem value="__loading" disabled>Cargando...</SelectItem>}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ret-iva-porc">Porcentaje IVA (%)</Label>
                  <NumericInput id="ret-iva-porc"
 
 value={retencionIvaPorcentaje || ''}
 onChange={(e) => setRetencionIvaPorcentaje(parseFloat(e.target.value) || 0)} />
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <h4 className="text-sm font-medium mb-3">Retención de Renta</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Código Retención Renta</Label>
                  <Select value={retencionRentaCodigo} onValueChange={(v) => { setRetencionRentaCodigo(v); const cat = sriCatalogs?.retencion_renta?.find(c => c.codigo === v); if (cat) { const match = cat.descripcion.match(/(\d+)[%.]/); if (match) setRetencionRentaPorcentaje(parseFloat(match[1])); } }}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccione código" />
                    </SelectTrigger>
                    <SelectContent>
                      {sriCatalogs?.retencion_renta?.map((cat) => (
                        <SelectItem key={cat.codigo} value={cat.codigo}>
                          {cat.codigo} - {cat.descripcion}
                        </SelectItem>
                      )) || <SelectItem value="__loading" disabled>Cargando...</SelectItem>}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ret-renta-porc">Porcentaje Renta (%)</Label>
                  <NumericInput id="ret-renta-porc"
 
 value={retencionRentaPorcentaje || ''}
 onChange={(e) => setRetencionRentaPorcentaje(parseFloat(e.target.value) || 0)} />
                </div>
              </div>
            </div>

            {baseImponible > 0 && (retencionIvaPorcentaje > 0 || retencionRentaPorcentaje > 0) && (
              <>
                <Separator />
                <div className="text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Base Imponible</span>
                    <span>${formatCurrency(baseImponible)}</span>
                  </div>
                  {retencionIvaPorcentaje > 0 && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Retención IVA ({retencionIvaPorcentaje}%)</span>
                      <span>-${formatCurrency(baseImponible * retencionIvaPorcentaje / 100)}</span>
                    </div>
                  )}
                  {retencionRentaPorcentaje > 0 && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Retención Renta ({retencionRentaPorcentaje}%)</span>
                      <span>-${formatCurrency(baseImponible * retencionRentaPorcentaje / 100)}</span>
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {step === 3 && tipoComprobante !== '07' && (
        <ItemsEditor
          items={items}
          onChange={setItems}
          products={products}
        />
      )}

      {step === 4 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Info className="h-4 w-4 text-primary" />
              Información Adicional
            </CardTitle>
            <CardDescription>Forma de pago e informacion adicional</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="forma-pago">Forma de Pago</Label>
              <Select value={formaPago} onValueChange={setFormaPago}>
                <SelectTrigger id="forma-pago">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FORMAS_PAGO.map((fp) => (
                    <SelectItem key={fp.codigo} value={fp.codigo}>
                      {fp.codigo} - {fp.descripcion}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Nota de Crédito/Débito additional fields */}
            {(tipoComprobante === '04' || tipoComprobante === '05') && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-medium mb-3">
                    {tipoComprobante === '04' ? 'Nota de Crédito' : 'Nota de Débito'} - Comprobante a Modificar
                  </h4>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="comp-modificado">Comprobante a Modificar</Label>
                      <Select value={comprobanteModificadoId} onValueChange={setComprobanteModificadoId}>
                        <SelectTrigger id="comp-modificado">
                          <SelectValue placeholder="Seleccione comprobante autorizado" />
                        </SelectTrigger>
                        <SelectContent>
                          {autorizados.length > 0 ? (
                            autorizados.map((aut) => (
                              <SelectItem key={aut.id} value={aut.id}>
                                {getTipoComprobanteLabel(aut.tipo_comprobante)} #{aut.secuencial} - {aut.cliente_razon_social} (${formatCurrency(aut.total_con_impuestos)})
                              </SelectItem>
                            ))
                          ) : (
                            <SelectItem value="__none" disabled>No hay comprobantes autorizados</SelectItem>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="motivo-mod">Motivo de Modificación *</Label>
                      <Textarea
                        id="motivo-mod"
                        placeholder="Describa el motivo de la nota de crédito/débito..."
                        value={motivoModificacion}
                        onChange={(e) => setMotivoModificacion(e.target.value)}
                        rows={3}
                      />
                    </div>
                  </div>
                </div>
              </>
            )}

            <Separator />

            <div>
              <Label>Información Adicional (opcional)</Label>
              <div className="mt-2 space-y-2">
                {Object.entries(infoAdicional).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Input value={key} disabled className="w-1/3" />
                    <Input value={value} disabled className="flex-1" />
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => removeInfoAdicional(key)}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
                <div className="flex items-center gap-2">
                  <NumericInput placeholder="Campo"
 value={newInfoKey}
 onChange={(e) => setNewInfoKey(e.target.value)}
 className="w-1/3"
 />
 <Input
 placeholder="Valor"
 value={newInfoValue}
 onChange={(e) => setNewInfoValue(e.target.value)}
 className="flex-1"
 />
 <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" onClick={addInfoAdicional}>
 <Plus className="h-3.5 w-3.5" />
 </Button>
 </div>
 </div>
 </div>
 </CardContent>
 </Card>
 )}

 {step === 5 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <CheckCircle2 className="h-4 w-4 text-primary" />
 Revisar y Crear
 </CardTitle>
 <CardDescription>Verifique los datos antes de crear el comprobante</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
 <div>
 <span className="text-muted-foreground">Tipo</span>
 <div className="font-medium">{getTipoComprobanteLabel(tipoComprobante)}</div>
 </div>
 <div>
 <span className="text-muted-foreground">Forma de Pago</span>
 <div className="font-medium">{FORMAS_PAGO.find((f) => f.codigo === formaPago)?.descripcion || formaPago}</div>
 </div>
 <div>
 <span className="text-muted-foreground">Cliente</span>
 <div className="font-medium">{clients.find((c) => c.id === clientId)?.razon_social || '-'}</div>
 </div>
 <div>
 <span className="text-muted-foreground">Identificación</span>
 <div className="font-mono text-xs">{clients.find((c) => c.id === clientId)?.identificacion || '-'}</div>
 </div>
 </div>

 <Separator />

 {/* Items summary */}
 <div>
 <h4 className="text-sm font-medium mb-2">Items ({items.length})</h4>
 <div className="rounded-md border">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Código</TableHead>
 <TableHead>Descripción</TableHead>
 <TableHead className="text-right">Cant.</TableHead>
 <TableHead className="text-right">P.Unit.</TableHead>
 <TableHead className="text-right">IVA</TableHead>
 <TableHead className="text-right">Subtotal</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {items.map((item, i) => (
 <TableRow key={i}>
 <TableCell className="font-mono text-xs">{item.codigo_principal}</TableCell>
 <TableCell className="max-w-[200px] truncate">{item.descripcion}</TableCell>
 <TableCell className="text-right">{item.cantidad}</TableCell>
 <TableCell className="text-right">${formatCurrency(item.precio_unitario)}</TableCell>
 <TableCell className="text-right">{item.iva_porcentaje}%</TableCell>
 <TableCell className="text-right font-medium">
 ${formatCurrency(getItemSubtotal(item))}
 </TableCell>
 </TableRow>
 ))}
 </TableBody>
 </Table>
 </div>
 </div>

 <Separator />

 {/* Totales en formato SRI */}
 <TotalesSRI totals={totals} />

 {Object.keys(infoAdicional).length > 0 && (
 <>
 <Separator />
 <div>
 <h4 className="text-sm font-medium mb-2">Info Adicional</h4>
 {Object.entries(infoAdicional).map(([k, v]) => (
 <div key={k} className="text-xs flex gap-2">
 <span className="text-muted-foreground">{k}:</span>
 <span>{v}</span>
 </div>
 ))}
 </div>
 </>
 )}
 </CardContent>
 </Card>
 )}

 {/* Navigation */}
 <div className="flex justify-between">
 <Button
 variant="outline"
 onClick={() => setStep((step - 1) as WizardStep)}
 disabled={step === 1}
 >
 <ChevronLeft className="mr-2 h-4 w-4" />
 Anterior
 </Button>
 {step < 5 ? (
 <Button
 onClick={() => setStep((step + 1) as WizardStep)}
 disabled={!canProceed()}
 >
 Siguiente
 <ChevronRight className="ml-2 h-4 w-4" />
 </Button>
 ) : (
 <Button
 onClick={handleCreate}
 disabled={creating || items.length === 0}
 className="bg-emerald-600 hover:bg-emerald-700"
 >
 {creating ? (
 <>
 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
 Creando...
 </>
 ) : (
 <>
 <CheckCircle2 className="mr-2 h-4 w-4" />
 Crear Comprobante
 </>
 )}
 </Button>
 )}
 </div>
 </div>
 );
}

// ─── Client Selector ────────────────────────────────────────────

function ClientSelector({
 companyId,
 clients,
 selectedClientId,
 onSelect,
 onClientsUpdate,
}: {
 companyId: string;
 clients: ClientResponse[];
 selectedClientId: string;
 onSelect: (id: string) => void;
 onClientsUpdate: (clients: ClientResponse[]) => void;
}) {
 const [search, setSearch] = useState('');
 const [showNewClient, setShowNewClient] = useState(false);
 const [newClient, setNewClient] = useState({
 tipo_identificacion: '05',
 identificacion: '',
 razon_social: '',
 direccion: '',
 email: '',
 telefono: '',
 });
 const [creatingClient, setCreatingClient] = useState(false);

 const filtered = clients.filter(
 (c) =>
 c.razon_social.toLowerCase().includes(search.toLowerCase()) ||
 c.identificacion.includes(search)
 );

 async function handleCreateClient() {
 setCreatingClient(true);
 try {
 const created = await createClient({
 company_id: companyId,
 ...newClient,
 });
 onClientsUpdate([...clients, created]);
 onSelect(created.id);
 setShowNewClient(false);
 setNewClient({
 tipo_identificacion: '05',
 identificacion: '',
 razon_social: '',
 direccion: '',
 email: '',
 telefono: '',
 });
 toast.success('Cliente creado exitosamente');
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al crear cliente');
 } finally {
 setCreatingClient(false);
 }
 }

 return (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Users className="h-4 w-4 text-primary" />
 Seleccionar Cliente
 </CardTitle>
 <CardDescription>Busque un cliente existente o cree uno nuevo</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="flex gap-2">
 <div className="relative flex-1">
 <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
 <Input
 placeholder="Buscar por nombre o identificacion..."
 value={search}
 onChange={(e) => setSearch(e.target.value)}
 className="pl-9"
 />
 </div>
 <Button variant="outline" onClick={() => setShowNewClient(true)}>
 <Plus className="mr-2 h-4 w-4" />
 Nuevo
 </Button>
 </div>

 <ScrollArea className="max-h-[300px]">
 <div className="space-y-2">
 {filtered.length > 0 ? (
 filtered.map((client) => (
 <button
 key={client.id}
 onClick={() => onSelect(client.id)}
 className={`w-full text-left rounded-md border p-3 transition-colors ${
 selectedClientId === client.id
 ? 'border-primary bg-primary/5'
 : 'hover:bg-accent/50'
 }`}
 >
 <div className="flex items-center justify-between">
 <div>
 <span className="font-medium text-sm">{client.razon_social}</span>
 <span className="text-xs text-muted-foreground ml-2 font-mono">
 {client.identificacion}
 </span>
 </div>
 {selectedClientId === client.id && (
 <CheckCircle2 className="h-4 w-4 text-primary" />
 )}
 </div>
 {client.email && (
 <p className="text-xs text-muted-foreground mt-1">{client.email}</p>
 )}
 </button>
 ))
 ) : (
 <p className="text-sm text-muted-foreground text-center py-4">
 No se encontraron clientes
 </p>
 )}
 </div>
 </ScrollArea>
 </CardContent>

 {/* New Client Dialog */}
 <Dialog open={showNewClient} onOpenChange={setShowNewClient}>
 <DialogContent className="sm:max-w-md">
 <DialogHeader>
 <DialogTitle>Nuevo Cliente</DialogTitle>
 <DialogDescription>Registre un nuevo cliente</DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Tipo Identificación</Label>
 <Select
 value={newClient.tipo_identificacion}
 onValueChange={(v) => setNewClient({ ...newClient, tipo_identificacion: v })}
 >
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {TIPOS_IDENTIFICACION.filter((t) => t.codigo !== '07').map((t) => (
 <SelectItem key={t.codigo} value={t.codigo}>
 {t.descripcion}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 <div className="space-y-2">
 <Label>Identificación</Label>
 <Input
 value={newClient.identificacion}
 onChange={(e) => setNewClient({ ...newClient, identificacion: e.target.value.replace(/\D/g, '').slice(0, 13) })}
 placeholder="1712345678"
 maxLength={13}
 inputMode="numeric"
 />
 </div>
 </div>
 <div className="space-y-2">
 <Label>Razón Social / Nombre</Label>
 <Input
 value={newClient.razon_social}
 onChange={(e) => setNewClient({ ...newClient, razon_social: e.target.value })}
 placeholder="Juan Perez"
 />
 </div>
 <div className="space-y-2">
 <Label>Dirección</Label>
 <Input
 value={newClient.direccion}
 onChange={(e) => setNewClient({ ...newClient, direccion: e.target.value })}
 placeholder="Av. Amazonas 123"
 />
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Email</Label>
 <Input
 type="email"
 value={newClient.email}
 onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
 placeholder="cliente@correo.com"
 />
 </div>
 <div className="space-y-2">
 <Label>Teléfono</Label>
 <Input
 value={newClient.telefono}
 onChange={(e) => setNewClient({ ...newClient, telefono: e.target.value })}
 placeholder="0991234567"
 />
 </div>
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setShowNewClient(false)}>
 Cancelar
 </Button>
 <Button
 onClick={handleCreateClient}
 disabled={creatingClient || !newClient.identificacion || !newClient.razon_social}
 >
 {creatingClient ? (
 <>
 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
 Creando...
 </>
 ) : (
 'Crear Cliente'
 )}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 </Card>
 );
}

// ─── Items Editor ────────────────────────────────────────────────

function ItemsEditor({
 items,
 onChange,
 products,
}: {
 items: ComprobanteDetalleCreate[];
 onChange: (items: ComprobanteDetalleCreate[]) => void;
 products: ProductResponse[];
}) {
 const [search, setSearch] = useState('');
 const [showSearch, setShowSearch] = useState(false);
 // Índice del item expandido: al agregar un nuevo item, los anteriores se contraen
 const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

 const filteredProducts = products.filter(
 (p) =>
 (p.descripcion || '').toLowerCase().includes(search.toLowerCase()) ||
 (p.codigo_principal || '').toLowerCase().includes(search.toLowerCase())
 );  function addFromProduct(product: ProductResponse) {
    // Si el IVA está incluido en el precio, extraer el precio base (sin IVA)
    // para que el comprobante muestre: base + IVA = precio total
    let precioBase = product.precio_unitario;
    if (product.iva_incluido && product.iva_porcentaje > 0) {
      precioBase = product.precio_unitario / (1 + product.iva_porcentaje / 100);
      precioBase = Math.round(precioBase * 100) / 100; // Redondear a 2 decimales
    }
    const newItem: ComprobanteDetalleCreate = {
      product_id: product.id,
      codigo_principal: product.codigo_principal,
      codigo_auxiliar: product.codigo_auxiliar || undefined,
      descripcion: product.descripcion,
      cantidad: 1,
      unidad_medida: product.unidad_medida,
      precio_unitario: precioBase,
      descuento: product.descuento || undefined,
      iva_codigo: product.iva_codigo,
      iva_porcentaje: product.iva_porcentaje,
    };
 const newItems = [...items, newItem];
 onChange(newItems);
 setExpandedIndex(newItems.length - 1);
 setShowSearch(false);
 setSearch('');
 }

 function addEmptyItem() {
 const newItem: ComprobanteDetalleCreate = {
 codigo_principal: '',
 descripcion: '',
 cantidad: 1,
 unidad_medida: 'Unidad',
 precio_unitario: 0,
 iva_codigo: '4',
 iva_porcentaje: 15,
 };
 const newItems = [...items, newItem];
 onChange(newItems);
 setExpandedIndex(newItems.length - 1);
 }

 function updateItem(index: number, updates: Partial<ComprobanteDetalleCreate>) {
 const newItems = [...items];
 newItems[index] = { ...newItems[index], ...updates };
 onChange(newItems);
 }

 function removeItem(index: number) {
 onChange(items.filter((_, i) => i !== index));
 }

 // Totales con desglose completo estilo SRI
 const totals = computeTotales(items);

 return (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Package className="h-4 w-4 text-primary" />
 Agregar Items
 </CardTitle>
 <CardDescription>Agregue productos o servicios al comprobante</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="flex gap-2">
 <Button variant="outline" onClick={() => setShowSearch(!showSearch)}>
 <Search className="mr-2 h-4 w-4" />
 Buscar Producto
 </Button>
 <Button variant="outline" onClick={addEmptyItem}>
 <Plus className="mr-2 h-4 w-4" />
 Ingreso Manual
 </Button>
 </div>

 {/* Product Search */}
 {showSearch && (
 <div className="space-y-2">
 <Input
 placeholder="Buscar por nombre o codigo..."
 value={search}
 onChange={(e) => setSearch(e.target.value)}
 />
 {filteredProducts.length > 0 ? (
 <ScrollArea className="max-h-[200px]">
 <div className="space-y-1">
 {filteredProducts.slice(0, 20).map((product) => (
 <button
 key={product.id}
 onClick={() => addFromProduct(product)}
 className="w-full text-left rounded-md border p-2 hover:bg-accent/50 transition-colors text-sm"
 >
 <div className="flex justify-between">
 <span className="font-medium">{product.descripcion}</span>
 <span className="text-muted-foreground">${formatCurrency(product.precio_unitario)}</span>
 </div>
 <span className="text-xs text-muted-foreground font-mono">
 {product.codigo_principal} | IVA {product.iva_porcentaje}%
 </span>
 </button>
 ))}
 </div>
 </ScrollArea>
 ) : (
 <p className="text-xs text-muted-foreground text-center py-2">
 No se encontraron productos. Intente ingreso manual.
 </p>
 )}
 </div>
 )}

 {/* Items List: colapsados salvo el item expandido */}
 {items.length > 0 ? (
 <div className="space-y-2">
 {items.map((item, i) => {
 const expanded = expandedIndex === i;
 return (
 <div key={i} className="rounded-md border">
 {/* Encabezado: clic para expandir/contraer */}
 <button
 type="button"
 onClick={() => setExpandedIndex(expanded ? null : i)}
 className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left hover:bg-accent/40 transition-colors"
 >
 <div className="flex items-center gap-2 min-w-0">
 {expanded ? (
 <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
 ) : (
 <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
 )}
 <span className="text-xs font-medium text-muted-foreground shrink-0">Item {i + 1}</span>
 <span className="text-sm font-medium truncate">
 {item.descripcion || item.codigo_principal || 'Sin descripción'}
 </span>
 </div>
 <div className="flex items-center gap-3 shrink-0">
 <span className="text-xs text-muted-foreground hidden sm:inline">
 {item.cantidad} × ${formatCurrency(item.precio_unitario)}
 </span>
 <span className="text-xs font-semibold">${formatCurrency(getItemSubtotal(item))}</span>
 <span
 role="button"
 tabIndex={0}
 aria-label="Eliminar item"
 onClick={(e) => { e.stopPropagation(); removeItem(i); }}
 onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); removeItem(i); } }}
 className="h-6 w-6 inline-flex items-center justify-center rounded hover:bg-destructive/10 text-destructive"
 >
 <X className="h-3.5 w-3.5" />
 </span>
 </div>
 </button>

 {expanded && (
 <div className="px-3 pb-3 space-y-3 border-t pt-3">
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
 <div className="space-y-1">
 <Label className="text-xs">Código Principal</Label>
 <Input
 value={item.codigo_principal}
 onChange={(e) => updateItem(i, { codigo_principal: e.target.value })}
 placeholder="COD001"
 className="h-8 text-sm"
 />
 </div>
 <div className="space-y-1 sm:col-span-2 lg:col-span-2">
 <Label className="text-xs">Descripción</Label>
 <Input
 value={item.descripcion}
 onChange={(e) => updateItem(i, { descripcion: e.target.value })}
 placeholder="Descripción del producto o servicio"
 className="h-8 text-sm"
 />
 </div>
 <div className="space-y-1">
 <Label className="text-xs">Cantidad</Label>
 <NumericInput integer
 
 value={item.cantidad}
 onChange={(e) => updateItem(i, { cantidad: parseFloat(e.target.value) || 0 })}
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Precio Unitario</Label>
                          <PriceInput
                            value={item.precio_unitario}
                            onChange={(v) => updateItem(i, { precio_unitario: v })}
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Tipo Descuento</Label>
                          <Select
                            value={item.descuento_tipo || 'dolares'}
                            onValueChange={(v) =>
                              updateItem(i, {
                                descuento_tipo: v as DescuentoTipo,
                                descuento: v === 'porcentaje' && item.descuento_valor != null
                                  ? (item.cantidad * item.precio_unitario * item.descuento_valor) / 100
                                  : item.descuento_valor ?? undefined,
                              })
                            }
                          >
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="dolares">Dólares ($)</SelectItem>
                              <SelectItem value="porcentaje">Porcentaje (%)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Descuento {item.descuento_tipo === 'porcentaje' ? '(%)' : '($)'}</Label>
                          <NumericInput value={item.descuento_valor ?? item.descuento ?? ''}
 onChange={(e) => {
 const v = parseFloat(e.target.value) || 0;
 updateItem(i, {
 descuento_valor: v,
 descuento:
 item.descuento_tipo === 'porcentaje'
 ? (item.cantidad * item.precio_unitario * v) / 100
 : v || undefined,
 });
 }}
 placeholder={item.descuento_tipo === 'porcentaje' ? '0' : '0.00'}
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">IRBPNR / unidad ($)</Label>
                          <NumericInput value={item.irbpnr_valor ?? ''}
 onChange={(e) => updateItem(i, { irbpnr_valor: parseFloat(e.target.value) || undefined })}
 placeholder="0.00"
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">ICE (%)</Label>
                          <NumericInput value={item.ice_porcentaje ?? ''}
 onChange={(e) => updateItem(i, { ice_porcentaje: parseFloat(e.target.value) || undefined })}
 placeholder="0"
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Tasa IVA</Label>
                          <Select
                            value={item.iva_codigo}
                            onValueChange={(v) => {
                              const rate = IVA_RATES.find((r) => r.codigo === v);
                              if (rate) {
                                updateItem(i, { iva_codigo: v, iva_porcentaje: rate.porcentaje });
                              }
                            }}
                          >
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {IVA_RATES.map((r) => (
                                <SelectItem key={r.codigo} value={r.codigo}>
                                  {r.descripcion} (cod. {r.codigo})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Unidad</Label>
                          <NumericInput value={item.unidad_medida || ''}
 onChange={(e) => updateItem(i, { unidad_medida: e.target.value })}
 placeholder="Unidad"
 className="h-8 text-sm"
 />
 </div>
 </div>
 {/* Item subtotal */}
 <div className="text-right text-xs text-muted-foreground">
 Subtotal: ${formatCurrency(getItemSubtotal(item))}
 {getItemDiscount(item) > 0 && (
 <span className="text-destructive"> - Desc. ${formatCurrency(getItemDiscount(item))}</span>
 )}
 {item.iva_porcentaje > 0 && (
 <span> + IVA ${formatCurrency(getItemSubtotal(item) * item.iva_porcentaje / 100)}</span>
 )}
 {(item.ice_porcentaje || 0) > 0 && (
 <span> + ICE ${formatCurrency(getItemSubtotal(item) * (item.ice_porcentaje || 0) / 100)}</span>
 )}
 {(item.irbpnr_valor || 0) > 0 && (
 <span> + IRBPNR ${formatCurrency((item.irbpnr_valor || 0) * item.cantidad)}</span>
 )}
 </div>
 </div>
 )}
 </div>
 );
 })}
 </div>
 ) : (
 <div className="text-center py-8 text-muted-foreground">
 <Package className="h-8 w-8 mx-auto mb-2" />
 <p className="text-sm">Agregue items al comprobante</p>
 </div>
 )}

 {/* Running Totals en formato SRI */}
 {items.length > 0 && (
 <TotalesSRI totals={totals} />
 )}
 </CardContent>
 </Card>
 );
}

// ─── Productos Tab ───────────────────────────────────────────────

function ProductosTab({ companyId }: { companyId: string }) {
 const [products, setProducts] = useState<ProductResponse[]>([]);
 const [loading, setLoading] = useState(true);
 const [showDialog, setShowDialog] = useState(false);
 const [editProduct, setEditProduct] = useState<ProductResponse | null>(null);
 const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
 const [saving, setSaving] = useState(false);
 const [search, setSearch] = useState('');

 const [form, setForm] = useState<ProductCreate>({
 company_id: companyId,
 codigo_principal: '',
 codigo_auxiliar: '',
 descripcion: '',
 tipo: 'B',
 precio_unitario: 0,
 iva_codigo: '4',
 iva_porcentaje: 15,
 iva_incluido: false,
 ice_codigo: '',
 ice_porcentaje: 0,
 valor_ice_unitario: 0,
 valor_irbpnr: 0,
 subsidio: 0,
 categoria: '',
 detalle: '',
 imagen: '',
 unidad_medida: 'Unidad',
 descuento: 0,
 });

 const loadProducts = useCallback(async () => {
 if (!companyId) return;
 setLoading(true);
 try {
 const data = await getProducts(companyId);
 // Guard defensivo: si la API devuelve algo que no es un array, no romper el render
 setProducts(Array.isArray(data) ? data : []);
 } catch {
 toast.error('Error al cargar productos');
 } finally {
 setLoading(false);
 }
 }, [companyId]);

 useEffect(() => {
 loadProducts();
 }, [loadProducts]);

 function openNewProduct() {
 setEditProduct(null);
 setForm({
 company_id: companyId,
 codigo_principal: '',
 codigo_auxiliar: '',
 descripcion: '',
 tipo: 'B',
 precio_unitario: 0,
 iva_codigo: '4',
 iva_porcentaje: 15,
 iva_incluido: false,
 ice_codigo: '',
 ice_porcentaje: 0,
 valor_ice_unitario: 0,
 valor_irbpnr: 0,
 subsidio: 0,
 categoria: '',
 detalle: '',
 imagen: '',
 unidad_medida: 'Unidad',
 descuento: 0,
 });
 setShowDialog(true);
 }

 function openEditProduct(product: ProductResponse) {
 setEditProduct(product);
 setForm({
 company_id: product.company_id,
 codigo_principal: product.codigo_principal,
 codigo_auxiliar: product.codigo_auxiliar || '',
 descripcion: product.descripcion,
 tipo: product.tipo,
 precio_unitario: product.precio_unitario,
 iva_codigo: product.iva_codigo,
 iva_porcentaje: product.iva_porcentaje,
 iva_incluido: product.iva_incluido || false,
 ice_codigo: product.ice_codigo || '',
 ice_porcentaje: product.ice_porcentaje || 0,
 valor_ice_unitario: product.valor_ice_unitario || 0,
 valor_irbpnr: product.valor_irbpnr || 0,
 subsidio: product.subsidio || 0,
 categoria: product.categoria || '',
 detalle: product.detalle || '',
 imagen: product.imagen || '',
 unidad_medida: product.unidad_medida,
 descuento: product.descuento,
 });
 setShowDialog(true);
 }

 async function handleSave() {
 setSaving(true);
 try {
 if (editProduct) {
 await updateProduct(editProduct.id, form);
 toast.success('Producto actualizado');
 } else {
 await createProduct(form);
 toast.success('Producto creado');
 }
 setShowDialog(false);
 loadProducts();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al guardar producto');
 } finally {
 setSaving(false);
 }
 }

 async function handleDelete(id: string) {
 try {
 await deleteProduct(id);
 toast.success('Producto eliminado');
 setDeleteConfirm(null);
 loadProducts();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al eliminar');
 }
 }

 const filtered = products.filter(
 (p) =>
 (p.descripcion || '').toLowerCase().includes(search.toLowerCase()) ||
 (p.codigo_principal || '').toLowerCase().includes(search.toLowerCase())
 );

 if (loading) {
 return (
 <div className="flex items-center justify-center h-48">
 <Loader2 className="h-8 w-8 animate-spin text-primary" />
 </div>
 );
 }

 return (
 <div className="space-y-4">
 <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
 <div className="relative flex-1 max-w-sm">
 <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
 <Input
 placeholder="Buscar productos..."
 value={search}
 onChange={(e) => setSearch(e.target.value)}
 className="pl-9"
 />
 </div>
 <Button onClick={openNewProduct}>
 <Plus className="mr-2 h-4 w-4" />
 Nuevo Producto
 </Button>
 </div>

 {filtered.length > 0 ? (
 <Card>
 <CardContent className="p-0">
 <ScrollArea className="max-h-[500px]">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Código</TableHead>
 <TableHead>Descripción</TableHead>
 <TableHead>Tipo</TableHead>
 <TableHead className="text-right">Precio</TableHead>
 <TableHead>IVA</TableHead>
 <TableHead className="text-right">Acciones</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {filtered.map((product) => (
 <TableRow key={product.id}>
 <TableCell className="font-mono text-xs">{product.codigo_principal}</TableCell>
 <TableCell className="max-w-[200px] truncate">{product.descripcion}</TableCell>
 <TableCell>
 <Badge variant="outline" className="text-xs">
 {product.tipo === 'B' ? 'Bien' : 'Servicio'}
 </Badge>
 </TableCell>
 <TableCell className="text-right font-medium">
 ${formatCurrency(product.precio_unitario)}
 </TableCell>
 <TableCell>
 <Badge variant="secondary" className="text-xs">
 {product.iva_porcentaje}%
 </Badge>
 </TableCell>
 <TableCell className="text-right">
 <div className="flex justify-end gap-1">
 <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditProduct(product)}>
 <Pencil className="h-3.5 w-3.5" />
 </Button>
 <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => setDeleteConfirm(product.id)}>
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
 <Package className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
 <h3 className="text-lg font-medium">Sin productos</h3>
 <p className="text-muted-foreground text-sm mt-1">
 Registre productos para agilizar la creacion de comprobantes
 </p>
 <Button className="mt-4" onClick={openNewProduct}>
 <Plus className="mr-2 h-4 w-4" />
 Registrar Producto
 </Button>
 </CardContent>
 </Card>
 )}

 {/* Product Create/Edit Dialog */}
 <Dialog open={showDialog} onOpenChange={setShowDialog}>
 <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
 <DialogHeader>
 <DialogTitle>{editProduct ? 'Editar Producto' : 'Nuevo Producto'}</DialogTitle>
 <DialogDescription>
 {editProduct ? 'Modifique los datos del producto' : 'Registre un nuevo producto o servicio'}
 </DialogDescription>
 </DialogHeader>
 <ScrollArea className="max-h-[60vh] pr-4">
 <div className="space-y-4">
 {/* Row 1: Categoria, Imagen */}
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Categoria</Label>
 <Input
 value={form.categoria || ''}
 onChange={(e) => setForm({ ...form, categoria: e.target.value })}
 placeholder="General"
 />
 </div>
 <div className="space-y-2">
 <Label>Imagen (URL)</Label>
 <Input
 value={form.imagen || ''}
 onChange={(e) => setForm({ ...form, imagen: e.target.value })}
 placeholder="/images/product.png"
 />
 </div>
 </div>

 {/* Row 2: Código Principal, Código Auxiliar */}
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Código Principal *</Label>
 <Input
 value={form.codigo_principal}
 onChange={(e) => setForm({ ...form, codigo_principal: e.target.value })}
 placeholder="COD001"
 required
 />
 </div>
 <div className="space-y-2">
 <Label>Código Auxiliar</Label>
 <Input
 value={form.codigo_auxiliar || ''}
 onChange={(e) => setForm({ ...form, codigo_auxiliar: e.target.value })}
 placeholder="Opcional"
 />
 </div>
 </div>

 {/* Row 3: Nombre (descripcion) */}
 <div className="space-y-2">
 <Label>Nombre *</Label>
 <Input
 value={form.descripcion}
 onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
 placeholder="Nombre del producto o servicio"
 required
 />
 </div>

 {/* Row 4: Precio Unitario, Subsidio */}
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Precio Unitario</Label>
 <NumericInput
 
 value={form.precio_unitario}
 onChange={(e) => setForm({ ...form, precio_unitario: parseFloat(e.target.value) || 0 })} />
              </div>
              <div className="space-y-2">
                <Label>Subsidio</Label>
                <NumericInput value={form.subsidio || 0}
 onChange={(e) => setForm({ ...form, subsidio: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>

            {/* Row 5: IVA, IVA Incluido */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>IVA</Label>
                <Select
                  value={form.iva_codigo}
                  onValueChange={(v) => {
                    const rate = IVA_RATES.find((r) => r.codigo === v);
                    if (rate) setForm({ ...form, iva_codigo: v, iva_porcentaje: rate.porcentaje });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {IVA_RATES.map((r) => (
                      <SelectItem key={r.codigo} value={r.codigo}>
                        {r.descripcion} (cod. {r.codigo})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 flex items-end pb-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.iva_incluido || false}
                    onChange={(e) => setForm({ ...form, iva_incluido: e.target.checked })}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">IVA incluido en precio</span>
                </label>
              </div>
            </div>

            {/* Row 6: ICE, Valor ICE Unitario (conditional) */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>ICE</Label>
                <Select
                  value={form.ice_codigo || '__none__'}
                  onValueChange={(v) => {
                    setForm({ ...form, ice_codigo: v === '__none__' ? undefined : v });
                    if (!v || v === '__none__') setForm({ ...form, ice_codigo: undefined, valor_ice_unitario: 0 });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sin ICE" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">Sin ICE</SelectItem>
                    <SelectItem value="1">Código 1</SelectItem>
                    <SelectItem value="2">Código 2</SelectItem>
                    <SelectItem value="3">Código 3</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {form.ice_codigo && (
                <div className="space-y-2">
                  <Label>Valor ICE Unitario</Label>
                  <NumericInput value={form.valor_ice_unitario || 0}
 onChange={(e) => setForm({ ...form, valor_ice_unitario: parseFloat(e.target.value) || 0 })} />
                </div>
              )}
            </div>

            {/* Row 7: Valor IRBPNR */}
            <div className="space-y-2">
              <Label>Valor IRBP_NR</Label>
              <NumericInput value={form.valor_irbpnr || 0}
 onChange={(e) => setForm({ ...form, valor_irbpnr: parseFloat(e.target.value) || 0 })} />
            </div>

            {/* Row 8: Detalle, Descripción */}
            <div className="space-y-2">
              <Label>Detalle</Label>
              <Textarea
                value={form.detalle || ''}
                onChange={(e) => setForm({ ...form, detalle: e.target.value })}
                placeholder="Detalle adicional del producto"
                rows={2}
              />
            </div>

            {/* Row 9: Tipo, Unidad de Medida */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="B">Bien</SelectItem>
                    <SelectItem value="S">Servicio</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Unidad de Medida</Label>
                <Input value={form.unidad_medida || ''}
 onChange={(e) => setForm({ ...form, unidad_medida: e.target.value })}
 placeholder="Unidad"
 />
 </div>
 </div>
 </div>
 </ScrollArea>
 <DialogFooter>
 <Button variant="outline" onClick={() => setShowDialog(false)}>
 Cancelar
 </Button>
 <Button onClick={handleSave} disabled={saving || !form.codigo_principal || !form.descripcion}>
 {saving ? (
 <>
 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
 Guardando...
 </>
 ) : (
 'Guardar'
 )}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* Delete Confirmation */}
 <AlertDialog open={!!deleteConfirm} onOpenChange={(o) => !o && setDeleteConfirm(null)}>
 <AlertDialogContent>
 <AlertDialogHeader>
 <AlertDialogTitle>Eliminar producto</AlertDialogTitle>
 <AlertDialogDescription>
 Esta seguro de que desea eliminar este producto? El producto sera desactivado.
 </AlertDialogDescription>
 </AlertDialogHeader>
 <AlertDialogFooter>
 <AlertDialogCancel>Cancelar</AlertDialogCancel>
 <AlertDialogAction
 className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
 onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
 >
 Eliminar
 </AlertDialogAction>
 </AlertDialogFooter>
 </AlertDialogContent>
 </AlertDialog>
 </div>
 );
}

// ─── Clientes Tab ────────────────────────────────────────────────

function ClientesTab({ companyId }: { companyId: string }) {
 const [clients, setClients] = useState<ClientResponse[]>([]);
 const [loading, setLoading] = useState(true);
 const [showDialog, setShowDialog] = useState(false);
 const [editClient, setEditClient] = useState<ClientResponse | null>(null);
 const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
 const [saving, setSaving] = useState(false);
 const [search, setSearch] = useState('');

 const [form, setForm] = useState<ClientCreate>({
 company_id: companyId,
 tipo_identificacion: '05',
 identificacion: '',
 razon_social: '',
 direccion: '',
 email: '',
 telefono: '',
 });

 const loadClients = useCallback(async () => {
 if (!companyId) return;
 setLoading(true);
 try {
 const data = await getClients(companyId);
 // Guard defensivo: si la API devuelve algo que no es un array, no romper el render
 setClients(Array.isArray(data) ? data : []);
 } catch {
 toast.error('Error al cargar clientes');
 } finally {
 setLoading(false);
 }
 }, [companyId]);

 useEffect(() => {
 loadClients();
 }, [loadClients]);

 function openNewClient() {
 setEditClient(null);
 setForm({
 company_id: companyId,
 tipo_identificacion: '05',
 identificacion: '',
 razon_social: '',
 direccion: '',
 email: '',
 telefono: '',
 });
 setShowDialog(true);
 }

 function openEditClient(client: ClientResponse) {
 setEditClient(client);
 setForm({
 company_id: client.company_id,
 tipo_identificacion: client.tipo_identificacion,
 identificacion: client.identificacion,
 razon_social: client.razon_social,
 direccion: client.direccion || '',
 email: client.email || '',
 telefono: client.telefono || '',
 });
 setShowDialog(true);
 }

 async function handleSave() {
 setSaving(true);
 try {
 if (editClient) {
 await updateClient(editClient.id, form);
 toast.success('Cliente actualizado');
 } else {
 await createClient(form);
 toast.success('Cliente creado');
 }
 setShowDialog(false);
 loadClients();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al guardar cliente');
 } finally {
 setSaving(false);
 }
 }

 async function handleDelete(id: string) {
 try {
 await deleteClient(id);
 toast.success('Cliente eliminado');
 setDeleteConfirm(null);
 loadClients();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al eliminar');
 }
 }

 const filtered = clients.filter(
 (c) =>
 c.razon_social.toLowerCase().includes(search.toLowerCase()) ||
 c.identificacion.includes(search)
 );

 if (loading) {
 return (
 <div className="flex items-center justify-center h-48">
 <Loader2 className="h-8 w-8 animate-spin text-primary" />
 </div>
 );
 }

 return (
 <div className="space-y-4">
 <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
 <div className="relative flex-1 max-w-sm">
 <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
 <Input
 placeholder="Buscar clientes..."
 value={search}
 onChange={(e) => setSearch(e.target.value)}
 className="pl-9"
 />
 </div>
 <Button onClick={openNewClient}>
 <Plus className="mr-2 h-4 w-4" />
 Nuevo Cliente
 </Button>
 </div>

 {filtered.length > 0 ? (
 <Card>
 <CardContent className="p-0">
 <ScrollArea className="max-h-[500px]">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Identificación</TableHead>
 <TableHead>Razón Social</TableHead>
 <TableHead>Email</TableHead>
 <TableHead>Teléfono</TableHead>
 <TableHead className="text-right">Acciones</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {filtered.map((client) => (
 <TableRow key={client.id}>
 <TableCell>
 <div className="flex items-center gap-2">
 <span className="font-mono text-xs">{client.identificacion}</span>
 {client.is_default_consumer && (
 <Badge variant="outline" className="text-[10px]">CF</Badge>
 )}
 </div>
 </TableCell>
 <TableCell className="font-medium">{client.razon_social}</TableCell>
 <TableCell className="text-muted-foreground text-xs">{client.email || '-'}</TableCell>
 <TableCell className="text-muted-foreground text-xs">{client.telefono || '-'}</TableCell>
 <TableCell className="text-right">
 {!client.is_default_consumer && (
 <div className="flex justify-end gap-1">
 <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditClient(client)}>
 <Pencil className="h-3.5 w-3.5" />
 </Button>
 <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => setDeleteConfirm(client.id)}>
 <Trash2 className="h-3.5 w-3.5" />
 </Button>
 </div>
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
 <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
 <h3 className="text-lg font-medium">Sin clientes</h3>
 <p className="text-muted-foreground text-sm mt-1">
 Registre clientes para emitir comprobantes
 </p>
 <Button className="mt-4" onClick={openNewClient}>
 <Plus className="mr-2 h-4 w-4" />
 Registrar Cliente
 </Button>
 </CardContent>
 </Card>
 )}

 {/* Client Create/Edit Dialog */}
 <Dialog open={showDialog} onOpenChange={setShowDialog}>
 <DialogContent className="sm:max-w-md">
 <DialogHeader>
 <DialogTitle>{editClient ? 'Editar Cliente' : 'Nuevo Cliente'}</DialogTitle>
 <DialogDescription>
 {editClient ? 'Modifique los datos del cliente' : 'Registre un nuevo cliente'}
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Tipo Identificación</Label>
 <Select
 value={form.tipo_identificacion}
 onValueChange={(v) => setForm({ ...form, tipo_identificacion: v })}
 >
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {TIPOS_IDENTIFICACION.filter((t) => t.codigo !== '07').map((t) => (
 <SelectItem key={t.codigo} value={t.codigo}>
 {t.descripcion}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 <div className="space-y-2">
 <Label>Identificación</Label>
 <Input
 value={form.identificacion}
 onChange={(e) => setForm({ ...form, identificacion: e.target.value.replace(/\D/g, '').slice(0, 13) })}
 placeholder="1712345678"
 maxLength={13}
 inputMode="numeric"
 />
 </div>
 </div>
 <div className="space-y-2">
 <Label>Razón Social / Nombre</Label>
 <Input
 value={form.razon_social}
 onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
 placeholder="Juan Perez"
 />
 </div>
 <div className="space-y-2">
 <Label>Dirección</Label>
 <Input
 value={form.direccion || ''}
 onChange={(e) => setForm({ ...form, direccion: e.target.value })}
 placeholder="Av. Amazonas 123"
 />
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Email</Label>
 <Input
 type="email"
 value={form.email || ''}
 onChange={(e) => setForm({ ...form, email: e.target.value })}
 placeholder="cliente@correo.com"
 />
 </div>
 <div className="space-y-2">
 <Label>Teléfono</Label>
 <Input
 value={form.telefono || ''}
 onChange={(e) => setForm({ ...form, telefono: e.target.value })}
 placeholder="0991234567"
 pattern="[0-9]*"
 inputMode="numeric"
 />
 </div>
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setShowDialog(false)}>
 Cancelar
 </Button>
 <Button onClick={handleSave} disabled={saving || !form.identificacion || !form.razon_social}>
 {saving ? (
 <>
 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
 Guardando...
 </>
 ) : (
 'Guardar'
 )}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* Delete Confirmation */}
 <AlertDialog open={!!deleteConfirm} onOpenChange={(o) => !o && setDeleteConfirm(null)}>
 <AlertDialogContent>
 <AlertDialogHeader>
 <AlertDialogTitle>Eliminar cliente</AlertDialogTitle>
 <AlertDialogDescription>
 Esta seguro de que desea eliminar este cliente? El cliente sera desactivado.
 No se puede eliminar el cliente Consumidor Final.
 </AlertDialogDescription>
 </AlertDialogHeader>
 <AlertDialogFooter>
 <AlertDialogCancel>Cancelar</AlertDialogCancel>
 <AlertDialogAction
 className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
 onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
 >
 Eliminar
 </AlertDialogAction>
 </AlertDialogFooter>
 </AlertDialogContent>
 </AlertDialog>
 </div>
 );
}

// ─── Proforma Estado Badge ──────────────────────────────────────

function getProformaEstadoBadge(estado: string) {
 switch (estado.toUpperCase()) {
 case 'BORRADOR':
 return <Badge variant="secondary">Borrador</Badge>;
 case 'CERRADA':
 return <Badge className="bg-primary hover:bg-primary/90">Cerrada</Badge>;
 case 'ENVIADA':
 return <Badge className="bg-sky-600 hover:bg-sky-700">Enviada</Badge>;
 case 'ACEPTADA':
 return <Badge className="bg-emerald-600 hover:bg-emerald-700">Aceptada</Badge>;
 case 'RECHAZADA':
 return <Badge variant="destructive">Rechazada</Badge>;
 case 'CONVERTIDA':
 return <Badge className="bg-primary hover:bg-primary/90">Convertida</Badge>;
 default:
 return <Badge variant="outline">{estado}</Badge>;
 }
}

// ─── Proformas Tab ──────────────────────────────────────────────

function ProformasTab({ companyId, onNewProforma }: { companyId: string; onNewProforma: () => void }) {
 const [proformas, setProformas] = useState<ProformaListResponse[]>([]);
 const [stats, setStats] = useState<ProformaStatsResponse | null>(null);
 const [loading, setLoading] = useState(true);
 const [filterEstado, setFilterEstado] = useState<string>('all');
 const [actionLoading, setActionLoading] = useState<string | null>(null);
 const [detailDialog, setDetailDialog] = useState<{ open: boolean; data: ProformaResponse | null }>({ open: false, data: null });
 const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
 const [detailLoading, setDetailLoading] = useState(false);
 const [convertirDialog, setConvertirDialog] = useState<{ open: boolean; proformaId: string; secuencial: string }>({ open: false, proformaId: '', secuencial: '' });

 const loadData = useCallback(async () => {
 if (!companyId) return;
 setLoading(true);
 try {
 const [profs, st] = await Promise.all([
 getProformas({
 company_id: companyId,
 estado: filterEstado !== 'all' ? filterEstado : undefined,
 }),
 getProformaStats(companyId),
 ]);
 setProformas(profs);
 setStats(st);
 } catch {
 toast.error('Error al cargar proformas');
 } finally {
 setLoading(false);
 }
 }, [companyId, filterEstado]);

 useEffect(() => {
 loadData();
 }, [loadData]);

 async function handleAction(action: string, id: string) {
 setActionLoading(id + action);
 try {
 switch (action) {
 case 'detalle': {
 setDetailLoading(true);
 const prof = await getProforma(id);
 setDetailDialog({ open: true, data: prof });
 setActionLoading(null);
 setDetailLoading(false);
 return;
 }
 case 'enviar': {
 const result = await enviarProforma(id);
 toast.success(result.message || 'Proforma enviada exitosamente');
 // Si el cliente no tiene correo, ofrecer/descargar el PDF de la proforma
 if (result.download_available && !result.email_sent) {
 try {
 const blob = await downloadProformaPDF(id);
 const url = window.URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = `Proforma_${id}.pdf`;
 document.body.appendChild(a);
 a.click();
 document.body.removeChild(a);
 window.URL.revokeObjectURL(url);
 } catch {
 // El PDF se puede descargar manualmente desde el detalle
 }
 }
 break;
 }
 case 'convertir': {
 const prof = proformas.find((p) => p.id === id);
 setConvertirDialog({ open: true, proformaId: id, secuencial: prof?.secuencial || '' });
 setActionLoading(null);
 return;
 }
 case 'convertir-confirm': {
 const result = await convertirProforma(id);
 toast.success(`Proforma convertida a comprobante #${result.secuencial}`);
 setConvertirDialog({ ...convertirDialog, open: false });
 break;
 }
 case 'download-pdf': {
 const blob = await downloadProformaPDF(id);
 const url = window.URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = `Proforma_${id}.pdf`;
 document.body.appendChild(a);
 a.click();
 document.body.removeChild(a);
 window.URL.revokeObjectURL(url);
 toast.success('PDF de proforma descargado');
 break;
 }
 }
 loadData();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error en la operacion');
 } finally {
 setActionLoading(null);
 setDetailLoading(false);
 }
 }

 async function handleDelete(id: string) {
 try {
 await deleteProforma(id);
 toast.success('Proforma eliminada');
 setDeleteConfirm(null);
 loadData();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al eliminar');
 }
 }

 if (loading) {
 return (
 <div className="flex items-center justify-center h-48">
 <Loader2 className="h-8 w-8 animate-spin text-primary" />
 </div>
 );
 }

 return (
 <div className="space-y-4">
 {/* Header */}
 <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
 <div>
 <h3 className="text-lg font-semibold">Proformas</h3>
 <p className="text-sm text-muted-foreground">Gestione sus proformas y conviertalas a facturas</p>
 </div>
 <Button onClick={onNewProforma}>
 <Plus className="mr-2 h-4 w-4" />
 Nueva Proforma
 </Button>
 </div>

 {/* Stats Cards */}
 {stats && (
 <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold">{stats.total}</div>
 <p className="text-xs text-muted-foreground">Total</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold">{stats.borrador}</div>
 <p className="text-xs text-muted-foreground">Borradores</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-primary">{stats.cerrada ?? 0}</div>
 <p className="text-xs text-muted-foreground">Cerradas</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-sky-600">{stats.enviada}</div>
 <p className="text-xs text-muted-foreground">Enviadas</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-emerald-600">{stats.aceptada}</div>
 <p className="text-xs text-muted-foreground">Aceptadas</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-destructive">{stats.rechazada}</div>
 <p className="text-xs text-muted-foreground">Rechazadas</p>
 </div>
 </Card>
 <Card className="p-3">
 <div className="text-center">
 <div className="text-lg font-bold text-primary">{stats.convertida}</div>
 <p className="text-xs text-muted-foreground">Convertidas</p>
 </div>
 </Card>
 </div>
 )}

 {/* Filters */}
 <div className="flex flex-wrap gap-3 items-center">
 <Select value={filterEstado} onValueChange={setFilterEstado}>
 <SelectTrigger className="w-[180px]">
 <SelectValue placeholder="Estado" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">Todos los estados</SelectItem>
 <SelectItem value="BORRADOR">Borrador</SelectItem>
 <SelectItem value="CERRADA">Cerrada</SelectItem>
 <SelectItem value="ENVIADA">Enviada</SelectItem>
 <SelectItem value="ACEPTADA">Aceptada</SelectItem>
 <SelectItem value="RECHAZADA">Rechazada</SelectItem>
 <SelectItem value="CONVERTIDA">Convertida</SelectItem>
 </SelectContent>
 </Select>
 <Button variant="outline" size="icon" onClick={loadData}>
 <RefreshCw className="h-4 w-4" />
 </Button>
 </div>

 {/* Table */}
 {proformas.length > 0 ? (
 <Card>
 <CardContent className="p-0">
 <ScrollArea className="max-h-[500px]">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Secuencial</TableHead>
 <TableHead>Cliente</TableHead>
 <TableHead>Fecha Emisión</TableHead>
 <TableHead>Validez</TableHead>
 <TableHead className="text-right">Total</TableHead>
 <TableHead>Estado</TableHead>
 <TableHead className="text-right">Acciones</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {proformas.map((prof) => (
 <TableRow key={prof.id}>
 <TableCell className="font-mono text-xs">{prof.secuencial}</TableCell>
 <TableCell className="max-w-[150px] truncate">{prof.cliente_razon_social}</TableCell>
 <TableCell className="text-xs">
 {new Date(prof.fecha_emision).toLocaleDateString('es-EC')}
 </TableCell>
 <TableCell className="text-xs">
 {prof.fecha_validez ? new Date(prof.fecha_validez).toLocaleDateString('es-EC') : '-'}
 </TableCell>
 <TableCell className="text-right font-medium">
 ${formatCurrency(prof.total_con_impuestos)}
 </TableCell>
 <TableCell>{getProformaEstadoBadge(prof.estado)}</TableCell>
 <TableCell className="text-right">
 <div className="flex justify-end gap-1">
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7"
 onClick={() => handleAction('detalle', prof.id)}
 disabled={!!actionLoading || detailLoading}
 title="Ver detalle"
 >
 {detailLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
 </Button>
 {(prof.estado.toUpperCase() === 'BORRADOR' || prof.estado.toUpperCase() === 'CERRADA') && (
 <>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-sky-600"
 onClick={() => handleAction('enviar', prof.id)}
 disabled={!!actionLoading}
 title="Enviar proforma por correo al cliente"
 >
 {actionLoading === prof.id + 'enviar' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Send className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('download-pdf', prof.id)}
 disabled={!!actionLoading}
 title="Descargar PDF"
 >
 {actionLoading === prof.id + 'download-pdf' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <Download className="h-3.5 w-3.5" />
 )}
 </Button>
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-destructive"
 onClick={() => setDeleteConfirm(prof.id)}
 disabled={!!actionLoading}
 title="Eliminar"
 >
 <Trash2 className="h-3.5 w-3.5" />
 </Button>
 </>
 )}
 {(prof.estado.toUpperCase() === 'ENVIADA' || prof.estado.toUpperCase() === 'ACEPTADA') && (
 <Button
 variant="ghost"
 size="icon"
 className="h-7 w-7 text-emerald-600"
 onClick={() => handleAction('convertir', prof.id)}
 disabled={!!actionLoading}
 title="Convertir a Factura"
 >
 {actionLoading === prof.id + 'convertir' ? (
 <Loader2 className="h-3.5 w-3.5 animate-spin" />
 ) : (
 <ArrowRightLeft className="h-3.5 w-3.5" />
 )}
 </Button>
 )}
 {prof.estado.toUpperCase() === 'CONVERTIDA' && (
 <Badge variant="outline" className="text-xs">
 Factura
 </Badge>
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
 <h3 className="text-lg font-medium">Sin proformas</h3>
 <p className="text-muted-foreground text-sm mt-1">
 Cree su primera proforma para comenzar
 </p>
 <Button className="mt-4" onClick={onNewProforma}>
 <Plus className="mr-2 h-4 w-4" />
 Nueva Proforma
 </Button>
 </CardContent>
 </Card>
 )}

 {/* Detail Dialog */}
 <Dialog open={detailDialog.open} onOpenChange={(o) => setDetailDialog({ ...detailDialog, open: o })}>
 <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
 <DialogHeader>
 <DialogTitle>Detalle de Proforma</DialogTitle>
 <DialogDescription>
 {detailDialog.data ? `Proforma #${detailDialog.data.secuencial}` : ''}
 </DialogDescription>
 </DialogHeader>
 {detailDialog.data && <ProformaDetailView prof={detailDialog.data} />}
 {detailDialog.data && (
 <div className="flex justify-end gap-2 pt-2 border-t">
 <Button
 variant="outline"
 onClick={async () => {
 try {
 const id = detailDialog.data?.id;
 if (!id) return;
 const blob = await downloadProformaPDF(id);
 const url = window.URL.createObjectURL(blob);
 window.open(url, '_blank');
 setTimeout(() => window.URL.revokeObjectURL(url), 30000);
 } catch {
 toast.error('No se pudo generar el PDF');
 }
 }}
 >
 <FileText className="mr-2 h-4 w-4" />
 Ver PDF
 </Button>
 <Button onClick={() => setDetailDialog({ ...detailDialog, open: false })}>
 Cerrar
 </Button>
 </div>
 )}
 </DialogContent>
 </Dialog>

 {/* Delete Confirmation */}
 <AlertDialog open={!!deleteConfirm} onOpenChange={(o) => !o && setDeleteConfirm(null)}>
 <AlertDialogContent>
 <AlertDialogHeader>
 <AlertDialogTitle>Eliminar proforma</AlertDialogTitle>
 <AlertDialogDescription>
 Esta seguro de que desea eliminar esta proforma? Solo se pueden eliminar proformas en estado Borrador.
 </AlertDialogDescription>
 </AlertDialogHeader>
 <AlertDialogFooter>
 <AlertDialogCancel>Cancelar</AlertDialogCancel>
 <AlertDialogAction
 className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
 onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
 >
 Eliminar
 </AlertDialogAction>
 </AlertDialogFooter>
 </AlertDialogContent>
 </AlertDialog>

 {/* Convert to Invoice Dialog */}
 <Dialog open={convertirDialog.open} onOpenChange={(o) => setConvertirDialog({ ...convertirDialog, open: o })}>
 <DialogContent className="sm:max-w-md">
 <DialogHeader>
 <DialogTitle>Convertir Proforma a Factura</DialogTitle>
 <DialogDescription>
 La proforma #{convertirDialog.secuencial} sera convertida en un comprobante electronico (Factura).
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-3">
 <div className="flex items-start gap-3 p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
 <ArrowRightLeft className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
 <div>
 <p className="font-medium text-emerald-800 dark:text-emerald-200 text-sm">Conversion a Factura</p>
 <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
 Se creara una nueva factura con los mismos datos de la proforma. La proforma cambiara a estado CONVERTIDA.
 </p>
 </div>
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setConvertirDialog({ ...convertirDialog, open: false })}>
 Cancelar
 </Button>
 <Button
 onClick={() => handleAction('convertir-confirm', convertirDialog.proformaId)}
 disabled={!!actionLoading}
 className="bg-emerald-600 hover:bg-emerald-700"
 >
 {actionLoading === convertirDialog.proformaId + 'convertir-confirm' ? (
 <>
 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
 Convirtiendo...
 </>
 ) : (
 <>
 <ArrowRightLeft className="mr-2 h-4 w-4" />
 Convertir a Factura
 </>
 )}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 </div>
 );
}

// ─── Proforma Detail View ───────────────────────────────────────

function ProformaDetailView({ prof }: { prof: ProformaResponse }) {
 return (
 <ScrollArea className="max-h-[65vh]">
 <div className="space-y-4">
 <div className="grid grid-cols-2 gap-4 text-sm">
 <div>
 <span className="text-muted-foreground">Estado</span>
 <div className="mt-1">{getProformaEstadoBadge(prof.estado)}</div>
 </div>
 <div>
 <span className="text-muted-foreground">Fecha Emisión</span>
 <div className="mt-1">{new Date(prof.fecha_emision).toLocaleString('es-EC')}</div>
 </div>
 <div>
 <span className="text-muted-foreground">Cliente</span>
 <div className="font-medium mt-1">{prof.cliente_razon_social}</div>
 </div>
 <div>
 <span className="text-muted-foreground">Identificación</span>
 <div className="font-mono text-xs mt-1">{prof.cliente_identificacion}</div>
 </div>
 {prof.fecha_validez && (
 <div>
 <span className="text-muted-foreground">Fecha Validez</span>
 <div className="mt-1">{new Date(prof.fecha_validez).toLocaleDateString('es-EC')}</div>
 </div>
 )}
 {prof.forma_pago && (
 <div>
 <span className="text-muted-foreground">Forma de Pago</span>
 <div className="mt-1">
 {FORMAS_PAGO.find((f) => f.codigo === prof.forma_pago)?.descripcion || prof.forma_pago}
 <span className="text-muted-foreground text-xs ml-1">({prof.forma_pago})</span>
 </div>
 </div>
 )}
 {prof.cliente_direccion && (
 <div className="col-span-2">
 <span className="text-muted-foreground">Dirección</span>
 <div className="text-sm mt-1">{prof.cliente_direccion}</div>
 </div>
 )}
 {prof.cliente_email && (
 <div>
 <span className="text-muted-foreground">Email</span>
 <div className="text-sm mt-1">{prof.cliente_email}</div>
 </div>
 )}
 {prof.cliente_telefono && (
 <div>
 <span className="text-muted-foreground">Teléfono</span>
 <div className="text-sm mt-1">{prof.cliente_telefono}</div>
 </div>
 )}
 </div>

 <Separator />

 {/* Totales en formato SRI */}
 <TotalesSRI totals={totalesFromResponse(prof)} propinaOverride={prof.propina} />

 <Separator />

 {/* Detalles */}
 <div>
 <h4 className="text-sm font-medium mb-2">Detalles</h4>
 <div className="space-y-2">
 {prof.detalles.map((det, i) => (
 <div key={det.id || i} className="rounded-md border p-3 text-xs space-y-1">
 <div className="flex justify-between">
 <span className="font-medium">{det.descripcion}</span>
 <span className="font-medium">${formatCurrency(det.precio_total_sin_impuestos)}</span>
 </div>
 <div className="flex gap-4 text-muted-foreground">
 <span>Cod: {det.codigo_principal}</span>
 <span>Cant: {det.cantidad}</span>
 <span>P.Unit: ${formatCurrency(det.precio_unitario)}</span>
 <span>IVA: {det.iva_porcentaje}%</span>
 {det.ice_porcentaje && <span>ICE: {det.ice_porcentaje}%</span>}
 </div>
 </div>
 ))}
 </div>
 </div>

 {prof.observaciones && (
 <>
 <Separator />
 <div className="text-sm">
 <span className="text-muted-foreground">Observaciones: </span>
 <span>{prof.observaciones}</span>
 </div>
 </>
 )}

 {prof.comprobante_convertido_id && (
 <>
 <Separator />
 <div className="flex items-center gap-2 p-3 rounded-md bg-primary/10 text-sm">
 <ArrowRightLeft className="h-4 w-4 text-primary" />
 <span className="text-muted-foreground">Convertida a comprobante:</span>
 <span className="font-mono text-xs">{prof.comprobante_convertido_id}</span>
 </div>
 </>
 )}
 </div>
 </ScrollArea>
 );
}

// ─── Nueva Proforma Wizard ──────────────────────────────────────

type ProformaWizardStep = 1 | 2 | 3;

function NuevaProformaWizard({ companyId, onCreated }: { companyId: string; onCreated: () => void }) {
 const [step, setStep] = useState<ProformaWizardStep>(1);
 const [creating, setCreating] = useState(false);

 // Step 1: Client (optional)
 const [clientId, setClientId] = useState<string>('');
 const [clients, setClients] = useState<ClientResponse[]>([]);

 // Step 2: Items
 const [items, setItems] = useState<ProformaDetalleCreate[]>([]);
 const [products, setProducts] = useState<ProductResponse[]>([]);

 // Step 3: Summary
 const [observaciones, setObservaciones] = useState('');
 const [fechaValidez, setFechaValidez] = useState('');
 const [formaPago, setFormaPago] = useState<string>('01');
 const [propina, setPropina] = useState(0);

 // Load clients and products
 useEffect(() => {
 if (!companyId) return;
 async function load() {
 try {
 const [cls, prods] = await Promise.all([
 getClients(companyId),
 getProducts(companyId),
 ]);
 // Guard defensivo: evitar que respuestas no-array rompan el render
 setClients(Array.isArray(cls) ? cls : []);
 setProducts(Array.isArray(prods) ? prods : []);
 } catch {
 toast.error('Error al cargar datos');
 }
 }
 load();
 }, [companyId]);

 // Calculate totals (desglose completo estilo SRI)
 const totals = computeTotales(items);

 // Validate step
 function canProceed(): boolean {
 switch (step) {
 case 1: return true; // Client is optional
 case 2: return items.length > 0;
 case 3: return true;
 }
 }

 async function handleCreate() {
 setCreating(true);
 try {
 const proformaData: ProformaCreate = {
 company_id: companyId,
 client_id: clientId || undefined,
 // Enviar el monto de descuento efectivo calculado (dólares) por línea
 detalles: items.map((item) => ({
 ...item,
 descuento: getItemDiscount(item) || undefined,
 descuento_tipo: item.descuento_tipo || undefined,
 descuento_valor: item.descuento_valor ?? undefined,
 })),
 observaciones: observaciones || undefined,
 forma_pago: formaPago,
 fecha_validez: fechaValidez || undefined,
 propina: propina || undefined,
 };

 await createProforma(proformaData);
 toast.success('Proforma creada exitosamente');
 onCreated();
 } catch (err) {
 toast.error(err instanceof Error ? err.message : 'Error al crear proforma');
 } finally {
 setCreating(false);
 }
 }

 const defaultConsumer = clients.find((c) => c.is_default_consumer);

 const steps = [
 { num: 1, label: 'Cliente' },
 { num: 2, label: 'Items' },
 { num: 3, label: 'Resumen' },
 ];

 return (
 <div className="space-y-6">
 {/* Step indicator */}
 <div className="flex items-center gap-2">
 {steps.map((s, i) => (
 <div key={s.num} className="flex items-center">
 <button
 onClick={() => s.num <= step && setStep(s.num as ProformaWizardStep)}
 className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
 step === s.num
 ? 'bg-primary text-primary-foreground'
 : step > s.num
 ? 'bg-primary/20 text-primary'
 : 'bg-muted text-muted-foreground'
 }`}
 >
 <span className="h-5 w-5 rounded-full flex items-center justify-center border text-[10px]">
 {step > s.num ? <CheckCircle2 className="h-3 w-3" /> : s.num}
 </span>
 <span className="hidden sm:inline">{s.label}</span>
 </button>
 {i < steps.length - 1 && <ChevronRight className="h-3 w-3 text-muted-foreground mx-1" />}
 </div>
 ))}
 </div>

 {/* Step Content */}
 {step === 1 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Users className="h-4 w-4 text-primary" />
 Seleccionar Cliente
 </CardTitle>
 <CardDescription>
 Seleccione un cliente o use Consumidor Final por defecto (opcional)
 </CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="space-y-2">
 <Label>Cliente</Label>
 <Select value={clientId} onValueChange={setClientId}>
 <SelectTrigger>
 <SelectValue placeholder="Consumidor Final (por defecto)" />
 </SelectTrigger>
 <SelectContent>
 {defaultConsumer && (
 <SelectItem value={defaultConsumer.id}>
 Consumidor Final (por defecto)
 </SelectItem>
 )}
 {clients
 .filter((c) => !c.is_default_consumer)
 .map((client) => (
 <SelectItem key={client.id} value={client.id}>
 {client.razon_social} - {client.identificacion}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 {clientId && (
 <div className="rounded-md border p-3 bg-muted/50 text-sm">
 <div className="grid grid-cols-2 gap-2">
 <div>
 <span className="text-muted-foreground">Nombre: </span>
 <span className="font-medium">{clients.find((c) => c.id === clientId)?.razon_social}</span>
 </div>
 <div>
 <span className="text-muted-foreground">Identificación: </span>
 <span className="font-mono text-xs">{clients.find((c) => c.id === clientId)?.identificacion}</span>
 </div>
 </div>
 </div>
 )}
 <p className="text-xs text-muted-foreground">
 El cliente es opcional. Si no selecciona uno, se usara Consumidor Final.
 </p>
 </CardContent>
 </Card>
 )}

 {step === 2 && (
 <ProformaItemsEditor
 items={items}
 onChange={setItems}
 products={products}
 />
 )}

 {step === 3 && (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <CheckCircle2 className="h-4 w-4 text-primary" />
 Resumen de Proforma
 </CardTitle>
 <CardDescription>Verifique los datos y configure opciones adicionales</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 {/* Client info */}
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
 <div>
 <span className="text-muted-foreground">Cliente</span>
 <div className="font-medium">
 {clientId ? clients.find((c) => c.id === clientId)?.razon_social : 'Consumidor Final'}
 </div>
 </div>
 <div>
 <span className="text-muted-foreground">Identificación</span>
 <div className="font-mono text-xs">
 {clientId ? clients.find((c) => c.id === clientId)?.identificacion : '9999999999999'}
 </div>
 </div>
 </div>

 <Separator />

 {/* Items summary */}
 <div>
 <h4 className="text-sm font-medium mb-2">Items ({items.length})</h4>
 <div className="rounded-md border">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Código</TableHead>
 <TableHead>Descripción</TableHead>
 <TableHead className="text-right">Cant.</TableHead>
 <TableHead className="text-right">P.Unit.</TableHead>
 <TableHead className="text-right">IVA</TableHead>
 <TableHead className="text-right">Subtotal</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {items.map((item, i) => (
 <TableRow key={i}>
 <TableCell className="font-mono text-xs">{item.codigo_principal}</TableCell>
 <TableCell className="max-w-[200px] truncate">{item.descripcion}</TableCell>
 <TableCell className="text-right">{item.cantidad}</TableCell>
 <TableCell className="text-right">${formatCurrency(item.precio_unitario)}</TableCell>
 <TableCell className="text-right">{item.iva_porcentaje}%</TableCell>
 <TableCell className="text-right font-medium">
 ${formatCurrency(getItemSubtotal(item))}
 </TableCell>
 </TableRow>
 ))}
 </TableBody>
 </Table>
 </div>
 </div>

 <Separator />

 {/* Totales en formato SRI */}
 <TotalesSRI totals={totals} propinaOverride={propina} />

 <Separator />

 {/* Additional fields */}
 <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
 <div className="space-y-2">
 <Label htmlFor="pf-forma-pago">Forma de Pago</Label>
 <Select value={formaPago} onValueChange={setFormaPago}>
 <SelectTrigger id="pf-forma-pago">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {FORMAS_PAGO.map((fp) => (
 <SelectItem key={fp.codigo} value={fp.codigo}>
 {fp.codigo} - {fp.descripcion}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 <div className="space-y-2">
 <Label htmlFor="pf-fecha-validez">Fecha de Validez</Label>
 <Input
 id="pf-fecha-validez"
 type="date"
 value={fechaValidez}
 onChange={(e) => setFechaValidez(e.target.value)}
 />
 </div>
 <div className="space-y-2">
 <Label htmlFor="pf-propina">Propina ($)</Label>
 <PriceInput
 value={propina}
 onChange={setPropina}
 placeholder="0,00"
 />
 </div>
 </div>

 <div className="space-y-2">
 <Label htmlFor="pf-observaciones">Observaciones</Label>
 <Textarea
 id="pf-observaciones"
 placeholder="Observaciones adicionales para la proforma..."
 value={observaciones}
 onChange={(e) => setObservaciones(e.target.value)}
 rows={3}
 />
 </div>
 </CardContent>
 </Card>
 )}

 {/* Navigation */}
 <div className="flex justify-between">
 <Button
 variant="outline"
 onClick={() => setStep((step - 1) as ProformaWizardStep)}
 disabled={step === 1}
 >
 <ChevronLeft className="mr-2 h-4 w-4" />
 Anterior
 </Button>
 {step < 3 ? (
 <Button
 onClick={() => setStep((step + 1) as ProformaWizardStep)}
 disabled={!canProceed()}
 >
 Siguiente
 <ChevronRight className="ml-2 h-4 w-4" />
 </Button>
 ) : (
 <Button
 onClick={handleCreate}
 disabled={creating || items.length === 0}
 className="bg-emerald-600 hover:bg-emerald-700"
 >
 {creating ? (
 <>
 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
 Creando...
 </>
 ) : (
 <>
 <CheckCircle2 className="mr-2 h-4 w-4" />
 Crear Proforma
 </>
 )}
 </Button>
 )}
 </div>
 </div>
 );
}

// ─── Proforma Items Editor ──────────────────────────────────────

function ProformaItemsEditor({
 items,
 onChange,
 products,
}: {
 items: ProformaDetalleCreate[];
 onChange: (items: ProformaDetalleCreate[]) => void;
 products: ProductResponse[];
}) {
 const [search, setSearch] = useState('');
 const [showSearch, setShowSearch] = useState(false);
 // Índice del item expandido: al agregar un nuevo item, los anteriores se contraen
 const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

 const filteredProducts = products.filter(
 (p) =>
 (p.descripcion || '').toLowerCase().includes(search.toLowerCase()) ||
 (p.codigo_principal || '').toLowerCase().includes(search.toLowerCase())
 ); function addFromProduct(product: ProductResponse) {
    // Si el IVA está incluido en el precio, extraer el precio base (sin IVA)
    let precioBase = product.precio_unitario;
    if (product.iva_incluido && product.iva_porcentaje > 0) {
      precioBase = product.precio_unitario / (1 + product.iva_porcentaje / 100);
      precioBase = Math.round(precioBase * 100) / 100;
    }
    const newItem: ProformaDetalleCreate = {
      product_id: product.id,
      codigo_principal: product.codigo_principal,
      codigo_auxiliar: product.codigo_auxiliar || undefined,
      descripcion: product.descripcion,
      cantidad: 1,
      unidad_medida: product.unidad_medida,
      precio_unitario: precioBase,
      descuento: product.descuento || undefined,
      iva_codigo: product.iva_codigo,
      iva_porcentaje: product.iva_porcentaje,
    };
    const newItems = [...items, newItem];
    onChange(newItems);
    setExpandedIndex(newItems.length - 1);
    setShowSearch(false);
    setSearch('');
  }

 function addEmptyItem() {
 const newItem: ProformaDetalleCreate = {
 codigo_principal: '',
 descripcion: '',
 cantidad: 1,
 unidad_medida: 'Unidad',
 precio_unitario: 0,
 iva_codigo: '4',
 iva_porcentaje: 15,
 };
 const newItems = [...items, newItem];
 onChange(newItems);
 setExpandedIndex(newItems.length - 1);
 }

 function updateItem(index: number, updates: Partial<ProformaDetalleCreate>) {
 const newItems = [...items];
 newItems[index] = { ...newItems[index], ...updates };
 onChange(newItems);
 }

 function removeItem(index: number) {
 onChange(items.filter((_, i) => i !== index));
 }

 // Totales con desglose completo estilo SRI
 const totals = computeTotales(items);

 return (
 <Card>
 <CardHeader>
 <CardTitle className="text-base flex items-center gap-2">
 <Package className="h-4 w-4 text-primary" />
 Agregar Items
 </CardTitle>
 <CardDescription>Agregue productos o servicios a la proforma</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="flex gap-2">
 <Button variant="outline" onClick={() => setShowSearch(!showSearch)}>
 <Search className="mr-2 h-4 w-4" />
 Buscar Producto
 </Button>
 <Button variant="outline" onClick={addEmptyItem}>
 <Plus className="mr-2 h-4 w-4" />
 Ingreso Manual
 </Button>
 </div>

 {/* Product Search */}
 {showSearch && (
 <div className="space-y-2">
 <Input
 placeholder="Buscar por nombre o codigo..."
 value={search}
 onChange={(e) => setSearch(e.target.value)}
 />
 {filteredProducts.length > 0 ? (
 <ScrollArea className="max-h-[200px]">
 <div className="space-y-1">
 {filteredProducts.slice(0, 20).map((product) => (
 <button
 key={product.id}
 onClick={() => addFromProduct(product)}
 className="w-full text-left rounded-md border p-2 hover:bg-accent/50 transition-colors text-sm"
 >
 <div className="flex justify-between">
 <span className="font-medium">{product.descripcion}</span>
 <span className="text-muted-foreground">${formatCurrency(product.precio_unitario)}</span>
 </div>
 <span className="text-xs text-muted-foreground font-mono">
 {product.codigo_principal} | IVA {product.iva_porcentaje}%
 </span>
 </button>
 ))}
 </div>
 </ScrollArea>
 ) : (
 <p className="text-xs text-muted-foreground text-center py-2">
 No se encontraron productos. Intente ingreso manual.
 </p>
 )}
 </div>
 )}

 {/* Items List: colapsados salvo el item expandido */}
 {items.length > 0 ? (
 <div className="space-y-2">
 {items.map((item, i) => {
 const expanded = expandedIndex === i;
 return (
 <div key={i} className="rounded-md border">
 {/* Encabezado: clic para expandir/contraer */}
 <button
 type="button"
 onClick={() => setExpandedIndex(expanded ? null : i)}
 className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left hover:bg-accent/40 transition-colors"
 >
 <div className="flex items-center gap-2 min-w-0">
 {expanded ? (
 <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
 ) : (
 <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
 )}
 <span className="text-xs font-medium text-muted-foreground shrink-0">Item {i + 1}</span>
 <span className="text-sm font-medium truncate">
 {item.descripcion || item.codigo_principal || 'Sin descripción'}
 </span>
 </div>
 <div className="flex items-center gap-3 shrink-0">
 <span className="text-xs text-muted-foreground hidden sm:inline">
 {item.cantidad} × ${formatCurrency(item.precio_unitario)}
 </span>
 <span className="text-xs font-semibold">${formatCurrency(getItemSubtotal(item))}</span>
 <span
 role="button"
 tabIndex={0}
 aria-label="Eliminar item"
 onClick={(e) => { e.stopPropagation(); removeItem(i); }}
 onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); removeItem(i); } }}
 className="h-6 w-6 inline-flex items-center justify-center rounded hover:bg-destructive/10 text-destructive"
 >
 <X className="h-3.5 w-3.5" />
 </span>
 </div>
 </button>

 {expanded && (
 <div className="px-3 pb-3 space-y-3 border-t pt-3">
 <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
 <div className="space-y-1">
 <Label className="text-xs">Código Principal</Label>
 <Input
 value={item.codigo_principal}
 onChange={(e) => updateItem(i, { codigo_principal: e.target.value })}
 placeholder="COD001"
 className="h-8 text-sm"
 />
 </div>
 <div className="space-y-1 sm:col-span-2 lg:col-span-2">
 <Label className="text-xs">Descripción</Label>
 <Input
 value={item.descripcion}
 onChange={(e) => updateItem(i, { descripcion: e.target.value })}
 placeholder="Descripción del producto o servicio"
 className="h-8 text-sm"
 />
 </div>
 <div className="space-y-1">
 <Label className="text-xs">Cantidad</Label>
 <NumericInput integer
 
 value={item.cantidad}
 onChange={(e) => updateItem(i, { cantidad: parseFloat(e.target.value) || 0 })}
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Precio Unitario</Label>
                          <PriceInput
                            value={item.precio_unitario}
                            onChange={(v) => updateItem(i, { precio_unitario: v })}
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Tipo Descuento</Label>
                          <Select
                            value={item.descuento_tipo || 'dolares'}
                            onValueChange={(v) =>
                              updateItem(i, {
                                descuento_tipo: v as DescuentoTipo,
                                descuento: v === 'porcentaje' && item.descuento_valor != null
                                  ? (item.cantidad * item.precio_unitario * item.descuento_valor) / 100
                                  : item.descuento_valor ?? undefined,
                              })
                            }
                          >
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="dolares">Dólares ($)</SelectItem>
                              <SelectItem value="porcentaje">Porcentaje (%)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Descuento {item.descuento_tipo === 'porcentaje' ? '(%)' : '($)'}</Label>
                          <NumericInput value={item.descuento_valor ?? item.descuento ?? ''}
 onChange={(e) => {
 const v = parseFloat(e.target.value) || 0;
 updateItem(i, {
 descuento_valor: v,
 descuento:
 item.descuento_tipo === 'porcentaje'
 ? (item.cantidad * item.precio_unitario * v) / 100
 : v || undefined,
 });
 }}
 placeholder={item.descuento_tipo === 'porcentaje' ? '0' : '0.00'}
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">IRBPNR / unidad ($)</Label>
                          <NumericInput value={item.irbpnr_valor ?? ''}
 onChange={(e) => updateItem(i, { irbpnr_valor: parseFloat(e.target.value) || undefined })}
 placeholder="0.00"
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">ICE (%)</Label>
                          <NumericInput value={item.ice_porcentaje ?? ''}
 onChange={(e) => updateItem(i, { ice_porcentaje: parseFloat(e.target.value) || undefined })}
 placeholder="0"
 className="h-8 text-sm" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">IVA</Label>
                          <Select
                            value={item.iva_codigo}
                            onValueChange={(v) => {
                              const rate = IVA_RATES.find((r) => r.codigo === v);
                              updateItem(i, { iva_codigo: v, iva_porcentaje: rate?.porcentaje ?? 0 });
                            }}
                          >
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {IVA_RATES.map((rate) => (
                                <SelectItem key={rate.codigo} value={rate.codigo}>
                                  {rate.descripcion} ({rate.porcentaje}%)
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="text-right text-xs text-muted-foreground">
                        Subtotal: ${formatCurrency(getItemSubtotal(item))}
                        {getItemDiscount(item) > 0 && (
                          <span className="text-destructive"> - Desc. ${formatCurrency(getItemDiscount(item))}</span>
                        )}
                        {item.iva_porcentaje > 0 && (
                          <span> + IVA ${formatCurrency(getItemSubtotal(item) * item.iva_porcentaje / 100)}</span>
                        )}
                        {(item.ice_porcentaje || 0) > 0 && (
                          <span> + ICE ${formatCurrency(getItemSubtotal(item) * (item.ice_porcentaje || 0) / 100)}</span>
                        )}
                        {(item.irbpnr_valor || 0) > 0 && (
                          <span> + IRBPNR ${formatCurrency((item.irbpnr_valor || 0) * item.cantidad)}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6">
            <Package className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">Agregue items a la proforma</p>
          </div>
        )}

        {/* Running Totals en formato SRI */}
        {items.length > 0 && (
          <TotalesSRI totals={totals} />
        )}
      </CardContent>
    </Card>
  );
}
