'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
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
import { Textarea } from '@/components/ui/textarea';
import { NumericInput } from '@/components/ui/numeric-input';
import {
  Brain,
  TrendingUp,
  Shield,
  MessageSquare,
  Lightbulb,
  Tag,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Eye,
  CheckCircle2,
  XCircle,
  Send,
  AlertTriangle,
  Sparkles,
  BarChart3,
  Search,
  Pencil,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getMLStats,
  getMLPredicciones,
  createMLPrediccion,
  deleteMLPrediccion,
  scanFraude,
  getMLAlertasFraude,
  updateMLAlertaFraude,
  createMLChatbotSesion,
  getMLChatbotSesiones,
  sendMLChatMessage,
  getMLChatbotMensajes,
  closeMLChatbotSesion,
  generateMLRecomendaciones,
  getMLRecomendaciones,
  updateMLRecomendacion,
  deleteMLRecomendacion,
  getMLCategoriasReglas,
  createMLCategoriaRegla,
  updateMLCategoriaRegla,
  deleteMLCategoriaRegla,
  categorizeMLDescription,
  type User as UserType,
  type Company as CompanyType,
  type MLStats,
  type MLPrediccion,
  type MLPrediccionCreate,
  type MLAlertaFraude,
  type MLAlertaFraudeUpdate,
  type MLChatbotSesion,
  type MLChatbotMensaje,
  type MLChatRequest,
  type MLRecomendacion,
  type MLRecomendacionUpdate,
  type MLCategoriaRegla,
  type MLCategoriaReglaCreate,
  type MLCategoriaReglaUpdate,
} from '@/lib/api';

interface ContaECMLAIProps {
  user: UserType;
  companies: CompanyType[];
}

// Color maps
const SEVERIDAD_COLORS: Record<string, string> = {
  baja: 'bg-green-100 text-green-800',
  media: 'bg-yellow-100 text-yellow-800',
  alta: 'bg-orange-100 text-orange-800',
  critica: 'bg-red-100 text-red-800',
};

const TIPO_PREDICCION_COLORS: Record<string, string> = {
  ventas: 'bg-emerald-100 text-emerald-800',
  ingresos: 'bg-teal-100 text-teal-800',
  gastos: 'bg-rose-100 text-rose-800',
  flujo_caja: 'bg-amber-100 text-amber-800',
};

const TIPO_RECOMENDACION_COLORS: Record<string, string> = {
  producto: 'bg-violet-100 text-violet-800',
  cliente: 'bg-cyan-100 text-cyan-800',
  precio: 'bg-fuchsia-100 text-fuchsia-800',
  inventario: 'bg-lime-100 text-lime-800',
  financiera: 'bg-sky-100 text-sky-800',
};

const ESTADO_PREDICCION_COLORS: Record<string, string> = {
  pendiente: 'bg-yellow-100 text-yellow-800',
  completada: 'bg-green-100 text-green-800',
  con_error: 'bg-red-100 text-red-800',
};

const ESTADO_ALERTA_COLORS: Record<string, string> = {
  pendiente: 'bg-yellow-100 text-yellow-800',
  confirmado: 'bg-red-100 text-red-800',
  descartado: 'bg-gray-100 text-gray-800',
  investigando: 'bg-orange-100 text-orange-800',
};

const ESTADO_RECOMENDACION_COLORS: Record<string, string> = {
  pendiente: 'bg-yellow-100 text-yellow-800',
  aplicada: 'bg-green-100 text-green-800',
  descartada: 'bg-gray-100 text-gray-800',
};

