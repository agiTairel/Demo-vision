"""Tairel Data · Demo IA para el campo (evento agroalimentario).

Recorrido:
  1. Bienvenida: qué es la demo y registro (correo, nombre, empresa opcional).
  2. Tus campos: cuántos, de qué cultivo y en qué comarca de Navarra.
  3. Fotos: como agricultor, envía una foto de cada campo; la IA detecta plagas y enfermedades.
  4. Previsión: la previsión de campaña (demo de previsión) con lo que dicen las fotos.

Ejecutar en local:  streamlit run app.py
"""

from __future__ import annotations

import html
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from calidad.analizador import ErrorAnalisis, config, huella, orden_proveedores, preparar_imagen
from calidad.estilo import CSS
from calidad.leads import email_valido, guardar_lead
from calidad.prevision import html_prevision
from calidad.sanidad import (
    COMARCAS,
    CULTIVOS,
    FOTOS_CAMPO,
    analizar_sanidad,
    comarca_tipica,
    peso_cultivo,
)

RAIZ = Path(__file__).parent
DIR_FOTOS = RAIZ / "ejemplos" / "campos"
LOGO = RAIZ / "assets" / "logo_tairel.png"
ICONO = RAIZ / "assets" / "icono.png"
MAX_CAMPOS = 4

PASO = st.session_state.get("paso", "bienvenida")

st.set_page_config(
    page_title="IA para el campo · Tairel Data",
    page_icon=str(ICONO) if ICONO.exists() else "🌱",
    layout="wide" if PASO == "prevision" else "centered",
    initial_sidebar_state="collapsed",
)

# Los secretos pasan a variables de entorno para que el hilo que llama a la API los lea.
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

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    """
<style>
.bienvenida{background:var(--blanco);border:1px solid var(--linea);border-radius:24px;padding:22px 20px;margin:8px 0 14px;
  box-shadow:0 10px 30px rgba(31,42,31,.08);}
.bienvenida h2{font-weight:800;color:var(--tinta);margin:0 0 6px;font-size:1.35rem;}
.bienvenida ol{margin:10px 0 0;padding-left:20px;color:var(--tinta-2);} .bienvenida li{margin:5px 0;}
.pasos{display:flex;gap:6px;margin:4px 0 14px;}
.pasos span{flex:1;height:6px;border-radius:999px;background:var(--linea);}
.pasos span.on{background:var(--hoja);} .pasos span.hecho{background:#9cc58a;}
.campo-cab{display:flex;align-items:center;gap:10px;font-weight:800;color:var(--tinta);font-size:1.05rem;margin:4px 0 2px;}
.campo-cab .num{display:inline-flex;width:28px;height:28px;border-radius:50%;background:var(--trigo);color:var(--tinta);
  align-items:center;justify-content:center;font-size:.9rem;}
.estado{border-radius:18px;padding:16px 18px;color:#fff;margin:10px 0 6px;}
.estado .t{font-family:var(--f-cifra) !important;font-stretch:76%;font-size:2rem;font-weight:800;line-height:1.05;}
.estado .s{opacity:.95;font-weight:600;margin-top:2px;}
.reco{margin:6px 0 0;padding-left:18px;} .reco li{margin:4px 0;}
.resumen-campos{display:grid;gap:8px;margin:8px 0;}
.rc{display:flex;gap:10px;align-items:center;background:var(--blanco);border:1px solid var(--linea);border-radius:14px;padding:10px 12px;}
.rc .b{width:12px;height:12px;border-radius:50%;flex:0 0 12px;}
.rc small{color:var(--tinta-3);display:block;}
</style>
""",
    unsafe_allow_html=True,
)
if PASO == "prevision":
    st.markdown(
        "<style>.block-container{max-width:1400px;padding-left:1rem;padding-right:1rem;}"
        "iframe{border-radius:16px;border:1px solid var(--linea) !important;background:#fbfbf6;}</style>",
        unsafe_allow_html=True,
    )

COLOR_ESTADO = {
    "Sano": "#2a7230",
    "Incidencia leve": "#9a6a00",
    "Incidencia moderada": "#c0611f",
    "Incidencia grave": "#b3361f",
    "No evaluable": "#566354",
}
SEV_COLOR = {"leve": "#e2ac24", "moderada": "#9a6a00", "grave": "#b3361f"}
ETAPAS = [
    "Recibiendo la foto del agricultor…",
    "Identificando el cultivo…",
    "Buscando síntomas en hojas, tallos y frutos…",
    "Comparando con plagas y enfermedades de la zona…",
    "Estimando la superficie afectada…",
    "Calculando la pérdida de cosecha…",
]

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def esc(t) -> str:
    return html.escape(str(t or ""))


