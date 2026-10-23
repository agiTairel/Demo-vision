"""Precalcula los informes de las imágenes de ejemplo.

Así la galería responde al instante, no gasta API durante el evento y sigue
funcionando aunque la conexión falle. Ejecutar después de añadir o cambiar
imágenes en ejemplos/:

    python precalcular.py            # solo las que falten
    python precalcular.py --todas    # recalcula todas

Lee las claves de .streamlit/secrets.toml o de variables de entorno.
"""

import json
import os
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).parent
secretos = RAIZ / ".streamlit" / "secrets.toml"
if secretos.exists():
    for k, v in tomllib.loads(secretos.read_text(encoding="utf-8")).items():
        os.environ.setdefault(k, str(v))

from calidad.analizador import analizar, huella, preparar_imagen  # noqa: E402
from calidad.sanidad import CULTIVOS, analizar_sanidad, comarca_tipica, fotos_carpeta  # noqa: E402

DIR = RAIZ / "ejemplos"
SALIDA = DIR / "resultados.json"


def main() -> None:
    todas = "--todas" in sys.argv
    ejemplos = json.loads((DIR / "ejemplos.json").read_text(encoding="utf-8"))
    resultados = {} if todas or not SALIDA.exists() else json.loads(SALIDA.read_text(encoding="utf-8"))
    validas = set()
    for e in ejemplos:
        ruta = DIR / e["archivo"]
        if not ruta.exists():
            print(f"  · falta {e['archivo']} (se omite)")
            continue
        prod = e.get("producto", "auto")
        jpeg, _ = preparar_imagen(ruta.read_bytes())
        h = huella(jpeg, prod)
        validas.add(h)
        if h in resultados:
            print(f"  = {e['archivo']}: ya calculado")
            continue
        r = analizar(jpeg, prod)
        resultados[h] = {"informe": r.informe, "proveedor": "precalculado", "modelo": r.modelo, "segundos": r.segundos}
        print(f"  + {e['archivo']}: {r.informe['categoria']} ({r.informe['puntuacion_calidad']}/100) "
              f"con {r.proveedor} en {r.segundos:.1f} s")
    resultados = {h: v for h, v in resultados.items() if h in validas}
    SALIDA.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado {SALIDA} ({len(resultados)} informes). Revisa que los textos te convenzan.")


def campos() -> None:
    """Fotos predeterminadas de los campos (ejemplos/campos/): informe de plagas y enfermedades."""
    d = DIR / "campos"
    salida = d / "resultados.json"
    todas = "--todas" in sys.argv
    resultados = {} if todas or not salida.exists() else json.loads(salida.read_text(encoding="utf-8"))
    validas = set()
    for cultivo in CULTIVOS:
        fotos = fotos_carpeta(d, cultivo)
        if not fotos:
            print(f"  · {cultivo}: sin fotos de ejemplo")
        for ruta, titulo in fotos:
            archivo = ruta.relative_to(d).as_posix()
            jpeg, _ = preparar_imagen(ruta.read_bytes())
            h = huella(jpeg, "sanidad:" + cultivo)
            validas.add(h)
            if h in resultados:
                print(f"  = campos/{archivo}: ya calculado")
                continue
            r = analizar_sanidad(jpeg, cultivo, comarca_tipica(cultivo))
            resultados[h] = {"informe": r.informe, "proveedor": "precalculado", "modelo": r.modelo, "segundos": r.segundos}
            inc = ", ".join(x["nombre"] for x in r.informe["incidencias"]) or "sin incidencias"
            print(f"  + campos/{archivo}: {r.informe['estado']} ({inc}), pérdida {r.informe['perdida_cosecha_pct']} %")
    resultados = {h: v for h, v in resultados.items() if h in validas}
    d.mkdir(exist_ok=True)
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado {salida} ({len(resultados)} informes).")


if __name__ == "__main__":
    print("Fotos de los campos:")
    campos()
    if (DIR / "ejemplos.json").exists() and "--calidad" in sys.argv:
        print("Galería del inspector de calidad:")
        main()
