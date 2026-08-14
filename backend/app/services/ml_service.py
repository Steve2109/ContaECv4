"""
ContaEC - Servicio de Machine Learning / IA
Predicciones de ventas, detección de fraude, auto-categorización,
chatbot inteligente y generación de recomendaciones.

Implementa algoritmos reales que operan sobre los datos de la base
de datos (comprobantes, clientes, productos, etc.)
"""
import json
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, extract, cast, String, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_admin import log_ai_error, is_ai_enabled_for_user
from app.core.database import engine

from app.models.client import Client
from app.models.comprobante import Comprobante, ComprobanteDetalle, ComprobanteEstado
from app.models.integration import MovimientoBancario
from app.models.ml_ai import (
    ChatbotEstado,
    FraudeEstado,
    FraudeSeveridad,
    MLAlertaFraude,
    MLCategoriaRegla,
    MLChatbotMensaje,
    MLChatbotSesion,
    MLPrediccion,
    MLRecomendacion,
    PrediccionEstado,
    RecomendacionEstado,
)
from app.models.product import Product
from app.models.purchase import CuentaPorPagar

logger = logging.getLogger(__name__)


# ==========================================
# 1. PREDICCIÓN DE VENTAS
# ==========================================

class SalesPredictor:
    """Algoritmos de predicción de ventas"""

    @staticmethod
    def moving_average(data: list[float], window: int = 3) -> list[float]:
        """Promedio móvil simple"""
        if len(data) < window:
            return data[-1:] if data else [0.0]

        predictions = []
        for i in range(window, len(data) + 1):
            subset = data[max(0, i - window): i]
            predictions.append(sum(subset) / len(subset))

        # Predict next period
        last_window = data[-window:]
        next_pred = sum(last_window) / len(last_window)
        predictions.append(next_pred)
        return predictions

    @staticmethod
    def exponential_smoothing(
        data: list[float], alpha: float = 0.3
    ) -> list[float]:
        """Suavización exponencial simple"""
        if not data:
            return [0.0]

        smoothed = [data[0]]
        for i in range(1, len(data)):
            s = alpha * data[i] + (1 - alpha) * smoothed[i - 1]
            smoothed.append(s)

        # Predict next period
        next_pred = alpha * data[-1] + (1 - alpha) * smoothed[-1]
        smoothed.append(next_pred)
        return smoothed

    @staticmethod
    def linear_regression(data: list[float]) -> list[float]:
        """Regresión lineal simple"""
        n = len(data)
        if n < 2:
            return data if data else [0.0]

        x_vals = list(range(n))
        x_mean = sum(x_vals) / n
        y_mean = sum(data) / n

        numerator = sum(
            (x_vals[i] - x_mean) * (data[i] - y_mean) for i in range(n)
        )
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return [y_mean] * (n + 1)

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        predictions = [slope * x + intercept for x in range(n)]
        # Predict next period
        next_pred = slope * n + intercept
        predictions.append(next_pred)
        return predictions

    @staticmethod
    def calculate_mape(actual: list[float], predicted: list[float]) -> float:
        """Mean Absolute Percentage Error"""
        if not actual or len(actual) != len(predicted):
            return 100.0
        errors = []
        for a, p in zip(actual, predicted):
            if a != 0:
                errors.append(abs((a - p) / a))
        return (sum(errors) / len(errors) * 100) if errors else 100.0

    @staticmethod
    def calculate_rmse(actual: list[float], predicted: list[float]) -> float:
        """Root Mean Squared Error"""
        if not actual or len(actual) != len(predicted):
            return 0.0
        mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)
        return math.sqrt(mse)

    @staticmethod
    def calculate_r2(actual: list[float], predicted: list[float]) -> float:
        """R-squared (coefficient of determination)"""
        if not actual or len(actual) != len(predicted):
            return 0.0
        y_mean = sum(actual) / len(actual)
        ss_tot = sum((a - y_mean) ** 2 for a in actual)
        ss_res = sum((a - p) ** 2 for a, p in zip(actual, predicted))
        if ss_tot == 0:
            return 1.0
        return 1 - (ss_res / ss_tot)