def ir(paso: str) -> None:
    st.session_state["paso"] = paso
    st.rerun()


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
def precalculados() -> dict:
    f = DIR_FOTOS / "resultados.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def fotos_de(cultivo: str) -> list[tuple[Path, str]]:
    return [(DIR_FOTOS / a, t) for a, t in FOTOS_CAMPO.get(cultivo, []) if (DIR_FOTOS / a).exists()]


@st.cache_data(show_spinner=False, max_entries=1000)
def analizar_cacheado(jpeg: bytes, cultivo: str, comarca: str) -> dict:
    r = analizar_sanidad(jpeg, cultivo, comarca)
    return {"informe": r.informe, "proveedor": r.proveedor, "segundos": r.segundos}


def ejecutar_con_progreso(jpeg: bytes, cultivo: str, comarca: str) -> dict:
    barra = st.progress(0, text=ETAPAS[0])
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(analizar_cacheado, jpeg, cultivo, comarca)
        t0 = time.time()
        while not fut.done():
            tr = time.time() - t0
            barra.progress(min(0.92, 1 - 1 / (1 + tr / 3)), text=ETAPAS[min(len(ETAPAS) - 1, int(tr / 1.4))])
            time.sleep(0.15)
        res = fut.result()
    barra.progress(1.0, text="Informe listo")
    time.sleep(0.25)
    barra.empty()
    return res


def analizar_campo(i: int, datos: bytes) -> None:
    """Analiza la foto del campo i y guarda el resultado en la sesión."""
    campo = st.session_state["campos"][i]
    try:
        jpeg, _ = preparar_imagen(datos)
    except Exception as e:  # noqa: BLE001
        print("ERROR imagen:", e, flush=True)
        st.session_state["error"] = "No hemos podido leer esa imagen. Prueba con una foto en JPG o PNG."
        return
    campo["foto"] = jpeg
    st.session_state["error"] = None
    pre = precalculados().get(huella(jpeg, "sanidad:" + campo["cultivo"]))
    if pre:
        with st.spinner("Analizando la foto…"):
            time.sleep(1.2)
        campo["informe"] = pre["informe"]
        return
    if not cupo_disponible():
        st.session_state["error"] = "Has alcanzado el número máximo de análisis de esta demo. ¡Pásate por nuestro stand!"
        return
    try:
        res = ejecutar_con_progreso(jpeg, campo["cultivo"], campo["comarca"])
        campo["informe"] = res["informe"]
        registrar_uso()
    except ErrorAnalisis as e:
        print("ERROR análisis:", e, flush=True)
        st.session_state["error"] = (
            "No hemos podido analizar la foto ahora mismo (la red del evento a veces se satura). "
            "Prueba de nuevo en unos segundos."
        )


def cabecera(paso_n: int | None = None) -> None:
    if LOGO.exists():
        st.image(str(LOGO), width=200)
    if paso_n is not None:
        st.markdown(
            '<div class="pasos">' + "".join(
                f'<span class="{"on" if k == paso_n else "hecho" if k < paso_n else ""}"></span>' for k in range(1, 4)
            ) + "</div>",
            unsafe_allow_html=True,
        )


def pie() -> None:
    st.markdown(
        '<div class="pie">Tairel Data · Spin-off de la Universidad Pública de Navarra<br>'
        "Las fotos se procesan solo para generar el informe y no se almacenan.</div>",
        unsafe_allow_html=True,
    )


for k, v in {"campos": [], "campo_actual": 0, "error": None, "usos": 0, "usuario": None}.items():
    st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# 1. Bienvenida y registro
# ---------------------------------------------------------------------------

