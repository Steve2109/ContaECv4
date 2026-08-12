'use client';

import Image from 'next/image';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  BookOpen,
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  LayoutDashboard,
  Key,
  LogOut,
  Menu,
  Moon,
  Plus,
  Shield,
  ShieldAlert,
  Sun,
  User,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  DollarSign,
  Receipt,
  Server,
  Users,
  Briefcase,
  Loader2,
  Trash2,
  Pencil,
  Wrench,
  Package,
  Truck,
  ShoppingCart,
  ScrollText,
  Globe,
  Warehouse as WarehouseIcon,
  Monitor,
  PieChart,
  Kanban,
  Plug,
  Brain,
  Activity,
  Scale,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { toast } from 'sonner';
import { getCurrentLocale, setCurrentLocale, getLocaleLabel, LOCALES, t, type Locale } from '@/lib/i18n';
import { useLicense, FEATURE_LABELS } from '@/hooks/useLicense';
import { ContaECSettings } from '@/components/contaec-settings';
import { ContaECInvoices } from '@/components/contaec-invoices';
import { ContaECInventory } from '@/components/contaec-inventory';
import { ContaECHR } from '@/components/contaec-hr';
import { ContaECSuppliers } from '@/components/contaec-suppliers';
import { ContaECPurchases } from '@/components/contaec-purchases';
import { ContaECAudit } from '@/components/contaec-audit';
import { ContaECWarehouses } from '@/components/contaec-warehouses';
import { ContaECPOS } from '@/components/contaec-pos';
import { ContaECBudgets } from '@/components/contaec-budgets';
import { ContaECCRM } from '@/components/contaec-crm';
import { ContaECProjects } from '@/components/contaec-projects';
import { ContaECIntegrations } from '@/components/contaec-integrations';
import { ContaECMLAI } from '@/components/contaec-ml-ai';
import { ContaECAccounting } from '@/components/contaec-accounting';
import { LOPDPolicy, TermsPolicy, RefundPolicy } from '@/components/policies';
import {
  logout,
  clearTokens,
  getLicenseStatus,
  getLicenseOptions,
  getCompanies,
  createCompany,
  uploadCompanyFile,
  validateSignature,
  updateCompany,
  deleteCompany,
  lookupRuc,
  getSRIIVARates,
  getSRIDocumentTypes,
  getSRITipoIdentificacion,
  getInvoiceStats,
  type User as UserType,
  type LicenseStatus as LicenseStatusType,
  type LicenseOptions as LicenseOptionsType,
  type Company as CompanyType,
  type SRIIVARate,
  type SRIDocumentType,
  type SRICatalog,
  type InvoiceStats as InvoiceStatsType,
} from '@/lib/api';

interface ContaECDashboardProps {
  user: UserType;
  onLogout: () => void;
}

type NavItem = 'dashboard' | 'companies' | 'sri' | 'license' | 'invoices' | 'proformas' | 'products' | 'inventory' | 'warehouses' | 'pos' | 'hr' | 'suppliers' | 'purchases' | 'budgets' | 'crm' | 'projects' | 'integrations' | 'mlai' | 'accounting' | 'audit' | 'settings' | 'policies' | 'admin-overview' | 'admin-users' | 'admin-system' | 'admin-licenses' | 'admin-security';

