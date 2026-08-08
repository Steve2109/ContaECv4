'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import {
  Mail,
  Plus,
  Edit,
  Trash2,
  Eye,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import {
  getEmailTemplates,
  createEmailTemplate,
  updateEmailTemplate,
  deleteEmailTemplate,
  previewEmailTemplateCustom,
  type EmailTemplate,
} from '@/lib/api';

const TEMPLATE_TYPES = [
  { value: 'factura', label: 'Factura' },
  { value: 'nota_credito', label: 'Nota de Crédito' },
  { value: 'nota_debito', label: 'Nota de Débito' },
  { value: 'proforma', label: 'Proforma' },
  { value: 'general', label: 'General' },
];

const AVAILABLE_VARIABLES = [
  { variable: '{{razon_social}}', description: 'Razón social de la empresa' },
  { variable: '{{ruc}}', description: 'RUC de la empresa' },
  { variable: '{{cliente_nombre}}', description: 'Nombre del cliente' },
  { variable: '{{cliente_cedula}}', description: 'Cédula/RUC del cliente' },
  { variable: '{{secuencial}}', description: 'Número secuencial del comprobante' },
  { variable: '{{clave_acceso}}', description: 'Clave de acceso SRI' },
  { variable: '{{fecha_emision}}', description: 'Fecha de emisión' },
  { variable: '{{subtotal}}', description: 'Subtotal sin impuestos' },
  { variable: '{{iva}}', description: 'Valor del IVA' },
  { variable: '{{total}}', description: 'Total a pagar' },
  { variable: '{{numero_autorizacion}}', description: 'Número de autorización SRI' },
];

interface EmailTemplateEditorProps {
  companyId?: string;
}

