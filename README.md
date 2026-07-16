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

### Locale del sistema (o configuración de locales)
# 1. Instalar el paquete locales
sudo apt-get install locales
# 2. Generar el locale es_EC.UTF-8
sudo locale-gen es_EC.UTF-8
# 3. Reconfigurar locales
sudo dpkg-reconfigure locales
# 4. Selecciona es_EC.UTF-8 como default
sudo locale-gen es_EC.UTF-8
# 5. Verificar que se instaló
locale -a | grep es_EC
# 6. Verificar el locale disponible
locale -a | grep UTF-8
# 7. Configurar permanentemente en /etc/environment
sudo nano /etc/environment
# 8. Agregar estas líneas (en el editor nano)
LANG=es_EC.UTF-8
LC_ALL=es_EC.UTF-8
LANGUAGE=es_EC.UTF-8
# 9. Aplicar (opcional, para el shell actual)
source /etc/environment
# 10. Persistir permanentemente en /etc/environment (alternativa sin nano)
echo 'LANG=es_EC.UTF-8' > /etc/environment
echo 'LC_ALL=es_EC.UTF-8' >> /etc/environment
echo 'LANGUAGE=es_EC.UTF-8' >> /etc/environment
# 11. Exportar para el shell actual
export LANGUAGE=es_EC.UTF-8
export LANG=es_EC.UTF-8
export LC_ALL=es_EC.UTF-8
# 12. Opcional: agregar también a /etc/profile para persistencia en todas las sesiones
echo 'export LANG=es_EC.UTF-8' >> /etc/profile
echo 'export LC_ALL=es_EC.UTF-8' >> /etc/profile
echo 'export LANGUAGE=es_EC.UTF-8' >> /etc/profile
# 13. Reinicia el shell o ejecuta:
bash
# 14. Luego verifica:
locale
# 15. Verifica que ya no aparezca el error
perl -v
```

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

**Configuración de PostgreSQL** (`/etc/postgresql/17/main/postgresql.conf`):

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

**Configuración de acceso** (`/etc/postgresql/17/main/pg_hba.conf`):

```
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
nano /opt/contaec/backend/.env

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

Crear el archivo `/opt/contaec/backend/.env` con el siguiente contenido:

```bash
# ============================================
# ContaEC - Variables de Entorno de Producción
# ============================================

# --- Aplicación ---
APP_NAME=ContaEC
APP_VERSION=1.0.0
APP_ENV=production
DEBUG=false

# SECURITY: Generar claves únicas y seguras con:
# SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
SECRET_KEY=<GENERAR_CON_PYTHON>
ENCRYPTION_KEY=<GENERAR_CON_PYTHON>
JWT_SECRET_KEY=<GENERAR_CON_PYTHON>

# --- Base de Datos (PostgreSQL) ---
DATABASE_URL=postgresql+asyncpg://contaec_user:<TU_PASSWORD>@localhost:5432/contaec_db
POSTGRES_USER=contaec_user
POSTGRES_PASSWORD=<TU_PASSWORD_POSTGRES>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=contaec_db

# --- Autenticación JWT ---
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# --- Credenciales Admin ---
ADMIN_EMAIL=steve.mejia@tymtechnology.shop
ADMIN_PASSWORD=<GENERAR_CONTRASENA_SEGURA>

# --- Servicios Web del SRI ---
# (Las URLs ya están configuradas por defecto en config.py)
# SRI_WS_RECEPCION_PRUEBAS=https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
# SRI_WS_AUTORIZACION_PRUEBAS=https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl
# SRI_WS_RECEPCION_PRODUCCION=https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
# SRI_WS_AUTORIZACION_PRODUCCION=https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl

# --- Respaldos ---
BACKUP_DIR=./backups
BACKUP_ENCRYPTION_KEY=<GENERAR_CON_PYTHON>

# --- ClamAV (Antivirus) ---
CLAMAV_ENABLED=true
CLAMAV_SOCKET=/var/run/clamav/clamd.ctl
CLAMAV_HOST=127.0.0.1
CLAMAV_PORT=3310

# --- VirusTotal ---
VIRUSTOTAL_ENABLED=false
VIRUSTOTAL_API_KEY=<TU_API_KEY_VIRUSTOTAL>

# --- CORS ---
CORS_ORIGINS=https://conta.tymtechnology.shop,http://10.0.1.20

# --- Rate Limiting ---
RATE_LIMIT_PER_MINUTE=60

# --- Servidor ---
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# --- Almacenamiento Volátil ---
TEMP_DIR=./temp
UPLOAD_DIR=./uploads
```

```bash
# Ejecutar estas líneas y copiar los resultados al .env
source /opt/contaec/.venv/bin/activate
# SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
# ENCRYPTION_KEY
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(64))"
# JWT_SECRET_KEY
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
# BACKUP_ENCRYPTION_KEY (Fernet)
python3 -c "from cryptography.fernet import Fernet; print('BACKUP_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

```bash
# Reiniciar el servicio para que cargue los nuevos valores
sudo systemctl restart contaec-backend
# Espera 30 segundos
sleep 30
# Verificar que arrancó
sudo systemctl status contaec-backend
# Test conexión
curl http://localhost:8000/api/health
```

### 4.9 Configuración de Caddy (Proxy Reverso)

```bash
# Instalar Caddy
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy
```

Editar el Caddyfile (`/etc/caddy/Caddyfile`):

```
conta.tymtechnology.shop {
    # Proxy principal → Next.js (frontend + API proxy)
    reverse_proxy localhost:3000

    # Seguridad
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }

    # Compresión
    encode gzip zstd

    # Logs
    log {
        output file /var/log/caddy/contaec.log
        format console
    }
}
```

```bash
# Crear directorio de logs
mkdir -p /var/log/caddy
chown caddy:caddy /var/log/caddy

# Reiniciar Caddy
systemctl restart caddy

# Verificar que Caddy obtuvo certificado SSL
systemctl status caddy
journalctl -u caddy --no-pager | tail -20
```

### 4.10 Instalación de ClamAV

```bash
# Instalar ClamAV y el daemon
apt install -y clamav clamav-daemon

# Actualizar base de datos de virus
# 1. Detener clamav-daemon
sudo systemctl stop clamav-daemon
# 2. Detener clamav-freshclam
sudo systemctl stop clamav-freshclam
# 3. Actualizar base de firmas
sudo freshclam
# 4. Reiniciar servicios
sudo systemctl start clamav-daemon
sudo systemctl start clamav-freshclam
# 5. Verificar estado
sudo systemctl status clamav-daemon
sudo systemctl status clamav-freshclam

