'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
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
import {
  ScrollText,
  Loader2,
  RefreshCw,
  Users,
  Activity,
  Shield,
  Clock,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getAuditLogs,
  getAuditStats,
  type AuditLogEntry,
} from '@/lib/api';

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('es-EC', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

export function ContaECAudit() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState<string>('all');
  const [filterEntityType, setFilterEntityType] = useState<string>('all');
  const [filterFechaDesde, setFilterFechaDesde] = useState('');
  const [filterFechaHasta, setFilterFechaHasta] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [logsData, statsData] = await Promise.all([
        getAuditLogs({
          action: filterAction !== 'all' ? filterAction : undefined,
          entity_type: filterEntityType !== 'all' ? filterEntityType : undefined,
          fecha_desde: filterFechaDesde || undefined,
          fecha_hasta: filterFechaHasta || undefined,
          limit: 100,
        }),
        getAuditStats(),
      ]);
      setLogs(logsData);
      setStats(statsData as Record<string, unknown>);
    } catch {
      toast.error('Error al cargar registro de auditoria');
    } finally {
      setLoading(false);
    }
  }, [filterAction, filterEntityType, filterFechaDesde, filterFechaHasta]);

  useEffect(() => { loadData(); }, [loadData]);

  const actionTypes = ['create', 'update', 'delete', 'login', 'logout', 'firmar', 'enviar', 'consultar', 'procesar'];
  const entityTypes = ['company', 'employee', 'supplier', 'comprobante', 'payroll', 'user', 'purchase_order', 'cuenta_por_pagar', 'retencion_compra'];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Auditoría</h2>
        <p className="text-muted-foreground">Registro de acciones y actividades del sistema</p>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-primary/10 p-2"><Activity className="h-4 w-4 text-primary" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Total Acciones</p>
                <div className="text-xl font-bold">{String(stats.total_actions ?? 0)}</div>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-emerald-600/10 p-2"><Users className="h-4 w-4 text-emerald-600" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Logins Recientes (24h)</p>
                <div className="text-xl font-bold">{String(stats.recent_logins ?? 0)}</div>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-amber-500/10 p-2"><Shield className="h-4 w-4 text-amber-500" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Tipos de Accion</p>
                <div className="text-xl font-bold">{Object.keys(stats.actions_by_type as Record<string, number> || {}).length}</div>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-sky-600/10 p-2"><ScrollText className="h-4 w-4 text-sky-600" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Entidades Afectadas</p>
                <div className="text-xl font-bold">{Object.keys(stats.actions_by_entity as Record<string, number> || {}).length}</div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filterAction} onValueChange={setFilterAction}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="Accion" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las acciones</SelectItem>
            {actionTypes.map((a) => (<SelectItem key={a} value={a}>{a}</SelectItem>))}
          </SelectContent>
        </Select>
        <Select value={filterEntityType} onValueChange={setFilterEntityType}>
          <SelectTrigger className="w-[180px]"><SelectValue placeholder="Tipo Entidad" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las entidades</SelectItem>
            {entityTypes.map((e) => (<SelectItem key={e} value={e}>{e}</SelectItem>))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <Label className="text-xs whitespace-nowrap">Desde:</Label>
          <Input type="date" value={filterFechaDesde} onChange={(e) => setFilterFechaDesde(e.target.value)} className="w-36" />
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs whitespace-nowrap">Hasta:</Label>
          <Input type="date" value={filterFechaHasta} onChange={(e) => setFilterFechaHasta(e.target.value)} className="w-36" />
        </div>
        <Button variant="outline" size="icon" onClick={loadData}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* Audit Log Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
      ) : logs.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="max-h-96">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha/Hora</TableHead>
                    <TableHead>Usuario</TableHead>
                    <TableHead>Accion</TableHead>
                    <TableHead>Entidad</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead>IP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="text-xs whitespace-nowrap">
                        <div className="flex items-center gap-1"><Clock className="h-3 w-3 text-muted-foreground" />{formatDate(log.created_at)}</div>
                      </TableCell>
                      <TableCell className="text-xs">{log.user_email || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={log.action === 'delete' ? 'destructive' : log.action === 'create' ? 'default' : 'secondary'}
                          className={log.action === 'create' ? 'bg-emerald-600' : ''}>
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell><Badge variant="outline" className="text-xs">{log.entity_type}</Badge></TableCell>
                      <TableCell className="max-w-[250px] truncate text-xs">{log.description}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{log.ip_address || '-'}</TableCell>
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
            <ScrollText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-medium">Sin registros de auditoria</h3>
            <p className="text-muted-foreground text-sm mt-1">No se encontraron registros con los filtros seleccionados</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
