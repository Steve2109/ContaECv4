"""
ContaEC - Módulo de escaneo de malware
ClamAV (escaneo local vía clamd) + VirusTotal (escaneo en la nube, opcional)
Soporta degradación graceful cuando los servicios no están disponibles

NOTA: Las operaciones síncronas (pyclamd) se ejecutan en un executor
para no bloquear el event loop de asyncio.
"""
import asyncio
import logging
import tempfile
import os
from functools import partial
from typing import Optional

import aiofiles

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScanResult:
    """Resultado del escaneo de malware"""
    def __init__(
        self,
        is_clean: bool,
        scanner: str = "none",
        threat: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.is_clean = is_clean
        self.scanner = scanner
        self.threat = threat
        self.details = details

    def to_dict(self) -> dict:
        return {
            "is_clean": self.is_clean,
            "scanner": self.scanner,
            "threat": self.threat,
            "details": self.details,
        }


class ClamAVScanner:
    """
    Escáner ClamAV vía clamd (demonio local).
    
    Soporta dos modos de conexión:
    - Unix socket (predeterminado): /var/run/clamav/clamd.ctl
    - TCP: host:port (127.0.0.1:3310)
    
    Si ClamAV no está disponible, devuelve un resultado "limpio"
    con una advertencia en los logs.
    """

    def __init__(self):
        self._available: Optional[bool] = None
        self._cd = None

    def _try_connect(self) -> bool:
        """Intenta conectar al demonio ClamAV.

        Usa el protocolo clamd directamente (PING/PONG sobre el socket Unix o TCP)
        para que la detección no dependa de que pyclamd esté instalado o sea
        compatible con la versión de ClamAV del servidor.
        """
        if self._available is not None:
            return self._available

        import socket

        def _ping(sock) -> bool:
            sock.settimeout(3.0)
            sock.sendall(b"PING\n")
            data = sock.recv(16)
            return data.strip() == b"PONG"

        connected = False
        # 1. Unix socket
        try:
            sock_path = settings.CLAMAV_SOCKET
            if sock_path and os.path.exists(sock_path):
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(sock_path)
                if _ping(s):
                    connected = True
                    logger.info("ClamAV conectado vía Unix socket")
                s.close()
        except Exception:
            pass

        # 2. TCP
        if not connected:
            try:
                s = socket.create_connection(
                    (settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=3.0
                )
                if _ping(s):
                    connected = True
                    logger.info("ClamAV conectado vía TCP")
                s.close()
            except Exception:
                pass

        if not connected:
            self._available = False
            logger.warning(
                "ClamAV no disponible. Los archivos NO serán escaneados localmente. "
                "Instale y configure ClamAV para protección completa."
            )
            return False

        # Intentar usar pyclamd para escaneos rápidos; si no está disponible,
        # el escaneo usará el protocolo INSTREAM directamente (más abajo).
        self._available = True
        try:
            import pyclamd
            cd = None
            try:
                cd = pyclamd.ClamdUnixSocket(path=settings.CLAMAV_SOCKET)
                cd.ping()
            except Exception:
                cd = None
            if cd is None:
                try:
                    cd = pyclamd.ClamdNetworkSocket(
                        host=settings.CLAMAV_HOST, port=settings.CLAMAV_PORT
                    )
                    cd.ping()
                except Exception:
                    cd = None
            self._cd = cd
        except ImportError:
            self._cd = None
            logger.info("pyclamd no instalado: se usará el protocolo INSTREAM directo")

        return True

    def _scan_stream_raw(self, content: bytes) -> ScanResult:
        """
        Escaneo con clamd usando el comando INSTREAM por socket (sin pyclamd).
        """
        import socket

        sock = None
        try:
            # Conectar (misma lógica que _try_connect)
            sock_path = settings.CLAMAV_SOCKET
            if sock_path and os.path.exists(sock_path):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(sock_path)
            else:
                sock = socket.create_connection(
                    (settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=5.0
                )
            sock.settimeout(30.0)
            sock.sendall(b"zINSTREAM\0")

            chunk_size = 8192
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                sock.sendall(len(chunk).to_bytes(4, "big") + chunk)
            sock.sendall(b"\0\0\0\0")

            # Leer respuesta
            data = b""
            while True:
                try:
                    part = sock.recv(4096)
                except socket.timeout:
                    break
                if not part:
                    break
                data += part
                if len(part) < 4096:
                    break

            respuesta = data.decode("utf-8", "replace").strip()
            if "FOUND" in respuesta:
                threat = respuesta.split(":")[-1].strip().replace(" FOUND", "")
                threat = threat or "desconocido"
                logger.warning(f"⚠️ MALWARE DETECTADO por ClamAV: {threat}")
                return ScanResult(
                    is_clean=False,
                    scanner="clamav",
                    threat=threat,
                    details=f"Amenaza detectada: {threat}",
                )
            if "ERROR" in respuesta:
                logger.warning(f"ClamAV respondió ERROR: {respuesta}")
                return ScanResult(
                    is_clean=True,
                    scanner="clamav",
                    details=f"ClamAV error: {respuesta}",
                )
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details="Archivo limpio (clamd)",
            )
        except Exception as e:
            logger.error(f"Error escaneando stream con ClamAV: {e}")
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details=f"Error en escaneo: {str(e)}",
            )
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _scan_file_sync(self, file_path: str) -> ScanResult:
        """Escaneo síncrono de archivo con ClamAV (para ejecutar en executor)."""
        if not self._try_connect():
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details="ClamAV no disponible - escaneo omitido",
            )

        if self._cd is not None:
            try:
                result = self._cd.scan_file(file_path)

                if result is None:
                    return ScanResult(
                        is_clean=True,
                        scanner="clamav",
                        details="Archivo limpio",
                    )

                for filename, (status, threat_name) in result.items():
                    if status == "FOUND":
                        logger.warning(
                            f"⚠️ MALWARE DETECTADO por ClamAV: {threat_name} en {filename}"
                        )
                        return ScanResult(
                            is_clean=False,
                            scanner="clamav",
                            threat=threat_name,
                            details=f"Amenaza detectada: {threat_name}",
                        )

                return ScanResult(
                    is_clean=True,
                    scanner="clamav",
                    details="Archivo limpio",
                )
            except Exception as e:
                logger.error(f"Error escaneando con ClamAV: {e}")
                return ScanResult(
                    is_clean=True,  # No bloquear si falla el escáner
                    scanner="clamav",
                    details=f"Error en escaneo: {str(e)}",
                )

        # Fallback: protocolo INSTREAM directo
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return self._scan_stream_raw(content)
        except Exception as e:
            logger.error(f"Error leyendo archivo para ClamAV: {e}")
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details=f"Error en escaneo: {str(e)}",
            )

    async def scan_file(self, file_path: str) -> ScanResult:
        """
        Escanea un archivo con ClamAV.
        Ejecuta el escaneo en un executor para no bloquear el event loop.
        """
        if not settings.CLAMAV_ENABLED:
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details="ClamAV deshabilitado en configuración",
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(self._scan_file_sync, file_path)
        )

    def _scan_bytes_sync(self, content: bytes) -> ScanResult:
        """Escaneo síncrono de bytes con ClamAV (para ejecutar en executor)."""
        if not self._try_connect():
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details="ClamAV no disponible - escaneo omitido",
            )

        if self._cd is not None:
            try:
                result = self._cd.scan_stream(content)

                if result is None:
                    return ScanResult(
                        is_clean=True,
                        scanner="clamav",
                        details="Archivo limpio",
                    )

                for stream, (status, threat_name) in result.items():
                    if status == "FOUND":
                        logger.warning(
                            f"⚠️ MALWARE DETECTADO por ClamAV (stream): {threat_name}"
                        )
                        return ScanResult(
                            is_clean=False,
                            scanner="clamav",
                            threat=threat_name,
                            details=f"Amenaza detectada: {threat_name}",
                        )

                return ScanResult(
                    is_clean=True,
                    scanner="clamav",
                    details="Archivo limpio",
                )

            except Exception as e:
                logger.error(f"Error escaneando stream con ClamAV: {e}")
                return ScanResult(
                    is_clean=True,
                    scanner="clamav",
                    details=f"Error en escaneo: {str(e)}",
                )

        # Fallback: protocolo INSTREAM directo
        return self._scan_stream_raw(content)

    async def scan_bytes(self, content: bytes) -> ScanResult:
        """
        Escanea contenido en memoria con ClamAV.
        Ejecuta el escaneo en un executor para no bloquear el event loop.
        """
        if not settings.CLAMAV_ENABLED:
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                details="ClamAV deshabilitado en configuración",
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(self._scan_bytes_sync, content)
        )


