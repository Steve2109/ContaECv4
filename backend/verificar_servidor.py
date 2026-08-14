"""
ContaEC - Verificación rápida en el servidor de producción
===========================================================
Uso (dentro de la carpeta del backend, con el venv activo):

    python verificar_servidor.py

Verifica:
  1. ClamAV: detección por socket (PING/PONG) + escaneo real con el archivo EICAR
     (debe DETECTARLO) y con un archivo limpio (debe pasar).
  2. Consulta RUC del SRI: prueba las dos fuentes (API clásica y API móvil)
     con un RUC real para decidir si hace falta integrar algo adicional.
  3. Módulo ML/IA: estado del CLI z-ai y de la capa de IA global.
"""
import asyncio
import sys

RUC_PRUEBA = "1792286127001"  # Cambie por un RUC real de su cliente si lo desea


def check_clamav() -> None:
    print("=" * 60)
    print("1) CLAMAV")
    print("=" * 60)
    from app.core.scanner import check_clamav_available, clamav_scanner

    ok = check_clamav_available(force=True)
    if not ok:
        print("  Estado (PING/PONG): NO DISPONIBLE")
        print("  Revise en el .env: CLAMAV_ENABLED=true, CLAMAV_SOCKET y que el")
        print("  daemon esté activo: systemctl status clamav-daemon")
        return
    print("  Estado (PING/PONG): DISPONIBLE")

    # Archivo de prueba estándar EICAR (debe ser detectado como virus)
    eicar = (
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-"
        b"ANTIVIRUS-TEST-FILE!$H+H*"
    )
    res = asyncio.run(clamav_scanner.scan_bytes(eicar))
    print(f"  Escaneo EICAR (esperado: detectado) -> is_clean={res.is_clean} threat={res.threat}")
    if res.is_clean:
        print("  ⚠️  ClamAV NO detectó el EICAR: revise las firmas (freshclam) y permisos del socket.")
    else:
        print("  ✅ ClamAV detectó el EICAR correctamente.")

    limpio = asyncio.run(clamav_scanner.scan_bytes(b"datos limpios de prueba"))
    print(f"  Escaneo archivo limpio -> is_clean={limpio.is_clean} ({limpio.details})")


async def check_sri(ruc: str) -> None:
    print("=" * 60)
    print("2) CONSULTA RUC DEL SRI")
    print("=" * 60)
    import httpx

    headers_clasica = {"User-Agent": "ContaEC/4.0"}
    headers_movil = {
        "User-Agent": "okhttp/4.9.0",
        "Accept": "application/json",
        "Accept-Language": "es",
    }
    urls = [
        ("API clásica", "https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest/ConsultaRuc/obtenerDatosRuc", headers_clasica, {"params": {"ruc": ruc}}),
        ("API móvil", f"https://srienlinea.sri.gob.ec/movil-servicios/api/v1.0/ruc/{ruc}", headers_movil, {}),
    ]

    async with httpx.AsyncClient(timeout=20) as client:
        for name, url, headers, extra in urls:
            try:
                r = await client.get(url, headers=headers, **extra)
                body = r.text[:200].replace("\n", " ")
                if r.status_code == 200 and ("razonSocial" in r.text or "razon_social" in r.text):
                    print(f"  {name}: HTTP {r.status_code} -> ¡RESPONDE! {body}")
                    print("  ✅ El botón SRI funcionará con esta fuente.")
                else:
                    print(f"  {name}: HTTP {r.status_code} -> no devuelve datos ({body[:120]})")
            except Exception as e:
                print(f"  {name}: ERROR {type(e).__name__}: {str(e)[:120]}")

    print("  Nota: si NINGUNA responde, el botón usará la validación local del RUC")
    print("  (dígito verificador, tipo de contribuyente y provincia) y habrá que")
    print("  evaluar un proveedor de consulta RUC de pago.")


def check_ai() -> None:
    print("=" * 60)
    print("3) MÓDULO ML/IA")
    print("=" * 60)
    from app.core.ai_admin import z_ai_installed, ai_global_enabled

    print(f"  CLI 'z-ai' instalado: {z_ai_installed()}")
    print(f"  Capa de IA global habilitada: {ai_global_enabled()}")
    if not z_ai_installed():
        print("  El chatbot funciona con reglas locales. Para la capa LLM:")
        print("  instale y autentique el CLI z-ai en el servidor.")
    else:
        print("  Verifique la autenticación con: z-ai chat --prompt 'hola'")


if __name__ == "__main__":
    ruc = sys.argv[1] if len(sys.argv) > 1 else RUC_PRUEBA
    check_clamav()
    asyncio.run(check_sri(ruc))
    check_ai()
    print("=" * 60)
    print("Verificación completada.")
