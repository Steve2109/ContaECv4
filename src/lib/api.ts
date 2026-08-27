// ContaEC API Client - Ecuadorian Accounting & Electronic Invoicing System
// Communicates with FastAPI backend through Next.js API proxy

const API_BASE = '/api';

function buildUrl(endpoint: string): string {
  return `${API_BASE}${endpoint}`;
}

// Token management
function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('contaec_token');
}

function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('contaec_token', token);
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('contaec_refresh_token');
}

function setRefreshToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('contaec_refresh_token', token);
}

function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('contaec_token');
  localStorage.removeItem('contaec_refresh_token');
  localStorage.removeItem('contaec_user');
}

function setUserCache(user: unknown): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('contaec_user', JSON.stringify(user));
}

function getUserCache(): unknown | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('contaec_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

// Generic API helpers
async function apiRequest<T>(
  method: string,
  endpoint: string,
  body?: unknown,
  options?: { skipAuth?: boolean }
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (!options?.skipAuth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const config: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(buildUrl(endpoint), config);

  if (response.status === 401) {
    // Try refresh (single-flight: varias peticiones 401 simultáneas comparten UN solo refresh,
    // evitando que la rotación de refresh tokens revoque la cadena por replay)
    const refreshed = await refreshToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getToken()}`;
      const retryResponse = await fetch(buildUrl(endpoint), {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      if (!retryResponse.ok) {
        const errorData = await retryResponse.json().catch(() => ({ detail: 'Error de servidor' }));
        throw new Error(errorData.detail || `Error ${retryResponse.status}`);
      }
      return retryResponse.json();
    }
    clearTokens();
    throw new Error('Sesion expirada. Por favor inicie sesion nuevamente.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error de servidor' }));
    const detail = errorData.detail;
    // Handle Pydantic 422 validation errors (array of {loc, msg, type})
    let message: string;
    if (Array.isArray(detail)) {
      message = detail.map((e: { loc?: (string | number)[]; msg?: string }) => e.msg || e).filter(Boolean).join(', ');
    } else if (typeof detail === 'string') {
      message = detail;
    } else {
      message = `Error ${response.status}`;
    }
    throw new Error(message);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

async function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>('GET', endpoint);
}

async function apiPost<T>(endpoint: string, body?: unknown, options?: { skipAuth?: boolean }): Promise<T> {
  return apiRequest<T>('POST', endpoint, body, options);
}

async function apiPut<T>(endpoint: string, body?: unknown): Promise<T> {
  return apiRequest<T>('PUT', endpoint, body);
}

async function apiDelete<T>(endpoint: string): Promise<T> {
  return apiRequest<T>('DELETE', endpoint);
}

// Validates that a companyId is a real value (not empty/'undefined'/'null')
function isValidCompanyId(companyId: string | undefined | null): boolean {
  if (!companyId) return false;
  const trimmed = companyId.trim();
  return trimmed !== '' && trimmed !== 'undefined' && trimmed !== 'null';
}

// Auth functions
interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  must_change_password: boolean;
  is_subaccount: boolean;
  parent_user_id: string | null;
  allowed_modules: string[];
  phone: string | null;
  language: string;
  theme: string;
  license_type: string;
  license_start_date: string | null;
  license_end_date: string | null;
  is_trial?: boolean;
  trial_start_date?: string | null;
  trial_end_date?: string | null;
  created_at: string;
  updated_at: string;
}

async function login(email: string, password: string): Promise<{ token: AuthResponse; user: User }> {
  const tokenResp = await apiRequest<AuthResponse>('POST', '/v1/auth/login', { email, password }, { skipAuth: true });
  setToken(tokenResp.access_token);
  setRefreshToken(tokenResp.refresh_token);
  // Fetch user data separately since login only returns tokens
  const userResp = await apiRequest<User>('GET', '/v1/auth/me');
  setUserCache(userResp);
  return { token: tokenResp, user: userResp };
}

async function register(data: {
  email: string;
  password: string;
  confirm_password: string;
  full_name: string;
  phone?: string;
  license_type?: string;
}): Promise<{ token: AuthResponse; user: User }> {
  const tokenResp = await apiRequest<AuthResponse>('POST', '/v1/auth/register', data, { skipAuth: true });
  setToken(tokenResp.access_token);
  setRefreshToken(tokenResp.refresh_token);
  // Fetch user data separately since register only returns UserResponse
  const userResp = await apiRequest<User>('GET', '/v1/auth/me');
  setUserCache(userResp);
  return { token: tokenResp, user: userResp };
}

async function getMe(): Promise<User> {
  const user = await apiGet<User>('/v1/auth/me');
  setUserCache(user);
  return user;
}

// Refresh single-flight: si varias peticiones reciben 401 a la vez, todas esperan
// la MISMA promesa de refresh. Sin esto, cada una refrescaba con el mismo refresh
// token y la rotación (replay detection) revocaba toda la cadena de sesiones,
// cerrando la sesión (visible sobre todo en el panel del administrador, que hace
// muchas llamadas paralelas).
let refreshPromise: Promise<boolean> | null = null;

async function refreshToken(): Promise<boolean> {
  const rt = getRefreshToken();
  if (!rt) return false;

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(buildUrl('/v1/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      setToken(data.access_token);
      if (data.refresh_token) {
        setRefreshToken(data.refresh_token);
      }
      return true;
    } catch {
      return false;
    } finally {
      // Permitir que el siguiente ciclo de 401 pueda refrescar de nuevo
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

function logout(): void {
  clearTokens();
}

async function forgotPassword(data: {
  email: string;
  full_name?: string;
  phone?: string;
}): Promise<{ message: string }> {
  return apiPost<{ message: string }>('/v1/auth/forgot-password', data, { skipAuth: true });
}

async function forceChangePassword(data: {
  new_password: string;
  confirm_new_password: string;
}): Promise<AuthResponse> {
  const tokenResp = await apiPost<AuthResponse>('/v1/auth/force-change-password', data);
  setToken(tokenResp.access_token);
  if (tokenResp.refresh_token) setRefreshToken(tokenResp.refresh_token);
  return tokenResp;
}

async function adminResetUserPassword(
  userId: string,
  data: { temporary_password?: string; send_email?: boolean }
): Promise<{ message: string; user_id: string; temporary_password: string; must_change_password: boolean }> {
  return apiPost(`/v1/admin/users/${userId}/reset-password`, data);
}

async function updateUserProfile(data: Partial<{ full_name: string; phone: string; language: string; theme: string }>): Promise<User> {
  const user = await apiPut<User>('/v1/auth/me', data);
  setUserCache(user);
  return user;
}

// Company CRUD
interface Company {
  id: string;
  user_id: string;
  ruc: string;
  razon_social: string;
  nombre_comercial: string | null;
  dir_matriz: string;
  dir_establecimiento: string | null;
  cod_establecimiento: string;
  cod_punto_emision: string;
  contribuyente_especial: string | null;
  obligado_contabilidad: string;
  tipo_ambiente: string;
  tipo_emision: string;
  rise: string | null;
  agente_retencion: string | null;
  contribuyente_rimpe: string | null;
  logo_path: string | null;
  // Contacto
  correo: string | null;
  telefono: string | null;
  // Firma electronica
  firma_electronica_path: string | null;
  // Registro turistico
  registro_turistico: boolean;
  // Operadora Transportista
  operadora_transportista_comercial: boolean;
  operadora_transportista_ligera: boolean;
  ruc_operadora_comercial: string | null;
  ruc_operadora_transportista: string | null;
  // Informacion adicional
  codigo_artesano: string | null;
  nombre_recibos: string | null;
  // SMTP por empresa
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_protocol: string | null;
  smtp_ssl: boolean;
  // Ambiente por empresa
  environment_mode: string;
  // VirusTotal por empresa
  virustotal_enabled: boolean;
  // Estado
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

async function getCompanies(): Promise<Company[]> {
  return apiGet<Company[]>('/v1/companies');
}

async function getCompany(id: string): Promise<Company> {
  return apiGet<Company>(`/v1/companies/${id}`);
}

async function createCompany(data: Partial<Company>): Promise<Company> {
  return apiPost<Company>('/v1/companies', data);
}

async function uploadCompanyFile(type: 'logo' | 'firma', file: File): Promise<{ file_path: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const token = getToken();
  const response = await fetch(buildUrl('/v1/companies/upload/' + type), {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al subir archivo' }));
    throw new Error(typeof errorData.detail === 'string' ? errorData.detail : 'Error al subir archivo');
  }

  return response.json();
}

async function updateCompany(id: string, data: Partial<Company>): Promise<Company> {
  return apiPut<Company>(`/v1/companies/${id}`, data);
}

async function deleteCompany(id: string): Promise<void> {
  return apiDelete<void>(`/v1/companies/${id}`);
}

// Company config (per-company settings)
export interface CompanyConfig {
  id: string;
  ruc: string;
  razon_social: string;
  nombre_comercial: string | null;
  logo_path: string | null;
  firma_electronica_path: string | null;
  correo: string | null;
  telefono: string | null;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_protocol: string | null;
  smtp_ssl: boolean;
  environment_mode: string;
  virustotal_enabled: boolean;
}

async function getCompanyConfig(companyId: string): Promise<CompanyConfig> {
  return apiGet<CompanyConfig>(`/v1/config/companies/${companyId}`);
}

async function updateCompanyConfig(companyId: string, data: Partial<CompanyConfig>): Promise<{ message: string }> {
  return apiPut<{ message: string }>(`/v1/config/companies/${companyId}`, data);
}

async function getClamavStatus(force = false): Promise<{ clamav_available: boolean; cached: boolean }> {
  return apiGet<{ clamav_available: boolean; cached: boolean }>(`/v1/config/clamav-status?force=${force}`);
}

interface SRICompanyData {
  ruc: string;
  razon_social: string;
  nombre_comercial: string;
  dir_matriz: string;
  cod_establecimiento: string;
  cod_punto_emision: string;
  obligado_contabilidad: string;
  contribuyente_especial: string;
  message?: string;
}

async function lookupRuc(ruc: string): Promise<SRICompanyData> {
  return apiGet<SRICompanyData>(`/v1/companies/ruc/${ruc}`);
}

// SRI Catalog functions
// All SRI catalogs are served from a single endpoint: /api/sri/catalogs
interface SRICatalog {
  codigo: string;
  descripcion: string;
  // Algunos catálogos (p.ej. tipos de identificación) pueden enviar 'nombre'
  nombre?: string;
}

interface SRIIVARate {
  codigo: string;
  codigo_porcentaje: string;
  porcentaje: number;
  descripcion: string;
}

interface SRIDocumentType {
  codigo: string;
  descripcion: string;
}

interface SRICodeName {
  codigo: string;
  nombre: string;
}

interface SRICatalogsResponse {
  iva_tarifas: SRIIVARate[];
  ice_tarifas: SRICatalog[];
  retencion_iva: SRICatalog[];
  retencion_renta: SRICatalog[];
  tipos_comprobante: SRIDocumentType[];
  tipos_identificacion: SRICatalog[];
  formas_pago: SRICatalog[];
  estados_comprobante: SRICatalog[];
  contribuyente_tipos: SRICodeName[];
  regimen_tipos: SRICodeName[];
}

// Cached SRI catalogs
let _sriCatalogsCache: SRICatalogsResponse | null = null;

async function getSRICatalogsData(): Promise<SRICatalogsResponse> {
  if (_sriCatalogsCache) return _sriCatalogsCache;
  const data = await apiGet<SRICatalogsResponse>('/sri/catalogs');
  _sriCatalogsCache = data;
  return data;
}

async function getSRITipoImpuesto(): Promise<SRICatalog[]> {
  // Not a separate endpoint - return from full catalogs
  const catalogs = await getSRICatalogsData();
  return catalogs.iva_tarifas.map(t => ({ codigo: t.codigo_porcentaje, descripcion: t.descripcion }));
}

async function getSRIIVARates(): Promise<SRIIVARate[]> {
  const catalogs = await getSRICatalogsData();
  return catalogs.iva_tarifas;
}

async function getSRIDocumentTypes(): Promise<SRIDocumentType[]> {
  const catalogs = await getSRICatalogsData();
  return catalogs.tipos_comprobante;
}

async function getSRITipoIdentificacion(): Promise<SRICatalog[]> {
  const catalogs = await getSRICatalogsData();
  return catalogs.tipos_identificacion;
}

async function getSRIMoneda(): Promise<SRICatalog[]> {
  // SRI only uses USD - not in catalogs endpoint
  return [{ codigo: 'DOLAR', descripcion: 'Dólar estadounidense' }];
}

async function getSRIFormaPago(): Promise<SRICatalog[]> {
  const catalogs = await getSRICatalogsData();
  return catalogs.formas_pago;
}

// Admin dashboard functions
interface AdminStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  total_companies: number;
  total_clients: number;
  expiring_licenses: number;
  expired_licenses: number;
  trial_users: number;
  trial_users_total: number;
  license_distribution: Record<string, number>;
}

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  is_trial: boolean;
  phone: string | null;
  language: string;
  theme: string;
  license_type: string;
  license_start_date: string | null;
  license_end_date: string | null;
  trial_end_date: string | null;
  created_at: string;
  updated_at: string;
}

interface SecurityIssue {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  detected_at: string;
  resolved: boolean;
}

async function getAdminStats(): Promise<AdminStats> {
  return apiGet<AdminStats>('/v1/admin/dashboard');
}

async function getAdminUsers(): Promise<AdminUser[]> {
  return apiGet<AdminUser[]>('/v1/admin/users');
}

async function modifyUserLicense(userId: string, data: { license_type: string }): Promise<{ message: string; user_id: string; license_type: string; license_end_date: string }> {
  return apiPut<{ message: string; user_id: string; license_type: string; license_end_date: string }>(`/v1/admin/users/${userId}/license?license_type=${data.license_type}`);
}

async function toggleUserActive(userId: string, isActive: boolean): Promise<{ message: string }> {
  return apiPut<{ message: string }>(`/v1/admin/users/${userId}/active?is_active=${isActive}`);
}

// Trial management functions
async function modifyUserTrial(userId: string, trialDays: number): Promise<{ message: string; user_id: string; trial_start_date: string; trial_end_date: string; trial_days: number }> {
  return apiPut<{ message: string; user_id: string; trial_start_date: string; trial_end_date: string; trial_days: number }>(`/v1/admin/users/${userId}/trial?trial_days=${trialDays}`);
}

async function endUserTrial(userId: string): Promise<{ message: string; user_id: string }> {
  return apiPut<{ message: string; user_id: string }>(`/v1/admin/users/${userId}/end-trial`);
}

async function getTrialUsers(): Promise<{ trial_users: Array<{ id: string; email: string; full_name: string; is_active: boolean; trial_start_date: string | null; trial_end_date: string | null; trial_days_remaining: number }> }> {
  return apiGet('/v1/admin/trial-users');
}

async function getSystemHealth(): Promise<{
  system: Record<string, unknown>;
  database: Record<string, unknown>;
  application: Record<string, unknown>;
}> {
  return apiGet('/v1/admin/system-health');
}

async function getSecurityIssues(): Promise<{
  expired_active_licenses: Array<{ user_id: string; email: string; full_name: string; license_end_date: string | null; days_expired: number | null }>;
  users_without_config: Array<{ user_id: string; email: string; full_name: string; reason?: string; reason_label?: string }>;
}> {
  return apiGet('/v1/admin/security-issues');
}

// License functions
interface LicenseStatus {
  license_type: string | null;
  license_start_date: string | null;
  license_end_date: string | null;
  is_expired: boolean;
  license_expired: boolean;
  days_remaining: number | null;
  is_active: boolean;
  // Trial info
  is_trial: boolean;
  trial_start_date: string | null;
  trial_end_date: string | null;
  trial_days_remaining: number | null;
  // Trial/License active flags
  trial_active: boolean;
  license_active: boolean;
  license_days_remaining: number | null;
}

interface LicenseOptions {
  options: Array<{ type: string; price: number; months: number; label: string }>;
  currency: string;
  contact_whatsapp: string;
}

async function getLicenseStatus(): Promise<LicenseStatus> {
  return apiGet<LicenseStatus>('/v1/licenses/status');
}

async function getLicenseOptions(): Promise<LicenseOptions> {
  return apiGet<LicenseOptions>('/v1/licenses/options');
}

async function renewLicenseViaWhatsApp(licenseType: string): Promise<{ whatsapp_url: string; license_type: string; price: number; label: string; message: string }> {
  return apiPost<{ whatsapp_url: string; license_type: string; price: number; label: string; message: string }>(`/v1/licenses/renew-whatsapp?license_type=${licenseType}`);
}

async function checkLicenseExpiry(): Promise<{ alert: boolean; message: string | null; days_remaining: number; license_end_date: string }> {
  return apiGet('/v1/licenses/check-expiry');
}

async function checkFeatureAccess(featureName: string): Promise<{ feature: string; has_access: boolean; current_tier: string | null; minimum_tier_required: string | null; message: string }> {
  return apiGet(`/v1/licenses/feature/${featureName}`);
}

async function checkLicenseLimit(limitType: string, companyId?: string): Promise<{ limit_type: string; max: number; current: number; available: number; is_at_limit: boolean; company_id?: string; period?: string }> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet(`/v1/licenses/check-limit/${limitType}${qs}`);
}

// Backup functions
interface BackupInfo {
  filename: string;
  size_bytes: number;
  created_at: string;
}

interface BackupListResponse {
  backups: BackupInfo[];
}

interface CreateBackupResponse {
  message: string;
  filename: string;
  size_bytes: number;
  timestamp: string;
}

interface RestoreBackupResponse {
  message: string;
  backup_version: string;
  backup_timestamp: string;
  companies: {
    total_in_backup: number;
    created: number;
    updated: number;
    skipped: number;
  };
  clients: {
    total_in_backup: number;
    created: number;
    updated: number;
    skipped: number;
  };
  products?: {
    total_in_backup: number;
    created: number;
    updated: number;
    skipped: number;
  };
}

async function getBackups(): Promise<BackupInfo[]> {
  const response = await apiGet<BackupListResponse>('/v1/backup/list');
  return response.backups;
}

async function createBackup(): Promise<CreateBackupResponse> {
  return apiPost<CreateBackupResponse>('/v1/backup/create');
}

async function downloadBackup(filename: string): Promise<Blob> {
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/backup/download/${encodeURIComponent(filename)}`), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) throw new Error('Error al descargar respaldo');
  return response.blob();
}

