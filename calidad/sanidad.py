"""Campos de cultivo, comarcas de Navarra y análisis de plagas y enfermedades por foto.

Los cultivos y las comarcas coinciden con los de la demo de previsión
(prevision/: modelo.js y las 7 comarcas agrarias del INE), para que la
incidencia detectada en cada campo pueda pasarse a la previsión.
"""

from __future__ import annotations

import re

from .analizador import Resultado, Tarea, ejecutar

# ---------------------------------------------------------------------------
# Catálogos (mismos identificadores que la previsión)
# ---------------------------------------------------------------------------

CULTIVOS = {
    # IV gama
    "lechuga": {
        "nombre": "Lechuga", "linea": "Hortalizas · IV gama", "icono": "🥬",
        "problemas": "mildiu (Bremia lactucae), esclerotinia, botritis, pulgones (Nasonovia ribisnigri), "
                     "trips y virus del bronceado (TSWV), y fisiopatías como el tip burn (quemado de bordes).",
    },
    "canonigos": {
        "nombre": "Canónigos", "linea": "Hortalizas · IV gama", "icono": "🌱",
        "problemas": "mildiu (Peronospora valerianellae), oídio, phoma, pulgón, babosas y amarilleo por exceso de humedad.",
    },
    "espinaca": {
        "nombre": "Espinaca", "linea": "Hortalizas · IV gama", "icono": "🍃",
        "problemas": "mildiu (Peronospora effusa), cladosporiosis, antracnosis, pulgones y minadores de hoja.",
    },
    # Congelado
    "brocoli": {
        "nombre": "Brócoli", "linea": "Hortalizas · congelado", "icono": "🥦",
        "problemas": "mildiu (Hyaloperonospora), alternaria, mancha negra, oruga de la col (Pieris), "
                     "polilla de las crucíferas (Plutella xylostella), pulgón ceroso y floretes amarillos o abiertos.",
    },
    "guisante": {
        "nombre": "Guisante", "linea": "Hortalizas · congelado", "icono": "🫛",
        "problemas": "oídio, ascoquitosis, mildiu, sitona, pulgón verde y trips.",
    },
    # Cereal
    "trigo": {
        "nombre": "Trigo", "linea": "Cereal", "icono": "🌾",
        "problemas": "roya amarilla (Puccinia striiformis), roya parda, septoriosis, oídio, fusariosis de la espiga, "
                     "pulgones y tronchaespigas.",
    },
    "cebada": {
        "nombre": "Cebada", "linea": "Cereal", "icono": "🌾",
        "problemas": "rincosporiosis, helmintosporiosis (mancha en red), roya parda, oídio y virus del enanismo amarillo (BYDV).",
    },
    "maiz": {
        "nombre": "Maíz", "linea": "Cereal", "icono": "🌽",
        "problemas": "taladro (Sesamia nonagrioides, Ostrinia nubilalis), fusarium en mazorca, carbón común, "
                     "helmintosporiosis, araña roja y gusano de alambre.",
    },
}

# 7 comarcas agrarias del INE, como en la previsión. Superficie: INE, Censo Agrario 2020.
COMARCAS = {
    "riberabaja": {"nombre": "Ribera Baja", "pueblos": "Tudela, Ablitas, Fustiñana, Cortes"},
    "riberaalta": {"nombre": "Ribera Alta Aragón", "pueblos": "Carcastillo, Falces, Sesma, Lerín"},
    "media": {"nombre": "Navarra Media", "pueblos": "Olite, Tafalla, Larraga, Cáseda"},
    "estella": {"nombre": "Tierra Estella", "pueblos": "Yerri, Arróniz, Oteiza, Los Arcos"},
    "cuenca": {"nombre": "Cuenca de Pamplona", "pueblos": "Cizur, Noáin, Olza, Galar"},
    "pirineos": {"nombre": "Pirineos", "pueblos": "Urraul Bajo, Lónguida, Izagaondoa, Lizoain"},
    "noroccidental": {"nombre": "Noroccidental", "pueblos": "Ezcabarte, Arakil, Ultzama, Larraun"},
}

# Hectáreas por comarca (INE, Censo Agrario 2020, tabla 52058), para proponer zonas típicas
SUPERFICIE = {
    "hortalizas": {"noroccidental": 27, "pirineos": 39, "cuenca": 204, "estella": 796, "media": 784, "riberaalta": 5384, "riberabaja": 4464},
    "trigo": {"noroccidental": 616, "pirineos": 8765, "cuenca": 11610, "estella": 19042, "media": 15401, "riberaalta": 11815, "riberabaja": 10905},
    "cebada": {"noroccidental": 336, "pirineos": 4734, "cuenca": 8373, "estella": 17646, "media": 14897, "riberaalta": 20741, "riberabaja": 11582},
    "maiz": {"noroccidental": 532, "pirineos": 45, "cuenca": 733, "estella": 219, "media": 5441, "riberaalta": 6704, "riberabaja": 4426},
}
GRUPO_INE = {"lechuga": "hortalizas", "canonigos": "hortalizas", "espinaca": "hortalizas", "brocoli": "hortalizas",
             "guisante": "hortalizas", "trigo": "trigo", "cebada": "cebada", "maiz": "maiz"}


