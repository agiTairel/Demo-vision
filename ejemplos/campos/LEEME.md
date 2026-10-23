# Fotos de ejemplo de los campos

Cada cultivo tiene su carpeta. La app muestra todas las fotos que haya dentro de la carpeta del cultivo que elige el visitante (JPG, JPEG, PNG o WEBP), y siempre ofrece también hacer o subir una foto propia.

Carpetas: `lechuga/`, `canonigo/` (o `canonigos/`), `espinaca/`, `brocoli/`, `guisante/`, `trigo/`, `cebada/`, `maiz/`.

El texto del botón sale del nombre del archivo:

- `..._sano` / `..._sana` → "Planta sana"
- `..._malo` / `..._mal` → "Planta con síntomas"
- `..._manchas` → "Hojas con manchas"
- `..._quemada` / `..._bordes` → "Bordes de hoja quemados"
- `..._oidio` → "Polvo blanco en las hojas"
- `..._mildiu` → "Manchas amarillas en las hojas"
- `..._roya` → "Pústulas en las hojas"
- `..._hongo` / `..._moho` → "Con moho"
- `..._amarillo` → "Floretes amarilleando"
- `..._oruga` / `..._plaga` → "Hojas mordidas"
- `..._taladro` → "Tallo o mazorca perforados"
- `..._espiga` → "Espigas blanquecinas"

Si la palabra no está en la lista, se usa tal cual (por ejemplo `trigo_granizo.jpg` → "Granizo").

Después de añadir o cambiar fotos, ejecuta `python precalcular.py`: deja los informes calculados en `resultados.json` para que salgan al instante y no gasten API en el evento.
