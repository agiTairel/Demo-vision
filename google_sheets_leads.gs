/**
 * Demo IA para el campo · Tairel Data
 *
 * 1. Recibe los contactos de la demo y los añade a la pestaña "Leads" con estado "pendiente".
 * 2. Cuando el visitante pulsa «Descargar mi informe», recibe sus tres PDF, los guarda en una carpeta
 *    privada de Google Drive y deja cada link en su columna, al final de la hoja:
 *      link_ficha_incidencia · link_dossier_resumen · link_informe_costes
 * 3. Cada día a las 8:00 (hora de Madrid) recorre los "pendiente" de días anteriores y les envía un correo
 *    con esos PDF adjuntos. Después cambia el estado a "enviado dd/mm/aaaa hh:mm".
 *
 * Instalación (o actualización, si ya teníais el script anterior):
 * 1. Abre la hoja con la cuenta que enviará los correos (info@taireldata.com, o una cuenta que tenga
 *    info@ como alias en Gmail). Extensiones > Apps Script.
 * 2. Pega este archivo sustituyendo todo y rellena SHEET_ID y TOKEN (el mismo TOKEN que LEADS_TOKEN en Streamlit).
 *    CARPETA_ID puede quedarse vacío: la primera vez se crea la carpeta "Demo IA campo · documentos" en tu Drive.
 * 3. Elige la función "probar" y pulsa Ejecutar. Acepta los permisos (Hojas, Drive y Gmail).
 *    Se añaden las tres columnas nuevas al final y una fila de prueba con sus tres links.
 * 4. Elige "instalarEnvioDiario" y pulsa Ejecutar: deja programado el envío de cada día a las 8:00.
 * 5. Implementar > Gestionar implementaciones > lápiz > Versión: "Nueva versión" > Implementar.
 *    (Ejecutar como: Yo · Quién tiene acceso: Cualquier usuario). La URL /exec no cambia.
 *
 * Para ver el correo antes del evento: ejecuta "vistaPrevia" (te lo envía a ti con la última fila que tenga
 * archivos, sin cambiar su estado). Para enviar ya los pendientes sin esperar a las 8:00: "enviarPendientes".
 *
 * La hoja contiene datos personales: no la publiquéis en la web ni la compartáis fuera del equipo.
 */

const SHEET_ID = 'PEGA_AQUI_EL_ID_DE_LA_HOJA';
const TOKEN = 'cambia-esto-por-una-clave-larga';
const PESTANA = 'Leads';
const CARPETA_ID = '';                      // vacío = se crea sola la primera vez
const ZONA = 'Europe/Madrid';
const HORA_ENVIO = 8;
const REMITENTE = 'info@taireldata.com';    // se usa si es tu cuenta o uno de tus alias de Gmail
const NOMBRE_REMITENTE = 'Tairel Data';
const WEB = 'https://taireldata.com';
const ASUNTO = 'Tu informe de campaña · Demo IA para el campo';
const ENVIAR_SIN_ARCHIVOS = false;          // true = también escribe a quien no descargó su informe (correo sin adjuntos)
const MAX_MB = 20;

const CABECERA = ['fecha_utc', 'email', 'nombre', 'empresa', 'producto_probado',
                  'categoria_obtenida', 'consentimiento', 'origen', 'estado_seguimiento'];
const LINKS = { ficha: 'link_ficha_incidencia', dossier: 'link_dossier_resumen', costes: 'link_informe_costes' };
const ADJUNTO = { ficha: 'Ficha de incidencia', dossier: 'Dossier resumen', costes: 'Informe completo de tu previsión de campaña' };

