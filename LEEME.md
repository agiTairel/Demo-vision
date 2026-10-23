# Demo · Previsión de costes y ventas (agro)

Módulo 1 de la demo de Tairel Data para la jornada de innovación abierta de CEIN. Funciona **100 % sin conexión**.

## Arrancar

| Qué | Cómo |
|---|---|
| Portátil | Doble clic en `INICIAR_DEMO.bat` (abre Edge o Chrome en modo app) |
| Tablet o pantalla del stand | Doble clic en `INICIAR_DEMO_KIOSKO.bat`: pantalla completa y reinicio automático tras 90 s sin uso. Para salir: `Alt+F4` |
| Sin Windows | Abrir `app/index.html` en cualquier navegador |

## Estructura

```
demo-prevision-agro/
├── INICIAR_DEMO.bat            lanzador (portátil)
├── INICIAR_DEMO_KIOSKO.bat     lanzador (stand, reinicio automático)
├── LEEME.md
├── requirements.txt            numpy, pandas (solo para regenerar datos/modelo)
├── app/                        ← la demo (no necesita Python ni internet)
│   ├── index.html              interfaz
│   ├── motor.js                motor de previsión y explicación (replica comun.py)
│   ├── modelo.js               coeficientes entrenados (generado)
│   ├── navarra.js              contornos de municipios y comarcas agrarias (generado)
│   └── fuentes.css             Archivo + Figtree incrustadas
├── scripts/
│   ├── comun.py                calendario, clima normal y variables (features)
│   ├── 1_generar_datos.py      dataset (clima y precios reales + empresa sintética)
│   ├── 2_entrenar_modelo.py    entrenamiento, backtest y exportación
│   ├── pruebas/probar_motor.js comprueba que JS calcula igual que Python
│   └── mapa/                   municipios → comarca agraria (INE) y generador de navarra.js
├── datos/                      CSV generados; datos/fuentes/ = series públicas reales (Meteo Navarra, OMIE, OMIP, Ministerio, INE)
├── modelo/                     modelo.json y metricas.md
└── docs/SUPUESTOS_DATOS.md     supuestos del dataset
```

## Regenerar datos y modelo (PowerShell)

```powershell
pip install -r requirements.txt
cd scripts
python 1_generar_datos.py
python 2_entrenar_modelo.py      # reescribe modelo/ y app/modelo.js
node pruebas/probar_motor.js     # opcional: verifica JS = Python
```

## Modelo

Para cada producto se entrena un conjunto de regresiones Ridge con estacionalidad (Fourier) y variables exógenas:

- **Volumen y precios:** clima, energía y promociones.
- **Costes:** merma, energía, mano de obra, transporte y envases.
- **Congelado:** además, el rendimiento de la campaña.

El navegador evalúa los coeficientes en menos de 1 ms, así que los sliders recalculan al instante.

- **Intervalo de confianza (80 %):** sale de los residuos al prever con clima *normal*. Es más ancho en cereal porque la cosecha depende de la lluvia.
- **"Factores que explican":** se calculan con valores de Shapley exactos.
  - Sin escenario: reparto del cambio de ventas frente al último año.
  - Con escenario: reparto del cambio de margen entre las palancas movidas.
- **Precisión (backtest):** entrenado hasta oct 2025 y evaluado en el año siguiente con clima normal. Error mensual medio del 9,4 %: 2-4 % en IV gama y congelado y mucho mayor en cereal, porque 2026 fue muy seco. Con el tiempo real, 2,9 %. Detalle en `modelo/metricas.md`.

## Con datos reales de un cliente

Sustituir `datos/ventas_costes.csv` por su histórico (mismas columnas) y las series de `datos/fuentes/` por la estación meteorológica de su zona (Meteo Navarra o AEMET); la luz y el gasóleo ya son reales. Después, ejecutar `2_entrenar_modelo.py`. La app no cambia.

## Mapa de Navarra

- Zonas: las 7 comarcas agrarias del INE (Noroccidental, Pirineos, Cuenca de Pamplona, Tierra Estella,
  Navarra Media, Ribera Alta Aragón, Ribera Baja), con sus 272 municipios (`scripts/mapa/muni_comarca_ine.json`).
- Datos reales:
  - Superficie por cultivo y comarca: INE, Censo Agrario 2020, tabla 52058 (hortalizas, trigo, cebada, maíz en grano).
  - Clima: fichas climáticas de Meteo Navarra, normales 1991-2020 (Doneztebe, Aoiz*, Pamplona, Estella,
    Olite, Falces, Tudela). *Aoiz no tiene normales 1991-2020: se usa su serie completa.
  - Tierra regable por comarca: INE, Censo Agrario 2020, tablas 51131 y 51128.
  - Contornos: Instituto Geográfico Nacional (CC BY 4.0), a través del paquete npm `es-atlas` (MIT).
- Supuestos de la demo: la empresa compra en cada comarca en proporción a esa superficie; todos los productos
  de hortaliza comparten el reparto de "hortalizas"; la sensibilidad de cada comarca al calor y cómo el regadío amortigua la sequía.
  El total de toneladas siempre es el del modelo; el mapa solo lo reparte.
- Regenerar: `cd scripts/mapa && npm i es-atlas@0.6.0 topojson-client@3.1.0 topojson-simplify@3.0.3 d3-geo@3.1.0`
  y `node generar_mapa.js 0.15 ./node_modules/es-atlas/es/municipalities.json`, luego copiar `navarra.js` a `app/`.

## Qué enseña la demo (resumen para quien la presente)

- Cifras clave a 12 meses, rango probable y un párrafo "En pocas palabras" que se reescribe con cada cambio.
- Escenarios rápidos (incluido el peor caso razonable), 7 factores a mano (también el precio de venta) y
  escenarios con nombre que el visitante guarda y compara.
- Gráfico con histórico, previsión, escenario y comparación con el año pasado o la media de 3 años.
- Mapa de Navarra por comarcas agrarias (datos reales del INE y Meteo Navarra): origen, clima, cambio y semáforo de riesgo.
- Comparativa de escenarios, reparto del coste, cascada de factores (Shapley) e informe en PDF.
