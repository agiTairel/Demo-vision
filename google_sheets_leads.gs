/**
 * Recibe los contactos de la demo y los añade a la pestaña "Leads".
 *
 * Instalación:
 * 1. Copia el ID de tu hoja: es la parte de la URL entre /d/ y /edit
 *    https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
 * 2. Pega este archivo en Apps Script (sustituyendo todo) y rellena SHEET_ID y TOKEN.
 * 3. Arriba, elige la función "probar" y pulsa Ejecutar. Acepta los permisos.
 *    Debe aparecer una fila de prueba en la pestaña "Leads".
 * 4. Implementar > Gestionar implementaciones > lápiz > Versión: "Nueva versión" > Implementar.
 *    (Ejecutar como: Yo · Quién tiene acceso: Cualquier usuario)
 */

const SHEET_ID = 'PEGA_AQUI_EL_ID_DE_LA_HOJA';
const TOKEN = 'cambia-esto-por-una-clave-larga';
const PESTANA = 'Leads';
const CABECERA = ['fecha_utc', 'email', 'nombre', 'empresa', 'producto_probado',
                  'categoria_obtenida', 'consentimiento', 'origen', 'estado_seguimiento'];

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.token !== TOKEN) return respuesta({ ok: false, error: 'token' });
    guardar(d);
    return respuesta({ ok: true });
  } catch (err) {
    return respuesta({ ok: false, error: String(err) });
  }
}

function guardar(d) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const libro = SpreadsheetApp.openById(SHEET_ID);
    const hoja = libro.getSheetByName(PESTANA) || libro.insertSheet(PESTANA);
    if (hoja.getLastRow() === 0) hoja.appendRow(CABECERA);
    hoja.appendRow([
      d.fecha_utc, d.email, d.nombre, d.empresa, d.producto, d.categoria,
      d.consentimiento ? 'sí' : 'no', d.origen, 'pendiente'
    ]);
  } finally {
    lock.releaseLock();
  }
}

/** Ejecútala una vez desde el editor para dar permisos y comprobar que escribe. */
function probar() {
  guardar({ fecha_utc: new Date().toISOString(), email: 'prueba@ejemplo.com', nombre: 'Prueba',
            empresa: 'Tairel', producto: '', categoria: '', consentimiento: true,
            origen: 'Prueba desde el editor' });
}

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