if PASO == "bienvenida":
    cabecera()
    st.markdown(
        """
<div class="hero">
  <div class="chip">DEMO DE TAIREL DATA · IA PARA EL CAMPO</div>
  <h1>De la foto de tu campo a la previsión de tu campaña</h1>
  <p>Una demo interactiva de cómo la inteligencia artificial ayuda a cooperativas y empresas agroalimentarias de Navarra.</p>
</div>
<div class="bienvenida">
  <h2>¿Qué vas a probar?</h2>
  <ol>
    <li>Configuras tu explotación: cuántos campos, qué cultivas y en qué comarca.</li>
    <li>Como agricultor, envías una foto de cada campo y la IA detecta plagas y enfermedades.</li>
    <li>Ves cómo afecta a la previsión de ventas, costes y margen de la campaña.</li>
  </ol>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="h3">Para empezar, déjanos tus datos</div>', unsafe_allow_html=True)
    with st.form("registro", border=False):
        email = st.text_input("Correo electrónico *", placeholder="nombre@empresa.com")
        nombre = st.text_input("Nombre *")
        empresa = st.text_input("Empresa (opcional)")
        acepto = st.checkbox("Acepto que Tairel Data me contacte por correo o teléfono para informarme sobre sus servicios.")
        st.markdown(
            f'<div class="nota">Responsable: Tairel Data, S.L. Usaremos tus datos solo para este contacto y no los '
            f"cederemos a terceros. Puedes pedir su acceso o borrado en {esc(EMAIL_CONTACTO)}.</div>",
            unsafe_allow_html=True,
        )
        enviar = st.form_submit_button("Probar demo", type="primary", use_container_width=True)
    if enviar:
        if not email_valido(email or ""):
            st.error("Revisa el correo electrónico, parece que no es válido.")
        elif not (nombre or "").strip():
            st.error("Dinos tu nombre para personalizar la demo.")
        elif not acepto:
            st.error("Necesitamos tu consentimiento para poder contactarte.")
        else:
            guardar_lead(email, nombre, empresa or "", acepto, producto="Demo campo + previsión", categoria="")
            st.session_state["usuario"] = {"email": email.strip(), "nombre": nombre.strip(), "empresa": (empresa or "").strip()}
            ir("campos")
    pie()

# ---------------------------------------------------------------------------
# 2. Tus campos
# ---------------------------------------------------------------------------

elif PASO == "campos":
    cabecera(1)
    nombre = (st.session_state.get("usuario") or {}).get("nombre", "")
    st.markdown(
        f'<div class="paso"><span>1</span>Tu explotación{", " + esc(nombre.split()[0]) if nombre else ""}</div>'
        '<div class="nota">Elige cuántos campos quieres en tu demo, qué cultivas en cada uno y dónde está.</div>',
        unsafe_allow_html=True,
    )
    opciones_n = list(range(1, MAX_CAMPOS + 1))
    n_defecto = len(st.session_state["campos"]) or 3
    if hasattr(st, "pills"):
        n = st.pills("¿Cuántos campos?", opciones_n, default=n_defecto,
                     format_func=lambda x: f"{x} campo" + ("s" if x > 1 else "")) or n_defecto
    else:
        n = st.radio("¿Cuántos campos?", opciones_n, index=n_defecto - 1, horizontal=True)

    claves_c = list(CULTIVOS)
    claves_z = list(COMARCAS)
    sugeridos = ["lechuga", "trigo", "brocoli", "maiz"]
    for i in range(n):
        previo = st.session_state["campos"][i] if i < len(st.session_state["campos"]) else {}
        cult_def = previo.get("cultivo", sugeridos[i % len(sugeridos)])
        st.markdown(f'<div class="campo-cab" style="margin-top:18px"><span class="num">{i + 1}</span>Campo {i + 1}</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            cultivo = st.selectbox(
                "Cultivo", claves_c, index=claves_c.index(cult_def), key=f"cult_{i}",
                format_func=lambda k: f"{CULTIVOS[k]['icono']} {CULTIVOS[k]['nombre']} · {CULTIVOS[k]['linea']}",
            )
        with c2:
            if f"zona_{i}" not in st.session_state:
                st.session_state[f"zona_{i}"] = previo.get("comarca", comarca_tipica(cultivo))
            comarca = st.selectbox(
                "Comarca de Navarra", claves_z, key=f"zona_{i}",
                format_func=lambda z, c=cultivo: f"{COMARCAS[z]['nombre']} · {peso_cultivo(c, z)}",
            )
        st.caption(f"Pueblos de referencia: {COMARCAS[comarca]['pueblos']}")

    if st.button("Continuar: enviar fotos de mis campos", type="primary", use_container_width=True):
        nuevos = []
        for i in range(n):
            cult, zona = st.session_state[f"cult_{i}"], st.session_state[f"zona_{i}"]
            previo = st.session_state["campos"][i] if i < len(st.session_state["campos"]) else {}
            mismo = previo.get("cultivo") == cult and previo.get("comarca") == zona
            nuevos.append({"cultivo": cult, "comarca": zona, "informe": previo.get("informe") if mismo else None,
                           "foto": previo.get("foto") if mismo else None})
        st.session_state["campos"] = nuevos
        st.session_state["campo_actual"] = 0
        st.session_state["error"] = None
        ir("fotos")
    pie()

# ---------------------------------------------------------------------------
# 3. Fotos de cada campo
# ---------------------------------------------------------------------------

elif PASO == "fotos":
    campos = st.session_state["campos"]
    if not campos:
        ir("campos")
    i = min(st.session_state["campo_actual"], len(campos) - 1)
    campo = campos[i]
    cult, zona = CULTIVOS[campo["cultivo"]], COMARCAS[campo["comarca"]]
    cabecera(2)
    st.markdown(
        f'<div class="paso"><span>2</span>Campo {i + 1} de {len(campos)}: {cult["icono"]} {esc(cult["nombre"])} en {esc(zona["nombre"])}</div>'
        '<div class="nota">Eres el agricultor: envía a tu cooperativa una foto de cómo está la cosecha.</div>',
        unsafe_allow_html=True,
    )

    inf = campo.get("informe")
    if not inf:
        fotos = fotos_de(campo["cultivo"])
        pestanas = st.tabs(["🖼️ Elegir una foto", "📷 Hacer o subir foto"] if fotos else ["📷 Hacer o subir foto"])
        if fotos:
            with pestanas[0]:
                cols = st.columns(2)
                for k, (ruta, titulo) in enumerate(fotos):
                    with cols[k % 2]:
                        st.image(str(ruta), use_container_width=True)
                        if st.button(f"Enviar: {titulo}", key=f"foto_{i}_{k}", use_container_width=True):
                            analizar_campo(i, ruta.read_bytes())
                            st.rerun()
        with pestanas[-1]:
            if not fotos:
                st.caption("Haz una foto a una hoja, planta o muestra de este cultivo, o sube una que tengas.")
            archivo = st.file_uploader("Toca para hacer una foto o elegir una imagen", type=["jpg", "jpeg", "png", "webp"],
                                       key=f"subir_{i}")
            camara = st.camera_input("Cámara", key=f"cam_{i}", label_visibility="collapsed") if st.toggle(
                "Usar la cámara en directo", key=f"tcam_{i}") else None
            fuente = camara or archivo
            if fuente is not None:
                st.image(fuente, use_container_width=True)
            if st.button("Enviar foto y analizar", type="primary", use_container_width=True, disabled=fuente is None,
                         key=f"enviar_{i}"):
                analizar_campo(i, fuente.getvalue())
                st.rerun()
        if st.session_state.get("error"):
            st.markdown(f'<div class="aviso">{esc(st.session_state["error"])}</div>', unsafe_allow_html=True)
        if st.button("Saltar este campo", key=f"saltar_{i}"):
            if i + 1 < len(campos):
                st.session_state["campo_actual"] = i + 1
                st.rerun()
            else:
                ir("prevision")
    else:
        color = COLOR_ESTADO.get(inf["estado"], "#566354")
        st.markdown(
            f'<div class="estado" style="background:linear-gradient(135deg,{color},{color}cc)">'
            f'<div class="t">{esc(inf["estado"])}</div><div class="s">{esc(inf["cultivo_detectado"])}</div></div>',
            unsafe_allow_html=True,
        )
        if inf.get("advertencia"):
            st.markdown(f'<div class="aviso">⚠️ {esc(inf["advertencia"])}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="kpis">
  <div class="kpi"><div class="v cifra">{inf['perdida_cosecha_pct']}%</div><div class="l">Pérdida de cosecha estimada</div></div>
  <div class="kpi"><div class="v cifra">{inf['indice_incidencia']}</div><div class="l">Índice de incidencia / 100</div></div>
  <div class="kpi"><div class="s">{esc(inf['riesgo_propagacion'])}</div><div class="l">Riesgo de propagación</div></div>
</div>
<div class="tarjeta"><div class="h3">Diagnóstico</div>{esc(inf['resumen'])}</div>
""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 1.3])
        with c1:
            if campo.get("foto"):
                st.image(campo["foto"], use_container_width=True)
        with c2:
            if inf["incidencias"]:
                items = "".join(
                    f'<div class="defecto" style="border-left-color:{SEV_COLOR.get(d["severidad"], "#999")}">'
                    f'<div class="t">{esc(d.get("nombre"))}<span class="sev" style="background:{SEV_COLOR.get(d["severidad"], "#999")};'
                    f'color:{"#1f2a1f" if d["severidad"] == "leve" else "#fff"}">{esc(d["severidad"])}</span></div>'
                    f'<div class="m">{esc(d.get("tipo"))} · {esc(d.get("agente"))} · {d["superficie_afectada_pct"]} % afectado</div>'
                    f'<div>{esc(d.get("sintomas"))}</div></div>'
                    for d in inf["incidencias"]
                )
            else:
                items = '<div class="defecto" style="border-left-color:#2a7230"><div class="t">Sin plagas ni enfermedades visibles</div></div>'
            st.markdown(f'<div class="tarjeta"><div class="h3">Qué se ve en la foto</div>{items}</div>', unsafe_allow_html=True)
        if inf["recomendaciones"]:
            st.markdown(
                '<div class="tarjeta"><div class="h3">Qué haría el técnico</div><ul class="reco">'
                + "".join(f"<li>{esc(r)}</li>" for r in inf["recomendaciones"]) + "</ul></div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="nota">Diagnóstico visual orientativo generado por IA a partir de una foto. '
            "En un proyecto real se valida con vuestros técnicos y vuestros datos de campo.</div>",
            unsafe_allow_html=True,
        )
        ultimo = i + 1 >= len(campos)
        if st.button("Ver la previsión de mi campaña →" if ultimo else f"Siguiente: campo {i + 2} →",
                     type="primary", use_container_width=True):
            if ultimo:
                ir("prevision")
            st.session_state["campo_actual"] = i + 1
            st.rerun()
        if st.button("↺ Enviar otra foto de este campo", use_container_width=True):
            campo["informe"], campo["foto"] = None, None
            st.rerun()

    if i > 0 and st.button("← Campo anterior"):
        st.session_state["campo_actual"] = i - 1
        st.rerun()
    pie()

# ---------------------------------------------------------------------------
# 4. Previsión de campaña con lo que dicen las fotos
# ---------------------------------------------------------------------------

elif PASO == "prevision":
    campos = st.session_state["campos"]
    if not campos:
        ir("campos")
    c1, c2 = st.columns([3, 1])
    with c1:
        cabecera(3)
        st.markdown(
            '<div class="paso"><span>3</span>Tu previsión de campaña</div>'
            '<div class="nota">Ventas, costes y margen a 12 meses de tus cultivos. Las plagas y enfermedades de tus fotos '
            'ya están aplicadas en el escenario «Según tus fotos»; mueve cualquier factor para ver qué pasa.</div>',
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("← Volver a mis campos", use_container_width=True):
            st.session_state["campo_actual"] = 0
            ir("fotos")
    filas = []
    for k, c in enumerate(campos, start=1):
        inf = c.get("informe") or {}
        col = COLOR_ESTADO.get(inf.get("estado"), "#7d8a78")
        incs = ", ".join(d["nombre"] for d in inf.get("incidencias", [])) or ("sin daños visibles" if inf else "sin foto")
        filas.append(
            f'<div class="rc"><span class="b" style="background:{col}"></span><div><b>Campo {k} · '
            f'{esc(CULTIVOS[c["cultivo"]]["nombre"])}</b><small>{esc(COMARCAS[c["comarca"]]["nombre"])} · {esc(incs)}'
            f'{" · pérdida " + str(inf.get("perdida_cosecha_pct", 0)) + " %" if inf else ""}</small></div></div>'
        )
    st.markdown('<div class="resumen-campos">' + "".join(filas) + "</div>", unsafe_allow_html=True)

    components.html(html_prevision(campos), height=2600, scrolling=True)

    st.markdown(
        """
<div class="cta">
  <h3>¿Lo vemos con tus datos?</h3>
  Esta demo usa datos de ejemplo. Con los tuyos, en Tairel Data construimos:
  <ul>
    <li>Detección de plagas y enfermedades con fotos de campo, drones o cámaras en planta.</li>
    <li>Previsión de ventas, costes y cosecha entrenada con tu histórico y el clima de tu zona.</li>
    <li>Alertas por comarca y conexión con tu ERP para decidir compras, turnos y stock.</li>
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )
    b1, b2, b3 = st.columns(3)
    with b1:
        st.link_button("✉️ Escríbenos", f"mailto:{EMAIL_CONTACTO}?subject=Demo%20IA%20para%20el%20campo", use_container_width=True)
    with b2:
        st.link_button("🌐 taireldata.com", WEB_CONTACTO, use_container_width=True)
    with b3:
        if st.button("↺ Empezar otra demo", use_container_width=True):
            usuario = st.session_state.get("usuario")
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state["usuario"] = usuario
            ir("campos" if usuario else "bienvenida")
    pie()

if config("MOSTRAR_DIAGNOSTICO", "0") == "1":
    with st.expander("Diagnóstico (solo equipo)"):
        st.write({"paso": PASO, "proveedores": orden_proveedores(), "usos_globales_hora": contador_global()["n"],
                  "hoja_leads_configurada": bool(config("LEADS_WEBHOOK_URL", ""))})
