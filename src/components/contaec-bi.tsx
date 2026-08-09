'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import {
  Bar,
  BarChart,
  Line,
  LineChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Pie,
  PieChart,
  Cell,
  Area,
  AreaChart,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Receipt,
  Users,
  Package,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Download,
  RefreshCw,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  Shield,
  Clock,
  Warehouse,
  CreditCard,
  Calculator,
  Target,
  Bell,
  FileDown,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getBIKPIs,
  getBIVentasMensuales,
  getBIVentasPorTipo,
  getBITopProductos,
  getBITopClientes,
  getBIFlujoEfectivo,
  getBIAlertas,
  getBICuadroMando,
  downloadBIPowerBIFile,
  type BIKPIs,
  type BIVentaMensual,
  type BIVentaPorTipo,
  type BITopProducto,
  type BITopCliente,
  type BIFlujoEfectivo,
  type BIAlerta,
  type BICuadroMando,
  type User as UserType,
  type Company as CompanyType,
} from '@/lib/api';

interface ContaECBIProps {
  user: UserType;
  companies: CompanyType[];
}

const _COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

const PIE_COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899', '#14b8a6'];

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' }).format(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('es-EC').format(value);
}

function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
const _MESES_FULL = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export function ContaECBI({ user: _user, companies }: ContaECBIProps) {
  const [selectedCompany, setSelectedCompany] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('kpis');

  // Data states
  const [kpis, setKpis] = useState<BIKPIs | null>(null);
  const [ventasMensuales, setVentasMensuales] = useState<BIVentaMensual[]>([]);
  const [ventasPorTipo, setVentasPorTipo] = useState<BIVentaPorTipo[]>([]);
  const [topProductos, setTopProductos] = useState<BITopProducto[]>([]);
  const [topClientes, setTopClientes] = useState<BITopCliente[]>([]);
  const [flujoEfectivo, setFlujoEfectivo] = useState<BIFlujoEfectivo[]>([]);
  const [alertas, setAlertas] = useState<BIAlerta[]>([]);
  const [cuadroMando, setCuadroMando] = useState<BICuadroMando | null>(null);
  const [exporting, setExporting] = useState(false);

  const companyId = selectedCompany === 'all' ? undefined : selectedCompany;

  const loadAllData = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        getBIKPIs({ company_id: companyId }),
        getBIVentasMensuales({ company_id: companyId }),
        getBIVentasPorTipo({ company_id: companyId }),
        getBITopProductos({ company_id: companyId, limite: 10 }),
        getBITopClientes({ company_id: companyId, limite: 10 }),
        getBIFlujoEfectivo({ company_id: companyId }),
        getBIAlertas({ company_id: companyId }),
        getBICuadroMando({ company_id: companyId }),
      ]);

      if (results[0].status === 'fulfilled') setKpis(results[0].value);
      if (results[1].status === 'fulfilled') setVentasMensuales(results[1].value);
      if (results[2].status === 'fulfilled') setVentasPorTipo(results[2].value);
      if (results[3].status === 'fulfilled') setTopProductos(results[3].value);
      if (results[4].status === 'fulfilled') setTopClientes(results[4].value);
      if (results[5].status === 'fulfilled') setFlujoEfectivo(results[5].value);
      if (results[6].status === 'fulfilled') setAlertas(results[6].value);
      if (results[7].status === 'fulfilled') setCuadroMando(results[7].value);
    } catch {
      toast.error('Error al cargar datos de Business Intelligence');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  async function handleExportPowerBI() {
    setExporting(true);
    try {
      const blob = await downloadBIPowerBIFile({ company_id: companyId });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `contaec-powerbi-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Exportación Power BI descargada exitosamente');
    } catch {
      toast.error('Error al exportar datos para Power BI');
    } finally {
      setExporting(false);
    }
  }

  // Chart configs
  const ventasChartConfig: ChartConfig = {
    total_ventas: { label: 'Ventas', color: '#10b981' },
    total_iva: { label: 'IVA', color: '#f59e0b' },
  };

  const flujoChartConfig: ChartConfig = {
    ingresos: { label: 'Ingresos', color: '#10b981' },
    egresos: { label: 'Egresos', color: '#ef4444' },
    flujo_neto: { label: 'Flujo Neto', color: '#3b82f6' },
  };

  const ventasTipoConfig: ChartConfig = {
    total: { label: 'Total' },
  };

  if (loading && !kpis) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Cargando Business Intelligence...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-primary" />
            Business Intelligence
          </h2>
          <p className="text-muted-foreground">
            KPIs en tiempo real, reportes visuales y cuadro de mando
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedCompany} onValueChange={setSelectedCompany}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Todas las empresas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las empresas</SelectItem>
              {companies.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.razon_social}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={loadAllData} title="Refrescar datos">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="outline" onClick={handleExportPowerBI} disabled={exporting}>
            {exporting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileDown className="mr-2 h-4 w-4" />
            )}
            Power BI
          </Button>
        </div>
      </div>

      {/* Smart Alerts Banner */}
      {alertas.length > 0 && (
        <div className="space-y-2">
          {alertas.slice(0, 3).map((alerta) => (
            <Alert
              key={alerta.id}
              variant={alerta.tipo === 'danger' ? 'destructive' : 'default'}
              className={
                alerta.tipo === 'warning'
                  ? 'border-amber-500/50 bg-amber-50 dark:bg-amber-950/20'
                  : alerta.tipo === 'success'
                  ? 'border-emerald-500/50 bg-emerald-50 dark:bg-emerald-950/20'
                  : alerta.tipo === 'info'
                  ? 'border-blue-500/50 bg-blue-50 dark:bg-blue-950/20'
                  : undefined
              }
            >
              {alerta.tipo === 'danger' ? (
                <XCircle className="h-4 w-4" />
              ) : alerta.tipo === 'warning' ? (
                <AlertTriangle className="h-4 w-4 text-amber-600" />
              ) : alerta.tipo === 'success' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : (
                <Bell className="h-4 w-4 text-blue-600" />
              )}
              <AlertTitle className="text-sm font-medium">{alerta.titulo}</AlertTitle>
              <AlertDescription className="text-xs">{alerta.mensaje}</AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-5">
          <TabsTrigger value="kpis" className="text-xs sm:text-sm">KPIs</TabsTrigger>
          <TabsTrigger value="reportes" className="text-xs sm:text-sm">Reportes</TabsTrigger>
          <TabsTrigger value="alertas" className="text-xs sm:text-sm">
            Alertas {alertas.length > 0 && <Badge variant="destructive" className="ml-1 h-5 text-xs">{alertas.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="cuadro" className="text-xs sm:text-sm">Cuadro de Mando</TabsTrigger>
          <TabsTrigger value="powerbi" className="text-xs sm:text-sm">Power BI</TabsTrigger>
        </TabsList>

        {/* KPIs Tab */}
        <TabsContent value="kpis" className="space-y-6">
          {kpis && <KPIDashboard kpis={kpis} />}
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reportes" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Monthly Sales Chart */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Ventas Mensuales
                </CardTitle>
                <CardDescription>Evolucion de ventas e IVA por mes</CardDescription>
              </CardHeader>
              <CardContent>
                {ventasMensuales.length > 0 ? (
                  <ChartContainer config={ventasChartConfig} className="h-[280px] w-full">
                    <BarChart data={ventasMensuales} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="mes" tickFormatter={(v) => MESES[v - 1]} tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar dataKey="total_ventas" fill="var(--color-total_ventas)" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="total_iva" fill="var(--color-total_iva)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ChartContainer>
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
                    Sin datos de ventas
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Sales by Type */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <PieChartIcon className="h-4 w-4 text-primary" />
                  Ventas por Tipo de Comprobante
                </CardTitle>
                <CardDescription>Distribución por tipo de documento</CardDescription>
              </CardHeader>
              <CardContent>
                {ventasPorTipo.length > 0 ? (
                  <div className="flex flex-col items-center">
                    <ChartContainer config={ventasTipoConfig} className="h-[220px] w-full">
                      <PieChart>
                        <Pie
                          data={ventasPorTipo}
                          dataKey="total"
                          nameKey="descripcion"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          label={({ descripcion, percent }) => `${descripcion} ${(percent * 100).toFixed(0)}%`}
                          labelLine={false}
                        >
                          {ventasPorTipo.map((_, index) => (
                            <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <ChartTooltip content={<ChartTooltipContent />} />
                      </PieChart>
                    </ChartContainer>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {ventasPorTipo.map((item, i) => (
                        <div key={item.tipo_comprobante} className="flex items-center gap-1.5 text-xs">
                          <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                          <span>{item.descripcion}: {formatCurrency(item.total)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
                    Sin datos por tipo
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Cash Flow */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-primary" />
                  Flujo de Efectivo
                </CardTitle>
                <CardDescription>Ingresos vs egresos mensuales</CardDescription>
              </CardHeader>
              <CardContent>
                {flujoEfectivo.length > 0 ? (
                  <ChartContainer config={flujoChartConfig} className="h-[280px] w-full">
                    <AreaChart data={flujoEfectivo} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="mes" tickFormatter={(v) => MESES[v - 1]} tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Area type="monotone" dataKey="ingresos" stroke="var(--color-ingresos)" fill="var(--color-ingresos)" fillOpacity={0.2} />
                      <Area type="monotone" dataKey="egresos" stroke="var(--color-egresos)" fill="var(--color-egresos)" fillOpacity={0.2} />
                      <Line type="monotone" dataKey="flujo_neto" stroke="var(--color-flujo_neto)" strokeWidth={2} dot={{ r: 3 }} />
                    </AreaChart>
                  </ChartContainer>
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
                    Sin datos de flujo
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top Products */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Package className="h-4 w-4 text-primary" />
                  Top Productos Vendidos
                </CardTitle>
                <CardDescription>Productos con mayor venta</CardDescription>
              </CardHeader>
              <CardContent>
                {topProductos.length > 0 ? (
                  <ScrollArea className="h-[280px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-xs">#</TableHead>
                          <TableHead className="text-xs">Producto</TableHead>
                          <TableHead className="text-xs text-right">Cant.</TableHead>
                          <TableHead className="text-xs text-right">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {topProductos.map((prod, i) => (
                          <TableRow key={prod.product_id}>
                            <TableCell className="text-xs font-medium">{i + 1}</TableCell>
                            <TableCell className="text-xs">
                              <div className="font-medium truncate max-w-[150px]">{prod.descripcion}</div>
                              <div className="text-muted-foreground">{prod.codigo}</div>
                            </TableCell>
                            <TableCell className="text-xs text-right">{formatNumber(prod.cantidad_vendida)}</TableCell>
                            <TableCell className="text-xs text-right font-medium">{formatCurrency(prod.total_venta)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground text-sm">
                    Sin datos de productos
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Top Clients */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Users className="h-4 w-4 text-primary" />
                Top Clientes
              </CardTitle>
              <CardDescription>Clientes con mayor volumen de compra</CardDescription>
            </CardHeader>
            <CardContent>
              {topClientes.length > 0 ? (
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>#</TableHead>
                        <TableHead>Cliente</TableHead>
                        <TableHead>Identificación</TableHead>
                        <TableHead className="text-right">Comprobantes</TableHead>
                        <TableHead className="text-right">Total Compras</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topClientes.map((cli, i) => (
                        <TableRow key={cli.client_id}>
                          <TableCell className="font-medium">{i + 1}</TableCell>
                          <TableCell className="font-medium">{cli.razon_social}</TableCell>
                          <TableCell className="text-muted-foreground font-mono text-xs">{cli.identificacion}</TableCell>
                          <TableCell className="text-right">{cli.cantidad_comprobantes}</TableCell>
                          <TableCell className="text-right font-medium">{formatCurrency(cli.total_compras)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : (
                <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
                  Sin datos de clientes
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alertas" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Alertas Inteligentes
            </h3>
            <Badge variant="secondary">{alertas.length} alertas</Badge>
          </div>

          {alertas.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {alertas.map((alerta) => (
                <Card
                  key={alerta.id}
                  className={
                    alerta.tipo === 'danger'
                      ? 'border-red-500/50'
                      : alerta.tipo === 'warning'
                      ? 'border-amber-500/50'
                      : alerta.tipo === 'success'
                      ? 'border-emerald-500/50'
                      : 'border-blue-500/50'
                  }
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div
                        className={`rounded-md p-2 shrink-0 ${
                          alerta.tipo === 'danger'
                            ? 'bg-red-100 dark:bg-red-950'
                            : alerta.tipo === 'warning'
                            ? 'bg-amber-100 dark:bg-amber-950'
                            : alerta.tipo === 'success'
                            ? 'bg-emerald-100 dark:bg-emerald-950'
                            : 'bg-blue-100 dark:bg-blue-950'
                        }`}
                      >
                        {alerta.tipo === 'danger' ? (
                          <XCircle className="h-4 w-4 text-red-600" />
                        ) : alerta.tipo === 'warning' ? (
                          <AlertTriangle className="h-4 w-4 text-amber-600" />
                        ) : alerta.tipo === 'success' ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        ) : (
                          <Bell className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-medium">{alerta.titulo}</h4>
                          <Badge
                            variant={
                              alerta.tipo === 'danger'
                                ? 'destructive'
                                : alerta.tipo === 'warning'
                                ? 'secondary'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            {alerta.categoria}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{alerta.mensaje}</p>
                        <p className="text-[10px] text-muted-foreground mt-1.5">
                          <Clock className="inline h-3 w-3 mr-1" />
                          {new Date(alerta.fecha).toLocaleString('es-EC')}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle2 className="h-12 w-12 mx-auto text-emerald-500 mb-3" />
                <h3 className="text-lg font-medium">Todo en orden</h3>
                <p className="text-muted-foreground text-sm mt-1">
                  No hay alertas activas en este momento
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Cuadro de Mando Tab */}
        <TabsContent value="cuadro" className="space-y-6">
          {cuadroMando ? (
            <CuadroMandoView data={cuadroMando} />
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Target className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <h3 className="text-lg font-medium">Sin datos</h3>
                <p className="text-muted-foreground text-sm mt-1">
                  No se pudo cargar el cuadro de mando
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Power BI Export Tab */}
        <TabsContent value="powerbi" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary" />
                Exportación Power BI
              </CardTitle>
              <CardDescription>
                Exporte sus datos en formato compatible con Microsoft Power BI para analisis avanzado
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Export Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-lg border p-4 space-y-3">
                  <h4 className="font-medium text-sm">Datos incluidos en la exportacion</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <Receipt className="h-4 w-4 text-primary" />
                      <span>Fact table: Ventas (comprobantes autorizados)</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Package className="h-4 w-4 text-primary" />
                      <span>Dimension: Productos</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Users className="h-4 w-4 text-primary" />
                      <span>Dimension: Clientes</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="h-4 w-4 text-primary" />
                      <span>Dimension: Tiempo</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Warehouse className="h-4 w-4 text-primary" />
                      <span>Fact table: Inventario</span>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border p-4 space-y-3">
                  <h4 className="font-medium text-sm">Como usar en Power BI</h4>
                  <ol className="space-y-1.5 text-xs text-muted-foreground list-decimal list-inside">
                    <li>Descargue el archivo JSON</li>
                    <li>Abra Power BI Desktop</li>
                    <li>Seleccione &quot;Obtener datos&quot; &gt; &quot;Archivo JSON&quot;</li>
                    <li>Cargue el archivo descargado</li>
                    <li>Power BI detectara automaticamente las tablas</li>
                    <li>Cree relaciones entre fact_ventas y dimensiones</li>
                    <li>Construya sus dashboards personalizados</li>
                  </ol>
                </div>
              </div>

              <Separator />

              {/* Export Button */}
              <div className="flex flex-col items-center gap-4 py-6">
                <div className="rounded-full bg-primary/10 p-6">
                  <FileDown className="h-10 w-10 text-primary" />
                </div>
                <div className="text-center">
                  <h3 className="text-lg font-medium">Exportar datos para Power BI</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Formato JSON con esquema en estrella (Star Schema)
                  </p>
                </div>
                <Button size="lg" onClick={handleExportPowerBI} disabled={exporting}>
                  {exporting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Exportando...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Descargar Exportación Power BI
                    </>
                  )}
                </Button>
              </div>

              {/* Quick Stats about data */}
              {kpis && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-lg border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Comprobantes</p>
                    <p className="text-lg font-bold">{formatNumber(kpis.comprobantes_emitidos)}</p>
                  </div>
                  <div className="rounded-lg border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Ventas Totales</p>
                    <p className="text-lg font-bold">{formatCurrency(kpis.ventas_totales)}</p>
                  </div>
                  <div className="rounded-lg border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Clientes</p>
                    <p className="text-lg font-bold">{formatNumber(kpis.clientes_activos)}</p>
                  </div>
                  <div className="rounded-lg border p-3 text-center">
                    <p className="text-xs text-muted-foreground">Productos</p>
                    <p className="text-lg font-bold">{formatNumber(kpis.productos_vendidos)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============ Sub-Components ============

function KPIDashboard({ kpis }: { kpis: BIKPIs }) {
  const variacionVentas = kpis.variacion_ventas;
  const _variacionPositive = variacionVentas >= 0;

  return (
    <div className="space-y-6">
      {/* Main KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <KPICard
          title="Ventas Totales"
          value={formatCurrency(kpis.ventas_totales)}
          icon={<DollarSign className="h-4 w-4" />}
          trend={variacionVentas}
          trendLabel="vs mes anterior"
          color="emerald"
        />
        <KPICard
          title="Comprobantes Emitidos"
          value={formatNumber(kpis.comprobantes_emitidos)}
          icon={<Receipt className="h-4 w-4" />}
          subtitle={`${formatNumber(kpis.comprobantes_autorizados)} autorizados`}
          color="primary"
        />
        <KPICard
          title="Tasa Aprobación SRI"
          value={`${kpis.tasa_aprobacion.toFixed(1)}%`}
          icon={<Shield className="h-4 w-4" />}
          subtitle={`${kpis.comprobantes_rechazados} rechazados`}
          color={kpis.tasa_aprobacion >= 90 ? 'emerald' : kpis.tasa_aprobacion >= 70 ? 'amber' : 'red'}
        />
        <KPICard
          title="Ticket Promedio"
          value={formatCurrency(kpis.ticket_promedio)}
          icon={<CreditCard className="h-4 w-4" />}
          color="primary"
        />
        <KPICard
          title="IVA Recaudado"
          value={formatCurrency(kpis.iva_recaudado)}
          icon={<Calculator className="h-4 w-4" />}
          color="amber"
        />
        <KPICard
          title="Clientes Activos"
          value={formatNumber(kpis.clientes_activos)}
          icon={<Users className="h-4 w-4" />}
          color="primary"
        />
        <KPICard
          title="Ctas. por Cobrar"
          value={formatCurrency(kpis.cuentas_por_cobrar)}
          icon={<TrendingUp className="h-4 w-4" />}
          color="blue"
        />
        <KPICard
          title="Ctas. por Pagar"
          value={formatCurrency(kpis.cuentas_por_pagar)}
          icon={<TrendingDown className="h-4 w-4" />}
          color="amber"
        />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniKPICard
          title="Valor Inventario"
          value={formatCurrency(kpis.inventario_valor)}
          icon={<Warehouse className="h-3.5 w-3.5" />}
        />
        <MiniKPICard
          title="Productos Vendidos"
          value={formatNumber(kpis.productos_vendidos)}
          icon={<Package className="h-3.5 w-3.5" />}
        />
        <MiniKPICard
          title="Empleados Activos"
          value={formatNumber(kpis.empleados_activos)}
          icon={<Users className="h-3.5 w-3.5" />}
        />
        <MiniKPICard
          title="Nómina Total"
          value={formatCurrency(kpis.nomina_total)}
          icon={<DollarSign className="h-3.5 w-3.5" />}
        />
      </div>

      {/* POS KPIs */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Punto de Venta - Hoy
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border p-3">
              <p className="text-xs text-muted-foreground">Ventas Hoy</p>
              <p className="text-xl font-bold">{formatCurrency(kpis.pos_ventas_hoy)}</p>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-xs text-muted-foreground">Tickets Hoy</p>
              <p className="text-xl font-bold">{formatNumber(kpis.pos_tickets_hoy)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function KPICard({
  title,
  value,
  icon,
  trend,
  trendLabel,
  subtitle,
  color = 'primary',
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend?: number;
  trendLabel?: string;
  subtitle?: string;
  color?: 'primary' | 'emerald' | 'amber' | 'red' | 'blue';
}) {
  const colorMap = {
    primary: 'bg-primary/10 text-primary',
    emerald: 'bg-emerald-100 dark:bg-emerald-950 text-emerald-600',
    amber: 'bg-amber-100 dark:bg-amber-950 text-amber-600',
    red: 'bg-red-100 dark:bg-red-950 text-red-600',
    blue: 'bg-blue-100 dark:bg-blue-950 text-blue-600',
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">{title}</span>
          <div className={`rounded-md p-1.5 ${colorMap[color]}`}>
            {icon}
          </div>
        </div>
        <div className="text-xl font-bold">{value}</div>
        {trend !== undefined && (
          <div className="flex items-center gap-1 mt-1">
            {trend >= 0 ? (
              <ArrowUpRight className="h-3 w-3 text-emerald-600" />
            ) : (
              <ArrowDownRight className="h-3 w-3 text-red-600" />
            )}
            <span className={`text-xs font-medium ${trend >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {formatPercent(trend)}
            </span>
            {trendLabel && <span className="text-[10px] text-muted-foreground">{trendLabel}</span>}
          </div>
        )}
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

function MiniKPICard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-2 mb-1">
        <div className="text-muted-foreground">{icon}</div>
        <span className="text-xs text-muted-foreground">{title}</span>
      </div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  );
}