class VirusTotalScanner:
    """
    Escáner VirusTotal vía API v3.
    
    Requiere una API key válida. Es opcional y se activa por usuario.
    Nota: La API gratuita tiene un límite de 4 requests/minuto.
    """

    def __init__(self):
        self._api_key = settings.VIRUSTOTAL_API_KEY

    async def scan_file(self, file_path: str) -> ScanResult:
        """
        Escanea un archivo con VirusTotal.
        
        Args:
            file_path: Ruta del archivo a escanear
            
        Returns:
            ScanResult con el resultado del escaneo
        """
        if not self._api_key:
            return ScanResult(
                is_clean=True,
                scanner="virustotal",
                details="API key de VirusTotal no configurada",
            )

        try:
            import vt

            async with vt.Client(self._api_key) as client:
                # Calcular hash del archivo
                import hashlib

                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()

                # Primero intentar consultar por hash (más rápido, no consume cuota)
                try:
                    file_report = await client.get_object(f"/files/{file_hash}")
                    stats = file_report.last_analysis_stats

                    malicious = stats.get("malicious", 0)
                    total = sum(stats.values())

                    if malicious > 0:
                        # Obtener detalles de las detecciones
                        threats = []
                        results = file_report.last_analysis_results
                        for engine, result in results.items():
                            if result.get("category") == "malicious":
                                threats.append(
                                    f"{engine}: {result.get('result', 'unknown')}"
                                )

                        threat_list = "; ".join(threats[:5])
                        logger.warning(
                            f"⚠️ VirusTotal: {malicious}/{total} motores detectaron amenaza"
                        )
                        return ScanResult(
                            is_clean=False,
                            scanner="virustotal",
                            threat=f"{malicious}/{total} detecciones",
                            details=threat_list,
                        )

                    return ScanResult(
                        is_clean=True,
                        scanner="virustotal",
                        details=f"Archivo limpio ({total} motores)",
                    )

                except vt.error.APIError as e:
                    if e.code == "NotFoundError":
                        # Archivo no conocido - subir para análisis
                        with open(file_path, "rb") as f:
                            analysis = await client.scan_file(f, wait_for_completion=True)

                        stats = analysis.stats
                        malicious = stats.get("malicious", 0)

                        if malicious > 0:
                            return ScanResult(
                                is_clean=False,
                                scanner="virustotal",
                                threat=f"{malicious} detecciones",
                                details="Archivo subido y analizado",
                            )

                        return ScanResult(
                            is_clean=True,
                            scanner="virustotal",
                            details="Archivo limpio (recién analizado)",
                        )
                    raise

        except ImportError:
            logger.warning("vt-py no instalado. VirusTotal no disponible.")
            return ScanResult(
                is_clean=True,
                scanner="virustotal",
                details="Librería vt-py no disponible",
            )
        except Exception as e:
            logger.error(f"Error escaneando con VirusTotal: {e}")
            return ScanResult(
                is_clean=True,  # No bloquear si falla
                scanner="virustotal",
                details=f"Error en escaneo: {str(e)}",
            )

    async def scan_bytes(self, content: bytes, filename: str = "upload") -> ScanResult:
        """
        Escanea contenido en memoria con VirusTotal.
        Escribe a archivo temporal y escanea.
        
        Args:
            content: Bytes del archivo a escanear
            filename: Nombre del archivo (para logging)
            
        Returns:
            ScanResult con el resultado del escaneo
        """
        # VirusTotal requiere un archivo físico para escaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            return await self.scan_file(tmp_path)
        finally:
            os.unlink(tmp_path)


