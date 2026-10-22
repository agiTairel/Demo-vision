"""Análisis de calidad con modelos de visión por API (Anthropic u OpenAI).

El proveedor se elige con la variable PROVEEDOR ("anthropic", "openai" o
"simulado"). Si el proveedor principal falla y hay clave del otro, se usa
el otro como respaldo automáticamente.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import time
from dataclasses import dataclass

from PIL import Image, ImageOps

from .productos import CATEGORIAS, PRODUCTOS

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

MODELO_ANTHROPIC_DEFECTO = "claude-sonnet-5-5"
MODELO_OPENAI_DEFECTO = "gpt-6.1-sol"
LADO_MAXIMO = 1280  # px; suficiente para ver defectos y abarata la llamada
TIMEOUT_S = 45


def config(clave: str, defecto: str | None = None) -> str | None:
    """Lee primero st.secrets (Streamlit Cloud) y después variables de entorno."""
    try:
        import streamlit as st

        if clave in st.secrets:
            return str(st.secrets[clave])
    except Exception:
        pass
    return os.environ.get(clave, defecto)


# ---------------------------------------------------------------------------
# Esquema de salida (compatible con Structured Outputs estricto de OpenAI
# y con input_schema de herramientas de Anthropic)
# ---------------------------------------------------------------------------

ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "producto_detectado",
        "es_producto_agroalimentario",
        "categoria",
        "puntuacion_calidad",
        "madurez",
        "color",
        "defectos",
        "calibre_estimado",
        "destino_recomendado",
        "resumen",
        "confianza",
        "advertencia",
    ],
    "properties": {
        "producto_detectado": {
            "type": "string",
            "description": "Producto y, si se aprecia, variedad o tipo. Ej.: 'Tomate tipo pera'.",
        },
        "es_producto_agroalimentario": {
            "type": "boolean",
            "description": "False si la imagen no muestra un producto agroalimentario evaluable.",
        },
        "categoria": {"type": "string", "enum": CATEGORIAS},
        "puntuacion_calidad": {
            "type": "integer",
            "description": "0 a 100. 90+ Extra, 75-89 I, 55-74 II, <55 Destrío.",
        },
        "madurez": {
            "type": "object",
            "additionalProperties": False,
            "required": ["estado", "porcentaje"],
            "properties": {
                "estado": {
                    "type": "string",
                    "description": "Ej.: 'Inmaduro', 'Pintón', 'Óptimo', 'Sobremaduro', 'No aplica'.",
                },
                "porcentaje": {
                    "type": "integer",
                    "description": "0 = totalmente inmaduro, 100 = sobremaduro. Óptimo comercial ~70.",
                },
            },
        },
        "color": {
            "type": "object",
            "additionalProperties": False,
            "required": ["descripcion", "uniformidad"],
            "properties": {
                "descripcion": {"type": "string"},
                "uniformidad": {"type": "integer", "description": "0 a 100"},
            },
        },
        "defectos": {
            "type": "array",
            "description": "Lista vacía si no hay defectos visibles.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tipo", "severidad", "zona", "descripcion"],
                "properties": {
                    "tipo": {"type": "string", "description": "Nombre técnico breve del defecto."},
                    "severidad": {"type": "string", "enum": ["leve", "moderado", "grave"]},
                    "zona": {"type": "string", "description": "Dónde se ve en la imagen."},
                    "descripcion": {"type": "string"},
                },
            },
        },
        "calibre_estimado": {
            "type": "string",
            "description": "Estimación orientativa de tamaño o 'No determinable sin referencia de escala'.",
        },
        "destino_recomendado": {
            "type": "string",
            "enum": [
                "Mercado en fresco premium",
                "Mercado en fresco",
                "Industria / transformación",
                "Alimentación animal / subproducto",
                "Descarte",
                "No aplica",
            ],
        },
        "resumen": {
            "type": "string",
            "description": "Dos frases como mucho, tono de técnico de calidad, en español.",
        },
        "confianza": {"type": "integer", "description": "0 a 100, confianza en la evaluación."},
        "advertencia": {
            "type": ["string", "null"],
            "description": "Problemas de la foto (desenfoque, luz, varios productos...) o null.",
        },
    },
}

PROMPT_SISTEMA = """Eres el inspector de calidad automático de una central hortofrutícola y \
cerealista de Navarra. Evalúas una única fotografía de producto agroalimentario como lo haría \
un técnico de control de calidad con experiencia en normas de comercialización de la UE.