# Configurar clamd para socket TCP (más compatible con Python)
# Editar /etc/clamav/clamd.conf
# Asegurar estas líneas:
# TCPSocket 3310
# TCPAddr 127.0.0.1
# o usar socket Unix:
# LocalSocket /var/run/clamav/clamd.ctl
```

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

## Estructura del Proyecto

```
ContaECv4/
├── backend/                        # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── accounting.py   # Plan de cuentas, asientos, balances
│   │   │   │   ├── admin.py        # Panel de administración
│   │   │   │   ├── audit.py        # Logs de auditoría
│   │   │   │   ├── auth.py         # Autenticación JWT
│   │   │   │   ├── backup.py       # Backups de base de datos
│   │   │   │   ├── bi.py           # Business Intelligence
│   │   │   │   ├── budgets.py      # Presupuestos
│   │   │   │   ├── clients.py      # Gestión de clientes
│   │   │   │   ├── companies.py    # Empresas + consulta RUC SRI
│   │   │   │   ├── comprobantes.py # Facturación electrónica SRI
│   │   │   │   ├── config.py       # Configuración del sistema
│   │   │   │   ├── crm.py          # CRM (pipeline, leads, oportunidades)
│   │   │   │   ├── email_receiver.py   # Recepción de correos
│   │   │   │   ├── email_templates.py  # Plantillas de correo
│   │   │   │   ├── employees.py    # Gestión de empleados
│   │   │   │   ├── exports.py      # Exportación de datos
│   │   │   │   ├── imports.py      # Importación de datos
│   │   │   │   ├── integrations.py # Integraciones externas
│   │   │   │   ├── kardex.py       # Kardex de inventario
│   │   │   │   ├── licenses.py     # Gestión de licencias
│   │   │   │   ├── ml_ai.py        # ML/AI endpoints
│   │   │   │   ├── notifications.py # Notificaciones
│   │   │   │   ├── payroll.py      # Nómina (roles, décimos, liquidaciones)
│   │   │   │   ├── pos.py          # Punto de Venta
│   │   │   │   ├── products.py     # Gestión de productos
│   │   │   │   ├── proformas.py    # Proformas/cotizaciones
│   │   │   │   ├── projects.py     # Gestión de proyectos
│   │   │   │   ├── purchases.py    # Compras
│   │   │   │   ├── smtp_profiles.py # Perfiles SMTP
│   │   │   │   ├── suppliers.py    # Gestión de proveedores
│   │   │   │   ├── uploads.py      # Subida de archivos
│   │   │   │   ├── user_roles.py   # Roles de usuario por empresa
│   │   │   │   └── warehouses.py   # Gestión de bodegas
│   │   │   └── router.py           # Router principal (~331 rutas)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── audit.py            # Logging de auditoría
│   │   │   ├── config.py           # Configuración (.env + pydantic)
│   │   │   ├── database.py         # SQLAlchemy async engine
│   │   │   ├── email_receiver.py   # Recepción de correos IMAP
│   │   │   ├── email_service.py    # Envío de correo SMTP
│   │   │   ├── encryption.py       # Cifrado Fernet (datos sensibles)
│   │   │   ├── hr_constants.py     # Constantes de RRHH Ecuador
│   │   │   ├── rate_limiter.py     # Rate limiting
│   │   │   ├── ride_generator.py   # PDF RIDE (factura impresa)
│   │   │   ├── scanner.py          # ClamAV + VirusTotal
│   │   │   ├── security.py         # JWT + bcrypt + blacklist
│   │   │   ├── sri_service.py      # Cliente SOAP SRI
│   │   │   ├── token_blacklist.py  # Blacklist de tokens JWT
│   │   │   ├── utils.py            # Utilidades generales
│   │   │   ├── volatile_storage.py # Almacenamiento volátil
│   │   │   ├── xml_generator.py    # Generación XML SRI
│   │   │   └── xml_signer.py       # Firma XAdES-BES
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── security.py         # Rate limit + sanitización + headers
│   │   ├── models/                 # Modelos SQLAlchemy
│   │   │   ├── __init__.py
│   │   │   ├── accounting.py       # Modelo contabilidad
│   │   │   ├── audit_log.py        # Modelo logs auditoría
│   │   │   ├── budget.py           # Modelo presupuestos
│   │   │   ├── client.py           # Modelo clientes
│   │   │   ├── company.py          # Modelo empresas
│   │   │   ├── comprobante.py      # Modelo comprobantes
│   │   │   ├── crm.py              # Modelo CRM
│   │   │   ├── email_template.py   # Modelo plantillas correo
│   │   │   ├── employee.py         # Modelo empleados
│   │   │   ├── hr_extended.py      # Modelo RRHH extendido
│   │   │   ├── hr_extended2.py     # Modelo RRHH extendido 2
│   │   │   ├── integration.py      # Modelo integraciones
│   │   │   ├── kardex.py           # Modelo kardex
│   │   │   ├── ml_ai.py            # Modelo ML/AI
│   │   │   ├── notification.py     # Modelo notificaciones
│   │   │   ├── payroll.py          # Modelo nómina
│   │   │   ├── pos.py              # Modelo punto de venta
│   │   │   ├── product.py          # Modelo productos
│   │   │   ├── proforma.py         # Modelo proformas
│   │   │   ├── project.py          # Modelo proyectos
│   │   │   ├── purchase.py         # Modelo compras
│   │   │   ├── smtp_profile.py     # Modelo perfiles SMTP
│   │   │   ├── supplier.py         # Modelo proveedores
│   │   │   ├── user.py             # Modelo usuarios
│   │   │   ├── user_company_role.py # Modelo roles por empresa
│   │   │   └── warehouse.py        # Modelo bodegas
│   │   ├── schemas/                # Schemas Pydantic
│   │   │   ├── __init__.py
│   │   │   ├── accounting.py       # Schema contabilidad
│   │   │   ├── audit_log.py        # Schema logs auditoría
│   │   │   ├── auth.py             # Schema autenticación
│   │   │   ├── bi.py               # Schema BI
│   │   │   ├── budget.py           # Schema presupuestos
│   │   │   ├── client.py           # Schema clientes
│   │   │   ├── company.py          # Schema empresas
│   │   │   ├── comprobante.py      # Schema comprobantes
│   │   │   ├── crm.py              # Schema CRM
│   │   │   ├── email_template.py   # Schema plantillas correo
│   │   │   ├── employee.py         # Schema empleados
│   │   │   ├── hr_extended2.py     # Schema RRHH extendido
│   │   │   ├── integration.py      # Schema integraciones
│   │   │   ├── kardex.py           # Schema kardex
│   │   │   ├── ml_ai.py            # Schema ML/AI
│   │   │   ├── notification.py     # Schema notificaciones
│   │   │   ├── payroll.py          # Schema nómina
│   │   │   ├── pos.py              # Schema punto de venta
│   │   │   ├── product.py          # Schema productos
│   │   │   ├── proforma.py         # Schema proformas
│   │   │   ├── project.py          # Schema proyectos
│   │   │   ├── purchase.py         # Schema compras
│   │   │   ├── smtp_profile.py     # Schema perfiles SMTP
│   │   │   ├── sri.py              # Schema SRI
│   │   │   ├── supplier.py         # Schema proveedores
│   │   │   ├── user_company_role.py # Schema roles por empresa
│   │   │   └── warehouse.py        # Schema bodegas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── ml_service.py       # Servicio de ML
│   │   ├── __init__.py
│   │   └── main.py                 # Entry point FastAPI
│   ├── requirements.txt            # Dependencias Python
│   ├── deploy/
│   │   └── postgresql_blueprint.md # Guía de migración PostgreSQL
│   ├── package.json                # Dependencias Node (mini-services)
│   ├── run.sh                      # Script de ejecución
│   └── start.sh                    # Script de inicio
│
├── src/                            # Next.js 16 Frontend
│   ├── app/
│   │   ├── api/[...path]/
│   │   │   └── route.ts            # API proxy → FastAPI
│   │   ├── globals.css             # Estilos globales
│   │   ├── layout.tsx              # Layout raíz
│   │   └── page.tsx                # Entry point (login/dashboard/admin)
│   ├── components/
│   │   ├── contaec-accounting.tsx  # Contabilidad
│   │   ├── contaec-admin.tsx       # Panel admin
│   │   ├── contaec-audit.tsx       # Auditoría
│   │   ├── contaec-bi.tsx          # Business Intelligence
│   │   ├── contaec-budgets.tsx     # Presupuestos
│   │   ├── contaec-crm.tsx         # CRM
│   │   ├── contaec-dashboard.tsx   # Dashboard principal
│   │   ├── contaec-hr.tsx          # Recursos Humanos
│   │   ├── contaec-integrations.tsx # Integraciones
│   │   ├── contaec-inventory.tsx   # Inventario
│   │   ├── contaec-invoices.tsx    # Facturación SRI
│   │   ├── contaec-login.tsx       # Login
│   │   ├── contaec-ml-ai.tsx       # ML/AI
│   │   ├── contaec-pos.tsx         # Punto de Venta
│   │   ├── contaec-projects.tsx    # Proyectos
│   │   ├── contaec-purchases.tsx   # Compras
│   │   ├── contaec-settings.tsx    # Configuración
│   │   ├── contaec-suppliers.tsx   # Proveedores
│   │   ├── contaec-warehouses.tsx  # Bodegas
│   │   ├── providers.tsx           # Providers (theme, query, etc.)
│   │   └── ui/                     # Componentes shadcn/ui
│   │       ├── accordion.tsx
│   │       ├── alert-dialog.tsx
│   │       ├── alert.tsx
│   │       ├── aspect-ratio.tsx
│   │       ├── avatar.tsx
│   │       ├── badge.tsx
│   │       ├── breadcrumb.tsx
│   │       ├── button.tsx
│   │       ├── calendar.tsx
│   │       ├── card.tsx
│   │       ├── carousel.tsx
│   │       ├── chart.tsx
│   │       ├── checkbox.tsx
│   │       ├── collapsible.tsx
│   │       ├── command.tsx
│   │       ├── context-menu.tsx
│   │       ├── dialog.tsx
│   │       ├── drawer.tsx
│   │       ├── dropdown-menu.tsx
│   │       ├── form.tsx
│   │       ├── hover-card.tsx
│   │       ├── input-otp.tsx
│   │       ├── input.tsx
│   │       ├── label.tsx
│   │       ├── menubar.tsx
│   │       ├── navigation-menu.tsx
│   │       ├── pagination.tsx
│   │       ├── popover.tsx
│   │       ├── progress.tsx
│   │       ├── radio-group.tsx
│   │       ├── resizable.tsx
│   │       ├── scroll-area.tsx
│   │       ├── select.tsx
│   │       ├── separator.tsx
│   │       ├── sheet.tsx
│   │       ├── sidebar.tsx
│   │       ├── skeleton.tsx
│   │       ├── slider.tsx
│   │       ├── sonner.tsx
│   │       ├── switch.tsx
│   │       ├── table.tsx
│   │       ├── tabs.tsx
│   │       ├── textarea.tsx
│   │       ├── toast.tsx
│   │       ├── toaster.tsx
│   │       ├── toggle-group.tsx
│   │       ├── toggle.tsx
│   │       └── tooltip.tsx
│   ├── hooks/
│   │   ├── use-mobile.ts           # Hook responsive mobile
│   │   └── use-toast.ts            # Hook notificaciones toast
│   └── lib/
│       ├── api.ts                  # ~320 funciones API + ~170 tipos
│       ├── db.ts                   # Utilidades de base de datos
│       ├── i18n.ts                 # 3 idiomas (es_EC, en_US, pt_BR)
│       └── utils.ts                # Utilidades Tailwind
│
├── prisma/
│   └── schema.prisma               # Schema Prisma (legacy, no usado en prod)
│
├── db/
│   └── custom.db                   # Base de datos personalizada
│
├── download/
│   └── README.md                   # Documentación de descargas
│
├── examples/
│   └── websocket/
│       ├── frontend.tsx            # Ejemplo cliente WebSocket
│       └── server.ts               # Ejemplo servidor WebSocket
│
├── mini-services/
│   ├── contaec-backend/
│   │   ├── contaec.db              # SQLite mini-service
│   │   ├── index.ts                # Entry point
│   │   ├── package.json
│   │   └── run.sh
│   └── .gitkeep
│
├── public/
│   ├── logo.svg                    # Logo del sistema
│   └── robots.txt                  # Robots.txt
│
├── upload/
│   └── FICHA_TECNICA.pdf           # Ficha técnica del proyecto
│
├── .env.example                    # Variables de entorno de ejemplo
├── .gitattributes
├── .gitignore
├── bun.lock                        # Lock file Bun
├── Caddyfile                       # Configuración proxy reverso
├── components.json                 # Configuración shadcn/ui
├── contaec.db                      # Base de datos SQLite principal
├── contaec.db-shm                  # SQLite shared memory
├── contaec.db-wal                  # SQLite write-ahead log
├── eslint.config.mjs               # Configuración ESLint
├── next.config.ts                  # Configuración Next.js
├── package.json                    # Dependencias Node.js
├── postcss.config.mjs              # Configuración PostCSS
├── tailwind.config.ts              # Configuración Tailwind
├── tsconfig.json                   # Configuración TypeScript
├── worklog.md                      # Registro de trabajo
├── worklog-new.md                  # Registro de trabajo (nuevo)
├── ia.md                           # Documentación IA
└── README.md                       # Este archivo
```

---

## Módulos y Funcionalidades

### Fase 0: Infraestructura Base ✅ COMPLETA (7/7 pasos)

| Paso | Funcionalidad | Archivos Principales | Endpoints |
|------|---------------|---------------------|-----------|
| **0.1** | Almacenamiento volátil con cleanup automático | `core/cleanup.py`, `core/volatile_storage.py` | `POST /api/v1/volatile/cleanup`, `GET /api/v1/volatile/status` |
| **0.2** | Catálogos SRI (IVA, ICE, Retenciones) | `schemas/sri.py` | `GET /api/v1/comprobantes/catalogos` |
| **0.3** | Estados de comprobante electrónico (9 estados) | `models/comprobante.py`, `schemas/comprobante.py` | `GET /api/v1/comprobantes/estados` |
| **0.4** | Tipos de contribuyente y regímenes (8 tipos) | `schemas/sri.py` | `GET /api/v1/companies/catalogos/contribuyentes` |
| **0.5** | Integración ClamAV + VirusTotal | `core/scanner.py` | `GET /api/v1/config/clamav-status` |
| **0.6** | Alertas de licenciamiento + Panel Admin | `api/v1/endpoints/admin.py`, `licenses.py` | `GET /api/v1/admin/dashboard`, `/system-health`, `/licenses/check-expiry` |
| **0.7** | Backup automático + Email Templates + Sandbox Mode | `api/v1/endpoints/backup.py`, `email_templates.py`, `config.py` | `POST /api/v1/backup/create`, `/email-templates`, `/config/environment-mode` |

**Características técnicas:**
- FastAPI (Python 3.12) + Next.js 16 (React 19)
- PostgreSQL (bloqueado en producción, SQLite solo desarrollo)
- Caddy proxy reverso con SSL Let's Encrypt
- 30+ endpoints añadidos en Fase 0
- 4 tipos de licencia: Mensual ($15), Trimestral ($40), Semestral ($75), Anual ($130)
- IVA 15% default (9 códigos: 0%, 5%, 8%, 12%, 13%, 14%, 15%, No objeto, Exento)
- ICE: 24 códigos de productos gravados
- Retenciones: 8 tasas (0%, 10%, 20%, 30%, 50%, 70%, 100%)

### Fase 1: Auth, Multiempresa, Admin, Licencias, ClamAV ✅
- JWT con revocación (blacklist) y rotación de refresh tokens
- Multi-empresa con roles granulares por empresa (UserCompanyRole)
- Panel admin con dashboard, salud del sistema, gestión de usuarios
- Licenciamiento: mensual, trimestral, semestral, anual
- Alerta de licencia por expirar (15 días antes)
- Renovación por WhatsApp (wa.me/593960068866)
- ClamAV + VirusTotal para escaneo de archivos subidos
- Rate limiting (60 req/min por IP)
- Sanitización de entradas (SQL injection + XSS)
- Headers de seguridad (CSP, X-Frame-Options, etc.)

### Fase 2: Facturación Electrónica SRI ✅
- 10 tarifas IVA: 0%, 5%, 8%, 12%, 13%, 14%, 15% (default), No objeto, Exento, Diferenciado
- 34 tarifas ICE con ad valorem + específica
- Retenciones IVA (10%, 20%, 30%, 50%, 70%, 100%, 0%) y Renta (28 códigos)
- 8 estados de comprobante: BORRADOR, FIRMADO, ENVIADO, AUTORIZADO, RECHAZADO, DEVUELTA, CADUCADA, CONTINGENCIA
- 8 tipos de contribuyente y 7 tipos de régimen (incluyendo RIMPE)
- Consumidor Final (cliente por defecto)
- Proformas con conversión a factura
- Facturas, Notas de Crédito/Débito, Retenciones, Guías de Remisión, Liquidación de Compras
- Generación XML per Ficha Técnica SRI v2.32 (clave acceso módulo 11)
- Firma XAdES-BES (RSA-SHA256) con signxml
- Comunicación SOAP con SRI (enviar + consultar con reintentos)
- RIDE PDF con código de barras, QR y todas las secciones SRI
- Pre-validación (8 reglas) y corrección de rechazados
- Envío por email de comprobantes autorizados
- Procesar (1-click: firmar + enviar + consultar)

### Fase 3: Inventario y Kardex ✅
- Control de productos con stock, stock mínimo, código de barras
- Kardex con saldos corridos (saldo_cantidad, saldo_valor)
- Métodos de valoración: FIFO, LIFO, Promedio Ponderado
- Ajustes de inventario
- Importación desde Excel y CSV
- Exportación a Excel, CSV, PDF, ZIP
- Almacenamiento volátil con auto-limpieza

### Fase 4: Nómina RRHH Completa ✅ IMPLEMENTADA (5/5 subfases)

| Subfase | Descripción | Modelos/Archivos | Endpoints Nuevos |
|---------|-------------|------------------|------------------|
| **1.1** | Modelos RRHH Extendidos | `hr_contract.py`, `hr_vacation.py`, `hr_loan.py`, `hr_history.py`, `hr_shift.py` | - |
| **1.2** | Cálculos Automáticos | `payroll_calculations.py`, `ir_calculation.py` | - |
| **1.3** | Reportes SRI Nómina | `payroll_reports.py` | `/rdep/xml`, `/rdep`, `/anexos-iess`, `/sut-xiii-xiv`, `/ir-retenciones` |
| **1.4** | Exportaciones Bancarias | `payroll_exports.py` | `/banco/pichincha`, `/banco/guayaquil`, `/banco/pacifico`, `/csv`, `/rol-pago/pdf`, `/excel` |
| **1.5** | Integración Asistencia | `attendance.py` | `/attendance/registro`, `/import/biometrico`, `/turnos/asignar`, `/resumen`, `/faltas` |

**Modelos creados (10 nuevos):**
- `Contrato` (Contrato laboral histórico): tipo_contrato, cargo, fecha_inicio, sueldo_base, estado
- `VacacionesPeriodo`: dias_correspondientes (15 + adicionales), dias_tomados, dias_pendientes
- `VacacionesSolicitud`: fecha_inicio, fecha_fin, estado, aprobacion
- `VacacionesHistorial`: registro histórico de vacaciones tomadas
- `PrestamoEmpleado`: monto_solicitado, numero_cuotas, saldo_pendiente, descuento_porcentaje (max 30%)
- `PrestamoDetalle`: registro de cuotas con fecha programada y pagada
- `HistorialLaboral`: tipo_movimiento (ingreso, ascenso, descenso, cambio_salarial, etc.)
- `TurnoRotativo`: tipo_turno (dia, tarde, noche), hora_entrada, hora_salida, porcentaje_recargo
- `TurnoAsignacion`: fecha_asignacion, horas_trabajadas, horas_extras, estado

**Cálculos automáticos implementados:**
- Décimo Tercero: 1/12 sueldo por mes (Art. 95, pago máximo 24 diciembre)
- Décimo Cuarto: 1/12 SBU ($460/12) (Art. 97, pago: agosto Sierra / marzo Costa)
- Fondo de Reserva: 8.33% del sueldo (requiere 1+ año servicio)
- Vacaciones: 15 días por año + 1 adicional, valor = sueldo_diario × días
- Horas Extras: 25% diurnas, 50% nocturnas (22:00-06:00), 100% dominicales
- Aportes IESS: 9.35% personal, 11.15% + 0.5% riesgos + 0.2% SECAP + 0.1% CENACES = 12.95% patronal
- Utilidades: 15% para trabajadores (50% días trabajo + 50% sueldos/salarios)
- Liquidación Laboral: sueldo pendiente + décimos + vacaciones + fondo reserva
- Impuesto Renta: tabla progresiva 2024-2026 (9 tramos, 0%-35%)

**Reportes SRI:**
- RDEP XML: archivo descargable con estructura SRI para presentación anual
- Anexos IESS: aportes personales y patronales por empleado
- SUT XIII-XIV: consolidado de pagos de décimos por tipo y año
- IR Retenciones: base imponible, tasa y retención por empleado

**Exportaciones bancarias:**
- Banco Pichincha: CSV (CUENTA,BENEFICIARIO,VALOR,TIPO)
- Banco Guayaquil: TXT posicional (registro tipo 1 cabecera, tipo 2 detalles)
- Banco Pacífico: TSV/Excel (TIPO_ID | IDENTIFICACION | NOMBRE | TIPO_CUENTA | NUMERO | VALOR)

**Asistencia biométrica:**
- Registro de entrada/salida por empleado
- Importación desde dispositivos biométricos (CSV/JSON)
- Turnos rotativos con asignación individual o masiva

**Flujo integrado (1-click):** Generar rol de pago + RDEP XML + archivo banco + PDF rol

### Fase 5: Frontend ✅
- React 19 + Next.js 16 + Tailwind CSS + shadcn/ui
- Modo claro/oscuro (colores suaves que no cansan la vista)
- 3 idiomas: Español Ecuador (default), English, Português Brasil
- Dashboard interactivo con KPIs
- 20+ componentes de dominio
- Responsive (mobile-first)

### Fase 6: SMTP + Sandbox ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Perfiles SMTP** | CRUD de perfiles SMTP multi-proveedor | `models/smtp_profile.py`, `schemas/smtp_profile.py` | `POST/GET/PUT/DELETE /api/v1/smtp-profiles`, `POST /api/v1/smtp-profiles/test` |
| **Plantillas Email** | Plantillas HTML con variables dinámicas | `models/email_template.py`, `schemas/email_template.py`, `api/v1/endpoints/email_templates.py` | `POST/GET/PUT/DELETE /api/v1/email-templates`, `POST /api/v1/email-templates/preview`, `POST /api/v1/email-templates/send` |
| **Email Logs** | Tracking de envíos con reintentos | `models/email_log.py`, `schemas/email_log.py`, `api/v1/endpoints/email_logs.py` | `GET /api/v1/email-logs`, `GET /api/v1/email-logs/stats`, `POST /api/v1/email-logs/{id}/retry`, `DELETE /api/v1/email-logs/{id}` |
| **Recepción IMAP** | Recepción de correos vía IMAP/POP3 | `core/email_receiver.py`, `api/v1/endpoints/email_receiver.py` | `POST /api/v1/email-receiver/receive`, `GET /api/v1/email-receiver/status` |
| **Servicio SMTP** | Envío asíncrono con reconexión | `core/email_service.py` | - |

**Modelos de datos:**
- `SMTPProfile`: provider_type (gmail, zoho, office365, outlook, yahoo, custom), host, port, username, password (cifrado), protocol (SSL/TLS/STARTTLS), signature_id
- `EmailTemplate`: nombre, tipo (factura, nota_credito, proforma, general), asunto, cuerpo_html, cuerpo_texto, is_default, is_active
- `EmailLog`: tipo (comprobante, proforma, notificacion), destinatario_principal, estado (pendiente, enviado, fallido, reintentando, cancelado), intentos, max_intentos, respuesta_smtp, error_mensaje, comprobante_id

**Características:**
- Variables en plantillas: `{{razon_social}}`, `{{ruc}}`, `{{cliente_nombre}}`, `{{secuencial}}`, `{{total}}`, etc.
- Reintentos automáticos con backoff exponencial (max 3 intentos, configurable)
- Estadísticas de envío: tasa de éxito, breakdown por tipo, tendencia diaria
- Test de conexión SMTP antes de guardar
- Vista previa de plantillas con datos de ejemplo
- Envío de comprobantes con adjuntos (XML + RIDE PDF)

### Fase 7: Compras y Proveedores ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Órdenes de Compra** | CRUD de OC con flujo de aprobación | `models/purchase.py` (OrdenCompra, OrdenCompraDetalle), `schemas/purchase.py`, `api/v1/endpoints/purchases.py` | `POST/GET/PUT/DELETE /api/v1/purchases/ordenes` |
| **Recepción de Mercadería** | Registro de recepciones vinculadas a OC | `models/purchase.py` (RecepcionMercaderia, RecepcionMercaderiaDetalle), `schemas/purchase.py` | `POST/GET/PUT/DELETE /api/v1/purchases/recepciones` |
| **Cuentas por Pagar** | Gestión de pagos a proveedores | `models/purchase.py` (CuentaPorPagar), `schemas/purchase.py`, `api/v1/endpoints/cuentas_pagar.py` | `POST/GET/PUT/DELETE /api/v1/purchases/cuentas-por-pagar`, `POST /api/v1/purchases/cuentas-por-pagar/{id}/payment` |
| **Retenciones de Compra** | Generación automática de retenciones | `models/purchase.py` (RetencionCompra), `schemas/purchase.py` | `POST/GET/PUT/DELETE /api/v1/purchases/retenciones` |
| **Proveedores** | Catálogo de proveedores | `models/supplier.py`, `schemas/supplier.py`, `api/v1/endpoints/suppliers.py` | `POST/GET/PUT/DELETE /api/v1/suppliers` |

**Modelos de datos:**
- `OrdenCompra`: numero (OC-000001), fecha_emision, fecha_entrega_estimada, estado (borrador, enviada, parcial, recibida, anulada), subtotal_sin_impuestos, total_iva, total_con_impuestos
- `OrdenCompraDetalle`: product_id, codigo_principal, descripcion, cantidad, cantidad_recibida, precio_unitario, iva_codigo, iva_porcentaje, descuento
- `RecepcionMercaderia`: numero (RM-000001), fecha_recepcion, estado (pendiente, conformada, rechazada), orden_compra_id (opcional)
- `RecepcionMercaderiaDetalle`: product_id, cantidad_recibida, cantidad_dañada, precio_unitario
- `CuentaPorPagar`: numero_factura, fecha_emision, fecha_vencimiento, monto_total, monto_pagado, monto_pendiente, estado (pendiente, parcial, pagada, vencida), dias_credito
- `RetencionCompra`: numero_retencion (RET-000001), base_imponible_iva, retencion_iva_codigo/porcentaje/valor, base_imponible_renta, retencion_renta_codigo/porcentaje/valor

**Características:**
- Auto-numeración de órdenes de compra (OC-000001), recepciones (RM-000001), retenciones (RET-000001)
- Flujo de recepción vinculado a orden de compra (actualiza cantidad_recibida en OC)
- Cuentas por pagar con cálculo automático de fecha de vencimiento (días de crédito)
- Registro de pagos parciales con actualización de estado (pendiente → parcial → pagada)
- Retenciones de IVA y Renta con códigos SRI (Tablas 19 y 20)
- Auditoría de todas las operaciones (logs de creación, actualización, eliminación)
- Frontend: componente `contaec-purchases.tsx` con pestañas para OC, CxP, Retenciones

### Fase 8: Multi-Almacén y Logística ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Almacenes** | CRUD de almacenes/bodegas | `models/warehouse.py` (Warehouse), `schemas/warehouse.py`, `api/v1/endpoints/warehouses.py` | `POST/GET/PUT/DELETE /api/v1/warehouses` |
| **Ubicaciones Físicas** | Gestión de zona/pasillo/rack/estante/nivel | `models/warehouse.py` (WarehouseLocation), `schemas/warehouse.py`, `api/v1/endpoints/ubicaciones.py` | `POST/GET/PUT/DELETE /api/v1/ubicaciones`, `GET /api/v1/ubicaciones/map` |
| **Transferencias** | Transferencias entre almacenes | `models/warehouse.py` (WarehouseTransfer, WarehouseTransferDetalle), `schemas/warehouse.py`, `api/v1/endpoints/warehouses.py` | `POST/GET/PUT /api/v1/warehouses/transfers` |
| **Kardex Detallado** | Movimientos con saldo por almacén | `models/kardex.py`, `schemas/kardex.py`, `api/v1/endpoints/kardex.py` | `POST/GET /api/v1/kardex`, `GET /api/v1/kardex/reporte`, `GET /api/v1/kardex/saldos` |

**Modelos de datos:**
- `Warehouse`: nombre, codigo, direccion, ciudad, responsable, telefono, is_principal (solo uno por empresa)
- `WarehouseLocation`: zona, pasillo, rack, estante, nivel, codigo_ubicacion (auto-generado: A-P3-RB-E2), ubicacion_completa, capacidad_maxima, capacidad_actual, producto_id
- `WarehouseTransfer`: numero (TRANS-000001), warehouse_origen_id, warehouse_destino_id, estado (pendiente, en_transito, recibida, anulada), fecha_envio, fecha_recepcion
- `WarehouseTransferDetalle`: product_id, cantidad, cantidad_recibida, observaciones
- `Kardex`: product_id, warehouse_id, tipo_movimiento (entrada, salida, ajuste, transferencia), cantidad, costo_unitario, saldo_cantidad, saldo_valor

**Características:**
- Múltiples almacenes por empresa con uno principal
- Ubicaciones físicas con direccionamiento jerárquico (zona-pasillo-rack-estante-nivel)
- Códigos cortos de ubicación auto-generados (ej: A-P3-RB-E2)
- Control de capacidad máxima y actual por ubicación
- Transferencias con flujo de estados: pendiente → en_transito → recibida
- Kardex con saldo en tiempo real (cantidad y valor) por producto/almacén
- Reportes de kardex por fechas con métodos FIFO/LIFO/PP
- Auditoría completa de movimientos
- Frontend: componente `contaec-warehouses.tsx`

### Fase 9: Punto de Venta (POS) ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Interfaz Táctil** | Terminal POS con botones grandes | `src/components/contaec-pos.tsx` | - |
| **Escáner** | Búsqueda por código de barras | `backend/app/api/v1/endpoints/pos.py`, `src/lib/api.ts` | `GET /api/v1/pos/products/barcode/:barcode` |
| **Tickets** | Venta con impresión 80mm | `models/pos.py`, `schemas/pos.py`, `api/v1/endpoints/pos.py` | `POST/GET /api/v1/pos/tickets`, `GET /api/v1/pos/tickets/:id/print` |
| **Arqueo** | Apertura/cierre de caja | `models/pos.py`, `schemas/pos.py`, `api/v1/endpoints/pos.py` | `POST/GET /api/v1/pos/sessions`, `POST /api/v1/pos/sessions/:id/close` |
| **Facturación Rápida** | Flujo retail optimizado | `src/components/contaec-pos.tsx`, `src/lib/api.ts` | `POST /api/v1/pos/tickets` |

**Modelos de datos:**
- `POSCashSession`: numero_caja, user_id, estado (abierta, cerrada), fecha_apertura, fecha_cierre, monto_apertura, monto_cierre_efectivo, monto_cierre_calculado, monto_diferencia, total_ventas_* (por forma de pago)
- `POSTicket`: numero (TICKET-000001), session_id, warehouse_id, tipo_venta (efectivo, tarjeta, credito, mixto), subtotal, iva, total, estado (pendiente, pagado, anulado, devuelto)
- `POSTicketDetalle`: product_id, cantidad, precio_unitario, descuento, total
- `POSArqueo`: session_id, tipo (parcial, final), monto_efectivo, monto_tarjeta, monto_credito, monto_cheque, diferencia, observaciones

**Características:**
- Sesiones de caja con control de apertura/cierre
- Búsqueda de productos por código de barras (escáner)
- Múltiples formas de pago: efectivo, tarjeta, crédito, mixto
- Impresión de tickets formato 80mm (PDF)
- Arqueo de caja con conteo de denominaciones
- Cálculo automático de sobrante/faltante
- Control de stock por almacén
- Devoluciones y anulaciones
- Auditoría completa de operaciones
- Frontend: componente `contaec-pos.tsx` con interfaz táctil, carrito, búsquedas y cierre de caja

### Fase 10: Business Intelligence ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **KPIs Tiempo Real** | 16 indicadores clave | `api/v1/endpoints/bi.py`, `schemas/bi.py` | `GET /api/v1/bi/kpis` |
| **Dashboards** | Gráficos Recharts | `src/components/contaec-bi.tsx`, `schemas/bi.py` | `GET /api/v1/bi/ventas-mensuales`, `/bi/ventas-por-tipo`, `/bi/top-productos`, `/bi/top-clientes`, `/bi/flujo-efectivo` |
| **Alertas** | Stock bajo, vencimientos, cumplimiento | `api/v1/endpoints/bi.py`, `schemas/bi.py` | `GET /api/v1/bi/alertas` |
| **Cuadro de Mando** | Indicadores de cumplimiento | `api/v1/endpoints/bi.py`, `schemas/bi.py` | `GET /api/v1/bi/cuadro-mando` |
| **Exportar Power BI** | Star schema JSON | `api/v1/endpoints/bi.py`, `schemas/bi.py` | `GET /api/v1/bi/export-powerbi`, `POST /api/v1/bi/export-powerbi-file` |

**KPIs implementados:**
1. Ventas totales (mensuales, variación % vs mes anterior)
2. Comprobantes emitidos/autorizados/rechazados
3. Tasa de aprobación SRI (%)
4. Ticket promedio
5. IVA recaudado
6. Clientes activos/nuevos
7. Productos más vendidos
8. Ventas por tipo de comprobante
9. Flujo de efectivo mensual
10. Cuentas por cobrar (total, vencidas, próximas)
11. Cuentas por pagar (total, vencidas, próximas)
12. Stock de productos
13. Órdenes de compra pendientes
14. Empleados activos
15. Roles de pago procesados
16. Tickets POS (cantidad, total)

**Alertas inteligentes:**
- Stock bajo (productos con stock < mínimo)
- Cuentas por cobrar vencidas
- Cuentas por pagar próximas a vencer
- Comprobantes rechazados SRI
- Sesiones POS con diferencias de efectivo
- Licencias por expirar
- Respaldos pendientes
- Productos sin movimiento

**Exportación Power BI:**
- FactVentaRow: tabla de hechos de ventas
- FactInventarioRow: tabla de hechos de inventario
- DimProducto: dimensión de productos
- DimCliente: dimensión de clientes
- DimTiempo: dimensión temporal
- Formato star schema listo para importar

**Frontend:** `contaec-bi.tsx` con gráficos de barras, líneas, tortas y tablas de KPIs

### Fase 11: Presupuestos ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Presupuesto Anual** | CRUD de presupuestos por ejercicio fiscal | `models/budget.py`, `schemas/budget.py`, `api/v1/endpoints/budgets.py` | `POST/GET/PUT/DELETE /api/v1/budgets` |
| **Cuentas Presupuestarias** | Presupuesto por cuenta contable (ingreso/egreso) | `models/budget.py`, `schemas/budget.py`, `api/v1/endpoints/budgets.py` | `POST/GET/PUT/DELETE /api/v1/budgets/cuentas` |
| **Ejecución Mensual** | Registro de ejecución presupuestaria mensual | `models/budget.py`, `schemas/budget.py`, `api/v1/endpoints/budgets.py` | `POST/GET/PUT /api/v1/budgets/ejecuciones` |
| **Alertas de Sobregiro** | Notificaciones automáticas por阈值 | `models/budget.py`, `api/v1/endpoints/budgets.py` | `GET /api/v1/budgets/alertas`, `GET /api/v1/budgets/alertas/summary` |
| **Comparativo** | Presupuestado vs real | `api/v1/endpoints/budgets.py`, `schemas/budget.py` | `GET /api/v1/budgets/comparativo`, `GET /api/v1/budgets/stats` |

**Modelos de datos:**
- `PresupuestoAnual`: anio, nombre, descripcion, estado (borrador, aprobado, cerrado, anulado), total_ingresos_presupuestado, total_egresos_presupuestado, total_ingresos_ejecutado, total_egresos_ejecutado
- `PresupuestoCuenta`: cuenta_codigo, cuenta_nombre, cuenta_tipo (ingreso/egreso), monto_anual, monto_ejecutado, monto_disponible, porcentaje_ejecucion
- `PresupuestoEjecucionMensual`: mes, monto_ejecutado, observaciones
- `PresupuestoAlerta`: tipo_alerta (50_porciento, 75_porciento, 90_porciento, sobregiro), mensaje, monto_presupuestado, monto_ejecutado, monto_sobregiro, porcentaje_ejecucion, is_leida, is_resuelta

**Características:**
- Presupuestos anuales por ejercicio fiscal con estado (borrador → aprobado → cerrado)
- Cuentas presupuestarias por tipo: ingreso y egreso
- Ejecución mensual con registro de montos ejecutados
- Cálculo automático de porcentaje de ejecución
- Alertas automáticas porthresholds: 50%, 75%, 90%, sobregiro (>100%)
- Alertas marcables como leídas/resueltas
- Recálculo automático de totales (cuenta → presupuesto anual)
- Comparativo presupuestado vs ejecutado
- Exportación de presupuestos (JSON/Excel)
- Auditoría completa de operaciones
- Frontend: componente `contaec-budgets.tsx`

### Fase 12: CRM ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Pipeline Ventas** | Pipeline visual con etapas personalizables | `models/crm.py`, `schemas/crm.py`, `api/v1/endpoints/crm.py` | `POST/GET/PUT/DELETE /api/v1/crm/pipelines`, `POST/GET/PUT/DELETE /api/v1/crm/pipelines/:id/stages` |
| **Leads** | Gestión de leads (nuevo→ganado/perdido) | `models/crm.py`, `schemas/crm.py`, `api/v1/endpoints/crm.py` | `POST/GET/PUT/DELETE /api/v1/crm/leads` |
| **Oportunidades** | Oportunidades con monto, probabilidad | `models/crm.py`, `schemas/crm.py`, `api/v1/endpoints/crm.py` | `POST/GET/PUT/DELETE /api/v1/crm/opportunities`, `PUT /api/v1/crm/opportunities/:id/stage` |
| **Actividades** | Llamada/email/reunión/tarea/nota | `models/crm.py`, `schemas/crm.py`, `api/v1/endpoints/crm.py` | `POST/GET/PUT/DELETE /api/v1/crm/activities` |
| **Segmentación** | Segmentos manual/regla/RFM | `models/crm.py`, `schemas/crm.py`, `api/v1/endpoints/crm.py` | `POST/GET/PUT/DELETE /api/v1/crm/segments` |
| **Automatización** | Triggers + actions | `models/crm.py`, `schemas/crm.py`, `api/v1/endpoints/crm.py` | `POST/GET/PUT/DELETE /api/v1/crm/automations` |

**Modelos de datos:**
- `CRMPipeline`: name, description, is_default, order (flujo de ventas de la empresa)
- `CRMPipelineStage`: pipeline_id, name, order, probability_percentage, color (etapas del pipeline)
- `CRMLead`: company_id, name, source (website, referral, social, ad, event), status (nuevo, contactado, cualificado, propuesta, negociacion, ganado, perdido), email, phone, converted_to_client_id
- `CRMOpportunity`: lead_id, stage_id, name, description, estimated_amount, probability, close_date, status (abierta, ganada, perdida), client_id
- `CRMActivity`: opportunity_id, lead_id, type (llamada, email, reunion, tarea, nota), status (pendiente, completada, cancelada), scheduled_at, completed_at, description
- `CRMContactSegment`: name, description, type (manual, regla, rfm), filter_config (JSON para segmentos dinámicos)
- `CRMContactSegmentMember`: segment_id, client_id (miembros de segmentos)
- `CRMAutomation`: name, trigger_type (lead_creado, oportunidad_ganada, oportunidad_perdida, stage_changed), trigger_config, actions (JSON)

**Características:**
- Múltiples pipelines de ventas por empresa
- Etapas personalizables con probabilidad de closure
- Leads con seguimiento de fuente y estado
- Conversión de lead a cliente
- Oportunidades con monto estimado y probabilidad de cierre
- Cálculo de pipeline value y weighted pipeline
- Actividades vinculadas a leads y oportunidades
- Segmentación de clientes (manual, por regla, RFM)
- Automatizaciones con triggers y acciones
- Estadísticas CRM: total leads/oportunidades, tasa de conversión, pipeline value
- Frontend: componente `contaec-crm.tsx` con vista Kanban del pipeline

### Fase 13: Proyectos y Servicios ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Proyectos** | CRUD de proyectos con seguimiento | `models/project.py` (Proyecto), `schemas/project.py`, `api/v1/endpoints/projects.py` | `POST/GET/PUT/DELETE /api/v1/projects` |
| **Tareas** | Tareas con prioridad y estado | `models/project.py` (ProyectoTarea), `schemas/project.py`, `api/v1/endpoints/projects.py` | `POST/GET/PUT/DELETE /api/v1/projects/:id/tareas` |
| **Recursos** | Recursos humanos/materiales/equipo | `models/project.py` (ProyectoRecurso), `schemas/project.py`, `api/v1/endpoints/projects.py` | `POST/GET/PUT/DELETE /api/v1/projects/:id/recursos` |
| **Timesheets** | Registro de horas trabajadas | `models/project.py` (ProyectoTimesheet), `schemas/project.py`, `api/v1/endpoints/projects.py` | `POST/GET/PUT/DELETE /api/v1/projects/:id/timesheets` |
| **Costos** | Costos adicionales de proyecto | `models/project.py` (ProyectoCosto), `schemas/project.py`, `api/v1/endpoints/projects.py` | `POST/GET/PUT/DELETE /api/v1/projects/:id/costos` |
| **Rentabilidad** | Cálculo automático de márgenes | `api/v1/endpoints/projects.py`, `schemas/project.py` | `GET /api/v1/projects/stats`, `POST /api/v1/projects/:id/recalcular` |

**Modelos de datos:**
- `Proyecto`: codigo (PRY-001), nombre, descripcion, cliente_id, cliente_nombre, estado (planificacion, en_progreso, en_pausa, completado, cancelado), fecha_inicio, fecha_fin_estimada, fecha_fin_real, presupuesto, costo_real, ingreso, margen, margen_porcentaje, progreso, responsable
- `ProyectoTarea`: proyecto_id, nombre, descripcion, estado (pendiente, en_progreso, completada, cancelada), prioridad (baja, media, alta, critica), fecha_inicio, fecha_fin_estimada, fecha_fin_real, asignado_a, progreso
- `ProyectoRecurso`: proyecto_id, tipo (humano, material, equipo), nombre, descripcion, costo_unitario, cantidad, costo_total
- `ProyectoTimesheet`: proyecto_id, tarea_id, user_id, recurso_id, horas_trabajadas, tarifa_hora, costo_total, facturable, fecha_trabajo, descripcion
- `ProyectoCosto`: proyecto_id, concepto, descripcion, monto, fecha_costo, tipo (material, servicio, otro)

**Características:**
- Gestión de proyectos con código auto-generado (PRY-001)
- Estados del proyecto: planificación → en progreso → en pausa → completado/cancelado
- Tareas con prioridad (baja, media, alta, crítica) y estado
- Recursos humanos, materiales y equipos con costo unitario y cantidad
- Timesheets con horas trabajadas, tarifa/hora, costo total, facturable/no facturable
- Costos adicionales por concepto (materiales, servicios, otros)
- Cálculo automático de rentabilidad: ingreso - costo_real = margen
- Progreso porcentual del proyecto
- Recálculo automático de márgenes al modificar costos/ingresos
- Estadísticas de proyectos por estado, cliente, responsable
- Frontend: componente `contaec-projects.tsx` con gestión completa de proyectos, tareas, recursos, timesheets y costos

### Fase 12: Integraciones ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Cuentas Bancarias** | CRUD de cuentas bancarias de la empresa | `models/integration.py` (CuentaBancaria), `schemas/integration.py`, `api/v1/endpoints/integrations.py` | `POST/GET/PUT/DELETE /api/v1/integrations/bank/accounts` |
| **Extractos Bancarios** | Importación de extractos por periodo | `models/integration.py` (ExtractoBancario), `schemas/integration.py`, `api/v1/endpoints/integrations.py` | `POST/GET/DELETE /api/v1/integrations/bank/statements` |
| **Movimientos Bancarios** | Movimientos con conciliación | `models/integration.py` (MovimientoBancario), `schemas/integration.py`, `api/v1/endpoints/integrations.py` | `POST/GET/PUT/DELETE /api/v1/integrations/bank/movements`, `POST /api/v1/integrations/bank/import-csv` |
| **Conciliación** | Conciliación manual/automática | `api/v1/endpoints/integrations.py`, `schemas/integration.py` | `PUT /api/v1/integrations/bank/movements/{id}` |
| **E-Commerce** | Conectores Shopify, WooCommerce, etc. | `models/integration.py` (EcommerceConnector), `schemas/integration.py`, `api/v1/endpoints/integrations.py` | `POST/GET/PUT/DELETE /api/v1/integrations/ecommerce/connectors` |
| **Sincronización** | Sync productos, órdenes, clientes, inventario | `models/integration.py` (EcommerceSyncLog), `api/v1/endpoints/integrations.py` | `POST /api/v1/integrations/ecommerce/{id}/sync`, `POST /api/v1/integrations/ecommerce/{id}/sync-products`, `/sync-orders`, `/sync-inventory`, `GET /api/v1/integrations/ecommerce/sync-logs` |

**Modelos de datos:**
- `CuentaBancaria`: nombre_banco, codigo_banco, tipo_cuenta (ahorros/corriente), numero_cuenta, iban, swift_bic, titular, moneda, saldo_inicial, saldo_actual, formato_extracto (csv/ofx/mt940/excel), configuracion_mapeo (JSON)
- `ExtractoBancario`: cuenta_bancaria_id, fecha_desde, fecha_hasta, saldo_inicial, saldo_final, total_debitos, total_creditos, numero_movimientos, movimientos_conciliados, estado (importado, en_conciliacion, conciliado, con_error), archivo_original
- `MovimientoBancario`: cuenta_bancaria_id, extracto_id, fecha, tipo (debito/credito), monto, saldo_posterior, referencia, descripcion, beneficiario, documento, conciliacion_estado (pendiente/conciliado/ignorado), conciliacion_fecha, comprobante_id, conciliacion_nota, categoria
- `EcommerceConnector`: plataforma (shopify/woocommerce/opencart/prestashop/magento/meli/otro), url_tienda, api_key, api_secret, access_token, refresh_token, webhook_url, configuracion_extra (JSON), estado (configurado/conectado/sincronizando/error/desactivado), sincronizacion_auto, frecuencia_sync, sync_productos, sync_ordenes, sync_clientes, sync_inventario
- `EcommerceSyncLog`: connector_id, tipo_sync (productos/ordenes/clientes/inventario/completo), estado (pendiente/en_progreso/completada/con_error), fecha_inicio, fecha_fin, registros_procesados/creados/actualizados/errores, detalle_errores (JSON), resultado_resumen (JSON)

**Características:**
- Múltiples cuentas bancarias por empresa con saldos inicial/actual
- Importación de extractos bancarios en formatos CSV, OFX, MT940, Excel
- Configuración de mapeo de columnas para extractos personalizados
- Movimientos bancários con clasificación (débito/crédito) y categorías auto-detectadas
- Conciliación bancaria manual y automática (vinculación con comprobantes)
- Estados de conciliación: pendiente → conciliado/ignorado
- Detección automática de categorías por descripción del movimiento
- Conectores e-commerce multi-plataforma (6 plataformas + genérico)
- Sincronización selectiva: productos, órdenes, clientes, inventario
- Sincronización automática con frecuencia configurable (en minutos)
- Logs de sincronización con métricas detalladas (procesados, creados, actualizados, errores)
- Test de conexión antes de guardar conector
- Estadísticas de uso: total cuentas, extractos pendientes, movimientos por conciliar, sync logs
- Frontend: componente `contaec-integrations.tsx` con pestañas para bancos y e-commerce

### Fase 13: Machine Learning / IA ✅ IMPLEMENTADA

| Componente | Descripción | Archivos | Endpoints |
|------------|-------------|----------|-----------|
| **Predicciones** | Predicción de ventas, ingresos, gastos, flujo de caja | `models/ml_ai.py` (MLPrediccion), `schemas/ml_ai.py`, `api/v1/endpoints/ml_ai.py` | `POST/GET/DELETE /api/v1/ml/predictions`, `GET /api/v1/ml/stats` |
| **Detección de Fraude** | Alertas de fraude con scoring y severidad | `models/ml_ai.py` (MLAlertaFraude), `schemas/ml_ai.py`, `api/v1/endpoints/ml_ai.py` | `POST /api/v1/ml/fraud/scan`, `GET/PUT /api/v1/ml/fraud/alerts` |
| **Chatbot** | Sesiones de chat, mensajes, reglas | `models/ml_ai.py` (MLChatbotSesion, MLChatbotMensaje), `schemas/ml_ai.py`, `api/v1/endpoints/ml_ai.py` | `POST/GET/DELETE /api/v1/ml/chatbot/sessions`, `POST /api/v1/ml/chatbot/chat`, `GET /api/v1/ml/chatbot/sessions/{id}/messages` |
| **Recomendaciones** | Recomendaciones de producto, cliente, precio, inventario, financiera | `models/ml_ai.py` (MLRecomendacion), `schemas/ml_ai.py`, `api/v1/endpoints/ml_ai.py` | `GET /api/v1/ml/recommendations`, `POST /api/v1/ml/recommendations/generate`, `PUT/DELETE /api/v1/ml/recommendations/{id}` |
| **Auto-categorización** | Reglas de categorización por keywords/regex | `models/ml_ai.py` (MLCategoriaRegla), `schemas/ml_ai.py`, `api/v1/endpoints/ml_ai.py` | `GET/POST/PUT/DELETE /api/v1/ml/categorize/rules`, `POST /api/v1/ml/categorize/categorize` |

**Modelos de datos:**
- `MLPrediccion`: tipo (ventas/ingresos/gastos/flujo_caja), estado (pendiente/completada/con_error), periodo_desde, periodo_hasta, datos_entrada (JSON), resultado (JSON), metricas (JSON con MAPE, RMSE, R2), modelo_usado (moving_average/exponential_smoothing/linear_regression/arima), confianza (0-100%)
- `MLAlertaFraude`: tipo_alerta (z-score/duplicado/secuencia_anomala/validacion_ruc), severidad (baja/media/alta/critica), estado (pendiente/confirmado/descartado/investigando), puntuacion_fraude (0-100), evidencia (JSON), comprobante_id, descripcion
- `MLChatbotSesion`: user_id, estado (activa/cerrada), mensaje_count, ultimo_mensaje_at
- `MLChatbotMensaje`: session_id, role (user/assistant/system), content, model_used, tokens_used, latency_ms
- `MLRecomendacion`: tipo (producto/cliente/precio/inventario/financiera), descripcion, prioridad (alta/media/baja), estado (pendiente/aplicada/descartada), impacto_esperado (JSON), metadata (JSON)
- `MLCategoriaRegla`: nombre, categoria_destino, keywords (lista), patrones_regex (lista), is_active, use_count

**Características:**
- Predicciones con múltiples modelos: Moving Average, Exponential Smoothing, Linear Regression, ARIMA
- Métricas de desempeño: MAPE (Mean Absolute Percentage Error), RMSE (Root Mean Square Error), R²
- Nivel de confianza de predicción (0-100%)
- Detección de fraude con 4 métodos: Z-score, duplicados, secuencia anómala, validación RUC
- Alertas de fraude con severidad clasificada y estado de investigación
- Chatbot híbrido: reglas + LLM (vía z-ai CLI)
- Sesiones de chat con tracking de mensajes, tokens y latencia
- Recomendaciones accionables con prioridad e impacto esperado
- Auto-categorización con reglas personalizables (keywords + regex)
- Contador de uso de reglas para optimización
- Estadísticas ML: total predicciones, alertas, sesiones chat, recomendaciones
- Frontend: componente `contaec-ml-ai.tsx`

---

## Variables de Entorno (.env)

El archivo `.env` va en `/opt/contaec/backend/.env`. Todas las variables se cargan con `pydantic-settings`.

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `APP_ENV` | Sí | `development` | `development` o `production` |
| `SECRET_KEY` | Sí (prod) | dev-default | Clave secreta de la aplicación |
| `ENCRYPTION_KEY` | Sí (prod) | dev-default | Clave de cifrado Fernet para datos sensibles |
| `JWT_SECRET_KEY` | Sí (prod) | dev-default | Clave para firmar tokens JWT |
| `DATABASE_URL` | Sí (prod) | SQLite local | URL de conexión a PostgreSQL |
| `POSTGRES_USER` | Sí (prod) | `contaec_user` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | Sí (prod) | vacío | Password PostgreSQL |
| `POSTGRES_HOST` | No | `localhost` | Host PostgreSQL |
| `POSTGRES_PORT` | No | `5432` | Puerto PostgreSQL |
| `POSTGRES_DB` | No | `contaec_db` | Nombre de la BD |
| `ADMIN_EMAIL` | No | `steve.mejia@tymtechnology.shop` | Email del administrador |
| `ADMIN_PASSWORD` | Sí | `Vitaestcum21..` | Password del administrador |
| `BACKUP_ENCRYPTION_KEY` | Recomendado | vacío | Clave Fernet para cifrar respaldos |
| `CLAMAV_ENABLED` | No | `false` | Activar escaneo ClamAV |
| `CLAMAV_SOCKET` | No | `/var/run/clamav/clamd.ctl` | Socket Unix de ClamAV |
| `VIRUSTOTAL_ENABLED` | No | `false` | Activar escaneo VirusTotal |
| `VIRUSTOTAL_API_KEY` | Si VT | vacío | API key de VirusTotal |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Orígenes CORS (separados por coma) |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Requests por minuto por IP |

**⚠️ IMPORTANTE:** En producción, `APP_ENV=production` bloquea SQLite y valida que las claves secretas no tengan valores por defecto.

---

## Administración

### Acceso al Panel Admin

- **URL:** `https://conta.tymtechnology.shop` → Iniciar sesión con credenciales admin
- **Email:** `steve.mejia@tymtechnology.shop`
- **Password:** `Vitaestcum21..`