// ───────────────────────── Peticiones de la app ─────────────────────────

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    const accion = d.accion || 'lead';
    if (accion === 'lead') {
      if (d.token !== TOKEN) return respuesta({ ok: false, error: 'token' });
      guardar(d);
      return respuesta({ ok: true });
    }
    if (accion === 'archivo' || accion === 'archivos') {
      // La ficha y el dossier pueden llegar desde Python (con TOKEN) o, como el informe de costes, desde la
      // página al pulsar el botón (sin TOKEN). En los dos casos solo se aceptan PDF para un id_lead que exista:
      // es un identificador aleatorio que solo conoce la sesión de ese visitante.
      const lista = accion === 'archivo' ? [d] : (d.archivos || []);
      const links = guardarArchivos(d.id_lead, lista);
      return respuesta({ ok: true, links: links, link: links[lista[0] && lista[0].tipo] || '' });
    }
    return respuesta({ ok: false, error: 'accion desconocida' });
  } catch (err) {
    console.error(err);
    return respuesta({ ok: false, error: String(err && err.message || err) });
  }
}

function guardar(d) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const hoja = hojaLeads();
    const col = columnas(hoja);
    const fila = new Array(hoja.getLastColumn()).fill('');
    const valores = {
      fecha_utc: d.fecha_utc, email: d.email, nombre: d.nombre, empresa: d.empresa, producto_probado: d.producto,
      categoria_obtenida: d.categoria, consentimiento: d.consentimiento ? 'sí' : 'no', origen: d.origen,
      estado_seguimiento: 'pendiente'
    };
    Object.keys(valores).forEach((k) => { fila[col[k] - 1] = valores[k] == null ? '' : valores[k]; });
    hoja.appendRow(fila);
    if (d.id_lead) {
      PropertiesService.getScriptProperties().setProperty('lead_' + d.id_lead,
        JSON.stringify({ email: String(d.email || '').toLowerCase(), fila: hoja.getLastRow() }));
    }
  } finally {
    lock.releaseLock();
  }
}

function guardarArchivos(idLead, lista) {
  if (!idLead || !/^[0-9a-f]{32}$/.test(idLead)) throw new Error('id_lead no válido');
  const props = PropertiesService.getScriptProperties();
  const reg = props.getProperty('lead_' + idLead);
  if (!reg) throw new Error('id_lead desconocido');
  const lead = JSON.parse(reg);
  const carpeta = carpetaDocumentos();
  const links = {};
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const hoja = hojaLeads();
    const col = columnas(hoja);
    const fila = filaDe(hoja, col, lead);
    if (!fila) throw new Error('No encuentro la fila del visitante');
    lead.fila = fila;
    lista.forEach((a) => {
      if (!LINKS[a.tipo]) throw new Error('tipo no válido: ' + a.tipo);
      const bytes = Utilities.base64Decode(a.base64 || '');
      if (bytes.length > MAX_MB * 1024 * 1024) throw new Error('archivo demasiado grande');
      if (String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]) !== '%PDF') throw new Error('no es un PDF');
      const nombre = String(a.nombre || a.tipo + '.pdf').replace(/[^\w.\-áéíóúñÁÉÍÓÚÑ ]/g, '_').slice(0, 120);
      const celda = hoja.getRange(fila, col[LINKS[a.tipo]]);
      const anterior = idDeLink(celda.getValue());
      if (anterior) { try { DriveApp.getFileById(anterior).setTrashed(true); } catch (e) { /* ya no existe */ } }
      const archivo = carpeta.createFile(Utilities.newBlob(bytes, 'application/pdf', nombre));
      archivo.setDescription('Demo IA para el campo · ' + lead.email + ' · ' + a.tipo);
      celda.setValue(archivo.getUrl());
      links[a.tipo] = archivo.getUrl();
      if (a.resumen) lead.resumen = String(a.resumen).slice(0, 600);
    });
    props.setProperty('lead_' + idLead, JSON.stringify(lead));
  } finally {
    lock.releaseLock();
  }
  return links;
}

// ───────────────────────── Envío diario ─────────────────────────