Reglas:
- Responde siempre en español de España, con terminología del sector.
- Sé honesto: si la imagen no permite evaluar algo, dilo y baja la confianza.
- No inventes defectos que no se vean. Si el producto está sano, la lista de defectos va vacía.
- Si en la imagen hay varias piezas o un lote, evalúa el lote en conjunto y menciónalo en el resumen.
- Si la imagen no es un producto agroalimentario, marca es_producto_agroalimentario=false, \
categoria "No evaluable", destino "No aplica", y explica en la advertencia qué se ve (con humor amable).
- Coherencia: puntuación 90-100 Extra, 75-89 I, 55-74 II, menos de 55 Destrío."""


def construir_prompt_usuario(producto: str) -> str:
    p = PRODUCTOS.get(producto, PRODUCTOS["auto"])
    if producto == "auto":
        cabecera = "El usuario no ha indicado el producto."
    else:
        cabecera = f"El usuario indica que el producto es: {p['nombre']}."
    return (
        f"{cabecera}\nCriterios a revisar: {p['criterios']}\n\n"
        "Analiza la fotografía y devuelve el informe de calidad con el esquema indicado."
    )


# ---------------------------------------------------------------------------
# Imagen
# ---------------------------------------------------------------------------


def preparar_imagen(datos: bytes) -> tuple[bytes, Image.Image]:
    """Corrige la rotación EXIF del móvil, pasa a RGB, reduce tamaño y recomprime en JPEG."""
    img = Image.open(io.BytesIO(datos))
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode in ("RGBA", "LA"):
            fondo.paste(img, mask=img.getchannel("A"))
            img = fondo
        else:
            img = img.convert("RGB")
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue(), img


def huella(jpeg: bytes, producto: str) -> str:
    return hashlib.sha256(jpeg + producto.encode()).hexdigest()[:24]


def paleta_dominante(img: Image.Image, n: int = 5) -> list[tuple[str, float]]:
    """Colores dominantes (hex, proporción) mediante cuantización. Cálculo local, sin IA."""
    peq = img.copy()
    peq.thumbnail((160, 160))
    q = peq.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    cuentas = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in cuentas)
    salida = []
    for c, idx in cuentas[:n]:
        r, g, b = pal[idx * 3 : idx * 3 + 3]
        salida.append((f"#{r:02x}{g:02x}{b:02x}", c / total))
    return salida


# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------


@dataclass
class Resultado:
    informe: dict
    proveedor: str
    modelo: str
    segundos: float
    desde_cache: bool = False


class ErrorAnalisis(Exception):
    pass


def _analizar_anthropic(jpeg: bytes, producto: str) -> tuple[dict, str]:
    import anthropic

    clave = config("ANTHROPIC_API_KEY")
    if not clave:
        raise ErrorAnalisis("Falta ANTHROPIC_API_KEY")
    modelo = config("ANTHROPIC_MODEL", MODELO_ANTHROPIC_DEFECTO)
    cliente = anthropic.Anthropic(api_key=clave, timeout=TIMEOUT_S, max_retries=1)
    resp = cliente.messages.create(
        model=modelo,
        max_tokens=2000,
        system=PROMPT_SISTEMA,
        tools=[
            {
                "name": "informe_calidad",
                "description": "Registra el informe de calidad de la imagen analizada.",
                "input_schema": ESQUEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "informe_calidad"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.b64encode(jpeg).decode(),
                        },
                    },
                    {"type": "text", "text": construir_prompt_usuario(producto)},
                ],
            }
        ],
    )
    for bloque in resp.content:
        if getattr(bloque, "type", None) == "tool_use":
            return dict(bloque.input), modelo
    raise ErrorAnalisis("La respuesta de Anthropic no contiene el informe")


def _analizar_openai(jpeg: bytes, producto: str) -> tuple[dict, str]:
    import openai

    clave = config("OPENAI_API_KEY")
    if not clave:
        raise ErrorAnalisis("Falta OPENAI_API_KEY")
    modelo = config("OPENAI_MODEL", MODELO_OPENAI_DEFECTO)
    cliente = openai.OpenAI(api_key=clave, timeout=TIMEOUT_S, max_retries=1)
    url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    resp = cliente.chat.completions.create(
        model=modelo,
        max_completion_tokens=4000,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "informe_calidad", "strict": True, "schema": ESQUEMA},
        },
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": construir_prompt_usuario(producto)},
                    {"type": "image_url", "image_url": {"url": url, "detail": "high"}},
                ],
            },
        ],
    )
    texto = resp.choices[0].message.content or ""
    try:
        return json.loads(texto), modelo
    except json.JSONDecodeError as e:
        raise ErrorAnalisis(f"Respuesta de OpenAI no es JSON válido: {e}") from e


def _analizar_simulado(jpeg: bytes, producto: str) -> tuple[dict, str]:
    """Respuesta de ejemplo para desarrollo sin clave. No usar ante clientes."""
    time.sleep(1.5)
    nombre = PRODUCTOS.get(producto, PRODUCTOS["tomate"])["nombre"]
    if producto == "auto":
        nombre = "Tomate"
    return (
        {
            "producto_detectado": f"{nombre} (modo simulado)",
            "es_producto_agroalimentario": True,
            "categoria": "I",
            "puntuacion_calidad": 81,
            "madurez": {"estado": "Óptimo", "porcentaje": 68},
            "color": {"descripcion": "Rojo intenso con ligera zona más clara junto al cáliz", "uniformidad": 84},
            "defectos": [
                {
                    "tipo": "Roce superficial",
                    "severidad": "leve",
                    "zona": "Lateral derecho",
                    "descripcion": "Marca de roce que no afecta a la pulpa.",
                },
                {
                    "tipo": "Microgrieta",
                    "severidad": "moderado",
                    "zona": "Zona peduncular",
                    "descripcion": "Grieta concéntrica cicatrizada de unos 5 mm.",
                },
            ],
            "calibre_estimado": "No determinable sin referencia de escala",
            "destino_recomendado": "Mercado en fresco",
            "resumen": "Pieza sana con defectos menores de piel que la sitúan en Categoría I. "
            "Apta para mercado en fresco.",
            "confianza": 77,
            "advertencia": "Modo simulado: este informe no procede de un modelo real.",
        },
        "simulado",
    )


PROVEEDORES = {
    "anthropic": _analizar_anthropic,
    "openai": _analizar_openai,
    "simulado": _analizar_simulado,
}


def orden_proveedores() -> list[str]:
    principal = (config("PROVEEDOR", "anthropic") or "anthropic").strip().lower()
    if principal not in PROVEEDORES:
        principal = "anthropic"
    if principal == "simulado":
        return ["simulado"]
    respaldo = "openai" if principal == "anthropic" else "anthropic"
    orden = [principal]
    if config(f"{respaldo.upper()}_API_KEY"):
        orden.append(respaldo)
    return orden


def normalizar(inf: dict) -> dict:
    """Asegura tipos y rangos aunque el modelo se salga un poco del esquema."""

    def entero(v, defecto=0):
        try:
            return max(0, min(100, int(round(float(v)))))
        except (TypeError, ValueError):
            return defecto

    inf = dict(inf)
    inf["puntuacion_calidad"] = entero(inf.get("puntuacion_calidad"))
    inf["confianza"] = entero(inf.get("confianza"), 50)
    if inf.get("categoria") not in CATEGORIAS:
        inf["categoria"] = "No evaluable"
    mad = inf.get("madurez") or {}
    inf["madurez"] = {"estado": str(mad.get("estado", "No aplica")), "porcentaje": entero(mad.get("porcentaje"))}
    col = inf.get("color") or {}
    inf["color"] = {"descripcion": str(col.get("descripcion", "")), "uniformidad": entero(col.get("uniformidad"))}
    defectos = inf.get("defectos") or []
    inf["defectos"] = [d for d in defectos if isinstance(d, dict)]
    for k in ("producto_detectado", "calibre_estimado", "destino_recomendado", "resumen"):
        inf[k] = str(inf.get(k) or "")
    inf.setdefault("es_producto_agroalimentario", True)
    adv = inf.get("advertencia")
    inf["advertencia"] = adv if adv and str(adv).strip().lower() not in ("null", "none", "") else None
    return inf


def analizar(jpeg: bytes, producto: str) -> Resultado:
    """Llama al proveedor configurado con respaldo automático."""
    errores = []
    for nombre in orden_proveedores():
        t0 = time.time()
        try:
            informe, modelo = PROVEEDORES[nombre](jpeg, producto)
            return Resultado(normalizar(informe), nombre, modelo, time.time() - t0)
        except Exception as e:  # noqa: BLE001  se registra y se prueba el siguiente
            errores.append(f"{nombre}: {type(e).__name__}: {e}")
    raise ErrorAnalisis(" | ".join(errores))
