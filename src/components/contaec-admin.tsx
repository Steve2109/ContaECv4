'use client';

import Image from 'next/image';
import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator'
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  ArrowLeft,
  AlertTriangle,
  Clock,
  Database,
  Heart,
  Loader2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Users,
  Key,
  Activity,
  RefreshCw,
  UserCheck,
  UserX,
  XCircle,
  Server,
  DollarSign,
  Edit2,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getAdminStats,
  getAdminUsers,
  modifyUserLicense,
  toggleUserActive,
  modifyUserTrial,
  endUserTrial,
  getTrialUsers,
  getSystemHealth,
  getSecurityIssues,
  type AdminStats,
  type AdminUser,
} from '@/lib/api';

interface ContaECAdminProps {
  onBack: () => void;
}

export function ContaECAdmin({ onBack }: ContaECAdminProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [health, setHealth] = useState<{
    system: Record<string, unknown>;
    database: Record<string, unknown>;
    application: Record<string, unknown>;
    environment_toggle_available?: boolean;
  } | null>(null);
  const [securityData, setSecurityData] = useState<{
    expired_active_licenses: Array<{ user_id: string; email: string; full_name: string; license_end_date: string | null; days_expired: number | null }>;
    users_without_config: Array<{ user_id: string; email: string; full_name: string }>;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  // License modification dialog
  const [licenseDialogOpen, setLicenseDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [licenseForm, setLicenseForm] = useState({ license_type: '' });
  const [modifying, setModifying] = useState(false);

  // License prices management
  const [licensePrices, setLicensePrices] = useState([
    { type: 'Mensual', key: 'monthly', price: 15.00, months: 1, color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
    { type: 'Trimestral', key: 'quarterly', price: 40.00, months: 3, color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    { type: 'Semestral', key: 'semiannual', price: 75.00, months: 6, color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
    { type: 'Anual', key: 'annual', price: 130.00, months: 12, color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' },
  ]);
  const [editingPrices, setEditingPrices] = useState(false);
  const [savingPrices, setSavingPrices] = useState(false);

  // Trial management state
  const [trialUsers, setTrialUsers] = useState<Array<{ id: string; email: string; full_name: string; is_active: boolean; trial_start_date: string | null; trial_end_date: string | null; trial_days_remaining: number }>>([]);
  const [trialDialogOpen, setTrialDialogOpen] = useState(false);
  const [selectedTrialUser, setSelectedTrialUser] = useState<{ id: string; email: string; full_name: string } | null>(null);
  const [trialDaysForm, setTrialDaysForm] = useState(15);
  const [modifyingTrial, setModifyingTrial] = useState(false);

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        getAdminStats(),
        getAdminUsers(),
        getSystemHealth(),
        getSecurityIssues(),
      ]);

      if (results[0].status === 'fulfilled') setStats(results[0].value);
      if (results[1].status === 'fulfilled') setUsers(results[1].value);
      if (results[2].status === 'fulfilled') setHealth(results[2].value);
      if (results[3].status === 'fulfilled') setSecurityData(results[3].value);
    } catch {
      toast.error('Error al cargar datos de administracion');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadLicensePrices = useCallback(async () => {
    try {
      const token = localStorage.getItem('contaec_token');
      const res = await fetch('/api/v1/admin/license-prices', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLicensePrices((prev) =>
          prev.map((p) => ({
            ...p,
            price: data.prices[p.key]?.price ?? p.price,
          }))
        );
      }
    } catch {
      // Use defaults
    }
  }, []);

  const loadTrialUsers = useCallback(async () => {
    try {
      const data = await getTrialUsers();
      setTrialUsers(data.trial_users || []);
    } catch {
      // No trial users or error
    }
  }, []);

  const handleSavePrices = async () => {
    setSavingPrices(true);
    try {
      const token = localStorage.getItem('contaec_token');
      const body: Record<string, number> = {};
      licensePrices.forEach((p) => {
        body[p.key] = p.price;
      });
      const res = await fetch('/api/v1/admin/license-prices', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Error al guardar precios');
      toast.success('Precios actualizados correctamente');
      setEditingPrices(false);
    } catch {
      toast.error('Error al guardar precios');
    } finally {
      setSavingPrices(false);
    }
  };

  const handlePriceChange = (key: string, value: string) => {
    const num = parseFloat(value);
    if (!isNaN(num) && num >= 0) {
      setLicensePrices((prev) =>
        prev.map((p) => (p.key === key ? { ...p, price: num } : p))
      );
    }
  };

  useEffect(() => {
    loadAdminData();
    loadLicensePrices();
    loadTrialUsers();
  }, [loadAdminData, loadLicensePrices, loadTrialUsers]);

  async function handleModifyLicense() {
    if (!selectedUser) return;
    setModifying(true);
    try {
      await modifyUserLicense(selectedUser.id, { license_type: licenseForm.license_type });
      const updatedUsers = await getAdminUsers();
      setUsers(updatedUsers);
      setLicenseDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al modificar licencia');
    } finally {
      setModifying(false);
    }
  }

  async function handleToggleUserActive(user: AdminUser) {
    try {
      await toggleUserActive(user.id, !user.is_active);
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: !u.is_active } : u))
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al cambiar estado del usuario');
    }
  }

  function openLicenseDialog(user: AdminUser) {
    setSelectedUser(user);
    setLicenseForm({
      license_type: user.license_type || '',
    });
    setLicenseDialogOpen(true);
  }

  function openTrialDialog(user: { id: string; email: string; full_name: string }) {
    setSelectedTrialUser(user);
    setTrialDaysForm(15);
    setTrialDialogOpen(true);
  }

  async function handleModifyTrial() {
    if (!selectedTrialUser) return;
    setModifyingTrial(true);
    try {
      await modifyUserTrial(selectedTrialUser.id, trialDaysForm);
      await loadTrialUsers();
      setTrialDialogOpen(false);
      toast.success(`Período de prueba actualizado a ${trialDaysForm} días`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al modificar período de prueba');
    } finally {
      setModifyingTrial(false);
    }
  }

  async function handleEndTrial(userId: string) {
    try {
      await endUserTrial(userId);
      await loadTrialUsers();
      toast.success('Período de prueba finalizado');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al finalizar período de prueba');
    }
  }

  const securityIssuesCount =
    (securityData?.expired_active_licenses?.length ?? 0) +
    (securityData?.users_without_config?.length ?? 0);

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
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-3">
          <Image
            src="/logo.svg"
            alt="ContaEC"
            width={36}
            height={36}
            className="h-9 w-9"
            priority
          />
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              Panel de Administracion
            </h2>
            <p className="text-muted-foreground">
              Gestion del sistema ContaEC
            </p>
          </div>
        </div>
      </div>

      {/* Admin Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview" className="gap-2">
            <Activity className="h-4 w-4" />
            Resumen
          </TabsTrigger>
          <TabsTrigger value="users" className="gap-2">
            <Users className="h-4 w-4" />
            Usuarios
          </TabsTrigger>
          <TabsTrigger value="health" className="gap-2">
            <Server className="h-4 w-4" />
            Sistema
          </TabsTrigger>
          <TabsTrigger value="licenses" className="gap-2">
            <Key className="h-4 w-4" />
            Licencias
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2">
            <Shield className="h-4 w-4" />
            Seguridad
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {stats && (
              <>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">Total Usuarios</span>
                      <Users className="h-4 w-4 text-primary" />
                    </div>
                    <div className="text-2xl font-bold">{stats.total_users}</div>
                    <p className="text-xs text-muted-foreground">
                      {stats.active_users} activos
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">Empresas</span>
                      <Database className="h-4 w-4 text-primary" />
                    </div>
                    <div className="text-2xl font-bold">{stats.total_companies}</div>
                    <p className="text-xs text-muted-foreground">registradas</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">Clientes</span>
                      <Activity className="h-4 w-4 text-primary" />
                    </div>
                    <div className="text-2xl font-bold">{stats.total_clients ?? 0}</div>
                    <p className="text-xs text-muted-foreground">registrados</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">Licencias Expiradas</span>
                      <Key className="h-4 w-4 text-destructive" />
                    </div>
                    <div className="text-2xl font-bold">{stats.expired_licenses ?? 0}</div>
                    <p className="text-xs text-muted-foreground">de {stats.total_users} usuarios</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">Por Expirar</span>
                      <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    </div>
                    <div className="text-2xl font-bold">{stats.expiring_licenses}</div>
                    <p className="text-xs text-muted-foreground">en los proximos 30 dias</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground">Problemas Seguridad</span>
                      <ShieldAlert className="h-4 w-4 text-destructive" />
                    </div>
                    <div className="text-2xl font-bold">
                      {securityIssuesCount}
                    </div>
                    <p className="text-xs text-muted-foreground">sin resolver</p>
                  </CardContent>
                </Card>
              </>
            )}
            {!stats && (
              <div className="col-span-full text-center py-8">
                <p className="text-muted-foreground">No se pudieron cargar las estadisticas</p>
                <Button variant="outline" className="mt-2" onClick={loadAdminData}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Reintentar
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Users className="h-4 w-4 text-primary" />
                Gestion de Usuarios
              </CardTitle>
              <CardDescription>
                Administre usuarios y sus licencias
              </CardDescription>
            </CardHeader>
            <CardContent>
              {users.length > 0 ? (
                <ScrollArea className="max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nombre</TableHead>
                        <TableHead>Correo</TableHead>
                        <TableHead>Licencia</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Expira</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {users.map((u) => {
                        // Calcular estado de trial
                        const now = new Date();
                        const trialEnd = u.trial_end_date ? new Date(u.trial_end_date) : null;
                        const licenseEnd = u.license_end_date ? new Date(u.license_end_date) : null;
                        const isTrialActive = u.is_trial && trialEnd && trialEnd > now;
                        const isLicenseActive = licenseEnd && licenseEnd > now;
                        const expiryDate = isTrialActive ? trialEnd : licenseEnd;
                        const expiryLabel = isTrialActive ? 'Trial' : 'Licencia';

                        return (
                        <TableRow key={u.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {u.is_admin && (
                                <Shield className="h-3.5 w-3.5 text-primary" />
                              )}
                              <span className="font-medium">{u.full_name}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-xs">
                            {u.email}
                          </TableCell>
                          <TableCell className="text-xs">
                            <div className="flex flex-col gap-1">
                              <Badge variant="outline" className="text-xs w-fit">{u.license_type || '-'}</Badge>
                              {u.is_trial && (
                                <Badge variant={isTrialActive ? 'default' : 'secondary'} className={`text-xs w-fit ${isTrialActive ? 'bg-amber-500' : ''}`}>
                                  {isTrialActive ? 'Trial Activo' : 'Trial Exp.'}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-col gap-1">
                              <Badge
                                variant={u.is_active ? 'default' : 'secondary'}
                                className={u.is_active ? 'bg-primary' : ''}
                              >
                                {u.is_active ? 'Activo' : 'Inactivo'}
                              </Badge>
                              {expiryDate && (
                                <span className={`text-xs ${isTrialActive || isLicenseActive ? 'text-emerald-600' : 'text-destructive'}`}>
                                  {isTrialActive || isLicenseActive ? 'Vigente' : 'Exp.'}
                                </span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-xs">
                            {expiryDate ? (
                              <div className="flex flex-col">
                                <span>{expiryDate.toLocaleDateString('es-EC')}</span>
                                <span className="text-muted-foreground text-[10px]">{expiryLabel}</span>
                              </div>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-7 text-xs"
                                onClick={() => openLicenseDialog(u)}
                              >
                                <Key className="mr-1 h-3 w-3" />
                                Licencia
                              </Button>
                              <Button
                                variant={u.is_active ? 'destructive' : 'default'}
                                size="sm"
                                className="h-7 text-xs"
                                onClick={() => handleToggleUserActive(u)}
                              >
                                {u.is_active ? (
                                  <>
                                    <UserX className="mr-1 h-3 w-3" />
                                    Desactivar
                                  </>
                                ) : (
                                  <>
                                    <UserCheck className="mr-1 h-3 w-3" />
                                    Activar
                                  </>
                                )}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : (
                <div className="text-center py-8">
                  <Users className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    No se pudieron cargar los usuarios
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Health Tab */}
        <TabsContent value="health">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Application Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Server className="h-4 w-4 text-primary" />
                  Aplicación
                </CardTitle>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Versión</span>
                      <Badge variant="outline" className="font-mono">{(health.application as Record<string, string>)?.version ?? 'N/A'}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Ambiente</span>
                      <Badge variant={(health.application as Record<string, string>)?.environment === 'production' ? 'destructive' : 'default'}>
                        {(health.application as Record<string, string>)?.environment ?? 'N/A'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Uptime</span>
                      <span className="text-sm font-medium">{(health.application as Record<string, string>)?.uptime ?? 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Python</span>
                      <span className="text-sm font-mono">{(health.application as Record<string, string>)?.python_version ?? ''}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">SO</span>
                      <span className="text-sm font-medium">{(health.application as Record<string, string>)?.system ?? ''}</span>
                    </div>
                    <Separator className="my-2" />
                    <p className="text-xs text-muted-foreground">
                      Para cambiar ambiente, edite <code className="bg-muted px-1">APP_ENV</code> en <code className="bg-muted px-1">.env</code> y reinicie el servidor.
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">Cargando...</p>
                )}
              </CardContent>
            </Card>

            {/* System Resources */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Heart className="h-4 w-4 text-primary" />
                  Recursos del Sistema
                </CardTitle>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-4">
                    {/* CPU */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">CPU</span>
                        <span className="text-sm font-medium">
                          {typeof (health.system as Record<string, unknown>)?.cpu_percent === 'number'
                            ? `${(health.system as Record<string, number>)?.cpu_percent}%`
                            : String((health.system as Record<string, unknown>)?.cpu_percent ?? 'N/A')}
                        </span>
                      </div>
                      {typeof (health.system as Record<string, unknown>)?.cpu_percent === 'number' && (
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${(health.system as Record<string, number>)?.cpu_percent}%` }}
                          />
                        </div>
                      )}
                    </div>

                    {/* Memory */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Memoria</span>
                        <span className="text-sm font-medium">
                          {typeof (health.system as Record<string, unknown>)?.memory_percent === 'number'
                            ? `${(health.system as Record<string, number>)?.memory_percent}%`
                            : String((health.system as Record<string, unknown>)?.memory_percent ?? 'N/A')}
                        </span>
                      </div>
                      {typeof (health.system as Record<string, unknown>)?.memory_percent === 'number' && (
                        <>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${(health.system as Record<string, number>)?.memory_percent}%` }}
                            />
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {((health.system as Record<string, number>)?.memory_used_mb ?? 0).toFixed(0)} MB / {((health.system as Record<string, number>)?.memory_total_mb ?? 0).toFixed(0)} MB
                          </p>
                        </>
                      )}
                    </div>

                    {/* Disk */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Disco</span>
                        <span className="text-sm font-medium">
                          {typeof (health.system as Record<string, unknown>)?.disk_percent === 'number'
                            ? `${(health.system as Record<string, number>)?.disk_percent}%`
                            : String((health.system as Record<string, unknown>)?.disk_percent ?? 'N/A')}
                        </span>
                      </div>
                      {typeof (health.system as Record<string, unknown>)?.disk_percent === 'number' && (
                        <>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className={`h-full transition-all ${(health.system as Record<string, number>)?.disk_percent > 90 ? 'bg-destructive' : 'bg-primary'}`}
                              style={{ width: `${(health.system as Record<string, number>)?.disk_percent}%` }}
                            />
                          </div>
                          <p className="text-xs text-muted-foreground">
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

            {/* Database Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Database className="h-4 w-4 text-primary" />
                  Base de Datos
                </CardTitle>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">Total Usuarios</span>
                      </div>
                      <span className="text-sm font-medium">
                        {(health.database as Record<string, number>)?.total_users ?? 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-2">
                        <Database className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">Total Empresas</span>
                      </div>
                      <span className="text-sm font-medium">
                        {(health.database as Record<string, number>)?.total_companies ?? 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-2">
                        <Activity className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">Total Clientes</span>
                      </div>
                      <span className="text-sm font-medium">
                        {(health.database as Record<string, number>)?.total_clients ?? 'N/A'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">Cargando...</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Licenses Tab */}
        <TabsContent value="licenses">
          <div className="space-y-6">
            {/* Price editing controls */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-primary" />
                      Precios de Licencias
                    </CardTitle>
                    <CardDescription>
                      {editingPrices
                        ? 'Edite los precios y haga clic en Guardar'
                        : 'Precios actuales del sistema. Haga clic en Editar para cambiar.'}
                    </CardDescription>
                  </div>
                  {!editingPrices ? (
                    <Button size="sm" onClick={() => setEditingPrices(true)}>
                      <Edit2 className="h-4 w-4 mr-1" />
                      Editar Precios
                    </Button>
                  ) : (
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => { setEditingPrices(false); loadLicensePrices(); }}>
                        Cancelar
                      </Button>
                      <Button size="sm" onClick={handleSavePrices} disabled={savingPrices}>
                        {savingPrices ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                        Guardar
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {licensePrices.map((plan) => (
                    <div key={plan.key} className="space-y-3 p-4 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{plan.type}</span>
                        <Badge className={plan.color}>{plan.type}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{plan.months} {plan.months === 1 ? 'mes' : 'meses'}</p>
                      {editingPrices ? (
                        <div className="space-y-1">
                          <Label htmlFor={`price-${plan.key}`}>Precio (USD)</Label>
                          <Input
                            id={`price-${plan.key}`}
                            type="number"
                            min="0"
                            step="0.01"
                            value={plan.price}
                            onChange={(e) => handlePriceChange(plan.key, e.target.value)}
                            className="text-lg font-bold"
                          />
                        </div>
                      ) : (
                        <div className="text-center py-2">
                          <div className="text-3xl font-bold">${plan.price.toFixed(2)}</div>
                          <p className="text-xs text-muted-foreground mt-1">
                            ${(plan.price / plan.months).toFixed(2)}/mes
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* License tiers info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-primary" />
                  Limites por Plan
                </CardTitle>
                <CardDescription>
                  Caracteristicas y limites de cada tipo de licencia
                </CardDescription>
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
                      <TableRow>
                        <TableCell className="font-medium">Empresas max.</TableCell>
                        <TableCell>1</TableCell>
                        <TableCell>2</TableCell>
                        <TableCell>5</TableCell>
                        <TableCell>Ilimitado</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Usuarios/empresa</TableCell>
                        <TableCell>2</TableCell>
                        <TableCell>5</TableCell>
                        <TableCell>10</TableCell>
                        <TableCell>Ilimitado</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Comprobantes/mes</TableCell>
                        <TableCell>50</TableCell>
                        <TableCell>200</TableCell>
                        <TableCell>500</TableCell>
                        <TableCell>Ilimitado</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Empleados</TableCell>
                        <TableCell>5</TableCell>
                        <TableCell>15</TableCell>
                        <TableCell>50</TableCell>
                        <TableCell>Ilimitado</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Productos</TableCell>
                        <TableCell>100</TableCell>
                        <TableCell>500</TableCell>
                        <TableCell>2,000</TableCell>
                        <TableCell>Ilimitado</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Trial Management Section */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-500" />
                  Usuarios en Período de Prueba
                </CardTitle>
                <CardDescription>
                  Usuarios con trial activo y gestión de duración
                </CardDescription>
              </CardHeader>
              <CardContent>
                {trialUsers.length > 0 ? (
                  <ScrollArea className="max-h-80">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Nombre</TableHead>
                          <TableHead>Correo</TableHead>
                          <TableHead>Inicio Trial</TableHead>
                          <TableHead>Fin Trial</TableHead>
                          <TableHead>Días Rest.</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {trialUsers.map((tu) => (
                          <TableRow key={tu.id}>
                            <TableCell className="font-medium">{tu.full_name}</TableCell>
                            <TableCell className="text-muted-foreground text-xs">{tu.email}</TableCell>
                            <TableCell className="text-xs">
                              {tu.trial_start_date ? new Date(tu.trial_start_date).toLocaleDateString('es-EC') : '-'}
                            </TableCell>
                            <TableCell className="text-xs">
                              {tu.trial_end_date ? new Date(tu.trial_end_date).toLocaleDateString('es-EC') : '-'}
                            </TableCell>
                            <TableCell>
                              <Badge variant={tu.trial_days_remaining > 0 ? 'default' : 'destructive'} className="text-xs">
                                {tu.trial_days_remaining > 0 ? `${tu.trial_days_remaining}` : 'Expirado'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-7 text-xs"
                                  onClick={() => openTrialDialog({ id: tu.id, email: tu.email, full_name: tu.full_name })}
                                >
                                  <Edit2 className="mr-1 h-3 w-3" />
                                  Modificar
                                </Button>
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  className="h-7 text-xs"
                                  onClick={() => handleEndTrial(tu.id)}
                                >
                                  <XCircle className="mr-1 h-3 w-3" />
                                  Finalizar
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                ) : (
                  <div className="text-center py-6">
                    <Clock className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground">No hay usuarios en período de prueba</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                Problemas de Seguridad
              </CardTitle>
              <CardDescription>
                Alertas y problemas de seguridad detectados
              </CardDescription>
            </CardHeader>
            <CardContent>
              {securityData && securityIssuesCount > 0 ? (
                <ScrollArea className="max-h-96">
                  <div className="space-y-3">
                    {securityData.expired_active_licenses.map((item) => (
                      <div key={item.user_id} className="rounded-lg border p-4 border-destructive/30">
                        <div className="flex items-start gap-3">
                          <ShieldAlert className="h-5 w-5 text-destructive mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-medium">Licencia expirada - {item.full_name}</h4>
                            <p className="text-xs text-muted-foreground">
                              {item.email} - Expirada hace {item.days_expired} dias
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                    {securityData.users_without_config.map((item) => (
                      <div key={item.user_id} className="rounded-lg border p-4 border-yellow-500/30">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-medium">Sin configuracion - {item.full_name}</h4>
                            <p className="text-xs text-muted-foreground">
                              {item.email} - No tiene configuracion de usuario
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <div className="text-center py-8">
                  <ShieldCheck className="h-12 w-12 mx-auto text-green-600 mb-3" />
                  <h3 className="text-lg font-medium">Todo en orden</h3>
                  <p className="text-muted-foreground text-sm mt-1">
                    No se detectaron problemas de seguridad
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* License Modification Dialog */}
      <Dialog open={licenseDialogOpen} onOpenChange={setLicenseDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Modificar Licencia</DialogTitle>
            <DialogDescription>
              Modificar la licencia del usuario {selectedUser?.full_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="mod-license-type">Tipo de Licencia</Label>
              <select
                id="mod-license-type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={licenseForm.license_type}
                onChange={(e) => setLicenseForm({ ...licenseForm, license_type: e.target.value })}
              >
                <option value="">Seleccionar...</option>
                <option value="monthly">Mensual - $15.00</option>
                <option value="quarterly">Trimestral - $40.00</option>
                <option value="semiannual">Semestral - $75.00</option>
                <option value="annual">Anual - $130.00</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setLicenseDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleModifyLicense} disabled={modifying || !licenseForm.license_type}>
                {modifying ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  'Guardar Cambios'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Trial Modification Dialog */}
      <Dialog open={trialDialogOpen} onOpenChange={setTrialDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Modificar Período de Prueba</DialogTitle>
            <DialogDescription>
              Modificar el período de prueba de {selectedTrialUser?.full_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="mod-trial-days">Días de prueba (1-90)</Label>
              <Input
                id="mod-trial-days"
                type="number"
                min={1}
                max={90}
                value={trialDaysForm}
                onChange={(e) => setTrialDaysForm(parseInt(e.target.value) || 15)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setTrialDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleModifyTrial} disabled={modifyingTrial || trialDaysForm < 1 || trialDaysForm > 90}>
                {modifyingTrial ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  'Guardar Cambios'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
