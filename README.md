# Inspector de calidad con IA · Tairel Data

Demo web para móvil: el visitante escanea el QR, hace una foto a un producto (o elige un ejemplo) y recibe un informe de calidad con categoría comercial, madurez, defectos, color y destino recomendado. El análisis lo hace un modelo de visión por API (Anthropic u OpenAI, configurable y con respaldo automático).

Productos incluidos: tomate, brócoli, pimiento, melocotón/nectarina, lechuga (IV gama) y cereal en grano, además de detección automática.

## Estructura

```
app.py                     Interfaz Streamlit
calidad/analizador.py      Prompt, esquema JSON, llamadas a Anthropic/OpenAI, respaldo, imagen
calidad/productos.py       Catálogo de productos y criterios de calidad
ejemplos/                  Fotos de la galería + ejemplos.json + resultados.json (precalculados)
precalcular.py             Genera resultados.json para que la galería sea instantánea
generar_qr.py              QR con colores e icono de Tairel
assets/                    Logo e icono
.streamlit/                Tema y plantilla de secretos
```

## 1. Probar en local

```bash
python -m venv .venv && .venv\Scripts\activate      # en Windows
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # y rellena las claves
streamlit run app.py
```

Para probar sin gastar API, pon `PROVEEDOR = "simulado"` (devuelve un informe de ejemplo marcado como simulado).

Para probarlo en el móvil dentro de la misma wifi: `streamlit run app.py --server.address 0.0.0.0` y abre `http://IP-DEL-PORTÁTIL:8501`.

## 2. Fotos de ejemplo

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

## Privacidad

Las imágenes se envían al proveedor de IA solo para generar el informe y la app no las guarda. Los resultados se cachean en memoria del servidor mientras la app está activa para no repetir llamadas con la misma imagen.