/** Lo ejecuta el activador cada día a las 8:00: envía los "pendiente" de días anteriores. */
function enviarPendientes() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return;
  try {
    const hoja = hojaLeads();
    const col = columnas(hoja);
    const datos = hoja.getDataRange().getValues();
    const hoy = Utilities.formatDate(new Date(), ZONA, 'yyyy-MM-dd');
    const resumenes = resumenesPorFila();
    let enviados = 0;
    for (let i = 1; i < datos.length; i++) {
      const r = datos[i], fila = i + 1;
      const estado = String(r[col.estado_seguimiento - 1] || '').trim().toLowerCase();
      if (estado !== 'pendiente') continue;
      if (diaDe(r[col.fecha_utc - 1]) >= hoy) continue;                 // los de hoy, mañana
      const email = String(r[col.email - 1] || '').trim();
      if (String(r[col.consentimiento - 1]).trim().toLowerCase() !== 'sí' || !/@/.test(email)) {
        hoja.getRange(fila, col.estado_seguimiento).setValue('sin consentimiento');
        continue;
      }
      const ids = {};
      Object.keys(LINKS).forEach((t) => { const id = idDeLink(r[col[LINKS[t]] - 1]); if (id) ids[t] = id; });
      if (!Object.keys(ids).length && !ENVIAR_SIN_ARCHIVOS) {
        hoja.getRange(fila, col.estado_seguimiento).setValue('sin informe');
        continue;
      }
      if (MailApp.getRemainingDailyQuota() < 1) { console.warn('Cupo diario de Gmail agotado; el resto queda pendiente'); break; }
      try {
        enviarCorreo(email, String(r[col.nombre - 1] || ''), String(r[col.empresa - 1] || ''), ids, resumenes[fila]);
        hoja.getRange(fila, col.estado_seguimiento).setValue('enviado ' + Utilities.formatDate(new Date(), ZONA, 'dd/MM/yyyy HH:mm'));
        enviados++;
      } catch (err) {
        console.error('Fila ' + fila + ': ' + err);
        hoja.getRange(fila, col.estado_seguimiento).setNote('Error al enviar (' + Utilities.formatDate(new Date(), ZONA, 'dd/MM HH:mm') + '): ' + err);
      }
    }
    console.log('Correos enviados: ' + enviados);
  } finally {
    lock.releaseLock();
  }
}

function enviarCorreo(para, nombre, empresa, ids, resumen) {
  const adjuntos = [], incluidos = [];
  ['ficha', 'dossier', 'costes'].forEach((t) => {
    if (!ids[t]) return;
    const f = DriveApp.getFileById(ids[t]);
    adjuntos.push(f.getBlob().setName(f.getName()));
    incluidos.push(ADJUNTO[t]);
  });
  const html = cuerpoCorreo(nombre, empresa, incluidos, resumen);
  const opciones = { htmlBody: html, attachments: adjuntos, name: NOMBRE_REMITENTE, replyTo: REMITENTE };
  const yo = Session.getEffectiveUser().getEmail().toLowerCase();
  if (REMITENTE && REMITENTE.toLowerCase() !== yo && GmailApp.getAliases().map((a) => a.toLowerCase()).indexOf(REMITENTE.toLowerCase()) >= 0) {
    opciones.from = REMITENTE;
  }
  GmailApp.sendEmail(para, ASUNTO, textoPlano(html), opciones);
}

