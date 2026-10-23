"""Control y gestión de documentación (parte de Irati).

Con lo que ha hecho el visitante en la demo (sus campos y el diagnóstico de cada foto):
  1. busca antecedentes de cada incidencia en el histórico de campañas,
  2. genera su FICHA DE INCIDENCIA (un PDF con identificador trazable, una sección por campo)
     y su DOSSIER RESUMEN (PDF),
  3. se los pasa a la previsión (prevision/index.html). Al pulsar «Descargar mi informe», la página los sube
     a Google Drive junto con el informe de costes (la previsión de Ainhoa) a través del Apps Script de los
     leads, que guarda los tres links en la fila del visitante. A las 8:00 del día siguiente se envía el correo.

La incidencia del agricultor son sus campos (cuántos, qué cultivo y dónde) y, si sube foto, su análisis.
Sin foto no hay análisis: la ficha recoge solo los campos.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean

from .sanidad import COMARCAS, CULTIVOS

DATOS = Path(__file__).resolve().parent / "datos" / "historico_plagas.json"

# Horas de trabajo técnico que costaría hacer esto a mano (estimación orientativa)
TRABAJO_MANUAL = [
    ("Visitar los campos y revisar el estado de cada uno", 1.5, 35, "por campo"),
    ("Diagnosticar plagas y enfermedades y redactar la ficha", 1.0, 40, "por campo"),
    ("Buscar antecedentes en partes, boletines y campañas anteriores", 4.0, 35, None),
    ("Recalcular la previsión de cosecha, costes y margen", 6.0, 45, None),
    ("Preparar y enviar el informe", 2.0, 40, None),
]
DIAS_REACCION_MANUAL = 5


def sin_tildes(s) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


@lru_cache(maxsize=1)
def historico() -> dict:
    return json.loads(DATOS.read_text(encoding="utf-8"))


def identificar_plaga(cultivo: str, *textos: str) -> str | None:
    """Relaciona el nombre que da la IA (p. ej. «Roya amarilla», «Puccinia striiformis») con el histórico."""
    t = " ".join(sin_tildes(x) for x in textos if x)
    mejor, largo = None, 0
    for nombre, p in (historico()["plagas"].get(cultivo) or {}).items():
        for s in p["sinonimos"]:
            s = sin_tildes(s)
            if re.search(r"(^|[^a-z])" + re.escape(s) + r"([^a-z]|$)", t) and len(s) > largo:
                mejor, largo = nombre, len(s)
    return mejor


def antecedentes(cultivo: str, plaga: str | None) -> dict | None:
    """Cómo ha afectado esta plaga a este cultivo en las últimas campañas (histórico de la demo)."""
    if not plaga:
        return None
    serie = [r for r in historico()["registros"] if r["cultivo"] == cultivo and r["plaga"] == plaga]
    if not serie:
        return None
    af = [r for r in serie if r["incidencia"]]
    sanas = [r for r in serie if not r["incidencia"]]
    p_sano = mean(r["precio_medio_eur_kg"] for r in sanas) if sanas else None
    p_af = mean(r["precio_medio_eur_kg"] for r in af) if af else None
    return {
        "plaga": plaga,
        "campañas": len(serie),
        "afectadas": len(af),
        "frecuencia_pct": round(100 * len(af) / len(serie)),
        "merma_media_pct": round(mean(r["merma_pct"] for r in af), 1) if af else 0.0,
        "merma_max_pct": max((r["merma_pct"] for r in af), default=0.0),
        "explotaciones_pct": round(mean(r["pct_explotaciones_afectadas"] for r in af)) if af else 0,
        "ultima": af[-1]["campaña"] if af else None,
        "subida_precio_pct": round(100 * (p_af / p_sano - 1), 1) if p_sano and p_af else None,
        "serie": [{"campaña": r["campaña"], "incidencia": r["incidencia"], "merma": r["merma_pct"]} for r in serie],
    }


def _principal(inf: dict) -> dict:
    incs = inf.get("incidencias") or []
    return max(incs, key=lambda d: d.get("superficie_afectada_pct", 0)) if incs else {}


def preparar(usuario: dict, campos: list[dict], id_lead: str) -> dict:
    """Reúne todo lo que necesitan la ficha y el dossier."""
    ahora = datetime.now(timezone.utc)
    id_ficha = f"IN-{ahora:%Y%m%d}-{id_lead[:5].upper()}"
    filas = []
    for n, c in enumerate(campos, start=1):
        inf = c.get("informe") or {}
        pr = _principal(inf)
        plaga = identificar_plaga(c["cultivo"], pr.get("nombre"), pr.get("agente"))
        cult = historico()["cultivos"].get(c["cultivo"], {})
        perdida = int(inf.get("perdida_cosecha_pct") or 0)
        eur_ha = round(cult.get("rendimiento_kg_ha", 0) * cult.get("precio_eur_kg", 0) * perdida / 100) if inf else 0
        filas.append({
            "n": n, "id": f"{id_ficha}-{n:02d}", "cultivo": c["cultivo"], "cultivo_nombre": CULTIVOS[c["cultivo"]]["nombre"],
            "icono": CULTIVOS[c["cultivo"]]["icono"], "comarca": COMARCAS[c["comarca"]]["nombre"], "pueblos": COMARCAS[c["comarca"]]["pueblos"],
            "analizado": bool(inf), "informe": inf, "principal": pr, "plaga": plaga, "antecedentes": antecedentes(c["cultivo"], plaga),
            "perdida": perdida, "eur_ha": eur_ha, "rendimiento": cult.get("rendimiento_kg_ha"), "precio": cult.get("precio_eur_kg"),
            "foto": c.get("foto"), "foto_sha256": hashlib.sha256(c["foto"]).hexdigest() if c.get("foto") else None,
        })
    analizados = [f for f in filas if f["analizado"]]
    con_inc = [f for f in analizados if f["principal"]]
    peor = max(analizados, key=lambda f: f["perdida"], default=None)
    n_campos = len(filas)
    horas = sum(h * (n_campos if por else 1) for _, h, _, por in TRABAJO_MANUAL)
    coste = sum(round(h * (n_campos if por else 1) * e) for _, h, e, por in TRABAJO_MANUAL)
    if con_inc:
        partes = [f"{f['principal'].get('nombre', 'incidencia').lower()} en {f['cultivo_nombre'].lower()} ({f['perdida']} % de cosecha)" for f in con_inc]
        resumen = (f"{len(con_inc)} de tus {n_campos} campos" if n_campos > 1 else "Tu campo") + " muestra" + ("n" if len(con_inc) > 1 and n_campos > 1 else "") \
            + " incidencias: " + "; ".join(partes) + "."
    elif analizados:
        resumen = "Tus fotos no muestran plagas ni enfermedades: el escenario «Según tus fotos» coincide con la previsión base."
    else:
        resumen = "No llegaste a enviar fotos de tus campos; el informe recoge tu explotación y la previsión de campaña."
    return {"fecha": ahora.isoformat(timespec="seconds"), "id_ficha": id_ficha, "id_lead": id_lead, "usuario": usuario, "campos": filas,
            "con_incidencia": con_inc, "peor": peor, "horas_manual": horas, "coste_manual": coste, "dias_manual": DIAS_REACCION_MANUAL,
            "resumen": resumen, "historico_demo": bool(historico().get("demo"))}


def huella_campos(campos: list[dict]) -> str:
    """Cambia si el visitante cambia sus campos o sus fotos (para no regenerar en cada recarga)."""
    h = hashlib.sha256()
    for c in campos:
        h.update(json.dumps([c.get("cultivo"), c.get("comarca"), c.get("informe")], sort_keys=True, ensure_ascii=False, default=str).encode())
    return h.hexdigest()[:16]


def generar(usuario: dict, campos: list[dict], id_lead: str) -> dict:
    """Devuelve {'datos': ..., 'ficha': (nombre, bytes), 'dossier': (nombre, bytes)}."""
    from .informes_pdf import pdf_dossier, pdf_ficha
    d = preparar(usuario, campos, id_lead)
    dia = d["fecha"][:10]
    return {"datos": d,
            "ficha": (f"{d['id_ficha']}_ficha_incidencia.pdf", pdf_ficha(d)),
            "dossier": (f"Dossier_resumen_{dia}_{id_lead[:5].upper()}.pdf", pdf_dossier(d))}


def archivos_para_informe(usuario: dict, campos: list[dict], id_lead: str, cache: dict | None = None) -> list[dict]:
    """Ficha y dossier listos para que la previsión los suba al pulsar «Descargar mi informe».

    Devuelve [{"tipo", "nombre", "base64", "resumen"?}]. Con `cache` (st.session_state) solo se regeneran
    si el visitante cambia sus campos o sus fotos.
    """
    h = huella_campos(campos) + id_lead
    if cache is not None and cache.get("docs_huella") == h:
        return cache["docs_archivos"]
    g = generar(usuario, campos, id_lead)
    archivos = []
    for tipo in ("ficha", "dossier"):
        nombre, datos = g[tipo]
        a = {"tipo": tipo, "nombre": nombre, "base64": base64.b64encode(datos).decode("ascii")}
        if tipo == "dossier":
            a["resumen"] = g["datos"]["resumen"]
        archivos.append(a)
    if cache is not None:
        cache["docs_huella"], cache["docs_archivos"] = h, archivos
    return archivos


def generar_y_subir(usuario: dict, campos: list[dict], id_lead: str) -> dict:
    """Genera la ficha y el dossier y los sube desde Python (útil para pruebas). Devuelve los links."""
    from .leads import subir_archivo
    g = generar(usuario, campos, id_lead)
    res = {"id_ficha": g["datos"]["id_ficha"]}
    for tipo in ("ficha", "dossier"):
        nombre, datos = g[tipo]
        res[tipo] = subir_archivo(id_lead, tipo, nombre, datos, resumen=g["datos"]["resumen"] if tipo == "dossier" else None)
    return res
