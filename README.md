# Demo IA para el campo · Tairel Data

Demo web para móvil en cuatro pasos:

1. Bienvenida y registro (correo, nombre y empresa opcional). El contacto se guarda en Google Sheets.
2. Tus campos: de 1 a 4 campos, cada uno con su cultivo (lechuga, canónigos, espinaca, brócoli, guisante, trigo, cebada o maíz) y su comarca agraria de Navarra.
3. Fotos: como agricultor, el visitante envía una foto de cada campo (predeterminada o propia) y la IA detecta plagas y enfermedades, la superficie afectada y la pérdida de cosecha estimada.
4. Previsión de campaña: la demo de previsión (carpeta `prevision/`) con el escenario «Según tus fotos», los campos en el mapa de Navarra y avisos por campo.
   - «Según tus fotos» es un escenario más: aparece en «¿Y si…?», en el sello y en la comparativa «¿Qué escenario pesa más?».
   - **Cosechas:** el visitante puede guardar el diagnóstico de sus fotos con nombre y fecha («Guardar cosecha»). Se recuerda en ese navegador y aparece como escenario para compararla en otra visita.
   - **¿De dónde salen estos números?** está siempre visible: fichas de cada fuente real (Meteo Navarra, OMIE, OMIP, Ministerio, INE), la de «Tus fotos» y la de lo simulado.

## Estructura (lo nuevo)

```
app.py                     Recorrido completo en Streamlit
calidad/sanidad.py         Cultivos, comarcas, fotos predeterminadas y análisis de plagas/enfermedades
calidad/prevision.py       Monta la previsión en una sola página y le pasa los campos (window.DEMO_TAIREL)
calidad/estilo.py          Estilos comunes
prevision/                 Demo de previsión (HTML/JS) adaptada: palanca «Plagas y enfermedades»,
                           escenario «Según tus fotos», campos en el mapa y avisos por campo
ejemplos/campos/           Fotos predeterminadas de los campos (ver LEEME.md) y resultados.json
```

La palanca nueva de `prevision/motor.js` (`plaga`, % de cosecha perdida) es solo de escenario, como el precio de venta: no cambia el modelo entrenado ni `comun.py`, y `probar_motor.js` sigue dando el mismo resultado. Efecto: en IV gama sube la merma, en congelado baja el rendimiento de campaña y encarece el kilo útil, y en cereal hay menos grano que vender.

El inspector de calidad de la primera versión (`calidad/analizador.py`, `calidad/productos.py`) sigue disponible como módulo; `analizador.py` aporta las llamadas a Anthropic/OpenAI que usan los dos análisis.

## 1. Probar en local

```bash
python -m venv .venv && .venv\Scripts\activate      # en Windows
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # y rellena las claves
streamlit run app.py
```

Para probar sin gastar API, pon `PROVEEDOR = "simulado"` (devuelve un informe de ejemplo marcado como simulado).

Para probarlo en el móvil dentro de la misma wifi: `streamlit run app.py --server.address 0.0.0.0` y abre `http://IP-DEL-PORTÁTIL:8501`.

## 2. Fotos de ejemplo de los campos

Lista de fotos y nombres en `ejemplos/campos/LEEME.md`. Después: `python precalcular.py`.

## 2b. Galería del inspector de calidad (versión anterior)

La pestaña "Ejemplos" aparece en cuanto hay alguna foto en `ejemplos/` con el nombre indicado en `ejemplos.json`. Recomendación: una pieza buena y una con defectos claros por producto.

- tomate_bueno.jpg / tomate_defecto.jpg (grieta, golpe o podredumbre apical)
- brocoli_bueno.jpg / brocoli_defecto.jpg (floretes amarillos o manchas)
- pimiento_bueno.jpg / pimiento_defecto.jpg (golpe de sol, arrugas)
- melocoton_bueno.jpg / melocoton_defecto.jpg (golpe, monilia)
- lechuga.jpg (con algo de tip burn si es posible)
- cereal.jpg (puñado de grano con algún partido o impureza)

Consejos de foto: fondo liso claro, luz natural o difusa, una pieza centrada, sin sombras duras. Las fotos propias funcionan mejor que las de internet y evitan problemas de derechos.

Después ejecuta `python precalcular.py`. Revisa `ejemplos/resultados.json`: si algún informe no te convence, cambia la foto y repite. Los ejemplos ya no consumen API durante el evento y funcionan aunque la red falle.

Puedes cambiar los títulos de los botones en `ejemplos.json` (por defecto "A" y "B" para que el visitante adivine cuál es la buena).

## 3. Desplegar en Streamlit Community Cloud (gratis)

1. Sube la carpeta a un repositorio de GitHub (el `.gitignore` ya excluye `secrets.toml`).
2. En share.streamlit.io: New app, elige el repo, rama y `app.py`. En Advanced settings elige Python 3.12.
3. En Settings > Secrets pega el contenido de tu `secrets.toml`.
4. Elige un subdominio fácil, por ejemplo `tairel-calidad.streamlit.app`.

Si tenéis dominio, crea una redirección `demo.taireldata.com` hacia esa URL y pon esa dirección en el QR: así podéis cambiar el alojamiento sin reimprimir nada.

## 4. QR

```bash
python generar_qr.py https://demo.taireldata.com
```

Genera `qr_demo.png` en azul Tairel con el icono en el centro. Úsalo en la última diapositiva y en un cartel del stand. Pruébalo desde varios móviles y a la distancia real de la pantalla.

## Configuración (secrets)

| Clave | Para qué |
|---|---|
| PROVEEDOR | anthropic, openai o simulado |
| ANTHROPIC_API_KEY / OPENAI_API_KEY | Con las dos, si el principal falla se usa el otro |
| ANTHROPIC_MODEL / OPENAI_MODEL | Por defecto claude-sonnet-5-5 y gpt-6.1-sol; más baratos: claude-haiku-5-5, gpt-6-luna |
| LIMITE_POR_SESION / LIMITE_GLOBAL_HORA | Topes de uso para controlar el gasto |
| EMAIL_CONTACTO / WEB_CONTACTO / FORMULARIO_LEADS | Botones de la llamada a la acción |
| MOSTRAR_DIAGNOSTICO | "1" muestra un panel técnico al final |

Pon también un límite de gasto mensual en la consola de cada proveedor.

## Checklist del día del evento

- Abrir la demo 10 minutos antes del pitch (los planes gratuitos se duermen tras un rato sin uso).
- Probar una foto real con datos móviles, no solo con wifi.
- Llevar fruta y verdura al stand, incluidas piezas con defectos.
- Tener un vídeo grabado de la demo por si falla la conexión.
- Dejar la diapositiva del QR en pantalla durante las preguntas.

## Privacidad

Las imágenes se envían al proveedor de IA solo para generar el informe y la app no las guarda. Los resultados se cachean en memoria del servidor mientras la app está activa para no repetir llamadas con la misma imagen.

## Contactos (leads) en Google Sheets

El formulario del final de la app guarda cada contacto (fecha, correo, nombre, empresa, producto probado, categoría obtenida, consentimiento) como una fila en la pestaña "Leads" de una hoja de Google Sheets. Instrucciones de instalación dentro de `google_sheets_leads.gs`. Después añade `LEADS_WEBHOOK_URL` y `LEADS_TOKEN` a los Secrets.

Si la hoja no responde, el contacto no se pierde: aparece en el registro de la app (Manage app) en una línea que empieza por `LEAD_PENDIENTE`.

Para la automatización: Archivo > Descargar > CSV, o leer la hoja directamente con su conector de Google Sheets. No publiquéis la hoja en la web, porque contiene datos personales.
