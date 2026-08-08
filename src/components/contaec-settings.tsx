'use client';

import Image from 'next/image';
import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  User,
  KeyRound,
  Globe,
  Mail,
  Shield,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Loader2,
  FileKey,
  Eye,
  EyeOff,
  Bug,
  Lock,
  Server,
  TestTube,
  Database,
  Download,
  RotateCcw,
  HardDrive,
  RefreshCw,
  Building2,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from 'next-themes';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  getUserConfig,
  getCompanies,
  getCompanyConfig,
  updateCompanyConfig,
  getClamavStatus,
  uploadDigitalSignature,
  toggleVirusTotal,
  configureSMTP,
  testSMTP,
  switchEnvironmentMode,
  updateProfile,
  changePassword,
  uploadCompanyLogo,
  validateSignature,
  getBackups,
  createBackup,
  downloadBackup,
  restoreBackup,
  type UserConfig,
  type Company,
  type CompanyConfig,
  type SignatureValidation,
  type BackupInfo,
  type RestoreBackupResponse,
} from '@/lib/api';

// SMTP provider presets
const SMTP_PRESETS: Record<string, { host: string; port: number; protocol: string; ssl: boolean }> = {
  gmail: { host: 'smtp.gmail.com', port: 587, protocol: 'TLS', ssl: false },
  zoho: { host: 'smtp.zoho.com', port: 587, protocol: 'TLS', ssl: false },
  outlook: { host: 'smtp-mail.outlook.com', port: 587, protocol: 'TLS', ssl: false },
  office365: { host: 'smtp.office365.com', port: 587, protocol: 'TLS', ssl: false },
};

export function ContaECSettings({ user }: { user?: { is_admin: boolean; email: string; full_name: string } }) {
  const isAdmin = user?.is_admin ?? false;

  // Admin users see only the Admin Panel shortcut, not regular settings
  if (isAdmin) {
    return <AdminSettingsView user={user} />;
  }

  return <RegularUserSettings />;
}

