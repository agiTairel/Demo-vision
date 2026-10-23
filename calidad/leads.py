"""Registro de contactos (leads) en una hoja de Google Sheets.

La app envía cada contacto a un Apps Script publicado como aplicación web
(ver google_sheets_leads.gs), que añade una fila a la pestaña "Leads".
Si el envío falla, el contacto se escribe en el registro de la app con el
prefijo LEAD_PENDIENTE para no perderlo.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
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
                 producto: str = "", categoria: str = "", id_lead: str = "") -> bool:
    """Devuelve True si el contacto quedó guardado en la hoja.

    id_lead identifica al visitante: con él se guardan después en su fila los links de su
    ficha de incidencia, su dossier resumen y su informe de costes (ver subir_archivo).
    """
    fila = {
        "token": config("LEADS_TOKEN", ""),
        "accion": "lead",
        "id_lead": id_lead,
        "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "email": _limpiar(email.lower(), 254),
        "nombre": _limpiar(nombre),
        "empresa": _limpiar(empresa),
        "producto": _limpiar(producto),
        "categoria": _limpiar(categoria),
        "consentimiento": bool(consentimiento),
        "origen": config("LEADS_ORIGEN", "Demo visión artificial · evento agro"),
    }
    respuesta = _post(fila)
    if respuesta.get("ok"):
        return True
    sin_token = {k: v for k, v in fila.items() if k != "token"}
    print("LEAD_PENDIENTE", json.dumps(sin_token, ensure_ascii=False), flush=True)
    return False


def subir_archivo(id_lead: str, tipo: str, nombre: str, datos: bytes, resumen: str | None = None) -> str | None:
    """Sube un PDF del visitante a la carpeta de Drive y guarda su link en la fila del Sheet.

    tipo: "ficha" (ficha de incidencia), "dossier" (dossier resumen) o "costes" (informe de la previsión).
    Si ya había uno del mismo tipo, el Apps Script lo sustituye. Devuelve el link, o None si falla.
    """
    carga = {"token": config("LEADS_TOKEN", ""), "accion": "archivo", "id_lead": id_lead, "tipo": tipo,
             "nombre": nombre, "mime": "application/pdf", "base64": base64.b64encode(datos).decode("ascii")}
    if resumen:
        carga["resumen"] = resumen[:600]
    r = _post(carga, timeout=60)
    if r.get("ok"):
        return r.get("link") or ""
    print(f"ERROR archivo {tipo} ({nombre}):", {k: v for k, v in r.items() if k != "ok"}, flush=True)
    return None


def _post(carga: dict, timeout: int = 20) -> dict:
    """Envía un JSON al Apps Script y devuelve su respuesta como dict ({"ok": False, ...} si falla)."""
    url = (config("LEADS_WEBHOOK_URL", "") or "").strip()
    if not url:
        return {"ok": False, "error": "falta LEADS_WEBHOOK_URL"}
    try:
        # Google rechaza con 403 algunas peticiones con el agente por defecto de Python,
        # así que nos identificamos como un navegador normal.
        req = urllib.request.Request(
            url,
            data=json.dumps(carga).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; TairelDemo/1.0)",
                "Accept": "application/json,text/plain,*/*",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cuerpo = r.read().decode("utf-8", "replace")
            url_final = r.geturl()
        try:
            respuesta = json.loads(cuerpo or "{}")
        except json.JSONDecodeError:
            # Google ha devuelto una página web: guardamos su título y dónde acabó la petición.
            titulo = re.search(r"<title>(.*?)</title>", cuerpo, re.S | re.I)
            error_gs = re.search(r'(?:errorMessage|Error|Excepción|Exception)[^<]{0,200}', cuerpo)
            respuesta = {
                "ok": False,
                "url_final": url_final.split("?")[0],
                "titulo": titulo.group(1).strip()[:120] if titulo else "",
                "detalle": error_gs.group(0)[:200] if error_gs else "",
            }
        if not respuesta.get("ok"):
            print("ERROR Apps Script: respuesta", respuesta, flush=True)
        return respuesta
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:300].replace("\n", " ")
        print(f"ERROR Apps Script: HTTP {e.code} en {e.geturl()} :: {detalle}", flush=True)
        return {"ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        print("ERROR Apps Script:", type(e).__name__, e, flush=True)
        return {"ok": False, "error": type(e).__name__}