### Funciones del Panel Admin

1. **Dashboard General** - Resumen de usuarios, licencias, estado del sistema
2. **Salud del Sistema** - CPU, RAM, disco, conexiones BD, uptime
3. **Gestión de Usuarios** - Listar, activar/desactivar, modificar licencias
4. **Problemas de Seguridad** - Alertas de seguridad por usuario

### Sistema de Licencias

| Plan | Duración | Código |
|------|----------|--------|
| Mensual | 30 días | `MENSUAL` |
| Trimestral | 90 días | `TRIMESTRAL` |
| Semestral | 180 días | `SEMESTRAL` |
| Anual | 365 días | `ANUAL` |

Cada tier tiene límites de funcionalidades: empresas, usuarios, comprobantes, empleados, productos.

---

## Respaldo y Restauración

### Respaldo Automático

El sistema realiza un respaldo automático a medianoche (hora Ecuador) de todos los usuarios activos que tienen clave de backup configurada. Los respaldos:

- Se cifran con Fernet usando la clave del usuario
- Se almacenan en `/opt/contaec/backend/backups/`
- Se eliminan automáticamente después de 30 días
- Formato: `backup_{email}_{fecha}.contaec`

### Respaldo Manual

Desde la interfaz: **Configuración → Respaldo → Crear Respaldo**