function CuadroMandoView({ data }: { data: BICuadroMando }) {
  const { kpis_resumen, indicadores_cumplimiento, tendencias, estado_general } = data;
  const puntuacion = estado_general;

  // Trend chart data from tendencias array
  const trendData = tendencias.map((t) => ({
    mes: t.nombre_mes,
    ventas: t.ventas,
    comprobantes: t.comprobantes,
  }));

  const trendConfig: ChartConfig = {
    ventas: { label: 'Ventas', color: '#10b981' },
    comprobantes: { label: 'Comprobantes', color: '#3b82f6' },
  };

  return (
    <div className="space-y-6">
      {/* Health Score */}
      <Card className={
        puntuacion >= 80
          ? 'border-emerald-500/30'
          : puntuacion >= 60
          ? 'border-amber-500/30'
          : 'border-red-500/30'
      }>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-center gap-6">
            <div className="flex-1 text-center md:text-left">
              <h3 className="text-lg font-semibold">Estado General del Negocio</h3>
              <p className="text-muted-foreground text-sm mt-1">
                Puntuacion calculada en base a KPIs financieros, cumplimiento SRI y salud operativa
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className={`text-5xl font-bold ${
                  puntuacion >= 80
                    ? 'text-emerald-600'
                    : puntuacion >= 60
                    ? 'text-amber-600'
                    : 'text-red-600'
                }`}>
                  {puntuacion}
                </div>
                <div className="text-xs text-muted-foreground mt-1">de 100</div>
              </div>
              <div className="space-y-1">
                <Badge
                  className={
                    puntuacion >= 80
                      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                      : puntuacion >= 60
                      ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                      : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                  }
                >
                  {puntuacion >= 80 ? 'Optimo' : puntuacion >= 60 ? 'Aceptable' : 'Critico'}
                </Badge>
                <Progress
                  value={puntuacion}
                  className="h-2 w-32"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Financial KPIs Summary */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-primary" />
              Resumen Financiero
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <CuadroMandoItem label="Ventas del Mes" value={formatCurrency(kpis_resumen.ventas_mes)} />
            <CuadroMandoItem label="Variacion Ventas" value={kpis_resumen.variacion_ventas != null ? formatPercent(kpis_resumen.variacion_ventas) : 'N/A'} highlight={kpis_resumen.variacion_ventas != null && kpis_resumen.variacion_ventas >= 0 ? 'positive' : 'negative'} />
            <CuadroMandoItem label="Ticket Promedio" value={formatCurrency(kpis_resumen.ticket_promedio)} />
            <CuadroMandoItem label="IVA Recaudado" value={formatCurrency(kpis_resumen.iva_recaudado)} />
            <Separator />
            <CuadroMandoItem label="Cuentas por Cobrar" value={formatCurrency(kpis_resumen.cuentas_por_cobrar)} />
            <CuadroMandoItem label="Cuentas por Pagar" value={formatCurrency(kpis_resumen.cuentas_por_pagar)} />
            <CuadroMandoItem label="Flujo Neto del Mes" value={formatCurrency(kpis_resumen.flujo_neto_mes)} highlight={kpis_resumen.flujo_neto_mes >= 0 ? 'positive' : 'negative'} />
            <CuadroMandoItem label="Nómina Total" value={formatCurrency(kpis_resumen.nomina_total)} />
          </CardContent>
        </Card>

        {/* Compliance Indicators */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              Indicadores de Cumplimiento
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {indicadores_cumplimiento.length > 0 ? indicadores_cumplimiento.map((ind, i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>{ind.nombre}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{ind.valor.toFixed(1)}%</span>
                    <Badge
                      variant={ind.estado === 'optimo' ? 'default' : ind.estado === 'aceptable' ? 'secondary' : 'destructive'}
                      className={ind.estado === 'optimo' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : ''}
                    >
                      {ind.estado === 'optimo' ? 'Optimo' : ind.estado === 'aceptable' ? 'Aceptable' : 'Critico'}
                    </Badge>
                  </div>
                </div>
                <Progress value={Number(ind.valor)} className="h-2" />
              </div>
            )) : (
              <div className="text-center py-4 text-sm text-muted-foreground">
                Sin indicadores de cumplimiento
              </div>
            )}
          </CardContent>
        </Card>

        {/* Trends */}
        {tendencias.length > 0 && (
          <Card className="lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Tendencia ({tendencias.length} meses)
              </CardTitle>
              <CardDescription>Comparativa de ventas y comprobantes</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={trendConfig} className="h-[240px] w-full">
                <LineChart data={trendData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="left" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Line yAxisId="left" type="monotone" dataKey="ventas" stroke="var(--color-ventas)" strokeWidth={2} dot={{ r: 4 }} />
                  <Line yAxisId="right" type="monotone" dataKey="comprobantes" stroke="var(--color-comprobantes)" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function CuadroMandoItem({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: 'positive' | 'negative' | 'warning';
}) {
  const colorClass = highlight === 'positive'
    ? 'text-emerald-600'
    : highlight === 'negative'
    ? 'text-red-600'
    : highlight === 'warning'
    ? 'text-amber-600'
    : '';

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm font-medium ${colorClass}`}>{value}</span>
    </div>
  );
}
