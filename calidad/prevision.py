"""Monta la demo de previsión (carpeta prevision/) como una sola página HTML.

La previsión es la herramienta HTML/JS de la compañera (sin servidor). Aquí
se incrustan sus scripts y fuentes en un único documento y se le pasa la
lista de campos del visitante como window.DEMO_TAIREL.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "prevision"
MARCA_INYECCION = "<script>\n(function () {"


@lru_cache(maxsize=1)
def _plantilla() -> str:
    html = (DIR / "index.html").read_text(encoding="utf-8")
    css = (DIR / "fuentes.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="fuentes.css">', "<style>" + css + "</style>")
    for nombre in ("modelo.js", "motor.js", "navarra.js"):
        js = (DIR / nombre).read_text(encoding="utf-8")
        etiqueta = f'<script src="{nombre}"></script>'
        if etiqueta not in html:
            raise RuntimeError(f"No encuentro {etiqueta} en prevision/index.html")
        html = html.replace(etiqueta, "<script>" + js + "</script>")
    if MARCA_INYECCION not in html:
        raise RuntimeError("No encuentro el script principal en prevision/index.html")
    return html


def campos_para_prevision(campos: list[dict]) -> list[dict]:
    """Convierte los campos de la app al formato que espera la previsión."""
    salida = []
    for i, c in enumerate(campos, start=1):
        inf = c.get("informe") or {}
        incs = inf.get("incidencias") or []
        principal = max(incs, key=lambda d: d.get("superficie_afectada_pct", 0)) if incs else {}
        salida.append({
            "n": i,
            "cultivo": c["cultivo"],
            "comarca": c["comarca"],
            "analizado": bool(inf),
            "estado": inf.get("estado", ""),
            "incidencia": principal.get("nombre", ""),
            "afectado": principal.get("superficie_afectada_pct", 0),
            "perdida": int(inf.get("perdida_cosecha_pct", 0) or 0),
            "riesgo": inf.get("riesgo_propagacion", ""),
            "recomendacion": (inf.get("recomendaciones") or [""])[0],
        })
    return salida


def html_prevision(campos: list[dict], email: str = "", web: str = "", subida: dict | None = None) -> str:
    """subida = {"url": <Apps Script>, "id_lead": ..., "archivos": [ficha, dossier]}: al pulsar «Descargar mi informe»
    la previsión sube esos archivos y el PDF de costes a Drive para enviarlos al día siguiente."""
    datos = json.dumps({"campos": campos_para_prevision(campos), "cta": {"email": email, "web": web},
                        "subida": subida if subida and subida.get("url") and subida.get("id_lead") else None},
                       ensure_ascii=False).replace("</", "<\\/")
    return _plantilla().replace(MARCA_INYECCION, f"<script>window.DEMO_TAIREL = {datos};</script>\n" + MARCA_INYECCION, 1)