async def prediccion_ventas(
    db: AsyncSession,
    company_id: str,
    user_id: str,
    tipo: str = "ventas",
    modelo: str = "moving_average",
) -> MLPrediccion:
    """
    Genera una predicción de ventas/ingresos/gastos/flujo_caja
    basada en datos históricos de comprobantes agrupados por mes.
    """
    now = datetime.now(timezone.utc)
    periodo_desde = now - timedelta(days=365)  # Último año
    periodo_hasta = now

    # Obtener datos históricos de comprobantes por mes
    # Usar extract() que funciona tanto en SQLite como en PostgreSQL
    year_col = extract("year", Comprobante.fecha_emision).label("anio")
    month_col = extract("month", Comprobante.fecha_emision).label("mes_num")
    
    result = await db.execute(
        select(
            year_col,
            month_col,
            func.sum(Comprobante.total_con_impuestos).label("total"),
        )
        .where(
            Comprobante.company_id == company_id,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO.value,
            Comprobante.fecha_emision >= periodo_desde,
            Comprobante.fecha_emision <= periodo_hasta,
        )
        .group_by(year_col, month_col)
        .order_by(year_col, month_col)
    )

    monthly_rows = result.all()
    # Convert to same format as before: {month_str: total}
    months = []
    data_points = []
    for row in monthly_rows:
        month_str = f"{int(row.anio)}-{int(row.mes_num):02d}"
        months.append(month_str)
        data_points.append(float(row.total or 0))

    # Si no hay datos suficientes, usar datos simulados basados en promedio
    if len(data_points) < 2:
        # Obtener total general
        total_result = await db.execute(
            select(func.sum(Comprobante.total_con_impuestos)).where(
                Comprobante.company_id == company_id,
                Comprobante.estado == ComprobanteEstado.AUTORIZADO.value,
            )
        )
        total = float(total_result.scalar() or 0)
        avg_monthly = total / 12 if total > 0 else 0
        data_points = [avg_monthly] * 6
        months = [
            (now - timedelta(days=30 * i)).strftime("%Y-%m")
            for i in range(5, -1, -1)
        ]

    predictor = SalesPredictor()

    # Aplicar modelo seleccionado
    if modelo == "exponential_smoothing":
        predictions = predictor.exponential_smoothing(data_points)
    elif modelo == "linear_regression":
        predictions = predictor.linear_regression(data_points)
    else:
        predictions = predictor.moving_average(data_points)

    # Calcular métricas (comparar datos reales vs predichos)
    fitted = predictions[:len(data_points)]
    mape = predictor.calculate_mape(data_points, fitted)
    rmse = predictor.calculate_rmse(data_points, fitted)
    r2 = predictor.calculate_r2(data_points, fitted)

    # Confianza basada en R2 y cantidad de datos
    confianza = min(95.0, max(10.0, r2 * 100 * (min(len(data_points), 12) / 12)))

    # Generar predicciones futuras (3 meses)
    next_pred_value = predictions[-1] if predictions else 0
    future_months = []
    for i in range(1, 4):
        future_date = now + timedelta(days=30 * i)
        future_months.append(future_date.strftime("%Y-%m"))

    resultado = {
        "historico": {
            months[i]: round(data_points[i], 2)
            for i in range(len(months))
        },
        "prediccion": {
            future_months[i]: round(next_pred_value, 2)
            for i in range(len(future_months))
        },
        "modelo": modelo,
        "puntos_historicos": len(data_points),
    }

    metricas = {
        "MAPE": round(mape, 2),
        "RMSE": round(rmse, 2),
        "R2": round(r2, 4),
    }

    prediccion = MLPrediccion(
        company_id=company_id,
        user_id=user_id,
        tipo=tipo,
        estado=PrediccionEstado.COMPLETADA.value,
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        datos_entrada=json.dumps({"meses": months, "valores": data_points}),
        resultado=json.dumps(resultado),
        metricas=json.dumps(metricas),
        modelo_usado=modelo,
        confianza=Decimal(str(round(confianza, 2))),
    )

    db.add(prediccion)
    await db.flush()

    return prediccion


# ==========================================
# 2. DETECCIÓN DE FRAUDE
# ==========================================

