// ContaEC Backend Process Manager
// Manages the FastAPI backend as a child process from Next.js

import { ChildProcess, spawn } from 'child_process';
import { NextRequest, NextResponse } from 'next/server';
import path from 'path';

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;

// Global reference to keep the backend alive
let backendProcess: ChildProcess | null = null;
let isStarting = false;
let startPromise: Promise<boolean> | null = null;
let backendReady = false;

// Resolve backend directory relative to project root
const backendDir = path.resolve(process.cwd(), 'backend');

// Cross-platform Python detection
function resolvePythonPath(): string {
  if (process.env.CONTAEC_PYTHON_PATH) return process.env.CONTAEC_PYTHON_PATH;
  // On Windows use 'python', on Unix use 'python3'
  return process.platform === 'win32' ? 'python' : 'python3';
}

const pythonPath = resolvePythonPath();

async function checkBackendHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/health`, {
      signal: AbortSignal.timeout(5000), // 5s to avoid false negatives under load
    });
    return resp.ok;
  } catch {
    return false;
  }
}

async function startBackend(): Promise<boolean> {
  if (backendProcess) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }

  return new Promise<boolean>((resolve) => {
    try {
      console.log('[ContaEC Proxy] Starting backend...');
      console.log(`[ContaEC Proxy] Backend dir: ${backendDir}`);
      console.log(`[ContaEC Proxy] Python: ${pythonPath}`);

      const proc = spawn(pythonPath, [
        '-m', 'uvicorn', 'main:app',
        '--host', '0.0.0.0',
        '--port', String(BACKEND_PORT),
      ], {
        cwd: backendDir,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
        },
      });

      backendProcess = proc;
      let resolved = false;

      const doResolve = (val: boolean) => {
        if (!resolved) {
          resolved = true;
          isStarting = false;
          backendReady = val;
          resolve(val);
        }
      };

      proc.stdout?.on('data', (data: Buffer) => {
        const msg = data.toString();
        process.stdout.write(`[backend:out] ${msg}`);
        if (!resolved && (msg.includes('Application startup complete') || msg.includes('Uvicorn running'))) {
          console.log('[ContaEC Proxy] Backend started successfully');
          doResolve(true);
        }
      });

      proc.stderr?.on('data', (data: Buffer) => {
        const msg = data.toString();
        process.stderr.write(`[backend:err] ${msg}`);
        if (!resolved && (msg.includes('Application startup complete') || msg.includes('Uvicorn running'))) {
          console.log('[ContaEC Proxy] Backend started successfully (stderr)');
          doResolve(true);
        }
      });

      proc.on('exit', (code) => {
        console.log(`[ContaEC Proxy] Backend exited with code ${code}`);
        backendProcess = null;
        isStarting = false;
        backendReady = false;
        doResolve(false);
      });

      proc.on('error', (err) => {
        console.error(`[ContaEC Proxy] Backend spawn error: ${err.message}`);
        backendProcess = null;
        isStarting = false;
        doResolve(false);
      });

      // Timeout
      setTimeout(() => {
        if (!resolved) {
          console.log('[ContaEC Proxy] Backend start timeout');
          doResolve(false);
        }
      }, 20000);

    } catch (err) {
      console.error('[ContaEC Proxy] Failed to start backend:', err);
      isStarting = false;
      resolve(false);
    }
  });
}

async function ensureBackend(): Promise<boolean> {
  // Quick check if already running
  if (backendReady) {
    const healthy = await checkBackendHealth();
    if (healthy) return true;
    backendReady = false;
  }

  // If starting, wait
  if (isStarting && startPromise) {
    return startPromise;
  }

  isStarting = true;
  startPromise = startBackend();
  return startPromise;
}

async function proxyRequest(request: NextRequest, method: string) {
  const backendOk = await ensureBackend();
  if (!backendOk) {
    return NextResponse.json(
      { detail: 'No se pudo iniciar el servidor backend. Intente de nuevo.' },
      { status: 503 }
    );
  }

  try {
    const url = new URL(request.url);
    const reqPath = url.pathname.replace(/^\/api/, '');
    const backendUrl = `${BACKEND_URL}/api${reqPath}${url.search}`;

    const headers: Record<string, string> = {};
    request.headers.forEach((value, key) => {
      if (!['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) {
        headers[key] = value;
      }
    });

    const config: RequestInit = { method, headers };

    if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
      const contentType = request.headers.get('content-type') || '';
      if (contentType.includes('multipart/form-data')) {
        config.body = await request.arrayBuffer();
        // Keep content-type header for multipart (FastAPI needs boundary)
      } else {
        // Use arrayBuffer for all body types - handles JSON, text, and binary uniformly
        config.body = await request.arrayBuffer();
      }
    }

    const response = await fetch(backendUrl, {
      ...config,
      redirect: 'follow',
      signal: AbortSignal.timeout(120000), // 2 min for file uploads, PDF gen, bulk ops
    });

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (!['transfer-encoding', 'connection'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await response.json();
      return NextResponse.json(data, {
        status: response.status,
        headers: responseHeaders,
      });
    } else if (contentType.includes('application/pdf') || contentType.includes('application/octet-stream')) {
      const buffer = await response.arrayBuffer();
      return new NextResponse(buffer, {
        status: response.status,
        headers: responseHeaders,
      });
    } else {
      const text = await response.text();
      return new NextResponse(text, {
        status: response.status,
        headers: responseHeaders,
      });
    }
  } catch (error) {
    console.error('[ContaEC Proxy] Request error:', error);
    // Don't mark backend as unhealthy on transient errors (network glitch, timeout)
    // Only restart if the backend is actually unreachable
    if (error instanceof Error && error.name === 'AbortError') {
      console.warn('[ContaEC Proxy] Request timed out - backend may be under heavy load');
    }
    return NextResponse.json(
      { detail: 'Error de conexion con el servidor backend' },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest) {
  return proxyRequest(request, 'GET');
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, 'POST');
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request, 'PUT');
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request, 'DELETE');
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request, 'PATCH');
}