function cuerpoCorreo(nombre, empresa, incluidos, resumen) {
  const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const n = esc(String(nombre || '').trim().split(' ')[0]);
  const de = empresa ? ' de ' + esc(empresa) : ' de tu explotación';
  const lista = incluidos.length
    ? '<p style="margin:18px 0 6px;font-weight:700;color:#1f2a1f">Te adjuntamos:</p><ul style="margin:0 0 18px;padding-left:20px">' +
      incluidos.map((x) => '<li style="margin:4px 0">' + esc(x) + '</li>').join('') + '</ul>'
    : '';
  return '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.55;color:#33413a;max-width:600px">' +
    '<div style="border-top:4px solid #e2ac24;background:#1f5a23;color:#fff;padding:18px 22px;border-radius:6px 6px 0 0">' +
    '<div style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#cfe3c8">Demo IA para el campo</div>' +
    '<div style="font-size:21px;font-weight:700;margin-top:4px">Tu informe de campaña</div></div>' +
    '<div style="padding:20px 22px;border:1px solid #dfe5d6;border-top:0;border-radius:0 0 6px 6px">' +
    '<p style="margin:0 0 12px">Hola' + (n ? ' ' + n : '') + ':</p>' +
    '<p style="margin:0 0 12px">Gracias por probar ayer nuestra demo. Con lo que nos contaste de tus campos, el sistema preparó solo, ' +
    'sin que nadie lo pidiera, la documentación de la incidencia y la previsión de ventas, costes y margen' + de + '.</p>' +
    (resumen ? '<p style="margin:0 0 12px;padding:10px 14px;background:#eef3e6;border-radius:6px">' + esc(resumen) + '</p>' : '') +
    lista +
    '<p style="margin:0 0 12px">Lo que viste es un caso de demostración. Con vuestros datos reales, el aviso de un campo llega en el momento ' +
    'a quien decide tratamientos, compras, precios y contratos, en vez de tardar días y horas de trabajo técnico.</p>' +
    '<p style="margin:20px 0"><a href="' + WEB + '" style="background:#2f7d32;color:#fff;text-decoration:none;font-weight:700;' +
    'padding:12px 20px;border-radius:5px;display:inline-block">Quiero verlo con mis datos</a></p>' +
    '<p style="margin:0">O responde a este correo y te llamamos.</p>' +
    '<p style="margin:18px 0 0">Un saludo,<br><b>Equipo de Tairel Data</b><br><a href="' + WEB + '" style="color:#2f7d32">' + WEB.replace(/^https?:\/\//, '') + '</a></p>' +
    '<p style="margin:22px 0 0;font-size:12px;color:#7d8a78">Recibes este correo porque te registraste en la demo y aceptaste que te contactáramos. ' +
    'Si no quieres recibir más, responde con «baja».</p></div></div>';
}

/** Activador diario a las 8:00 (Google lo lanza entre las 8:00 y las 8:15 aproximadamente). */
function instalarEnvioDiario() {
  ScriptApp.getProjectTriggers().filter((t) => t.getHandlerFunction() === 'enviarPendientes').forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('enviarPendientes').timeBased().everyDays(1).atHour(HORA_ENVIO).nearMinute(0).inTimezone(ZONA).create();
  console.log('Envío diario programado a las ' + HORA_ENVIO + ':00 (' + ZONA + ')');
}

// ───────────────────────── Pruebas desde el editor ─────────────────────────

/** Da permisos, añade las columnas nuevas y crea una fila de prueba con sus tres links. */
function probar() {
  const id = Utilities.getUuid().replace(/-/g, '');
  guardar({ id_lead: id, fecha_utc: new Date().toISOString(), email: Session.getEffectiveUser().getEmail(), nombre: 'Prueba',
            empresa: 'Tairel', producto: 'Prueba desde el editor', categoria: '', consentimiento: true, origen: 'Prueba desde el editor' });
  const pdf = Utilities.newBlob('%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj ' +
    '3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF').getBytes();
  const b64 = Utilities.base64Encode(pdf);
  console.log(guardarArchivos(id, [{ tipo: 'ficha', nombre: 'prueba_ficha.pdf', base64: b64 },
                                   { tipo: 'dossier', nombre: 'prueba_dossier.pdf', base64: b64, resumen: 'Fila de prueba.' },
                                   { tipo: 'costes', nombre: 'prueba_costes.pdf', base64: b64 }]));
}

/** Te envía a ti el correo de la última fila con archivos, sin cambiar su estado. */
function vistaPrevia() {
  const hoja = hojaLeads(), col = columnas(hoja), datos = hoja.getDataRange().getValues(), res = resumenesPorFila();
  for (let i = datos.length - 1; i >= 1; i--) {
    const ids = {};
    Object.keys(LINKS).forEach((t) => { const id = idDeLink(datos[i][col[LINKS[t]] - 1]); if (id) ids[t] = id; });
    if (Object.keys(ids).length) {
      enviarCorreo(Session.getEffectiveUser().getEmail(), String(datos[i][col.nombre - 1]), String(datos[i][col.empresa - 1]), ids, res[i + 1]);
      console.log('Vista previa enviada con la fila ' + (i + 1));
      return;
    }
  }
  console.log('Ninguna fila tiene archivos todavía');
}

// ───────────────────────── Utilidades ─────────────────────────

function hojaLeads() {
  const libro = SpreadsheetApp.openById(SHEET_ID);
  const hoja = libro.getSheetByName(PESTANA) || libro.insertSheet(PESTANA);
  if (hoja.getLastRow() === 0) hoja.appendRow(CABECERA);
  return hoja;
}

/** {nombre de columna: número}. Añade al final las columnas de links si aún no existen. */
function columnas(hoja) {
  let cab = hoja.getRange(1, 1, 1, Math.max(1, hoja.getLastColumn())).getValues()[0].map((x) => String(x).trim());
  const faltan = CABECERA.concat(Object.values(LINKS)).filter((c) => cab.indexOf(c) < 0);
  if (faltan.length) {
    hoja.getRange(1, cab.filter(String).length + 1, 1, faltan.length).setValues([faltan]);
    cab = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0].map((x) => String(x).trim());
  }
  const col = {};
  cab.forEach((c, i) => { if (c) col[c] = i + 1; });
  return col;
}

