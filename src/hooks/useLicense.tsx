/**
 * Hook para verificación de licencias y feature gating
 * Permite verificar si el usuario tiene acceso a funcionalidades según su plan
 */

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  getLicenseStatus,
  checkFeatureAccess,
  checkLicenseLimit,
  type LicenseStatus as LicenseStatusType,
} from '@/lib/api';

export interface FeatureCheckResult {
  feature: string;
  hasAccess: boolean;
  currentTier: string | null;
  minimumTierRequired: string | null;
  message: string;
}

export interface LimitCheckResult {
  limitType: string;
  max: number;
  current: number;
  available: number;
  isAtLimit: boolean;
  companyId?: string;
  period?: string;
}

interface UseLicenseReturn {
  license: LicenseStatusType | null;
  loading: boolean;
  refreshLicense: () => Promise<void>;
  checkFeature: (featureName: string) => Promise<FeatureCheckResult>;
  checkLimit: (limitType: string, companyId?: string) => Promise<LimitCheckResult>;
  hasFeature: (featureName: string) => boolean;
  isAtLimit: (limitType: string, companyId?: string) => boolean;
  showUpgradePrompt: (featureName?: string) => void;
  canCreate: (limitType: string, companyId?: string) => Promise<boolean>;
}

// Features disponibles en el sistema
export const LICENSE_FEATURES = {
  // Disponibles en todos los planes
  ELECTRONIC_INVOICING: 'electronic_invoicing',
  BASIC_ACCOUNTING: 'basic_accounting',
  INVENTORY: 'inventory',
  PROFORMAS: 'proformas',

  // Plan Trimestral+
  POS: 'pos',
  PAYROLL: 'payroll',
  BANKING_INTEGRATION: 'banking_integration',

  // Plan Semestral+
  MULTI_WAREHOUSE: 'multi_warehouse',
  BUDGETS: 'budgets',
  PROJECTS: 'projects',
  CRM: 'crm',
  ML_PREDICTIONS: 'ml_predictions',
  ECOMMERCE_INTEGRATION: 'ecommerce_integration',
  CUSTOM_REPORTS: 'custom_reports',

  // Plan Anual
  API_ACCESS: 'api_access',
  PRIORITY_SUPPORT: 'priority_support',
} as const;

export type FeatureKey = keyof typeof LICENSE_FEATURES;

// Tipo para los valores de feature (minúsculas, usados como claves en FEATURE_LABELS)
export type FeatureValue = typeof LICENSE_FEATURES[keyof typeof LICENSE_FEATURES];

// Mapeo de características a nombres legibles
// Las claves son los valores de LICENSE_FEATURES (minúsculas): 'pos', 'payroll', etc.
export const FEATURE_LABELS = {
  electronic_invoicing: 'Facturación Electrónica',
  basic_accounting: 'Contabilidad Básica',
  inventory: 'Inventario',
  proformas: 'Proformas',
  pos: 'Punto de Venta (POS)',
  payroll: 'Nómina (RRHH)',
  banking_integration: 'Integración Bancaria',
  multi_warehouse: 'Multi-Almacén',
  budgets: 'Presupuestos',
  projects: 'Proyectos',
  crm: 'CRM',
  ml_predictions: 'ML / IA',
  ecommerce_integration: 'E-commerce',
  custom_reports: 'Reportes Personalizados',
  api_access: 'API Access',
  priority_support: 'Soporte Prioritario',
} as const satisfies Record<FeatureValue, string>;

