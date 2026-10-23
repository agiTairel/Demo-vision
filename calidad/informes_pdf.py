"""PDF de la ficha de incidencia y del dossier resumen (A4, texto seleccionable, tipografía Archivo incrustada)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "assets" / "fuentes"
LOGO = RAIZ / "assets" / "logo_tairel.png"
try:
    pdfmetrics.registerFont(TTFont("Archivo", str(FUENTES / "Archivo-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Archivo-SemiBold", str(FUENTES / "Archivo-SemiBold.ttf")))
    pdfmetrics.registerFont(TTFont("Archivo-Bold", str(FUENTES / "Archivo-Bold.ttf")))
    pdfmetrics.registerFontFamily("Archivo", normal="Archivo", bold="Archivo-Bold", italic="Archivo", boldItalic="Archivo-Bold")
    R, SB, B = "Archivo", "Archivo-SemiBold", "Archivo-Bold"
except Exception:  # noqa: BLE001
    R, SB, B = "Helvetica", "Helvetica-Bold", "Helvetica-Bold"

C = {k: colors.HexColor(v) for k, v in {
    "hoja": "#2f7d32", "hoja_osc": "#1f5a23", "tinta": "#1f2a1f", "texto": "#33413a", "apagado": "#566354", "tenue": "#7d8a78",
    "linea": "#dfe5d6", "fondo": "#eef3e6", "trigo": "#e2ac24", "rojo": "#b3361f", "ambar": "#9a6a00", "blanco": "#ffffff"}.items()}
COLOR_ESTADO = {"Sano": "#2a7230", "Incidencia leve": "#9a6a00", "Incidencia moderada": "#c0611f", "Incidencia grave": "#b3361f", "No evaluable": "#566354"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

ANCHO, ALTO = A4
MARGEN = 18 * mm
UTIL = ANCHO - 2 * MARGEN

st = {
    "titulo": ParagraphStyle("titulo", fontName=B, fontSize=20, leading=24, textColor=C["blanco"]),
    "sub": ParagraphStyle("sub", fontName=R, fontSize=9.5, leading=13, textColor=colors.HexColor("#cfe3c8")),
    "h2": ParagraphStyle("h2", fontName=B, fontSize=13, leading=16, textColor=C["tinta"], spaceBefore=14, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName=B, fontSize=11, leading=14, textColor=C["tinta"], spaceBefore=4, spaceAfter=3),
    "p": ParagraphStyle("p", fontName=R, fontSize=9.8, leading=14, textColor=C["texto"], spaceAfter=4),
    "peq": ParagraphStyle("peq", fontName=R, fontSize=8.3, leading=11.5, textColor=C["tenue"]),
    "cifra": ParagraphStyle("cifra", fontName=B, fontSize=18, leading=21, textColor=C["hoja_osc"]),
    "cifra_txt": ParagraphStyle("cifra_txt", fontName=R, fontSize=8.3, leading=11, textColor=C["apagado"]),
    "k": ParagraphStyle("k", fontName=R, fontSize=9, leading=12, textColor=C["apagado"]),
    "v": ParagraphStyle("v", fontName=R, fontSize=9.3, leading=12.5, textColor=C["texto"]),
    "vd": ParagraphStyle("vd", fontName=R, fontSize=9.3, leading=12.5, textColor=C["apagado"], alignment=TA_RIGHT),
    "vb": ParagraphStyle("vb", fontName=B, fontSize=9.3, leading=12.5, textColor=C["tinta"], alignment=TA_RIGHT),
    "num": ParagraphStyle("num", fontName=B, fontSize=9.5, leading=12, textColor=C["blanco"], alignment=TA_CENTER),
    "cta": ParagraphStyle("cta", fontName=B, fontSize=11.5, leading=14, textColor=C["blanco"], alignment=TA_CENTER),
}


def e(s) -> str:
    return escape(str(s if s is not None else ""))


def nf(n, d: int = 0) -> str:
    if n is None:
        return "—"
    return f"{float(n):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def eur(n) -> str:
    return nf(n) + " €"


def _fecha(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    try:
        from zoneinfo import ZoneInfo
        d = d.astimezone(ZoneInfo("Europe/Madrid"))
    except Exception:  # noqa: BLE001
        pass
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}, {d:%H:%M}"


def _cabecera(titulo: str, subtitulo: str) -> Table:
    t = Table([[Paragraph(titulo, st["titulo"])], [Paragraph(subtitulo, st["sub"])]], colWidths=[UTIL])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C["hoja_osc"]), ("LEFTPADDING", (0, 0), (-1, -1), 16),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 16), ("TOPPADDING", (0, 0), (0, 0), 15), ("BOTTOMPADDING", (0, -1), (-1, -1), 13),
                           ("LINEBELOW", (0, -1), (-1, -1), 3, C["trigo"])]))
    return t


def _caja(valor: str, texto: str, color) -> Table:
    t = Table([[Paragraph(f'<font color="{color.hexval()}">{valor}</font>', st["cifra"])], [Paragraph(texto, st["cifra_txt"])]], colWidths=[UTIL / 2 - 4])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C["fondo"]), ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                           ("TOPPADDING", (0, 0), (0, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9), ("TOPPADDING", (0, 1), (-1, 1), 2),
                           ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
    return t


def _cifras(items) -> Table:
    filas = [[_caja(*items[0]), _caja(*items[1])], [_caja(*items[2]), _caja(*items[3])]]
    t = Table(filas, colWidths=[UTIL / 2] * 2)
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 4), ("LEFTPADDING", (1, 0), (1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def _datos(filas, ancho_k=42 * mm) -> Table:
    t = Table([[Paragraph(k, st["k"]), Paragraph(v if v not in (None, "") else "—", st["v"])] for k, v in filas], colWidths=[ancho_k, UTIL - ancho_k])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, C["linea"]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _tabla(cab, filas, anchos, total=None) -> Table:
    datos = []
    if cab:
        datos.append([Paragraph(c, ParagraphStyle("c", parent=st["k"], fontName=SB, alignment=0 if i == 0 else TA_RIGHT)) for i, c in enumerate(cab)])
    for f in filas:
        estilo3 = ParagraphStyle("x", parent=st["vb"], textColor=f[3]) if len(f) > 3 else st["vb"]
        datos.append([Paragraph(str(f[0]), st["v"]), Paragraph(str(f[1]), st["vd"]), Paragraph(str(f[2]), estilo3)])
    if total:
        datos.append([Paragraph(f"<b>{total[0]}</b>", st["v"]), Paragraph(f"<b>{total[1]}</b>", st["vb"]), Paragraph(f"<b>{total[2]}</b>", st["vb"])])
    t = Table(datos, colWidths=anchos)
    est = [("LINEABOVE", (0, 1 if cab else 0), (-1, -1), 0.6, C["linea"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]
    if total:
        est.append(("LINEABOVE", (0, -1), (-1, -1), 1.3, C["tinta"]))
    t.setStyle(TableStyle(est))
    return t


def _grafico(serie) -> Drawing:
    fila, etiq = 12, 46
    alto = fila * len(serie) + 4
    d = Drawing(UTIL, alto)
    ancho = UTIL - etiq - 50
    mx = max([1] + [s["merma"] for s in serie])
    for i, s in enumerate(serie):
        y = alto - (i + 1) * fila
        d.add(String(0, y + 2.5, s["campaña"], fontName=R, fontSize=7.5, fillColor=C["apagado"]))
        if s["incidencia"]:
            d.add(Rect(etiq, y + 1.5, max(2, ancho * s["merma"] / mx), 7.5, fillColor=C["trigo"], strokeColor=None))
            txt = nf(s["merma"], 1) + " %"
        else:
            d.add(Line(etiq, y + 5, etiq + 3, y + 5, strokeColor=C["linea"], strokeWidth=1))
            txt = "sin plaga"
        d.add(String(UTIL, y + 2.5, txt, fontName=SB if s["incidencia"] else R, fontSize=7.5,
                     fillColor=C["tinta"] if s["incidencia"] else C["tenue"], textAnchor="end"))
    return d


def _foto(jpeg: bytes | None, ancho: float, alto_max: float):
    if not jpeg:
        return None
    try:
        from PIL import Image as PImage
        im = PImage.open(BytesIO(jpeg))
        im.thumbnail((1000, 1000))          # suficiente para imprimir a 6 cm y el PDF pesa poco
        buf = BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=80, optimize=True)
        buf.seek(0)
        w, h = im.size
        a = min(ancho, alto_max * w / h)
        return Image(buf, width=a, height=a * h / w)
    except Exception:  # noqa: BLE001
        return None


def _boton(texto: str, url: str) -> Table:
    t = Table([[Paragraph(f'<link href="{e(url)}" color="#FFFFFF">{texto}</link>', st["cta"])]], colWidths=[min(UTIL, 125 * mm)])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C["hoja"]), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                           ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    t.hAlign = "CENTER"
    return t


def _documento(historia, titulo: str, asunto: str, pie: str) -> bytes:
    buf = BytesIO()

    def pie_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFont(R, 7.5)
        canvas.setFillColor(C["tenue"])
        canvas.drawString(MARGEN, 10 * mm, pie)
        canvas.drawRightString(ANCHO - MARGEN, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=MARGEN, rightMargin=MARGEN, topMargin=MARGEN, bottomMargin=18 * mm,
                          title=titulo, author="Tairel Data", subject=asunto, creator="Tairel Data · demo IA para el campo", lang="es-ES")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(MARGEN, 18 * mm, UTIL, ALTO - MARGEN - 18 * mm, leftPadding=0, rightPadding=0,
                                                             topPadding=0, bottomPadding=0)], onPage=pie_pagina)])
    doc.build(historia)
    return buf.getvalue()


def _aviso_demo(d) -> list:
    return [Spacer(1, 12), Paragraph("<b>Caso de demostración:</b> el diagnóstico es visual y orientativo, generado por IA a partir de una foto; "
                                     "el histórico de campañas y los rendimientos y precios por hectárea son datos simulados para la demo. "
                                     "En un proyecto real se trabaja con los técnicos y los datos de cada empresa.", st["peq"])]


# ───────────────────────── Ficha de incidencia ─────────────────────────

def pdf_ficha(d: dict) -> bytes:
    u = d["usuario"]
    H = [_cabecera(f"Ficha de incidencia {e(d['id_ficha'])}",
                   f"{e(u.get('nombre'))}{' · ' + e(u['empresa']) if u.get('empresa') else ''} · {_fecha(d['fecha'])} · "
                   f"{len(d['campos'])} campo{'s' if len(d['campos']) != 1 else ''}"), Spacer(1, 10)]
    H.append(Paragraph(e(d["resumen"]), st["p"]))
    for f in d["campos"]:
        inf, pr = f["informe"], f["principal"]
        bloque = [CondPageBreak(70 * mm),
                  Paragraph(f"{e(f['id'])} · Campo {f['n']}: {e(f['cultivo_nombre'])} en {e(f['comarca'])}", st["h2"])]
        if not f["analizado"]:
            bloque.append(Paragraph("Campo registrado sin foto: no hay análisis de plagas ni enfermedades para este campo.", st["p"]))
            H += bloque
            continue
        color = COLOR_ESTADO.get(inf.get("estado"), "#566354")
        filas = [("Estado", f'<font color="{color}"><b>{e(inf.get("estado"))}</b></font>'),
                 ("Cultivo detectado", e(inf.get("cultivo_detectado")) + ("" if inf.get("coincide_cultivo", True) else " · <b>no coincide con el indicado</b>")),
                 ("Pérdida de cosecha estimada", f"<b>{f['perdida']} %</b> si no se actúa"),
                 ("Índice de incidencia", f"{inf.get('indice_incidencia', 0)} / 100"),
                 ("Riesgo de propagación", e(inf.get("riesgo_propagacion"))),
                 ("Confianza del diagnóstico", f"{inf.get('confianza', '—')} %"),
                 ("Comarca", f"{e(f['comarca'])} ({e(f['pueblos'])})")]
        foto = _foto(f["foto"], 62 * mm, 62 * mm)
        tabla = _datos(filas, 44 * mm) if not foto else Table([[foto, _datos_estrecho(filas)]], colWidths=[66 * mm, UTIL - 66 * mm])
        if foto:
            tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        bloque.append(tabla)
        bloque.append(Spacer(1, 6))
        bloque.append(Paragraph(f"<b>Diagnóstico.</b> {e(inf.get('resumen'))}", st["p"]))
        if inf.get("incidencias"):
            bloque.append(_tabla(["Qué se ve", "Severidad", "Superficie"], [
                [f"<b>{e(x.get('nombre'))}</b> · {e(x.get('tipo'))} · <i>{e(x.get('agente'))}</i><br/>"
                 f'<font size="8.5" color="#566354">{e(x.get("sintomas"))}</font>', e(x.get("severidad")), f"{x.get('superficie_afectada_pct', 0)} %"]
                for x in inf["incidencias"]], [UTIL - 50 * mm, 25 * mm, 25 * mm]))
        if inf.get("recomendaciones"):
            bloque.append(KeepTogether([Paragraph("<b>Qué haría el técnico</b>", st["h3"])]
                                       + [Paragraph(e(r), ParagraphStyle("li", parent=st["p"], leftIndent=10), bulletText="•")
                                          for r in inf["recomendaciones"]]))
        if f["antecedentes"]:
            a = f["antecedentes"]
            bloque.append(Paragraph(f"<b>Antecedentes.</b> En las últimas {a['campañas']} campañas, {e(a['plaga'])} afectó al "
                                    f"{e(f['cultivo_nombre'].lower())} en Navarra en {a['afectadas']} ({a['frecuencia_pct']} %), con una merma media "
                                    f"de la cosecha del {nf(a['merma_media_pct'], 1)} %. Última campaña afectada: {e(a['ultima'] or '—')}.", st["p"]))
        if inf.get("advertencia"):
            bloque.append(Paragraph(f"<b>Advertencia sobre la foto:</b> {e(inf['advertencia'])}", st["peq"]))
        H += bloque

    H.append(KeepTogether([Paragraph("Trazabilidad", st["h2"]), _datos(
        [("Identificador", f"<b>{e(d['id_ficha'])}</b>"), ("Fecha", _fecha(d["fecha"])),
         ("Enviado por", f"{e(u.get('nombre'))} · {e(u.get('email'))}"),
         ("Campos", " · ".join(f"{f['id']}: {e(f['cultivo_nombre'])}" for f in d["campos"]))]
        + [(f"Huella foto {f['id'][-2:]} (SHA-256)", f'<font size="7">{f["foto_sha256"]}</font>') for f in d["campos"] if f["foto_sha256"]]
        + [("Estado", "Diagnóstico automático pendiente de validar por un técnico")])]))
    H += _aviso_demo(d)
    return _documento(H, f"Ficha de incidencia {d['id_ficha']}", "Incidencias de campo detectadas por IA", f"Tairel Data · Ficha de incidencia {d['id_ficha']}")


def _datos_estrecho(filas) -> Table:
    ancho = UTIL - 66 * mm
    t = Table([[Paragraph(k, st["k"]), Paragraph(v if v not in (None, "") else "—", st["v"])] for k, v in filas], colWidths=[38 * mm, ancho - 38 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, C["linea"]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


# ───────────────────────── Dossier resumen ─────────────────────────

def pdf_dossier(d: dict) -> bytes:
    u = d["usuario"]
    nombre = e(u.get("nombre", "").split(" ")[0]) if u.get("nombre") else None
    empresa = e(u["empresa"]) if u.get("empresa") else "tu empresa"
    con, peor = d["con_incidencia"], d["peor"]
    if peor and peor["principal"]:
        titulo = f"{e(peor['principal'].get('nombre', 'Incidencia'))} en {e(peor['cultivo_nombre'].lower())}: hasta un {peor['perdida']} % de cosecha en juego"
    elif peor:
        titulo = "Tus campos están sanos: así se vigila la campaña sin salir a mirarlos"
    else:
        titulo = "Tu explotación y tu previsión de campaña"
    H = [_cabecera(titulo, f"Dossier resumen · {_fecha(d['fecha'])} · {e(u.get('nombre'))}{' · ' + e(u['empresa']) if u.get('empresa') else ''}"),
         Spacer(1, 11)]
    hola = f"Hola {nombre}:" if nombre else "Hola:"
    if any(f["analizado"] for f in d["campos"]):
        intro = (f"{hola} nos contaste tus campos y enviaste sus fotos. Sin que nadie lo pidiera, el sistema las ha diagnosticado, ha buscado "
                 "cómo se comportaron esas plagas en campañas anteriores y ha llevado la pérdida a la previsión de ventas, costes y margen. "
                 f"Esto es lo que supone para {empresa}.")
    else:
        intro = (f"{hola} nos contaste tus campos y el sistema ha preparado tu previsión de ventas, costes y margen. No enviaste fotos, así que "
                 "no hay diagnóstico de plagas: con una foto de cada campo, la pérdida pasaría sola a la previsión.")
    H.append(Paragraph(intro, st["p"]))
    H.append(Spacer(1, 4))

    eur_ha = max((f["eur_ha"] for f in con), default=0)
    H.append(_cifras([
        (f"{peor['perdida']} %" if peor else "—", (f"de cosecha en riesgo en tu campo más afectado ({e(peor['cultivo_nombre'].lower())}, {e(peor['comarca'])})"
                                                 if peor else "sin fotos analizadas"), C["rojo"] if peor and peor["perdida"] else C["hoja_osc"]),
        (f"{eur(eur_ha)}/ha" if eur_ha else "0 €/ha", "de ingresos en juego por hectárea afectada si no se actúa" if eur_ha else "sin pérdidas a la vista en tus fotos",
         C["rojo"] if eur_ha else C["hoja_osc"]),
        (f"{d['dias_manual']} días", "de ventaja frente a enterarse tarde, para tratar a tiempo y ajustar precios y contratos", C["hoja_osc"]),
        (eur(d["coste_manual"]), f"de trabajo técnico evitado ({nf(d['horas_manual'], 1)} horas)", C["hoja_osc"]),
    ]))

    H.append(Paragraph("Tus campos", st["h2"]))
    filas = []
    for f in d["campos"]:
        inf = f["informe"]
        if not f["analizado"]:
            filas.append([f"<b>{f['n']}. {e(f['cultivo_nombre'])}</b> · {e(f['comarca'])}", "sin foto", "—"])
            continue
        inc = f["principal"].get("nombre") or "Sin daños visibles"
        col = colors.HexColor(COLOR_ESTADO.get(inf.get("estado"), "#566354"))
        filas.append([f"<b>{f['n']}. {e(f['cultivo_nombre'])}</b> · {e(f['comarca'])}<br/><font size='8.3' color='#566354'>{e(inc)} · "
                      f"riesgo de propagación {e(str(inf.get('riesgo_propagacion', '')).lower())} · ficha {e(f['id'])}</font>",
                      e(inf.get("estado")), f"{f['perdida']} %", col])
    H.append(_tabla(["Campo", "Estado", "Pérdida"], filas, [UTIL - 70 * mm, 42 * mm, 28 * mm]))
    H.append(Paragraph(f"El detalle de cada diagnóstico, con la foto y las recomendaciones, está en la ficha de incidencia {e(d['id_ficha'])} adjunta.", st["peq"]))

    for f in con:
        a = f["antecedentes"]
        if not a:
            continue
        bloque = [CondPageBreak(60 * mm), Paragraph(f"Lo que dice el histórico: {e(a['plaga'])} en {e(f['cultivo_nombre'].lower())}", st["h2"]),
                  Paragraph(f"En las últimas {a['campañas']} campañas apareció en {a['afectadas']} ({a['frecuencia_pct']} %). Cuando aparece, la cosecha cae un "
                            f"<b>{nf(a['merma_media_pct'], 1)} %</b> de media (hasta un {nf(a['merma_max_pct'], 1)} %) y suele afectar al "
                            f"{a['explotaciones_pct']} % de las explotaciones de la zona"
                            + (f"; el precio sube un {nf(a['subida_precio_pct'], 1)} % porque hay menos producto." if a.get("subida_precio_pct") else "."), st["p"]),
                  Spacer(1, 3), _grafico(a["serie"]), Spacer(1, 4)]
        if f["eur_ha"]:
            bloque.append(Paragraph(f"Con un rendimiento de {nf(f['rendimiento'])} kg/ha y {nf(f['precio'], 2)} €/kg, la pérdida estimada en tu foto "
                                    f"({f['perdida']} %) son <b>{eur(f['eur_ha'])} por hectárea</b>: en 20 ha de {e(f['cultivo_nombre'].lower())}, "
                                    f"{eur(f['eur_ha'] * 20)}.", st["p"]))
        H.append(KeepTogether(bloque))

    H.append(CondPageBreak(30 * mm))
    H.append(Paragraph("Tu previsión de campaña", st["h2"]))
    H.append(Paragraph("En la demo has visto cómo cambian las ventas, los costes y el margen a 12 meses con el escenario «Según tus fotos», "
                       "frente a una ola de calor, un año seco o un pico energético. El informe completo de tu previsión, con el escenario que "
                       "tenías puesto al descargarlo, va adjunto en este correo.", st["p"]))

    n_foto = sum(1 for f in d["campos"] if f["analizado"])
    pasos = [("Incidencia del agricultor", f"{len(d['campos'])} campo{'s' if len(d['campos']) != 1 else ''} registrado{'s' if len(d['campos']) != 1 else ''}; "
              + (f"{n_foto} con foto diagnosticada al momento." if n_foto else "sin fotos, así que sin diagnóstico.")),
             ("Búsqueda en la documentación", f"{len(con)} incidencia{'s' if len(con) != 1 else ''} cruzada{'s' if len(con) != 1 else ''} con 10 campañas de histórico."),
             ("Previsión de costes", "La pérdida pasa sola al escenario «Según tus fotos» de ventas, costes y margen."),
             ("Ficha y dossier", f"Documentados con el identificador {e(d['id_ficha'])} y enviados a tu correo.")]
    num = lambda i: _bolita(i)  # noqa: E731
    tp = Table([[num(i), [Paragraph(f"<b>{t}</b>", st["v"]), Paragraph(x, st["v"])]] for i, (t, x) in enumerate(pasos, 1)], colWidths=[11 * mm, UTIL - 11 * mm])
    tp.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    H.append(KeepTogether([Paragraph("Lo que ha hecho el sistema sin que nadie lo pidiera", st["h2"]), tp]))

    n = len(d["campos"])
    from .documentacion import TRABAJO_MANUAL
    filas_m = [[t, f"{nf(h * (n if por else 1), 1)} h", eur(round(h * (n if por else 1) * eh))] for t, h, eh, por in TRABAJO_MANUAL]
    H.append(KeepTogether([Paragraph("Lo que habría costado hacerlo a mano", st["h2"]),
                           _tabla(None, filas_m, [UTIL - 50 * mm, 22 * mm, 28 * mm], total=["Total", f"{nf(d['horas_manual'], 1)} h", eur(d["coste_manual"])]),
                           Spacer(1, 8),
                           Paragraph(f"Y lo más caro no son las horas: son los <b>{d['dias_manual']} días</b> que tarda la información del campo en llegar a quien "
                                     "decide tratamientos, compras, precios y contratos. Aquí ha llegado en el momento.", st["p"]),
                           Spacer(1, 10), _boton(f"Quiero esto con los datos de {empresa}", "https://taireldata.com")]))
    H += _aviso_demo(d)
    return _documento(H, f"Dossier resumen · {u.get('nombre', '')}", "Resumen de la demo IA para el campo", f"Tairel Data · Dossier resumen · ficha {d['id_ficha']}")


def _bolita(i: int) -> Table:
    t = Table([[Paragraph(str(i), st["num"])]], colWidths=[7 * mm], rowHeights=[7 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C["hoja_osc"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROUNDEDCORNERS", [3.5 * mm] * 4),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t