function filaDe(hoja, col, lead) {
  const ultima = hoja.getLastRow();
  if (lead.fila && lead.fila <= ultima &&
      String(hoja.getRange(lead.fila, col.email).getValue()).trim().toLowerCase() === lead.email) return lead.fila;
  const emails = hoja.getRange(1, col.email, ultima, 1).getValues();   // si alguien reordenó la hoja
  for (let i = emails.length - 1; i >= 1; i--) if (String(emails[i][0]).trim().toLowerCase() === lead.email) return i + 1;
  return null;
}

function resumenesPorFila() {
  const res = {}, props = PropertiesService.getScriptProperties().getProperties();
  Object.keys(props).forEach((k) => {
    if (k.indexOf('lead_') !== 0) return;
    try { const l = JSON.parse(props[k]); if (l.resumen && l.fila) res[l.fila] = l.resumen; } catch (e) { /* ignorar */ }
  });
  return res;
}

function carpetaDocumentos() {
  const props = PropertiesService.getScriptProperties();
  const id = CARPETA_ID || props.getProperty('carpeta_id');
  if (id) return DriveApp.getFolderById(id);
  const c = DriveApp.createFolder('Demo IA campo · documentos');
  props.setProperty('carpeta_id', c.getId());
  return c;
}

function idDeLink(v) {
  const m = String(v || '').match(/\/d\/([\w-]{20,})/) || String(v || '').match(/[?&]id=([\w-]{20,})/);
  return m ? m[1] : null;
}

function diaDe(v) {
  if (v instanceof Date) return Utilities.formatDate(v, ZONA, 'yyyy-MM-dd');
  const d = new Date(String(v).replace(' ', 'T') + (/[zZ]|[+-]\d\d:?\d\d$/.test(String(v)) ? '' : 'Z'));
  return isNaN(d) ? '0000-00-00' : Utilities.formatDate(d, ZONA, 'yyyy-MM-dd');
}

function textoPlano(html) {
  return html.replace(/<(br|\/p|\/li|\/div)[^>]*>/gi, '\n').replace(/<li[^>]*>/gi, '• ').replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\n{3,}/g, '\n\n').trim();
}

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