async def detectar_fraude(
    db: AsyncSession,
    company_id: str,
) -> list[MLAlertaFraude]:
    """
    Ejecuta la detección de fraude sobre los comprobantes de la empresa.
    Implementa: Z-score para montos anómalos, detección de duplicados,
    anomalías en secuencia, validación de RUC.
    """
    alertas: list[MLAlertaFraude] = []

    # Obtener comprobantes recientes (últimos 90 días)
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=90)
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.company_id == company_id,
            Comprobante.created_at >= fecha_limite,
        ).order_by(Comprobante.created_at.desc())
    )
    comprobantes = result.scalars().all()

    if not comprobantes:
        return alertas

    montos = [float(c.total_con_impuestos or 0) for c in comprobantes]

    # --- 1. Z-Score Anomaly Detection ---
    if len(montos) >= 3:
        mean_monto = sum(montos) / len(montos)
        std_monto = (
            math.sqrt(sum((m - mean_monto) ** 2 for m in montos) / len(montos))
            if len(montos) > 1
            else 0
        )

        if std_monto > 0:
            for comp in comprobantes:
                monto = float(comp.total_con_impuestos or 0)
                z_score = abs(monto - mean_monto) / std_monto

                if z_score > 3.0:
                    puntuacion = min(100, z_score * 15)
                    severidad = (
                        FraudeSeveridad.CRITICA.value
                        if puntuacion >= 80
                        else FraudeSeveridad.ALTA.value
                        if puntuacion >= 60
                        else FraudeSeveridad.MEDIA.value
                    )
                    alerta = MLAlertaFraude(
                        company_id=company_id,
                        comprobante_id=comp.id,
                        tipo_deteccion="monto_anomalo",
                        severidad=severidad,
                        estado=FraudeEstado.PENDIENTE.value,
                        puntuacion_fraude=Decimal(str(round(puntuacion, 2))),
                        descripcion=(
                            f"Monto anómalo detectado: ${monto:,.2f} "
                            f"(Z-score: {z_score:.2f}, promedio: ${mean_monto:,.2f})"
                        ),
                        evidencia=json.dumps({
                            "comprobante_id": comp.id,
                            "secuencial": comp.secuencial,
                            "monto": monto,
                            "z_score": round(z_score, 2),
                            "promedio": round(mean_monto, 2),
                            "desviacion": round(std_monto, 2),
                        }),
                    )
                    alertas.append(alerta)

    # --- 2. Duplicate Detection ---
    seen: dict[str, list[Comprobante]] = {}
    for comp in comprobantes:
        key = f"{comp.cliente_identificacion}_{comp.total_con_impuestos}_{comp.fecha_emision.strftime('%Y-%m-%d')}"
        if key in seen:
            seen[key].append(comp)
        else:
            seen[key] = [comp]

    for key, dupes in seen.items():
        if len(dupes) > 1:
            for comp in dupes[1:]:  # Skip first, flag the rest
                alerta = MLAlertaFraude(
                    company_id=company_id,
                    comprobante_id=comp.id,
                    tipo_deteccion="duplicado",
                    severidad=FraudeSeveridad.ALTA.value,
                    estado=FraudeEstado.PENDIENTE.value,
                    puntuacion_fraude=Decimal("85.00"),
                    descripcion=(
                        f"Posible comprobante duplicado: secuencial {comp.secuencial}, "
                        f"mismo RUC/monto/fecha que comprobante {dupes[0].secuencial}"
                    ),
                    evidencia=json.dumps({
                        "comprobante_id": comp.id,
                        "secuencial": comp.secuencial,
                        "duplicado_de": dupes[0].id,
                        "duplicado_secuencial": dupes[0].secuencial,
                        "ruc": comp.cliente_identificacion,
                        "monto": float(comp.total_con_impuestos or 0),
                    }),
                )
                alertas.append(alerta)

    # --- 3. Sequence Anomaly (gap in secuencial) ---
    secuencias = []
    for comp in comprobantes:
        try:
            secuencias.append((int(comp.secuencial), comp))
        except (ValueError, TypeError):
            pass

    secuencias.sort(key=lambda x: x[0])
    for i in range(1, len(secuencias)):
        gap = secuencias[i][0] - secuencias[i - 1][0]
        if gap > 10:  # Gap mayor a 10 secuencias
            alerta = MLAlertaFraude(
                company_id=company_id,
                comprobante_id=secuencias[i][1].id,
                tipo_deteccion="secuencia_anomala",
                severidad=FraudeSeveridad.MEDIA.value,
                estado=FraudeEstado.PENDIENTE.value,
                puntuacion_fraude=Decimal("45.00"),
                descripcion=(
                    f"Salto en secuencia detectado: de {secuencias[i-1][0]:09d} "
                    f"a {secuencias[i][0]:09d} (gap de {gap})"
                ),
                evidencia=json.dumps({
                    "secuencia_anterior": secuencias[i - 1][0],
                    "secuencia_actual": secuencias[i][0],
                    "gap": gap,
                    "comprobante_id": secuencias[i][1].id,
                }),
            )
            alertas.append(alerta)

    # --- 4. RUC Validation ---
    for comp in comprobantes:
        ruc = comp.cliente_identificacion or ""
        if len(ruc) == 13:
            # Validate RUC check digit (Ecuador)
            try:
                coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
                suma = 0
                for j, coef in enumerate(coeficientes):
                    val = int(ruc[j]) * coef
                    suma += val if val < 10 else val - 9
                digito_verificador = 10 - (suma % 10)
                if digito_verificador == 10:
                    digito_verificador = 0
                if digito_verificador != int(ruc[9]):
                    alerta = MLAlertaFraude(
                        company_id=company_id,
                        comprobante_id=comp.id,
                        tipo_deteccion="ruc_invalido",
                        severidad=FraudeSeveridad.CRITICA.value,
                        estado=FraudeEstado.PENDIENTE.value,
                        puntuacion_fraude=Decimal("95.00"),
                        descripcion=(
                            f"RUC con dígito verificador inválido: {ruc} "
                            f"(esperado: {digito_verificador}, encontrado: {ruc[9]})"
                        ),
                        evidencia=json.dumps({
                            "ruc": ruc,
                            "digito_esperado": digito_verificador,
                            "digito_encontrado": int(ruc[9]),
                            "comprobante_id": comp.id,
                            "secuencial": comp.secuencial,
                        }),
                    )
                    alertas.append(alerta)
            except (ValueError, IndexError):
                pass

    # Persist all alerts
    for alerta in alertas:
        db.add(alerta)
    await db.flush()

    return alertas


# ==========================================
# 3. AUTO-CATEGORIZACIÓN
# ==========================================

async def categorizar(
    db: AsyncSession,
    company_id: str,
    descripcion: str,
) -> dict:
    """
    Categoriza una descripción usando reglas de la empresa.
    Implementa matching por palabras clave y regex.
    """
    from app.schemas.ml_ai import CategorizeResponse

    # Obtener reglas activas de la empresa, ordenadas por prioridad
    result = await db.execute(
        select(MLCategoriaRegla).where(
            MLCategoriaRegla.company_id == company_id,
            MLCategoriaRegla.es_activa == True,
        ).order_by(MLCategoriaRegla.prioridad.desc())
    )
    reglas = result.scalars().all()

    if not reglas:
        # Default banking categories
        default_categories = _get_default_categories()
        return _match_default_category(descripcion, default_categories)

    descripcion_lower = descripcion.lower()
    candidatos = []

    for regla in reglas:
        score = 0.0

        # Keyword matching
        try:
            palabras = json.loads(regla.palabras_clave) if regla.palabras_clave else []
        except (json.JSONDecodeError, TypeError):
            palabras = []

        for palabra in palabras:
            if palabra.lower() in descripcion_lower:
                score += 10.0

        # Regex matching
        if regla.patron_regex:
            try:
                if re.search(regla.patron_regex, descripcion, re.IGNORECASE):
                    score += 20.0
            except re.error:
                pass

        # Bonus por prioridad
        score += regla.prioridad * 0.5

        if score > 0:
            candidatos.append({
                "regla_id": regla.id,
                "categoria": regla.categoria,
                "subcategoria": regla.subcategoria,
                "score": round(score, 2),
            })

    if not candidatos:
        default_categories = _get_default_categories()
        return _match_default_category(descripcion, default_categories)

    # Sort by score descending
    candidatos.sort(key=lambda x: x["score"], reverse=True)
    mejor = candidatos[0]

    # Normalize confidence to 0-100
    max_score = mejor["score"]
    confianza = min(100, max_score * 5)

    # Increment aplicaciones_count
    regla_result = await db.execute(
        select(MLCategoriaRegla).where(MLCategoriaRegla.id == mejor["regla_id"])
    )
    regla_obj = regla_result.scalars().first()
    if regla_obj:
        regla_obj.aplicaciones_count = (regla_obj.aplicaciones_count or 0) + 1
        await db.flush()

    return {
        "categoria": mejor["categoria"],
        "subcategoria": mejor["subcategoria"],
        "confianza": Decimal(str(round(confianza, 2))),
        "regla_aplicada_id": mejor["regla_id"],
        "todas_candidatas": candidatos[:5],
    }