def comarca_tipica(cultivo: str) -> str:
    ha = SUPERFICIE[GRUPO_INE[cultivo]]
    return max(ha, key=ha.get)


def comarcas_ordenadas(cultivo: str) -> list[str]:
    """Comarcas de más a menos superficie de ese cultivo."""
    ha = SUPERFICIE[GRUPO_INE[cultivo]]
    return sorted(COMARCAS, key=lambda z: -ha[z])


def peso_cultivo(cultivo: str, comarca: str) -> str:
    ha = SUPERFICIE[GRUPO_INE[cultivo]]
    return f"{ha[comarca]:,}".replace(",", ".") + " ha en la comarca"


# ---------------------------------------------------------------------------
# Fotos predeterminadas que el visitante puede "enviar" como agricultor.
# Se buscan en ejemplos/campos/. Las que no existan no se muestran.
# ---------------------------------------------------------------------------

FOTOS_CAMPO = {
    "lechuga": [("lechuga_sana.jpg", "Recién cortada en campo"), ("lechuga_manchas.jpg", "Hojas con manchas amarillas"),
                ("lechuga_bordes.jpg", "Bordes de hoja quemados")],
    "canonigos": [("canonigos_sanos.jpg", "Bandeja recién cosechada"), ("canonigos_manchas.jpg", "Hojas con polvo blanco o manchas")],
    "espinaca": [("espinaca_sana.jpg", "Recién cortada en campo"), ("espinaca_manchas.jpg", "Manchas amarillas en el haz")],
    "brocoli": [("brocoli_sano.jpg", "Pella recién cortada"), ("brocoli_amarillo.jpg", "Floretes amarilleando"),
                ("brocoli_oruga.jpg", "Hojas mordidas")],
    "guisante": [("guisante_sano.jpg", "Vainas en planta"), ("guisante_oidio.jpg", "Planta con polvo blanco")],
    "trigo": [("trigo_sano.jpg", "Espigas antes de cosechar"), ("trigo_roya.jpg", "Hojas con pústulas amarillas"),
              ("trigo_espiga.jpg", "Espigas blanquecinas")],
    "cebada": [("cebada_sana.jpg", "Espigas antes de cosechar"), ("cebada_manchas.jpg", "Hojas con manchas pardas")],
    "maiz": [("maiz_sano.jpg", "Mazorca recién abierta"), ("maiz_taladro.jpg", "Tallo o mazorca perforados"),
             ("maiz_hongo.jpg", "Mazorca con moho")],
}

# Fotos de la carpeta de cada cultivo: ejemplos/campos/<cultivo>/*.jpg|jpeg|png|webp
# Se muestran todas las que haya, ordenadas por nombre; el título sale del nombre del archivo.
EXTENSIONES_FOTO = {".jpg", ".jpeg", ".png", ".webp"}
CARPETAS_CULTIVO = {
    "lechuga": ["lechuga", "lechugas"],
    "canonigos": ["canonigos", "canonigo", "canónigos", "canónigo"],
    "espinaca": ["espinaca", "espinacas"],
    "brocoli": ["brocoli", "brócoli"],
    "guisante": ["guisante", "guisantes"],
    "trigo": ["trigo"],
    "cebada": ["cebada"],
    "maiz": ["maiz", "maíz"],
}
# Palabra del nombre del archivo -> lo que el agricultor diría de su foto
TITULOS_POR_PALABRA = {
    "sano": "Planta sana", "sana": "Planta sana", "sanos": "Planta sana", "sanas": "Planta sana", "bien": "Planta sana",
    "malo": "Planta con síntomas", "mala": "Planta con síntomas", "mal": "Planta con síntomas", "enfermo": "Planta con síntomas",
    "manchas": "Hojas con manchas", "mancha": "Hojas con manchas",
    "quemada": "Bordes de hoja quemados", "quemado": "Bordes de hoja quemados", "bordes": "Bordes de hoja quemados",
    "oidio": "Polvo blanco en las hojas", "mildiu": "Manchas amarillas en las hojas",
    "hongo": "Con moho", "moho": "Con moho", "roya": "Pústulas en las hojas",
    "amarillo": "Floretes amarilleando", "amarilla": "Hojas amarilleando",
    "oruga": "Hojas mordidas", "plaga": "Hojas mordidas", "taladro": "Tallo o mazorca perforados",
    "espiga": "Espigas blanquecinas",
}