// ─── Admin Settings View ────────────────────────────────────────
function AdminSettingsView({ user }: { user?: { email: string; full_name: string } }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Image
          src="/logo.svg"
          alt="ContaEC"
          width={32}
          height={32}
          className="h-8 w-8"
          priority
        />
        <div>
          <h2 className="text-2xl font-bold">Configuracion</h2>
          <p className="text-muted-foreground">
            Panel de administracion
          </p>
        </div>
      </div>

      <Card className="border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Admin Panel
          </CardTitle>
          <CardDescription>
            Como administrador, gestione usuarios, licencias y configuracion del sistema desde el panel de administracion.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-muted/50 p-4 space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <User className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Administrador:</span>
              <span className="font-medium">{user?.full_name || user?.email}</span>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Use el boton <strong>&quot;Admin Panel&quot;</strong> en la barra lateral para acceder a:
          </p>
          <ul className="text-sm text-muted-foreground space-y-1 ml-4 list-disc">
            <li>Resumen general del sistema</li>
            <li>Gestion de usuarios y licencias</li>
            <li>Salud del sistema (CPU, memoria, disco)</li>
            <li>Problemas de seguridad</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Regular User Settings (original full settings) ─────────────
function RegularUserSettings() {
  const [config, setConfig] = useState<UserConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Company selector state
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('');
  const [companyConfig, setCompanyConfig] = useState<CompanyConfig | null>(null);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [userData, companiesData] = await Promise.all([
        getUserConfig(),
        getCompanies(),
      ]);
      setConfig(userData);
      setCompanies(companiesData);
      if (companiesData.length > 0) {
        setSelectedCompanyId(companiesData[0].id);
        // Load company config for first company
        try {
          const cc = await getCompanyConfig(companiesData[0].id);
          setCompanyConfig(cc);
        } catch {
          // Company config not available yet
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar configuracion');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // Load company config when selected company changes
  useEffect(() => {
    if (selectedCompanyId) {
      getCompanyConfig(selectedCompanyId)
        .then(cc => setCompanyConfig(cc))
        .catch(() => setCompanyConfig(null));
    }
  }, [selectedCompanyId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error al cargar</AlertTitle>
          <AlertDescription>
            {error || 'No se pudo cargar la configuracion del usuario.'}
          </AlertDescription>
        </Alert>
        <Button onClick={loadConfig} variant="outline">
          <Loader2 className="mr-2 h-4 w-4" />
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Image
          src="/logo.svg"
          alt="ContaEC"
          width={32}
          height={32}
          className="h-8 w-8"
          priority
        />
        <div>
          <h2 className="text-2xl font-bold">Configuracion</h2>
          <p className="text-muted-foreground">
            Administre su perfil, firma electronica, ambiente y seguridad
          </p>
        </div>
      </div>

      {/* Company Selector */}
      {companies.length > 1 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              Empresa Activa
            </CardTitle>
            <CardDescription>
              Seleccione la empresa para la cual desea configurar los ajustes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccione una empresa" />
              </SelectTrigger>
              <SelectContent>
                {companies.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.razon_social} ({c.ruc})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="profile" className="gap-1.5">
            <User className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Perfil</span>
          </TabsTrigger>
          <TabsTrigger value="signature" className="gap-1.5">
            <KeyRound className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Firma Electronica</span>
          </TabsTrigger>
          <TabsTrigger value="environment" className="gap-1.5">
            <Globe className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Ambiente</span>
          </TabsTrigger>
          <TabsTrigger value="smtp" className="gap-1.5">
            <Mail className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Correo</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1.5">
            <Shield className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Seguridad</span>
          </TabsTrigger>
          <TabsTrigger value="backups" className="gap-1.5">
            <Database className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Respaldos</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <ProfileTab config={config} onConfigUpdate={loadConfig} />
        </TabsContent>

        <TabsContent value="signature">
          <SignatureTab config={config} companyConfig={companyConfig} selectedCompanyId={selectedCompanyId} onConfigUpdate={loadConfig} />
        </TabsContent>

        <TabsContent value="environment">
          <EnvironmentTab config={config} companyConfig={companyConfig} selectedCompanyId={selectedCompanyId} onConfigUpdate={loadConfig} />
        </TabsContent>

        <TabsContent value="smtp">
          <SMTPTab config={config} companyConfig={companyConfig} selectedCompanyId={selectedCompanyId} onConfigUpdate={loadConfig} />
        </TabsContent>

        <TabsContent value="security">
          <SecurityTab config={config} companyConfig={companyConfig} selectedCompanyId={selectedCompanyId} onConfigUpdate={loadConfig} />
        </TabsContent>

        <TabsContent value="backups">
          <BackupsTab config={config} selectedCompanyId={selectedCompanyId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Profile Tab ────────────────────────────────────────────────
function ProfileTab({
  config,
  onConfigUpdate,
}: {
  config: UserConfig;
  onConfigUpdate: () => void;
}) {
  const { setTheme } = useTheme();
  const [fullName, setFullName] = useState(config.user.full_name);
  const [phone, setPhone] = useState(config.user.phone || '');
  const [language, setLanguage] = useState(config.user.language || 'es_EC');
  const [selectedTheme, setSelectedTheme] = useState(config.user.theme || 'system');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Logo upload
  const [uploadingLogo, setUploadingLogo] = useState(false);

  async function handleSaveProfile() {
    setSaving(true);
    setMessage(null);
    try {
      await updateProfile({
        full_name: fullName,
        phone: phone || undefined,
        language,
        theme: selectedTheme,
      });
      setTheme(selectedTheme);
      setMessage({ type: 'success', text: 'Perfil actualizado correctamente' });
      onConfigUpdate();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al actualizar perfil',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingLogo(true);
    try {
      await uploadCompanyLogo(file);
      toast.success('Logo actualizado correctamente');
      onConfigUpdate();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al subir logo');
    } finally {
      setUploadingLogo(false);
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>{message.type === 'success' ? 'Exito' : 'Error'}</AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <User className="h-4 w-4 text-primary" />
              Informacion Personal
            </CardTitle>
            <CardDescription>Actualice sus datos personales</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="profile-name">Nombre Completo</Label>
                <Input
                  id="profile-name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Juan Perez"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-phone">Telefono</Label>
                <Input
                  id="profile-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="0991234567"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-email">Correo Electronico</Label>
              <Input id="profile-email" value={config.user.email} disabled className="bg-muted" />
              <p className="text-xs text-muted-foreground">
                El correo no puede ser modificado. Contacte al administrador si necesita cambiarlo.
              </p>
            </div>

            <Separator />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="profile-language">Idioma</Label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="es_EC">Espanol (Ecuador)</SelectItem>
                    <SelectItem value="en_US">English (US)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-theme">Tema</Label>
                <Select
                  value={selectedTheme}
                  onValueChange={(val) => {
                    setSelectedTheme(val);
                    setTheme(val);
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Claro</SelectItem>
                    <SelectItem value="dark">Oscuro</SelectItem>
                    <SelectItem value="system">Sistema</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button onClick={handleSaveProfile} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  'Guardar Cambios'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Logo / Avatar Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Upload className="h-4 w-4 text-primary" />
              Logo de Empresa
            </CardTitle>
            <CardDescription>Logo que aparecera en sus comprobantes</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <div className="w-32 h-32 rounded-lg border-2 border-dashed flex items-center justify-center bg-muted/50">
              {config.company_logo_path ? (
                <Image
                  src={config.company_logo_path}
                  alt="Logo de empresa"
                  width={128}
                  height={128}
                  className="object-contain rounded-lg"
                />
              ) : (
                <Upload className="h-8 w-8 text-muted-foreground" />
              )}
            </div>
            <label htmlFor="logo-upload">
              <Button variant="outline" size="sm" asChild disabled={uploadingLogo}>
                <span>
                  {uploadingLogo ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Subiendo...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Subir Logo
                    </>
                  )}
                </span>
              </Button>
            </label>
            <input
              id="logo-upload"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleLogoUpload}
            />
            <p className="text-xs text-muted-foreground text-center">
              PNG, JPG o SVG. Maximo 2MB.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Digital Signature Tab ──────────────────────────────────────
function SignatureTab({
  config,
  companyConfig,
  selectedCompanyId,
  onConfigUpdate,
}: {
  config: UserConfig;
  companyConfig: CompanyConfig | null;
  selectedCompanyId: string;
  onConfigUpdate: () => void;
}) {
  const [sigFile, setSigFile] = useState<File | null>(null);
  const [sigPassword, setSigPassword] = useState('');
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<SignatureValidation | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  async function handleUpload() {
    if (!sigFile || !sigPassword) return;
    setUploading(true);
    setMessage(null);
    try {
      await uploadDigitalSignature(sigFile, sigPassword);
      // Also update company config if a company is selected
      if (selectedCompanyId) {
        try {
          await updateCompanyConfig(selectedCompanyId, { firma_electronica_path: 'pending' });
        } catch { /* ignore */ }
      }
      setMessage({ type: 'success', text: 'Firma electronica cargada correctamente' });
      setSigFile(null);
      setSigPassword('');
      onConfigUpdate();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al subir firma',
      });
    } finally {
      setUploading(false);
    }
  }

  async function handleValidate() {
    if (!sigFile || !sigPassword) return;
    setValidating(true);
    setMessage(null);
    try {
      const result = await validateSignature(sigFile, sigPassword);
      setValidation(result);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al validar firma',
      });
    } finally {
      setValidating(false);
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'valid':
        return (
          <Badge className="bg-emerald-600 hover:bg-emerald-700">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Valida
          </Badge>
        );
      case 'expired':
        return (
          <Badge variant="destructive">
            <XCircle className="mr-1 h-3 w-3" />
            Expirada
          </Badge>
        );
      case 'expiring_soon':
        return (
          <Badge className="bg-amber-500 hover:bg-amber-600">
            <Clock className="mr-1 h-3 w-3" />
            Por expirar
          </Badge>
        );
      case 'uploaded':
        return (
          <Badge className="bg-primary">
            <FileKey className="mr-1 h-3 w-3" />
            Cargada
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            <XCircle className="mr-1 h-3 w-3" />
            Sin firma
          </Badge>
        );
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>{message.type === 'success' ? 'Exito' : 'Error'}</AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Current Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-primary" />
            Estado de Firma Electronica
          </CardTitle>
          <CardDescription>Estado actual de su firma digital registrada</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {companyConfig?.firma_electronica_path && selectedCompanyId && (
            <div className="flex items-center gap-2 text-sm text-amber-600">
              <Building2 className="h-4 w-4" />
              <span className="font-medium">Usando firma de la empresa seleccionada</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Estado</span>
            {getStatusBadge(config.signature_status)}
          </div>

          {config.signature_expiry_date && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Fecha de Expiracion</span>
              <span className="text-sm font-medium">
                {new Date(config.signature_expiry_date).toLocaleDateString('es-EC', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </span>
            </div>
          )}

          {config.signature_days_left !== null && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Dias restantes</span>
              <span
                className={`text-sm font-medium ${
                  config.signature_days_left <= 30
                    ? config.signature_days_left <= 0
                      ? 'text-destructive'
                      : 'text-amber-500'
                    : 'text-emerald-600'
                }`}
              >
                {config.signature_days_left} dias
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Expiring Soon Warning */}
      {config.signature_status === 'expiring_soon' && (
        <Alert className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <AlertTitle className="text-amber-700 dark:text-amber-400">Firma por expirar</AlertTitle>
          <AlertDescription className="text-amber-600 dark:text-amber-400">
            Su firma electronica expira en {config.signature_days_left} dias. Renueve su firma con
            el Banco Central del Ecuador para evitar interrupciones en la emision de comprobantes.
          </AlertDescription>
        </Alert>
      )}

      {config.signature_status === 'expired' && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Firma expirada</AlertTitle>
          <AlertDescription>
            Su firma electronica ha expirado. No podra emitir comprobantes electronicos hasta que
            cargue una nueva firma valida.
          </AlertDescription>
        </Alert>
      )}

      {/* Upload New Signature */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="h-4 w-4 text-primary" />
            Cargar Nueva Firma
          </CardTitle>
          <CardDescription>
            Suba su archivo de firma electronica (.p12 o .pfx) con su contrasena
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="sig-file">Archivo de Firma (.p12 / .pfx)</Label>
            <Input
              id="sig-file"
              type="file"
              accept=".p12,.pfx"
              onChange={(e) => setSigFile(e.target.files?.[0] || null)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="sig-password">Contrasena de la Firma</Label>
            <div className="relative">
              <Input
                id="sig-password"
                type={showPassword ? 'text' : 'password'}
                value={sigPassword}
                onChange={(e) => setSigPassword(e.target.value)}
                placeholder="Ingrese la contrasena de la firma"
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={handleValidate}
              disabled={!sigFile || !sigPassword || validating}
            >
              {validating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Validando...
                </>
              ) : (
                <>
                  <TestTube className="mr-2 h-4 w-4" />
                  Validar Firma
                </>
              )}
            </Button>
            <Button onClick={handleUpload} disabled={!sigFile || !sigPassword || uploading}>
              {uploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Subiendo...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Subir y Guardar
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Validation Results */}
      {validation && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2
                className={`h-4 w-4 ${
                  validation.is_valid ? 'text-emerald-600' : 'text-destructive'
                }`}
              />
              Resultado de Validacion
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Valida</span>
                {validation.is_valid ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Expirada</span>
                {validation.is_expired ? (
                  <XCircle className="h-4 w-4 text-destructive" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                )}
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Firma EC</span>
                {validation.is_ec_signature ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                )}
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Clave Privada</span>
                {validation.has_private_key ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
              </div>
              {validation.days_until_expiry !== null && (
                <div className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="text-xs text-muted-foreground">Dias rest.</span>
                  <span
                    className={`text-xs font-medium ${
                      validation.days_until_expiry <= 30
                        ? validation.days_until_expiry <= 0
                          ? 'text-destructive'
                          : 'text-amber-500'
                        : 'text-emerald-600'
                    }`}
                  >
                    {validation.days_until_expiry}
                  </span>
                </div>
              )}
            </div>

            <Separator />

            {/* Subject & Issuer Info */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Sujeto</h4>
                <div className="space-y-1 text-xs">
                  {Object.entries(validation.subject).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-muted-foreground">{key}</span>
                      <span className="font-medium truncate ml-2">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Emisor</h4>
                <div className="space-y-1 text-xs">
                  {Object.entries(validation.issuer).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-muted-foreground">{key}</span>
                      <span className="font-medium truncate ml-2">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Numero de Serie</span>
                <span className="font-mono font-medium">{validation.serial_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Emisor (CN)</span>
                <span className="font-medium truncate ml-2">{validation.issuer_cn}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Valida Desde</span>
                <span className="font-medium">
                  {new Date(validation.not_before).toLocaleDateString('es-EC')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Valida Hasta</span>
                <span className="font-medium">
                  {new Date(validation.not_after).toLocaleDateString('es-EC')}
                </span>
              </div>
            </div>

            {/* Warnings */}
            {validation.warnings.length > 0 && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                    Advertencias
                  </h4>
                  <ul className="space-y-1">
                    {validation.warnings.map((w, i) => (
                      <li key={i} className="text-xs text-amber-600 dark:text-amber-400">
                        &bull; {w}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Environment Tab ────────────────────────────────────────────
function EnvironmentTab({
  config,
  companyConfig: _companyConfig,
  selectedCompanyId: _selectedCompanyId,
  onConfigUpdate,
}: {
  config: UserConfig;
  companyConfig: CompanyConfig | null;
  selectedCompanyId: string;
  onConfigUpdate: () => void;
}) {
  const [switching, setSwitching] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingMode, setPendingMode] = useState<'sandbox' | 'production' | null>(null);

  async function handleSwitchMode(mode: 'sandbox' | 'production') {
    if (mode === 'production' && config.signature_status !== 'valid') {
      setPendingMode(mode);
      setShowConfirmDialog(true);
      return;
    }
    await doSwitchMode(mode);
  }

  async function doSwitchMode(mode: 'sandbox' | 'production') {
    setSwitching(true);
    setMessage(null);
    setShowConfirmDialog(false);
    try {
      await switchEnvironmentMode(mode);
      setMessage({
        type: 'success',
        text: `Ambiente cambiado a ${mode === 'sandbox' ? 'Pruebas' : 'Produccion'} correctamente`,
      });
      onConfigUpdate();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al cambiar ambiente',
      });
    } finally {
      setSwitching(false);
      setPendingMode(null);
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>{message.type === 'success' ? 'Exito' : 'Error'}</AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Current Mode */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4 text-primary" />
            Modo de Ambiente Actual
          </CardTitle>
          <CardDescription>
            Ambiente en el que se emiten los comprobantes electronicos
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Modo Actual</span>
            <Badge
              className={
                config.environment_mode === 'production'
                  ? 'bg-emerald-600 hover:bg-emerald-700'
                  : 'bg-amber-500 hover:bg-amber-600'
              }
            >
              {config.environment_mode === 'sandbox' ? 'Pruebas' : 'Produccion'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Mode Selection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Sandbox Card */}
        <Card
          className={`cursor-pointer transition-all ${
            config.environment_mode === 'sandbox'
              ? 'ring-2 ring-amber-500 border-amber-500'
              : 'hover:border-amber-300'
          }`}
          onClick={() => handleSwitchMode('sandbox')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <TestTube className="h-4 w-4 text-amber-500" />
                Pruebas (Sandbox)
              </CardTitle>
              {config.environment_mode === 'sandbox' && (
                <Badge className="bg-amber-500">Activo</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Los comprobantes se envian al SRI de pruebas. No tienen validez fiscal.
            </p>
            <ul className="space-y-1.5 text-xs text-muted-foreground">
              <li className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-amber-500" />
                Ideal para desarrollo y pruebas
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-amber-500" />
                No requiere firma electronica
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-amber-500" />
                Sin impacto fiscal
              </li>
            </ul>
            <Button
              variant={config.environment_mode === 'sandbox' ? 'default' : 'outline'}
              size="sm"
              className="w-full"
              disabled={config.environment_mode === 'sandbox' || switching}
              onClick={(e) => {
                e.stopPropagation();
                handleSwitchMode('sandbox');
              }}
            >
              {switching ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Cambiar a Pruebas
            </Button>
          </CardContent>
        </Card>

        {/* Production Card */}
        <Card
          className={`cursor-pointer transition-all ${
            config.environment_mode === 'production'
              ? 'ring-2 ring-emerald-500 border-emerald-500'
              : 'hover:border-emerald-300'
          }`}
          onClick={() => handleSwitchMode('production')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="h-4 w-4 text-emerald-600" />
                Produccion
              </CardTitle>
              {config.environment_mode === 'production' && (
                <Badge className="bg-emerald-600">Activo</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Los comprobantes se envian al SRI de produccion. Tienen validez fiscal. Requiere firma
              electronica valida.
            </p>
            <ul className="space-y-1.5 text-xs text-muted-foreground">
              <li className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                Comprobantes con validez fiscal
              </li>
              <li className="flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3 text-amber-500" />
                Requiere firma electronica valida
              </li>
              <li className="flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3 text-amber-500" />
                No se pueden eliminar comprobantes
              </li>
            </ul>
            <Button
              variant={config.environment_mode === 'production' ? 'default' : 'outline'}
              size="sm"
              className="w-full"
              disabled={config.environment_mode === 'production' || switching}
              onClick={(e) => {
                e.stopPropagation();
                handleSwitchMode('production');
              }}
            >
              {switching ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Cambiar a Produccion
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Confirmation Dialog for switching to production without valid signature */}
      {showConfirmDialog && pendingMode === 'production' && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Sin firma electronica valida</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>
              No tiene una firma electronica valida registrada. Para operar en produccion, el SRI
              requiere una firma electronica valida. Los comprobantes emitidos sin firma seran
              rechazados.
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowConfirmDialog(false);
                  setPendingMode(null);
                }}
              >
                Cancelar
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => doSwitchMode('production')}
                disabled={switching}
              >
                {switching ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Cambiar de todos modos
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

// ─── SMTP Tab ───────────────────────────────────────────────────
function SMTPTab({
  config,
  companyConfig: _companyConfig,
  selectedCompanyId,
  onConfigUpdate,
}: {
  config: UserConfig;
  companyConfig: CompanyConfig | null;
  selectedCompanyId: string;
  onConfigUpdate: () => void;
}) {
  const [smtpHost, setSmtpHost] = useState(config.smtp_host || '');
  const [smtpPort, setSmtpPort] = useState(config.smtp_port?.toString() || '587');
  const [smtpUser, setSmtpUser] = useState(config.smtp_user || '');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [smtpProtocol, setSmtpProtocol] = useState(config.smtp_protocol || 'TLS');
  const [smtpSsl, setSmtpSsl] = useState(config.smtp_ssl);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  function applyPreset(preset: string) {
    const p = SMTP_PRESETS[preset];
    if (p) {
      setSmtpHost(p.host);
      setSmtpPort(p.port.toString());
      setSmtpProtocol(p.protocol);
      setSmtpSsl(p.ssl);
    }
  }

  async function handleSaveSMTP() {
    setSaving(true);
    setMessage(null);
    try {
      await configureSMTP({
        smtp_host: smtpHost,
        smtp_port: parseInt(smtpPort, 10),
        smtp_user: smtpUser,
        smtp_password: smtpPassword,
        smtp_protocol: smtpProtocol,
        smtp_ssl: smtpSsl,
      });
      setMessage({ type: 'success', text: 'Configuracion SMTP guardada correctamente' });
      onConfigUpdate();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al guardar configuracion SMTP',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleTestSMTP() {
    setTesting(true);
    setMessage(null);
    try {
      const result = await testSMTP(selectedCompanyId || undefined);
      if (result.success) {
        setMessage({ type: 'success', text: 'Prueba de correo exitosa. Revise su bandeja.' });
      } else {
        setMessage({ type: 'error', text: result.message || 'La prueba de correo fallo.' });
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al probar configuracion SMTP',
      });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>{message.type === 'success' ? 'Exito' : 'Error'}</AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Quick Presets */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Mail className="h-4 w-4 text-primary" />
            Proveedores Preconfigurados
          </CardTitle>
          <CardDescription>Seleccione un proveedor para configurar automaticamente</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.keys(SMTP_PRESETS).map((preset) => (
              <Button
                key={preset}
                variant="outline"
                size="sm"
                onClick={() => applyPreset(preset)}
                className="capitalize"
              >
                {preset === 'office365' ? 'Office 365' : preset.charAt(0).toUpperCase() + preset.slice(1)}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* SMTP Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4 text-primary" />
            Configuracion SMTP
          </CardTitle>
          <CardDescription>
            Configure el servidor de correo para el envio de comprobantes
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="smtp-host">Servidor SMTP</Label>
              <Input
                id="smtp-host"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="smtp-port">Puerto</Label>
              <Input
                id="smtp-port"
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(e.target.value)}
                placeholder="587"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="smtp-user">Usuario / Correo</Label>
              <Input
                id="smtp-user"
                value={smtpUser}
                onChange={(e) => setSmtpUser(e.target.value)}
                placeholder="miempresa@gmail.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="smtp-password">Contrasena</Label>
              <div className="relative">
                <Input
                  id="smtp-password"
                  type={showPassword ? 'text' : 'password'}
                  value={smtpPassword}
                  onChange={(e) => setSmtpPassword(e.target.value)}
                  placeholder="Contrasena o app password"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="smtp-protocol">Protocolo</Label>
              <Select value={smtpProtocol} onValueChange={setSmtpProtocol}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TLS">TLS</SelectItem>
                  <SelectItem value="SSL">SSL</SelectItem>
                  <SelectItem value="STARTTLS">STARTTLS</SelectItem>
                  <SelectItem value="NONE">Sin cifrado</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>SSL/TLS</Label>
              <div className="flex items-center gap-3 h-9">
                <Switch checked={smtpSsl} onCheckedChange={setSmtpSsl} />
                <span className="text-sm text-muted-foreground">
                  {smtpSsl ? 'Habilitado' : 'Deshabilitado'}
                </span>
              </div>
            </div>
          </div>

          <Separator />

          <div className="flex flex-wrap gap-2">
            <Button onClick={handleSaveSMTP} disabled={saving || !smtpHost}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Guardar Configuracion'
              )}
            </Button>
            <Button variant="outline" onClick={handleTestSMTP} disabled={testing || !smtpHost}>
              {testing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Probando...
                </>
              ) : (
                <>
                  <TestTube className="mr-2 h-4 w-4" />
                  Probar Configuracion
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Current SMTP Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Estado del Correo</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Configuracion SMTP</span>
            <Badge variant={config.has_smtp_config ? 'default' : 'secondary'}>
              {config.has_smtp_config ? 'Configurado' : 'No configurado'}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Backups Tab ─────────────────────────────────────────────────
function BackupsTab({ config, selectedCompanyId }: { config: UserConfig; selectedCompanyId: string }) {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [restoreConfirm, setRestoreConfirm] = useState<'server' | 'file' | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoreResult, setRestoreResult] = useState<RestoreBackupResponse | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadBackups = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getBackups();
      setBackups(data);
    } catch {
      toast.error('Error al cargar respaldos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBackups();
  }, [loadBackups]);

  async function handleCreateBackup() {
    if (!config.has_backup_key) {
      setMessage({ type: 'error', text: 'Debe configurar primero su clave de cifrado. Vaya a la pestaña Seguridad → Clave de Cifrado de Respaldos.' });
      return;
    }
    if (!selectedCompanyId) {
      setMessage({ type: 'error', text: 'Debe seleccionar una empresa primero.' });
      return;
    }
    setCreating(true);
    setMessage(null);
    try {
      const result = await createBackup();
      setMessage({ type: 'success', text: `Respaldo creado: ${result.filename}` });
      loadBackups();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al crear respaldo',
      });
    } finally {
      setCreating(false);
    }
  }

  async function handleDownload(filename: string) {
    setDownloading(filename);
    try {
      const blob = await downloadBackup(filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al descargar respaldo',
      });
    } finally {
      setDownloading(null);
    }
  }

  async function handleRestoreFromFile() {
    if (!restoreFile) return;
    setRestoring(true);
    setMessage(null);
    setRestoreResult(null);
    try {
      const result = await restoreBackup(restoreFile);
      setRestoreResult(result);
      setMessage({ type: 'success', text: result.message });
      setRestoreConfirm(null);
      setRestoreFile(null);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al restaurar respaldo',
      });
    } finally {
      setRestoring(false);
    }
  }

  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString('es-EC', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>{message.type === 'success' ? 'Exito' : 'Error'}</AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Restore Result */}
      {restoreResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              Resultado de Restauracion
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Version</span>
                <p className="font-medium">{restoreResult.backup_version}</p>
              </div>
              <div className="rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Fecha Respaldo</span>
                <p className="font-medium">{formatDate(restoreResult.backup_timestamp)}</p>
              </div>
              <div className="rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Empresas</span>
                <p className="font-medium">
                  {restoreResult.companies.created} creadas, {restoreResult.companies.updated} act., {restoreResult.companies.skipped} omit.
                </p>
              </div>
              <div className="rounded-md border px-3 py-2">
                <span className="text-xs text-muted-foreground">Clientes</span>
                <p className="font-medium">
                  {restoreResult.clients.created} creados, {restoreResult.clients.updated} act., {restoreResult.clients.skipped} omit.
                </p>
              </div>
              {restoreResult.products && (
                <div className="rounded-md border px-3 py-2">
                  <span className="text-xs text-muted-foreground">Productos</span>
                  <p className="font-medium">
                    {restoreResult.products.created} creados, {restoreResult.products.updated} act., {restoreResult.products.skipped} omit.
                  </p>
                </div>
              )}
            </div>
            <Button variant="outline" size="sm" onClick={() => setRestoreResult(null)}>
              Cerrar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-primary" />
              Crear Respaldo
            </CardTitle>
            <CardDescription>
              Genere un respaldo cifrado de todas sus empresas, clientes y configuracion
            </CardDescription>
          </CardHeader>
          <CardContent>
            {config.has_backup_key ? (
              <div className="flex items-center gap-2 text-sm text-emerald-600 mb-4 rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/20 px-3 py-2">
                <CheckCircle2 className="h-4 w-4" />
                <span className="font-medium">Clave de cifrado configurada ✓</span>
              </div>
            ) : (
              <Alert className="mb-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Clave de cifrado requerida</AlertTitle>
                <AlertDescription>
                  Configure una clave de cifrado en la pestana de Seguridad antes de crear respaldos.
                </AlertDescription>
              </Alert>
            )}
            <Button onClick={handleCreateBackup} disabled={creating} className="w-full">
              {creating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creando respaldo...
                </>
              ) : (
                <>
                  <Database className="mr-2 h-4 w-4" />
                  Crear Respaldo Ahora
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-primary" />
              Restaurar desde Archivo
            </CardTitle>
            <CardDescription>
              Restaure datos desde un archivo de respaldo .contaec previamente descargado
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="restore-file">Archivo de Respaldo (.contaec)</Label>
              <Input
                id="restore-file"
                type="file"
                accept=".contaec,.enc"
                onChange={(e) => setRestoreFile(e.target.files?.[0] || null)}
              />
            </div>
            <Button
              variant="outline"
              className="w-full"
              disabled={!restoreFile}
              onClick={() => setRestoreConfirm('file')}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Restaurar desde Archivo
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Backup List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                Respaldos Disponibles
              </CardTitle>
              <CardDescription>
                Lista de respaldos almacenados en el servidor
              </CardDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={loadBackups} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : backups.length > 0 ? (
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Archivo</TableHead>
                    <TableHead>Tamano</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {backups.map((backup) => (
                    <TableRow key={backup.filename}>
                      <TableCell className="font-mono text-xs max-w-[200px] truncate">
                        {backup.filename}
                      </TableCell>
                      <TableCell className="text-sm">{formatSize(backup.size_bytes)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(backup.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleDownload(backup.filename)}
                            disabled={downloading === backup.filename}
                          >
                            {downloading === backup.filename ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Download className="h-3.5 w-3.5" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-amber-600"
                            onClick={() => setRestoreConfirm('server')}
                            title="Restaurar este respaldo"
                          >
                            <RotateCcw className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          ) : (
            <div className="text-center py-8">
              <Database className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                No hay respaldos disponibles. Cree uno para comenzar.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Restore Confirmation Dialog */}
      <Dialog open={!!restoreConfirm} onOpenChange={(open) => { if (!open) setRestoreConfirm(null); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Confirmar Restauracion</DialogTitle>
            <DialogDescription>
              {restoreConfirm === 'file'
                ? 'Esta a punto de restaurar datos desde un archivo de respaldo. Los datos existentes se actualizaran o se crearan nuevos registros.'
                : 'Esta a punto de restaurar datos desde un respaldo del servidor. Los datos existentes se actualizaran o se crearan nuevos registros.'}
            </DialogDescription>
          </DialogHeader>
          <Alert variant="destructive" className="my-2">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Precaucion</AlertTitle>
            <AlertDescription>
              La restauracion modificara sus datos actuales. Se recomienda crear un respaldo antes de restaurar.
            </AlertDescription>
          </Alert>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRestoreConfirm(null)}>
              Cancelar
            </Button>
            <Button
              onClick={handleRestoreFromFile}
              disabled={restoring || (restoreConfirm === 'file' && !restoreFile)}
            >
              {restoring ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Restaurando...
                </>
              ) : (
                <>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Restaurar
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Security Tab ───────────────────────────────────────────────
function SecurityTab({
  config,
  companyConfig: _companyConfig,
  selectedCompanyId: _selectedCompanyId,
  onConfigUpdate,
}: {
  config: UserConfig;
  companyConfig: CompanyConfig | null;
  selectedCompanyId: string;
  onConfigUpdate: () => void;
}) {
  const [vtEnabled, setVtEnabled] = useState(config.virustotal_enabled);
  const [vtToggling, setVtToggling] = useState(false);
  const [clamavAvailable, setClamavAvailable] = useState(config.clamav_available);
  const [virustotalAvailable] = useState(config.virustotal_available);
  const [recheckingClamav, setRecheckingClamav] = useState(false);
  const [backupKey, setBackupKey] = useState('');
  const [backupKeyConfirm, setBackupKeyConfirm] = useState('');
  const [savingKey, setSavingKey] = useState(false);
  const [showBackupKey, setShowBackupKey] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Password change state
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [changingPw, setChangingPw] = useState(false);

  async function handleChangePassword() {
    if (newPw !== confirmPw) {
      setMessage({ type: 'error', text: 'Las contraseñas nuevas no coinciden' });
      return;
    }
    if (newPw.length < 8) {
      setMessage({ type: 'error', text: 'La nueva contraseña debe tener al menos 8 caracteres' });
      return;
    }
    setChangingPw(true);
    setMessage(null);
    try {
      await changePassword(currentPw, newPw);
      setMessage({ type: 'success', text: 'Contraseña actualizada correctamente. Use la nueva contraseña en su proximo inicio de sesion.' });
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al cambiar contraseña',
      });
    } finally {
      setChangingPw(false);
    }
  }

  async function handleToggleVirusTotal(enabled: boolean) {
    setVtToggling(true);
    try {
      await toggleVirusTotal(enabled);
      setVtEnabled(enabled);
      setMessage({
        type: 'success',
        text: `VirusTotal ${enabled ? 'habilitado' : 'deshabilitado'} correctamente`,
      });
      onConfigUpdate();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al cambiar VirusTotal',
      });
    } finally {
      setVtToggling(false);
    }
  }

  async function handleRecheckClamav() {
    setRecheckingClamav(true);
    try {
      const status = await getClamavStatus(true);
      setClamavAvailable(status.clamav_available);
    } catch {
      // ignore
    } finally {
      setRecheckingClamav(false);
    }
  }

  async function handleSaveBackupKey() {
    if (backupKey !== backupKeyConfirm) {
      setMessage({ type: 'error', text: 'Las claves no coinciden' });
      return;
    }
    if (backupKey.length < 8) {
      setMessage({ type: 'error', text: 'La clave debe tener al menos 8 caracteres' });
      return;
    }
    setSavingKey(true);
    setMessage(null);
    try {
      await setBackupKey(backupKey);
      setMessage({ type: 'success', text: 'Clave de cifrado configurada correctamente' });
      setBackupKey('');
      setBackupKeyConfirm('');
      onConfigUpdate();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al configurar clave de cifrado',
      });
    } finally {
      setSavingKey(false);
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>{message.type === 'success' ? 'Exito' : 'Error'}</AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Antivirus Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Bug className="h-4 w-4 text-primary" />
            Analisis de Virus
          </CardTitle>
          <CardDescription>
            Estado de los motores de analisis de archivos del sistema
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm">ClamAV (Antivirus Local)</span>
              <Badge variant="outline" className="text-xs">
                Local
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={clamavAvailable ? 'default' : 'secondary'}>
                {clamavAvailable ? (
                  <>
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Disponible
                  </>
                ) : (
                  <>
                    <XCircle className="mr-1 h-3 w-3" />
                    No disponible
                  </>
                )}
              </Badge>
              <Button variant="ghost" size="sm" onClick={handleRecheckClamav} disabled={recheckingClamav}>
                {recheckingClamav ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
              </Button>
            </div>
          </div>
          {!clamavAvailable && (
            <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
              <p className="font-medium mb-1">Para instalar ClamAV en el servidor:</p>
              <code className="bg-background px-1 py-0.5 rounded">sudo apt install clamav-daemon &amp;&amp; sudo systemctl enable --now clamav-daemon</code>
            </div>
          )}

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm">VirusTotal</span>
                <Badge variant="outline" className="text-xs">
                  Nube
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Analisis de archivos en la nube con VirusTotal
              </p>
            </div>
            <div className="flex items-center gap-3">
              {virustotalAvailable ? (
                <>
                  <Badge variant={vtEnabled ? 'default' : 'secondary'} className="mr-2">
                    {vtEnabled ? 'Habilitado' : 'Deshabilitado'}
                  </Badge>
                  <Switch
                    checked={vtEnabled}
                    onCheckedChange={handleToggleVirusTotal}
                    disabled={vtToggling}
                  />
                </>
              ) : (
                <Badge variant="secondary">
                  <XCircle className="mr-1 h-3 w-3" />
                  No disponible
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backup Encryption Key */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary" />
            Clave de Cifrado de Respaldos
          </CardTitle>
          <CardDescription>
            Configure una clave para cifrar sus respaldos. Esta clave sera necesaria para restaurar
            los respaldos.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {config.has_backup_key && !backupKey ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-emerald-600">
                <CheckCircle2 className="h-4 w-4" />
                <span className="font-medium">Clave de cifrado configurada</span>
              </div>
              <Button variant="outline" size="sm" onClick={() => setBackupKey(' ')}>
                <Lock className="mr-2 h-4 w-4" />
                Cambiar Clave
              </Button>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="backup-key">Clave de Cifrado</Label>
                <div className="relative">
                  <Input
                    id="backup-key"
                    type={showBackupKey ? 'text' : 'password'}
                    value={backupKey}
                    onChange={(e) => setBackupKey(e.target.value)}
                    placeholder="Minimo 8 caracteres"
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowBackupKey(!showBackupKey)}
                  >
                    {showBackupKey ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="backup-key-confirm">Confirmar Clave</Label>
                <Input
                  id="backup-key-confirm"
                  type={showBackupKey ? 'text' : 'password'}
                  value={backupKeyConfirm}
                  onChange={(e) => setBackupKeyConfirm(e.target.value)}
                  placeholder="Repita la clave"
                />
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleSaveBackupKey}
                  disabled={savingKey || !backupKey || !backupKeyConfirm}
                >
                  {savingKey ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Lock className="mr-2 h-4 w-4" />
                      {config.has_backup_key ? 'Actualizar Clave' : 'Configurar Clave'}
                    </>
                  )}
                </Button>
                {config.has_backup_key && backupKey && (
                  <Button variant="outline" onClick={() => { setBackupKey(''); setBackupKeyConfirm(''); }}>
                    Cancelar
                  </Button>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Password Change */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-primary" />
            Cambiar Contrasena
          </CardTitle>
          <CardDescription>Cambie su contrasena de acceso al sistema</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password">Contrasena Actual</Label>
            <Input id="current-password" type="password" placeholder="Contrasena actual" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-password">Nueva Contrasena</Label>
            <Input id="new-password" type="password" placeholder="Minimo 8 caracteres" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirmar Nueva Contrasena</Label>
            <Input id="confirm-password" type="password" placeholder="Repita la nueva contrasena" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} />
          </div>
          <Button onClick={handleChangePassword} disabled={changingPw || !currentPw || !newPw || !confirmPw}>
            {changingPw ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Cambiando...
              </>
            ) : (
              <>
                <KeyRound className="mr-2 h-4 w-4" />
                Cambiar Contrasena
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