export function useLicense(): UseLicenseReturn {
  const [license, setLicense] = useState<LicenseStatusType | null>(null);
  const [loading, setLoading] = useState(true);
  const [_featureCache, _setFeatureCache] = useState<Record<string, boolean>>({});

  const loadLicense = useCallback(async () => {
    try {
      const status = await getLicenseStatus();
      setLicense(status);
    } catch (error) {
      console.error('Error loading license:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLicense();
  }, [loadLicense]);

  const checkFeature = useCallback(async (featureName: string): Promise<FeatureCheckResult> => {
    try {
      const result = await checkFeatureAccess(featureName);
      return {
        feature: result.feature,
        hasAccess: result.has_access,
        currentTier: result.current_tier,
        minimumTierRequired: result.minimum_tier_required,
        message: result.message,
      };
    } catch (error) {
      console.error('Error checking feature:', error);
      return {
        feature: featureName,
        hasAccess: false,
        currentTier: license?.license_type || null,
        minimumTierRequired: null,
        message: 'Error al verificar acceso',
      };
    }
  }, [license?.license_type]);

  const checkLimit = useCallback(async (limitType: string, companyId?: string): Promise<LimitCheckResult> => {
    try {
      const result = await checkLicenseLimit(limitType, companyId);
      return {
        limitType: result.limit_type,
        max: result.max,
        current: result.current,
        available: result.available,
        isAtLimit: result.is_at_limit,
        companyId: result.company_id,
        period: result.period,
      };
    } catch (error) {
      console.error('Error checking limit:', error);
      return {
        limitType,
        max: 0,
        current: 0,
        available: 0,
        isAtLimit: true,
      };
    }
  }, []);

  const hasFeature = useCallback((featureName: string): boolean => {
    // Features siempre disponibles (todos los planes)
    const alwaysAvailable = ['electronic_invoicing', 'basic_accounting', 'inventory', 'proformas'];
    if (alwaysAvailable.includes(featureName)) {
      return true;
    }

    // Durante el período de prueba ACTIVO hay acceso completo a todas las funcionalidades.
    // Se usa trial_active (basado en fechas), no is_trial (flag permanente): cuando la
    // prueba expira, el acceso premium se restringe automáticamente según el plan.
    if (license?.trial_active) return true;

    // Verificar según el tipo de licencia
    const tier = license?.license_type;
    if (!tier) return false;

    // Plan Anual - todo disponible
    if (tier === 'annual') return true;

    // Plan Semestral - casi todo excepto anual
    if (tier === 'semiannual') {
      return !['api_access', 'priority_support'].includes(featureName);
    }

    // Plan Trimestral
    if (tier === 'quarterly') {
      const quarterlyFeatures = ['pos', 'payroll', 'banking_integration'];
      return quarterlyFeatures.includes(featureName);
    }

    // Plan Mensual - solo básicos
    return false;
  }, [license?.license_type, license?.trial_active]);

  const isAtLimit = useCallback((_limitType: string, _companyId?: string): boolean => {
    // Para trial, usar límites del plan mensual como referencia
    const tier = license?.license_type || 'monthly';

    // Límites por defecto (plan mensual)
    const limits: Record<string, number> = {
      companies: 1,
      users: 2,
      employees: 5,
      products: 100,
      comprobantes: 50,
    };

    // Ajustar según el plan
    if (tier === 'quarterly') {
      limits.companies = 2;
      limits.users = 5;
      limits.employees = 15;
      limits.products = 500;
      limits.comprobantes = 200;
    } else if (tier === 'semiannual') {
      limits.companies = 5;
      limits.users = 10;
      limits.employees = 50;
      limits.products = 2000;
      limits.comprobantes = 500;
    } else if (tier === 'annual') {
      return false; // Ilimitado
    }

    // Esta es una verificación optimista
    // Para verificación real, usar checkLimit()
    return false;
  }, [license?.license_type]);

  const showUpgradePrompt = useCallback((featureName?: string) => {
    const featureLabel = featureName ? FEATURE_LABELS[featureName as FeatureValue] || featureName : '';

    toast.error(
      featureName
        ? `${featureLabel} no está incluido en tu plan actual. Actualiza para acceder.`
        : 'Esta funcionalidad no está incluida en tu plan actual.',
      {
        description: 'Contacta por WhatsApp para ver opciones de actualización',
        action: {
          label: 'Ver Planes',
          onClick: () => {
            window.open('https://wa.me/593960068866?text=' + encodeURIComponent('Hola, quiero información sobre los planes de ContaEC. Mi correo es: ' + (typeof window !== 'undefined' ? localStorage.getItem('contaec_user') || '' : '')), '_blank');
          },
        },
      }
    );
  }, []);

  const canCreate = useCallback(async (limitType: string, companyId?: string): Promise<boolean> => {
    // Verificación real usando la API
    try {
      const result = await checkLicenseLimit(limitType, companyId);
      return !result.is_at_limit;
    } catch (error) {
      console.error('Error checking limit:', error);
      return false;
    }
  }, []);

  return {
    license,
    loading,
    refreshLicense: loadLicense,
    checkFeature,
    checkLimit,
    hasFeature,
    isAtLimit,
    showUpgradePrompt,
    canCreate,
  };
}

/**
 * HOC para proteger componentes que requieren un feature específico
 */
export function withFeature<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  featureName: FeatureKey,
  featureLabel?: string
) {
  return function WithFeatureComponent(props: P) {
    const { hasFeature, showUpgradePrompt, loading } = useLicense();

    if (loading) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </div>
      );
    }

    if (!hasFeature(featureName)) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center border-2 border-dashed rounded-lg">
          <span className="text-4xl mb-4">🔒</span>
          <h3 className="text-lg font-semibold mb-2">
            {featureLabel} no disponible
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Esta funcionalidad no está incluida en tu plan actual
          </p>
          <button
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium"
            onClick={() => showUpgradePrompt(featureName)}
          >
            Ver opciones de actualización
          </button>
        </div>
      );
    }

    return <WrappedComponent {...props} />;
  };
}

/**
 * Hook para verificación de límites con polling opcional
 */
export function useLicenseLimit(
  limitType: string,
  companyId?: string,
  pollInterval?: number
) {
  const [result, setResult] = useState<LimitCheckResult | null>(null);
  const [loading, setLoading] = useState(true);

  const check = useCallback(async () => {
    setLoading(true);
    try {
      const res = await checkLicenseLimit(limitType, companyId);
      setResult({
        limitType: res.limit_type,
        max: res.max,
        current: res.current,
        available: res.available,
        isAtLimit: res.is_at_limit,
        companyId: res.company_id,
        period: res.period,
      });
    } catch (error) {
      console.error('Error checking limit:', error);
    } finally {
      setLoading(false);
    }
  }, [limitType, companyId]);

  useEffect(() => {
    check();

    if (pollInterval && pollInterval > 0) {
      const interval = setInterval(check, pollInterval);
      return () => clearInterval(interval);
    }
  }, [check, pollInterval]);

  return { ...result, loading, refresh: check };
}