def _titulo_foto(nombre_archivo: str) -> str:
    palabras = re.split(r"[_\-\s]+", nombre_archivo.rsplit(".", 1)[0].lower())
    for w in reversed(palabras):
        if w in TITULOS_POR_PALABRA:
            return TITULOS_POR_PALABRA[w]
    resto = [w for w in palabras[1:] if w and not w.isdigit()] or palabras
    return " ".join(resto).capitalize()


def fotos_carpeta(dir_base, cultivo: str) -> list:
    """Fotos de ejemplo de un cultivo: su carpeta y, por compatibilidad, los nombres antiguos sueltos."""
    from pathlib import Path

    base = Path(dir_base)
    fotos, vistos = [], set()
    for nombre in CARPETAS_CULTIVO.get(cultivo, [cultivo]):
        carpeta = base / nombre
        if carpeta.is_dir():
            for f in sorted(carpeta.iterdir(), key=lambda x: x.name.lower()):
                if f.is_file() and f.suffix.lower() in EXTENSIONES_FOTO and f.name.lower() not in vistos:
                    vistos.add(f.name.lower())
                    fotos.append((f, _titulo_foto(f.name)))
    for archivo, titulo in FOTOS_CAMPO.get(cultivo, []):
        f = base / archivo
        if f.exists() and archivo.lower() not in vistos:
            fotos.append((f, titulo))
    # Si dos fotos acaban con el mismo título, se numeran para distinguirlas
    cuenta = {}
    for _, t in fotos:
        cuenta[t] = cuenta.get(t, 0) + 1
    vistos_t, salida = {}, []
    for f, t in fotos:
        if cuenta[t] > 1:
            vistos_t[t] = vistos_t.get(t, 0) + 1
            t = f"{t} ({vistos_t[t]})"
        salida.append((f, t))
    return salida


# ---------------------------------------------------------------------------
# Esquema y prompt
# ---------------------------------------------------------------------------

ESTADOS = ["Sano", "Incidencia leve", "Incidencia moderada", "Incidencia grave", "No evaluable"]

ESQUEMA_SANIDAD = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cultivo_detectado", "coincide_cultivo", "estado", "incidencias", "indice_incidencia",
                 "perdida_cosecha_pct", "riesgo_propagacion", "recomendaciones", "resumen", "confianza", "advertencia"],
    "properties": {
        "cultivo_detectado": {"type": "string", "description": "Qué cultivo se ve en la foto."},
        "coincide_cultivo": {"type": "boolean", "description": "Si coincide con el cultivo indicado por el agricultor."},
        "estado": {"type": "string", "enum": ESTADOS},
        "incidencias": {
            "type": "array",
            "description": "Plagas, enfermedades o daños visibles. Vacía si está sano.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["nombre", "tipo", "agente", "severidad", "superficie_afectada_pct", "sintomas"],
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre común. Ej.: 'Mildiu', 'Roya amarilla', 'Taladro'."},
                    "tipo": {"type": "string", "enum": ["Enfermedad", "Plaga", "Fisiopatía", "Daño abiótico"]},
                    "agente": {"type": "string", "description": "Organismo causante probable o 'No aplica'."},
                    "severidad": {"type": "string", "enum": ["leve", "moderada", "grave"]},
                    "superficie_afectada_pct": {"type": "integer", "description": "0-100, parte visible afectada."},
                    "sintomas": {"type": "string", "description": "Qué se ve en la imagen que lo indica."},
                },
            },
        },
        "indice_incidencia": {"type": "integer", "description": "0 = sano, 100 = totalmente afectado."},
        "perdida_cosecha_pct": {
            "type": "integer",
            "description": "Pérdida de cosecha comercializable estimada si no se actúa (0-60). Sano: 0-2.",
        },
        "riesgo_propagacion": {"type": "string", "enum": ["Bajo", "Medio", "Alto"]},
        "recomendaciones": {
            "type": "array", "items": {"type": "string"},
            "description": "Hasta 3 acciones concretas para el agricultor (manejo, tratamiento autorizado, vigilancia).",
        },
        "resumen": {"type": "string", "description": "Dos frases como mucho, en lenguaje de técnico de campo."},
        "confianza": {"type": "integer", "description": "0-100"},
        "advertencia": {"type": ["string", "null"], "description": "Problemas de la foto o null."},
    },
}