export function EmailTemplateEditor({ companyId: _companyId }: EmailTemplateEditorProps) {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    nombre: '',
    tipo: 'factura',
    asunto: '',
    cuerpo_html: '',
    cuerpo_texto: '',
    is_default: false,
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  async function loadTemplates() {
    setLoading(true);
    try {
      const data = await getEmailTemplates();
      setTemplates(data);
    } catch {
      toast.error('Error al cargar plantillas');
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setFormData({
      nombre: '',
      tipo: 'factura',
      asunto: '',
      cuerpo_html: '',
      cuerpo_texto: '',
      is_default: false,
    });
    setEditingTemplate(null);
  }

  function handleEdit(template: EmailTemplate) {
    setEditingTemplate(template);
    setFormData({
      nombre: template.nombre,
      tipo: template.tipo,
      asunto: template.asunto,
      cuerpo_html: template.cuerpo_html,
      cuerpo_texto: template.cuerpo_texto || '',
      is_default: template.is_default,
    });
    setIsDialogOpen(true);
  }

  async function handleSave() {
    if (!formData.nombre || !formData.asunto || !formData.cuerpo_html) {
      toast.error('Complete los campos requeridos');
      return;
    }

    try {
      if (editingTemplate) {
        await updateEmailTemplate(editingTemplate.id, formData);
        toast.success('Plantilla actualizada correctamente');
      } else {
        await createEmailTemplate(formData);
        toast.success('Plantilla creada correctamente');
      }
      setIsDialogOpen(false);
      resetForm();
      loadTemplates();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al guardar plantilla');
    }
  }

  async function handleDelete(template: EmailTemplate) {
    if (!confirm(`¿Eliminar planta "${template.nombre}"?`)) return;

    try {
      await deleteEmailTemplate(template.id);
      toast.success('Plantilla eliminada');
      loadTemplates();
    } catch {
      toast.error('Error al eliminar plantilla');
    }
  }

  async function handlePreview() {
    try {
      const sampleData = {
        razon_social: 'MI EMPRESA S.A.',
        ruc: '1791234567001',
        cliente_nombre: 'Juan Pérez',
        cliente_cedula: '1712345678',
        secuencial: '001001000123456',
        clave_acceso: '1906202401179123456700120010010001234567012345678',
        fecha_emision: '19/06/2024',
        subtotal: '100.00',
        iva: '15.00',
        total: '115.00',
        numero_autorizacion: '1234567890123456789012345678901234567890',
      };

      const result = await previewEmailTemplateCustom({
        cuerpo_html: formData.cuerpo_html,
        asunto: formData.asunto,
        sample_data: sampleData,
      });

      setPreviewHtml(result.rendered_html ?? result.cuerpo_html ?? "");
      setIsPreviewOpen(true);
    } catch {
      toast.error('Error al generar vista previa');
    }
  }

  function insertVariable(variable: string) {
    const textarea = document.getElementById('cuerpo_html') as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = formData.cuerpo_html;
      const before = text.substring(0, start);
      const after = text.substring(end);
      setFormData({ ...formData, cuerpo_html: before + variable + after });
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Plantillas de Correo</h2>
          <p className="text-muted-foreground">
            Cree y gestione plantillas para envío de comprobantes
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Nueva Plantilla
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingTemplate ? 'Editar Plantilla' : 'Nueva Plantilla'}
              </DialogTitle>
              <DialogDescription>
                Configure la plantilla de correo para envío de comprobantes
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* Nombre y Tipo */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="nombre">Nombre *</Label>
                  <Input
                    id="nombre"
                    value={formData.nombre}
                    onChange={(e) =>
                      setFormData({ ...formData, nombre: e.target.value })
                    }
                    placeholder="Ej: Factura Estándar"
                  />
                </div>
                <div>
                  <Label htmlFor="tipo">Tipo *</Label>
                  <Select
                    value={formData.tipo}
                    onValueChange={(value) =>
                      setFormData({ ...formData, tipo: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TEMPLATE_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Asunto */}
              <div>
                <Label htmlFor="asunto">Asunto *</Label>
                <Input
                  id="asunto"
                  value={formData.asunto}
                  onChange={(e) =>
                    setFormData({ ...formData, asunto: e.target.value })
                  }
                  placeholder="Factura Electrónica #{{secuencial}} - {{razon_social}}"
                />
              </div>

              {/* Variables disponibles */}
              <div>
                <Label>Variables Disponibles</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {AVAILABLE_VARIABLES.map((v) => (
                    <Badge
                      key={v.variable}
                      variant="outline"
                      className="cursor-pointer hover:bg-primary hover:text-primary-foreground"
                      onClick={() => insertVariable(v.variable)}
                    >
                      {v.variable}
                    </Badge>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {`Click para insertar • También disponíveis: {{}}fecha_autorizacion, {{}}establecimiento, {{}}direccion, {{}}email, {{}}telefono`}
                </p>
              </div>

              {/* Cuerpo HTML */}
              <div>
                <Label htmlFor="cuerpo_html">Cuerpo HTML *</Label>
                <Textarea
                  id="cuerpo_html"
                  value={formData.cuerpo_html}
                  onChange={(e) =>
                    setFormData({ ...formData, cuerpo_html: e.target.value })
                  }
                  placeholder="<html><body>...</body></html>"
                  rows={12}
                  className="font-mono text-sm"
                />
              </div>

              {/* Cuerpo Texto */}
              <div>
                <Label htmlFor="cuerpo_texto">Cuerpo Texto Plano (opcional)</Label>
                <Textarea
                  id="cuerpo_texto"
                  value={formData.cuerpo_texto}
                  onChange={(e) =>
                    setFormData({ ...formData, cuerpo_texto: e.target.value })
                  }
                  placeholder="Texto plano para clientes sin HTML"
                  rows={6}
                  className="font-mono text-sm"
                />
              </div>

              {/* Default */}
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_default"
                  checked={formData.is_default}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_default: checked })
                  }
                />
                <Label htmlFor="is_default">Plantilla por defecto para este tipo</Label>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={handlePreview}>
                  <Eye className="w-4 h-4 mr-2" />
                  Vista Previa
                </Button>
                <Button onClick={handleSave}>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Guardar
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Preview Dialog */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Vista Previa de Plantilla</DialogTitle>
            <DialogDescription>
              Vista previa con datos de ejemplo
            </DialogDescription>
          </DialogHeader>
          <div
            className="border rounded-md p-4 bg-white"
            dangerouslySetInnerHTML={{ __html: previewHtml }}
          />
        </DialogContent>
      </Dialog>

      {/* Templates List */}
      <Card>
        <CardHeader>
          <CardTitle>Plantillas Configuradas</CardTitle>
          <CardDescription>
            {templates.length} plantilla(s) disponible(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              <RefreshCw className="w-8 h-8 mx-auto animate-spin mb-2" />
              Cargando plantillas...
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Mail className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No hay plantillas configuradas</p>
              <p className="text-sm">
                Haga clic en "Nueva Plantilla" para crear una
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Por Defecto</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.id}>
                    <TableCell className="font-medium">
                      {template.nombre}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {TEMPLATE_TYPES.find((t) => t.value === template.tipo)?.label || template.tipo}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {template.is_default ? (
                        <Badge variant="default">Sí</Badge>
                      ) : (
                        <Badge variant="secondary">No</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={template.is_active ? 'default' : 'secondary'}>
                        {template.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(template)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(template)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}