def _get_default_categories() -> list[dict]:
    """Categorías bancarias por defecto"""
    return [
        {"categoria": "Ventas", "palabras": ["factura", "venta", "cobro", "ingreso", "abono"]},
        {"categoria": "Compras", "palabras": ["compra", "pago proveedor", "factura compra"]},
        {"categoria": "Nómina", "palabras": ["nomina", "rollo", "pago empleado", "iess", "sueldo", "salario"]},
        {"categoria": "Servicios", "palabras": ["luz", "agua", "telefono", "internet", "celular", "cnt", "electricidad"]},
        {"categoria": "Alquiler", "palabras": ["alquiler", "arriendo", "renta oficina", "canon"]},
        {"categoria": "Impuestos", "palabras": ["sri", "iva", "renta", "impuesto", "tasas", "contribucion"]},
        {"categoria": "Transferencias", "palabras": ["transferencia", "trf", "envio", "recepcion"]},
        {"categoria": "Gastos Bancarios", "palabras": ["comision", "cargo bancario", "mantenimiento", "interes", "sobregiro"]},
        {"categoria": "Seguros", "palabras": ["seguro", "poliza", "aseguradora"]},
        {"categoria": "Transporte", "palabras": ["transporte", "flete", "gasolina", "combustible", "envio"]},
    ]


def _match_default_category(descripcion: str, categorias: list[dict]) -> dict:
    """Match contra categorías por defecto"""
    descripcion_lower = descripcion.lower()
    mejor = None
    mejor_score = 0

    for cat in categorias:
        score = sum(
            10 for p in cat["palabras"] if p in descripcion_lower
        )
        if score > mejor_score:
            mejor_score = score
            mejor = cat

    if mejor:
        confianza = min(100, mejor_score * 5)
    else:
        mejor = {"categoria": "Sin Categorizar", "palabras": []}
        confianza = 0

    return {
        "categoria": mejor["categoria"],
        "subcategoria": None,
        "confianza": Decimal(str(round(confianza, 2))),
        "regla_aplicada_id": None,
        "todas_candidatas": [],
    }


# ==========================================
# 4. CHATBOT
# ==========================================

# Intenciones soportadas con patrones
INTENCIONES = {
    "saludo": [
        r"^(?:hola|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|hey|hi)[\s!.?]*$",
        r"^(?:hola|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|hey|hi)\b",
    ],
    "ayuda": [
        r"(?:ayuda|help|asistencia|soporte|c[oó]mo\s+(?:funciona|uso|hago|puedo))",
        r"(?:qu[eé]\s+(?:puedo|haces|sabes|haces))",
    ],
    "crear_comprobante": [
        r"(?:crear|generar|emitir|hacer)\s+(?:un[ao]?\s+)?(?:factura|comprobante|nota|retenci[oó]n)",
        r"(?:nuev[oa]\s+(?:factura|comprobante|nota|retenci[oó]n))",
        r"(?:factura\s+nueva|comprobante\s+nuevo)",
    ],
    "consulta_impuestos": [
        r"(?:impuesto|iva|renta|sri|retenci[oó]n|declaraci[oó]n)",
        r"(?:cu[aá]nto\s+(?:debo|pago)\s+(?:de\s+)?(?:impuesto|iva|renta))",
    ],
    "consulta_saldo": [
        r"(?:saldo|balance|cuenta\s+corriente)",
        r"(?:cu[aá]nto\s+(?:tengo|debe|debo|hay)(?:\s+(?:en\s+)?(?:la\s+)?cuenta)?)",
        r"(?:estado\s+(?:financiero|de\s+cuenta))",
    ],
    "consulta_factura": [
        r"(?:ver|consultar|buscar|mostrar|muestra(?:me|le)?|visualizar|listar|dame)\s+(?:l[ao]s?\s+)?(?:factura|comprobante|invoice)",
        r"(?:cu[aá]nto|c[uo][aá]ntas)\s+(?:factura|comprobante)",
        r"(?:estado|situaci[oó]n)\s+(?:de\s+)?(?:l[ao]s?\s+)?(?:factura|comprobante)",
        r"(?:detalle|informaci[oó]n)\s+(?:de\s+)?(?:l[ao]s?\s+)?(?:factura|comprobante)",
    ],
    "consulta_cliente": [
        r"(?:ver|consultar|buscar|mostrar|muestra(?:me|le)?|visualizar|listar|dame)\s+(?:el\s+)?(?:cliente|ruc)",
        r"(?:datos|informaci[oó]n)\s+(?:del?\s+)?(?:cliente)",
    ],
    "consulta_producto": [
        r"(?:ver|consultar|buscar|mostrar|muestra(?:me|le)?|visualizar|listar|dame)\s+(?:el\s+)?(?:producto|inventario|stock)",
        r"(?:precio|costo)\s+(?:del\s+)?(?:producto)",
    ],
}

