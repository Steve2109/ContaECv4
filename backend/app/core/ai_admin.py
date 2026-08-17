"""
ContaEC - Configuración y salud del módulo ML/IA (admin)

Permite al administrador:
- Activar/desactivar la capa de IA (global y por usuario)
- Ver el estado del CLI `z-ai` (capa LLM opcional)
- Ver los errores recientes del módulo ML/IA y resolverlos desde el panel

La configuración se persiste en un archivo JSON (no requiere migración de BD).
Los errores se guardan en un buffer en memoria (los últimos N).
"""
import json
import logging
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Archivo de configuración de IA (persistente entre reinicios)
_AI_SETTINGS_FILE = os.environ.get(
    "AI_SETTINGS_FILE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ai_settings.json"),
)

_lock = threading.Lock()

# ==========================================
# Configuración (global + por usuario)
# ==========================================

def _default_settings() -> dict:
    return {"global_enabled": True, "users": {}}


def load_ai_settings() -> dict:
    """Carga la configuración de IA desde el archivo JSON"""
    try:
        with open(_AI_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "global_enabled": bool(data.get("global_enabled", True)),
                "users": data.get("users", {}) if isinstance(data.get("users"), dict) else {},
            }
    except FileNotFoundError:
        return _default_settings()
    except Exception as e:
        logger.warning(f"No se pudo leer {_AI_SETTINGS_FILE}: {e}")
        return _default_settings()


def save_ai_settings(data: dict) -> None:
    """Persiste la configuración de IA en el archivo JSON"""
    with _lock:
        try:
            os.makedirs(os.path.dirname(_AI_SETTINGS_FILE), exist_ok=True)
            with open(_AI_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"No se pudo guardar {_AI_SETTINGS_FILE}: {e}")


def ai_global_enabled() -> bool:
    """¿Está habilitada la capa de IA globalmente?"""
    return load_ai_settings().get("global_enabled", True)


def set_ai_global_enabled(enabled: bool) -> bool:
    """Activa/desactiva la capa de IA globalmente"""
    data = load_ai_settings()
    data["global_enabled"] = bool(enabled)
    save_ai_settings(data)
    return data["global_enabled"]


def get_user_ai_enabled(user_id: str) -> Optional[bool]:
    """Override por usuario (None = usa el valor global)"""
    users = load_ai_settings().get("users", {})
    entry = users.get(str(user_id))
    if isinstance(entry, dict):
        return bool(entry.get("enabled", True))
    return None


def set_user_ai_enabled(user_id: str, enabled: bool) -> bool:
    """Activa/desactiva la IA para un usuario específico"""
    data = load_ai_settings()
    data["users"][str(user_id)] = {"enabled": bool(enabled)}
    save_ai_settings(data)
    return bool(enabled)


def is_ai_enabled_for_user(user_id: str) -> bool:
    """Efectivo para un usuario: override si existe, si no el global"""
    override = get_user_ai_enabled(user_id)
    if override is not None:
        return override
    return ai_global_enabled()


def z_ai_installed() -> bool:
    """¿Está instalado el CLI z-ai en el servidor?"""
    return shutil.which("z-ai") is not None


def llm_configured() -> bool:
    """
    ¿Hay una capa LLM configurada? True si hay API key OpenAI-compatible
    (LLM_API_KEY) o si el CLI z-ai está instalado.
    """
    try:
        from app.core.config import get_settings
        if getattr(get_settings(), "LLM_API_KEY", ""):
            return True
    except Exception:
        pass
    return z_ai_installed()


# ==========================================
# Buffer de errores ML/IA
# ==========================================

_AI_ERRORS: list[dict] = []
_MAX_ERRORS = 100


def log_ai_error(
    source: str,
    message: str,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Registra un error del módulo ML/IA (visible en el panel del admin)"""
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "message": message,
        "user_id": user_id,
        "company_id": company_id,
        "detail": detail,
    }
    with _lock:
        _AI_ERRORS.append(entry)
        if len(_AI_ERRORS) > _MAX_ERRORS:
            del _AI_ERRORS[: len(_AI_ERRORS) - _MAX_ERRORS]
    logger.warning(f"[AI] {source}: {message}")


def get_ai_errors(limit: int = 50) -> list[dict]:
    """Devuelve los errores más recientes (nuevo primero)"""
    with _lock:
        return list(reversed(_AI_ERRORS[-limit:]))


def clear_ai_errors() -> int:
    """Limpia el buffer de errores. Devuelve cuántos se eliminaron."""
    with _lock:
        count = len(_AI_ERRORS)
        _AI_ERRORS.clear()
        return count


def ai_errors_count() -> int:
    with _lock:
        return len(_AI_ERRORS)


# ==========================================
# Autotest de respuestas de IA
# ==========================================

async def ai_self_test() -> dict:
    """
    Prueba la cadena de respuestas de IA con un mensaje de ejemplo:
    1. Detección de intención (reglas locales, sin costo)
    2. Capa LLM (z-ai) si está instalada y habilitada
    3. Fallback por reglas

    Devuelve un dict con el resultado de cada capa para mostrarlo en el panel.
    """
    from app.services.ml_service import (
        detectar_intencion,
        extraer_entidades,
        generar_respuesta_chatbot,
        _generate_llm_response,
    )

    sample = "¿Cuánto debo pagar de IVA este mes?"
    result = {
        "ok": False,
        "sample": sample,
        "intent_detected": None,
        "llm_available": False,
        "llm_response": None,
        "fallback_available": True,
        "fallback_response": None,
        "error": None,
        "z_ai_installed": z_ai_installed(),
        "llm_configured": llm_configured(),
        "global_enabled": ai_global_enabled(),
    }

    # 1. Reglas
    try:
        intencion = detectar_intencion(sample)
        entidades = extraer_entidades(sample)
        result["intent_detected"] = intencion
        result["fallback_response"] = generar_respuesta_chatbot(intencion, entidades, {}, sample)
    except Exception as e:
        result["error"] = f"Error en motor de reglas: {e}"
        log_ai_error("self_test", str(e))
        return result

    # 2. Capa LLM (z-ai)
    if ai_global_enabled():
        try:
            respuesta = await _generate_llm_response(sample, {}, company_id="self-test")
            if respuesta:
                result["llm_available"] = True
                result["llm_response"] = respuesta
        except Exception as e:
            result["error"] = f"Error en capa LLM: {e}"

    if result["llm_available"]:
        result["ok"] = True
    elif not result["error"] and not llm_configured():
        result["error"] = (
            "La capa inteligente (LLM) no está configurada. Configure una API key "
            "(LLM_API_KEY en el .env) de un proveedor OpenAI-compatible —OpenAI, OpenRouter, "
            "Groq, Ollama, etc.— para habilitarla sin instalar nada en el servidor, "
            "o instale el CLI z-ai. Mientras tanto, el chatbot funciona con respuestas basadas en reglas."
        )
        log_ai_error("self_test", result["error"])
    elif not result["error"]:
        result["error"] = "La capa LLM está configurada pero no devolvió respuesta (¿API key inválida o sin crédito?)."

    # El sistema siempre puede responder (fallback por reglas)
    result["ok"] = True
    return result
