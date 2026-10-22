"""Tairel Data · Inspector de calidad con IA (demo para evento agroalimentario).

Ejecutar en local:  streamlit run app.py
"""

from __future__ import annotations

import base64
import html
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from calidad.analizador import (
    ErrorAnalisis,
    analizar,
    config,
    huella,
    orden_proveedores,
    paleta_dominante,
    preparar_imagen,
)
from calidad.productos import COLOR_CATEGORIA, PRODUCTOS, TEXTO_CATEGORIA

RAIZ = Path(__file__).parent
DIR_EJEMPLOS = RAIZ / "ejemplos"
LOGO = RAIZ / "assets" / "logo_tairel.png"

st.set_page_config(
    page_title="Inspector de calidad con IA · Tairel Data",
    page_icon=str(RAIZ / "assets" / "icono.png") if (RAIZ / "assets" / "icono.png").exists() else "🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Los secretos de Streamlit Cloud pasan a variables de entorno para que el hilo
# que llama a la API pueda leerlos sin depender del contexto de Streamlit.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float)):
            os.environ.setdefault(_k, str(_v))
except Exception:
    pass

LIMITE_SESION = int(config("LIMITE_POR_SESION", "12"))
LIMITE_HORA = int(config("LIMITE_GLOBAL_HORA", "400"))
EMAIL_CONTACTO = config("EMAIL_CONTACTO", "info@taireldata.com")
WEB_CONTACTO = config("WEB_CONTACTO", "https://taireldata.com")
FORMULARIO_LEADS = config("FORMULARIO_LEADS", "")

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------

st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --azul:#0054a4; --azul2:#0168cb; --azul3:#5c95ff; --magenta:#b4228d; --morado:#5c2e92;
  --gris:#f6f6f6; --texto:#1d2433; --suave:#5b6475; --borde:#e3e6ec;
}
html, body, [class*="css"], .stMarkdown, button, input, label { font-family:'Nunito',system-ui,sans-serif !important; }
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.block-container{padding-top:1rem; padding-bottom:3rem; max-width:760px;}
.hero{background:linear-gradient(135deg,var(--azul) 0%,var(--azul2) 55%,var(--azul3) 100%);
  color:#fff;border-radius:22px;padding:22px 22px 20px;margin:6px 0 18px;position:relative;overflow:hidden;}
.hero:after{content:"";position:absolute;right:-40px;top:-40px;width:160px;height:160px;border-radius:50%;
  background:radial-gradient(circle,rgba(180,34,141,.55),rgba(180,34,141,0) 70%);}
.hero h1{font-size:1.65rem;line-height:1.15;margin:0 0 6px;font-weight:800;color:#fff;}
.hero p{margin:0;opacity:.92;font-size:1rem;}
.chip{display:inline-block;background:rgba(255,255,255,.18);border-radius:999px;padding:3px 10px;
  font-size:.78rem;font-weight:700;letter-spacing:.02em;margin-bottom:10px;}
.paso{font-weight:800;color:var(--azul);font-size:1.05rem;margin:14px 0 4px;}
.paso span{display:inline-flex;width:24px;height:24px;border-radius:50%;background:var(--magenta);color:#fff;
  align-items:center;justify-content:center;font-size:.85rem;margin-right:8px;}
.tarjeta{background:#fff;border:1px solid var(--borde);border-radius:18px;padding:16px 18px;margin:10px 0;}
.veredicto{border-radius:18px;padding:18px;color:#fff;margin:10px 0 6px;}
.veredicto .cat{font-size:1.9rem;font-weight:800;line-height:1.1;}
.veredicto .prod{opacity:.95;font-weight:600;margin-top:2px;}
.veredicto .dest{margin-top:10px;background:rgba(255,255,255,.2);display:inline-block;border-radius:999px;
  padding:4px 12px;font-weight:700;font-size:.9rem;}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:10px 0;}
.kpi{background:#fff;border:1px solid var(--borde);border-radius:16px;padding:12px 10px;text-align:center;}
.kpi .v{font-size:1.5rem;font-weight:800;color:var(--azul);line-height:1.1;}
.kpi .l{font-size:.78rem;color:var(--suave);font-weight:600;margin-top:2px;}
.kpi .s{font-size:.8rem;color:var(--texto);font-weight:700;}
.barra{height:10px;border-radius:999px;background:#eceff4;overflow:hidden;margin:6px 0 2px;}
.barra > div{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--azul2),var(--magenta));}
.h3{font-weight:800;color:var(--texto);font-size:1.02rem;margin-bottom:8px;}
.defecto{border-left:5px solid #ccc;padding:8px 12px;margin:8px 0;background:var(--gris);border-radius:0 12px 12px 0;}
.defecto .t{font-weight:800;color:var(--texto);}
.defecto .m{font-size:.82rem;color:var(--suave);}
.sev{font-size:.72rem;font-weight:800;text-transform:uppercase;border-radius:999px;padding:2px 8px;color:#fff;margin-left:6px;}
.paleta{display:flex;height:34px;border-radius:10px;overflow:hidden;margin:8px 0 4px;border:1px solid var(--borde);}
.nota{font-size:.78rem;color:var(--suave);}
.aviso{background:#fff7e0;border:1px solid #f3d27a;border-radius:14px;padding:10px 14px;font-size:.9rem;margin:8px 0;}
.cta{background:linear-gradient(135deg,var(--morado),var(--magenta));color:#fff;border-radius:22px;padding:22px;margin:22px 0 10px;}
.cta h3{color:#fff;margin:0 0 8px;font-weight:800;font-size:1.3rem;}
.cta ul{margin:8px 0 0 0;padding-left:18px;} .cta li{margin:4px 0;}
.pie{text-align:center;color:var(--suave);font-size:.78rem;margin-top:24px;}
div.stButton > button[kind="primary"]{background:var(--magenta);border-color:var(--magenta);border-radius:14px;
  font-weight:800;padding:.65rem 1rem;font-size:1.05rem;}
div.stButton > button[kind="primary"]:hover{background:#9a1c78;border-color:#9a1c78;}
div.stButton > button{border-radius:12px;font-weight:700;}
[data-testid="stFileUploaderDropzone"]{border-radius:16px;border:2px dashed var(--azul3);background:#f3f7ff;}
img{border-radius:14px;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def esc(t) -> str:
    return html.escape(str(t or ""))


@st.cache_resource
def contador_global() -> dict:
    return {"inicio": time.time(), "n": 0}


def cupo_disponible() -> bool:
    c = contador_global()
    if time.time() - c["inicio"] > 3600:
        c["inicio"], c["n"] = time.time(), 0
    return c["n"] < LIMITE_HORA and st.session_state.get("usos", 0) < LIMITE_SESION


def registrar_uso() -> None:
    contador_global()["n"] += 1
    st.session_state["usos"] = st.session_state.get("usos", 0) + 1


@st.cache_data(show_spinner=False)
def cargar_ejemplos() -> tuple[list[dict], dict]:
    indice = DIR_EJEMPLOS / "ejemplos.json"
    if not indice.exists():
        return [], {}
    lista = json.loads(indice.read_text(encoding="utf-8"))
    lista = [e for e in lista if (DIR_EJEMPLOS / e["archivo"]).exists()]
    precalc = {}
    f = DIR_EJEMPLOS / "resultados.json"
    if f.exists():
        precalc = json.loads(f.read_text(encoding="utf-8"))
    return lista, precalc


@st.cache_data(show_spinner=False, max_entries=1000)
def analizar_cacheado(jpeg: bytes, producto: str) -> dict:
    r = analizar(jpeg, producto)
    return {"informe": r.informe, "proveedor": r.proveedor, "modelo": r.modelo, "segundos": r.segundos}


ETAPAS = [
    "Corrigiendo orientación y normalizando la imagen…",
    "Identificando el producto…",
    "Midiendo color y madurez…",
    "Buscando defectos de piel y forma…",
    "Asignando categoría comercial…",
    "Redactando el informe de calidad…",
]


def ejecutar_analisis(jpeg: bytes, producto: str) -> dict:
    """Lanza el análisis en un hilo y anima una barra de progreso mientras tanto."""
    barra = st.progress(0, text=ETAPAS[0])
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(analizar_cacheado, jpeg, producto)
        t0, i = time.time(), 0
        while not fut.done():
            transcurrido = time.time() - t0
            avance = min(0.92, 1 - 1 / (1 + transcurrido / 3))  # se acerca a 92 % sin llegar
            i = min(len(ETAPAS) - 1, int(transcurrido / 1.4))
            barra.progress(avance, text=ETAPAS[i])
            time.sleep(0.15)
        res = fut.result()  # propaga excepciones
    barra.progress(1.0, text="Informe listo")
    time.sleep(0.25)
    barra.empty()
    return res


def lanzar(jpeg_original: bytes, producto: str, precalculado: dict | None = None) -> None:
    jpeg, img = preparar_imagen(jpeg_original)
    st.session_state["imagen"] = jpeg
    st.session_state["paleta"] = paleta_dominante(img)
    st.session_state["error"] = None
    if precalculado:
        with st.spinner("Analizando…"):
            time.sleep(1.2)  # ritmo natural también en los ejemplos
        st.session_state["resultado"] = precalculado
        st.session_state["desplazar"] = True
        return
    if not cupo_disponible():
        st.session_state["resultado"] = None
        st.session_state["error"] = (
            "Has alcanzado el número máximo de análisis de esta demo. "
            "¡Pásate por nuestro stand y lo vemos en directo!"
        )
        return
    try:
        st.session_state["resultado"] = ejecutar_analisis(jpeg, producto)
        st.session_state["desplazar"] = True
        registrar_uso()
    except ErrorAnalisis as e:
        print("ERROR análisis:", e, flush=True)
        st.session_state["resultado"] = None
        st.session_state["error"] = (
            "No hemos podido analizar la imagen ahora mismo (la red del evento a veces se satura). "
            "Prueba de nuevo en unos segundos o elige una imagen de ejemplo."
        )


# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------

if LOGO.exists():
    st.image(str(LOGO), width=220)

st.markdown(
    """
<div class="hero">
  <div class="chip">DEMO EN DIRECTO · VISIÓN ARTIFICIAL</div>
  <h1>Inspector de calidad con IA</h1>
  <p>Haz una foto a una fruta, hortaliza o muestra de grano y obtén en segundos su categoría
  comercial, madurez y defectos.</p>
</div>
""",
    unsafe_allow_html=True,
)

for k, v in {"imagen": None, "resultado": None, "error": None, "paleta": None, "usos": 0}.items():
    st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# Paso 1: producto
# ---------------------------------------------------------------------------

st.markdown('<div class="paso"><span>1</span>¿Qué producto vas a analizar?</div>', unsafe_allow_html=True)
claves = list(PRODUCTOS.keys())
etiquetas = {k: f"{PRODUCTOS[k]['icono']} {PRODUCTOS[k]['nombre']}" for k in claves}
if hasattr(st, "pills"):
    producto = st.pills(
        "Producto", claves, default="auto", format_func=etiquetas.get, label_visibility="collapsed"
    ) or "auto"
else:
    producto = st.selectbox("Producto", claves, format_func=etiquetas.get, label_visibility="collapsed")

# ---------------------------------------------------------------------------
# Paso 2: imagen
# ---------------------------------------------------------------------------

st.markdown('<div class="paso"><span>2</span>Haz una foto o prueba un ejemplo</div>', unsafe_allow_html=True)
ejemplos, precalculados = cargar_ejemplos()
pestanas = st.tabs(["📷 Tu foto", "🖼️ Ejemplos"] if ejemplos else ["📷 Tu foto"])

with pestanas[0]:
    archivo = st.file_uploader(
        "Toca para hacer una foto o elegir una imagen",
        type=["jpg", "jpeg", "png", "webp"],
        help="En el móvil puedes usar directamente la cámara trasera.",
    )
    usar_camara = st.toggle("Usar la cámara en directo", value=False)
    captura = st.camera_input("Cámara", label_visibility="collapsed") if usar_camara else None
    fuente = captura or archivo
    if fuente is not None:
        st.image(fuente, use_container_width=True)
    st.caption("Consejo: una sola pieza, buena luz y fondo liso dan los mejores resultados.")
    if st.button("Analizar calidad", type="primary", use_container_width=True, disabled=fuente is None):
        try:
            lanzar(fuente.getvalue(), producto)
        except Exception as e:  # imagen corrupta o formato no soportado
            print("ERROR imagen:", e, flush=True)
            st.session_state["resultado"] = None
            st.session_state["error"] = "No hemos podido leer esa imagen. Prueba con una foto en JPG o PNG."

if ejemplos:
    with pestanas[1]:
        st.caption("Imágenes reales de producto con distintos niveles de calidad.")
        cols = st.columns(2)
        for i, e in enumerate(ejemplos):
            with cols[i % 2]:
                ruta = DIR_EJEMPLOS / e["archivo"]
                st.image(str(ruta), use_container_width=True)
                if st.button(e["titulo"], key=f"ej_{i}", use_container_width=True):
                    datos = ruta.read_bytes()
                    jpeg, _ = preparar_imagen(datos)
                    prod = e.get("producto", "auto")
                    lanzar(datos, prod, precalculados.get(huella(jpeg, prod)))

# ---------------------------------------------------------------------------
# Paso 3: informe
# ---------------------------------------------------------------------------

if st.session_state["error"]:
    st.markdown(f'<div class="aviso">{esc(st.session_state["error"])}</div>', unsafe_allow_html=True)

res = st.session_state["resultado"]
if res:
    inf = res["informe"]
    st.markdown('<div id="informe" class="paso"><span>3</span>Informe de calidad</div>', unsafe_allow_html=True)
    if st.session_state.pop("desplazar", False):
        # En el móvil el informe queda debajo de la galería: lo traemos a la vista.
        components.html(
            "<script>setTimeout(function(){var e=window.parent.document.getElementById('informe');"
            "if(e){e.scrollIntoView({behavior:'smooth',block:'start'});}},300);</script>",
            height=0,
        )

    cat = inf["categoria"]
    color_cat = COLOR_CATEGORIA.get(cat, "#6b6b6b")
    st.markdown(
        f"""
<div class="veredicto" style="background:linear-gradient(135deg,{color_cat},{color_cat}cc);">
  <div class="cat">{esc(TEXTO_CATEGORIA.get(cat, cat))}</div>
  <div class="prod">{esc(inf['producto_detectado'])}</div>
  <div class="dest">Destino: {esc(inf['destino_recomendado'])}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if inf.get("advertencia"):
        st.markdown(f'<div class="aviso">⚠️ {esc(inf["advertencia"])}</div>', unsafe_allow_html=True)

    mad = inf["madurez"]
    st.markdown(
        f"""
<div class="kpis">
  <div class="kpi"><div class="v">{inf['puntuacion_calidad']}</div><div class="l">Calidad / 100</div></div>
  <div class="kpi"><div class="s">{esc(mad['estado'])}</div><div class="v">{mad['porcentaje']}%</div><div class="l">Madurez</div></div>
  <div class="kpi"><div class="v">{inf['confianza']}%</div><div class="l">Confianza</div></div>
</div>
<div class="tarjeta"><div class="h3">Resumen del inspector</div>{esc(inf['resumen'])}
  <div class="barra"><div style="width:{inf['puntuacion_calidad']}%"></div></div>
  <div class="nota">Índice de calidad global</div>
</div>
""",
        unsafe_allow_html=True,
    )

    col_img, col_def = st.columns([1, 1.25])
    with col_img:
        if st.session_state["imagen"]:
            st.image(st.session_state["imagen"], use_container_width=True)
    with col_def:
        sev_color = {"leve": "#e0a100", "moderado": "#ef6c00", "grave": "#c62828"}
        defectos = inf["defectos"]
        if defectos:
            items = "".join(
                f"""<div class="defecto" style="border-left-color:{sev_color.get(d.get('severidad'), '#999')}">
<div class="t">{esc(d.get('tipo'))}<span class="sev" style="background:{sev_color.get(d.get('severidad'), '#999')}">{esc(d.get('severidad'))}</span></div>
<div class="m">{esc(d.get('zona'))}</div><div>{esc(d.get('descripcion'))}</div></div>"""
                for d in defectos
            )
            titulo = f"Defectos detectados ({len(defectos)})"
        else:
            items = '<div class="defecto" style="border-left-color:#1a8f4c"><div class="t">Sin defectos visibles</div></div>'
            titulo = "Defectos detectados"
        st.markdown(f'<div class="tarjeta"><div class="h3">{titulo}</div>{items}</div>', unsafe_allow_html=True)

    paleta = st.session_state.get("paleta") or []
    franjas = "".join(f'<div style="background:{c};flex:{p:.3f}"></div>' for c, p in paleta)
    st.markdown(
        f"""
<div class="tarjeta"><div class="h3">Color</div>
  {esc(inf['color']['descripcion'])}
  <div class="paleta">{franjas}</div>
  <div class="nota">Colores dominantes de la imagen (cálculo local) · Uniformidad estimada: {inf['color']['uniformidad']}%</div>
  <div style="margin-top:10px"><b>Calibre:</b> {esc(inf['calibre_estimado'])}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    origen = "resultado precalculado" if res.get("proveedor") == "precalculado" else f"{res.get('segundos', 0):.1f} s"
    st.markdown(
        f'<div class="nota">Análisis generado por IA ({esc(origen)}). Estimación orientativa a partir de una sola imagen; '
        "un sistema en planta se entrena y valida con vuestros propios datos y criterios.</div>",
        unsafe_allow_html=True,
    )

    if st.button("↺ Analizar otra imagen", use_container_width=True):
        st.session_state["resultado"] = None
        st.session_state["imagen"] = None
        st.rerun()

# ---------------------------------------------------------------------------
# Llamada a la acción
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="cta">
  <h3>¿Y si esto funcionara en tu línea?</h3>
  Esta demo usa una sola foto. En planta, en Tairel Data lo llevamos mucho más lejos:
  <ul>
    <li>Cámaras industriales sobre cinta, inspeccionando cada pieza en tiempo real.</li>
    <li>Modelos entrenados con tus productos, tus defectos y tus categorías.</li>
    <li>IA en el borde (edge): funciona en la planta, sin depender de internet.</li>
    <li>Integración con tu ERP/MES: trazabilidad por lote y datos para decidir.</li>
  </ul>
</div>
""",
    unsafe_allow_html=True,
)
c1, c2 = st.columns(2)
with c1:
    st.link_button("✉️ Escríbenos", f"mailto:{EMAIL_CONTACTO}?subject=Demo%20visi%C3%B3n%20artificial", use_container_width=True)
with c2:
    if FORMULARIO_LEADS:
        st.link_button("📅 Quiero una reunión", FORMULARIO_LEADS, use_container_width=True, type="primary")
    else:
        st.link_button("🌐 taireldata.com", WEB_CONTACTO, use_container_width=True)

st.markdown(
    '<div class="pie">Tairel Data · Spin-off de la Universidad Pública de Navarra<br>'
    "Las imágenes se procesan solo para generar el informe y no se almacenan.</div>",
    unsafe_allow_html=True,
)

if config("MOSTRAR_DIAGNOSTICO", "0") == "1":
    with st.expander("Diagnóstico (solo equipo)"):
        st.write({"proveedores": orden_proveedores(), "usos_globales_hora": contador_global()["n"]})