### Restauración

1. Subir el archivo `.contaec`
2. Ingresar la clave de cifrado
3. El sistema restaura: empresas (por RUC), clientes (por identificación), productos (por código)

---

## Seguridad

### Medidas Implementadas

| Medida | Implementación |
|--------|---------------|
| Autenticación | JWT + bcrypt + refresh token rotation |
| Revocación de tokens | Blacklist in-memory con JTI + cleanup automático |
| Detección de replay | Rotación de refresh tokens con revocación en cadena |
| Cifrado de datos sensibles | Fernet (AES-128) para firmas, passwords SMTP, configs |
| Sanitización | SQL injection + XSS + path traversal en middleware |
| Rate limiting | 60 req/min por IP (configurable) |
| Headers seguridad | CSP, X-Frame-Options, X-XSS-Protection, HSTS |
| Antivirus | ClamAV (default) + VirusTotal (opcional) |
| Configuración por usuario | Cada usuario tiene su propia config cifrada (no .env compartido) |
| Claves no expuestas | Todos los secrets en .env, validación en producción |
| SQLite bloqueado en prod | RuntimeError si se intenta usar SQLite en producción |

### Permisos de Archivos

```bash
# Proteger el archivo .env
chmod 600 /opt/contaec/backend/.env
chown www-data:www-data /opt/contaec/backend/.env

# Proteger directorio de backups
chmod 700 /opt/contaec/backend/backups
chown www-data:www-data /opt/contaec/backend/backups

# Proteger directorio de uploads
chmod 755 /opt/contaec/backend/uploads
chown www-data:www-data /opt/contaec/backend/uploads

# Proteger firmas digitales
chmod 700 /opt/contaec/backend/signatures
chown www-data:www-data /opt/contaec/backend/signatures
```

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