# Instancias singleton
clamav_scanner = ClamAVScanner()
virustotal_scanner = VirusTotalScanner()


async def scan_upload(
    content: bytes,
    filename: str,
    use_virustotal: bool = False,
) -> list[ScanResult]:
    """
    Escanea un archivo subido con todos los escáneres disponibles.
    
    Args:
        content: Contenido del archivo en bytes
        filename: Nombre del archivo original
        use_virustotal: Si se debe usar VirusTotal (configurable por usuario)
        
    Returns:
        Lista de ScanResult, uno por cada escáner utilizado
    """
    results = []

    # 1. Escaneo ClamAV (siempre si está habilitado)
    clamav_result = await clamav_scanner.scan_bytes(content)
    results.append(clamav_result)

    # 2. Escaneo VirusTotal (opcional, activable por usuario)
    # Se usa con solo tener la API key configurada; el switch por usuario lo activa.
    if use_virustotal and settings.VIRUSTOTAL_API_KEY:
        vt_result = await virustotal_scanner.scan_bytes(content, filename)
        results.append(vt_result)

    return results


def is_any_threat_found(results: list[ScanResult]) -> bool:
    """Verifica si algun escaner detecto una amenaza"""
    return any(not r.is_clean for r in results)


# Module-level cache for ClamAV availability (5-min TTL)
_clamav_cache: Optional[bool] = None
_clamav_cache_time: float = 0


def check_clamav_available(force: bool = False) -> bool:
    """
    Verifica si ClamAV esta disponible probando conexion real (PING/PONG por socket).
    Cachea el resultado por 5 minutos.
    """
    import time
    global _clamav_cache, _clamav_cache_time

    now = time.time()
    if not force and _clamav_cache is not None and (now - _clamav_cache_time) < 300:
        return _clamav_cache

    if not settings.CLAMAV_ENABLED:
        _clamav_cache = False
        _clamav_cache_time = now
        return False

    scanner = ClamAVScanner()
    result = scanner._try_connect()
    _clamav_cache = result
    _clamav_cache_time = now
    return result


# Module-level cache for VirusTotal availability (5-min TTL)
_vt_cache: Optional[bool] = None
_vt_cache_time: float = 0


def check_virustotal_available(force: bool = False) -> bool:
    """
    Verifica si VirusTotal esta disponible.
    La disponibilidad depende de que exista una API key configurada en el .env
    (la activación real del escaneo la controla el switch por usuario).
    No se hace una llamada de red para no ralentizar la carga de configuración.
    """
    import time
    global _vt_cache, _vt_cache_time

    now = time.time()
    if not force and _vt_cache is not None and (now - _vt_cache_time) < 300:
        return _vt_cache

    result = bool(settings.VIRUSTOTAL_API_KEY)
    _vt_cache = result
    _vt_cache_time = now
    return result