export function ContaECDashboard({ user, onLogout }: ContaECDashboardProps) {
  const { theme, setTheme } = useTheme();
  const { license, checkLimit, showUpgradePrompt, hasFeature } = useLicense();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // Los administradores deben aterrizar en el resumen del panel admin (no en 'dashboard',
  // que no existe en su navegación y provocaba una ventana en blanco al iniciar sesión).
  const [activeNav, setActiveNav] = useState<NavItem>(user.is_admin ? 'admin-overview' : 'dashboard');
  const [licenseData, setLicense] = useState<LicenseStatusType | null>(null);
  const [companies, setCompanies] = useState<CompanyType[]>([]);
  const selectedCompanyId = companies.length > 0 ? companies[0].id : undefined;
  const [invoiceStats, setInvoiceStats] = useState<InvoiceStatsType | null>(null);
  const [ivaRates, setIvaRates] = useState<SRIIVARate[]>([]);
  const [documentTypes, setDocumentTypes] = useState<SRIDocumentType[]>([]);
  const [identTypes, setIdentTypes] = useState<SRICatalog[]>([]);
  const [loading, setLoading] = useState(true);
  const [licenseExpiring, setLicenseExpiring] = useState(false);
  const [locale, setLocale] = useState<Locale>(getCurrentLocale);

  // New company dialog
  const [showNewCompany, setShowNewCompany] = useState(false);
  const [newCompany, setNewCompany] = useState({
    ruc: '',
    razon_social: '',
    nombre_comercial: '',
    correo: '',
    telefono: '',
    dir_matriz: '',
    cod_establecimiento: '001',
    cod_punto_emision: '001',
    obligado_contabilidad: 'NO',
    contribuyente_especial: '',
    contribuyente_rimpe: '',
    agente_retencion: '',
    firma_electronica_password: '',
    registro_turistico: false,
    operadora_transportista_comercial: false,
    operadora_transportista_ligera: false,
    ruc_operadora_comercial: '',
    ruc_operadora_transportista: '',
    codigo_artesano: '',
    nombre_recibos: '',
  });
  const logoInputRef = useRef<HTMLInputElement>(null);
  const firmaInputRef = useRef<HTMLInputElement>(null);
  const [creatingCompany, setCreatingCompany] = useState(false);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        getLicenseStatus(),
        getCompanies(),
        getSRIIVARates(),
        getSRIDocumentTypes(),
        getSRITipoIdentificacion(),
        getInvoiceStats(),
      ]);

      // Detect session expiry: if ALL API calls are rejected, session is invalid
      const allRejected = results.every(r => r.status === 'rejected');
      if (allRejected) {
        clearTokens();
        onLogout();
        toast.error(t('common.session_expired'));
        return;
      }

      if (results[0].status === 'fulfilled') {
        const lic = results[0].value;
        setLicense(lic);
        // Check if license expires within 30 days
        if (lic.days_remaining !== null) {
          setLicenseExpiring(lic.days_remaining <= 30 && lic.days_remaining > 0);
        }
      }
      if (results[1].status === 'fulfilled' && Array.isArray(results[1].value)) setCompanies(results[1].value);
      if (results[2].status === 'fulfilled' && Array.isArray(results[2].value)) setIvaRates(results[2].value);
      if (results[3].status === 'fulfilled' && Array.isArray(results[3].value)) setDocumentTypes(results[3].value);
      if (results[4].status === 'fulfilled' && Array.isArray(results[4].value)) setIdentTypes(results[4].value);
      if (results[5].status === 'fulfilled') setInvoiceStats(results[5].value);
    } catch {
      toast.error(t('dash.load_error'));
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  async function handleCreateCompany() {
    // Verificar límite de empresas según el plan
    const limitResult = await checkLimit('companies');
    if (limitResult.isAtLimit) {
      showUpgradePrompt('companies');
      return;
    }

    setCreatingCompany(true);
    try {
      let logoPath: string | undefined;
      let firmaPath: string | undefined;

      // Upload logo if selected
      const logoFile = logoInputRef.current?.files?.[0];
      if (logoFile) {
        try {
          const logoResult = await uploadCompanyFile('logo', logoFile);
          logoPath = logoResult.file_path;
        } catch {
          toast.warning(t('company.upload_logo_error'));
        }
      }

      // La firma electrónica y su contraseña son OBLIGATORIAS para crear la empresa
      const firmaFile = firmaInputRef.current?.files?.[0];
      if (!firmaFile) {
        toast.error(t('company.signature_required'));
        setCreatingCompany(false);
        return;
      }
      if (!newCompany.firma_electronica_password) {
        toast.error(t('company.signature_pass_required'));
        setCreatingCompany(false);
        return;
      }

      // Validar que la contraseña corresponde a la firma electrónica (.p12)
      try {
        const firmaValidation = await validateSignature(firmaFile, newCompany.firma_electronica_password);
        if (!firmaValidation.is_valid) {
          const warning = firmaValidation.warnings?.[0];
          toast.error(warning || t('company.signature_invalid'));
          setCreatingCompany(false);
          return;
        }
      } catch (err) {
        toast.error(err instanceof Error ? err.message : t('company.signature_invalid'));
        setCreatingCompany(false);
        return;
      }

      // Subir la firma electrónica
      try {
        const firmaResult = await uploadCompanyFile('firma', firmaFile);
        firmaPath = firmaResult.file_path;
      } catch {
        toast.error(t('company.upload_signature_error'));
        setCreatingCompany(false);
        return;
      }

      // Build company data with file paths
      const companyData = {
        ...newCompany,
        logo_path: logoPath || null,
        firma_electronica_path: firmaPath || null,
        // Clean empty strings to optional fields
        contribuyente_especial: newCompany.contribuyente_especial || null,
        agente_retencion: newCompany.agente_retencion || null,
        ruc_operadora_comercial: newCompany.ruc_operadora_comercial || null,
        ruc_operadora_transportista: newCompany.ruc_operadora_transportista || null,
        codigo_artesano: newCompany.codigo_artesano || null,
        nombre_recibos: newCompany.nombre_recibos || null,
        correo: newCompany.correo || null,
        telefono: newCompany.telefono || null,
      };

      const company = await createCompany(companyData);
      setCompanies((prev) => [...prev, company]);
      setShowNewCompany(false);
      setNewCompany({
        ruc: '',
        razon_social: '',
        nombre_comercial: '',
        correo: '',
        telefono: '',
        dir_matriz: '',
        cod_establecimiento: '001',
        cod_punto_emision: '001',
        obligado_contabilidad: 'NO',
        contribuyente_especial: '',
        contribuyente_rimpe: '',
        agente_retencion: '',
        firma_electronica_password: '',
        registro_turistico: false,
        operadora_transportista_comercial: false,
        operadora_transportista_ligera: false,
        ruc_operadora_comercial: '',
        ruc_operadora_transportista: '',
        codigo_artesano: '',
        nombre_recibos: '',
      });
      // Reset file inputs
      if (logoInputRef.current) logoInputRef.current.value = '';
      if (firmaInputRef.current) firmaInputRef.current.value = '';
      toast.success(t('company.created'));
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('company.create_error');
      toast.error(msg);
    } finally {
      setCreatingCompany(false);
    }
  }

  function handleLogout() {
    logout();
    onLogout();
  }

  const userNavItems: { id: NavItem; label: string; icon: React.ReactNode; locked?: boolean; requiredTier?: string }[] = [
    { id: 'dashboard', label: t('nav.dashboard'), icon: <LayoutDashboard className="h-4 w-4" /> },
    { id: 'companies', label: t('nav.companies'), icon: <Building2 className="h-4 w-4" /> },
    { id: 'sri', label: t('nav.sri'), icon: <Shield className="h-4 w-4" /> },
    { id: 'license', label: t('nav.license'), icon: <FileText className="h-4 w-4" /> },
    { id: 'invoices', label: t('nav.invoices'), icon: <Receipt className="h-4 w-4" /> },
    { id: 'proformas', label: t('nav.proformas'), icon: <FileText className="h-4 w-4" /> },
    { id: 'products', label: t('nav.products'), icon: <Package className="h-4 w-4" /> },
    { id: 'inventory', label: t('nav.inventory'), icon: <Database className="h-4 w-4" /> },
    { id: 'warehouses', label: t('nav.warehouses'), icon: <WarehouseIcon className="h-4 w-4" />, locked: true, requiredTier: 'semiannual' },
    { id: 'pos', label: t('nav.pos'), icon: <Monitor className="h-4 w-4" />, locked: true, requiredTier: 'quarterly' },
    { id: 'hr', label: t('nav.hr'), icon: <Users className="h-4 w-4" />, locked: true, requiredTier: 'quarterly' },
    { id: 'suppliers', label: t('nav.suppliers'), icon: <Truck className="h-4 w-4" /> },
    { id: 'purchases', label: t('nav.purchases'), icon: <ShoppingCart className="h-4 w-4" /> },
    { id: 'budgets', label: t('nav.budgets'), icon: <PieChart className="h-4 w-4" />, locked: true, requiredTier: 'semiannual' },
    { id: 'crm', label: t('nav.crm'), icon: <Kanban className="h-4 w-4" />, locked: true, requiredTier: 'semiannual' },
    { id: 'projects', label: t('nav.projects'), icon: <Briefcase className="h-4 w-4" />, locked: true, requiredTier: 'semiannual' },
    { id: 'integrations', label: t('nav.integrations'), icon: <Plug className="h-4 w-4" />, locked: true, requiredTier: 'semiannual' },
    { id: 'mlai', label: t('nav.ai'), icon: <Brain className="h-4 w-4" />, locked: true, requiredTier: 'semiannual' },
    { id: 'accounting', label: t('nav.accounting'), icon: <BookOpen className="h-4 w-4" /> },
    { id: 'audit', label: t('nav.audit'), icon: <ScrollText className="h-4 w-4" /> },
    { id: 'settings', label: t('nav.settings'), icon: <Wrench className="h-4 w-4" /> },
    { id: 'policies', label: t('nav.policies'), icon: <Scale className="h-4 w-4" /> },
  ];

  // Filtrar items según el plan del usuario
  const currentTier = license?.license_type;
  // Durante el período de prueba ACTIVO hay acceso completo a todas las funcionalidades.
  // Se usa trial_active (basado en fechas) y no is_trial (flag permanente) para que el
  // acceso premium se restrinja automáticamente cuando la prueba expire.
  const isTrialActive = !!(license?.trial_active || licenseData?.trial_active);
  const filteredNavItems: { id: NavItem; label: string; icon: React.ReactNode; locked?: boolean; requiredTier?: string }[] = userNavItems
    .filter(item => {
      if (!item.locked) return true;
      if (!item.requiredTier) return true;

      if (isTrialActive) return true;

      // Plan Anual - todo disponible
      if (currentTier === 'annual') return true;

      // Plan Semestral - semiannual y menores
      if (currentTier === 'semiannual') {
        return ['semiannual', 'quarterly'].includes(item.requiredTier);
      }

      // Plan Trimestral - solo quarterly
      if (currentTier === 'quarterly') {
        return item.requiredTier === 'quarterly';
      }

      // Plan Mensual - nada de features premium
      if (currentTier === 'monthly') {
        return false;
      }

      return true;
    })
    // En prueba activa los items premium se muestran sin candado ni bloqueo
    .map(item => (isTrialActive && item.locked ? { ...item, locked: false } : item));

  const adminNavItems: { id: NavItem; label: string; icon: React.ReactNode; locked?: boolean; requiredTier?: string }[] = [
    { id: 'admin-overview', label: t('admin.overview'), icon: <Activity className="h-4 w-4" /> },
    { id: 'admin-users', label: t('admin.users'), icon: <Users className="h-4 w-4" /> },
    { id: 'admin-system', label: t('admin.system'), icon: <Server className="h-4 w-4" /> },
    { id: 'admin-licenses', label: t('nav.licenses'), icon: <Key className="h-4 w-4" /> },
    { id: 'admin-security', label: t('admin.security'), icon: <ShieldAlert className="h-4 w-4" /> },
    { id: 'policies', label: t('nav.policies'), icon: <Scale className="h-4 w-4" /> },
  ];

  // Admin users see admin tabs, regular users see filtered nav items
  const navItems = user.is_admin ? adminNavItems : filteredNavItems;

  // Feature mapping for access control
  const featureMap: Record<string, keyof typeof FEATURE_LABELS> = {
    pos: 'pos',
    hr: 'payroll',
    warehouses: 'multi_warehouse',
    budgets: 'budgets',
    crm: 'crm',
    projects: 'projects',
    integrations: 'ecommerce_integration',
    mlai: 'ml_predictions',
  } as const;

  // Check if current view requires feature access
  const currentFeature = activeNav in featureMap ? featureMap[activeNav] : null;
  const canAccessCurrentView = !currentFeature || hasFeature(currentFeature);

  // Render locked screen
  const renderLockedView = (featureName: keyof typeof FEATURE_LABELS) => (
    <div className="flex flex-col items-center justify-center p-12 text-center space-y-4">
      <div className="text-6xl mb-2">🔒</div>
      <h3 className="text-xl font-bold">{FEATURE_LABELS[featureName]} {t('locked.not_available')}</h3>
      <p className="text-muted-foreground max-w-md">
        {t('locked.not_included')}
        {license?.license_type && `(${t('locked.plan')} ${t(license.license_type === 'monthly' ? 'license.plan_monthly' : license.license_type === 'quarterly' ? 'license.plan_quarterly' : license.license_type === 'semiannual' ? 'license.plan_semiannual' : 'license.plan_annual')})`}.
      </p>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setActiveNav('license')}>
          {t('locked.view_plans')}
        </Button>
        <Button onClick={() => {
          const msg = `${t('locked.whatsapp_msg')} ${FEATURE_LABELS[featureName]}. ${t('locked.my_email')}: ${user.email}`;
          window.open(`https://wa.me/593960068866?text=${encodeURIComponent(msg)}`, '_blank');
        }}>
          {t('locked.whatsapp')}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="h-screen overflow-hidden flex bg-background">
      {/* Sidebar: scroll independiente del contenido central */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-16'
        } border-r bg-card transition-all duration-300 flex flex-col shrink-0 overflow-hidden`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-1.5 shrink-0">
            <Image
              src="/logo.svg"
              alt="ContaEC"
              width={32}
              height={32}
              className="h-8 w-8"
              priority
            />
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden">
              <h2 className="font-bold text-sm leading-tight">ContaEC</h2>
              <p className="text-[10px] text-muted-foreground truncate">{t('shell.tagline')}</p>
            </div>
          )}
        </div>

        {/* Nav Items (scroll independiente) */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                if (item.locked && !user.is_admin) {
                  const featureMap: Record<string, keyof typeof FEATURE_LABELS> = {
                    pos: 'pos',
                    hr: 'payroll',
                    warehouses: 'multi_warehouse',
                    budgets: 'budgets',
                    crm: 'crm',
                    projects: 'projects',
                    integrations: 'ecommerce_integration',
                    mlai: 'ml_predictions',
                  } as const;
                  const feature = featureMap[item.id];
                  if (feature) {
                    showUpgradePrompt(feature as keyof typeof FEATURE_LABELS);
                    return;
                  }
                }
                setActiveNav(item.id);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                activeNav === item.id
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              } ${item.locked ? 'opacity-60' : ''}`}
            >
              {item.locked && sidebarOpen && (
                <span className="text-xs">🔒</span>
              )}
              {item.icon}
              {sidebarOpen && <span>{item.label}{item.locked && ` (${t('locked.premium')})`}</span>}
            </button>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-2 border-t">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            {sidebarOpen ? (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span>{t('shell.collapse')}</span>
              </>
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-14 border-b bg-card flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="sm:hidden"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-lg font-semibold hidden sm:block">
              {navItems.find((n) => n.id === activeNav)?.label || t('nav.dashboard')}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" title={t('shell.language')}>
                  <Globe className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {LOCALES.map((l) => (
                  <DropdownMenuItem
                    key={l}
                    className={locale === l ? 'bg-accent' : ''}
                    onClick={() => { setLocale(l); setCurrentLocale(l); }}
                  >
                    {getLocaleLabel(l)}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2">
                  <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-4 w-4 text-primary" />
                  </div>
                  <span className="text-sm hidden sm:inline">{user.full_name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled>
                  <User className="mr-2 h-4 w-4" />
                  {user.email}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  {t('shell.logout')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : activeNav === 'policies' ? (
            <PoliciesView />
          ) : user.is_admin ? (
            <AdminDashboardView onLogout={onLogout} activeAdminTab={activeNav} />
          ) : (
            <>
              {activeNav === 'dashboard' && (
                <DashboardView
                  user={user}
                  license={licenseData}
                  licenseExpiring={licenseExpiring}
                  companies={companies}
                  invoiceStats={invoiceStats}
                  ivaRates={ivaRates}
                  documentTypes={documentTypes}
                />
              )}
              {activeNav === 'companies' && (
                <CompaniesView
                  companies={companies}
                  onNewCompany={() => setShowNewCompany(true)}
                  onCompaniesChanged={loadDashboardData}
                />
              )}
              {activeNav === 'sri' && (
                <SRIView
                  ivaRates={ivaRates}
                  documentTypes={documentTypes}
                  identTypes={identTypes}
                />
              )}
              {activeNav === 'license' && (
                <LicenseView license={licenseData} licenseExpiring={licenseExpiring} user={user} />
              )}
              {activeNav === 'invoices' && (
                <ContaECInvoices user={user} companies={companies} />
              )}
              {activeNav === 'proformas' && (
                <ContaECInvoices user={user} companies={companies} initialTab="proformas" />
              )}
              {activeNav === 'products' && (
                <ContaECInvoices user={user} companies={companies} initialTab="productos" />
              )}
              {activeNav === 'inventory' && (
                <ContaECInventory user={user} companies={companies} />
              )}
              {activeNav === 'warehouses' && (
                canAccessCurrentView ? <ContaECWarehouses user={user} companies={companies} /> : renderLockedView('multi_warehouse')
              )}
              {activeNav === 'pos' && (
                canAccessCurrentView ? <ContaECPOS user={user} companies={companies} /> : renderLockedView('pos')
              )}
              {activeNav === 'hr' && (
                canAccessCurrentView ? <ContaECHR user={user} companies={companies} /> : renderLockedView('payroll')
              )}
              {activeNav === 'suppliers' && (
                <ContaECSuppliers user={user} companies={companies} />
              )}
              {activeNav === 'purchases' && (
                <ContaECPurchases user={user} companies={companies} />
              )}
              {activeNav === 'budgets' && (
                canAccessCurrentView ? <ContaECBudgets user={user} companies={companies} /> : renderLockedView('budgets')
              )}
              {activeNav === 'crm' && (
                canAccessCurrentView ? <ContaECCRM user={user} companies={companies} /> : renderLockedView('crm')
              )}
              {activeNav === 'projects' && (
                canAccessCurrentView ? <ContaECProjects user={user} companies={companies} /> : renderLockedView('projects')
              )}
              {activeNav === 'integrations' && (
                canAccessCurrentView ? <ContaECIntegrations user={user} companies={companies} /> : renderLockedView('ecommerce_integration')
              )}
              {activeNav === 'mlai' && (
                canAccessCurrentView ? <ContaECMLAI user={user} companies={companies} /> : renderLockedView('ml_predictions')
              )}
              {activeNav === 'accounting' && selectedCompanyId && (
                <ContaECAccounting companyId={selectedCompanyId} />
              )}
              {activeNav === 'audit' && (
                <ContaECAudit />
              )}
              {activeNav === 'settings' && (
                <ContaECSettings user={user} />
              )}
            </>
          )}
        </main>

        {/* Sticky Footer */}
        <footer className="border-t bg-card py-3 px-4 text-center shrink-0">
          <p className="text-xs text-muted-foreground">
            {t('shell.developed_by')} <span className="font-semibold text-foreground">T&amp;M Technology Ec</span>
            &nbsp;&mdash;&nbsp; info@tymtechnology.shop &nbsp;|&nbsp; 0960068866
          </p>
        </footer>
      </div>

      {/* New Company Dialog */}
      <Dialog open={showNewCompany} onOpenChange={setShowNewCompany}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('company.new_title')}</DialogTitle>
            <DialogDescription>
              {t('company.new_desc')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-2">
            {/* Seccion: Informacion Fiscal */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">{t('company.fiscal_info')}</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-2">
                    <Label htmlFor="nc-ruc">RUC <span className="text-red-500">*</span></Label>
                    <div className="flex gap-2">
                      <Input
                        id="nc-ruc"
                        placeholder="1790000000001"
                        value={newCompany.ruc}
                        onChange={(e) => setNewCompany({ ...newCompany, ruc: e.target.value.replace(/\D/g, '').slice(0, 13) })}
                        maxLength={13}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={newCompany.ruc.length !== 13}
                        onClick={async () => {
                          if (newCompany.ruc.length !== 13) return;
                          try {
                            const data = await lookupRuc(newCompany.ruc);
                            if (data.razon_social) {
                              setNewCompany((prev) => ({
                                ...prev,
                                razon_social: data.razon_social || prev.razon_social,
                                nombre_comercial: data.nombre_comercial || prev.nombre_comercial,
                                dir_matriz: data.dir_matriz || prev.dir_matriz,
                                obligado_contabilidad: data.obligado_contabilidad || prev.obligado_contabilidad,
                                contribuyente_especial: data.contribuyente_especial || prev.contribuyente_especial,
                              }));
                              toast.success(t('company.data_from_sri'));
                            } else if (data.message) {
                              toast.warning(data.message);
                            }
                          } catch {
                            toast.error(t('company.sri_error'));
                          }
                        }}
                      >
                        SRI
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nc-cod-est">{t('company.code_est')}</Label>
                    <Input id="nc-cod-est" placeholder="001" value={newCompany.cod_establecimiento} onChange={(e) => setNewCompany({ ...newCompany, cod_establecimiento: e.target.value.replace(/\D/g, '').slice(0, 3) })} maxLength={3} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="nc-razon">{t('company.name')} <span className="text-red-500">*</span></Label>
                    <Input id="nc-razon" placeholder="Mi Empresa S.A." value={newCompany.razon_social} onChange={(e) => setNewCompany({ ...newCompany, razon_social: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nc-nombre">{t('company.commercial')}</Label>
                    <Input id="nc-nombre" placeholder="Mi Empresa" value={newCompany.nombre_comercial} onChange={(e) => setNewCompany({ ...newCompany, nombre_comercial: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nc-dir">{t('company.address')} <span className="text-red-500">*</span></Label>
                  <Input id="nc-dir" placeholder="Av. Amazonas 123, Quito" value={newCompany.dir_matriz} onChange={(e) => setNewCompany({ ...newCompany, dir_matriz: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="nc-correo">{t('company.email')}</Label>
                    <Input id="nc-correo" type="email" placeholder="info@empresa.com" value={newCompany.correo} onChange={(e) => setNewCompany({ ...newCompany, correo: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nc-tel">{t('company.phone')}</Label>
                    <Input id="nc-tel" placeholder="0999999999" value={newCompany.telefono} onChange={(e) => setNewCompany({ ...newCompany, telefono: e.target.value })} />
                  </div>
                </div>
              </div>
            </div>

            {/* Seccion: Configuracion Fiscal */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">{t('company.fiscal_config')}</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="nc-obligado">{t('company.obligated')}</Label>
                    <select
                      id="nc-obligado"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={newCompany.obligado_contabilidad}
                      onChange={(e) => setNewCompany({ ...newCompany, obligado_contabilidad: e.target.value })}
                    >
                      <option value="NO">NO</option>
                      <option value="SI">SI</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nc-cod-pemi">{t('company.code_emission')}</Label>
                    <Input id="nc-cod-pemi" placeholder="001" value={newCompany.cod_punto_emision} onChange={(e) => setNewCompany({ ...newCompany, cod_punto_emision: e.target.value.replace(/\D/g, '').slice(0, 3) })} maxLength={3} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>{t('company.rimpe')}</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      className={`flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer transition-colors text-left ${
                        newCompany.contribuyente_rimpe === 'RIMPE Emprendedor'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'hover:bg-accent'
                      }`}
                      onClick={() => setNewCompany({
                        ...newCompany,
                        contribuyente_rimpe: newCompany.contribuyente_rimpe === 'RIMPE Emprendedor' ? '' : 'RIMPE Emprendedor',
                      })}
                    >
                      <div className={`h-4 w-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                        newCompany.contribuyente_rimpe === 'RIMPE Emprendedor' ? 'border-primary' : 'border-muted-foreground'
                      }`}>
                        {newCompany.contribuyente_rimpe === 'RIMPE Emprendedor' && (
                          <div className="h-2 w-2 rounded-full bg-primary" />
                        )}
                      </div>
                      <span className="text-sm">{t('company.rimpe_emprendedor')}</span>
                    </button>
                    <button
                      type="button"
                      className={`flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer transition-colors text-left ${
                        newCompany.contribuyente_rimpe === 'RIMPE Negocio Popular'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'hover:bg-accent'
                      }`}
                      onClick={() => setNewCompany({
                        ...newCompany,
                        contribuyente_rimpe: newCompany.contribuyente_rimpe === 'RIMPE Negocio Popular' ? '' : 'RIMPE Negocio Popular',
                      })}
                    >
                      <div className={`h-4 w-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                        newCompany.contribuyente_rimpe === 'RIMPE Negocio Popular' ? 'border-primary' : 'border-muted-foreground'
                      }`}>
                        {newCompany.contribuyente_rimpe === 'RIMPE Negocio Popular' && (
                          <div className="h-2 w-2 rounded-full bg-primary" />
                        )}
                      </div>
                      <span className="text-sm">{t('company.rimpe_popular')}</span>
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">{t('company.rimpe_note')}</p>
                </div>

                {/* Campos condicionales para RIMPE Negocio Popular */}
                {newCompany.contribuyente_rimpe === 'RIMPE Negocio Popular' && (
                  <div className="pl-2 border-l-2 border-amber-400 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label htmlFor="nc-artesano-rimpe">{t('company.artisan_code')}</Label>
                        <Input id="nc-artesano-rimpe" placeholder={t('company.assigned_code')} value={newCompany.codigo_artesano} onChange={(e) => setNewCompany({ ...newCompany, codigo_artesano: e.target.value })} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="nc-nom-recibos-rimpe">{t('company.receipts_name')}</Label>
                        <Input id="nc-nom-recibos-rimpe" placeholder={t('company.receipts_placeholder')} value={newCompany.nombre_recibos} onChange={(e) => setNewCompany({ ...newCompany, nombre_recibos: e.target.value })} />
                      </div>
                    </div>
                  </div>
                )}
                <label className="flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer hover:bg-accent">
                  <input
                    type="checkbox"
                    checked={newCompany.registro_turistico}
                    onChange={(e) => setNewCompany({ ...newCompany, registro_turistico: e.target.checked })}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">{t('company.tourism')}</span>
                </label>
              </div>
            </div>

            {/* Seccion: Firma Electronica */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">{t('company.signature')}</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="nc-logo">{t('company.logo')}</Label>
                    <Input id="nc-logo" type="file" accept="image/*" ref={logoInputRef} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nc-firma-archivo">{t('company.signature_file')} <span className="text-destructive">*</span></Label>
                    <Input id="nc-firma-archivo" type="file" accept=".p12,.pfx" ref={firmaInputRef} required />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nc-firma-pass">{t('company.signature_pass')} <span className="text-destructive">*</span></Label>
                  <Input id="nc-firma-pass" type="password" placeholder={t('company.signature_pass_placeholder')} value={newCompany.firma_electronica_password} onChange={(e) => setNewCompany({ ...newCompany, firma_electronica_password: e.target.value })} required />
                  <p className="text-xs text-muted-foreground">{t('company.signature_required_hint')}</p>
                </div>
              </div>
            </div>

            {/* Seccion: Transportista (condicional) */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">{t('company.transport')}</h3>
              <div className="space-y-2">
                <label className="flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer hover:bg-accent">
                  <input
                    type="checkbox"
                    checked={newCompany.operadora_transportista_comercial}
                    onChange={(e) => setNewCompany({ ...newCompany, operadora_transportista_comercial: e.target.checked })}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">{t('company.transport_commercial')}</span>
                </label>
                <label className="flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer hover:bg-accent">
                  <input
                    type="checkbox"
                    checked={newCompany.operadora_transportista_ligera}
                    onChange={(e) => setNewCompany({ ...newCompany, operadora_transportista_ligera: e.target.checked })}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">{t('company.transport_light')}</span>
                </label>
              </div>
              {(newCompany.operadora_transportista_comercial || newCompany.operadora_transportista_ligera) && (
                <div className="mt-3 space-y-3 pl-2 border-l-2 border-primary/30">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="nc-ruc-op-comercial">{t('company.ruc_operator_commercial')}</Label>
                      <p className="text-xs text-muted-foreground">{t('company.only_partner')}</p>
                      <Input id="nc-ruc-op-comercial" placeholder="1790000000001" value={newCompany.ruc_operadora_comercial} onChange={(e) => setNewCompany({ ...newCompany, ruc_operadora_comercial: e.target.value.replace(/\D/g, '').slice(0, 13) })} maxLength={13} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="nc-ruc-op">{t('company.ruc_operator')}</Label>
                      <Input id="nc-ruc-op" placeholder="1790000000001" value={newCompany.ruc_operadora_transportista} onChange={(e) => setNewCompany({ ...newCompany, ruc_operadora_transportista: e.target.value.replace(/\D/g, '').slice(0, 13) })} maxLength={13} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="nc-agente-ret">{t('company.agent_retention')}</Label>
                      <Input id="nc-agente-ret" placeholder={t('company.resolution_number')} value={newCompany.agente_retencion} onChange={(e) => setNewCompany({ ...newCompany, agente_retencion: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="nc-contrib-esp">{t('company.special_contributor')}</Label>
                      <Input id="nc-contrib-esp" placeholder={t('company.resolution_number')} value={newCompany.contribuyente_especial} onChange={(e) => setNewCompany({ ...newCompany, contribuyente_especial: e.target.value })} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="nc-artesano">{t('company.artisan_code')}</Label>
                      <Input id="nc-artesano" placeholder={t('company.code')} value={newCompany.codigo_artesano} onChange={(e) => setNewCompany({ ...newCompany, codigo_artesano: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="nc-nom-recibos">{t('company.receipts_name')}</Label>
                      <Input id="nc-nom-recibos" placeholder={t('company.receipts_placeholder')} value={newCompany.nombre_recibos} onChange={(e) => setNewCompany({ ...newCompany, nombre_recibos: e.target.value })} />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Botones */}
            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button variant="outline" onClick={() => setShowNewCompany(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={handleCreateCompany} disabled={creatingCompany}>
                {creatingCompany ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('company.creating')}
                  </>
                ) : (
                  t('company.create')
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// --- Sub-views ---

function DashboardView({
  user,
  license,
  licenseExpiring,
  companies,
  invoiceStats,
  ivaRates,
  documentTypes,
}: {
  user: UserType;
  license: LicenseStatusType | null;
  licenseExpiring: boolean;
  companies: CompanyType[];
  invoiceStats: InvoiceStatsType | null;
  ivaRates: SRIIVARate[];
  documentTypes: SRIDocumentType[];
}) {
  return (
    <div className="space-y-6">
      {/* License Alert */}
      {licenseExpiring && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>{t('dash.license_expiring')}</AlertTitle>
          <AlertDescription>
            {t('dash.license_expiring_desc')}
          </AlertDescription>
        </Alert>
      )}

      {/* Trial Status Banner */}
      {license?.is_trial && license.trial_days_remaining !== null && (
        <Alert variant={license.trial_days_remaining <= 3 ? 'destructive' : 'default'}>
          <Clock className="h-4 w-4" />
          <AlertTitle>
            {license.trial_days_remaining <= 0
              ? t('dash.trial_ended')
              : license.trial_days_remaining <= 3
              ? t('dash.trial_expiring')
              : t('dash.trial_active')}
          </AlertTitle>
          <AlertDescription>
            {license.trial_days_remaining <= 0
              ? t('dash.trial_ended_desc')
              : license.trial_days_remaining <= 3
              ? t('dash.trial_days_left', { days: license.trial_days_remaining })
              : t('dash.trial_remaining', { days: license.trial_days_remaining })}
            {license.trial_end_date && (
              <span className="block mt-1 text-xs">
                {t('dash.expires')} {new Date(license.trial_end_date).toLocaleDateString('es-EC', { year: 'numeric', month: 'long', day: 'numeric' })}
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Welcome */}
      <div>
        <h2 className="text-2xl font-bold">
          {t('dash.welcome', { name: user.full_name || user.email })}
        </h2>
        <p className="text-muted-foreground">
          {t('dash.subtitle')}
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <QuickStatCard
          title={t('dash.companies')}
          value={companies.length}
          icon={<Building2 className="h-4 w-4" />}
          description={t('dash.registered')}
        />
        <QuickStatCard
          title={t('dash.vouchers')}
          value={invoiceStats?.total ?? 0}
          icon={<Receipt className="h-4 w-4" />}
          description={t('dash.issued')}
        />
        <QuickStatCard
          title={t('dash.approved_sri')}
          value={invoiceStats?.autorizado ?? 0}
          icon={<CheckCircle2 className="h-4 w-4" />}
          description={t('dash.this_month')}
        />
        <QuickStatCard
          title={t('dash.rejected')}
          value={invoiceStats?.rechazado ?? 0}
          icon={<XCircle className="h-4 w-4" />}
          description={t('dash.this_month')}
          variant="warning"
        />
      </div>

      {/* License Status + SRI Catalogs Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* License Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              {t('dash.license_status')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {license ? (
              <div className="space-y-3">
                {/* Trial Activo */}
                {license.trial_active ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('common.status')}</span>
                      <Badge variant="default" className="bg-amber-500">{t('dash.in_trial')}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('dash.days_remaining')}</span>
                      <span className="text-sm font-bold text-amber-600">{license.trial_days_remaining} {t('license.days')}</span>
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('dash.trial_end')}</span>
                      <span className="text-sm font-medium">
                        {license.trial_end_date
                          ? new Date(license.trial_end_date).toLocaleDateString('es-EC')
                          : 'N/A'}
                      </span>
                    </div>
                  </>
                ) : license.license_active ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('common.status')}</span>
                      <Badge variant="default" className="bg-emerald-500">{t('dash.active')}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('common.type')}</span>
                      <Badge variant="secondary" className="capitalize">
                        {license.license_type || 'N/A'}
                      </Badge>
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('dash.days_remaining')}</span>
                      <span className={`text-sm font-bold ${
                        (license.license_days_remaining ?? 0) <= 30 ? 'text-amber-500' : 'text-emerald-600'
                      }`}>
                        {license.license_days_remaining ?? 'N/A'} {t('license.days')}
                      </span>
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('dash.expires_on')}</span>
                      <span className="text-sm font-medium">
                        {license.license_end_date
                          ? new Date(license.license_end_date).toLocaleDateString('es-EC')
                          : 'N/A'}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{t('common.status')}</span>
                      <Badge variant="destructive">{t('dash.inactive')}</Badge>
                    </div>
                    {license.license_expired && (
                      <p className="text-xs text-destructive">
                        {t('dash.license_expired_note')}
                      </p>
                    )}
                  </>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <AlertTriangle className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  {t('dash.load_license_error')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* SRI Catalogs Preview */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              {t('dash.sri_catalogs')}
            </CardTitle>
            <CardDescription>
              {t('dash.sri_catalogs_desc')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-2">{t('dash.iva_rates')}</h4>
                {ivaRates.length > 0 ? (
                  <div className="grid grid-cols-2 gap-2">
                    {ivaRates.slice(0, 6).map((rate) => (
                      <div
                        key={rate.codigo}
                        className="flex items-center justify-between rounded-md border px-3 py-1.5"
                      >
                        <span className="text-xs">{rate.descripcion}</span>
                        <Badge variant="secondary" className="text-xs">
                          {rate.porcentaje}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {t('dash.no_iva_error')}
                  </p>
                )}
              </div>
              <Separator />
              <div>
                <h4 className="text-sm font-medium mb-2">{t('dash.doc_types')}</h4>
                {documentTypes.length > 0 ? (
                  <div className="space-y-1">
                    {documentTypes.slice(0, 5).map((dt) => (
                      <div
                        key={dt.codigo}
                        className="flex items-center justify-between rounded-md border px-3 py-1.5"
                      >
                        <span className="text-xs">{dt.descripcion}</span>
                        <Badge variant="outline" className="text-xs">
                          {dt.codigo}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {t('dash.no_docs_error')}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Companies Quick List */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" />
            {t('dash.companies_registered')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {companies.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {companies.map((company) => (
                <div
                  key={company.id}
                  className="rounded-lg border p-4 hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-medium">{company.razon_social}</h4>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        RUC: {company.ruc}
                      </p>
                    </div>
                    <Badge
                      variant={company.is_active ? 'default' : 'secondary'}
                      className={company.is_active ? 'bg-primary' : ''}
                    >
                      {company.is_active ? t('companies.active') : t('companies.inactive')}
                    </Badge>
                  </div>
                  {company.nombre_comercial && (
                    <p className="text-xs text-muted-foreground mt-2">
                      {company.nombre_comercial}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Building2 className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                {t('dash.no_companies')}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function QuickStatCard({
  title,
  value,
  icon,
  description,
  variant = 'default',
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  description: string;
  variant?: 'default' | 'warning';
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">{title}</span>
          <div
            className={`rounded-md p-1.5 ${
              variant === 'warning' ? 'bg-destructive/10' : 'bg-primary/10'
            }`}
          >
            <span className={variant === 'warning' ? 'text-destructive' : 'text-primary'}>
              {icon}
            </span>
          </div>
        </div>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

function CompaniesView({
  companies,
  onNewCompany,
  onCompaniesChanged,
}: {
  companies: CompanyType[];
  onNewCompany: () => void;
  onCompaniesChanged: () => void;
}) {
  const [editingCompany, setEditingCompany] = useState<CompanyType | null>(null);
  const [deletingCompanyId, setDeletingCompanyId] = useState<string | null>(null);
  const [operating, setOperating] = useState(false);
  const [editForm, setEditForm] = useState({
    ruc: '',
    razon_social: '',
    nombre_comercial: '',
    dir_matriz: '',
    cod_establecimiento: '',
    cod_punto_emision: '',
  });

  function handleEditClick(company: CompanyType) {
    setEditingCompany(company);
    setEditForm({
      ruc: company.ruc,
      razon_social: company.razon_social,
      nombre_comercial: company.nombre_comercial || '',
      dir_matriz: company.dir_matriz,
      cod_establecimiento: company.cod_establecimiento,
      cod_punto_emision: company.cod_punto_emision,
    });
  }

  async function handleEditSave() {
    if (!editingCompany) return;
    setOperating(true);
    try {
      await updateCompany(editingCompany.id, editForm);
      setEditingCompany(null);
      onCompaniesChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('companies.save_error'));
    } finally {
      setOperating(false);
    }
  }

  async function handleDeleteConfirm() {
    if (!deletingCompanyId) return;
    setOperating(true);
    try {
      await deleteCompany(deletingCompanyId);
      setDeletingCompanyId(null);
      onCompaniesChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('companies.delete_error'));
    } finally {
      setOperating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t('companies.title')}</h2>
          <p className="text-muted-foreground">
            {t('companies.subtitle')}
          </p>
        </div>
        <Button onClick={onNewCompany}>
          <Plus className="mr-2 h-4 w-4" />
          {t('companies.new')}
        </Button>
      </div>

      {companies.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>RUC</TableHead>
                    <TableHead>{t('companies.name')}</TableHead>
                    <TableHead>{t('companies.commercial_name')}</TableHead>
                    <TableHead>{t('companies.state')}</TableHead>
                    <TableHead className="text-right">{t('companies.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {companies.map((company) => (
                    <TableRow key={company.id}>
                      <TableCell className="font-mono text-xs">{company.ruc}</TableCell>
                      <TableCell className="font-medium">{company.razon_social}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {company.nombre_comercial || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={company.is_active ? 'default' : 'secondary'}
                          className={company.is_active ? 'bg-primary' : ''}
                        >
                          {company.is_active ? t('companies.active') : t('companies.inactive')}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleEditClick(company)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive"
                            onClick={() => setDeletingCompanyId(company.id)}
                          >
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
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">{t('companies.no_companies')}</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {t('companies.no_companies_desc')}
            </p>
            <Button className="mt-4" onClick={onNewCompany}>
              <Plus className="mr-2 h-4 w-4" />
              {t('companies.register')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Edit Company Dialog */}
      <Dialog open={!!editingCompany} onOpenChange={(open) => { if (!open) setEditingCompany(null); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('companies.edit_title')}</DialogTitle>
            <DialogDescription>
              {t('companies.edit_desc')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-ruc">RUC</Label>
                <Input
                  id="edit-ruc"
                  value={editForm.ruc}
                  onChange={(e) => setEditForm({ ...editForm, ruc: e.target.value })}
                  maxLength={13}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-cod-est">{t('companies.code_est')}</Label>
                <Input
                  id="edit-cod-est"
                  value={editForm.cod_establecimiento}
                  onChange={(e) => setEditForm({ ...editForm, cod_establecimiento: e.target.value })}
                  maxLength={3}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-razon">{t('companies.name')}</Label>
              <Input
                id="edit-razon"
                value={editForm.razon_social}
                onChange={(e) => setEditForm({ ...editForm, razon_social: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-nombre">{t('companies.commercial_name')}</Label>
              <Input
                id="edit-nombre"
                value={editForm.nombre_comercial}
                onChange={(e) => setEditForm({ ...editForm, nombre_comercial: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-dir">{t('companies.address')}</Label>
              <Input
                id="edit-dir"
                value={editForm.dir_matriz}
                onChange={(e) => setEditForm({ ...editForm, dir_matriz: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-cod-pemi">{t('companies.code_emission')}</Label>
                <Input
                  id="edit-cod-pemi"
                  value={editForm.cod_punto_emision}
                  onChange={(e) => setEditForm({ ...editForm, cod_punto_emision: e.target.value })}
                  maxLength={3}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditingCompany(null)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={handleEditSave} disabled={operating}>
                {operating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('common.saving')}
                  </>
                ) : (
                  t('companies.save_changes')
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Company Confirmation Dialog */}
      <Dialog open={!!deletingCompanyId} onOpenChange={(open) => { if (!open) setDeletingCompanyId(null); }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('companies.delete_title')}</DialogTitle>
            <DialogDescription>
              {t('companies.delete_confirm')}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDeletingCompanyId(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={operating}>
              {operating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.deleting')}
                </>
              ) : (
                t('common.delete')
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SRIView({
  ivaRates,
  documentTypes,
  identTypes,
}: {
  ivaRates: SRIIVARate[];
  documentTypes: SRIDocumentType[];
  identTypes: SRICatalog[];
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t('sri.title')}</h2>
        <p className="text-muted-foreground">
          {t('sri.subtitle')}
        </p>
      </div>

      <Tabs defaultValue="iva" className="space-y-4">
        <TabsList>
          <TabsTrigger value="iva">{t('sri.iva_tab')}</TabsTrigger>
          <TabsTrigger value="docs">{t('sri.docs_tab')}</TabsTrigger>
          <TabsTrigger value="ident">{t('sri.ident_tab')}</TabsTrigger>
        </TabsList>

        <TabsContent value="iva">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('sri.iva_title')}</CardTitle>
              <CardDescription>{t('sri.iva_desc')}</CardDescription>
            </CardHeader>
            <CardContent>
              {ivaRates.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('sri.code')}</TableHead>
                      <TableHead>{t('sri.description')}</TableHead>
                      <TableHead className="text-right">{t('sri.percentage')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ivaRates.map((rate) => (
                      <TableRow key={rate.codigo}>
                        <TableCell className="font-mono text-xs">{rate.codigo}</TableCell>
                        <TableCell>{rate.descripcion}</TableCell>
                        <TableCell className="text-right font-medium">{rate.porcentaje}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {t('sri.no_iva_error')}
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="docs">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('sri.docs_title')}</CardTitle>
              <CardDescription>{t('sri.docs_desc')}</CardDescription>
            </CardHeader>
            <CardContent>
              {documentTypes.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('sri.code')}</TableHead>
                      <TableHead>{t('sri.description')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documentTypes.map((dt) => (
                      <TableRow key={dt.codigo}>
                        <TableCell className="font-mono text-xs">{dt.codigo}</TableCell>
                        <TableCell>{dt.descripcion}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {t('sri.no_docs_error')}
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ident">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('sri.ident_title')}</CardTitle>
              <CardDescription>{t('sri.ident_desc')}</CardDescription>
            </CardHeader>
            <CardContent>
              {identTypes.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('sri.code')}</TableHead>
                      <TableHead>{t('sri.description')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {identTypes.map((it) => (
                      <TableRow key={it.codigo}>
                        <TableCell className="font-mono text-xs">{it.codigo}</TableCell>
                        <TableCell>{it.descripcion || it.nombre || '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {t('sri.no_ident_error')}
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function LicenseView({
  license,
  licenseExpiring,
  user,
}: {
  license: LicenseStatusType | null;
  licenseExpiring: boolean;
  user: UserType;
}) {
  const [licenseOptions, setLicenseOptions] = useState<LicenseOptionsType | null>(null);
  const [licenseTiers, setLicenseTiers] = useState<{
    tiers: Record<string, {
      price: number;
      months: number;
      label: string;
      max_companies: number;
      max_users_per_company: number;
      max_comprobantes_month: number;
      max_employees: number;
      max_products: number;
      features: Record<string, boolean>;
    }>;
  } | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [loadingTiers, setLoadingTiers] = useState(false);

  // Cargar opciones y tiers al montar
  useEffect(() => {
    setLoadingOptions(true);
    setLoadingTiers(true);
    Promise.allSettled([
      getLicenseOptions(),
      fetch('/api/v1/licenses/tiers').then(r => r.ok ? r.json() : Promise.reject()).catch(() => null),
    ]).then(([optionsResult, tiersResult]) => {
      if (optionsResult.status === 'fulfilled') {
        setLicenseOptions(optionsResult.value);
      }
      if (tiersResult.status === 'fulfilled' && tiersResult.value) {
        setLicenseTiers(tiersResult.value);
      }
    }).catch(() => toast.error(t('license.load_error'))).finally(() => {
      setLoadingOptions(false);
      setLoadingTiers(false);
    });
  }, []);

  // Determinar estado mostrado consistente
  const isTrialActive = license?.trial_active ?? false;
  const isLicenseActive = license?.license_active ?? false;
  const effectiveActive = isTrialActive || isLicenseActive;
  const effectiveExpired = !effectiveActive && (license?.license_expired ?? false);
  const _effectiveDaysRemaining = license?.days_remaining ?? license?.trial_days_remaining ?? null;

  // Un usuario en período de prueba aún NO tiene un plan pagado: todos los planes
  // deben poder seleccionarse. Solo se marca "Plan Actual" si hay una licencia
  // real activa (no trial) del mismo tipo.
  const isCurrentPlan = (type: string) => !license?.is_trial && license?.license_type === type;

  // Handler para WhatsApp
  const handleWhatsAppClick = (planType: string, price: number, months: number) => {
    const periodText = `${months} ${months === 1 ? t('license.month') : t('license.months')}`;
    const msg = `Hola, quiero adquirir/renovar mi licencia de ContaEC:\n\n• Plan: ${periodText}\n• Precio: $${price.toFixed(2)} USD\n• Mi correo: ${user.email}\n\nEspero información para el pago. Gracias.`;
    window.open(`https://wa.me/593960068866?text=${encodeURIComponent(msg)}`, '_blank');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t('license.title')}</h2>
        <p className="text-muted-foreground">
          {t('license.subtitle')}
        </p>
      </div>

      {licenseExpiring && license && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>{t('license.expiring_title')}</AlertTitle>
          <AlertDescription>
            {t('license.expiring_desc')}
          </AlertDescription>
        </Alert>
      )}

      {/* === ESTADO ACTUAL (CONSOLIDADO) === */}
      {license && (
        <>
          {/* Trial Activo */}
          {isTrialActive && (
            <Card className="border-amber-500">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-500" />
                  {t('license.trial_active_title')}
                </CardTitle>
                <CardDescription>{t('license.trial_active_desc')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">{t('common.status')}</span>
                    <Badge variant="default" className="bg-amber-500">{t('license.active')}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">{t('license.days_left')}</span>
                    <span className="text-sm font-bold text-amber-600">{license.trial_days_remaining} {t('license.days')}</span>
                  </div>
                  {license.trial_start_date && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">{t('license.start')}</span>
                      <span className="text-sm">{new Date(license.trial_start_date).toLocaleDateString('es-EC')}</span>
                    </div>
                  )}
                  {license.trial_end_date && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">{t('license.end')}</span>
                      <span className="text-sm font-medium">{new Date(license.trial_end_date).toLocaleDateString('es-EC')}</span>
                    </div>
                  )}
                </div>
                <Alert variant="default">
                  <AlertTitle className="text-sm">{t('license.trial_hint_title')}</AlertTitle>
                  <AlertDescription className="text-xs">
                    {t('license.trial_hint_desc')}
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          )}

          {/* Licencia Activa (cuando no hay trial activo) */}
          {!isTrialActive && isLicenseActive && (
            <Card className="border-emerald-500">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  {t('license.license_active_title', { plan: t(license.license_type === 'monthly' ? 'license.plan_monthly' : license.license_type === 'quarterly' ? 'license.plan_quarterly' : license.license_type === 'semiannual' ? 'license.plan_semiannual' : 'license.plan_annual') })}
                </CardTitle>
                <CardDescription>{t('license.license_active_desc', { plan: t(license.license_type === 'monthly' ? 'license.plan_monthly_lc' : license.license_type === 'quarterly' ? 'license.plan_quarterly_lc' : license.license_type === 'semiannual' ? 'license.plan_semiannual_lc' : 'license.plan_annual_lc') })}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">{t('common.status')}</span>
                    <Badge variant="default" className="bg-emerald-500">{t('license.active')}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">{t('license.days_left')}</span>
                    <span className="text-sm font-bold text-emerald-600">{license.license_days_remaining ?? 'N/A'} {t('license.days')}</span>
                  </div>
                  {license.license_start_date && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">{t('license.start')}</span>
                      <span className="text-sm">{new Date(license.license_start_date).toLocaleDateString('es-EC')}</span>
                    </div>
                  )}
                  {license.license_end_date && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">{t('license.end')}</span>
                      <span className="text-sm font-medium">{new Date(license.license_end_date).toLocaleDateString('es-EC')}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trial Expirado sin Licencia */}
          {!effectiveActive && (license?.is_trial || effectiveExpired) && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-destructive" />
                  {license?.is_trial ? t('license.trial_expired_title') : t('license.expired_title')}
                </CardTitle>
                <CardDescription>{t('license.expired_desc')}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {license?.is_trial
                    ? t('license.trial_ended_on', { date: license.trial_end_date ? new Date(license.trial_end_date).toLocaleDateString('es-EC') : '' })
                    : t('license.license_ended_on', { date: license.license_end_date ? new Date(license.license_end_date).toLocaleDateString('es-EC') : '' })
                  }
                </p>
                <p className="text-sm mt-2">{t('license.pick_plan')}</p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* === PLANES DISPONIBLES CON TABLA COMPARATIVA === */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-primary" />
            {t('license.plans_title')}
          </CardTitle>
          <CardDescription>
            {t('license.plans_desc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Tarjetas de precios */}
          {loadingOptions ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : licenseOptions ? (
            <>
              {license?.is_trial && isTrialActive && (
                <Alert variant="default" className="bg-amber-50 border-amber-200 dark:bg-amber-950/30">
                  <Clock className="h-4 w-4 text-amber-600" />
                  <AlertTitle className="text-sm">{t('license.trial_can_purchase')}</AlertTitle>
                </Alert>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {licenseOptions.options.map((option) => {
                const currentPlan = isCurrentPlan(option.type);
                return (
                  <Card key={option.type} className={`hover:border-primary transition-colors ${
                    currentPlan ? 'border-primary ring-2 ring-primary/20' : ''
                  }`}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg">{t(`license.plan_${option.type}`)}</CardTitle>
                      <CardDescription>{option.months} {option.months === 1 ? t('license.month') : t('license.months')}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="text-center">
                        <span className="text-3xl font-bold">${option.price.toFixed(2)}</span>
                        <p className="text-xs text-muted-foreground">
                          ${(option.price / option.months).toFixed(2)}/{t('license.per_month')}
                        </p>
                      </div>
                      {currentPlan && (
                        <Badge className="w-full justify-center">{t('license.current_plan')}</Badge>
                      )}
                      <Button
                        className="w-full"
                        variant={currentPlan ? 'outline' : 'default'}
                        onClick={() => handleWhatsAppClick(option.type, option.price, option.months)}
                        disabled={currentPlan}
                      >
                        {currentPlan ? t('license.already_have') : t('license.buy_plan')}
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              {t('license.no_options_error')}
            </p>
          )}

          <Separator />

          {/* Tabla comparativa detallada */}
          <div>
            <h3 className="text-lg font-semibold mb-4">{t('license.compare_table')}</h3>
            {loadingTiers ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : licenseTiers?.tiers ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[200px]">{t('license.feature')}</TableHead>
                      <TableHead className="text-center">{t('license.monthly')}</TableHead>
                      <TableHead className="text-center">{t('license.quarterly')}</TableHead>
                      <TableHead className="text-center">{t('license.semiannual')}</TableHead>
                      <TableHead className="text-center">{t('license.annual')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {/* Precios */}
                    <TableRow className="bg-primary/5">
                      <TableCell className="font-semibold">{t('license.price')}</TableCell>
                      <TableCell className="text-center font-bold">${licenseTiers.tiers.monthly?.price}</TableCell>
                      <TableCell className="text-center font-bold">${licenseTiers.tiers.quarterly?.price}</TableCell>
                      <TableCell className="text-center font-bold">${licenseTiers.tiers.semiannual?.price}</TableCell>
                      <TableCell className="text-center font-bold">${licenseTiers.tiers.annual?.price}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">{t('license.duration')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.monthly?.months} {t('license.month')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.quarterly?.months} {t('license.months')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.semiannual?.months} {t('license.months')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.annual?.months} {t('license.months')}</TableCell>
                    </TableRow>
                    {/* Límites */}
                    <TableRow className="bg-muted/30">
                      <TableCell className="font-semibold">{t('license.limits')}</TableCell>
                      <TableCell colSpan={4}></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.max_companies')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.monthly?.max_companies}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.quarterly?.max_companies}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.semiannual?.max_companies}</TableCell>
                      <TableCell className="text-center">{t('license.unlimited')}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.users_per_company')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.monthly?.max_users_per_company}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.quarterly?.max_users_per_company}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.semiannual?.max_users_per_company}</TableCell>
                      <TableCell className="text-center">{t('license.unlimited')}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.vouchers_per_month')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.monthly?.max_comprobantes_month}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.quarterly?.max_comprobantes_month}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.semiannual?.max_comprobantes_month}</TableCell>
                      <TableCell className="text-center">{t('license.unlimited')}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.employees')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.monthly?.max_employees}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.quarterly?.max_employees}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.semiannual?.max_employees}</TableCell>
                      <TableCell className="text-center">{t('license.unlimited')}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.products')}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.monthly?.max_products}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.quarterly?.max_products}</TableCell>
                      <TableCell className="text-center">{licenseTiers.tiers.semiannual?.max_products}</TableCell>
                      <TableCell className="text-center">{t('license.unlimited')}</TableCell>
                    </TableRow>
                    {/* Funcionalidades */}
                    <TableRow className="bg-muted/30">
                      <TableCell className="font-semibold">{t('license.features')}</TableCell>
                      <TableCell colSpan={4}></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.electronic_invoicing')}</TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.basic_accounting')}</TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.inventory')}</TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.proformas')}</TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.pos')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.payroll')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.multi_warehouse')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.budgets')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.crm')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.projects')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.ml_ai')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.banking_integration')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">{t('license.priority_support')}</TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><XCircle className="h-4 w-4 mx-auto text-muted-foreground" /></TableCell>
                      <TableCell className="text-center"><CheckCircle2 className="h-4 w-4 mx-auto text-emerald-600" /></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                {t('license.no_table_error')}
              </p>
            )}
          </div>

          {/* CTA final */}
          <div className="bg-muted/50 rounded-lg p-4 text-center">
            <p className="text-sm text-muted-foreground mb-2">
              {t('license.help')}
            </p>
            <Button variant="outline" onClick={() => handleWhatsAppClick('consulta', 0, 0)}>
              {t('license.whatsapp')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {!license && (
        <div className="space-y-6">
          <Card>
            <CardContent className="py-12 text-center">
              <AlertTriangle className="h-12 w-12 mx-auto text-amber-500 mb-3" />
              <h3 className="text-lg font-medium">{t('license.no_license_title')}</h3>
              <p className="text-muted-foreground text-sm mt-1">
                {t('license.no_license_desc')}
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function _InvoicesView({ invoiceStats }: { invoiceStats: InvoiceStatsType | null }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t('invoices.section_title')}</h2>
        <p className="text-muted-foreground">
          {t('invoices.section_subtitle')}
        </p>
      </div>

      {invoiceStats ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <Receipt className="h-6 w-6 mx-auto text-primary mb-2" />
              <div className="text-2xl font-bold">{invoiceStats.total}</div>
              <p className="text-xs text-muted-foreground">{t('invoices.total_issued')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Clock className="h-6 w-6 mx-auto text-muted-foreground mb-2" />
              <div className="text-2xl font-bold">{invoiceStats.borrador}</div>
              <p className="text-xs text-muted-foreground">{t('invoices.drafts')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <FileText className="h-6 w-6 mx-auto text-primary mb-2" />
              <div className="text-2xl font-bold">{invoiceStats.enviado}</div>
              <p className="text-xs text-muted-foreground">{t('invoices.sent_sri')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <CheckCircle2 className="h-6 w-6 mx-auto text-green-600 mb-2" />
              <div className="text-2xl font-bold">{invoiceStats.autorizado}</div>
              <p className="text-xs text-muted-foreground">{t('invoices.approved')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <XCircle className="h-6 w-6 mx-auto text-destructive mb-2" />
              <div className="text-2xl font-bold">{invoiceStats.rechazado}</div>
              <p className="text-xs text-muted-foreground">{t('invoices.rejected')}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <DollarSign className="h-6 w-6 mx-auto text-primary mb-2" />
              <div className="text-2xl font-bold">
                ${invoiceStats.total_amount.toLocaleString('es-EC', { minimumFractionDigits: 2 })}
              </div>
              <p className="text-xs text-muted-foreground">{t('invoices.total_amount')}</p>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Receipt className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">{t('invoices.no_data_title')}</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {t('invoices.no_data_desc')}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Policies View (visible to all users) ─────────────────────────────────
type PolicyType = 'lopd' | 'terms' | 'refund' | null;

function PoliciesView() {
  const [activePolicy, setActivePolicy] = useState<PolicyType>(null);

  const policies = [
    {
      key: 'lopd' as PolicyType,
      title: t('policy.lopd', 'L.O.P.D'),
      subtitle: t('policy.lopd.subtitle', 'Ley Organica de Proteccion de Datos Personales'),
      description: t('policy.lopd.desc', 'Marco legal para la proteccion de datos personales en Ecuador'),
      icon: Shield,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    },
    {
      key: 'terms' as PolicyType,
      title: t('policy.terms', 'Terminos y Condiciones'),
      subtitle: t('policy.terms.subtitle', 'Acuerdo de uso del sistema ContaEC'),
      description: t('policy.terms.desc', 'Reglas y condiciones para el uso de la plataforma'),
      icon: FileText,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
    },
    {
      key: 'refund' as PolicyType,
      title: t('policy.refund', 'Politica de Reembolso'),
      subtitle: t('policy.refund.subtitle', 'Condiciones de devolucion y reembolso'),
      description: t('policy.refund.desc', 'Politicas aplicables a reembolsos y devoluciones'),
      icon: DollarSign,
      color: 'text-amber-600',
      bgColor: 'bg-amber-100 dark:bg-amber-900/30',
    },
  ];

  if (activePolicy) {
    return (
      <div className="space-y-6">
        <Button variant="outline" size="sm" onClick={() => setActivePolicy(null)} className="gap-2">
          <ChevronLeft className="h-4 w-4" />
          Volver a Politicas
        </Button>
        {activePolicy === 'lopd' && <LOPDPolicy />}
        {activePolicy === 'terms' && <TermsPolicy />}
        {activePolicy === 'refund' && <RefundPolicy />}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t('nav.policies', 'Politicas')}</h2>
        <p className="text-muted-foreground">{t('policies.description', 'Informacion legal y politicas de uso del sistema')}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {policies.map((p) => (
          <Card
            key={p.key}
            className="cursor-pointer hover:border-primary transition-colors border-2"
            onClick={() => setActivePolicy(p.key)}
          >
            <CardHeader>
              <div className={`rounded-lg ${p.bgColor} w-12 h-12 flex items-center justify-center mb-3`}>
                <p.icon className={`h-6 w-6 ${p.color}`} />
              </div>
              <CardTitle className="text-lg">{p.title}</CardTitle>
              <CardDescription>{p.subtitle}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{p.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Admin Dashboard View (integrated into main dashboard) ────────────────
function AdminDashboardView({ onLogout, activeAdminTab }: { onLogout: () => void; activeAdminTab: string }) {
  const [adminStats, setAdminStats] = useState<{
    total_users: number;
    total_companies: number;
    total_clients: number;
    expiring_licenses: number;
    expired_licenses: number;
    license_distribution: Record<string, number>;
  } | null>(null);
  const [adminUsers, setAdminUsers] = useState<Array<{
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
    is_admin: boolean;
    license_type: string;
    license_end_date: string | null;
    created_at: string;
  }>>([]);
  const [health, setHealth] = useState<{
    system: Record<string, unknown>;
    database: Record<string, unknown>;
    application: Record<string, unknown>;
  } | null>(null);
  const [securityData, setSecurityData] = useState<{
    expired_active_licenses: Array<{ user_id: string; email: string; full_name: string; license_end_date: string | null; days_expired: number | null }>;
    users_without_config: Array<{ user_id: string; email: string; full_name: string }>;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [licenseDialogOpen, setLicenseDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [licenseForm, setLicenseForm] = useState({ license_type: '' });
  const [modifying, setModifying] = useState(false);
  const [licensePrices, setLicensePrices] = useState<Array<{ type: string; key: string; price: number; months: number; color: string }>>([
    { type: 'Mensual', key: 'monthly', price: 15.00, months: 1, color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
    { type: 'Trimestral', key: 'quarterly', price: 40.00, months: 3, color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    { type: 'Semestral', key: 'semiannual', price: 75.00, months: 6, color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
    { type: 'Anual', key: 'annual', price: 130.00, months: 12, color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' },
  ]);
  const [editingPrice, setEditingPrice] = useState<string | null>(null);
  const [priceForm, setPriceForm] = useState<Record<string, number>>({});
  const [savingPrices, setSavingPrices] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('contaec_token') || '';
      const headers = { headers: { Authorization: `Bearer ${token}` } };
      const results = await Promise.allSettled([
        fetch('/api/v1/admin/dashboard', headers).then(r => r.ok ? r.json() : Promise.reject(r.status)),
        fetch('/api/v1/admin/users', headers).then(r => r.ok ? r.json() : Promise.reject(r.status)),
        fetch('/api/v1/admin/system-health', headers).then(r => r.ok ? r.json() : Promise.reject(r.status)),
        fetch('/api/v1/admin/security-issues', headers).then(r => r.ok ? r.json() : Promise.reject(r.status)),
        fetch('/api/v1/admin/license-prices', headers).then(r => r.ok ? r.json() : Promise.reject(r.status)),
      ]);

      // Detect session expiry: if ALL admin API calls are rejected, session is invalid
      const allRejected = results.every(r => r.status === 'rejected');
      if (allRejected) {
        clearTokens();
        onLogout();
        toast.error(t('common.session_expired'));
        return;
      }

      if (results[0].status === 'fulfilled') setAdminStats(results[0].value);
      if (results[1].status === 'fulfilled' && Array.isArray(results[1].value)) setAdminUsers(results[1].value);
      if (results[2].status === 'fulfilled') setHealth(results[2].value);
      if (results[3].status === 'fulfilled') setSecurityData(results[3].value);
      // Load license prices from API
      if (results[4].status === 'fulfilled' && results[4].value?.prices) {
        const prices = results[4].value.prices;
        const colorMap: Record<string, string> = {
          monthly: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
          quarterly: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
          semiannual: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
          annual: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
        };
        setLicensePrices([
          { type: prices.monthly?.label || 'Mensual', key: 'monthly', price: prices.monthly?.price || 15, months: prices.monthly?.months || 1, color: colorMap.monthly },
          { type: prices.quarterly?.label || 'Trimestral', key: 'quarterly', price: prices.quarterly?.price || 40, months: prices.quarterly?.months || 3, color: colorMap.quarterly },
          { type: prices.semiannual?.label || 'Semestral', key: 'semiannual', price: prices.semiannual?.price || 75, months: prices.semiannual?.months || 6, color: colorMap.semiannual },
          { type: prices.annual?.label || 'Anual', key: 'annual', price: prices.annual?.price || 130, months: prices.annual?.months || 12, color: colorMap.annual },
        ]);
        setPriceForm({
          monthly: prices.monthly?.price || 15,
          quarterly: prices.quarterly?.price || 40,
          semiannual: prices.semiannual?.price || 75,
          annual: prices.annual?.price || 130,
        });
      }
    } catch {
      toast.error('Error al cargar datos de administracion');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadAdminData();
  }, [loadAdminData]);

  async function handleModifyLicense() {
    if (!selectedUserId) return;
    setModifying(true);
    try {
      const token = localStorage.getItem('contaec_token') || '';
      const res = await fetch(`/api/v1/admin/users/${selectedUserId}/license?license_type=${licenseForm.license_type}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Error al modificar licencia');
      toast.success('Licencia actualizada');
      setLicenseDialogOpen(false);
      loadAdminData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al modificar licencia');
    } finally {
      setModifying(false);
    }
  }

  async function handleToggleUser(userId: string, isActive: boolean) {
    try {
      const token = localStorage.getItem('contaec_token') || '';
      const res = await fetch(`/api/v1/admin/users/${userId}/active?is_active=${!isActive}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Error al cambiar estado' }));
        throw new Error(error.detail || 'Error al cambiar estado');
      }
      toast.success(isActive ? 'Usuario desactivado' : 'Usuario activado');
      loadAdminData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error');
    }
  }

  async function handleSavePrices() {
    setSavingPrices(true);
    try {
      const token = localStorage.getItem('contaec_token') || '';
      const res = await fetch('/api/v1/admin/license-prices', {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(priceForm),
      });
      if (!res.ok) throw new Error('Error al guardar precios');
      toast.success('Precios actualizados correctamente');
      setEditingPrice(null);
      loadAdminData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al guardar precios');
    } finally {
      setSavingPrices(false);
    }
  }

  async function handleDeleteUser(userId: string, email: string) {
    setDeleting(true);
    try {
      const token = localStorage.getItem('contaec_token') || '';
      const res = await fetch(`/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Error al eliminar usuario' }));
        throw new Error(error.detail || 'Error al eliminar usuario');
      }
      toast.success(`Usuario ${email} eliminado con toda su informacion asociada`);
      setDeleteDialogOpen(false);
      loadAdminData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al eliminar usuario');
    } finally {
      setDeleting(false);
    }
  }

  if (loading && !adminStats) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Panel de Administracion</h2>
        <p className="text-muted-foreground">Gestion del sistema ContaEC</p>
      </div>

      {/* Overview */}
      {activeAdminTab === 'admin-overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardContent className="p-6 text-center">
                <Users className="h-8 w-8 mx-auto text-primary mb-2" />
                <div className="text-3xl font-bold">{adminStats?.total_users ?? 0}</div>
                <p className="text-sm text-muted-foreground">Total Usuarios</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 text-center">
                <Building2 className="h-8 w-8 mx-auto text-primary mb-2" />
                <div className="text-3xl font-bold">{adminStats?.total_companies ?? 0}</div>
                <p className="text-sm text-muted-foreground">Total Empresas</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 text-center">
                <Database className="h-8 w-8 mx-auto text-primary mb-2" />
                <div className="text-3xl font-bold">{adminStats?.total_clients ?? 0}</div>
                <p className="text-sm text-muted-foreground">Total Clientes</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 text-center">
                <Clock className="h-8 w-8 mx-auto text-amber-500 mb-2" />
                <div className="text-3xl font-bold">{adminStats?.expiring_licenses ?? 0}</div>
                <p className="text-sm text-muted-foreground">Licencias por Expirar (30d)</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 text-center">
                <XCircle className="h-8 w-8 mx-auto text-destructive mb-2" />
                <div className="text-3xl font-bold">{adminStats?.expired_licenses ?? 0}</div>
                <p className="text-sm text-muted-foreground">Licencias Expiradas</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Users */}
        {activeAdminTab === 'admin-users' && (
          <Card>
            <CardHeader>
              <CardTitle>Usuarios del Sistema</CardTitle>
              <CardDescription>Gestione usuarios y licencias</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Licencia</TableHead>
                      <TableHead>Expiracion</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {adminUsers.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell className="font-medium">{u.full_name}</TableCell>
                        <TableCell>{u.email}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="capitalize">{u.license_type || 'N/A'}</Badge>
                        </TableCell>
                        <TableCell>
                          {u.license_end_date
                            ? new Date(u.license_end_date).toLocaleDateString('es-EC')
                            : 'Sin limite'}
                        </TableCell>
                        <TableCell>
                          <Badge variant={u.is_active ? 'default' : 'destructive'}>
                            {u.is_active ? 'Activo' : 'Inactivo'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => { setSelectedUserId(u.id); setLicenseDialogOpen(true); setLicenseForm({ license_type: u.license_type }); }}
                            >
                              Licencia
                            </Button>
                            <Button
                              size="sm"
                              variant={u.is_active ? 'destructive' : 'default'}
                              onClick={() => handleToggleUser(u.id, u.is_active)}
                            >
                              {u.is_active ? 'Desactivar' : 'Activar'}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-destructive hover:text-destructive"
                              onClick={() => { setSelectedUserId(u.id); setDeleteDialogOpen(true); }}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* System */}
        {activeAdminTab === 'admin-system' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Server className="h-4 w-4 text-primary" />
                  Aplicacion
                </CardTitle>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Version</span>
                      <Badge variant="outline" className="font-mono">{(health.application as Record<string, string>)?.version ?? 'N/A'}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Ambiente</span>
                      <Badge variant={(health.application as Record<string, string>)?.environment === 'production' ? 'destructive' : 'default'}>
                        {(health.application as Record<string, string>)?.environment ?? 'N/A'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Uptime</span>
                      <span className="text-sm font-medium">{(health.application as Record<string, string>)?.uptime ?? 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Python</span>
                      <span className="text-sm font-mono">{(health.application as Record<string, string>)?.python_version ?? ''}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">SO</span>
                      <span className="text-sm font-medium">{(health.application as Record<string, string>)?.system ?? ''}</span>
                    </div>
                    <Separator />
                    <div className="text-xs text-muted-foreground">
                      <p>Para cambiar ambiente, edite <code className="bg-muted px-1">APP_ENV</code> en <code className="bg-muted px-1">.env</code> y reinicie el servidor.</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">Cargando...</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recursos del Sistema</CardTitle>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">CPU</span>
                        <span className="font-medium">
                          {typeof (health.system as Record<string, unknown>)?.cpu_percent === 'number'
                            ? `${(health.system as Record<string, number>)?.cpu_percent}%`
                            : String((health.system as Record<string, unknown>)?.cpu_percent ?? 'N/A')}
                        </span>
                      </div>
                      {typeof (health.system as Record<string, unknown>)?.cpu_percent === 'number' && (
                        <div className="h-2 bg-muted rounded-full overflow-hidden mt-1">
                          <div className="h-full bg-primary transition-all" style={{ width: `${(health.system as Record<string, number>)?.cpu_percent}%` }} />
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Memoria</span>
                        <span className="font-medium">
                          {typeof (health.system as Record<string, unknown>)?.memory_percent === 'number'
                            ? `${(health.system as Record<string, number>)?.memory_percent}%`
                            : String((health.system as Record<string, unknown>)?.memory_percent ?? 'N/A')}
                        </span>
                      </div>
                      {typeof (health.system as Record<string, unknown>)?.memory_percent === 'number' && (
                        <>
                          <div className="h-2 bg-muted rounded-full overflow-hidden mt-1">
                            <div className="h-full bg-primary transition-all" style={{ width: `${(health.system as Record<string, number>)?.memory_percent}%` }} />
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {((health.system as Record<string, number>)?.memory_used_mb ?? 0).toFixed(0)} MB / {((health.system as Record<string, number>)?.memory_total_mb ?? 0).toFixed(0)} MB
                          </p>
                        </>
                      )}
                    </div>
                    <div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Disco</span>
                        <span className="font-medium">
                          {typeof (health.system as Record<string, unknown>)?.disk_percent === 'number'
                            ? `${(health.system as Record<string, number>)?.disk_percent}%`
                            : String((health.system as Record<string, unknown>)?.disk_percent ?? 'N/A')}
                        </span>
                      </div>
                      {typeof (health.system as Record<string, unknown>)?.disk_percent === 'number' && (
                        <>
                          <div className="h-2 bg-muted rounded-full overflow-hidden mt-1">
                            <div className={`h-full transition-all ${(health.system as Record<string, number>)?.disk_percent > 90 ? 'bg-destructive' : 'bg-primary'}`} style={{ width: `${(health.system as Record<string, number>)?.disk_percent}%` }} />
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {((health.system as Record<string, number>)?.disk_used_gb ?? 0).toFixed(1)} GB / {((health.system as Record<string, number>)?.disk_total_gb ?? 0).toFixed(1)} GB
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">Cargando...</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Base de Datos</CardTitle>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-3">
                    <div className="flex justify-between p-3 rounded-lg border">
                      <span className="text-sm">Usuarios</span>
                      <span className="font-medium">{(health.database as Record<string, number>)?.total_users ?? 'N/A'}</span>
                    </div>
                    <div className="flex justify-between p-3 rounded-lg border">
                      <span className="text-sm">Empresas</span>
                      <span className="font-medium">{(health.database as Record<string, number>)?.total_companies ?? 'N/A'}</span>
                    </div>
                    <div className="flex justify-between p-3 rounded-lg border">
                      <span className="text-sm">Clientes</span>
                      <span className="font-medium">{(health.database as Record<string, number>)?.total_clients ?? 'N/A'}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">Cargando...</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Licenses */}
        {activeAdminTab === 'admin-licenses' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-medium">Precios de Licencias</h3>
              <div className="flex gap-2">
                {editingPrice ? (
                  <>
                    <Button variant="outline" size="sm" onClick={() => { setEditingPrice(null); loadAdminData(); }}>
                      Cancelar
                    </Button>
                    <Button size="sm" onClick={handleSavePrices} disabled={savingPrices}>
                      {savingPrices ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                      Guardar Precios
                    </Button>
                  </>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => setEditingPrice('prices')}>
                    <Pencil className="h-3.5 w-3.5 mr-1" />
                    Editar Precios
                  </Button>
                )}
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {licensePrices.map((plan) => (
              <Card key={plan.key} className="border-2">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">{plan.type}</CardTitle>
                  <CardDescription>{plan.months} {plan.months === 1 ? 'mes' : 'meses'}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center">
                    {editingPrice ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="text-lg font-bold">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          className="w-24 text-center text-xl font-bold"
                          value={priceForm[plan.key] ?? plan.price}
                          onChange={(e) => setPriceForm({ ...priceForm, [plan.key]: parseFloat(e.target.value) || 0 })}
                        />
                      </div>
                    ) : (
                      <span className="text-3xl font-bold">${plan.price.toFixed(2)}</span>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      ${((priceForm[plan.key] ?? plan.price) / plan.months).toFixed(2)}/mes
                    </p>
                  </div>
                  <Badge className={`w-full justify-center mt-3 ${plan.color}`}>{plan.type}</Badge>
                </CardContent>
              </Card>
            ))}
          </div>
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-base">Limites por Plan</CardTitle>
              <CardDescription>Caracteristicas y limites de cada tipo de licencia</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Limite</TableHead>
                      <TableHead>Mensual</TableHead>
                      <TableHead>Trimestral</TableHead>
                      <TableHead>Semestral</TableHead>
                      <TableHead>Anual</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow><TableCell className="font-medium">Empresas max.</TableCell><TableCell>1</TableCell><TableCell>2</TableCell><TableCell>5</TableCell><TableCell>Ilimitado</TableCell></TableRow>
                    <TableRow><TableCell className="font-medium">Usuarios/empresa</TableCell><TableCell>2</TableCell><TableCell>5</TableCell><TableCell>10</TableCell><TableCell>Ilimitado</TableCell></TableRow>
                    <TableRow><TableCell className="font-medium">Comprobantes/mes</TableCell><TableCell>50</TableCell><TableCell>200</TableCell><TableCell>500</TableCell><TableCell>Ilimitado</TableCell></TableRow>
                    <TableRow><TableCell className="font-medium">Empleados</TableCell><TableCell>5</TableCell><TableCell>15</TableCell><TableCell>50</TableCell><TableCell>Ilimitado</TableCell></TableRow>
                    <TableRow><TableCell className="font-medium">Productos</TableCell><TableCell>100</TableCell><TableCell>500</TableCell><TableCell>2,000</TableCell><TableCell>Ilimitado</TableCell></TableRow>
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
          </div>
        )}

        {/* Security */}
        {activeAdminTab === 'admin-security' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-amber-500" />
                Problemas de Seguridad
              </CardTitle>
              <CardDescription>Usuarios con licencias expiradas pero activos, y sin configuracion</CardDescription>
            </CardHeader>
            <CardContent>
              {securityData ? (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-destructive" />
                      Licencias Expiradas pero Activas ({securityData.expired_active_licenses.length})
                    </h3>
                    {securityData.expired_active_licenses.length > 0 ? (
                      <Table>
                        <TableHeader>
                          <TableRow><TableHead>Usuario</TableHead><TableHead>Email</TableHead><TableHead>Expiro</TableHead><TableHead>Dias</TableHead></TableRow>
                        </TableHeader>
                        <TableBody>
                          {securityData.expired_active_licenses.map((u) => (
                            <TableRow key={u.user_id}>
                              <TableCell className="font-medium">{u.full_name}</TableCell>
                              <TableCell>{u.email}</TableCell>
                              <TableCell>{u.license_end_date ? new Date(u.license_end_date).toLocaleDateString('es-EC') : 'N/A'}</TableCell>
                              <TableCell className="text-destructive">{u.days_expired ?? 'N/A'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      <p className="text-sm text-muted-foreground">No hay problemas</p>
                    )}
                  </div>
                  <Separator />
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      Usuarios sin Configuracion ({securityData.users_without_config.length})
                    </h3>
                    {securityData.users_without_config.length > 0 ? (
                      <Table>
                        <TableHeader>
                          <TableRow><TableHead>Usuario</TableHead><TableHead>Email</TableHead></TableRow>
                        </TableHeader>
                        <TableBody>
                          {securityData.users_without_config.map((u) => (
                            <TableRow key={u.user_id}>
                              <TableCell className="font-medium">{u.full_name}</TableCell>
                              <TableCell>{u.email}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      <p className="text-sm text-muted-foreground">Todos los usuarios tienen configuracion</p>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">Cargando...</p>
              )}
            </CardContent>
          </Card>
        )}

      {/* License Dialog */}
      <Dialog open={licenseDialogOpen} onOpenChange={setLicenseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modificar Licencia</DialogTitle>
            <DialogDescription>Seleccione el tipo de licencia para el usuario</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Tipo de Licencia</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={licenseForm.license_type}
                onChange={(e) => setLicenseForm({ license_type: e.target.value })}
              >
                {licensePrices.map((p) => (
                  <option key={p.key} value={p.key}>{p.type} - ${p.price.toFixed(2)}</option>
                ))}
              </select>
            </div>
            <Button onClick={handleModifyLicense} disabled={modifying} className="w-full">
              {modifying ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Guardar Cambios
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              Eliminar Usuario
            </DialogTitle>
            <DialogDescription>
              Esta accion eliminara permanentemente al usuario y toda su informacion asociada (empresas, clientes, comprobantes, configuracion, etc.). Esta accion no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Accion irreversible</AlertTitle>
              <AlertDescription>
                Se eliminara toda la informacion atada a este usuario.
              </AlertDescription>
            </Alert>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
                Cancelar
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleDeleteUser(selectedUserId, adminUsers.find(u => u.id === selectedUserId)?.email || '')}
                disabled={deleting}
              >
                {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Eliminar Permanentemente
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
