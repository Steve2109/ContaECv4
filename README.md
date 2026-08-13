# ContaEC - Sistema Contable y Facturación Electrónica del Ecuador

**Versión:** 4.0.0  
**Desarrollado por:** T&M Technology Ec  
**Teléfono:** 0960068866  
**Soporte:** info@tymtechnology.shop  
**DNS:** conta.tymtechnology.shop  

---

## Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Requisitos del Servidor](#requisitos-del-servidor)
4. [Instalación Paso a Paso](#instalación-paso-a-paso)
   - [4.1 Preparación del Servidor](#41-preparación-del-servidor)
   - [4.2 Instalación de PostgreSQL](#42-instalación-de-postgresql)
   - [4.3 Configuración de la Base de Datos](#43-configuración-de-la-base-de-datos)
   - [4.4 Instalación de Python y Dependencias](#44-instalación-de-python-y-dependencias)
   - [4.5 Instalación de Node.js y Bun](#45-instalación-de-nodejs-y-bun)
   - [4.6 Despliegue del Backend (FastAPI)](#46-despliegue-del-backend-fastapi)
   - [4.7 Despliegue del Frontend (Next.js)](#47-despliegue-del-frontend-nextjs)
   - [4.8 Configuración del Archivo .env](#48-configuración-del-archivo-env)
   - [4.9 Configuración de Caddy (Proxy Reverso)](#49-configuración-de-caddy-proxy-reverso)
   - [4.10 Instalación de ClamAV](#410-instalación-de-clamav)
   - [4.11 Integración de Email Templates en Frontend](#411-integración-de-email-templates-en-frontend)
   - [4.12 Creacion de symlink](#412-creacion-de-symlink)
5. [Estructura del Proyecto](#estructura-del-proyecto)
6. [Módulos y Funcionalidades](#módulos-y-funcionalidades)
7. [Variables de Entorno (.env)](#variables-de-entorno-env)
8. [Administración](#administración)
9. [Respaldo y Restauración](#respaldo-y-restauración)
10. [Seguridad](#seguridad)
11. [Solución de Problemas](#solución-de-problemas)

---

## Descripción General

ContaEC es un sistema contable integral con facturación electrónica para el Ecuador, cumpliendo con las normativas del SRI (Servicio de Rentas Internas). Incluye:

- **Facturación Electrónica SRI** (XML, XAdES-BES, SOAP, RIDE)
- **Contabilidad de doble partida** (Plan de Cuentas, Asientos, Balance)
- **Nómina RRHH** (IESS, Décimos, Vacaciones, Fondo de Reserva, Liquidaciones)
- **Inventario y Kardex** (FIFO/LIFO/PP, códigos de barras)
- **Multi-empresa** con roles por empresa
- **Licenciamiento** (mensual, trimestral, semestral, anual)
- **CRM, POS, BI, Presupuestos, Proyectos, Integraciones bancarias, ML/IA**
- **Seguridad** (ClamAV, VirusTotal, JWT con revocación, rate limiting, sanitización)

---

## Arquitectura del Sistema

```
Internet (DNS: conta.tymtechnology.shop)
    │
    ▼
┌─────────────────────────────────┐
│   Caddy (Proxy Reverso :80)     │
│   Certificado Let's Encrypt     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Next.js 16 (React 19) :3000   │
│   - Interfaz de usuario         │
│   - API Proxy → FastAPI :8000   │
│   - SSR/SSG + Client Components │
└────────────┬────────────────────┘
             │ /api/*
             ▼
┌─────────────────────────────────┐
│   FastAPI (Python 3.12) :8000   │
│   - REST API (~331 endpoints)   │
│   - SRI SOAP (zeep)             │
│   - XML/XAdES-BES (signxml)     │
│   - RIDE PDF (reportlab)        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   PostgreSQL :5432              │
│   - 73+ modelos SQLAlchemy      │
│   - UUID primary keys           │
│   - Full-text search            │
└─────────────────────────────────┘
```

---

## Requisitos del Servidor

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| CPU | 2 núcleos | 3+ núcleos |
| RAM | 4 GB | 8 GB |
| Almacenamiento | 50 GB | 200 GB |
| SO | Debian 12/Ubuntu 22.04+ | Debian 12 |
| Python | 3.11+ | 3.12 |
| Node.js | 20+ | 22+ |
| PostgreSQL | 15+ | 16+ |

**Servidor actual (LXC Proxmox):**
- IP: 10.0.1.20:80
- CPU: 8 x Intel Xeon E5-1620 v2 (3 núcleos usados)
- RAM: 10 GB (6 GB libres)
- Disco: 205 GB HDD
- Red: vmbr0 (internet) + vmbr1 (10.0.1.20/24)

---
## Si se desea hacer cambio de ambiente general de producción a desarrollo hacer lo siguiente:
How to change environment
Edit /opt/contaec/backend/.env on the server:
# Switch to production:
sed -i 's/APP_ENV=.*/APP_ENV=production/' /opt/contaec/backend/.env
# Switch to development:
sed -i 's/APP_ENV=.*/APP_ENV=development/' /opt/contaec/backend/.env
# Then restart:
systemctl restart contaec-backend
# Then wait:
sleep 15

## Instalación Paso a Paso

### 4.1 Preparación del Servidor

```bash
# Actualizar y Crear Locale

## 1. Verificar locales existentes
locale -a | grep -iE 'es_EC|C\.utf'
## 2. Configurar español de Ecuador inicialmente
update-locale LANG=es_EC.UTF-8
## 3. Verificar la configuración actual
nano -l /etc/default/locale
## 4. Vlidar y agregar la configuración actual
LANG=es_EC.UTF-8
LANG=en_US.UTF-8
## 5. Revisar si en_US.UTF-8 estaba habilitada
grep -nE '^[# ]*en_US\.UTF-8' /etc/locale.gen
## 6. Habilitar en_US.UTF-8
sed -i 's/^# *en_US\.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
## 7. Habilitar ingles y español
nano -l /etc/locale.gen
> Descomentar linea 165 y 186
## 8. Generar las locales
locale-gen
## 9. Establecer en_US.UTF-8 como locale predeterminada
update-locale LANG=es_EC.UTF-8
## 10. Verificar la configuración persistente
cat /etc/default/locale
## 11. Confirmar todas las locales instaladas
locale -a
## 12. Confirmar que Perl ya no muestra advertencias
perl -we 'use locale; print "Locale correcta\n"'

# Actualizar el sistema
apt update && apt upgrade -y
# Instalar herramientas esenciales
apt install -y curl wget git unzip htop nano sudo gnupg2 lsb-release net-tools
# Instalar certificados CA
apt install -y ca-certificates
```

### 4.2 Instalación de PostgreSQL

```bash
# Create Key Directory
sudo install -d /usr/share/postgresql-common/pgdg
# Agregar repositorio oficial de PostgreSQL
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc

# Update the Repository List with the Key Path
# Overwrite your existing list file to include the signed-by directive:
sudo sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Instalar PostgreSQL 17
apt update
apt install -y postgresql-17 postgresql-contrib-17
# Crear el cluster
sudo pg_createcluster 17 main
# Habilitar y arrancar el servicio
sudo systemctl enable postgresql@17-main
sudo systemctl start postgresql@17-main
# Verifica que arrancó
sudo systemctl status postgresql@17-main
sudo ss -tlnp | grep 5432
pg_isready -h localhost -p 5432
```
### Locale del sistema (o configuración de locales)
# # 1. Instalar el paquete locales
# sudo apt-get install locales
# # 2. Generar el locale es_EC.UTF-8
# sudo locale-gen es_EC.UTF-8
# # 3. Reconfigurar locales
# sudo dpkg-reconfigure locales
# # 4. Selecciona es_EC.UTF-8 como default
# sudo locale-gen es_EC.UTF-8
# # 5. Verificar que se instaló
# locale -a | grep es_EC
# # 6. Verificar el locale disponible
# locale -a | grep UTF-8
# # 7. Configurar permanentemente
# sudo sed -i 's/^# *es_EC.UTF-8 UTF-8/es_EC.UTF-8 UTF-8/' /etc/locale.gen
# sudo locale-gen
# # 8. Validación de la configuración
# nl /etc/default/locale
# locale -a | grep es_EC
# # 9. Reinicia el shell o ejecuta:
# bash
# # 10. Luego verifica:
# locale
# # 11. Verifica que ya no aparezca el error
# perl -v

---

### 4.3 Configuración de la Base de Datos

```bash
# Cambiar al usuario postgres y ejecutar SQL
sudo -u postgres psql << 'EOF'
CREATE USER contaec_user WITH PASSWORD 'EvJcqP2z4zoryZ5';
CREATE DATABASE contaec_db OWNER contaec_user;
GRANT ALL PRIVILEGES ON DATABASE contaec_db TO contaec_user;
\c contaec_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
EOF
```

**Configuración de PostgreSQL** (`nano -l /etc/postgresql/17/main/postgresql.conf`):

```ini
# Memoria (ajustar según RAM disponible, 6GB libres → asignar ~2GB)
shared_buffers = 512MB
effective_cache_size = 1536MB
work_mem = 16MB
maintenance_work_mem = 128MB

# Conexiones
listen_addresses = 'localhost'
max_connections = 100
superuser_reserved_connections = 3

# WAL
wal_buffers = 16MB
min_wal_size = 80MB
max_wal_size = 1GB
checkpoint_completion_target = 0.9

# Logging
log_min_duration_statement = 500
log_checkpoints = on
log_connections = on
log_disconnections = on

# Locale
lc_messages = 'es_EC.UTF-8'
lc_monetary = 'es_EC.UTF-8'
lc_numeric = 'es_EC.UTF-8'
lc_time = 'es_EC.UTF-8'
```

**Configuración de acceso** (`nano -l /etc/postgresql/17/main/pg_hba.conf`):

```sh
# Añadir línea para el usuario de la app (colocar antes de las configuraciones del sistema)
local   contaec_db      contaec_user                            md5
host    contaec_db      contaec_user    127.0.0.1/32            md5
host    contaec_db      contaec_user    ::1/128                 md5

# Database administrative login by Unix domain socket
```

```bash
# Reiniciar PostgreSQL para aplicar cambios
sudo systemctl restart postgresql@17-main

# Verifica que reinició correctamente
sudo systemctl status postgresql@17-main
pg_isready -h localhost -p 5432

# Verificar conexión
psql -U contaec_user -d contaec_db -h localhost -c "SELECT version();"
# Test adicional por IP explícita
psql -U contaec_user -d contaec_db -h 127.0.0.1 -c "SELECT version();"
# Verificar extensión UUID
psql -U contaec_user -d contaec_db -c "\dx"
```

### 4.4 Instalación de Python y Dependencias

```bash
# Instalar Python 3 y herramientas de compilación
sudo apt install -y python3 python3-venv python3-dev python3-pip build-essential libpq-dev
# Crear entorno virtual
cd /opt && mkdir -p contaec && cd contaec

# Clonar el repositorio (o copiar archivos del proyecto)
git clone https://github.com/Steve2109/ContaECv4.git
# O copiar vía scp/rsync
# Para mover el repositorio clonado al directorio padre
sudo mv /opt/contaec/ContaECv4/* /opt/contaec/
sudo mv /opt/contaec/ContaECv4/.* /opt/contaec/ 2>/dev/null && sudo rmdir /opt/contaec/ContaECv4

# Crear y activar entorno virtual
python3 -m venv /opt/contaec/.venv
source /opt/contaec/.venv/bin/activate

# Instalar dependencias del backend
cd /opt/contaec/backend
pip install -r requirements.txt
deactivate
```

### 4.5 Instalación de Node.js y Bun

```bash
# Instalar Node.js 22
cd ..
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

# Instalar Bun (runtime alternativo, más rápido)
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# Verificar instalaciones
# v22.x
node --version
# 1.x
bun --version
```

### 4.6 Despliegue del Backend (FastAPI)

```bash
# Crear directorios necesarios
mkdir -p /opt/contaec/backend/backups /opt/contaec/backend/uploads /opt/contaec/backend/temp /opt/contaec/backend/signatures
chmod 777 /opt/contaec/backend/backups /opt/contaec/backend/uploads /opt/contaec/backend/temp /opt/contaec/backend/signatures

# Configurar el archivo .env
cp /opt/contaec/.env.example /opt/contaec/backend/.env
nano -l /opt/contaec/backend/.env

# Crear servicio systemd para el backend
cat > /etc/systemd/system/contaec-backend.service << 'EOF'
[Unit]
Description=ContaEC FastAPI Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/contaec/backend
ExecStart=/opt/contaec/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment=APP_ENV=production

[Install]
WantedBy=multi-user.target
EOF

# Habilitar y arrancar el backend
systemctl daemon-reload
systemctl enable contaec-backend
systemctl start contaec-backend
systemctl status contaec-backend

# Verificar que el backend responde
sleep 10
curl http://localhost:8000/api/health
```

### 4.7 Despliegue del Frontend (Next.js)

```bash
cd /opt/contaec

# Instalar dependencias del frontend
bun install
bun add socket.io-client
bun add socket.io
bun install @eslint/eslintrc

# Construir el frontend para producción
bun run build

# Crear servicio systemd para el frontend
cat > /etc/systemd/system/contaec-frontend.service << 'EOF'
[Unit]
Description=ContaEC Next.js Frontend
After=network.target contaec-backend.service
Requires=contaec-backend.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/contaec
ExecStart=/root/.bun/bin/bun .next/standalone/server.js
Restart=always
RestartSec=5
Environment=PORT=3000
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

# Habilitar y arrancar el frontend
systemctl daemon-reload
systemctl enable contaec-frontend
systemctl start contaec-frontend
systemctl status contaec-frontend

# Ver logs del frontend
sudo journalctl -u contaec-frontend -n 100 --no-pager | tail -50
# Ver estado
sudo systemctl status contaec-frontend

# Verificar que el frontend responde
sleep 10
curl http://localhost:3000
```

### 4.8 Configuración del Archivo .env

```sh
# --- Servicios Web del SRI ---
# (Las URLs ya están configuradas por defecto en config.py)
# SRI_WS_RECEPCION_PRUEBAS=https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
# SRI_WS_AUTORIZACION_PRUEBAS=https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl
# SRI_WS_RECEPCION_PRODUCCION=https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
# SRI_WS_AUTORIZACION_PRODUCCION=https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl
```

# ```bash
# # Ejecutar estas líneas y copiar los resultados al .env
# source /opt/contaec/.venv/bin/activate
# # SECRET_KEY
# python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
# # ENCRYPTION_KEY
# python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(64))"
# # JWT_SECRET_KEY
# python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
# # BACKUP_ENCRYPTION_KEY (Fernet)
# python3 -c "from cryptography.fernet import Fernet; print('BACKUP_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
# ```
# 
# ```bash
# # Reiniciar el servicio para que cargue los nuevos valores
# sudo systemctl restart contaec-backend
# # Espera 30 segundos
# sleep 30
# # Verificar que arrancó
# sudo systemctl status contaec-backend
# # Test conexión
# curl http://localhost:8000/api/health
# ```

# ### 4.9 Configuración de Caddy (Proxy Reverso)
# 
# ```bash
# # Instalar Caddy
# apt install -y debian-keyring debian-archive-keyring apt-transport-https
# curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
# curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
# apt update
# apt install -y caddy
# ```
# 
# Editar el Caddyfile (`/etc/caddy/Caddyfile`):
# 
# ```
# conta.tymtechnology.shop {
#     # Proxy principal → Next.js (frontend + API proxy)
#     reverse_proxy localhost:3000
# 
#     # Seguridad
#     header {
#         X-Content-Type-Options nosniff
#         X-Frame-Options DENY
#         X-XSS-Protection "1; mode=block"
#         Referrer-Policy strict-origin-when-cross-origin
#         Strict-Transport-Security "max-age=31536000; includeSubDomains"
#     }
# 
#     # Compresión
#     encode gzip zstd
# 
#     # Logs
#     log {
#         output file /var/log/caddy/contaec.log
#         format console
#     }
# }
# ```
# 
# ```bash
# # Crear directorio de logs
# mkdir -p /var/log/caddy
# chown caddy:caddy /var/log/caddy
# 
# # Reiniciar Caddy
# systemctl restart caddy
# 
# # Verificar que Caddy obtuvo certificado SSL
# systemctl status caddy
# journalctl -u caddy --no-pager | tail -20
# ```

### 4.10 Instalación de ClamAV

```bash
# Instalar ClamAV y el daemon
apt install -y clamav clamav-daemon

# Configurar clamd para socket TCP (más compatible con Python)
nano -l /etc/clamav/clamd.conf
# Asegurar estas líneas si no existen agregarlas al final:
TCPSocket 3310
TCPAddr 127.0.0.1
# o usar socket Unix:
# LocalSocket /var/run/clamav/clamd.ctl

# Actualizar base de datos de virus
# 1. Detener clamav-daemon y clamav-freshclam
sudo systemctl stop clamav-daemon clamav-freshclam
# 2. Actualizar base de firmas
sudo freshclam
# 3. Reiniciar servicios
sudo systemctl start clamav-daemon clamav-freshclam
# 4. Si esta desabilitado uno de los servicios habilitarlos
sudo systemctl enable clamav-daemon clamav-freshclam
# 5. Verificar estado
sudo systemctl status clamav-daemon clamav-freshclam

### Permisos de Archivos

```bash
# Proteger el archivo .env
chmod 600 /opt/contaec/backend/.env
# Proteger directorio de backups y firmas digitales
chmod 700 /opt/contaec/backend/backups /opt/contaec/backend/signatures
# Proteger directorio de uploads
chmod 755 /opt/contaec/backend/uploads
# Proteger todos los propietarios
chown www-data:www-data /opt/contaec/backend/.env /opt/contaec/backend/backups /opt/contaec/backend/signatures /opt/contaec/backend/uploads
```

```sh
### 4.11 Integración de Email Templates en Frontend

El sistema incluye un editor visual de plantillas de correo en `src/components/email-template-editor.tsx`.

**Características del editor:**
- Lista de plantillas con filtro por tipo (factura, nota_credito, proforma, general)
- Formulario modal para crear/editar plantillas
- Insertador de variables dinámicas (click para insertar `{{variable}}`)
- Vista previa con datos de ejemplo
- Activación/desactivación de plantillas
- Selección de plantilla por defecto por tipo

**Variables disponibles:**
`{{razon_social}}`, `{{ruc}}`, `{{cliente_nombre}}`, `{{cliente_cedula}}`, `{{secuencial}}`, `{{clave_acceso}}`, `{{fecha_emision}}`, `{{subtotal}}`, `{{iva}}`, `{{total}}`, `{{numero_autorizacion}}`

**Uso en la aplicación:**
Importar el componente en la página de configuración de email:
```tsx
import { EmailTemplateEditor } from '@/components/email-template-editor';

// En tu página
<EmailTemplateEditor companyId={companyId} />
```

### 4.12 Creacion de symlink
```bash
ln -sf /opt/contaec/backend/uploads /opt/contaec/public/uploads
ls -la /opt/contaec/public/
ls -la /opt/contaec/backend/uploads/
---

## Solución de Problemas

### El backend no arranca

```bash
# Verificar logs del servicio
journalctl -u contaec-backend --no-pager | tail -50

# Verificar que PostgreSQL está corriendo
systemctl status postgresql

# Verificar conexión a la BD
psql -U contaec_user -d contaec_db -h localhost -c "SELECT 1;"

# Verificar que el .env tiene las variables correctas
cat /opt/contaec/backend/.env | grep DATABASE_URL
```

### Error de certificado SSL SRI

El SRI usa certificados que pueden no estar en el bundle CA del sistema. Si hay errores SSL:

```bash
# Descargar certificado del SRI
echo | openssl s_client -connect celcer.sri.gob.ec:443 2>/dev/null | openssl x509 > /usr/local/share/ca-certificates/sri.crt
update-ca-certificates
```

### Error de firma electrónica

1. Verificar que el archivo .p12/.pfx es válido
2. Verificar que la contraseña es correcta
3. Verificar que la firma no ha expirado
4. El sistema detecta automáticamente CAs ecuatorianas (BCE, Security Data, ANF)

### El frontend no conecta al backend

1. Verificar que el backend está en puerto 8000: `curl http://localhost:8000/api/health`
2. Verificar que Caddy está proxyando correctamente: `curl https://conta.tymtechnology.shop/api/health`
3. Verificar CORS en el .env: `CORS_ORIGINS=https://conta.tymtechnology.shop`

### Resetear password de admin

```bash
cd /opt/contaec/backend
source /opt/contaec/.venv/bin/activate
python3 -c "
import bcrypt
new_pass = 'NUEVA_PASSWORD'
hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
print(f'Hash: {hashed}')
print('Ejecutar en PostgreSQL:')
print(f\"UPDATE users SET hashed_password = '{hashed}' WHERE email = 'steve.mejia@tymtechnology.shop';\")
"
```

---

## Comandos Útiles

```bash
# Reiniciar todos los servicios
systemctl restart postgresql contaec-backend contaec-frontend caddy

# Ver estado de todos los servicios
systemctl status postgresql contaec-backend contaec-frontend caddy

# Ver logs en tiempo real
journalctl -u contaec-backend -f

# Respaldar la base de datos manualmente
sudo -u postgres pg_dump contaec_db > /opt/contaec/backups/manual_$(date +%Y%m%d_%H%M%S).sql

# Restaurar base de datos desde SQL
sudo -u postgres psql contaec_db < /opt/contaec/backups/manual_YYYYMMDD_HHMMSS.sql

# Actualizar la aplicación
cd /opt/contaec
git pull  # o copiar nuevos archivos
cd backend && source /opt/contaec/.venv/bin/activate && pip install -r requirements.txt
cd .. && bun install && bun run build
systemctl restart contaec-backend contaec-frontend
```

---

## Estadísticas del Proyecto

| Métrica | Cantidad |
|---------|----------|
| Modelos SQLAlchemy | 144+ (10 Fase 1 RRHH + 6 Fase 5 Compras + 5 Fase 6 Multi-Almacén + 4 Fase 7 POS + 5 Fase 8 BI + 4 Fase 9 Presupuestos + 8 Fase 10 CRM + 5 Fase 11 Proyectos + 10 Fase 12 Integraciones + 6 Fase 13 ML/IA) |
| Endpoints API | ~595 (+17 Fase 1, +6 Fase 6 Email, ~20 Fase 5 Compras, ~15 Fase 6 Multi-Almacén, ~15 Fase 7 POS, ~15 Fase 8 BI, ~20 Fase 9 Presupuestos, ~25 Fase 10 CRM, ~20 Fase 11 Proyectos, ~55 Fase 12 Integraciones, ~23 Fase 13 ML/IA) |
| Schemas Pydantic | ~11,000 líneas |
| Componentes React | 70+ dominio + 45 UI (+1 email-template-editor, +1 bi-dashboard, +1 budgets, +1 crm, +1 projects, +1 integrations, +1 ml-ai) |
| Funciones API (frontend) | ~400 |
| Tipos TypeScript | ~210 |
| Traducciones i18n | ~350 keys × 3 idiomas (next-intl) |
| Librerías Python | 27 |
| Módulos Core | 17 (+2 en Fase 1: payroll_calculations.py, ir_calculation.py) |
| Fases Completadas | 13/13 ✅ (Fase 0-13 completas per Plan_Maestro.md) |

---

**ContaEC** - Sistema Contable y Facturación Electrónica del Ecuador  
© 2024 T&M Technology Ec | info@tymtechnology.shop | 0960068866

---

## Migración a next-intl (Internacionalización)

El sistema utiliza **next-intl v3** para la gestión de traducciones. Esta sección describe la configuración y migración desde el i18n customizado.

### Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `messages/es.json` | Traducciones en español (350+ keys) |
| `messages/en.json` | Traducciones en inglés |
| `messages/pt.json` | Traducciones en portugués |
| `src/i18n.ts` | Configuración `getRequestConfig` de next-intl |
| `src/i18n-config.ts` | Configuración de locales y helpers |
| `src/middleware.ts` | Middleware para detección de idioma |
| `src/app/layout.tsx` | `NextIntlClientProvider` envolviendo la app |
| `next-intl.config.ts` | Plugin de next-intl para Next.js |
| `next.config.ts` | Integrado con `withNextIntl` |
| `package.json` | Dependencia `next-intl@^3.26.0` |

### Locales Soportados

| Código | Nombre | Default |
|--------|--------|---------|
| `es` | Español (Ecuador) | ✅ |
| `en` | English (US) | |
| `pt` | Português (Brasil) | |

### URL Structure

```
https://conta.tymtechnology.shop/           # → Redirige a /es (default)
https://conta.tymtechnology.shop/es/        # Español
https://conta.tymtechnology.shop/en/        # English
https://conta.tymtechnology.shop/pt/        # Portuguese
```

### Instalación en Producción

```bash
cd /opt/contaec
bun install              # Instala next-intl automáticamente
bun run build            # Build de producción
systemctl restart contaec-frontend
```

### Migración de Componentes

**Patrón para actualizar componentes que usan traducciones:**

```typescript
// ANTES (i18n customizado - OBSOLETO)
import { useI18n } from '@/lib/i18n-context';
const { t } = useI18n();
t('nav.dashboard')

// AHORA (next-intl)
import { useTranslations } from 'next-intl';
const t = useTranslations('Navigation');
t('dashboard')
```

**Ejemplo completo - Componente Cliente:**

```typescript
'use client';
import { useTranslations } from 'next-intl';

export function DashboardWelcome() {
  const t = useTranslations('Dashboard');
  
  return (
    <div>
      <h1>{t('welcome')}</h1>
      <p>{t('companies')}</p>
      <span>{t('days_remaining', { days: 5 })}</span>
    </div>
  );
}
```

**Ejemplo - Componente Servidor:**

```typescript
import { getTranslations } from 'next-intl/server';

export default async function Dashboard() {
  const t = await getTranslations('Navigation');
  
  return <h1>{t('dashboard')}</h1>;
}
```

### Interpolación de Variables

```typescript
// messages/es.json
{
  "Dashboard": {
    "days_remaining": "{days} días restantes"
  }
}

// Componente
t('days_remaining', { days: 5 })  // "5 días restantes"
```

### Formateo de Fechas y Números

```typescript
import { useTranslations, useTimeZone } from 'next-intl';

export function FechaContable({ fecha, monto }) {
  const t = useTranslations();
  const timeZone = useTimeZone();
  
  return (
    <div>
      {/* Fecha formateada */}
      <span>{t.formatDate(fecha, { timeZone })}</span>
      
      {/* Número como moneda */}
      <span>{t.formatNumber(monto, { style: 'currency', currency: 'USD' })}</span>
    </div>
  );
}
```

### Selector de Idioma

```typescript
'use client';
import { useLocale } from 'next-intl';
import { locales, localeNames } from '@/i18n-config';
import { usePathname, useRouter } from 'next/navigation';

export function LocaleSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  function handleLocaleChange(newLocale: string) {
    const newPath = pathname.replace(/^\/[a-z]{2}/, `/${newLocale}`);
    router.push(newPath);
  }

  return (
    <Select value={locale} onValueChange={handleLocaleChange}>
      {locales.map((loc) => (
        <SelectItem key={loc} value={loc}>
          {localeNames[loc]}
        </SelectItem>
      ))}
    </Select>
  );
}
```

### Archivos Obsoletos (Eliminar después de migrar)

Después de actualizar todos los componentes:

```bash
rm src/lib/i18n.ts              # 1097 líneas - traducciones hardcodeadas
rm src/lib/i18n-context.tsx     # Contexto React customizado
```

### Comandos Útiles

```bash
# Buscar componentes que necesitan migración
grep -r "useI18n" src/components/ --include="*.tsx"

# Verificar instalación
bun list next-intl

# Build de producción
bun run build
```

### Solución de Problemas

| Error | Solución |
|-------|----------|
| `Module not found: next-intl` | Ejecutar `bun install` |
| `Messages not loaded` | Verificar `NextIntlClientProvider` en layout.tsx |
| `Locale segment not found` | El middleware requiere `/es/`, `/en/`, `/pt/` en las rutas |
| Traducciones no actualizadas | Ejecutar `bun run build` y reiniciar frontend |

### Helper para Códigos Legacy

Si necesitas compatibilidad con códigos legacy (es_EC, en_US, pt_BR):

```typescript
import { legacyToNextIntl, nextIntlToLegacy } from '@/i18n-config';

// Convertir de legacy a next-intl
const newLocale = legacyToNextIntl('es_EC'); // retorna 'es'

// Convertir de next-intl a legacy (para API calls, DB, etc.)
const legacyCode = nextIntlToLegacy('es'); // retorna 'es_EC'
```