# Patrones para extracción de entidades
ENTIDAD_PATTERNS = {
    "ruc": r"\b\d{10,13}\b",
    "monto": r"\$\s*[\d,]+(?:\.\d{2})?|\b\d+(?:\.\d{2})?\s*(?:d[oó]lares|usd)\b",
    "fecha": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    "secuencial": r"\b\d{6,9}\b",
}


def detectar_intencion(mensaje: str) -> Optional[str]:
    """Detecta la intención del mensaje del usuario"""
    mensaje_lower = mensaje.lower()
    for intencion, patrones in INTENCIONES.items():
        for patron in patrones:
            if re.search(patron, mensaje_lower, re.IGNORECASE):
                return intencion
    return None


def extraer_entidades(mensaje: str) -> dict:
    """Extrae entidades del mensaje (RUCs, montos, fechas, secuenciales)"""
    entidades = {}
    for tipo, patron in ENTIDAD_PATTERNS.items():
        matches = re.findall(patron, mensaje, re.IGNORECASE)
        if matches:
            entidades[tipo] = matches[0] if len(matches) == 1 else matches
    return entidades


def generar_respuesta_chatbot(
    intencion: Optional[str],
    entidades: dict,
    contexto: dict,
    mensaje: str,
) -> str:
    """Genera una respuesta contextual basada en la intención detectada"""

    if intencion == "saludo":
        return (
            "¡Hola! Soy el asistente virtual de ContaEC. "
            "Puedo ayudarte con:\n"
            "• Consultar facturas y comprobantes\n"
            "• Verificar saldos y estado financiero\n"
            "• Crear comprobantes electrónicos\n"
            "• Consultar clientes y productos\n"
            "• Información sobre impuestos (IVA, Renta, SRI)\n\n"
            "¿En qué puedo ayudarte?"
        )

    if intencion == "ayuda":
        return (
            "Puedo ayudarte con las siguientes tareas:\n\n"
            "📋 **Comprobantes**: Consultar, crear o verificar facturas\n"
            "💰 **Saldos**: Verificar tu balance y estado de cuenta\n"
            "👤 **Clientes**: Buscar información de clientes\n"
            "📦 **Productos**: Consultar inventario y precios\n"
            "🏛️ **Impuestos**: Información sobre IVA, retenciones y SRI\n\n"
            "Ejemplo: \"Muéstrame las facturas del mes\" o \"¿Cuál es mi saldo?\""
        )

    if intencion == "consulta_factura":
        respuesta = "Para consultar facturas, puedo ayudarte de las siguientes formas:\n\n"
        if "secuencial" in entidades:
            respuesta += f"• Buscaré la factura con secuencial {entidades['secuencial']}\n"
        else:
            respuesta += (
                "• Puedes ir a la sección de **Comprobantes** en el menú lateral\n"
                "• Usar filtros por fecha, estado o cliente\n"
                "• Pedirme detalles de una factura específica por su número\n\n"
            )
            respuesta += "¿Deseas buscar alguna factura en particular?"
        return respuesta

    if intencion == "consulta_saldo":
        return (
            "Para consultar tu saldo o estado financiero:\n\n"
            "• El resumen financiero está en el **Dashboard**\n"
            "• Los movimientos bancarios están en **Integraciones > Bancaria**\n"
            "• Las cuentas por cobrar/pagar en **Compras > Cuentas por Pagar**\n\n"
            "¿Necesitas información específica sobre algún saldo?"
        )

    if intencion == "crear_comprobante":
        return (
            "Para crear un comprobante electrónico:\n\n"
            "1. Ve a **Facturación** en el menú lateral\n"
            "2. Haz clic en **Nueva Factura**\n"
            "3. Sigue el asistente paso a paso:\n"
            "   - Selecciona el cliente\n"
            "   - Agrega productos/servicios\n"
            "   - Revisa totales y confirma\n\n"
            "Los tipos disponibles son: Factura, Nota de Crédito, "
            "Nota de Débito, Comprobante de Retención."
        )

    if intencion == "consulta_cliente":
        if "ruc" in entidades:
            return (
                f"Voy a buscar información del RUC {entidades['ruc']}. "
                f"Puedes usar la sección de **Clientes** en el menú lateral "
                f"para ver todos los detalles y su historial de compras."
            )
        return (
            "Para consultar clientes:\n\n"
            "• Ve a **Clientes** en el menú lateral\n"
            "• Puedes buscar por nombre o RUC\n"
            "• Cada cliente muestra su historial de comprobantes\n\n"
            "¿Buscas algún cliente en particular?"
        )

    if intencion == "consulta_producto":
        return (
            "Para consultar productos e inventario:\n\n"
            "• Ve a **Inventario** en el menú lateral\n"
            "• Puedes ver el stock actual en la pestaña **Stock**\n"
            "• El kardex muestra todos los movimientos\n\n"
            "¿Buscas algún producto específico?"
        )

    if intencion == "consulta_impuestos":
        return (
            "Información sobre impuestos en Ecuador:\n\n"
            "• **IVA**: 15% (tarifa vigente 2024-2025)\n"
            "• **Retención IVA**: 10%, 20%, 30%, 50%, 70%, 100%\n"
            "• **Retención Renta**: 1%, 2%, 8%, 10%, 25%\n"
            "• **Declaración**: Mensual si es agente de retención\n\n"
            "Puedes ver las retenciones aplicadas en cada comprobante. "
            "¿Necesitas información más específica?"
        )

    # Fallback - respuesta genérica
    return (
        "Entiendo tu consulta. Aunque no puedo ejecutar acciones directamente, "
        "puedo guiarte:\n\n"
        "• Para facturación: menú **Facturación**\n"
        "• Para clientes: menú **Clientes**\n"
        "• Para inventario: menú **Inventario**\n"
        "• Para reportes: menú **Dashboard**\n\n"
        "¿Puedes ser más específico sobre lo que necesitas?"
    )