PROMPT_SANIDAD = """Eres el técnico de sanidad vegetal de una cooperativa agraria de Navarra. \
Un agricultor te envía una foto de su cultivo o cosecha y tú evalúas si hay plagas, enfermedades, \
fisiopatías o daños, cuánto afectan y cuánta cosecha podría perderse.

Reglas:
- Responde en español de España con terminología agronómica, pero entendible por un agricultor.
- Sé prudente: es un diagnóstico visual orientativo; si dudas entre varias causas, nombra la más probable \
y baja la confianza. No inventes daños que no se vean: si está sano, incidencias vacía y pérdida 0-2 %.
- La pérdida de cosecha es la estimada en ese campo si no se actúa, coherente con la severidad \
(leve 1-5 %, moderada 5-15 %, grave 15-40 %, excepcionalmente más).
- Las recomendaciones deben ser prácticas (vigilancia, manejo, momento de tratamiento, productos \
autorizados por materia activa genérica, consultar al técnico), sin dosis.
- Si la foto no es de un cultivo, estado "No evaluable" y explica en la advertencia qué se ve."""


def peticion_sanidad(cultivo: str, comarca: str) -> str:
    c = CULTIVOS[cultivo]
    z = COMARCAS[comarca]["nombre"]
    return (
        f"Cultivo indicado por el agricultor: {c['nombre']} ({c['linea']}). Campo en la comarca de {z} (Navarra).\n"
        f"Problemas habituales de este cultivo en la zona: {c['problemas']}\n\n"
        "Analiza la foto y devuelve el informe sanitario con el esquema indicado."
    )


def _entero(v, lo=0, hi=100, defecto=0):
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return defecto


def normalizar_sanidad(inf: dict) -> dict:
    inf = dict(inf)
    if inf.get("estado") not in ESTADOS:
        inf["estado"] = "No evaluable"
    inf["indice_incidencia"] = _entero(inf.get("indice_incidencia"))
    inf["perdida_cosecha_pct"] = _entero(inf.get("perdida_cosecha_pct"), 0, 60)
    inf["confianza"] = _entero(inf.get("confianza"), defecto=50)
    if inf.get("riesgo_propagacion") not in ("Bajo", "Medio", "Alto"):
        inf["riesgo_propagacion"] = "Bajo"
    incs = []
    for d in inf.get("incidencias") or []:
        if isinstance(d, dict):
            d = dict(d)
            d["superficie_afectada_pct"] = _entero(d.get("superficie_afectada_pct"))
            if d.get("severidad") not in ("leve", "moderada", "grave"):
                d["severidad"] = "leve"
            incs.append(d)
    inf["incidencias"] = incs
    inf["recomendaciones"] = [str(r) for r in (inf.get("recomendaciones") or [])][:3]
    for k in ("cultivo_detectado", "resumen"):
        inf[k] = str(inf.get(k) or "")
    inf.setdefault("coincide_cultivo", True)
    adv = inf.get("advertencia")
    inf["advertencia"] = adv if adv and str(adv).strip().lower() not in ("null", "none", "") else None
    if inf["estado"] == "Sano":
        inf["perdida_cosecha_pct"] = min(inf["perdida_cosecha_pct"], 2)
    return inf


def analizar_sanidad(jpeg: bytes, cultivo: str, comarca: str) -> Resultado:
    tarea = Tarea(
        PROMPT_SANIDAD,
        peticion_sanidad(cultivo, comarca),
        ESQUEMA_SANIDAD,
        nombre="informe_sanitario",
        descripcion="Registra el informe sanitario del cultivo de la foto.",
    )
    return ejecutar(jpeg, tarea, normalizar_sanidad)


def simulado_sanidad(peticion: str) -> dict:
    """Informe de ejemplo para desarrollo sin clave (modo simulado). No usar ante clientes."""
    m = re.search(r"agricultor: ([^(]+) \(", peticion)
    nombre = (m.group(1).strip() if m else "Cultivo")
    return {
        "cultivo_detectado": f"{nombre} (modo simulado)",
        "coincide_cultivo": True,
        "estado": "Incidencia moderada",
        "incidencias": [{
            "nombre": "Mildiu", "tipo": "Enfermedad", "agente": "Oomiceto (simulado)", "severidad": "moderada",
            "superficie_afectada_pct": 18, "sintomas": "Manchas amarillas angulosas en el haz con micelio en el envés.",
        }],
        "indice_incidencia": 22,
        "perdida_cosecha_pct": 9,
        "riesgo_propagacion": "Alto",
        "recomendaciones": [
            "Revisa el campo en las próximas 48 horas, sobre todo las zonas bajas y húmedas.",
            "Si sigue extendiéndose, consulta con tu técnico un tratamiento autorizado.",
            "Evita el riego por aspersión a última hora de la tarde.",
        ],
        "resumen": "Mildiu en fase activa en parte del campo. Con humedad alta puede extenderse rápido.",
        "confianza": 70,
        "advertencia": "Modo simulado: este informe no procede de un modelo real.",
    }
