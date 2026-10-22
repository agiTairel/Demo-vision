"""Registro de contactos (leads) en una hoja de Google Sheets.

La app envía cada contacto a un Apps Script publicado como aplicación web
(ver google_sheets_leads.gs), que añade una fila a la pestaña "Leads".
Si el envío falla, el contacto se escribe en el registro de la app con el
prefijo LEAD_PENDIENTE para no perderlo.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone

from .analizador import config

PATRON_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def email_valido(email: str) -> bool:
    return bool(PATRON_EMAIL.match(email.strip()))


def _limpiar(texto: str, maximo: int = 120) -> str:
    """Recorta y evita que la hoja interprete el texto como fórmula."""
    t = (texto or "").strip().replace("\n", " ")[:maximo]
    if t[:1] in ("=", "+", "-", "@"):
        t = "'" + t
    return t


def guardar_lead(email: str, nombre: str, empresa: str, consentimiento: bool,
                 producto: str = "", categoria: str = "") -> bool:
    """Devuelve True si el contacto quedó guardado en la hoja."""
    fila = {
        "token": config("LEADS_TOKEN", ""),
        "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "email": _limpiar(email.lower(), 254),
        "nombre": _limpiar(nombre),
        "empresa": _limpiar(empresa),
        "producto": _limpiar(producto),
        "categoria": _limpiar(categoria),
        "consentimiento": bool(consentimiento),
        "origen": config("LEADS_ORIGEN", "Demo visión artificial · evento agro"),
    }
    url = config("LEADS_WEBHOOK_URL", "")
    if url:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(fila).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                respuesta = json.loads(r.read().decode("utf-8") or "{}")
            if respuesta.get("ok"):
                return True
            print("ERROR lead: respuesta", respuesta, flush=True)
        except Exception as e:  # noqa: BLE001
            print("ERROR lead:", type(e).__name__, e, flush=True)
    sin_token = {k: v for k, v in fila.items() if k != "token"}
    print("LEAD_PENDIENTE", json.dumps(sin_token, ensure_ascii=False), flush=True)
    return False