# ==========================================
# 4b. LLM-POWERED CHATBOT (Hybrid)
# ==========================================

# System prompt for the LLM chatbot
CHATBOT_SYSTEM_PROMPT = """Eres el asistente virtual de ContaEC, un sistema de contabilidad y facturación electrónica del Ecuador desarrollado por T&M Technology Ec.

Tu rol es ayudar a los usuarios con consultas sobre:
- Facturación electrónica SRI (claves de acceso, XML, firmas digitales, autorización)
- Contabilidad (plan de cuentas, asientos contables, períodos fiscales)
- Impuestos ecuatorianos (IVA 15%, retenciones de renta e IVA, declaraciones)
- Gestión de clientes, proveedores, productos e inventario
- Roles de pago, recursos humanos, décimos
- Conciliación bancaria y estados financieros

Reglas importantes:
- Responde SIEMPRE en español ecuatoriano
- Sé conciso pero informativo
- Si no sabes algo, indícalo claramente en vez de inventar
- Para acciones específicas (crear facturas, etc.), guía al usuario al menú correspondiente
- Menciona regulaciones del SRI cuando sea relevante
- El IVA en Ecuador es 15% (vigente 2024-2025)
- Los tipos de comprobantes electrónicos son: 01=Factura, 03=Liquidación, 04=Nota Crédito, 05=Nota Débito, 06=Guía Remisión, 07=Retención
- La clave de acceso tiene 49 dígitos con dígito verificador módulo 11
"""