async function restoreBackup(file: File): Promise<RestoreBackupResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(buildUrl('/v1/backup/restore'), {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al restaurar respaldo' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

// Use ComprobanteStatsResponse for dashboard stats (matches backend response)
// Re-exported from the comprobante types above

// Config / Settings functions
interface UserConfig {
  id: string;
  user_id: string;
  environment_mode: 'sandbox' | 'production';
  virustotal_enabled: boolean;
  has_digital_signature: boolean;
  has_backup_key: boolean;
  signature_status: 'none' | 'valid' | 'expired' | 'expiring_soon' | 'uploaded';
  signature_expiry_date: string | null;
  signature_days_left: number | null;
  has_smtp_config: boolean;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_ssl: boolean;
  smtp_protocol: string | null;
  company_logo_path: string | null;
  user: {
    id: string;
    email: string;
    full_name: string;
    phone: string | null;
    language: string;
    theme: string;
    license_type: string;
    license_start_date: string | null;
    license_end_date: string | null;
  };
  clamav_available: boolean;
  virustotal_available: boolean;
}

interface SignatureValidation {
  is_valid: boolean;
  is_expired: boolean;
  is_not_yet_valid: boolean;
  is_ec_signature: boolean;
  subject: Record<string, string>;
  issuer: Record<string, string>;
  issuer_cn: string;
  serial_number: string;
  not_before: string;
  not_after: string;
  days_until_expiry: number | null;
  has_private_key: boolean;
  additional_certs_count: number;
  warnings: string[];
}

async function getUserConfig(): Promise<UserConfig> {
  return apiGet<UserConfig>('/v1/config/user-config');
}

async function uploadDigitalSignature(file: File, password: string): Promise<{ message: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('password', password);
  const token = getToken();
  const response = await fetch(buildUrl('/v1/config/digital-signature'), {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al subir firma' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

async function getSignatureStatus(): Promise<{
  has_signature: boolean;
  status: 'none' | 'valid' | 'expired' | 'expiring_soon' | 'uploaded';
  expiry_date: string | null;
  days_left: number | null;
}> {
  return apiGet('/v1/config/signature-status');
}

async function toggleVirusTotal(enabled: boolean): Promise<{ message: string }> {
  return apiPut<{ message: string }>(`/v1/config/virustotal?enabled=${enabled}`);
}

async function configureSMTP(data: {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  smtp_protocol: string;
  smtp_ssl: boolean;
}): Promise<{ message: string }> {
  return apiPost<{ message: string }>('/v1/config/smtp', data);
}

async function testSMTP(companyId?: string): Promise<{ message: string; success: boolean }> {
  const url = companyId
    ? `/v1/config/test-smtp?company_id=${companyId}`
    : '/v1/config/test-smtp';
  return apiPost<{ message: string; success: boolean }>(url);
}

async function switchEnvironmentMode(mode: 'sandbox' | 'production'): Promise<{ message: string }> {
  return apiPut<{ message: string }>(`/v1/config/environment-mode?mode=${mode}`);
}

async function updateProfile(data: {
  full_name?: string;
  phone?: string;
  language?: string;
  theme?: string;
}): Promise<{ message: string }> {
  return apiPut<{ message: string }>('/v1/config/profile', data);
}

async function setBackupKey(key: string): Promise<{ message: string }> {
  return apiPost<{ message: string }>('/v1/config/backup-key', { key });
}

async function changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
  return apiPut<{ message: string }>('/v1/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_new_password: newPassword,
  });
}

async function getCompanyLogoBlobUrl(): Promise<string | null> {
  // Descarga el logo autenticado y devuelve una URL de objeto para <img>
  const token = getToken();
  if (!token) return null;
  try {
    const response = await fetch(buildUrl('/v1/config/company-logo'), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return null;
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch {
    return null;
  }
}

async function uploadCompanyLogo(file: File): Promise<{ message: string; logo_path: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(buildUrl('/v1/config/company-logo'), {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al subir logo' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

async function deleteDigitalSignature(): Promise<{ message: string }> {
  return apiDelete<{ message: string }>('/v1/config/digital-signature');
}

async function getSignatureInfo(): Promise<SignatureValidation> {
  return apiGet<SignatureValidation>('/v1/config/signature-info');
}

async function deleteCompanyLogo(): Promise<{ message: string }> {
  return apiDelete<{ message: string }>('/v1/config/company-logo');
}

async function validateSignature(file: File, password: string): Promise<SignatureValidation> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('password', password);
  const token = getToken();
  const response = await fetch(buildUrl('/v1/uploads/validate-signature'), {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al validar firma' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

// ============ COMPROBANTE TYPES ============

interface ComprobanteDetalleCreate {
  product_id?: string;
  codigo_principal: string;
  codigo_auxiliar?: string;
  descripcion: string;
  cantidad: number;
  unidad_medida?: string;
  precio_unitario: number;
  /** Monto de descuento efectivo en dólares (calculado) */
  descuento?: number;
  /** Tipo de descuento: 'porcentaje' (% del total de la línea) o 'dolares' (monto fijo) */
  descuento_tipo?: 'porcentaje' | 'dolares';
  /** Valor bruto del descuento ingresado por el usuario */
  descuento_valor?: number;
  /** Valor del impuesto IRBPNR por unidad (para botellas plásticas) */
  irbpnr_valor?: number;
  iva_codigo: string;
  iva_porcentaje: number;
  ice_codigo?: string;
  ice_porcentaje?: number;
}

interface ComprobanteCreate {
  company_id: string;
  client_id: string;
  tipo_comprobante: string;
  forma_pago?: string;
  detalles: ComprobanteDetalleCreate[];
  comprobante_modificado_id?: string;
  motivo_modificacion?: string;
  retencion_iva_codigo?: string;
  retencion_iva_porcentaje?: number;
  retencion_renta_codigo?: string;
  retencion_renta_porcentaje?: number;
  info_adicional?: Record<string, string>;
}

interface ComprobanteDetalleResponse {
  id: string;
  product_id: string | null;
  codigo_principal: string;
  codigo_auxiliar: string | null;
  descripcion: string;
  cantidad: number;
  unidad_medida: string;
  precio_unitario: number;
  descuento: number;
  precio_total_sin_impuestos: number;
  iva_codigo: string;
  iva_porcentaje: number;
  iva_valor: number;
  ice_codigo: string | null;
  ice_porcentaje: number | null;
  ice_valor: number | null;
}

interface ComprobanteResponse {
  id: string;
  company_id: string;
  client_id: string;
  tipo_comprobante: string;
  secuencial: string;
  clave_acceso: string | null;
  fecha_emision: string;
  estado: string;
  ambiente: string;
  cliente_tipo_identificacion: string;
  cliente_identificacion: string;
  cliente_razon_social: string;
  subtotal_sin_impuestos: number;
  subtotal_iva_0: number;
  subtotal_iva_5: number;
  subtotal_iva_8: number;
  subtotal_iva_12: number;
  subtotal_iva_13: number;
  subtotal_iva_14: number;
  subtotal_iva_15: number;
  subtotal_no_objeto_iva: number;
  subtotal_exento_iva: number;
  total_iva: number;
  total_ice: number;
  total_descuento: number;
  total_con_impuestos: number;
  forma_pago: string | null;
  numero_autorizacion: string | null;
  fecha_autorizacion: string | null;
  sri_mensaje: string | null;
  detalles: ComprobanteDetalleResponse[];
  created_at: string;
  updated_at: string;
}

interface ComprobanteListResponse {
  id: string;
  tipo_comprobante: string;
  secuencial: string;
  clave_acceso: string | null;
  fecha_emision: string;
  estado: string;
  cliente_razon_social: string;
  total_con_impuestos: number;
  numero_autorizacion: string | null;
  created_at: string;
}

interface ComprobanteStatsResponse {
  total: number;
  borrador: number;
  firmado: number;
  enviado: number;
  autorizado: number;
  rechazado: number;
  total_amount: number;
}

// Product types
interface ProductCreate {
  company_id: string;
  codigo_principal: string;
  codigo_auxiliar?: string;
  descripcion: string;
  tipo: string;
  precio_unitario: number;
  iva_codigo: string;
  iva_porcentaje: number;
  iva_incluido?: boolean;
  ice_codigo?: string;
  ice_porcentaje?: number;
  valor_ice_unitario?: number;
  valor_irbpnr?: number;
  subsidio?: number;
  categoria?: string;
  detalle?: string;
  imagen?: string;
  unidad_medida?: string;
  descuento?: number;
}

interface ProductResponse {
  id: string;
  company_id: string;
  codigo_principal: string;
  codigo_auxiliar: string | null;
  descripcion: string;
  tipo: string;
  precio_unitario: number;
  iva_codigo: string;
  iva_porcentaje: number;
  iva_incluido: boolean | null;
  ice_codigo: string | null;
  ice_porcentaje: number | null;
  valor_ice_unitario: number | null;
  valor_irbpnr: number | null;
  subsidio: number | null;
  categoria: string | null;
  detalle: string | null;
  imagen: string | null;
  unidad_medida: string;
  descuento: number;
  is_active: boolean;
  created_at: string;
}

// Client types
interface ClientCreate {
  company_id: string;
  tipo_identificacion: string;
  identificacion: string;
  razon_social: string;
  direccion?: string;
  email?: string;
  telefono?: string;
}

interface ClientResponse {
  id: string;
  company_id: string;
  tipo_identificacion: string;
  identificacion: string;
  razon_social: string;
  direccion: string | null;
  email: string | null;
  telefono: string | null;
  is_default_consumer: boolean;
  is_active: boolean;
  created_at: string;
}

// ============ COMPROBANTE API FUNCTIONS ============

async function getComprobantes(params?: {
  company_id?: string;
  tipo_comprobante?: string;
  estado?: string;
  skip?: number;
  limit?: number;
}): Promise<ComprobanteListResponse[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.tipo_comprobante) query.push(`tipo_comprobante=${params.tipo_comprobante}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  if (params?.skip !== undefined) query.push(`skip=${params.skip}`);
  if (params?.limit !== undefined) query.push(`limit=${params.limit}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<ComprobanteListResponse[]>(`/v1/comprobantes${qs}`);
}

async function getComprobante(id: string): Promise<ComprobanteResponse> {
  return apiGet<ComprobanteResponse>(`/v1/comprobantes/${id}`);
}

async function createComprobante(data: ComprobanteCreate): Promise<ComprobanteResponse> {
  return apiPost<ComprobanteResponse>('/v1/comprobantes', data);
}

async function firmarComprobante(id: string): Promise<unknown> {
  return apiPost(`/v1/comprobantes/${id}/firmar`);
}

async function enviarComprobanteSRI(id: string): Promise<unknown> {
  return apiPost(`/v1/comprobantes/${id}/enviar`);
}

async function consultarComprobanteSRI(id: string): Promise<unknown> {
  return apiPost(`/v1/comprobantes/${id}/consultar`);
}

// Recuperar un comprobante enviado al SRI (válido dentro de 72h desde su emisión)
async function recuperarComprobanteSRI(id: string): Promise<{
  message: string;
  comprobante_id: string;
  estado: string;
  secuencial: string;
  clave_acceso: string | null;
  sri_mensaje: string | null;
  numero_autorizacion: string | null;
  fecha_autorizacion: string | null;
}> {
  return apiPost(`/v1/comprobantes/${id}/recuperar`);
}

async function getComprobanteXML(id: string): Promise<{ comprobante_id: string; tipo_comprobante: string; secuencial: string; clave_acceso: string | null; estado: string; xml_content: string | null; is_signed: boolean; message?: string }> {
  return apiGet(`/v1/comprobantes/${id}/xml`);
}

async function deleteComprobante(id: string): Promise<void> {
  return apiDelete(`/v1/comprobantes/${id}`);
}

async function getComprobanteStats(companyId?: string): Promise<ComprobanteStatsResponse> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<ComprobanteStatsResponse>(`/v1/comprobantes/stats${qs}`);
}

// RIDE (Representación Impresa de Documento Electrónico) PDF download
async function downloadRIDE(id: string): Promise<Blob> {
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/comprobantes/${id}/ride`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error al descargar RIDE');
  return response.blob();
}

// Send comprobante by email (only for AUTORIZADO)
async function enviarComprobanteEmail(id: string): Promise<{ message: string }> {
  return apiPost(`/v1/comprobantes/${id}/enviar-email`);
}

// 1-click process: enviar + consultar SRI (only for FIRMADO)
async function procesarComprobante(id: string): Promise<{
  message: string;
  comprobante_id: string;
  estado: string;
  secuencial: string;
  clave_acceso: string | null;
  sri_mensaje: string | null;
  numero_autorizacion: string | null;
  fecha_autorizacion: string | null;
}> {
  return apiPost(`/v1/comprobantes/${id}/procesar`);
}

// SRI Pre-validation (only for BORRADOR)
interface ValidationIssue {
  field: string;
  message: string;
}

interface ValidationResult {
  valid: boolean;
  errors: Array<ValidationIssue>;
  warnings: Array<ValidationIssue>;
}

async function validarComprobante(id: string): Promise<ValidationResult> {
  return apiPost(`/v1/comprobantes/${id}/validar`);
}

// Correct rejected comprobante (only for RECHAZADO)
interface CorreccionComprobante {
  detalles?: ComprobanteDetalleCreate[];
  info_adicional?: Record<string, string>;
  forma_pago?: string;
  motivo_modificacion?: string;
}

async function corregirComprobante(id: string, data: CorreccionComprobante): Promise<ComprobanteResponse> {
  return apiPost(`/v1/comprobantes/${id}/corregir`, data);
}

// ============ PRODUCT API FUNCTIONS ============

async function getProducts(companyId?: string): Promise<ProductResponse[]> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<ProductResponse[]>(`/v1/products${qs}`);
}

async function createProduct(data: ProductCreate): Promise<ProductResponse> {
  return apiPost<ProductResponse>('/v1/products', data);
}

async function updateProduct(id: string, data: Partial<ProductCreate>): Promise<ProductResponse> {
  return apiPut<ProductResponse>(`/v1/products/${id}`, data);
}

async function deleteProduct(id: string): Promise<void> {
  return apiDelete(`/v1/products/${id}`);
}

// ============ CLIENT API FUNCTIONS ============

async function getClients(companyId: string): Promise<ClientResponse[]> {
  if (!isValidCompanyId(companyId)) {
    return [];
  }
  return apiGet<ClientResponse[]>(`/v1/clients?company_id=${encodeURIComponent(companyId.trim())}`);
}

async function createClient(data: ClientCreate): Promise<ClientResponse> {
  return apiPost<ClientResponse>('/v1/clients', data);
}

async function updateClient(id: string, data: Partial<ClientCreate>): Promise<ClientResponse> {
  return apiPut<ClientResponse>(`/v1/clients/${id}`, data);
}

async function deleteClient(id: string): Promise<void> {
  return apiDelete(`/v1/clients/${id}`);
}

// ============ PROFORMA TYPES ============

interface ProformaDetalleCreate {
  product_id?: string;
  codigo_principal: string;
  codigo_auxiliar?: string;
  descripcion: string;
  cantidad: number;
  unidad_medida?: string;
  precio_unitario: number;
  /** Monto de descuento efectivo en dólares (calculado) */
  descuento?: number;
  /** Tipo de descuento: 'porcentaje' (% del total de la línea) o 'dolares' (monto fijo) */
  descuento_tipo?: 'porcentaje' | 'dolares';
  /** Valor bruto del descuento ingresado por el usuario */
  descuento_valor?: number;
  /** Valor del impuesto IRBPNR por unidad (para botellas plásticas) */
  irbpnr_valor?: number;
  iva_codigo: string;
  iva_porcentaje: number;
  ice_codigo?: string;
  ice_porcentaje?: number;
}

interface ProformaCreate {
  company_id: string;
  client_id?: string;
  detalles: ProformaDetalleCreate[];
  observaciones?: string;
  forma_pago?: string;
  fecha_validez?: string;
  info_adicional?: Record<string, string>;
  propina?: number;
}

interface ProformaDetalleResponse {
  id: string;
  product_id: string | null;
  codigo_principal: string;
  codigo_auxiliar: string | null;
  descripcion: string;
  cantidad: number;
  unidad_medida: string;
  precio_unitario: number;
  descuento: number;
  precio_total_sin_impuestos: number;
  iva_codigo: string;
  iva_porcentaje: number;
  iva_valor: number;
  ice_codigo: string | null;
  ice_porcentaje: number | null;
  ice_valor: number | null;
}

interface ProformaResponse {
  id: string;
  company_id: string;
  client_id: string | null;
  secuencial: string;
  fecha_emision: string;
  fecha_validez: string | null;
  estado: string;
  cliente_tipo_identificacion: string;
  cliente_identificacion: string;
  cliente_razon_social: string;
  cliente_direccion: string | null;
  cliente_email: string | null;
  cliente_telefono: string | null;
  subtotal_sin_impuestos: number;
  subtotal_iva_0: number;
  subtotal_iva_5: number;
  subtotal_iva_8: number;
  subtotal_iva_12: number;
  subtotal_iva_13: number;
  subtotal_iva_14: number;
  subtotal_iva_15: number;
  subtotal_no_objeto_iva: number;
  subtotal_exento_iva: number;
  total_iva: number;
  total_ice: number;
  total_descuento: number;
  total_con_impuestos: number;
  forma_pago: string | null;
  observaciones: string | null;
  propina: number;
  info_adicional: Record<string, string> | null;
  comprobante_convertido_id: string | null;
  detalles: ProformaDetalleResponse[];
  created_at: string;
  updated_at: string;
}

interface ProformaListResponse {
  id: string;
  secuencial: string;
  fecha_emision: string;
  fecha_validez: string | null;
  estado: string;
  cliente_razon_social: string;
  total_con_impuestos: number;
  comprobante_convertido_id: string | null;
  created_at: string;
}

interface ProformaStatsResponse {
  total: number;
  borrador: number;
  cerrada: number;
  enviada: number;
  aceptada: number;
  rechazada: number;
  convertida: number;
}

// ============ PROFORMA API FUNCTIONS ============

async function getProformas(params?: {
  company_id?: string;
  estado?: string;
  skip?: number;
  limit?: number;
}): Promise<ProformaListResponse[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  if (params?.skip !== undefined) query.push(`skip=${params.skip}`);
  if (params?.limit !== undefined) query.push(`limit=${params.limit}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<ProformaListResponse[]>(`/v1/proformas${qs}`);
}

async function getProforma(id: string): Promise<ProformaResponse> {
  return apiGet<ProformaResponse>(`/v1/proformas/${id}`);
}

async function createProforma(data: ProformaCreate): Promise<ProformaResponse> {
  return apiPost<ProformaResponse>('/v1/proformas', data);
}

async function updateProforma(id: string, data: Partial<ProformaCreate>): Promise<ProformaResponse> {
  return apiPut<ProformaResponse>(`/v1/proformas/${id}`, data);
}

async function deleteProforma(id: string): Promise<void> {
  return apiDelete(`/v1/proformas/${id}`);
}

async function getProformaStats(companyId?: string): Promise<ProformaStatsResponse> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<ProformaStatsResponse>(`/v1/proformas/stats${qs}`);
}

async function enviarProforma(id: string): Promise<{ message: string; estado: string; email_sent?: boolean; download_available?: boolean }> {
  return apiPost(`/v1/proformas/${id}/enviar`);
}

async function convertirProforma(id: string): Promise<{ message: string; comprobante_id: string; secuencial: string }> {
  return apiPost(`/v1/proformas/${id}/convertir`);
}

async function downloadProformaPDF(id: string): Promise<Blob> {
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/proformas/${id}/pdf`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error al descargar proforma PDF');
  return response.blob();
}

// ============ SRI CATALOGS ============

// Get all SRI catalogs in one call
async function getSRICatalogs(): Promise<SRICatalogsResponse> {
  return getSRICatalogsData();
}

// ============ KARDEX (INVENTORY) TYPES ============
interface KardexMovement {
  id: string;
  company_id: string;
  product_id: string;
  tipo_movimiento: string; // entrada, salida, ajuste
  cantidad: number;
  costo_unitario: number;
  costo_total: number;
  saldo_cantidad: number;
  saldo_valor: number;
  referencia_tipo: string | null;
  referencia_id: string | null;
  referencia_secuencial: string | null;
  detalle: string | null;
  fecha_movimiento: string;
  is_active: boolean;
  created_at: string;
}

interface KardexCreate {
  company_id: string;
  product_id: string;
  tipo_movimiento: string;
  cantidad: number;
  costo_unitario: number;
  referencia_tipo?: string;
  referencia_id?: string;
  referencia_secuencial?: string;
  detalle?: string;
}

interface KardexSaldo {
  product_id: string;
  saldo_cantidad: number;
  saldo_valor: number;
  costo_promedio: number;
}

interface KardexAjuste {
  company_id: string;
  product_id: string;
  tipo_ajuste: string; // positivo, negativo
  cantidad: number;
  costo_unitario: number;
  detalle: string;
}

// Kardex API functions
async function getKardexMovements(params?: { company_id?: string; product_id?: string; tipo_movimiento?: string; fecha_desde?: string; fecha_hasta?: string; skip?: number; limit?: number }): Promise<KardexMovement[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.product_id) query.push(`product_id=${params.product_id}`);
  if (params?.tipo_movimiento) query.push(`tipo_movimiento=${params.tipo_movimiento}`);
  if (params?.fecha_desde) query.push(`fecha_desde=${params.fecha_desde}`);
  if (params?.fecha_hasta) query.push(`fecha_hasta=${params.fecha_hasta}`);
  if (params?.skip !== undefined) query.push(`skip=${params.skip}`);
  if (params?.limit !== undefined) query.push(`limit=${params.limit}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<KardexMovement[]>(`/v1/kardex${qs}`);
}

async function getProductKardex(productId: string): Promise<KardexMovement[]> {
  return apiGet<KardexMovement[]>(`/v1/kardex/product/${productId}`);
}

async function getProductSaldo(productId: string): Promise<KardexSaldo> {
  return apiGet<KardexSaldo>(`/v1/kardex/product/${productId}/saldo`);
}

async function createKardexMovement(data: KardexCreate): Promise<KardexMovement> {
  return apiPost<KardexMovement>('/v1/kardex', data);
}

async function createKardexAjuste(data: KardexAjuste): Promise<KardexMovement> {
  return apiPost<KardexMovement>('/v1/kardex/ajuste', data);
}

// ============ EMPLOYEE (HR) TYPES ============
interface Employee {
  id: string;
  company_id: string;
  cedula: string;
  apellidos: string;
  nombres: string;
  nombre_completo: string;
  fecha_nacimiento: string | null;
  genero: string | null;
  estado_civil: string | null;
  direccion: string | null;
  telefono: string | null;
  email: string | null;
  cargo: string;
  departamento: string | null;
  tipo_contrato: string;
  fecha_ingreso: string;
  fecha_salida: string | null;
  estado: string;
  tipo_pago: string;
  sueldo_mensual: number;
  sueldo_diario: number;
  horas_trabajo_semanal: number;
  fondo_reserva: boolean;
  decimo_tercero_acumulado: number;
  decimo_cuarto_acumulado: number;
  vacaciones_acumuladas_dias: number;
  fondos_reserva_acumulado: number;
  iess_afiliado: boolean;
  iess_numero_seguro: string | null;
  banco: string | null;
  tipo_cuenta: string | null;
  numero_cuenta: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface EmployeeCreate {
  company_id: string;
  cedula: string;
  apellidos: string;
  nombres: string;
  fecha_nacimiento?: string;
  genero?: string;
  estado_civil?: string;
  direccion?: string;
  telefono?: string;
  email?: string;
  cargo: string;
  departamento?: string;
  tipo_contrato: string;
  fecha_ingreso: string;
  tipo_pago?: string;
  sueldo_mensual: number;
  horas_trabajo_semanal?: number;
  fondo_reserva?: boolean;
  iess_afiliado?: boolean;
  iess_numero_seguro?: string;
  banco?: string;
  tipo_cuenta?: string;
  numero_cuenta?: string;
}

interface EmployeeUpdate {
  apellidos?: string;
  nombres?: string;
  fecha_nacimiento?: string;
  genero?: string;
  estado_civil?: string;
  direccion?: string;
  telefono?: string;
  email?: string;
  cargo?: string;
  departamento?: string;
  tipo_contrato?: string;
  tipo_pago?: string;
  sueldo_mensual?: number;
  horas_trabajo_semanal?: number;
  fondo_reserva?: boolean;
  iess_afiliado?: boolean;
  iess_numero_seguro?: string;
  banco?: string;
  tipo_cuenta?: string;
  numero_cuenta?: string;
}

interface EmployeeCese {
  fecha_salida: string;
  motivo?: string;
}

// Employee API functions
async function getEmployees(params?: { company_id?: string; estado?: string; departamento?: string }): Promise<Employee[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  if (params?.departamento) query.push(`departamento=${params.departamento}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<Employee[]>(`/v1/employees${qs}`);
}

async function getEmployee(id: string): Promise<Employee> {
  return apiGet<Employee>(`/v1/employees/${id}`);
}

async function createEmployee(data: EmployeeCreate): Promise<Employee> {
  return apiPost<Employee>('/v1/employees', data);
}

async function updateEmployee(id: string, data: EmployeeUpdate): Promise<Employee> {
  return apiPut<Employee>(`/v1/employees/${id}`, data);
}

async function deactivateEmployee(id: string): Promise<{ message: string }> {
  return apiDelete(`/v1/employees/${id}`);
}

async function recordEmployeeCese(id: string, data: EmployeeCese): Promise<Employee> {
  return apiPost<Employee>(`/v1/employees/${id}/cese`, data);
}

async function getEmployeeDepartments(companyId: string): Promise<Array<{ departamento: string; count: number }>> {
  if (!isValidCompanyId(companyId)) return [];
  return apiGet(`/v1/employees/departments?company_id=${encodeURIComponent(companyId.trim())}`);
}

// ============ PAYROLL TYPES ============
interface RolPagoDetalle {
  id: string;
  rol_pago_id: string;
  employee_id: string;
  employee_name: string;
  sueldo_base: number;
  horas_extras_diurnas: number;
  valor_horas_extras_diurnas: number;
  horas_extras_nocturnas: number;
  valor_horas_extras_nocturnas: number;
  horas_extras_dominicales: number;
  valor_horas_extras_dominicales: number;
  comisiones: number;
  bonos: number;
  otros_ingresos: number;
  total_ingresos: number;
  iess_personal_945: number;
  anticipo: number;
  prestamo_empresa: number;
  retencion_judicial: number;
  otros_descuentos: number;
  total_descuentos: number;
  iess_patronal_1115: number;
  iee_0005: number;
  secap_002: number;
  cenaces_001: number;
  total_aportes_empleador: number;
  decimo_tercero: number;
  decimo_cuarto: number;
  vacaciones_provision: number;
  fondos_reserva: number;
  liquido_recibir: number;
}

interface RolPago {
  id: string;
  company_id: string;
  periodo_mes: number;
  periodo_anio: number;
  fecha_pago: string | null;
  estado: string;
  total_remuneraciones: number;
  total_descuentos: number;
  total_empleador: number;
  total_liquido: number;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface RolPagoFull extends RolPago {
  detalles: RolPagoDetalle[];
}

interface PayrollGenerate {
  company_id: string;
  periodo_mes: number;
  periodo_anio: number;
  employee_ids?: string[];
}

// Payroll API functions
async function generatePayroll(data: PayrollGenerate): Promise<RolPagoFull> {
  return apiPost<RolPagoFull>('/v1/payroll/generate', data);
}

async function getPayrolls(params?: { company_id?: string; estado?: string; periodo_anio?: number }): Promise<RolPago[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  if (params?.periodo_anio) query.push(`periodo_anio=${params.periodo_anio}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<RolPago[]>(`/v1/payroll${qs}`);
}

async function getPayroll(id: string): Promise<RolPagoFull> {
  return apiGet<RolPagoFull>(`/v1/payroll/${id}`);
}

async function approvePayroll(id: string): Promise<{ message: string }> {
  return apiPut(`/v1/payroll/${id}/approve`);
}

async function payPayroll(id: string): Promise<{ message: string }> {
  return apiPut(`/v1/payroll/${id}/pay`);
}

async function getEmployeePayrollHistory(employeeId: string): Promise<RolPago[]> {
  return apiGet<RolPago[]>(`/v1/payroll/employee/${employeeId}`);
}

async function calculateDecimoTercero(data: { company_id: string; periodo_anio: number; employee_ids?: string[] }): Promise<unknown> {
  return apiPost('/v1/payroll/decimo-tercero', data);
}

async function calculateDecimoCuarto(data: { company_id: string; periodo_anio: number; region?: string; employee_ids?: string[] }): Promise<unknown> {
  return apiPost('/v1/payroll/decimo-cuarto', data);
}

async function getVacacionesBalance(employeeId: string): Promise<unknown> {
  return apiGet(`/v1/payroll/vacaciones/${employeeId}`);
}

async function getFondosReservaBalance(employeeId: string): Promise<unknown> {
  return apiGet(`/v1/payroll/fondos-reserva/${employeeId}`);
}

async function getIESSReport(params: { company_id: string; periodo_mes: number; periodo_anio: number }): Promise<unknown> {
  return apiGet(`/v1/payroll/iess/report?company_id=${params.company_id}&periodo_mes=${params.periodo_mes}&periodo_anio=${params.periodo_anio}`);
}

async function getRDEPReport(params: { company_id: string; periodo_anio: number }): Promise<unknown> {
  return apiGet(`/v1/payroll/rdep/report?company_id=${params.company_id}&periodo_anio=${params.periodo_anio}`);
}

// ============ SUPPLIER TYPES ============
interface Supplier {
  id: string;
  company_id: string;
  tipo_identificacion: string;
  identificacion: string;
  razon_social: string;
  nombre_comercial: string | null;
  direccion: string | null;
  email: string | null;
  telefono: string | null;
  contacto_nombre: string | null;
  contacto_telefono: string | null;
  forma_pago_habitual: string;
  plazo_credito_dias: number;
  retencion_iva_codigo: string | null;
  retencion_iva_porcentaje: number | null;
  retencion_renta_codigo: string | null;
  retencion_renta_porcentaje: number | null;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface SupplierCreate {
  company_id: string;
  tipo_identificacion: string;
  identificacion: string;
  razon_social: string;
  nombre_comercial?: string;
  direccion?: string;
  email?: string;
  telefono?: string;
  contacto_nombre?: string;
  contacto_telefono?: string;
  forma_pago_habitual?: string;
  plazo_credito_dias?: number;
  retencion_iva_codigo?: string;
  retencion_iva_porcentaje?: number;
  retencion_renta_codigo?: string;
  retencion_renta_porcentaje?: number;
  observaciones?: string;
  is_active?: boolean;
}

// Supplier API functions
async function getSuppliers(companyId?: string): Promise<Supplier[]> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<Supplier[]>(`/v1/suppliers${qs}`);
}

async function getSupplier(id: string): Promise<Supplier> {
  return apiGet<Supplier>(`/v1/suppliers/${id}`);
}

async function createSupplier(data: SupplierCreate): Promise<Supplier> {
  return apiPost<Supplier>('/v1/suppliers', data);
}

async function updateSupplier(id: string, data: Partial<SupplierCreate>): Promise<Supplier> {
  return apiPut<Supplier>(`/v1/suppliers/${id}`, data);
}

async function deleteSupplier(id: string): Promise<{ message: string }> {
  return apiDelete(`/v1/suppliers/${id}`);
}

// ============ PURCHASE ORDER TYPES ============
interface OrdenCompra {
  id: string;
  company_id: string;
  supplier_id: string;
  numero: string;
  fecha_emision: string;
  fecha_entrega_estimada: string | null;
  estado: string;
  subtotal_sin_impuestos: number;
  total_iva: number;
  total_con_impuestos: number;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface OrdenCompraCreate {
  company_id: string;
  supplier_id: string;
  fecha_emision?: string;
  fecha_entrega_estimada?: string;
  observaciones?: string;
  detalles: Array<{
    product_id?: string;
    codigo_principal: string;
    descripcion: string;
    cantidad: number;
    precio_unitario: number;
    iva_codigo: string;
    iva_porcentaje: number;
    descuento?: number;
  }>;
}

// Purchase Order API functions
async function getOrdenesCompra(params?: { company_id?: string; estado?: string }): Promise<OrdenCompra[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<OrdenCompra[]>(`/v1/purchases/ordenes${qs}`);
}

async function createOrdenCompra(data: OrdenCompraCreate): Promise<OrdenCompra> {
  return apiPost<OrdenCompra>('/v1/purchases/ordenes', data);
}

async function getOrdenCompra(id: string): Promise<OrdenCompra> {
  return apiGet<OrdenCompra>(`/v1/purchases/ordenes/${id}`);
}

async function deleteOrdenCompra(id: string): Promise<{ message: string }> {
  return apiDelete(`/v1/purchases/ordenes/${id}`);
}

// ============ ACCOUNTS PAYABLE ============
interface CuentaPorPagar {
  id: string;
  company_id: string;
  supplier_id: string;
  numero_factura: string | null;
  fecha_emision: string;
  fecha_vencimiento: string | null;
  monto_total: number;
  monto_pagado: number;
  monto_pendiente: number;
  estado: string;
  dias_credito: number;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

async function getCuentasPorPagar(params?: { company_id?: string; estado?: string }): Promise<CuentaPorPagar[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<CuentaPorPagar[]>(`/v1/purchases/cuentas-por-pagar${qs}`);
}

async function createCuentaPorPagar(data: {
  company_id: string;
  supplier_id: string;
  orden_compra_id?: string;
  numero_factura?: string;
  fecha_emision: string;
  monto_total: number;
  dias_credito?: number;
  observaciones?: string;
}): Promise<CuentaPorPagar> {
  return apiPost<CuentaPorPagar>('/v1/purchases/cuentas-por-pagar', data);
}

async function registerPaymentCuentaPorPagar(id: string, data: { monto: number; fecha_pago?: string }): Promise<{ message: string }> {
  return apiPost(`/v1/purchases/cuentas-por-pagar/${id}/pago`, data);
}

// ============ PURCHASE RETENTION ============
interface RetencionCompra {
  id: string;
  company_id: string;
  supplier_id: string;
  numero_retencion: string | null;
  fecha_emision: string;
  base_imponible_iva: number;
  retencion_iva_codigo: string;
  retencion_iva_porcentaje: number;
  retencion_iva_valor: number;
  base_imponible_renta: number;
  retencion_renta_codigo: string;
  retencion_renta_porcentaje: number;
  retencion_renta_valor: number;
  estado: string;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

async function getRetencionesCompra(params?: { company_id?: string; estado?: string }): Promise<RetencionCompra[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<RetencionCompra[]>(`/v1/purchases/retenciones${qs}`);
}

async function createRetencionCompra(data: {
  company_id: string;
  supplier_id: string;
  cuenta_por_pagar_id?: string;
  fecha_emision: string;
  base_imponible_iva: number;
  retencion_iva_codigo: string;
  retencion_iva_porcentaje: number;
  base_imponible_renta: number;
  retencion_renta_codigo: string;
  retencion_renta_porcentaje: number;
  observaciones?: string;
}): Promise<RetencionCompra> {
  return apiPost<RetencionCompra>('/v1/purchases/retenciones', data);
}

async function updateRetencionCompra(id: string, data: Partial<{
  estado?: string;
  base_imponible_iva?: number;
  retencion_iva_codigo?: string;
  retencion_iva_porcentaje?: number;
  base_imponible_renta?: number;
  retencion_renta_codigo?: string;
  retencion_renta_porcentaje?: number;
  observaciones?: string;
}>): Promise<RetencionCompra> {
  return apiPut<RetencionCompra>(`/v1/purchases/retenciones/${id}`, data);
}

async function deleteRetencionCompra(id: string): Promise<{ message: string }> {
  return apiDelete(`/v1/purchases/retenciones/${id}`);
}

// ============ AUDIT LOG TYPES ============
interface AuditLogEntry {
  id: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  description: string;
  ip_address: string | null;
  created_at: string;
}

async function getAuditLogs(params?: { user_id?: string; action?: string; entity_type?: string; fecha_desde?: string; fecha_hasta?: string; skip?: number; limit?: number }): Promise<AuditLogEntry[]> {
  const query: string[] = [];
  if (params?.user_id) query.push(`user_id=${params.user_id}`);
  if (params?.action) query.push(`action=${params.action}`);
  if (params?.entity_type) query.push(`entity_type=${params.entity_type}`);
  if (params?.fecha_desde) query.push(`fecha_desde=${params.fecha_desde}`);
  if (params?.fecha_hasta) query.push(`fecha_hasta=${params.fecha_hasta}`);
  if (params?.skip !== undefined) query.push(`skip=${params.skip}`);
  if (params?.limit !== undefined) query.push(`limit=${params.limit}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<AuditLogEntry[]>(`/v1/audit${qs}`);
}

async function getAuditStats(): Promise<unknown> {
  return apiGet('/v1/audit/stats');
}

// ============ EMAIL TEMPLATE TYPES ============
interface EmailTemplate {
  id: string;
  user_id: string;
  nombre: string;
  tipo: string;
  asunto: string;
  cuerpo_html: string;
  cuerpo_texto: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

async function getEmailTemplates(tipo?: string): Promise<EmailTemplate[]> {
  const qs = tipo ? `?tipo=${tipo}` : '';
  return apiGet<EmailTemplate[]>(`/v1/email-templates${qs}`);
}

async function createEmailTemplate(data: { nombre: string; tipo: string; asunto: string; cuerpo_html: string; cuerpo_texto?: string; is_default?: boolean }): Promise<EmailTemplate> {
  return apiPost<EmailTemplate>('/v1/email-templates', data);
}

async function updateEmailTemplate(id: string, data: Partial<{ nombre: string; tipo: string; asunto: string; cuerpo_html: string; cuerpo_texto: string; is_default: boolean }>): Promise<EmailTemplate> {
  return apiPut<EmailTemplate>(`/v1/email-templates/${id}`, data);
}

async function deleteEmailTemplate(id: string): Promise<{ message: string }> {
  return apiDelete(`/v1/email-templates/${id}`);
}

async function previewEmailTemplate(id: string, data: { comprobante_id?: string }): Promise<unknown> {
  return apiPost(`/v1/email-templates/${id}/preview`, data);
}

async function previewEmailTemplateCustom(data: { cuerpo_html: string; asunto: string; sample_data?: Record<string, unknown> }): Promise<{ rendered_html?: string; cuerpo_html?: string }> {
  return apiPost('/v1/email-templates/preview', data);
}

async function sendEmailWithTemplate(data: { template_id: string; comprobante_id: string; to_email?: string }): Promise<{ message: string }> {
  return apiPost('/v1/email-templates/send', data);
}

// ============ IMPORT/EXPORT ============
interface ImportProductsResult {
  message: string;
  success_count: number;
  error_count: number;
  errors: { row: number; error: string }[];
}

async function importProductsExcel(companyId: string, file: File): Promise<ImportProductsResult> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/imports/products/excel?company_id=${companyId}`), {
    method: 'POST',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al importar' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

async function importProductsCSV(companyId: string, file: File): Promise<ImportProductsResult> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/imports/products/csv?company_id=${companyId}`), {
    method: 'POST',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al importar' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

async function importClientsExcel(companyId: string, file: File): Promise<{ success: number; errors: number; error_details: string[] }> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/imports/clients/excel?company_id=${companyId}`), {
    method: 'POST',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al importar' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

async function importClientsCSV(companyId: string, file: File): Promise<{ success: number; errors: number; error_details: string[] }> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/imports/clients/csv?company_id=${companyId}`), {
    method: 'POST',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error al importar' }));
    throw new Error(errorData.detail || `Error ${response.status}`);
  }
  return response.json();
}

async function exportProductsExcel(companyId: string): Promise<Blob> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/exports/products/excel?company_id=${companyId}`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error al exportar');
  return response.blob();
}

async function exportProductsCSV(companyId: string): Promise<Blob> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/exports/products/csv?company_id=${companyId}`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error al exportar');
  return response.blob();
}

async function exportComprobantesExcel(companyId: string): Promise<Blob> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/exports/comprobantes/excel?company_id=${companyId}`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error al exportar');
  return response.blob();
}

async function exportComprobantesXMLZip(companyId: string): Promise<Blob> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  const token = getToken();
  const response = await fetch(buildUrl(`/v1/exports/comprobantes/xml-zip?company_id=${companyId}`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error al exportar');
  return response.blob();
}

// ============ PHASE 9: WAREHOUSE TYPES ============

interface Warehouse {
  id: string;
  company_id: string;
  nombre: string;
  codigo: string;
  direccion: string | null;
  ciudad: string | null;
  responsable: string | null;
  telefono: string | null;
  is_principal: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface WarehouseCreate {
  company_id: string;
  nombre: string;
  codigo?: string;
  direccion?: string;
  ciudad?: string;
  responsable?: string;
  telefono?: string;
  is_principal?: boolean;
}

interface WarehouseUpdate {
  nombre?: string;
  direccion?: string;
  ciudad?: string;
  responsable?: string;
  telefono?: string;
  is_principal?: boolean;
  is_active?: boolean;
}

interface WarehouseLocation {
  id: string;
  warehouse_id: string;
  producto_id: string | null;
  zona: string;
  rack: string;
  estante: string;
  nivel: string | null;
  codigo_ubicacion: string;
  capacidad_maxima: number | null;
  cantidad_actual: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface WarehouseLocationCreate {
  warehouse_id: string;
  producto_id?: string;
  zona: string;
  rack: string;
  estante: string;
  nivel?: string;
  capacidad_maxima?: number;
}

interface WarehouseLocationUpdate {
  zona?: string;
  rack?: string;
  estante?: string;
  nivel?: string;
  capacidad_maxima?: number;
  is_active?: boolean;
}

interface WarehouseStock {
  product_id: string;
  product_codigo: string;
  product_descripcion: string;
  cantidad: number;
  costo_promedio: number;
  valor_total: number;
}

interface WarehouseTransferDetalle {
  id: string;
  transferencia_id: string;
  product_id: string;
  product_descripcion: string;
  product_codigo: string;
  cantidad: number;
  costo_unitario: number;
  costo_total: number;
  ubicacion_origen_id: string | null;
  ubicacion_destino_id: string | null;
  created_at: string;
}

interface WarehouseTransfer {
  id: string;
  company_id: string;
  numero: string;
  warehouse_origen_id: string;
  warehouse_destino_id: string;
  warehouse_origen_nombre: string;
  warehouse_destino_nombre: string;
  estado: 'pendiente' | 'en_transito' | 'recibida' | 'anulada';
  motivo: string | null;
  observaciones: string | null;
  user_id: string;
  fecha_envio: string | null;
  fecha_recepcion: string | null;
  detalles: WarehouseTransferDetalle[];
  created_at: string;
  updated_at: string;
}

interface WarehouseTransferCreate {
  company_id: string;
  warehouse_origen_id: string;
  warehouse_destino_id: string;
  motivo?: string;
  observaciones?: string;
  detalles: Array<{
    product_id: string;
    cantidad: number;
    costo_unitario: number;
    ubicacion_origen_id?: string;
    ubicacion_destino_id?: string;
  }>;
}

interface WarehouseKardexDetalle {
  id: string;
  company_id: string;
  warehouse_id: string;
  warehouse_nombre: string;
  product_id: string;
  product_descripcion: string;
  product_codigo: string;
  tipo_movimiento: string;
  cantidad: number;
  costo_unitario: number;
  costo_total: number;
  saldo_cantidad: number;
  saldo_valor: number;
  referencia_tipo: string | null;
  referencia_secuencial: string | null;
  detalle: string | null;
  fecha_movimiento: string;
  created_at: string;
}

// ============ PHASE 9: WAREHOUSE API FUNCTIONS ============

// Warehouse CRUD
async function getWarehouses(companyId: string): Promise<Warehouse[]> {
  if (!isValidCompanyId(companyId)) return [];
  return apiGet<Warehouse[]>(`/v1/warehouses?company_id=${encodeURIComponent(companyId.trim())}`);
}

async function getWarehouse(id: string): Promise<Warehouse> {
  return apiGet<Warehouse>(`/v1/warehouses/${id}`);
}

async function createWarehouse(data: WarehouseCreate): Promise<Warehouse> {
  return apiPost<Warehouse>('/v1/warehouses', data);
}

async function updateWarehouse(id: string, data: WarehouseUpdate): Promise<Warehouse> {
  return apiPut<Warehouse>(`/v1/warehouses/${id}`, data);
}

async function deleteWarehouse(id: string): Promise<void> {
  return apiDelete(`/v1/warehouses/${id}`);
}

// Warehouse Locations
async function getWarehouseLocations(warehouseId: string): Promise<WarehouseLocation[]> {
  return apiGet<WarehouseLocation[]>(`/v1/warehouses/${warehouseId}/locations`);
}

async function createWarehouseLocation(data: WarehouseLocationCreate): Promise<WarehouseLocation> {
  return apiPost<WarehouseLocation>(`/v1/warehouses/${data.warehouse_id}/locations`, data);
}

async function updateWarehouseLocation(id: string, data: WarehouseLocationUpdate): Promise<WarehouseLocation> {
  return apiPut<WarehouseLocation>(`/v1/warehouses/locations/${id}`, data);
}

async function deleteWarehouseLocation(id: string): Promise<void> {
  return apiDelete(`/v1/warehouses/locations/${id}`);
}

// Warehouse Stock
async function getWarehouseStock(warehouseId: string): Promise<WarehouseStock[]> {
  return apiGet<WarehouseStock[]>(`/v1/warehouses/${warehouseId}/stock`);
}

// Warehouse Transfers
async function createWarehouseTransfer(data: WarehouseTransferCreate): Promise<WarehouseTransfer> {
  return apiPost<WarehouseTransfer>('/v1/warehouses/transfers', data);
}

async function getWarehouseTransfers(params?: { company_id?: string; estado?: string }): Promise<WarehouseTransfer[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<WarehouseTransfer[]>(`/v1/warehouses/transfers${qs}`);
}

async function getWarehouseTransfer(id: string): Promise<WarehouseTransfer> {
  return apiGet<WarehouseTransfer>(`/v1/warehouses/transfers/${id}`);
}

async function sendWarehouseTransfer(id: string): Promise<WarehouseTransfer> {
  return apiPost<WarehouseTransfer>(`/v1/warehouses/transfers/${id}/enviar`);
}

async function receiveWarehouseTransfer(id: string): Promise<WarehouseTransfer> {
  return apiPost<WarehouseTransfer>(`/v1/warehouses/transfers/${id}/recibir`);
}

async function cancelWarehouseTransfer(id: string): Promise<WarehouseTransfer> {
  return apiPost<WarehouseTransfer>(`/v1/warehouses/transfers/${id}/anular`);
}

// Detailed Kardex with warehouse info
async function getDetailedKardex(params?: { company_id?: string; product_id?: string; warehouse_id?: string; fecha_desde?: string; fecha_hasta?: string }): Promise<WarehouseKardexDetalle[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.product_id) query.push(`product_id=${params.product_id}`);
  if (params?.warehouse_id) query.push(`warehouse_id=${params.warehouse_id}`);
  if (params?.fecha_desde) query.push(`fecha_desde=${params.fecha_desde}`);
  if (params?.fecha_hasta) query.push(`fecha_hasta=${params.fecha_hasta}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<WarehouseKardexDetalle[]>(`/v1/warehouses/kardex${qs}`);
}

// ============ PHASE 10: POS TYPES ============

interface POSCashSession {
  id: string;
  company_id: string;
  warehouse_id: string | null;
  warehouse_nombre: string | null;
  numero_caja: string;
  user_id: string;
  user_nombre: string;
  estado: 'abierta' | 'cerrada';
  fecha_apertura: string;
  fecha_cierre: string | null;
  monto_apertura: number;
  monto_cierre_efectivo: number | null;
  monto_cierre_calculado: number | null;
  monto_diferencia: number | null;
  total_ventas_efectivo: number;
  total_ventas_tarjeta: number;
  total_ventas_credito: number;
  total_ventas_otro: number;
  total_ventas: number;
  total_propina: number;
  total_descuentos: number;
  total_devoluciones: number;
  observaciones_cierre: string | null;
  created_at: string;
  updated_at: string;
}

interface POSCashSessionOpen {
  company_id: string;
  warehouse_id?: string;
  numero_caja: string;
  monto_apertura: number;
}

interface POSTicketDetalle {
  id: string;
  ticket_id: string;
  product_id: string | null;
  codigo_principal: string;
  descripcion: string;
  cantidad: number;
  unidad_medida: string;
  precio_unitario: number;
  descuento: number;
  precio_total_sin_impuestos: number;
  iva_codigo: string;
  iva_porcentaje: number;
  iva_valor: number;
  created_at: string;
}

interface POSTicket {
  id: string;
  company_id: string;
  cash_session_id: string;
  comprobante_id: string | null;
  numero_ticket: string;
  estado: 'pendiente' | 'pagado' | 'anulado' | 'devuelto';
  tipo_venta: 'efectivo' | 'tarjeta' | 'credito' | 'mixto' | 'otro';
  cliente_nombre: string;
  cliente_identificacion: string;
  cliente_tipo_identificacion: string;
  cliente_direccion: string | null;
  cliente_telefono: string | null;
  cliente_email: string | null;
  subtotal_sin_impuestos: number;
  total_iva: number;
  total_descuento: number;
  total_con_impuestos: number;
  monto_efectivo: number;
  monto_tarjeta: number;
  monto_credito: number;
  monto_otro: number;
  cambio: number;
  propina: number;
  numero_tarjeta: string | null;
  tarjeta_tipo: string | null;
  tarjeta_marca: string | null;
  tarjeta_banco: string | null;
  tarjeta_titular: string | null;
  referencia_pago: string | null;
  observaciones: string | null;
  user_id: string;
  created_at: string;
  updated_at: string;
  detalles: POSTicketDetalle[];
}

interface POSTicketCreate {
  company_id: string;
  cash_session_id: string;
  tipo_venta: string;
  cliente_nombre?: string;
  cliente_identificacion?: string;
  cliente_tipo_identificacion?: string;
  cliente_direccion?: string;
  cliente_telefono?: string;
  cliente_email?: string;
  detalles: Array<{
    product_id?: string;
    codigo_principal: string;
    descripcion: string;
    cantidad: number;
    unidad_medida?: string;
    precio_unitario: number;
    descuento?: number;
    iva_codigo: string;
    iva_porcentaje: number;
  }>;
  monto_efectivo?: number;
  monto_tarjeta?: number;
  monto_credito?: number;
  monto_otro?: number;
  propina?: number;
  numero_tarjeta?: string;
  tarjeta_tipo?: string;
  tarjeta_marca?: string;
  tarjeta_banco?: string;
  tarjeta_titular?: string;
  referencia_pago?: string;
  observaciones?: string;
  crear_comprobante?: boolean;
}

interface POSArqueo {
  id: string;
  cash_session_id: string;
  company_id: string;
  tipo: 'parcial' | 'final';
  billetes: Record<string, number> | null;
  monedas: Record<string, number> | null;
  total_billetes: number;
  total_monedas: number;
  total_efectivo_contado: number;
  total_efectivo_calculado: number;
  diferencia: number;
  observaciones: string | null;
  user_id: string;
  created_at: string;
}

interface POSArqueoCreate {
  cash_session_id: string;
  tipo: 'parcial' | 'final';
  billetes?: Record<string, number>;
  monedas?: Record<string, number>;
  total_efectivo_contado: number;
  observaciones?: string;
  monto_cierre_efectivo?: number;
  observaciones_cierre?: string;
}

interface POSProductSearchResult {
  id: string;
  codigo_principal: string;
  codigo_auxiliar: string | null;
  codigo_barras: string | null;
  descripcion: string;
  tipo: string;
  precio_unitario: number;
  iva_codigo: string;
  iva_porcentaje: number;
  stock: number;
  unidad_medida: string;
  iva_incluido?: boolean | null;
}

interface POSTicketPrintData {
  numero_ticket: string;
  fecha: string;
  cliente_nombre: string;
  cliente_identificacion: string;
  cliente_direccion?: string | null;
  cliente_telefono?: string | null;
  cajero: string;
  numero_caja: string;
  items: Array<{
    codigo: string;
    descripcion: string;
    cantidad: string;
    precio_unitario: string;
    descuento: string;
    precio_total_sin_impuestos: string;
    iva_porcentaje: string;
    iva_valor: string;
  }>;
  subtotal_sin_impuestos: number;
  total_iva: number;
  total_descuento: number;
  total_con_impuestos: number;
  monto_efectivo: number;
  monto_tarjeta: number;
  monto_credito: number;
  monto_otro: number;
  cambio: number;
  propina: number;
  tipo_venta: string;
  numero_tarjeta?: string | null;
  tarjeta_tipo?: string | null;
  tarjeta_marca?: string | null;
  tarjeta_banco?: string | null;
  tarjeta_titular?: string | null;
  empresa_nombre?: string | null;
  empresa_ruc?: string | null;
  empresa_direccion?: string | null;
}

interface POSCashSessionResumen {
  session: POSCashSession;
  total_tickets: number;
  tickets_por_tipo: Record<string, number>;
  ultimos_tickets: POSTicket[];
}

// ============ PHASE 10: POS API FUNCTIONS ============

// POS Cash Sessions
async function openPOSSession(data: POSCashSessionOpen): Promise<POSCashSession> {
  return apiPost<POSCashSession>('/v1/pos/sessions', data);
}

async function getPOSSessions(params?: { company_id?: string; estado?: string }): Promise<POSCashSession[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<POSCashSession[]>(`/v1/pos/sessions${qs}`);
}

async function getPOSSession(id: string): Promise<POSCashSession> {
  return apiGet<POSCashSession>(`/v1/pos/sessions/${id}`);
}

async function closePOSSession(id: string, data: { monto_cierre_efectivo: number; observaciones_cierre?: string }): Promise<POSCashSession> {
  return apiPut<POSCashSession>(`/v1/pos/sessions/${id}/cerrar`, data);
}

async function getPOSSessionResumen(id: string): Promise<POSCashSessionResumen> {
  return apiGet<POSCashSessionResumen>(`/v1/pos/sessions/${id}/resumen`);
}

// POS Arqueos
async function createPOSArqueo(data: POSArqueoCreate): Promise<POSArqueo> {
  return apiPost<POSArqueo>('/v1/pos/arqueos', data);
}

// POS Tickets
async function createPOSTicket(data: POSTicketCreate): Promise<POSTicket> {
  return apiPost<POSTicket>('/v1/pos/tickets', data);
}

async function getPOSTickets(params?: { company_id?: string; session_id?: string; estado?: string }): Promise<POSTicket[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.session_id) query.push(`session_id=${params.session_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<POSTicket[]>(`/v1/pos/tickets${qs}`);
}

async function getPOSTicket(id: string): Promise<POSTicket> {
  return apiGet<POSTicket>(`/v1/pos/tickets/${id}`);
}

async function voidPOSTicket(id: string): Promise<POSTicket> {
  return apiPost<POSTicket>(`/v1/pos/tickets/${id}/anular`);
}

async function getPOSTicketPrintData(id: string): Promise<POSTicketPrintData> {
  return apiGet<POSTicketPrintData>(`/v1/pos/tickets/${id}/print`);
}

// POS Product Search
async function searchProductByBarcode(barcode: string, companyId: string): Promise<POSProductSearchResult[]> {
  return apiGet<POSProductSearchResult[]>(`/v1/pos/products/search?barcode=${encodeURIComponent(barcode)}&company_id=${companyId}`);
}

// ============ BUDGET (PRESUPUESTOS) TYPES ============

interface PresupuestoEjecucionMensual {
  id: string;
  presupuesto_cuenta_id: string;
  mes: number;
  monto_presupuestado: number;
  monto_ejecutado: number;
  monto_disponible: number;
  porcentaje_ejecucion: number;
  observaciones: string | null;
  created_at: string;
  updated_at: string;
}

interface PresupuestoAlerta {
  id: string;
  company_id: string;
  presupuesto_cuenta_id: string;
  tipo_alerta: string; // sobregiro, 90_porciento, 75_porciento, 50_porciento
  mensaje: string;
  monto_presupuestado: number;
  monto_ejecutado: number;
  monto_sobregiro: number;
  porcentaje_ejecucion: number;
  is_leida: boolean;
  is_resuelta: boolean;
  created_at: string;
}

interface PresupuestoCuenta {
  id: string;
  presupuesto_id: string;
  cuenta_codigo: string;
  cuenta_nombre: string;
  cuenta_tipo: string; // ingreso, egreso
  monto_anual: number;
  monto_ejecutado: number;
  monto_disponible: number;
  porcentaje_ejecucion: number;
  is_active: boolean;
  ejecuciones_mensuales: PresupuestoEjecucionMensual[];
  alertas: PresupuestoAlerta[];
  created_at: string;
  updated_at: string;
}

interface PresupuestoAnual {
  id: string;
  company_id: string;
  user_id: string;
  anio: number;
  nombre: string;
  descripcion: string | null;
  estado: string; // borrador, aprobado, cerrado, anulado
  total_ingresos_presupuestado: number;
  total_egresos_presupuestado: number;
  total_ingresos_ejecutado: number;
  total_egresos_ejecutado: number;
  is_active: boolean;
  cuentas: PresupuestoCuenta[];
  created_at: string;
  updated_at: string;
}

interface PresupuestoCuentaCreate {
  cuenta_codigo: string;
  cuenta_nombre: string;
  cuenta_tipo: string;
  monto_anual: number;
  distribucion_mensual?: number[];
}

interface PresupuestoAnualCreate {
  company_id: string;
  anio: number;
  nombre: string;
  descripcion?: string;
  cuentas: PresupuestoCuentaCreate[];
}

interface PresupuestoStats {
  total_presupuestos: number;
  presupuestos_borrador: number;
  presupuestos_aprobados: number;
  presupuestos_cerrados: number;
  total_cuentas_con_alerta: number;
  total_sobregiros: number;
}

interface ComparativoCuenta {
  cuenta_codigo: string;
  cuenta_nombre: string;
  cuenta_tipo: string;
  monto_presupuestado: number;
  monto_ejecutado: number;
  monto_disponible: number;
  porcentaje_ejecucion: number;
  variacion: number;
  variacion_porcentaje: number;
  alerta_tipo: string | null;
}

interface ComparativoGeneral {
  anio: number;
  total_ingresos_presupuestado: number;
  total_ingresos_ejecutado: number;
  total_egresos_presupuestado: number;
  total_egresos_ejecutado: number;
  resultado_presupuestario: number;
  resultado_real: number;
  cuentas: ComparativoCuenta[];
}

interface AlertaSummary {
  total_alertas: number;
  alertas_no_leidas: number;
  sobregiros_activos: number;
  alertas_90: number;
  alertas_75: number;
  alertas_50: number;
}

// Backward compatibility alias
type _InvoiceStats = ComprobanteStatsResponse;

// ============ BUDGET API FUNCTIONS ============

async function getPresupuestos(params?: { company_id?: string; anio?: number; estado?: string }): Promise<PresupuestoAnual[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.anio) query.push(`anio=${params.anio}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<PresupuestoAnual[]>(`/v1/budgets${qs}`);
}

async function getPresupuesto(id: string): Promise<PresupuestoAnual> {
  return apiGet<PresupuestoAnual>(`/v1/budgets/${id}`);
}

async function createPresupuesto(data: PresupuestoAnualCreate): Promise<PresupuestoAnual> {
  return apiPost<PresupuestoAnual>('/v1/budgets', data);
}

async function updatePresupuesto(id: string, data: Partial<PresupuestoAnualCreate>): Promise<PresupuestoAnual> {
  return apiPut<PresupuestoAnual>(`/v1/budgets/${id}`, data);
}

async function deletePresupuesto(id: string): Promise<void> {
  return apiDelete(`/v1/budgets/${id}`);
}

async function approvePresupuesto(id: string): Promise<PresupuestoAnual> {
  return apiPut<PresupuestoAnual>(`/v1/budgets/${id}/approve`);
}

async function closePresupuesto(id: string): Promise<PresupuestoAnual> {
  return apiPut<PresupuestoAnual>(`/v1/budgets/${id}/close`);
}

async function addPresupuestoCuenta(presupuestoId: string, data: PresupuestoCuentaCreate): Promise<PresupuestoCuenta> {
  return apiPost<PresupuestoCuenta>(`/v1/budgets/${presupuestoId}/cuentas`, data);
}

async function updatePresupuestoCuenta(cuentaId: string, data: { monto_anual?: number; distribucion_mensual?: number[] }): Promise<PresupuestoCuenta> {
  return apiPut<PresupuestoCuenta>(`/v1/budgets/cuentas/${cuentaId}`, data);
}

async function deletePresupuestoCuenta(cuentaId: string): Promise<void> {
  return apiDelete(`/v1/budgets/cuentas/${cuentaId}`);
}

async function registerEjecucionMensual(cuentaId: string, data: { monto_ejecutado: number; observaciones?: string }): Promise<PresupuestoEjecucionMensual> {
  return apiPost<PresupuestoEjecucionMensual>(`/v1/budgets/cuentas/${cuentaId}/ejecucion`, data);
}

async function getEjecucionMensual(cuentaId: string): Promise<PresupuestoEjecucionMensual[]> {
  return apiGet<PresupuestoEjecucionMensual[]>(`/v1/budgets/cuentas/${cuentaId}/ejecucion`);
}

async function getPresupuestoAlertas(params?: { company_id?: string; tipo?: string; is_leida?: boolean }): Promise<PresupuestoAlerta[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.tipo) query.push(`tipo=${params.tipo}`);
  if (params?.is_leida !== undefined) query.push(`is_leida=${params.is_leida}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<PresupuestoAlerta[]>(`/v1/budgets/alertas${qs}`);
}

async function markAlertaRead(alertaId: string): Promise<PresupuestoAlerta> {
  return apiPut<PresupuestoAlerta>(`/v1/budgets/alertas/${alertaId}/read`);
}

async function markAlertaResolved(alertaId: string): Promise<PresupuestoAlerta> {
  return apiPut<PresupuestoAlerta>(`/v1/budgets/alertas/${alertaId}/resolve`);
}

async function getAlertaSummary(companyId?: string): Promise<AlertaSummary> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<AlertaSummary>(`/v1/budgets/alertas/summary${qs}`);
}

async function getComparativoPresupuestario(params?: { company_id?: string; anio?: number }): Promise<ComparativoGeneral> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.anio) query.push(`anio=${params.anio}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<ComparativoGeneral>(`/v1/budgets/comparativo${qs}`);
}

async function getPresupuestoComparativo(id: string): Promise<ComparativoGeneral> {
  return apiGet<ComparativoGeneral>(`/v1/budgets/${id}/comparativo`);
}

async function getPresupuestoStats(companyId?: string): Promise<PresupuestoStats> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<PresupuestoStats>(`/v1/budgets/stats${qs}`);
}

async function recalcularPresupuesto(id: string): Promise<PresupuestoAnual> {
  return apiPost<PresupuestoAnual>(`/v1/budgets/${id}/recalcular`);
}

// ============ CRM TYPES ============

interface CRMOpportunity {
  id: string;
  company_id: string;
  lead_id: string | null;
  client_id: string | null;
  pipeline_id: string;
  stage_id: string;
  name: string;
  description: string | null;
  estimated_amount: number;
  probability: number;
  expected_close_date: string | null;
  actual_close_date: string | null;
  status: string;
  assigned_to: string | null;
  lost_reason: string | null;
  created_at: string;
  updated_at: string;
  // Enriched fields from backend OpportunityWithDetails
  lead_name?: string | null;
  client_name?: string | null;
  stage_name?: string | null;
  stage_color?: string | null;
  pipeline_name?: string | null;
  weighted_amount?: number | null;
  // Legacy aliases for component compatibility
  titulo?: string;
  etapa?: string;
  valor_estimado?: number;
  fecha_cierre_estimada?: string | null;
  cliente_razon_social?: string | null;
}

interface CRMOpportunityCreate {
  company_id: string;
  name: string;
  pipeline_id: string;
  stage_id: string;
  client_id?: string;
  lead_id?: string;
  description?: string;
  estimated_amount?: number;
  probability?: number;
  expected_close_date?: string;
  status?: string;
  assigned_to?: string;
}

interface CRMOpportunityUpdate {
  name?: string;
  description?: string;
  pipeline_id?: string;
  stage_id?: string;
  client_id?: string;
  lead_id?: string;
  estimated_amount?: number;
  probability?: number;
  expected_close_date?: string;
  actual_close_date?: string;
  status?: string;
  assigned_to?: string;
  lost_reason?: string;
}

interface CRMActivity {
  id: string;
  company_id: string;
  opportunity_id: string | null;
  lead_id: string | null;
  user_id: string;
  type: string; // llamada, email, reunion, tarea, nota
  subject: string;
  description: string | null;
  scheduled_at: string | null;
  completed_at: string | null;
  status: string; // pendiente, completada, cancelada
  result: string | null;
  created_at: string;
  // Legacy aliases for component compatibility
  tipo?: string;
  asunto?: string;
  descripcion?: string | null;
  fecha_actividad?: string | null;
  estado?: string;
  oportunidad_titulo?: string | null;
}

interface CRMActivityCreate {
  company_id: string;
  type: string;
  subject: string;
  opportunity_id?: string;
  lead_id?: string;
  description?: string;
  scheduled_at?: string;
  status?: string;
  result?: string;
}

interface CRMActivityUpdate {
  type?: string;
  subject?: string;
  description?: string;
  opportunity_id?: string;
  lead_id?: string;
  scheduled_at?: string;
  completed_at?: string;
  status?: string;
  result?: string;
}

interface CRMSegment {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  type: string; // manual, regla, rfm
  rules: string | null; // JSON string
  rfm_score: string | null; // JSON string
  color: string | null;
  is_active: boolean;
  client_members: Array<{ id: string; segment_id: string; client_id: string; created_at: string }> | null;
  created_at: string;
  updated_at: string;
  // Legacy aliases
  nombre?: string;
  criterio?: string | null;
  cliente_count?: number;
}

interface CRMSegmentCreate {
  company_id: string;
  name: string;
  type: string;
  description?: string;
  rules?: string;
  rfm_score?: string;
  color?: string;
}

interface CRMAutomation {
  id: string;
  company_id: string;
  name: string;
  trigger_type: string; // lead_creado, oportunidad_ganada, stage_changed, etc.
  trigger_conditions: string | null; // JSON string
  actions: string | null; // JSON string
  is_active: boolean;
  last_triggered_at: string | null;
  trigger_count: number;
  created_at: string;
  updated_at: string;
  // Legacy aliases
  nombre?: string;
  evento_disparador?: string;
  condiciones?: string | null;
  acciones?: string | null;
  ejecuciones_count?: number;
  ultima_ejecucion?: string | null;
}

interface CRMAutomationCreate {
  company_id: string;
  name: string;
  trigger_type: string;
  trigger_conditions?: string;
  actions?: string;
  is_active?: boolean;
}

interface CRMStats {
  total_oportunidades: number;
  valor_pipeline: number;
  valor_ganado: number;
  valor_perdido: number;
  tasa_conversion: number;
  promedio_cierre_dias: number;
  oportunidades_por_etapa: Record<string, number>;
  valor_por_etapa: Record<string, number>;
  actividades_pendientes: number;
  actividades_vencidas: number;
}

// ============ CRM API FUNCTIONS ============

async function getCRMOpportunities(params?: {
  company_id?: string;
  etapa?: string;
  responsable?: string;
  fuente?: string;
  segmento?: string;
  prioridad?: string;
  is_active?: boolean;
}): Promise<CRMOpportunity[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.etapa) query.push(`etapa=${params.etapa}`);
  if (params?.responsable) query.push(`responsable=${params.responsable}`);
  if (params?.fuente) query.push(`fuente=${params.fuente}`);
  if (params?.segmento) query.push(`segmento=${params.segmento}`);
  if (params?.prioridad) query.push(`prioridad=${params.prioridad}`);
  if (params?.is_active !== undefined) query.push(`is_active=${params.is_active}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  const list = await apiGet<Array<Record<string, unknown>>>(`/v1/crm/opportunities${qs}`);
  // Normalizar campos del backend a los alias legacy que usa el componente
  return list.map((o) => ({
    ...o,
    titulo: (o.name as string) || (o.titulo as string) || '',
    etapa: (o.stage_id as string) || undefined,
    valor_estimado: o.estimated_amount as number | undefined,
    cliente_razon_social: (o.client_name as string | null) || undefined,
    fecha_cierre_estimada: (o.expected_close_date as string | null) || undefined,
  } as CRMOpportunity));
}

async function getCRMOpportunity(id: string): Promise<CRMOpportunity> {
  return apiGet<CRMOpportunity>(`/v1/crm/opportunities/${id}`);
}

async function createCRMOpportunity(data: CRMOpportunityCreate): Promise<CRMOpportunity> {
  return apiPost<CRMOpportunity>('/v1/crm/opportunities', data);
}

async function updateCRMOpportunity(id: string, data: CRMOpportunityUpdate): Promise<CRMOpportunity> {
  return apiPut<CRMOpportunity>(`/v1/crm/opportunities/${id}`, data);
}

async function deleteCRMOpportunity(id: string): Promise<void> {
  return apiDelete(`/v1/crm/opportunities/${id}`);
}

async function moveCRMOpportunity(id: string, stageId: string): Promise<CRMOpportunity> {
  return apiPut<CRMOpportunity>(`/v1/crm/opportunities/${id}/stage`, { stage_id: stageId });
}

async function convertCRMOpportunityToProforma(id: string): Promise<{ message: string; proforma_id: string }> {
  return apiPost(`/v1/crm/opportunities/${id}/convert-proforma`);
}

async function convertCRMOpportunityToInvoice(id: string): Promise<{ message: string; comprobante_id: string }> {
  return apiPost(`/v1/crm/opportunities/${id}/convert-invoice`);
}

async function getCRMActivities(params?: {
  company_id?: string;
  opportunity_id?: string;
  client_id?: string;
  tipo?: string;
  estado?: string;
}): Promise<CRMActivity[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.opportunity_id) query.push(`opportunity_id=${params.opportunity_id}`);
  if (params?.client_id) query.push(`client_id=${params.client_id}`);
  if (params?.tipo) query.push(`tipo=${params.tipo}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<CRMActivity[]>(`/v1/crm/activities${qs}`);
}

async function createCRMActivity(data: CRMActivityCreate): Promise<CRMActivity> {
  return apiPost<CRMActivity>('/v1/crm/activities', data);
}

async function updateCRMActivity(id: string, data: CRMActivityUpdate): Promise<CRMActivity> {
  return apiPut<CRMActivity>(`/v1/crm/activities/${id}`, data);
}

async function deleteCRMActivity(id: string): Promise<void> {
  return apiDelete(`/v1/crm/activities/${id}`);
}

async function completeCRMActivity(id: string): Promise<CRMActivity> {
  return apiPost<CRMActivity>(`/v1/crm/activities/${id}/complete`);
}

async function getCRMSegments(companyId: string): Promise<CRMSegment[]> {
  if (!isValidCompanyId(companyId)) return [];
  return apiGet<CRMSegment[]>(`/v1/crm/segments?company_id=${encodeURIComponent(companyId.trim())}`);
}

async function createCRMSegment(data: CRMSegmentCreate): Promise<CRMSegment> {
  return apiPost<CRMSegment>('/v1/crm/segments', data);
}

async function updateCRMSegment(id: string, data: Partial<CRMSegmentCreate>): Promise<CRMSegment> {
  return apiPut<CRMSegment>(`/v1/crm/segments/${id}`, data);
}

async function deleteCRMSegment(id: string): Promise<void> {
  return apiDelete(`/v1/crm/segments/${id}`);
}

async function assignClientToSegment(segmentId: string, clientId: string): Promise<{ message: string }> {
  return apiPost(`/v1/crm/segments/${segmentId}/assign`, { client_id: clientId });
}

async function getCRMAutomations(companyId: string): Promise<CRMAutomation[]> {
  if (!isValidCompanyId(companyId)) return [];
  return apiGet<CRMAutomation[]>(`/v1/crm/automations?company_id=${encodeURIComponent(companyId.trim())}`);
}

async function createCRMAutomation(data: CRMAutomationCreate): Promise<CRMAutomation> {
  return apiPost<CRMAutomation>('/v1/crm/automations', data);
}

async function toggleCRMAutomation(id: string, isActive: boolean): Promise<CRMAutomation> {
  return apiPut<CRMAutomation>(`/v1/crm/automations/${id}`, { is_active: isActive });
}

async function deleteCRMAutomation(id: string): Promise<void> {
  return apiDelete(`/v1/crm/automations/${id}`);
}

async function getCRMStats(companyId?: string): Promise<CRMStats> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  const raw = await apiGet<Record<string, unknown>>(`/v1/crm/stats${qs}`);
  // Mapear la respuesta del backend (total_opportunities, pipeline_value, ...) a la forma que usa el componente
  return {
    total_oportunidades: Number(raw.total_opportunities ?? 0),
    valor_pipeline: Number(raw.pipeline_value ?? 0),
    valor_ganado: Number(raw.won_opportunities ?? 0),
    valor_perdido: Number(raw.lost_opportunities ?? 0),
    tasa_conversion: Number(raw.conversion_rate ?? 0),
    promedio_cierre_dias: 0,
    oportunidades_por_etapa: {},
    valor_por_etapa: {},
    actividades_pendientes: Number(raw.total_activities ?? 0),
    actividades_vencidas: 0,
  };
}

// ============ PROJECT (PHASE 14) TYPES ============

interface ProyectoResponse {
  id: string;
  company_id: string;
  user_id: string;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  cliente_id: string | null;
  cliente_nombre: string | null;
  estado: string;
  fecha_inicio: string | null;
  fecha_fin_estimada: string | null;
  fecha_fin_real: string | null;
  presupuesto: number;
  costo_real: number;
  ingreso: number;
  margen: number;
  margen_porcentaje: number;
  progreso: number;
  responsable: string | null;
  notas: string | null;
  is_active: boolean;
  tareas: ProyectoTareaResponse[];
  recursos: ProyectoRecursoResponse[];
  timesheets: ProyectoTimesheetResponse[];
  costos: ProyectoCostoResponse[];
  created_at: string;
  updated_at: string;
}

interface ProyectoCreate {
  company_id: string;
  codigo: string;
  nombre: string;
  descripcion?: string;
  cliente_id?: string;
  cliente_nombre?: string;
  estado?: string;
  fecha_inicio?: string;
  fecha_fin_estimada?: string;
  presupuesto?: number;
  responsable?: string;
  notas?: string;
}

interface ProyectoUpdate {
  codigo?: string;
  nombre?: string;
  descripcion?: string;
  cliente_id?: string;
  cliente_nombre?: string;
  estado?: string;
  fecha_inicio?: string;
  fecha_fin_estimada?: string;
  fecha_fin_real?: string;
  presupuesto?: number;
  ingreso?: number;
  responsable?: string;
  notas?: string;
  is_active?: boolean;
}

interface ProyectoTareaResponse {
  id: string;
  proyecto_id: string;
  titulo: string;
  descripcion: string | null;
  estado: string;
  prioridad: string;
  fase: string | null;
  asignado_a: string | null;
  employee_id: string | null;
  fecha_inicio: string | null;
  fecha_fin_estimada: string | null;
  fecha_fin_real: string | null;
  horas_estimadas: number;
  horas_reales: number;
  progreso: number;
  orden: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ProyectoTareaCreate {
  titulo: string;
  descripcion?: string;
  estado?: string;
  prioridad?: string;
  fase?: string;
  asignado_a?: string;
  employee_id?: string;
  fecha_inicio?: string;
  fecha_fin_estimada?: string;
  horas_estimadas?: number;
  orden?: number;
}

interface ProyectoTareaUpdate {
  titulo?: string;
  descripcion?: string;
  estado?: string;
  prioridad?: string;
  fase?: string;
  asignado_a?: string;
  employee_id?: string;
  fecha_inicio?: string;
  fecha_fin_estimada?: string;
  fecha_fin_real?: string;
  horas_estimadas?: number;
  progreso?: number;
  orden?: number;
}

interface ProyectoRecursoResponse {
  id: string;
  proyecto_id: string;
  tipo_recurso: string;
  nombre: string;
  descripcion: string | null;
  employee_id: string | null;
  costo_unitario: number;
  cantidad: number;
  costo_total: number;
  fecha_asignacion: string | null;
  fecha_liberacion: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ProyectoRecursoCreate {
  tipo_recurso: string;
  nombre: string;
  descripcion?: string;
  employee_id?: string;
  costo_unitario?: number;
  cantidad?: number;
  fecha_asignacion?: string;
}

interface ProyectoRecursoUpdate {
  tipo_recurso?: string;
  nombre?: string;
  descripcion?: string;
  costo_unitario?: number;
  cantidad?: number;
  fecha_liberacion?: string;
  is_active?: boolean;
}

interface ProyectoTimesheetResponse {
  id: string;
  company_id: string;
  proyecto_id: string;
  tarea_id: string | null;
  employee_id: string | null;
  empleado_nombre: string;
  fecha: string;
  horas: number;
  tarifa_hora: number;
  costo_total: number;
  descripcion: string | null;
  es_facturable: boolean;
  created_at: string;
  updated_at: string;
}

interface ProyectoTimesheetCreate {
  company_id: string;
  tarea_id?: string;
  employee_id?: string;
  empleado_nombre: string;
  fecha: string;
  horas: number;
  tarifa_hora?: number;
  descripcion?: string;
  es_facturable?: boolean;
}

interface ProyectoTimesheetUpdate {
  tarea_id?: string;
  employee_id?: string;
  empleado_nombre?: string;
  fecha?: string;
  horas?: number;
  tarifa_hora?: number;
  descripcion?: string;
  es_facturable?: boolean;
}

interface ProyectoCostoResponse {
  id: string;
  proyecto_id: string;
  concepto: string;
  descripcion: string | null;
  monto: number;
  fecha: string;
  categoria: string | null;
  es_facturable: boolean;
  comprobante_id: string | null;
  created_at: string;
}

interface ProyectoCostoCreate {
  concepto: string;
  descripcion?: string;
  monto: number;
  fecha: string;
  categoria?: string;
  es_facturable?: boolean;
  comprobante_id?: string;
}

interface ProyectoStats {
  total_proyectos: number;
  en_planificacion: number;
  en_progreso: number;
  completados: number;
  cancelados: number;
  total_presupuesto: number;
  total_costo_real: number;
  total_ingreso: number;
  margen_total: number;
  horas_totales: number;
}

// ============ PROJECT API FUNCTIONS ============

async function getProyectos(params?: { company_id?: string; estado?: string }): Promise<ProyectoResponse[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<ProyectoResponse[]>(`/v1/projects${qs}`);
}

async function getProyecto(id: string): Promise<ProyectoResponse> {
  return apiGet<ProyectoResponse>(`/v1/projects/${id}`);
}

async function createProyecto(data: ProyectoCreate): Promise<ProyectoResponse> {
  return apiPost<ProyectoResponse>('/v1/projects', data);
}

async function updateProyecto(id: string, data: ProyectoUpdate): Promise<ProyectoResponse> {
  return apiPut<ProyectoResponse>(`/v1/projects/${id}`, data);
}

async function deleteProyecto(id: string): Promise<void> {
  return apiDelete(`/v1/projects/${id}`);
}

async function getProyectoStats(companyId: string): Promise<ProyectoStats> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  return apiGet<ProyectoStats>(`/v1/projects/stats?company_id=${encodeURIComponent(companyId.trim())}`);
}

async function recalcularProyecto(id: string): Promise<ProyectoResponse> {
  return apiPost<ProyectoResponse>(`/v1/projects/${id}/recalcular`);
}

// Project Tareas
async function getProyectoTareas(proyectoId: string): Promise<ProyectoTareaResponse[]> {
  return apiGet<ProyectoTareaResponse[]>(`/v1/projects/${proyectoId}/tareas`);
}

async function createProyectoTarea(proyectoId: string, data: ProyectoTareaCreate): Promise<ProyectoTareaResponse> {
  return apiPost<ProyectoTareaResponse>(`/v1/projects/${proyectoId}/tareas`, data);
}

async function updateProyectoTarea(tareaId: string, data: ProyectoTareaUpdate): Promise<ProyectoTareaResponse> {
  return apiPut<ProyectoTareaResponse>(`/v1/projects/tareas/${tareaId}`, data);
}

async function deleteProyectoTarea(tareaId: string): Promise<void> {
  return apiDelete(`/v1/projects/tareas/${tareaId}`);
}

// Project Recursos
async function getProyectoRecursos(proyectoId: string): Promise<ProyectoRecursoResponse[]> {
  return apiGet<ProyectoRecursoResponse[]>(`/v1/projects/${proyectoId}/recursos`);
}

async function createProyectoRecurso(proyectoId: string, data: ProyectoRecursoCreate): Promise<ProyectoRecursoResponse> {
  return apiPost<ProyectoRecursoResponse>(`/v1/projects/${proyectoId}/recursos`, data);
}

async function updateProyectoRecurso(recursoId: string, data: ProyectoRecursoUpdate): Promise<ProyectoRecursoResponse> {
  return apiPut<ProyectoRecursoResponse>(`/v1/projects/recursos/${recursoId}`, data);
}

async function deleteProyectoRecurso(recursoId: string): Promise<void> {
  return apiDelete(`/v1/projects/recursos/${recursoId}`);
}

// Project Timesheets
async function getProyectoTimesheets(proyectoId: string): Promise<ProyectoTimesheetResponse[]> {
  return apiGet<ProyectoTimesheetResponse[]>(`/v1/projects/${proyectoId}/timesheets`);
}

async function createProyectoTimesheet(proyectoId: string, data: ProyectoTimesheetCreate): Promise<ProyectoTimesheetResponse> {
  return apiPost<ProyectoTimesheetResponse>(`/v1/projects/${proyectoId}/timesheets`, data);
}

async function updateProyectoTimesheet(tsId: string, data: ProyectoTimesheetUpdate): Promise<ProyectoTimesheetResponse> {
  return apiPut<ProyectoTimesheetResponse>(`/v1/projects/timesheets/${tsId}`, data);
}

async function deleteProyectoTimesheet(tsId: string): Promise<void> {
  return apiDelete(`/v1/projects/timesheets/${tsId}`);
}

// Project Costos
async function getProyectoCostos(proyectoId: string): Promise<ProyectoCostoResponse[]> {
  return apiGet<ProyectoCostoResponse[]>(`/v1/projects/${proyectoId}/costos`);
}

async function createProyectoCosto(proyectoId: string, data: ProyectoCostoCreate): Promise<ProyectoCostoResponse> {
  return apiPost<ProyectoCostoResponse>(`/v1/projects/${proyectoId}/costos`, data);
}

async function deleteProyectoCosto(costoId: string): Promise<void> {
  return apiDelete(`/v1/projects/costos/${costoId}`);
}

// ============ INTEGRATION (PHASE 15) TYPES ============

// Bank Account
interface CuentaBancariaResponse {
  id: string;
  company_id: string;
  nombre_banco: string;
  codigo_banco: string | null;
  tipo_cuenta: string;
  numero_cuenta: string;
  iban: string | null;
  swift_bic: string | null;
  titular: string;
  moneda: string;
  saldo_inicial: number;
  saldo_actual: number;
  ultima_fecha_sincronizacion: string | null;
  formato_extracto: string;
  configuracion_mapeo: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface CuentaBancariaCreate {
  company_id: string;
  nombre_banco: string;
  codigo_banco?: string;
  tipo_cuenta?: string;
  numero_cuenta: string;
  iban?: string;
  swift_bic?: string;
  titular: string;
  moneda?: string;
  saldo_inicial?: number;
  formato_extracto?: string;
  configuracion_mapeo?: string;
}

interface CuentaBancariaUpdate {
  nombre_banco?: string;
  codigo_banco?: string;
  tipo_cuenta?: string;
  numero_cuenta?: string;
  iban?: string;
  swift_bic?: string;
  titular?: string;
  moneda?: string;
  saldo_inicial?: number;
  formato_extracto?: string;
  configuracion_mapeo?: string;
  is_active?: boolean;
}

// Bank Statement (Extracto)
interface ExtractoBancarioResponse {
  id: string;
  company_id: string;
  cuenta_bancaria_id: string;
  fecha_desde: string;
  fecha_hasta: string;
  saldo_inicial: number;
  saldo_final: number;
  total_debitos: number;
  total_creditos: number;
  estado: string;
  numero_movimientos: number;
  movimientos_conciliados: number;
  archivo_original: string | null;
  notas: string | null;
  created_at: string;
  updated_at: string;
  banco_nombre?: string;
  cuenta_numero?: string;
}

interface ExtractoBancarioCreate {
  company_id: string;
  cuenta_bancaria_id: string;
  fecha_desde: string;
  fecha_hasta: string;
  saldo_inicial?: number;
  saldo_final?: number;
  total_debitos?: number;
  total_creditos?: number;
  numero_movimientos?: number;
  archivo_original?: string;
  notas?: string;
}

// Bank Movement (Movimiento)
interface MovimientoBancarioResponse {
  id: string;
  company_id: string;
  cuenta_bancaria_id: string;
  extracto_id: string;
  fecha: string;
  tipo: string;
  monto: number;
  saldo_posterior: number | null;
  referencia: string | null;
  descripcion: string | null;
  beneficiario: string | null;
  documento: string | null;
  conciliacion_estado: string;
  conciliacion_fecha: string | null;
  comprobante_id: string | null;
  conciliacion_nota: string | null;
  categoria: string | null;
  created_at: string;
}

interface MovimientoBancarioCreate {
  company_id: string;
  cuenta_bancaria_id: string;
  extracto_id: string;
  fecha: string;
  tipo: string;
  monto: number;
  saldo_posterior?: number;
  referencia?: string;
  descripcion?: string;
  beneficiario?: string;
  documento?: string;
  categoria?: string;
}

interface MovimientoBancarioUpdate {
  conciliacion_estado?: string;
  conciliacion_nota?: string;
  comprobante_id?: string;
  categoria?: string;
}

// E-Commerce Connector
interface EcommerceConnectorResponse {
  id: string;
  company_id: string;
  user_id: string;
  nombre: string;
  plataforma: string;
  url_tienda: string;
  api_key: string | null;
  access_token: string | null;
  webhook_url: string | null;
  configuracion_extra: string | null;
  estado: string;
  ultimo_error: string | null;
  ultima_sincronizacion: string | null;
  sincronizacion_auto: boolean;
  frecuencia_sync: number;
  sync_productos: boolean;
  sync_ordenes: boolean;
  sync_clientes: boolean;
  sync_inventario: boolean;
  total_ordenes_sync: number;
  total_productos_sync: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface EcommerceConnectorCreate {
  company_id: string;
  nombre: string;
  plataforma: string;
  url_tienda: string;
  api_key?: string;
  api_secret?: string;
  access_token?: string;
  refresh_token?: string;
  configuracion_extra?: string;
  sincronizacion_auto?: boolean;
  frecuencia_sync?: number;
  sync_productos?: boolean;
  sync_ordenes?: boolean;
  sync_clientes?: boolean;
  sync_inventario?: boolean;
}

interface EcommerceConnectorUpdate {
  nombre?: string;
  url_tienda?: string;
  api_key?: string;
  api_secret?: string;
  access_token?: string;
  refresh_token?: string;
  configuracion_extra?: string;
  sincronizacion_auto?: boolean;
  frecuencia_sync?: number;
  sync_productos?: boolean;
  sync_ordenes?: boolean;
  sync_clientes?: boolean;
  sync_inventario?: boolean;
  is_active?: boolean;
}

// E-Commerce Sync Log
interface EcommerceSyncLogResponse {
  id: string;
  company_id: string;
  connector_id: string;
  tipo_sync: string;
  estado: string;
  fecha_inicio: string;
  fecha_fin: string | null;
  registros_procesados: number;
  registros_creados: number;
  registros_actualizados: number;
  registros_errores: number;
  detalle_errores: string | null;
  resultado_resumen: string | null;
  creado_por: string | null;
  created_at: string;
  connector_nombre?: string;
  connector_plataforma?: string;
}

// Integration Stats
interface IntegrationStats {
  total_cuentas_bancarias: number;
  cuentas_activas: number;
  total_extractos: number;
  extractos_pendientes: number;
  movimientos_pendientes_conciliar: number;
  movimientos_conciliados: number;
  saldo_total_cuentas: number;
  total_connectors: number;
  connectors_activos: number;
  connectors_por_plataforma: Record<string, number>;
  total_sync_logs: number;
  sync_logs_hoy: number;
  ultima_sync_fecha: string | null;
}

// ============ INTEGRATION API FUNCTIONS ============

// Integration Stats
async function getIntegrationStats(companyId: string): Promise<IntegrationStats> {
  if (!isValidCompanyId(companyId)) throw new Error('Empresa no seleccionada.');
  return apiGet<IntegrationStats>(`/v1/integrations/stats?company_id=${encodeURIComponent(companyId.trim())}`);
}

// Bank Accounts
async function getCuentasBancarias(companyId?: string): Promise<CuentaBancariaResponse[]> {
  const qs = companyId ? `?company_id=${companyId}` : '';
  return apiGet<CuentaBancariaResponse[]>(`/v1/integrations/bank/accounts${qs}`);
}

async function getCuentaBancaria(accountId: string): Promise<CuentaBancariaResponse> {
  return apiGet<CuentaBancariaResponse>(`/v1/integrations/bank/accounts/${accountId}`);
}

async function createCuentaBancaria(data: CuentaBancariaCreate): Promise<CuentaBancariaResponse> {
  return apiPost<CuentaBancariaResponse>('/v1/integrations/bank/accounts', data);
}

async function updateCuentaBancaria(accountId: string, data: CuentaBancariaUpdate): Promise<CuentaBancariaResponse> {
  return apiPut<CuentaBancariaResponse>(`/v1/integrations/bank/accounts/${accountId}`, data);
}

async function deleteCuentaBancaria(accountId: string): Promise<void> {
  return apiDelete(`/v1/integrations/bank/accounts/${accountId}`);
}

// Bank Statements (Extractos)
async function getExtractosBancarios(params?: {
  company_id?: string;
  cuenta_bancaria_id?: string;
  estado?: string;
}): Promise<ExtractoBancarioResponse[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.cuenta_bancaria_id) query.push(`cuenta_bancaria_id=${params.cuenta_bancaria_id}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<ExtractoBancarioResponse[]>(`/v1/integrations/bank/statements${qs}`);
}

async function importBankExtractFile(cuentaBancariaId: string, companyId: string, file: File): Promise<{
  message: string;
  cuenta_id: string;
  extracto_id: string;
  movimientos_importados: number;
  filas_ignoradas: number;
}> {
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const response = await fetch(
    buildUrl(`/v1/integrations/bank/import-csv?cuenta_bancaria_id=${encodeURIComponent(cuentaBancariaId)}&company_id=${encodeURIComponent(companyId)}`),
    {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    }
  );
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error de servidor' }));
    const detail = errorData.detail;
    let message: string;
    if (Array.isArray(detail)) {
      message = detail.map((e: { msg?: string }) => e.msg || e).filter(Boolean).join(', ');
    } else if (typeof detail === 'string') {
      message = detail;
    } else {
      message = `Error ${response.status}`;
    }
    throw new Error(message);
  }
  return response.json();
}

async function createExtractoBancario(data: ExtractoBancarioCreate): Promise<ExtractoBancarioResponse> {
  return apiPost<ExtractoBancarioResponse>('/v1/integrations/bank/statements', data);
}

async function deleteExtractoBancario(statementId: string): Promise<void> {
  return apiDelete(`/v1/integrations/bank/statements/${statementId}`);
}

// Bank Movements
async function getMovimientosBancarios(params?: {
  extracto_id?: string;
  cuenta_bancaria_id?: string;
  conciliacion_estado?: string;
  tipo?: string;
  skip?: number;
  limit?: number;
}): Promise<MovimientoBancarioResponse[]> {
  const query: string[] = [];
  if (params?.extracto_id) query.push(`extracto_id=${params.extracto_id}`);
  if (params?.cuenta_bancaria_id) query.push(`cuenta_bancaria_id=${params.cuenta_bancaria_id}`);
  if (params?.conciliacion_estado) query.push(`conciliacion_estado=${params.conciliacion_estado}`);
  if (params?.tipo) query.push(`tipo=${params.tipo}`);
  if (params?.skip) query.push(`skip=${params.skip}`);
  if (params?.limit) query.push(`limit=${params.limit}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<MovimientoBancarioResponse[]>(`/v1/integrations/bank/movements${qs}`);
}

async function createMovimientoBancario(data: MovimientoBancarioCreate): Promise<MovimientoBancarioResponse> {
  return apiPost<MovimientoBancarioResponse>('/v1/integrations/bank/movements', data);
}

async function updateMovimientoBancario(movementId: string, data: MovimientoBancarioUpdate): Promise<MovimientoBancarioResponse> {
  return apiPut<MovimientoBancarioResponse>(`/v1/integrations/bank/movements/${movementId}`, data);
}

async function deleteMovimientoBancario(movementId: string): Promise<void> {
  return apiDelete(`/v1/integrations/bank/movements/${movementId}`);
}

// E-Commerce Connectors
async function getEcommerceConnectors(companyId?: string, plataforma?: string): Promise<EcommerceConnectorResponse[]> {
  const query: string[] = [];
  if (companyId) query.push(`company_id=${companyId}`);
  if (plataforma) query.push(`plataforma=${plataforma}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<EcommerceConnectorResponse[]>(`/v1/integrations/ecommerce/connectors${qs}`);
}

async function getEcommerceConnector(connectorId: string): Promise<EcommerceConnectorResponse> {
  return apiGet<EcommerceConnectorResponse>(`/v1/integrations/ecommerce/connectors/${connectorId}`);
}

async function createEcommerceConnector(data: EcommerceConnectorCreate): Promise<EcommerceConnectorResponse> {
  return apiPost<EcommerceConnectorResponse>('/v1/integrations/ecommerce/connectors', data);
}

async function updateEcommerceConnector(connectorId: string, data: EcommerceConnectorUpdate): Promise<EcommerceConnectorResponse> {
  return apiPut<EcommerceConnectorResponse>(`/v1/integrations/ecommerce/connectors/${connectorId}`, data);
}

async function deleteEcommerceConnector(connectorId: string): Promise<void> {
  return apiDelete(`/v1/integrations/ecommerce/connectors/${connectorId}`);
}

async function testEcommerceConnection(connectorId: string): Promise<{ status: string; message: string }> {
  return apiPost<{ status: string; message: string }>(`/v1/integrations/ecommerce/connectors/${connectorId}/test`);
}

async function syncEcommerceConnector(connectorId: string, tipoSync?: string): Promise<EcommerceSyncLogResponse> {
  const qs = tipoSync ? `?tipo_sync=${tipoSync}` : '';
  return apiPost<EcommerceSyncLogResponse>(`/v1/integrations/ecommerce/connectors/${connectorId}/sync${qs}`);
}

interface EcommerceSyncProductsResponse {
  connector_id: string;
  connector_nombre: string;
  plataforma: string;
  total_procesados: number;
  total_creados: number;
  total_actualizados: number;
  total_errores: number;
  errores: string[];
  sync_log_id: string;
}

interface EcommerceSyncOrdersResponse {
  connector_id: string;
  connector_nombre: string;
  plataforma: string;
  total_procesados: number;
  total_creados: number;
  total_actualizados: number;
  total_errores: number;
  errores: string[];
  sync_log_id: string;
}

interface EcommerceSyncInventoryResponse {
  connector_id: string;
  connector_nombre: string;
  plataforma: string;
  total_procesados: number;
  total_actualizados: number;
  total_errores: number;
  errores: string[];
  sync_log_id: string;
}

async function syncEcommerceProducts(connectorId: string): Promise<EcommerceSyncProductsResponse> {
  return apiPost<EcommerceSyncProductsResponse>(`/v1/integrations/ecommerce/${connectorId}/sync-products`);
}

async function syncEcommerceOrders(connectorId: string): Promise<EcommerceSyncOrdersResponse> {
  return apiPost<EcommerceSyncOrdersResponse>(`/v1/integrations/ecommerce/${connectorId}/sync-orders`);
}

async function syncEcommerceInventory(connectorId: string): Promise<EcommerceSyncInventoryResponse> {
  return apiPost<EcommerceSyncInventoryResponse>(`/v1/integrations/ecommerce/${connectorId}/sync-inventory`);
}

// E-Commerce Sync Logs
async function getEcommerceSyncLogs(params?: {
  connector_id?: string;
  company_id?: string;
  tipo_sync?: string;
  estado?: string;
}): Promise<EcommerceSyncLogResponse[]> {
  const query: string[] = [];
  if (params?.connector_id) query.push(`connector_id=${params.connector_id}`);
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.tipo_sync) query.push(`tipo_sync=${params.tipo_sync}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<EcommerceSyncLogResponse[]>(`/v1/integrations/ecommerce/sync-logs${qs}`);
}

// ============ ML / IA TYPES ============

interface MLPrediccion {
  id: string;
  company_id: string;
  user_id: string;
  tipo: string; // ventas, ingresos, gastos, flujo_caja
  estado: string; // pendiente, completada, con_error
  periodo_desde: string;
  periodo_hasta: string;
  datos_entrada: string | null; // JSON
  resultado: string | null; // JSON
  metricas: string | null; // JSON
  modelo_usado: string;
  confianza: number;
  created_at: string;
  updated_at: string;
}

interface MLPrediccionCreate {
  company_id: string;
  tipo: string;
  periodo_desde: string;
  periodo_hasta: string;
  modelo_usado?: string;
}

interface MLAlertaFraude {
  id: string;
  company_id: string;
  comprobante_id: string | null;
  tipo_deteccion: string;
  severidad: string; // baja, media, alta, critica
  estado: string; // pendiente, confirmado, descartado, investigando
  puntuacion_fraude: number;
  descripcion: string;
  evidencia: string | null; // JSON
  resolucion_nota: string | null;
  resolucion_fecha: string | null;
  resuelto_por: string | null;
  created_at: string;
  updated_at: string;
}

interface MLAlertaFraudeUpdate {
  estado?: string;
  resolucion_nota?: string;
}

interface MLChatbotSesion {
  id: string;
  company_id: string;
  user_id: string;
  estado: string;
  titulo: string;
  contexto: string | null;
  created_at: string;
  updated_at: string;
}

interface MLChatbotMensaje {
  id: string;
  sesion_id: string;
  rol: string; // usuario, asistente, sistema
  contenido: string;
  intencion_detectada: string | null;
  entidades: string | null; // JSON
  created_at: string;
}

interface MLChatRequest {
  sesion_id: string;
  mensaje: string;
}

interface MLChatResponse {
  respuesta: string;
  sesion_id: string;
  intencion_detectada: string | null;
  entidades: string | null;
}

interface MLRecomendacion {
  id: string;
  company_id: string;
  user_id: string;
  tipo: string; // producto, cliente, precio, inventario, financiera
  estado: string; // pendiente, aplicada, descartada
  titulo: string;
  descripcion: string;
  datos_contexto: string | null; // JSON
  impacto_estimado: string | null;
  confianza: number;
  fecha_aplicacion: string | null;
  aplicada_por: string | null;
  created_at: string;
  updated_at: string;
}

interface MLRecomendacionUpdate {
  estado?: string;
}

interface MLCategoriaRegla {
  id: string;
  company_id: string;
  categoria: string;
  subcategoria: string | null;
  palabras_clave: string | null; // JSON
  patron_regex: string | null;
  prioridad: number;
  es_activa: boolean;
  aplicaciones_count: number;
  created_at: string;
  updated_at: string;
}

interface MLCategoriaReglaCreate {
  company_id: string;
  categoria: string;
  subcategoria?: string;
  palabras_clave?: string;
  patron_regex?: string;
  prioridad?: number;
}

interface MLCategoriaReglaUpdate {
  categoria?: string;
  subcategoria?: string;
  palabras_clave?: string;
  patron_regex?: string;
  prioridad?: number;
  es_activa?: boolean;
}

interface MLStats {
  total_predicciones: number;
  predicciones_completadas: number;
  total_alertas_fraude: number;
  alertas_pendientes: number;
  alertas_criticas: number;
  total_recomendaciones: number;
  recomendaciones_pendientes: number;
  recomendaciones_aplicadas: number;
  total_sesiones_chatbot: number;
  sesiones_activas: number;
  total_reglas_categorias: number;
  reglas_activas: number;
}

// ============ ACCOUNTING CORE TYPES ============

interface CuentaContable {
  id: string;
  company_id: string;
  codigo: string;
  nombre: string;
  tipo: string;
  naturaleza: string;
  nivel: number;
  cuenta_padre_id: string | null;
  es_cuenta_movimiento: boolean;
  es_imputable: boolean;
  saldo_inicial: number;
  saldo_actual: number;
  total_debitos: number;
  total_creditos: number;
  descripcion: string | null;
  etiqueta: string | null;
  notas: string | null;
  cuenta_contrapartida_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  codigo_nombre?: string;
}

interface CuentaContableCreate {
  codigo: string;
  nombre: string;
  tipo: string;
  naturaleza: string;
  nivel?: number;
  cuenta_padre_id?: string | null;
  es_cuenta_movimiento?: boolean;
  es_imputable?: boolean;
  saldo_inicial?: number;
  descripcion?: string | null;
  etiqueta?: string | null;
  notas?: string | null;
  cuenta_contrapartida_id?: string | null;
}

interface AsientoDetalleCreate {
  cuenta_contable_id: string;
  debito: number;
  credito: number;
  descripcion?: string | null;
}

interface AsientoContable {
  id: string;
  company_id: string;
  user_id: string;
  periodo_fiscal_id: string | null;
  numero: string;
  fecha: string;
  tipo: string;
  estado: string;
  total_debitos: number;
  total_creditos: number;
  concepto: string;
  referencia_tipo: string | null;
  referencia_id: string | null;
  referencia_secuencial: string | null;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  detalles: AsientoDetalleResponse[];
  is_cuadrado?: boolean;
}

interface AsientoDetalleResponse {
  id: string;
  asiento_id: string;
  cuenta_contable_id: string;
  debito: number;
  credito: number;
  descripcion: string | null;
  cuenta_codigo?: string;
  cuenta_nombre?: string;
}

interface AsientoContableCreate {
  fecha: string;
  tipo?: string;
  concepto: string;
  referencia_tipo?: string | null;
  referencia_id?: string | null;
  referencia_secuencial?: string | null;
  observaciones?: string | null;
  detalles: AsientoDetalleCreate[];
  periodo_fiscal_id?: string | null;
}

interface CuentaPorCobrar {
  id: string;
  company_id: string;
  client_id: string | null;
  comprobante_id: string | null;
  numero_factura: string | null;
  fecha_emision: string;
  fecha_vencimiento: string | null;
  monto_total: number;
  monto_pagado: number;
  monto_pendiente: number;
  estado: string;
  dias_credito: number;
  dias_vencida: number;
  cliente_nombre: string | null;
  cliente_identificacion: string | null;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  rango_vencimiento?: string;
}

interface CuentaPorCobrarCreate {
  client_id?: string | null;
  comprobante_id?: string | null;
  numero_factura?: string | null;
  fecha_emision: string;
  fecha_vencimiento?: string | null;
  monto_total: number;
  dias_credito?: number;
  cliente_nombre?: string | null;
  cliente_identificacion?: string | null;
  observaciones?: string | null;
}

interface Pago {
  id: string;
  company_id: string;
  user_id: string;
  tipo: string;
  numero: string;
  fecha: string;
  monto: number;
  forma_pago: string;
  referencia: string | null;
  cuenta_bancaria_id: string | null;
  cuenta_por_cobrar_id: string | null;
  cuenta_por_pagar_id: string | null;
  tercero_nombre: string | null;
  tercero_identificacion: string | null;
  estado: string;
  observaciones: string | null;
  asiento_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PagoCreate {
  tipo: string;
  fecha: string;
  monto: number;
  forma_pago?: string;
  referencia?: string | null;
  cuenta_bancaria_id?: string | null;
  cuenta_por_cobrar_id?: string | null;
  cuenta_por_pagar_id?: string | null;
  tercero_nombre?: string | null;
  tercero_identificacion?: string | null;
  observaciones?: string | null;
}

interface PeriodoFiscal {
  id: string;
  company_id: string;
  nombre: string;
  anio: number;
  mes: number | null;
  tipo_periodo: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: string;
  fecha_cierre: string | null;
  cerrado_por: string | null;
  total_debitos: number;
  total_creditos: number;
  total_asientos: number;
  observaciones: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PeriodoFiscalCreate {
  nombre: string;
  anio: number;
  mes?: number | null;
  tipo_periodo?: string;
  fecha_inicio: string;
  fecha_fin: string;
  observaciones?: string | null;
}

interface ContabilidadStats {
  total_cuentas: number;
  total_cuentas_activas: number;
  total_asientos: number;
  total_asientos_aprobados: number;
  total_cxc: number;
  total_cxc_pendiente: number;
  total_cxp_pendiente: number;
  total_cobros_mes: number;
  total_pagos_mes: number;
  periodos_abiertos: number;
  periodo_actual: string | null;
}

interface BalanceComprobacionItem {
  codigo: string;
  nombre: string;
  tipo: string;
  nivel: number;
  saldo_deudor: number;
  saldo_acreedor: number;
  total_debitos: number;
  total_creditos: number;
}

interface BalanceComprobacionResponse {
  items: BalanceComprobacionItem[];
  total_debitos: number;
  total_creditos: number;
  total_saldo_deudor: number;
  total_saldo_acreedor: number;
  periodo: string | null;
}

interface EnvejecimientoCarteraItem {
  cliente_id: string | null;
  cliente_nombre: string;
  cliente_identificacion: string | null;
  total: number;
  vigente: number;
  dias_1_30: number;
  dias_31_60: number;
  dias_61_90: number;
  dias_91_180: number;
  dias_mas_180: number;
}

interface EnvejecimientoCarteraResponse {
  items: EnvejecimientoCarteraItem[];
  total_general: number;
  total_vigente: number;
  total_1_30: number;
  total_31_60: number;
  total_61_90: number;
  total_91_180: number;
  total_mas_180: number;
}

// ============ ACCOUNTING CORE API FUNCTIONS ============

async function getContabilidadStats(companyId?: string): Promise<ContabilidadStats> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiGet<ContabilidadStats>(`/v1/accounting/stats${params}`);
}

async function getCuentasContables(companyId?: string, tipo?: string, search?: string): Promise<CuentaContable[]> {
  const params: string[] = [];
  if (companyId) params.push(`company_id=${companyId}`);
  if (tipo) params.push(`tipo=${tipo}`);
  if (search) params.push(`search=${encodeURIComponent(search)}`);
  const qs = params.length ? `?${params.join('&')}` : '';
  return apiGet<CuentaContable[]>(`/v1/accounting/cuentas-contables${qs}`);
}

async function createCuentaContable(data: CuentaContableCreate, companyId?: string): Promise<CuentaContable> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiPost<CuentaContable>(`/v1/accounting/cuentas-contables${params}`, data);
}

async function updateCuentaContable(id: string, data: Partial<CuentaContableCreate>): Promise<CuentaContable> {
  return apiPut<CuentaContable>(`/v1/accounting/cuentas-contables/${id}`, data);
}

async function deleteCuentaContable(id: string): Promise<void> {
  return apiDelete(`/v1/accounting/cuentas-contables/${id}`);
}

async function seedPlanCuentasDefault(companyId: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/cuentas-contables/seed-default/${companyId}`, {});
}

async function getCatalogoOficial(): Promise<{ code: string; name: string; tipo: string; naturaleza: string; level: number }[]> {
  return apiGet(`/v1/accounting/catalogo-oficial`);
}

async function getAsientosContables(companyId?: string, estado?: string, skip?: number, limit?: number): Promise<AsientoContable[]> {
  const params: string[] = [];
  if (companyId) params.push(`company_id=${companyId}`);
  if (estado) params.push(`estado=${estado}`);
  if (skip) params.push(`skip=${skip}`);
  if (limit) params.push(`limit=${limit}`);
  const qs = params.length ? `?${params.join('&')}` : '';
  return apiGet<AsientoContable[]>(`/v1/accounting/asientos-contables${qs}`);
}

async function createAsientoContable(data: AsientoContableCreate, companyId?: string): Promise<AsientoContable> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiPost<AsientoContable>(`/v1/accounting/asientos-contables${params}`, data);
}

async function aprobarAsiento(id: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/asientos-contables/${id}/aprobar`, {});
}

async function anularAsiento(id: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/asientos-contables/${id}/anular`, {});
}

async function getCuentasPorCobrar(companyId?: string, estado?: string): Promise<CuentaPorCobrar[]> {
  const params: string[] = [];
  if (companyId) params.push(`company_id=${companyId}`);
  if (estado) params.push(`estado=${estado}`);
  const qs = params.length ? `?${params.join('&')}` : '';
  return apiGet<CuentaPorCobrar[]>(`/v1/accounting/cuentas-por-cobrar${qs}`);
}

async function createCuentaPorCobrar(data: CuentaPorCobrarCreate, companyId?: string): Promise<CuentaPorCobrar> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiPost<CuentaPorCobrar>(`/v1/accounting/cuentas-por-cobrar${params}`, data);
}

async function getEnvejecimientoCartera(companyId?: string): Promise<EnvejecimientoCarteraResponse> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiGet<EnvejecimientoCarteraResponse>(`/v1/accounting/cuentas-por-cobrar/envejecimiento${params}`);
}

async function getPagos(companyId?: string, tipo?: string): Promise<Pago[]> {
  const params: string[] = [];
  if (companyId) params.push(`company_id=${companyId}`);
  if (tipo) params.push(`tipo=${tipo}`);
  const qs = params.length ? `?${params.join('&')}` : '';
  return apiGet<Pago[]>(`/v1/accounting/pagos${qs}`);
}

async function createPago(data: PagoCreate, companyId?: string): Promise<Pago> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiPost<Pago>(`/v1/accounting/pagos${params}`, data);
}

async function confirmarPago(id: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/pagos/${id}/confirmar`, {});
}

async function anularPago(id: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/pagos/${id}/anular`, {});
}

async function getPeriodosFiscales(companyId?: string, estado?: string): Promise<PeriodoFiscal[]> {
  const params: string[] = [];
  if (companyId) params.push(`company_id=${companyId}`);
  if (estado) params.push(`estado=${estado}`);
  const qs = params.length ? `?${params.join('&')}` : '';
  return apiGet<PeriodoFiscal[]>(`/v1/accounting/periodos-fiscales${qs}`);
}

async function createPeriodoFiscal(data: PeriodoFiscalCreate, companyId?: string): Promise<PeriodoFiscal> {
  const params = companyId ? `?company_id=${companyId}` : '';
  return apiPost<PeriodoFiscal>(`/v1/accounting/periodos-fiscales${params}`, data);
}

async function cerrarPeriodoFiscal(id: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/periodos-fiscales/${id}/cerrar`, {});
}

async function reabrirPeriodoFiscal(id: string): Promise<{ detail: string }> {
  return apiPost<{ detail: string }>(`/v1/accounting/periodos-fiscales/${id}/reabrir`, {});
}

async function getBalanceComprobacion(companyId?: string, anio?: number): Promise<BalanceComprobacionResponse> {
  const params: string[] = [];
  if (companyId) params.push(`company_id=${companyId}`);
  if (anio) params.push(`anio=${anio}`);
  const qs = params.length ? `?${params.join('&')}` : '';
  return apiGet<BalanceComprobacionResponse>(`/v1/accounting/balance-comprobacion${qs}`);
}

// ============ ML / IA API FUNCTIONS ============

async function getMLStats(companyId: string): Promise<MLStats> {
  return apiGet<MLStats>(`/v1/ml-ai/stats?company_id=${companyId}`);
}

async function getMLPredicciones(params?: { company_id?: string; tipo?: string }): Promise<MLPrediccion[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.tipo) query.push(`tipo=${params.tipo}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<MLPrediccion[]>(`/v1/ml-ai/predictions${qs}`);
}

async function createMLPrediccion(data: MLPrediccionCreate): Promise<MLPrediccion> {
  return apiPost<MLPrediccion>('/v1/ml-ai/predictions', data);
}

async function getMLPrediccion(id: string): Promise<MLPrediccion> {
  return apiGet<MLPrediccion>(`/v1/ml-ai/predictions/${id}`);
}

async function deleteMLPrediccion(id: string): Promise<void> {
  return apiDelete(`/v1/ml-ai/predictions/${id}`);
}

async function scanFraude(companyId: string): Promise<{ alertas_creadas: number; message: string }> {
  return apiPost<{ alertas_creadas: number; message: string }>(`/v1/ml-ai/fraud/scan?company_id=${companyId}`);
}

async function getMLAlertasFraude(params?: { company_id?: string; severidad?: string; estado?: string }): Promise<MLAlertaFraude[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.severidad) query.push(`severidad=${params.severidad}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<MLAlertaFraude[]>(`/v1/ml-ai/fraud/alerts${qs}`);
}

async function updateMLAlertaFraude(id: string, data: MLAlertaFraudeUpdate): Promise<MLAlertaFraude> {
  return apiPut<MLAlertaFraude>(`/v1/ml-ai/fraud/alerts/${id}`, data);
}

async function getMLAlertaFraude(id: string): Promise<MLAlertaFraude> {
  return apiGet<MLAlertaFraude>(`/v1/ml-ai/fraud/alerts/${id}`);
}

async function createMLChatbotSesion(companyId: string): Promise<MLChatbotSesion> {
  return apiPost<MLChatbotSesion>('/v1/ml-ai/chatbot/sessions', { company_id: companyId });
}

async function getMLChatbotSesiones(companyId: string): Promise<MLChatbotSesion[]> {
  return apiGet<MLChatbotSesion[]>(`/v1/ml-ai/chatbot/sessions?company_id=${companyId}`);
}

async function sendMLChatMessage(data: MLChatRequest): Promise<MLChatResponse> {
  return apiPost<MLChatResponse>('/v1/ml-ai/chatbot/chat', data);
}

async function getMLChatbotMensajes(sesionId: string): Promise<MLChatbotMensaje[]> {
  return apiGet<MLChatbotMensaje[]>(`/v1/ml-ai/chatbot/sessions/${sesionId}/messages`);
}

async function closeMLChatbotSesion(id: string): Promise<void> {
  return apiDelete(`/v1/ml-ai/chatbot/sessions/${id}`);
}

async function generateMLRecomendaciones(companyId: string): Promise<{ recomendaciones_creadas: number; message: string }> {
  return apiPost<{ recomendaciones_creadas: number; message: string }>(`/v1/ml-ai/recommendations/generate?company_id=${companyId}`);
}

async function getMLRecomendaciones(params?: { company_id?: string; tipo?: string; estado?: string }): Promise<MLRecomendacion[]> {
  const query: string[] = [];
  if (params?.company_id) query.push(`company_id=${params.company_id}`);
  if (params?.tipo) query.push(`tipo=${params.tipo}`);
  if (params?.estado) query.push(`estado=${params.estado}`);
  const qs = query.length ? `?${query.join('&')}` : '';
  return apiGet<MLRecomendacion[]>(`/v1/ml-ai/recommendations${qs}`);
}

async function updateMLRecomendacion(id: string, data: MLRecomendacionUpdate): Promise<MLRecomendacion> {
  return apiPut<MLRecomendacion>(`/v1/ml-ai/recommendations/${id}`, data);
}

async function deleteMLRecomendacion(id: string): Promise<void> {
  return apiDelete(`/v1/ml-ai/recommendations/${id}`);
}

async function getMLCategoriasReglas(companyId: string): Promise<MLCategoriaRegla[]> {
  return apiGet<MLCategoriaRegla[]>(`/v1/ml-ai/categorize/rules?company_id=${companyId}`);
}

async function createMLCategoriaRegla(data: MLCategoriaReglaCreate): Promise<MLCategoriaRegla> {
  return apiPost<MLCategoriaRegla>('/v1/ml-ai/categorize/rules', data);
}

async function updateMLCategoriaRegla(id: string, data: MLCategoriaReglaUpdate): Promise<MLCategoriaRegla> {
  return apiPut<MLCategoriaRegla>(`/v1/ml-ai/categorize/rules/${id}`, data);
}

async function deleteMLCategoriaRegla(id: string): Promise<void> {
  return apiDelete(`/v1/ml-ai/categorize/rules/${id}`);
}

async function categorizeMLDescription(companyId: string, descripcion: string): Promise<{ categoria: string; subcategoria: string | null; confianza: number }> {
  return apiPost<{ categoria: string; subcategoria: string | null; confianza: number }>('/v1/ml-ai/categorize/categorize', { company_id: companyId, descripcion });
}

// ============ CRM EXTENDED TYPES (Pipeline, Leads) ============

interface CRMPipeline {
  id: string;
  name: string;
  description?: string;
  is_default: boolean;
  company_id: string;
  order: number;
  created_at: string;
  stages?: CRMPipelineStage[];
}

interface CRMPipelineStage {
  id: string;
  pipeline_id: string;
  name: string;
  order: number;
  probability_percentage: number;
  color: string;
}

interface CRMLead {
  id: string;
  company_id: string;
  client_id?: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  source: string;
  status: string;
  estimated_value?: number;
  notes?: string;
  next_follow_up?: string;
  converted_to_opportunity: boolean;
  created_at: string;
}

interface CRMLeadCreate {
  company_id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  source?: string;
  status?: string;
  estimated_value?: number;
  notes?: string;
  next_follow_up?: string;
}

interface CRMContactSegment {
  id: string;
  company_id: string;
  name: string;
  description?: string;
  type: string;
  rules?: string;
  color?: string;
  is_active: boolean;
  created_at: string;
}

// CRM Pipeline API functions
async function getCRMPipelines(companyId: string): Promise<CRMPipeline[]> {
  return apiGet<CRMPipeline[]>(`/v1/crm/pipelines?company_id=${companyId}`);
}

async function createCRMPipeline(data: { company_id: string; name: string; description?: string; is_default?: boolean }): Promise<CRMPipeline> {
  return apiPost<CRMPipeline>('/v1/crm/pipelines', data);
}

// CRM Lead API functions
async function getCRMLeads(companyId: string): Promise<CRMLead[]> {
  return apiGet<CRMLead[]>(`/v1/crm/leads?company_id=${companyId}`);
}

async function createCRMLead(data: CRMLeadCreate): Promise<CRMLead> {
  return apiPost<CRMLead>('/v1/crm/leads', data);
}

async function updateCRMLead(id: string, data: Partial<CRMLeadCreate>): Promise<CRMLead> {
  return apiPut<CRMLead>(`/v1/crm/leads/${id}`, data);
}

async function convertCRMLead(id: string, data: { company_id: string; titulo: string; valor_estimado?: number }): Promise<CRMOpportunity> {
  return apiPost<CRMOpportunity>(`/v1/crm/leads/${id}/convert`, data);
}

async function moveCRMOpportunityStage(id: string, data: { stage_id: string }): Promise<CRMOpportunity> {
  return apiPut<CRMOpportunity>(`/v1/crm/opportunities/${id}/stage`, data);
}

// ============ HR EXTENDED API FUNCTIONS ============

interface CargaFamiliar {
  id: string;
  employee_id: string;
  nombres: string;
  apellidos: string;
  parentesco: string;
  fecha_nacimiento?: string;
  identificacion?: string;
  discapacidad: boolean;
  porcentaje_discapacidad?: number | null;
  tipo_discapacidad?: string | null;
  es_estudiante: boolean;
  created_at: string;
}

interface CargaFamiliarCreate {
  employee_id: string;
  nombres: string;
  apellidos: string;
  parentesco: string;
  fecha_nacimiento?: string;
  identificacion?: string;
  discapacidad?: boolean;
  porcentaje_discapacidad?: number;
  tipo_discapacidad?: string;
  es_estudiante?: boolean;
}

interface AsistenciaRecord {
  id: string;
  company_id: string;
  employee_id: string;
  fecha: string;
  hora_entrada?: string;
  hora_salida?: string;
  horas_trabajadas: number;
  tipo: string;
  observacion?: string;
  created_at: string;
  employee_name?: string;
}

interface Liquidacion {
  id: string;
  company_id: string;
  employee_id: string;
  fecha: string;
  motivo: string;
  sueldo_ultimo_mes: number;
  decimo_tercero: number;
  decimo_cuarto: number;
  vacaciones: number;
  fondo_reserva: number;
  otros_ingresos: number;
  total_ingresos: number;
  iess_personal: number;
  anticipos: number;
  otros_descuentos: number;
  total_descuentos: number;
  liquido_recibir: number;
  estado: string;
  employee_name?: string;
  created_at: string;
}

interface UtilidadRecord {
  id: string;
  company_id: string;
  employee_id: string;
  periodo_anio: number;
  utilidad_total: number;
  dias_trabajados: number;
  valor_recibido: number;
  employee_name?: string;
  created_at: string;
}

interface IRCalculation {
  base_imponible: number;
  impuesto: number;
  fraccion_basica: number;
  exceso: number;
  tasa: number;
  impuesto_fraccion: number;
  fecha: string;
}

async function createCargaFamiliar(data: CargaFamiliarCreate): Promise<CargaFamiliar> {
  return apiPost<CargaFamiliar>('/v1/payroll/cargas-familiares', data);
}

async function getCargasFamiliares(employeeId: string): Promise<CargaFamiliar[]> {
  return apiGet<CargaFamiliar[]>(`/v1/payroll/cargas-familiares/${employeeId}`);
}

async function deleteCargaFamiliar(id: string): Promise<void> {
  return apiDelete(`/v1/payroll/cargas-familiares/${id}`);
}

async function createEvaluacion(data: Record<string, unknown>): Promise<unknown> {
  return apiPost('/v1/payroll/evaluaciones', data);
}

async function getEvaluaciones(companyId: string): Promise<unknown[]> {
  return apiGet(`/v1/payroll/evaluaciones?company_id=${companyId}`);
}

async function createAsistencia(data: Record<string, unknown>): Promise<AsistenciaRecord> {
  return apiPost<AsistenciaRecord>('/v1/payroll/asistencia', data);
}

async function getAsistencia(companyId: string): Promise<AsistenciaRecord[]> {
  return apiGet<AsistenciaRecord[]>(`/v1/payroll/asistencia?company_id=${companyId}`);
}

async function calcularLiquidacion(data: { company_id: string; employee_id: string; tipo: string; fecha_fin: string }): Promise<Liquidacion> {
  return apiPost<Liquidacion>('/v1/payroll/liquidacion', data);
}

async function getLiquidaciones(companyId: string): Promise<Liquidacion[]> {
  return apiGet<Liquidacion[]>(`/v1/payroll/liquidacion?company_id=${companyId}`);
}

async function aprobarLiquidacion(id: string): Promise<Liquidacion> {
  return apiPut<Liquidacion>(`/v1/payroll/liquidacion/${id}/approve`, {});
}

async function calcularUtilidades(data: { company_id: string; anio: number; total_utilidades: number; porcentaje_trabajadores?: number }): Promise<UtilidadRecord[]> {
  return apiPost<UtilidadRecord[]>('/v1/payroll/utilidades', data);
}

async function getUtilidades(companyId: string): Promise<UtilidadRecord[]> {
  return apiGet<UtilidadRecord[]>(`/v1/payroll/utilidades?company_id=${companyId}`);
}

async function calcularIR(data: { ingreso_gravable: number; periodo: string }): Promise<IRCalculation> {
  return apiPost<IRCalculation>('/v1/payroll/calcular-ir', data);
}

// ============= Sub-Cuentas (cuentas de empleados con acceso limitado) =============
interface SubAccount {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  parent_user_id: string;
  allowed_modules: string[];
  must_change_password: boolean;
  created_at: string;
  email_warning?: string | null;
}

const SUBACCOUNT_MODULES: { key: string; label: string }[] = [
  { key: 'dashboard', label: 'Panel principal' },
  { key: 'facturacion', label: 'Facturación y comprobantes' },
  { key: 'clientes', label: 'Clientes' },
  { key: 'proveedores', label: 'Proveedores' },
  { key: 'inventario', label: 'Inventario y almacenes' },
  { key: 'compras', label: 'Compras y cuentas por pagar' },
  { key: 'contabilidad', label: 'Contabilidad' },
  { key: 'presupuestos', label: 'Presupuestos' },
  { key: 'proyectos', label: 'Proyectos' },
  { key: 'crm', label: 'CRM' },
  { key: 'rh', label: 'Recursos Humanos' },
  { key: 'integraciones', label: 'Integraciones y ecommerce' },
  { key: 'pos', label: 'Punto de venta (POS)' },
  { key: 'bi', label: 'Business Intelligence' },
  { key: 'ml_ai', label: 'ML / IA' },
  { key: 'sri', label: 'Catálogos SRI' },
  { key: 'configuracion', label: 'Configuración' },
];

async function getSubAccounts(): Promise<SubAccount[]> {
  return apiGet<SubAccount[]>('/v1/sub-accounts');
}

async function createSubAccount(data: { email: string; full_name: string; password: string; allowed_modules: string[] }): Promise<SubAccount> {
  return apiPost<SubAccount>('/v1/sub-accounts', data);
}

async function updateSubAccount(id: string, data: { full_name?: string; allowed_modules?: string[]; is_active?: boolean; password?: string }): Promise<SubAccount> {
  return apiPut<SubAccount>(`/v1/sub-accounts/${id}`, data);
}

async function deleteSubAccount(id: string): Promise<void> {
  return apiDelete(`/v1/sub-accounts/${id}`);
}

// ============= Business Intelligence (BI) =============
interface BIKPIs {
  ventas_totales: number; variacion_ventas: number; comprobantes_emitidos: number;
  comprobantes_autorizados: number; comprobantes_rechazados: number; tasa_aprobacion: number;
  ticket_promedio: number; iva_recaudado: number; clientes_activos: number;
  productos_vendidos: number; cuentas_por_cobrar: number; cuentas_por_pagar: number;
  inventario_valor: number; empleados_activos: number; nomina_total: number;
  pos_ventas_hoy: number; pos_tickets_hoy: number;
}
interface BIVentaMensual { mes: string; total: number; cantidad: number; }
interface BIVentaPorTipo { tipo_comprobante: string; descripcion: string; total: number; cantidad: number; porcentaje: number; }
interface BITopProducto { product_id: string; producto: string; descripcion: string; codigo: string; cantidad_vendida: number; total_venta: number; }
interface BITopCliente { client_id: string; cliente: string; razon_social: string; identificacion: string; cantidad_comprobantes: number; total_compras: number; }
interface BIFlujoEfectivo { mes: string; ingresos: number; egresos: number; saldo: number; }
interface BIAlerta { id: string; tipo: string; titulo: string; mensaje: string; fecha: string; categoria: string; }
interface BICuadroMando {
  kpis_resumen: Record<string, number>;
  indicadores_cumplimiento: Array<{ nombre: string; valor: number; objetivo: number; estado: string }>;
  tendencias: Array<{ nombre_mes: string; mes: string; ventas: number; comprobantes: number; valor: number }>;
  estado_general: number;
}

async function getBIKPIs(params: { company_id?: string }): Promise<BIKPIs> {
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  return apiGet<BIKPIs>(`/v1/bi/kpis${qs}`);
}
async function getBIVentasMensuales(params: { company_id?: string }): Promise<BIVentaMensual[]> {
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  return apiGet<BIVentaMensual[]>(`/v1/bi/ventas-mensuales${qs}`);
}
async function getBIVentasPorTipo(params: { company_id?: string }): Promise<BIVentaPorTipo[]> {
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  return apiGet<BIVentaPorTipo[]>(`/v1/bi/ventas-por-tipo${qs}`);
}
async function getBITopProductos(params: { company_id?: string; limite?: number }): Promise<BITopProducto[]> {
  const p = new URLSearchParams();
  if (params.company_id) p.set('company_id', params.company_id);
  if (params.limite) p.set('limite', String(params.limite));
  const qs = p.toString() ? `?${p.toString()}` : '';
  return apiGet<BITopProducto[]>(`/v1/bi/top-productos${qs}`);
}
async function getBITopClientes(params: { company_id?: string; limite?: number }): Promise<BITopCliente[]> {
  const p = new URLSearchParams();
  if (params.company_id) p.set('company_id', params.company_id);
  if (params.limite) p.set('limite', String(params.limite));
  const qs = p.toString() ? `?${p.toString()}` : '';
  return apiGet<BITopCliente[]>(`/v1/bi/top-clientes${qs}`);
}
async function getBIFlujoEfectivo(params: { company_id?: string }): Promise<BIFlujoEfectivo[]> {
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  return apiGet<BIFlujoEfectivo[]>(`/v1/bi/flujo-efectivo${qs}`);
}
async function getBIAlertas(params: { company_id?: string }): Promise<BIAlerta[]> {
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  return apiGet<BIAlerta[]>(`/v1/bi/alertas${qs}`);
}
async function getBICuadroMando(params: { company_id?: string }): Promise<BICuadroMando> {
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  return apiGet<BICuadroMando>(`/v1/bi/cuadro-mando${qs}`);
}
async function downloadBIPowerBIFile(params: { company_id?: string }): Promise<Blob> {
  const token = getToken();
  const qs = params.company_id ? `?company_id=${params.company_id}` : '';
  const response = await fetch(`${API_BASE}/v1/bi/export-powerbi-file${qs}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Error descargando archivo Power BI');
  return response.blob();
}

export {
  API_BASE,
  buildUrl,
  getToken,
  setToken,
  clearTokens,
  getUserCache,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  login,
  register,
  getMe,
  refreshToken,
  logout,
  forgotPassword,
  forceChangePassword,
  adminResetUserPassword,
  updateUserProfile,
  getCompanies,
  getCompany,
  createCompany,
  uploadCompanyFile,
  updateCompany,
  deleteCompany,
  getCompanyConfig,
  updateCompanyConfig,
  getClamavStatus,
  getSRITipoImpuesto,
  getSRIIVARates,
  getSRIDocumentTypes,
  getSRITipoIdentificacion,
  getSRIMoneda,
  getSRIFormaPago,
  getAdminStats,
  getAdminUsers,
  modifyUserLicense,
  toggleUserActive,
  modifyUserTrial,
  endUserTrial,
  getTrialUsers,
  getSystemHealth,
  getSecurityIssues,
  getLicenseStatus,
  getLicenseOptions,
  renewLicenseViaWhatsApp,
  checkLicenseExpiry,
  checkFeatureAccess,
  checkLicenseLimit,
  getBackups,
  createBackup,
  downloadBackup,
  restoreBackup,
  // RIDE download
  downloadRIDE,
  // Email and process
  enviarComprobanteEmail,
  procesarComprobante,
  // Validation and correction
  validarComprobante,
  corregirComprobante,
  getComprobanteStats as getInvoiceStats,
  getUserConfig,
  uploadDigitalSignature,
  getSignatureStatus,
  toggleVirusTotal,
  configureSMTP,
  testSMTP,
  switchEnvironmentMode,
  updateProfile,
  setBackupKey,
  changePassword,
  uploadCompanyLogo,
  getCompanyLogoBlobUrl,
  deleteDigitalSignature,
  deleteCompanyLogo,
  validateSignature,
  getSignatureInfo,
  // Comprobante functions
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
  // Product functions
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  // Client functions
  getClients,
  createClient,
  updateClient,
  deleteClient,
  // Proforma functions
  getProformas,
  getProforma,
  createProforma,
  updateProforma,
  deleteProforma,
  getProformaStats,
  enviarProforma,
  convertirProforma,
  downloadProformaPDF,
  // SRI Catalogs
  getSRICatalogs,
  getSRICatalogsData,
  // RUC lookup
  lookupRuc,
  // Kardex functions
  getKardexMovements,
  getProductKardex,
  getProductSaldo,
  createKardexMovement,
  createKardexAjuste,
  // Employee functions
  getEmployees,
  getEmployee,
  createEmployee,
  updateEmployee,
  deactivateEmployee,
  recordEmployeeCese,
  getEmployeeDepartments,
  // Payroll functions
  generatePayroll,
  getPayrolls,
  getPayroll,
  approvePayroll,
  payPayroll,
  getEmployeePayrollHistory,
  calculateDecimoTercero,
  calculateDecimoCuarto,
  getVacacionesBalance,
  getFondosReservaBalance,
  getIESSReport,
  getRDEPReport,
  // Supplier functions
  getSuppliers,
  getSupplier,
  createSupplier,
  updateSupplier,
  deleteSupplier,
  // Purchase Order functions
  getOrdenesCompra,
  createOrdenCompra,
  getOrdenCompra,
  deleteOrdenCompra,
  // Accounts Payable functions
  getCuentasPorPagar,
  createCuentaPorPagar,
  registerPaymentCuentaPorPagar,
  // Purchase Retention functions
  getRetencionesCompra,
  createRetencionCompra,
  updateRetencionCompra,
  deleteRetencionCompra,
  // Audit Log functions
  getAuditLogs,
  getAuditStats,
  // Email Template functions
  getEmailTemplates,
  createEmailTemplate,
  updateEmailTemplate,
  deleteEmailTemplate,
  previewEmailTemplate,
  previewEmailTemplateCustom,
  sendEmailWithTemplate,
  // Import/Export functions
  importProductsExcel,
  importProductsCSV,
  importClientsExcel,
  importClientsCSV,
  exportProductsExcel,
  exportProductsCSV,
  exportComprobantesExcel,
  exportComprobantesXMLZip,
  // Warehouse functions (Phase 9)
  getWarehouses,
  getWarehouse,
  createWarehouse,
  updateWarehouse,
  deleteWarehouse,
  getWarehouseLocations,
  createWarehouseLocation,
  updateWarehouseLocation,
  deleteWarehouseLocation,
  getWarehouseStock,
  createWarehouseTransfer,
  getWarehouseTransfers,
  getWarehouseTransfer,
  sendWarehouseTransfer,
  receiveWarehouseTransfer,
  cancelWarehouseTransfer,
  getDetailedKardex,
  // POS functions (Phase 10)
  openPOSSession,
  getPOSSessions,
  getPOSSession,
  closePOSSession,
  getPOSSessionResumen,
  createPOSArqueo,
  createPOSTicket,
  getPOSTickets,
  getPOSTicket,
  voidPOSTicket,
  getPOSTicketPrintData,
  searchProductByBarcode,
  // Presupuestos (Budget) functions
  getPresupuestos,
  getPresupuesto,
  createPresupuesto,
  updatePresupuesto,
  deletePresupuesto,
  approvePresupuesto,
  closePresupuesto,
  addPresupuestoCuenta,
  updatePresupuestoCuenta,
  deletePresupuestoCuenta,
  registerEjecucionMensual,
  getEjecucionMensual,
  getPresupuestoAlertas,
  markAlertaRead,
  markAlertaResolved,
  getAlertaSummary,
  // CRM API functions
  getCRMOpportunities,
  getCRMOpportunity,
  createCRMOpportunity,
  updateCRMOpportunity,
  deleteCRMOpportunity,
  moveCRMOpportunity,
  convertCRMOpportunityToProforma,
  convertCRMOpportunityToInvoice,
  getCRMActivities,
  createCRMActivity,
  updateCRMActivity,
  deleteCRMActivity,
  completeCRMActivity,
  getCRMSegments,
  createCRMSegment,
  updateCRMSegment,
  deleteCRMSegment,
  assignClientToSegment,
  getCRMAutomations,
  createCRMAutomation,
  toggleCRMAutomation,
  deleteCRMAutomation,
  getCRMStats,
  // CRM Extended (Pipeline, Leads)
  getCRMPipelines,
  createCRMPipeline,
  getCRMLeads,
  createCRMLead,
  updateCRMLead,
  convertCRMLead,
  moveCRMOpportunityStage,
  // HR Extended functions
  createCargaFamiliar,
  getCargasFamiliares,
  deleteCargaFamiliar,
  createEvaluacion,
  getEvaluaciones,
  createAsistencia,
  getAsistencia,
  calcularLiquidacion,
  getLiquidaciones,
  aprobarLiquidacion,
  calcularUtilidades,
  getUtilidades,
  calcularIR,
  getSubAccounts,
  createSubAccount,
  updateSubAccount,
  deleteSubAccount,
  SUBACCOUNT_MODULES,
  type SubAccount,
  getComparativoPresupuestario,
  getPresupuestoComparativo,
  getPresupuestoStats,
  recalcularPresupuesto,
  // Project (Phase 14) functions
  getProyectos,
  getProyecto,
  createProyecto,
  updateProyecto,
  deleteProyecto,
  getProyectoStats,
  recalcularProyecto,
  getProyectoTareas,
  createProyectoTarea,
  updateProyectoTarea,
  deleteProyectoTarea,
  getProyectoRecursos,
  createProyectoRecurso,
  updateProyectoRecurso,
  deleteProyectoRecurso,
  getProyectoTimesheets,
  createProyectoTimesheet,
  updateProyectoTimesheet,
  deleteProyectoTimesheet,
  getProyectoCostos,
  createProyectoCosto,
  deleteProyectoCosto,
  // Integration (Phase 15) functions
  getIntegrationStats,
  getCuentasBancarias,
  getCuentaBancaria,
  createCuentaBancaria,
  updateCuentaBancaria,
  deleteCuentaBancaria,
  getExtractosBancarios,
  createExtractoBancario,
  importBankExtractFile,
  deleteExtractoBancario,
  getMovimientosBancarios,
  createMovimientoBancario,
  updateMovimientoBancario,
  deleteMovimientoBancario,
  getEcommerceConnectors,
  getEcommerceConnector,
  createEcommerceConnector,
  updateEcommerceConnector,
  deleteEcommerceConnector,
  testEcommerceConnection,
  syncEcommerceConnector,
  syncEcommerceProducts,
  syncEcommerceOrders,
  syncEcommerceInventory,
  getEcommerceSyncLogs,
  // ML/IA functions (Phase 16)
  getMLStats,
  getMLPredicciones,
  createMLPrediccion,
  getMLPrediccion,
  deleteMLPrediccion,
  scanFraude,
  getMLAlertasFraude,
  updateMLAlertaFraude,
  getMLAlertaFraude,
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
  // Accounting Core functions
  getContabilidadStats,
  getCuentasContables,
  createCuentaContable,
  updateCuentaContable,
  deleteCuentaContable,
  seedPlanCuentasDefault,
  getCatalogoOficial,
  getAsientosContables,
  createAsientoContable,
  aprobarAsiento,
  anularAsiento,
  getCuentasPorCobrar,
  createCuentaPorCobrar,
  getEnvejecimientoCartera,
  getPagos,
  createPago,
  confirmarPago,
  anularPago,
  getPeriodosFiscales,
  createPeriodoFiscal,
  cerrarPeriodoFiscal,
  reabrirPeriodoFiscal,
  getBalanceComprobacion,
  // Business Intelligence functions
  getBIKPIs,
  getBIVentasMensuales,
  getBIVentasPorTipo,
  getBITopProductos,
  getBITopClientes,
  getBIFlujoEfectivo,
  getBIAlertas,
  getBICuadroMando,
  downloadBIPowerBIFile,
};

export type {
  AuthResponse,
  User,
  Company,
  SRICatalog,
  SRIIVARate,
  SRIDocumentType,
  SRICodeName,
  AdminStats,
  AdminUser,
  SecurityIssue,
  LicenseStatus,
  LicenseOptions,
  BackupInfo,
  BackupListResponse,
  CreateBackupResponse,
  RestoreBackupResponse,
  ComprobanteStatsResponse as InvoiceStats,
  UserConfig,
  SignatureValidation,
  // Comprobante types
  ComprobanteDetalleCreate,
  ComprobanteCreate,
  ComprobanteDetalleResponse,
  ComprobanteResponse,
  ComprobanteListResponse,
  ComprobanteStatsResponse,
  // Validation types
  ValidationIssue,
  ValidationResult,
  CorreccionComprobante,
  // Product types
  ProductCreate,
  ProductResponse,
  // Client types
  ClientCreate,
  ClientResponse,
  // Proforma types
  ProformaDetalleCreate,
  ProformaCreate,
  ProformaDetalleResponse,
  ProformaResponse,
  ProformaListResponse,
  ProformaStatsResponse,
  // Kardex types
  KardexMovement,
  KardexCreate,
  KardexSaldo,
  KardexAjuste,
  // Employee types
  Employee,
  EmployeeCreate,
  EmployeeUpdate,
  EmployeeCese,
  // Payroll types
  RolPagoDetalle,
  RolPago,
  RolPagoFull,
  PayrollGenerate,
  // Supplier types
  Supplier,
  SupplierCreate,
  // Purchase Order types
  OrdenCompra,
  OrdenCompraCreate,
  // Accounts Payable types
  CuentaPorPagar,
  // Purchase Retention types
  RetencionCompra,
  // Audit Log types
  AuditLogEntry,
  // Email Template types
  EmailTemplate,
  // Warehouse types (Phase 9)
  Warehouse,
  WarehouseCreate,
  WarehouseUpdate,
  WarehouseLocation,
  WarehouseLocationCreate,
  WarehouseLocationUpdate,
  WarehouseStock,
  WarehouseTransfer,
  WarehouseTransferDetalle,
  WarehouseTransferCreate,
  WarehouseKardexDetalle,
  // POS types (Phase 10)
  POSCashSession,
  POSCashSessionOpen,
  POSTicket,
  POSTicketDetalle,
  POSTicketCreate,
  POSArqueo,
  POSArqueoCreate,
  POSProductSearchResult,
  POSTicketPrintData,
  POSCashSessionResumen,
  // Presupuestos (Budget) types
  PresupuestoAnual,
  PresupuestoCuenta,
  PresupuestoEjecucionMensual,
  PresupuestoAlerta,
  PresupuestoAnualCreate,
  PresupuestoCuentaCreate,
  PresupuestoStats,
  ComparativoCuenta,
  ComparativoGeneral,
  AlertaSummary,
  // Project (Phase 14) types
  ProyectoResponse,
  ProyectoCreate,
  ProyectoUpdate,
  ProyectoTareaResponse,
  ProyectoTareaCreate,
  ProyectoTareaUpdate,
  ProyectoRecursoResponse,
  ProyectoRecursoCreate,
  ProyectoRecursoUpdate,
  ProyectoTimesheetResponse,
  ProyectoTimesheetCreate,
  ProyectoTimesheetUpdate,
  ProyectoCostoResponse,
  ProyectoCostoCreate,
  ProyectoStats,
  // CRM types
  CRMOpportunity,
  CRMOpportunityCreate,
  CRMOpportunityUpdate,
  CRMActivity,
  CRMActivityCreate,
  CRMActivityUpdate,
  CRMSegment,
  CRMSegmentCreate,
  CRMAutomation,
  CRMAutomationCreate,
  CRMStats,
  // CRM Extended types
  CRMPipeline,
  CRMPipelineStage,
  CRMLead,
  CRMLeadCreate,
  CRMContactSegment,
  // HR Extended types
  CargaFamiliar,
  CargaFamiliarCreate,
  AsistenciaRecord,
  Liquidacion,
  UtilidadRecord,
  IRCalculation,
  // Integration (Phase 15) types
  CuentaBancariaResponse,
  CuentaBancariaCreate,
  CuentaBancariaUpdate,
  ExtractoBancarioResponse,
  ExtractoBancarioCreate,
  MovimientoBancarioResponse,
  MovimientoBancarioCreate,
  MovimientoBancarioUpdate,
  EcommerceConnectorResponse,
  EcommerceConnectorCreate,
  EcommerceConnectorUpdate,
  EcommerceSyncLogResponse,
  IntegrationStats,
  // ML/IA types (Phase 16)
  MLPrediccion,
  MLPrediccionCreate,
  MLAlertaFraude,
  MLAlertaFraudeUpdate,
  MLChatbotSesion,
  MLChatbotMensaje,
  MLChatRequest,
  MLChatResponse,
  MLRecomendacion,
  MLRecomendacionUpdate,
  MLCategoriaRegla,
  MLCategoriaReglaCreate,
  MLCategoriaReglaUpdate,
  MLStats,
  // Accounting types (Core Contable)
  CuentaContable,
  CuentaContableCreate,
  AsientoContable,
  AsientoContableCreate,
  AsientoDetalleCreate,
  CuentaPorCobrar,
  CuentaPorCobrarCreate,
  Pago,
  PagoCreate,
  PeriodoFiscal,
  PeriodoFiscalCreate,
  ContabilidadStats,
  BalanceComprobacionResponse,
  EnvejecimientoCarteraResponse,
  // Business Intelligence types
  BIKPIs,
  BIVentaMensual,
  BIVentaPorTipo,
  BITopProducto,
  BITopCliente,
  BIFlujoEfectivo,
  BIAlerta,
  BICuadroMando,
};