export function ContaECMLAI({ user: _user, companies }: ContaECMLAIProps) {
  const selectedCompany = companies[0];
  const companyId = selectedCompany?.id || '';

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<MLStats | null>(null);
  const [predicciones, setPredicciones] = useState<MLPrediccion[]>([]);
  const [alertas, setAlertas] = useState<MLAlertaFraude[]>([]);
  const [sesiones, setSesiones] = useState<MLChatbotSesion[]>([]);
  const [mensajes, setMensajes] = useState<MLChatbotMensaje[]>([]);
  const [recomendaciones, setRecomendaciones] = useState<MLRecomendacion[]>([]);
  const [reglas, setReglas] = useState<MLCategoriaRegla[]>([]);

  // Dialogs
  const [showPrediccionDialog, setShowPrediccionDialog] = useState(false);
  const [showReglaDialog, setShowReglaDialog] = useState(false);
  const [showAlertaDialog, setShowAlertaDialog] = useState(false);
  const [showPrediccionDetail, setShowPrediccionDetail] = useState(false);
  const [selectedPrediccion, setSelectedPrediccion] = useState<MLPrediccion | null>(null);
  const [selectedAlerta, setSelectedAlerta] = useState<MLAlertaFraude | null>(null);

  // Chat state
  const [activeSesionId, setActiveSesionId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');

  // Pestaña activa controlada (evita que vuelva a "predicciones" al recargar datos)
  const [activeTab, setActiveTab] = useState('predicciones');

  // Filters
  const [filterTipoPrediccion, setFilterTipoPrediccion] = useState<string>('');
  const [filterSeveridad, setFilterSeveridad] = useState<string>('');
  const [filterEstadoAlerta, setFilterEstadoAlerta] = useState<string>('');
  const [filterTipoRecomendacion, setFilterTipoRecomendacion] = useState<string>('');
  const [filterEstadoRecomendacion, setFilterEstadoRecomendacion] = useState<string>('');

  // Forms
  const [prediccionForm, setPrediccionForm] = useState<MLPrediccionCreate>({
    company_id: companyId,
    tipo: 'ventas',
    periodo_desde: new Date().toISOString().split('T')[0],
    periodo_hasta: new Date().toISOString().split('T')[0],
    modelo_usado: 'regresion_lineal',
  });

  const [reglaForm, setReglaForm] = useState<MLCategoriaReglaCreate>({
    company_id: companyId,
    categoria: '',
    subcategoria: '',
    palabras_clave: '',
    patron_regex: '',
    prioridad: 1,
  });

  const [editingRegla, setEditingRegla] = useState<MLCategoriaRegla | null>(null);
  const [alertaResolucion, setAlertaResolucion] = useState('');

  // Categorization test
  const [testDescripcion, setTestDescripcion] = useState('');
  const [testResult, setTestResult] = useState<{ categoria: string; subcategoria: string | null; confianza: number } | null>(null);

  // Loading states
  const [saving, setSaving] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [sendingChat, setSendingChat] = useState(false);
  const [testingCat, setTestingCat] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const initialLoadDoneRef = useRef(false);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    if (!initialLoadDoneRef.current) setLoading(true); // solo spinner en la carga inicial
    try {
      const [statsData, predsData, alertasData, sesionesData, recsData, reglasData] = await Promise.all([
        getMLStats(companyId).catch(() => null),
        getMLPredicciones({ company_id: companyId }).catch(() => []),
        getMLAlertasFraude({ company_id: companyId }).catch(() => []),
        getMLChatbotSesiones(companyId).catch(() => []),
        getMLRecomendaciones({ company_id: companyId }).catch(() => []),
        getMLCategoriasReglas(companyId).catch(() => []),
      ]);
      setStats(statsData);
      setPredicciones(predsData);
      setAlertas(alertasData);
      setSesiones(sesionesData);
      setRecomendaciones(recsData);
      setReglas(reglasData);
    } catch {
      toast.error('Error al cargar datos de ML/IA');
    } finally {
      initialLoadDoneRef.current = true;
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (activeSesionId) {
      loadMensajes(activeSesionId);
    }
  }, [activeSesionId]);

  useEffect(() => {
    scrollToBottom();
  }, [mensajes, scrollToBottom]);

  const loadMensajes = async (sesionId: string) => {
    try {
      const data = await getMLChatbotMensajes(sesionId);
      setMensajes(data);
    } catch {
      toast.error('Error al cargar mensajes');
    }
  };

  // ---- Predicciones handlers ----
  const handleCreatePrediccion = async () => {
    setSaving(true);
    try {
      await createMLPrediccion({ ...prediccionForm, company_id: companyId });
      toast.success('Predicción creada exitosamente');
      setShowPrediccionDialog(false);
      setPrediccionForm({
        company_id: companyId,
        tipo: 'ventas',
        periodo_desde: new Date().toISOString().split('T')[0],
        periodo_hasta: new Date().toISOString().split('T')[0],
        modelo_usado: 'regresion_lineal',
      });
      loadData();
    } catch {
      toast.error('Error al crear prediccion');
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePrediccion = async (id: string) => {
    try {
      await deleteMLPrediccion(id);
      toast.success('Predicción eliminada');
      loadData();
    } catch {
      toast.error('Error al eliminar prediccion');
    }
  };

  // ---- Fraude handlers ----
  const handleScanFraude = async () => {
    setScanning(true);
    try {
      const result = await scanFraude(companyId);
      toast.success(result.message || `${result.alertas_creadas} alertas creadas`);
      loadData();
    } catch {
      toast.error('Error al escanear fraude');
    } finally {
      setScanning(false);
    }
  };

  const handleUpdateAlerta = async (id: string, data: MLAlertaFraudeUpdate) => {
    try {
      await updateMLAlertaFraude(id, data);
      toast.success('Alerta actualizada');
      setShowAlertaDialog(false);
      setSelectedAlerta(null);
      setAlertaResolucion('');
      loadData();
    } catch {
      toast.error('Error al actualizar alerta');
    }
  };

  // ---- Chatbot handlers ----
  const handleNewSesion = async () => {
    try {
      const sesion = await createMLChatbotSesion(companyId);
      setActiveSesionId(sesion.id);
      setMensajes([]);
      toast.success('Nueva sesion de chat iniciada');
      loadData();
    } catch {
      toast.error('Error al crear sesion de chat');
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;
    if (!activeSesionId) {
      toast.error('Primero crea una sesion de chat');
      return;
    }
    setSendingChat(true);
    try {
      const request: MLChatRequest = {
        sesion_id: activeSesionId,
        mensaje: chatInput.trim(),
      };
      const response = await sendMLChatMessage(request);
      setChatInput('');
      if (response.sesion_id) {
        loadMensajes(response.sesion_id);
      }
      loadData();
    } catch {
      toast.error('Error al enviar mensaje');
    } finally {
      setSendingChat(false);
    }
  };

  const handleCloseSesion = async (id: string) => {
    try {
      await closeMLChatbotSesion(id);
      if (activeSesionId === id) {
        setActiveSesionId(null);
        setMensajes([]);
      }
      toast.success('Sesión cerrada');
      loadData();
    } catch {
      toast.error('Error al cerrar sesion');
    }
  };

  // ---- Recomendaciones handlers ----
  const handleGenerateRecomendaciones = async () => {
    setGenerating(true);
    try {
      const result = await generateMLRecomendaciones(companyId);
      const count = result?.recomendaciones_creadas ?? 0;
      if (count > 0) {
        toast.success(`Se generaron ${count} recomendación(es) basadas en tus datos`);
      } else {
        toast.info('No se encontraron datos suficientes: crea facturas, clientes, productos o cuentas por pagar para obtener recomendaciones.');
      }
      loadData();
    } catch {
      toast.error('Error al generar recomendaciones');
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdateRecomendacion = async (id: string, data: MLRecomendacionUpdate) => {
    try {
      await updateMLRecomendacion(id, data);
      toast.success('Recomendacion actualizada');
      loadData();
    } catch {
      toast.error('Error al actualizar recomendacion');
    }
  };

  const handleDeleteRecomendacion = async (id: string) => {
    try {
      await deleteMLRecomendacion(id);
      toast.success('Recomendacion eliminada');
      loadData();
    } catch {
      toast.error('Error al eliminar recomendacion');
    }
  };

  // ---- Categorizacion handlers ----
  const handleCreateRegla = async () => {
    setSaving(true);
    try {
      await createMLCategoriaRegla({ ...reglaForm, company_id: companyId });
      toast.success('Regla de categorizacion creada');
      setShowReglaDialog(false);
      setReglaForm({
        company_id: companyId,
        categoria: '',
        subcategoria: '',
        palabras_clave: '',
        patron_regex: '',
        prioridad: 1,
      });
      loadData();
    } catch {
      toast.error('Error al crear regla');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateRegla = async (id: string, data: MLCategoriaReglaUpdate) => {
    try {
      await updateMLCategoriaRegla(id, data);
      toast.success('Regla actualizada');
      setEditingRegla(null);
      loadData();
    } catch {
      toast.error('Error al actualizar regla');
    }
  };

  const handleDeleteRegla = async (id: string) => {
    try {
      await deleteMLCategoriaRegla(id);
      toast.success('Regla eliminada');
      loadData();
    } catch {
      toast.error('Error al eliminar regla');
    }
  };

  const handleTestCategorize = async () => {
    if (!testDescripcion.trim()) return;
    setTestingCat(true);
    try {
      const result = await categorizeMLDescription(companyId, testDescripcion.trim());
      setTestResult(result);
    } catch {
      toast.error('Error al categorizar descripcion');
    } finally {
      setTestingCat(false);
    }
  };

  // ---- Filtered data ----
  const filteredPredicciones = predicciones.filter(p => !filterTipoPrediccion || p.tipo === filterTipoPrediccion);
  const filteredAlertas = alertas.filter(a =>
    (!filterSeveridad || a.severidad === filterSeveridad) &&
    (!filterEstadoAlerta || a.estado === filterEstadoAlerta)
  );
  const filteredRecomendaciones = recomendaciones.filter(r =>
    (!filterTipoRecomendacion || r.tipo === filterTipoRecomendacion) &&
    (!filterEstadoRecomendacion || r.estado === filterEstadoRecomendacion)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="h-6 w-6" />
            ML / IA
          </h2>
          <p className="text-muted-foreground">Inteligencia artificial y aprendizaje automatico</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Predicciones</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.predicciones_completadas || 0}</div>
            <p className="text-xs text-muted-foreground">
              de {stats?.total_predicciones || 0} totales
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Alertas Fraude</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(stats?.alertas_pendientes || 0) + (stats?.alertas_criticas || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.alertas_criticas || 0} criticas, {stats?.alertas_pendientes || 0} pendientes
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recomendaciones</CardTitle>
            <Lightbulb className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(stats?.recomendaciones_pendientes || 0) + (stats?.recomendaciones_aplicadas || 0)}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.recomendaciones_aplicadas || 0} aplicadas, {stats?.recomendaciones_pendientes || 0} pendientes
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Chatbot</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.sesiones_activas || 0}</div>
            <p className="text-xs text-muted-foreground">
              de {stats?.total_sesiones_chatbot || 0} sesiones
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="predicciones" className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            <span className="hidden sm:inline">Predicciones</span>
          </TabsTrigger>
          <TabsTrigger value="fraude" className="flex items-center gap-1">
            <Shield className="h-3 w-3" />
            <span className="hidden sm:inline">Fraude</span>
          </TabsTrigger>
          <TabsTrigger value="chatbot" className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            <span className="hidden sm:inline">Chatbot</span>
          </TabsTrigger>
          <TabsTrigger value="recomendaciones" className="flex items-center gap-1">
            <Lightbulb className="h-3 w-3" />
            <span className="hidden sm:inline">Recomendaciones</span>
          </TabsTrigger>
          <TabsTrigger value="categorizacion" className="flex items-center gap-1">
            <Tag className="h-3 w-3" />
            <span className="hidden sm:inline">Categorizacion</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab: PREDICCIONES */}
        <TabsContent value="predicciones" className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Select value={filterTipoPrediccion} onValueChange={(v) => setFilterTipoPrediccion(v === 'all' ? '' : v)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filtrar tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="ventas">Ventas</SelectItem>
                  <SelectItem value="ingresos">Ingresos</SelectItem>
                  <SelectItem value="gastos">Gastos</SelectItem>
                  <SelectItem value="flujo_caja">Flujo de Caja</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={() => setShowPrediccionDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Nueva Predicción
            </Button>
          </div>

          {filteredPredicciones.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-10">
                <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No hay predicciones disponibles</p>
                <p className="text-xs text-muted-foreground mt-1">Cree una nueva prediccion para comenzar</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Modelo</TableHead>
                        <TableHead>Período</TableHead>
                        <TableHead>Confianza</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredPredicciones.map((pred) => (
                        <TableRow key={pred.id}>
                          <TableCell>
                            <Badge className={TIPO_PREDICCION_COLORS[pred.tipo] || 'bg-gray-100 text-gray-800'}>
                              {pred.tipo}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">{pred.modelo_usado}</TableCell>
                          <TableCell className="text-sm">
                            {new Date(pred.periodo_desde).toLocaleDateString('es-EC')} - {new Date(pred.periodo_hasta).toLocaleDateString('es-EC')}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Sparkles className="h-3 w-3 text-amber-500" />
                              <span className="text-sm">{(pred.confianza * 100).toFixed(1)}%</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={ESTADO_PREDICCION_COLORS[pred.estado] || 'bg-gray-100 text-gray-800'}>
                              {pred.estado}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedPrediccion(pred);
                                  setShowPrediccionDetail(true);
                                }}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeletePrediccion(pred.id)}
                              >
                                <Trash2 className="h-4 w-4 text-red-500" />
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
          )}
        </TabsContent>

        {/* Tab: FRAUDE */}
        <TabsContent value="fraude" className="space-y-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">
                Analisis de fraude: detecta transacciones inusuales comparando patrones historicos.
                Alertas sobre montos atipicos, frecuencias anormales o cambios sospechosos.
              </p>
            </CardContent>
          </Card>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Select value={filterSeveridad} onValueChange={(v) => setFilterSeveridad(v === 'all' ? '' : v)}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Severidad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="baja">Baja</SelectItem>
                  <SelectItem value="media">Media</SelectItem>
                  <SelectItem value="alta">Alta</SelectItem>
                  <SelectItem value="critica">Critica</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterEstadoAlerta} onValueChange={(v) => setFilterEstadoAlerta(v === 'all' ? '' : v)}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="pendiente">Pendiente</SelectItem>
                  <SelectItem value="investigando">Investigando</SelectItem>
                  <SelectItem value="confirmado">Confirmado</SelectItem>
                  <SelectItem value="descartado">Descartado</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleScanFraude} disabled={scanning}>
              {scanning ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Search className="h-4 w-4 mr-2" />}
              Escanear Fraude
            </Button>
          </div>

          {filteredAlertas.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-10">
                <Shield className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No hay alertas de fraude</p>
                <p className="text-xs text-muted-foreground mt-1">Ejecute un escaneo para detectar anomalias</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Tipo Deteccion</TableHead>
                        <TableHead>Severidad</TableHead>
                        <TableHead>Puntuacion</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Descripción</TableHead>
                        <TableHead>Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredAlertas.map((alerta) => (
                        <TableRow key={alerta.id}>
                          <TableCell className="text-sm font-medium">{alerta.tipo_deteccion}</TableCell>
                          <TableCell>
                            <Badge className={SEVERIDAD_COLORS[alerta.severidad] || 'bg-gray-100 text-gray-800'}>
                              {alerta.severidad}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <AlertTriangle className={`h-3 w-3 ${alerta.puntuacion_fraude > 0.7 ? 'text-red-500' : alerta.puntuacion_fraude > 0.4 ? 'text-orange-500' : 'text-green-500'}`} />
                              <span className="text-sm">{(alerta.puntuacion_fraude * 100).toFixed(1)}%</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={ESTADO_ALERTA_COLORS[alerta.estado] || 'bg-gray-100 text-gray-800'}>
                              {alerta.estado}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm max-w-[200px] truncate">{alerta.descripcion}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {alerta.estado === 'pendiente' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleUpdateAlerta(alerta.id, { estado: 'investigando' })}
                                  title="Investigar"
                                >
                                  <Search className="h-4 w-4 text-orange-500" />
                                </Button>
                              )}
                              {(alerta.estado === 'pendiente' || alerta.estado === 'investigando') && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleUpdateAlerta(alerta.id, { estado: 'confirmado' })}
                                    title="Confirmar"
                                  >
                                    <CheckCircle2 className="h-4 w-4 text-red-500" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      setSelectedAlerta(alerta);
                                      setShowAlertaDialog(true);
                                    }}
                                    title="Descartar con nota"
                                  >
                                    <XCircle className="h-4 w-4 text-gray-500" />
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
          )}
        </TabsContent>

        {/* Tab: CHATBOT */}
        <TabsContent value="chatbot" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Sessions sidebar */}
            <Card className="md:col-span-1">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">Sesiones</CardTitle>
                  <Button size="sm" onClick={handleNewSesion}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-2">
                <ScrollArea className="max-h-80">
                  {sesiones.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">No hay sesiones</p>
                  ) : (
                    <div className="space-y-1">
                      {sesiones.map((sesion) => (
                        <div
                          key={sesion.id}
                          className={`flex items-center justify-between p-2 rounded-lg cursor-pointer text-sm transition-colors ${
                            activeSesionId === sesion.id
                              ? 'bg-primary/10 text-primary font-medium'
                              : 'hover:bg-accent'
                          }`}
                          onClick={() => {
                            setActiveSesionId(sesion.id);
                            loadMensajes(sesion.id);
                          }}
                        >
                          <div className="flex-1 min-w-0">
                            <p className="truncate">{sesion.titulo || 'Sesión sin titulo'}</p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(sesion.created_at).toLocaleDateString('es-EC')}
                            </p>
                          </div>
                          <div className="flex items-center gap-1 ml-2">
                            <Badge variant="outline" className="text-[10px] px-1">
                              {sesion.estado}
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCloseSesion(sesion.id);
                              }}
                            >
                              <XCircle className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Chat area */}
            <Card className="md:col-span-2 flex flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Asistente IA ContaEC
                </CardTitle>
                <CardDescription>
                  Pregunte sobre facturacion, impuestos, contabilidad y mas
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col p-4">
                <ScrollArea className="flex-1 max-h-80 mb-4">
                  {mensajes.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8">
                      <MessageSquare className="h-12 w-12 text-muted-foreground mb-3" />
                      <p className="text-muted-foreground text-sm">Inicie una conversacion con el asistente IA</p>
                      <p className="text-xs text-muted-foreground mt-1">Puede preguntar sobre facturacion, SRI, impuestos, etc.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {mensajes.map((msg) => (
                        <div
                          key={msg.id}
                          className={`flex ${msg.rol === 'usuario' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-[80%] rounded-lg p-3 ${
                              msg.rol === 'usuario'
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-accent'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap">{msg.contenido}</p>
                            {msg.rol === 'asistente' && msg.intencion_detectada && (
                              <Badge variant="outline" className="mt-2 text-[10px]">
                                {msg.intencion_detectada}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                      <div ref={chatEndRef} />
                    </div>
                  )}
                </ScrollArea>
                <div className="flex items-center gap-2">
                  <NumericInput placeholder="Escriba su mensaje..."
 value={chatInput}
 onChange={(e) => setChatInput(e.target.value)}
 onKeyDown={(e) => {
 if (e.key === 'Enter' && !e.shiftKey) {
 e.preventDefault();
 handleSendMessage();
 }
 }}
 disabled={sendingChat}
 />
 <Button
 onClick={handleSendMessage}
 disabled={sendingChat || !chatInput.trim()}
 size="icon"
 >
 {sendingChat ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
 </Button>
 </div>
 </CardContent>
 </Card>
 </div>
 </TabsContent>

 {/* Tab: RECOMENDACIONES */}
 <TabsContent value="recomendaciones" className="space-y-4">
 <Card>
 <CardContent className="pt-4">
 <p className="text-sm text-muted-foreground">
 Las recomendaciones se generan analizando <strong>tus propios datos</strong>:
 facturas autorizadas (productos más/menos vendidos, mejores clientes), stock
 de productos por debajo del mínimo e inventario, y cuentas por pagar pendientes.
 Si acabas de empezar, primero crea facturas, clientes, productos o compras para
 que el sistema tenga información de la que extraer recomendaciones.
 </p>
 </CardContent>
 </Card>
 <div className="flex items-center justify-between flex-wrap gap-2">
 <div className="flex items-center gap-2">
 <Select value={filterTipoRecomendacion} onValueChange={(v) => setFilterTipoRecomendacion(v === 'all' ? '' : v)}>
 <SelectTrigger className="w-[150px]">
 <SelectValue placeholder="Tipo" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">Todos</SelectItem>
 <SelectItem value="producto">Producto</SelectItem>
 <SelectItem value="cliente">Cliente</SelectItem>
 <SelectItem value="precio">Precio</SelectItem>
 <SelectItem value="inventario">Inventario</SelectItem>
 <SelectItem value="financiera">Financiera</SelectItem>
 </SelectContent>
 </Select>
 <Select value={filterEstadoRecomendacion} onValueChange={(v) => setFilterEstadoRecomendacion(v === 'all' ? '' : v)}>
 <SelectTrigger className="w-[150px]">
 <SelectValue placeholder="Estado" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">Todos</SelectItem>
 <SelectItem value="pendiente">Pendiente</SelectItem>
 <SelectItem value="aplicada">Aplicada</SelectItem>
 <SelectItem value="descartada">Descartada</SelectItem>
 </SelectContent>
 </Select>
 </div>
 <Button onClick={handleGenerateRecomendaciones} disabled={generating}>
 {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
 Generar Recomendaciones
 </Button>
 </div>

 {filteredRecomendaciones.length === 0 ? (
 <Card>
 <CardContent className="flex flex-col items-center justify-center py-10">
 <Lightbulb className="h-12 w-12 text-muted-foreground mb-4" />
 <p className="text-muted-foreground">No hay recomendaciones disponibles</p>
 <p className="text-xs text-muted-foreground mt-1">Genere recomendaciones basadas en sus datos</p>
 </CardContent>
 </Card>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {filteredRecomendaciones.map((rec) => (
 <Card key={rec.id}>
 <CardHeader className="pb-3">
 <div className="flex items-start justify-between">
 <div className="flex items-center gap-2">
 <Badge className={TIPO_RECOMENDACION_COLORS[rec.tipo] || 'bg-gray-100 text-gray-800'}>
 {rec.tipo}
 </Badge>
 <Badge className={ESTADO_RECOMENDACION_COLORS[rec.estado] || 'bg-gray-100 text-gray-800'}>
 {rec.estado}
 </Badge>
 </div>
 <div className="flex items-center gap-1">
 <Sparkles className="h-3 w-3 text-amber-500" />
 <span className="text-sm">{(rec.confianza * 100).toFixed(1)}%</span>
 </div>
 </div>
 <CardTitle className="text-base mt-2">{rec.titulo}</CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 <p className="text-sm text-muted-foreground">{rec.descripcion}</p>
 {rec.impacto_estimado && (
 <div className="flex items-center gap-1 text-sm">
 <TrendingUp className="h-3 w-3 text-green-500" />
 <span>Impacto estimado: {rec.impacto_estimado}</span>
 </div>
 )}
 {rec.fecha_aplicacion && (
 <p className="text-xs text-muted-foreground">
 Aplicada: {new Date(rec.fecha_aplicacion).toLocaleDateString('es-EC')}
 </p>
 )}
 {rec.estado === 'pendiente' && (
 <div className="flex items-center gap-2 pt-2">
 <Button
 size="sm"
 onClick={() => handleUpdateRecomendacion(rec.id, { estado: 'aplicada' })}
 >
 <CheckCircle2 className="h-4 w-4 mr-1" />
 Aplicar
 </Button>
 <Button
 size="sm"
 variant="outline"
 onClick={() => handleUpdateRecomendacion(rec.id, { estado: 'descartada' })}
 >
 <XCircle className="h-4 w-4 mr-1" />
 Descartar
 </Button>
 <Button
 size="sm"
 variant="ghost"
 onClick={() => handleDeleteRecomendacion(rec.id)}
 >
 <Trash2 className="h-4 w-4 text-red-500" />
 </Button>
 </div>
 )}
 </CardContent>
 </Card>
 ))}
 </div>
 )}
 </TabsContent>

 {/* Tab: CATEGORIZACION */}
 <TabsContent value="categorizacion" className="space-y-4">
 <Card>
 <CardContent className="pt-4">
 <div className="space-y-2 text-sm text-muted-foreground">
 <p>
 Patrón Regex: expresion regular que busca coincidencias en la descripcion.
 Ejemplo: <code className="bg-muted px-1 rounded">.*SUPERMERCADO.*</code> para compras en supermercados
 </p>
 <p>
 Prioridad: 1 = maxima (se evalua primero), 10 = minima.
 </p>
 </div>
 </CardContent>
 </Card>
 <div className="flex items-center justify-between">
 <h3 className="text-lg font-semibold">Reglas de Categorizacion</h3>
 <Button onClick={() => {
 setEditingRegla(null);
 setReglaForm({
 company_id: companyId,
 categoria: '',
 subcategoria: '',
 palabras_clave: '',
 patron_regex: '',
 prioridad: 1,
 });
 setShowReglaDialog(true);
 }}>
 <Plus className="h-4 w-4 mr-2" />
 Nueva Regla
 </Button>
 </div>

 {reglas.length === 0 ? (
 <Card>
 <CardContent className="flex flex-col items-center justify-center py-10">
 <Tag className="h-12 w-12 text-muted-foreground mb-4" />
 <p className="text-muted-foreground">No hay reglas de categorizacion</p>
 <p className="text-xs text-muted-foreground mt-1">Cree reglas para categorizar automaticamente sus transacciones</p>
 </CardContent>
 </Card>
 ) : (
 <Card>
 <CardContent className="p-0">
 <ScrollArea className="max-h-96">
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>Categoria</TableHead>
 <TableHead>Subcategoria</TableHead>
 <TableHead>Palabras Clave</TableHead>
 <TableHead>Prioridad</TableHead>
 <TableHead>Activa</TableHead>
 <TableHead>Aplicaciones</TableHead>
 <TableHead>Acciones</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {reglas.map((regla) => (
 <TableRow key={regla.id}>
 <TableCell className="font-medium">{regla.categoria}</TableCell>
 <TableCell className="text-sm">{regla.subcategoria || '-'}</TableCell>
 <TableCell className="text-sm max-w-[200px] truncate">
 {regla.palabras_clave || '-'}
 </TableCell>
 <TableCell className="text-sm">{regla.prioridad}</TableCell>
 <TableCell>
 {regla.es_activa ? (
 <CheckCircle2 className="h-4 w-4 text-green-500" />
 ) : (
 <XCircle className="h-4 w-4 text-gray-400" />
 )}
 </TableCell>
 <TableCell className="text-sm">{regla.aplicaciones_count}</TableCell>
 <TableCell>
 <div className="flex items-center gap-1">
 <Button
 variant="ghost"
 size="sm"
 onClick={() => {
 setEditingRegla(regla);
 setReglaForm({
 company_id: companyId,
 categoria: regla.categoria,
 subcategoria: regla.subcategoria || '',
 palabras_clave: regla.palabras_clave || '',
 patron_regex: regla.patron_regex || '',
 prioridad: regla.prioridad,
 });
 setShowReglaDialog(true);
 }}
 >
 <Pencil className="h-4 w-4" />
 </Button>
 <Button
 variant="ghost"
 size="sm"
 onClick={() => handleDeleteRegla(regla.id)}
 >
 <Trash2 className="h-4 w-4 text-red-500" />
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
 )}

 {/* Test Categorization */}
 <Card>
 <CardHeader>
 <CardTitle className="text-sm flex items-center gap-2">
 <Search className="h-4 w-4" />
 Probar Categorizacion
 </CardTitle>
 <CardDescription>
 Ingrese una descripcion para probar la categorizacion automatica
 </CardDescription>
 </CardHeader>
 <CardContent className="space-y-3">
 <div className="flex items-center gap-2">
 <Input
 placeholder="Descripción de la transaccion..."
 value={testDescripcion}
 onChange={(e) => setTestDescripcion(e.target.value)}
 onKeyDown={(e) => {
 if (e.key === 'Enter') handleTestCategorize();
 }}
 />
 <Button onClick={handleTestCategorize} disabled={testingCat || !testDescripcion.trim()}>
 {testingCat ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
 </Button>
 </div>
 {testResult && (
 <div className="p-3 rounded-lg bg-accent space-y-1">
 <div className="flex items-center gap-2">
 <Tag className="h-4 w-4" />
 <span className="text-sm font-medium">Categoria: {testResult.categoria}</span>
 </div>
 {testResult.subcategoria && (
 <p className="text-sm text-muted-foreground ml-6">Subcategoria: {testResult.subcategoria}</p>
 )}
 <div className="flex items-center gap-1 ml-6">
 <Sparkles className="h-3 w-3 text-amber-500" />
 <span className="text-xs">Confianza: {(testResult.confianza * 100).toFixed(1)}%</span>
 </div>
 </div>
 )}
 </CardContent>
 </Card>
 </TabsContent>
 </Tabs>

 {/* Dialog: Nueva Predicción */}
 <Dialog open={showPrediccionDialog} onOpenChange={setShowPrediccionDialog}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>Nueva Predicción</DialogTitle>
 <DialogDescription>
 Configure los parametros para generar una nueva prediccion
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="space-y-2">
 <Label>Tipo de Predicción</Label>
 <Select
 value={prediccionForm.tipo}
 onValueChange={(v) => setPrediccionForm({ ...prediccionForm, tipo: v })}
 >
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="ventas">Ventas</SelectItem>
 <SelectItem value="ingresos">Ingresos</SelectItem>
 <SelectItem value="gastos">Gastos</SelectItem>
 <SelectItem value="flujo_caja">Flujo de Caja</SelectItem>
 </SelectContent>
 </Select>
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>Desde</Label>
 <Input
 type="date"
 value={prediccionForm.periodo_desde}
 onChange={(e) => setPrediccionForm({ ...prediccionForm, periodo_desde: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>Hasta</Label>
 <Input
 type="date"
 value={prediccionForm.periodo_hasta}
 onChange={(e) => setPrediccionForm({ ...prediccionForm, periodo_hasta: e.target.value })}
 />
 </div>
 </div>
 <div className="space-y-2">
 <Label>Modelo</Label>
 <Select
 value={prediccionForm.modelo_usado || 'regresion_lineal'}
 onValueChange={(v) => setPrediccionForm({ ...prediccionForm, modelo_usado: v })}
 >
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="regresion_lineal">Regresion Lineal</SelectItem>
 <SelectItem value="promedio_movil">Promedio Movil</SelectItem>
 <SelectItem value="suavizacion_exponencial">Suavizacion Exponencial</SelectItem>
 <SelectItem value="arima">ARIMA</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>
 <div className="flex justify-end gap-2 pt-4">
 <Button variant="outline" onClick={() => setShowPrediccionDialog(false)}>
 Cancelar
 </Button>
 <Button onClick={handleCreatePrediccion} disabled={saving}>
 {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
 Crear Predicción
 </Button>
 </div>
 </DialogContent>
 </Dialog>

 {/* Dialog: Predicción Detail */}
 <Dialog open={showPrediccionDetail} onOpenChange={setShowPrediccionDetail}>
 <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
 <DialogHeader>
 <DialogTitle>Detalle de Predicción</DialogTitle>
 <DialogDescription>
 Resultados y metricas de la prediccion
 </DialogDescription>
 </DialogHeader>
 {selectedPrediccion && (
 <div className="space-y-4">
 <div className="grid grid-cols-2 gap-4">
 <div>
 <p className="text-xs text-muted-foreground">Tipo</p>
 <Badge className={TIPO_PREDICCION_COLORS[selectedPrediccion.tipo] || 'bg-gray-100 text-gray-800'}>
 {selectedPrediccion.tipo}
 </Badge>
 </div>
 <div>
 <p className="text-xs text-muted-foreground">Estado</p>
 <Badge className={ESTADO_PREDICCION_COLORS[selectedPrediccion.estado] || 'bg-gray-100 text-gray-800'}>
 {selectedPrediccion.estado}
 </Badge>
 </div>
 <div>
 <p className="text-xs text-muted-foreground">Modelo</p>
 <p className="text-sm font-medium">{selectedPrediccion.modelo_usado}</p>
 </div>
 <div>
 <p className="text-xs text-muted-foreground">Confianza</p>
 <p className="text-sm font-medium">{(selectedPrediccion.confianza * 100).toFixed(1)}%</p>
 </div>
 </div>
 <Separator />
 <div>
 <p className="text-xs text-muted-foreground mb-1">Período</p>
 <p className="text-sm">
 {new Date(selectedPrediccion.periodo_desde).toLocaleDateString('es-EC')} - {new Date(selectedPrediccion.periodo_hasta).toLocaleDateString('es-EC')}
 </p>
 </div>
 {selectedPrediccion.resultado && (
 <div>
 <p className="text-xs text-muted-foreground mb-1">Resultado</p>
 <ScrollArea className="max-h-40">
 <pre className="text-xs bg-accent p-3 rounded-lg whitespace-pre-wrap">
 {JSON.stringify(JSON.parse(selectedPrediccion.resultado), null, 2)}
 </pre>
 </ScrollArea>
 </div>
 )}
 {selectedPrediccion.metricas && (
 <div>
 <p className="text-xs text-muted-foreground mb-1">Metricas</p>
 <ScrollArea className="max-h-40">
 <pre className="text-xs bg-accent p-3 rounded-lg whitespace-pre-wrap">
 {JSON.stringify(JSON.parse(selectedPrediccion.metricas), null, 2)}
 </pre>
 </ScrollArea>
 </div>
 )}
 </div>
 )}
 </DialogContent>
 </Dialog>

 {/* Dialog: Descartar Alerta */}
 <Dialog open={showAlertaDialog} onOpenChange={setShowAlertaDialog}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>Descartar Alerta de Fraude</DialogTitle>
 <DialogDescription>
 Proporcione una nota de resolucion para descartar esta alerta
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 {selectedAlerta && (
 <div className="p-3 bg-accent rounded-lg">
 <p className="text-sm font-medium">{selectedAlerta.tipo_deteccion}</p>
 <p className="text-xs text-muted-foreground mt-1">{selectedAlerta.descripcion}</p>
 </div>
 )}
 <div className="space-y-2">
 <Label>Nota de Resolución</Label>
 <Textarea
 placeholder="Explique por que se descarta esta alerta..."
 value={alertaResolucion}
 onChange={(e) => setAlertaResolucion(e.target.value)}
 />
 </div>
 </div>
 <div className="flex justify-end gap-2 pt-4">
 <Button variant="outline" onClick={() => {
 setShowAlertaDialog(false);
 setSelectedAlerta(null);
 setAlertaResolucion('');
 }}>
 Cancelar
 </Button>
 <Button
 variant="destructive"
 onClick={() => {
 if (selectedAlerta) {
 handleUpdateAlerta(selectedAlerta.id, {
 estado: 'descartado',
 resolucion_nota: alertaResolucion || undefined,
 });
 }
 }}
 >
 Descartar Alerta
 </Button>
 </div>
 </DialogContent>
 </Dialog>

 {/* Dialog: Nueva/Editar Regla */}
 <Dialog open={showReglaDialog} onOpenChange={setShowReglaDialog}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>{editingRegla ? 'Editar Regla' : 'Nueva Regla de Categorizacion'}</DialogTitle>
 <DialogDescription>
 {editingRegla ? 'Modifique los campos de la regla' : 'Defina una nueva regla para categorizar automaticamente'}
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="space-y-2">
 <Label>Categoria</Label>
 <Input
 placeholder="Ej: Servicios, Ventas, Gastos..."
 value={reglaForm.categoria}
 onChange={(e) => setReglaForm({ ...reglaForm, categoria: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>Subcategoria</Label>
 <Input
 placeholder="Subcategoria (opcional)"
 value={reglaForm.subcategoria || ''}
 onChange={(e) => setReglaForm({ ...reglaForm, subcategoria: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>Palabras Clave</Label>
 <Input
 placeholder="Separadas por comas: factura, venta, servicio"
 value={reglaForm.palabras_clave || ''}
 onChange={(e) => setReglaForm({ ...reglaForm, palabras_clave: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>Patrón Regex</Label>
 <Input
 placeholder="Expresion regular (opcional)"
 value={reglaForm.patron_regex || ''}
 onChange={(e) => setReglaForm({ ...reglaForm, patron_regex: e.target.value })}
 />
 <p className="text-xs text-muted-foreground">
 Patrón Regex: expresion regular que busca coincidencias en la descripcion.
 Ejemplo: <code className="bg-muted px-1 rounded">.*SUPERMERCADO.*</code> para compras en supermercados
 </p>
 </div>
 <div className="space-y-2">
 <Label>Prioridad</Label>
 <Input
 
 min={1}
 max={100}
 value={reglaForm.prioridad || 1}
 onChange={(e) => setReglaForm({ ...reglaForm, prioridad: parseInt(e.target.value) || 1 })} />
              <p className="text-xs text-muted-foreground">
                Prioridad: 1 = maxima (se evalua primero), 10 = minima.
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => {
              setShowReglaDialog(false);
              setEditingRegla(null);
            }}>
              Cancelar
            </Button>
            <Button
              onClick={() => {
                if (editingRegla) {
                  handleUpdateRegla(editingRegla.id, {
                    categoria: reglaForm.categoria,
                    subcategoria: reglaForm.subcategoria || undefined,
                    palabras_clave: reglaForm.palabras_clave || undefined,
                    patron_regex: reglaForm.patron_regex || undefined,
                    prioridad: reglaForm.prioridad,
                  });
                } else {
                  handleCreateRegla();
                }
              }}
              disabled={saving}
            >
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingRegla ? 'Guardar Cambios' : 'Crear Regla'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