async def _generate_llm_response(
    mensaje: str,
    contexto: dict,
    company_id: str,
) -> Optional[str]:
    """
    Genera una respuesta usando LLM (z-ai) para consultas complejas
    que no pueden ser resueltas por el sistema basado en reglas.
    
    Uses the z-ai CLI tool for chat completions.
    Falls back to None if the LLM is unavailable.
    """
    import asyncio
    import tempfile
    
    try:
        # Build context-aware prompt
        context_info = ""
        if contexto.get("ultima_intencion"):
            context_info += f"\nContexto: La intención anterior fue '{contexto['ultima_intencion']}'."
        if contexto.get("ultima_entidades"):
            context_info += f" Entidades previas: {json.dumps(contexto['ultima_entidades'])}"
        
        full_prompt = f"{mensaje}{context_info}"
        
        # Use z-ai CLI for LLM chat completion
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        proc = await asyncio.create_subprocess_exec(
            "z-ai", "chat",
            "--prompt", full_prompt,
            "--system", CHATBOT_SYSTEM_PROMPT,
            "--output", tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("LLM chatbot timed out after 30s")
            log_ai_error("chatbot_llm", "z-ai tardó más de 30s en responder (timeout)", company_id=company_id)
            return None
        
        if proc.returncode != 0:
            err_text = stderr.decode(errors='replace')[:300]
            logger.warning(f"LLM chatbot failed: {err_text}")
            log_ai_error("chatbot_llm", "z-ai falló al generar la respuesta", company_id=company_id, detail=err_text)
            return None
        
        # Read the response from the output file
        import os
        try:
            with open(tmp_path, 'r') as f:
                result = json.load(f)
            
            # The z-ai CLI returns JSON with the response
            if isinstance(result, dict):
                respuesta = result.get("content") or result.get("message") or result.get("response", "")
            elif isinstance(result, str):
                respuesta = result
            elif isinstance(result, list) and result:
                # May return a list of messages
                first = result[0]
                if isinstance(first, dict):
                    respuesta = first.get("content", "")
                else:
                    respuesta = str(first)
            else:
                respuesta = str(result)
            
            if respuesta and len(respuesta.strip()) > 10:
                return respuesta.strip()
            
            return None
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            log_ai_error("chatbot_llm", "No se pudo interpretar la respuesta de z-ai", company_id=company_id, detail=str(e))
            return None
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            
    except FileNotFoundError:
        logger.warning("z-ai CLI not found, falling back to rule-based chatbot")
        log_ai_error("chatbot_llm", "CLI 'z-ai' no instalado: la capa LLM no está disponible", company_id=company_id)
        return None
    except Exception as e:
        logger.error(f"Error in LLM chatbot: {e}")
        log_ai_error("chatbot_llm", f"Error inesperado en la capa LLM: {e}", company_id=company_id)
        return None


async def chatbot_responder(
    db: AsyncSession,
    sesion_id: str,
    mensaje: str,
    user_id: str,
) -> MLChatbotMensaje:
    """
    Procesa un mensaje del chatbot: detecta intención, extrae entidades,
    genera respuesta contextual y actualiza la sesión.
    
    Estrategia híbrida:
    1. Si la intención es reconocida (saludo, ayuda, consultas específicas):
       usa respuestas basadas en reglas (rápido, sin costo de API).
    2. Si la intención NO es reconocida o el mensaje es complejo:
       usa LLM (z-ai) para generar una respuesta inteligente.
    """
    # Obtener sesión
    result = await db.execute(
        select(MLChatbotSesion).where(MLChatbotSesion.id == sesion_id)
    )
    sesion = result.scalars().first()
    if not sesion:
        raise ValueError("Sesión de chatbot no encontrada")

    # Load context
    try:
        contexto = json.loads(sesion.contexto) if sesion.contexto else {}
    except (json.JSONDecodeError, TypeError):
        contexto = {}

    # Detect intention and extract entities
    intencion = detectar_intencion(mensaje)
    entidades = extraer_entidades(mensaje)

    # Generate response - hybrid approach
    use_llm = intencion is None or intencion == "ayuda"
    
    if use_llm:
        # La capa LLM se puede desactivar globalmente o por usuario desde el
        # panel del administrador (ML/IA). Si está desactivada, se usa solo reglas.
        if is_ai_enabled_for_user(user_id):
            # Try LLM for unknown/complex queries
            respuesta = await _generate_llm_response(mensaje, contexto, sesion.company_id)
        else:
            respuesta = None
        if respuesta is None:
            # LLM failed or disabled, fall back to rule-based
            respuesta = generar_respuesta_chatbot(intencion, entidades, contexto, mensaje)
    else:
        # Use rule-based for known intents (fast, no API cost)
        respuesta = generar_respuesta_chatbot(intencion, entidades, contexto, mensaje)

    # Save user message
    user_msg = MLChatbotMensaje(
        sesion_id=sesion_id,
        rol="usuario",
        contenido=mensaje,
        intencion_detectada=intencion,
        entidades=json.dumps(entidades) if entidades else None,
    )
    db.add(user_msg)
    await db.flush()

    # Save assistant response
    assistant_msg = MLChatbotMensaje(
        sesion_id=sesion_id,
        rol="asistente",
        contenido=respuesta,
        intencion_detectada=None,
        entidades=None,
    )
    db.add(assistant_msg)
    await db.flush()

    # Update session context
    contexto["ultima_intencion"] = intencion
    contexto["ultima_entidades"] = entidades
    contexto["mensajes_count"] = contexto.get("mensajes_count", 0) + 1
    if not sesion.titulo and intencion:
        sesion.titulo = f"Chat: {intencion.replace('_', ' ').title()}"
    sesion.contexto = json.dumps(contexto)
    await db.flush()

    return assistant_msg


# ==========================================
# 5. RECOMENDACIONES
# ==========================================

async def generar_recomendaciones(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> list[MLRecomendacion]:
    """
    Genera recomendaciones basadas en el análisis de datos de la empresa.
    Incluye: productos, clientes, precios, inventario, finanzas.
    """
    recomendaciones: list[MLRecomendacion] = []

    # --- 1. Product Recommendations (top sellers / low sellers) ---
    result = await db.execute(
        select(
            ComprobanteDetalle.descripcion,
            ComprobanteDetalle.codigo_principal,
            func.sum(ComprobanteDetalle.cantidad).label("total_vendido"),
            func.sum(ComprobanteDetalle.precio_total_sin_impuestos).label("total_ingresos"),
        )
        .join(Comprobante, ComprobanteDetalle.comprobante_id == Comprobante.id)
        .where(
            Comprobante.company_id == company_id,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO.value,
        )
        .group_by(
            ComprobanteDetalle.descripcion,
            ComprobanteDetalle.codigo_principal,
        )
        .order_by(func.sum(ComprobanteDetalle.cantidad).desc())
    )
    productos_ventas = result.all()

    # Top seller recommendation
    if productos_ventas and len(productos_ventas) > 0:
        top = productos_ventas[0]
        recomendaciones.append(
            MLRecomendacion(
                company_id=company_id,
                user_id=user_id,
                tipo="producto",
                estado=RecomendacionEstado.PENDIENTE.value,
                titulo="Producto más vendido - Oportunidad de promoción",
                descripcion=(
                    f"El producto '{top.descripcion}' (código: {top.codigo_principal}) "
                    f"es tu producto más vendido con {float(top.total_vendido or 0):.0f} unidades. "
                    "Considera crear promociones o bundles para aumentar aún más las ventas."
                ),
                datos_contexto=json.dumps({
                    "codigo": top.codigo_principal,
                    "total_vendido": float(top.total_vendido or 0),
                    "total_ingresos": float(top.total_ingresos or 0),
                }),
                impacto_estimado="Aumento potencial del 10-15% en ventas",
                confianza=Decimal("80.00"),
            )
        )

    # Low seller recommendation
    if productos_ventas and len(productos_ventas) > 3:
        low = productos_ventas[-1]
        recomendaciones.append(
            MLRecomendacion(
                company_id=company_id,
                user_id=user_id,
                tipo="producto",
                estado=RecomendacionEstado.PENDIENTE.value,
                titulo="Producto con baja rotación - Evaluar descuento",
                descripcion=(
                    f"El producto '{low.descripcion}' tiene baja rotación "
                    f"({float(low.total_vendido or 0):.0f} unidades vendidas). "
                    "Considera aplicar descuentos o descontinuar el producto."
                ),
                datos_contexto=json.dumps({
                    "codigo": low.codigo_principal,
                    "total_vendido": float(low.total_vendido or 0),
                    "total_ingresos": float(low.total_ingresos or 0),
                }),
                impacto_estimado="Reducción de inventario estancado",
                confianza=Decimal("65.00"),
            )
        )

    # --- 2. Client Recommendations ---
    result = await db.execute(
        select(
            Comprobante.cliente_identificacion,
            Comprobante.cliente_razon_social,
            func.count(Comprobante.id).label("total_comprobantes"),
            func.sum(Comprobante.total_con_impuestos).label("total_compras"),
        )
        .where(
            Comprobante.company_id == company_id,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO.value,
        )
        .group_by(
            Comprobante.cliente_identificacion,
            Comprobante.cliente_razon_social,
        )
        .order_by(func.sum(Comprobante.total_con_impuestos).desc())
    )
    clientes_ventas = result.all()

    # Top client recommendation
    if clientes_ventas and len(clientes_ventas) > 0:
        top_cliente = clientes_ventas[0]
        nombre = top_cliente.cliente_razon_social or top_cliente.cliente_identificacion or "Cliente"
        recomendaciones.append(
            MLRecomendacion(
                company_id=company_id,
                user_id=user_id,
                tipo="cliente",
                estado=RecomendacionEstado.PENDIENTE.value,
                titulo="Cliente principal - Programa de fidelización",
                descripcion=(
                    f"El cliente '{nombre}' genera el mayor volumen de compras "
                    f"(${float(top_cliente.total_compras or 0):,.2f} en "
                    f"{top_cliente.total_comprobantes} comprobantes). "
                    "Considera implementar un programa de fidelización o descuentos especiales."
                ),
                datos_contexto=json.dumps({
                    "ruc": top_cliente.cliente_identificacion,
                    "total_compras": float(top_cliente.total_compras or 0),
                    "total_comprobantes": top_cliente.total_comprobantes,
                }),
                impacto_estimado="Retención de cliente clave",
                confianza=Decimal("75.00"),
            )
        )

    # --- 3. Price Optimization ---
    if productos_ventas and len(productos_ventas) >= 2:
        precios = [
            float(p.total_ingresos or 0) / max(float(p.total_vendido or 1), 1)
            for p in productos_ventas
        ]
        if precios:
            avg_price = sum(precios) / len(precios)
            max_price = max(precios)
            if max_price > avg_price * 1.5:
                recomendaciones.append(
                    MLRecomendacion(
                        company_id=company_id,
                        user_id=user_id,
                        tipo="precio",
                        estado=RecomendacionEstado.PENDIENTE.value,
                        titulo="Oportunidad de ajuste de precios",
                        descripcion=(
                            f"Tu precio promedio es ${avg_price:,.2f} pero algunos productos "
                            f"tienen un precio de ${max_price:,.2f}. "
                            "Considera ajustar precios para maximizar márgenes en productos premium."
                        ),
                        datos_contexto=json.dumps({
                            "precio_promedio": round(avg_price, 2),
                            "precio_maximo": round(max_price, 2),
                            "diferencia_pct": round((max_price / avg_price - 1) * 100, 2),
                        }),
                        impacto_estimado="Aumento potencial de margen del 5-10%",
                        confianza=Decimal("60.00"),
                    )
                )

    # --- 4. Inventory Alerts ---
    result = await db.execute(
        select(Product).where(
            Product.company_id == company_id,
            Product.is_active == True,
        )
    )
    productos = result.scalars().all()

    low_stock = [
        p for p in productos
        if p.stock is not None and p.stock_minimo is not None and p.stock <= p.stock_minimo
    ]

    if low_stock:
        productos_nombres = ", ".join(
            [f"{p.nombre} (stock: {p.stock})" for p in low_stock[:5]]
        )
        recomendaciones.append(
            MLRecomendacion(
                company_id=company_id,
                user_id=user_id,
                tipo="inventario",
                estado=RecomendacionEstado.PENDIENTE.value,
                titulo=f"Alerta de stock bajo - {len(low_stock)} producto(s)",
                descripcion=(
                    f"Los siguientes productos están por debajo del stock mínimo: "
                    f"{productos_nombres}. "
                    "Es recomendable realizar un reabastecimiento pronto."
                ),
                datos_contexto=json.dumps({
                    "productos_bajo_stock": [
                        {
                            "id": p.id,
                            "nombre": p.nombre,
                            "stock": float(p.stock or 0),
                            "stock_minimo": float(p.stock_minimo or 0),
                        }
                        for p in low_stock
                    ],
                }),
                impacto_estimado="Evitar rupturas de stock",
                confianza=Decimal("90.00"),
            )
        )

    # --- 5. Financial Health ---
    # Check accounts payable
    result = await db.execute(
        select(
            func.count(CuentaPorPagar.id).label("total_cxp"),
            func.sum(CuentaPorPagar.monto_pendiente).label("total_pendiente"),
        ).where(
            CuentaPorPagar.company_id == company_id,
            CuentaPorPagar.estado.in_(["pendiente", "parcial", "vencida"]),
        )
    )
    cxp_stats = result.first()

    if cxp_stats and cxp_stats.total_pendiente and float(cxp_stats.total_pendiente) > 0:
        total_pendiente = float(cxp_stats.total_pendiente)
        recomendaciones.append(
            MLRecomendacion(
                company_id=company_id,
                user_id=user_id,
                tipo="financiera",
                estado=RecomendacionEstado.PENDIENTE.value,
                titulo="Cuentas por pagar pendientes - Planificar pagos",
                descripcion=(
                    f"Tienes {cxp_stats.total_cxp} cuenta(s) por pagar pendientes "
                    f"por un total de ${total_pendiente:,.2f}. "
                    "Considera planificar los pagos para evitar recargos por mora "
                    "y mantener un buen historial crediticio."
                ),
                datos_contexto=json.dumps({
                    "total_cuentas": cxp_stats.total_cxp,
                    "total_pendiente": total_pendiente,
                }),
                impacto_estimado="Evitar penalidades por pago tardío",
                confianza=Decimal("85.00"),
            )
        )

    # Persist all recommendations
    for rec in recomendaciones:
        db.add(rec)
    await db.flush()

    return recomendaciones
