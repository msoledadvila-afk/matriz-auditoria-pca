/**
 * Relay de mail del Diagnóstico PCA™ — Talento Impulsa Consulting
 *
 * Por qué existe: el plan gratuito de Render bloquea las conexiones salientes
 * a los puertos SMTP (25, 465 y 587), así que el backend no puede mandar mail
 * por smtp.gmail.com. Este script se publica como app web desde la casilla
 * hola@talentoimpulsa.com.ar: el backend le hace un POST por HTTPS (puerto
 * 443, que sí está permitido) y el script envía el mail.
 *
 * Por qué GmailApp y no MailApp (21/10/2026): Gmail rechazaba en el acto
 * ("Message rejected") TODO lo que salía con MailApp desde esta casilla,
 * incluso un texto plano de una línea. Con GmailApp el mismo contenido llega a
 * la bandeja principal de Gmail. GmailApp envía como un mail escrito desde la
 * bandeja de hola@ (queda en "Enviados"). Prueba completa en
 * PruebaEntregaGmail.gs.
 *
 * Seguridad:
 *  - Solo acepta pedidos que traigan la clave guardada en Propiedades del
 *    script (RELAY_TOKEN). La clave NUNCA va escrita en este archivo.
 *  - Valida destinatario, asunto y tamaño del HTML.
 *  - Se publica con "Ejecutar como: Yo" y "Quién tiene acceso: Cualquier
 *    persona": la clave es lo que protege el envío.
 *
 * Configuración (una sola vez):
 *  0. Configuración del proyecto → "Mostrar el archivo de manifiesto" y pegar
 *     appsscript.json de esta carpeta (declara los permisos de envío de mail,
 *     incluido https://mail.google.com/ que necesita GmailApp).
 *  1. Configuración del proyecto (engranaje) → Propiedades del script →
 *     agregar RELAY_TOKEN con una clave larga al azar.
 *  2. Implementar → Nueva implementación → Aplicación web →
 *     Ejecutar como: Yo · Acceso: Cualquier persona → Implementar.
 *     (Para actualizar sin cambiar la URL: Implementar → Gestionar
 *     implementaciones → lápiz → Versión: "Nueva versión" → Implementar.)
 *  3. Copiar la URL que termina en /exec y cargarla en Render como
 *     MAIL_RELAY_URL, y la misma clave como MAIL_RELAY_TOKEN.
 *
 * Prueba manual: ejecutar la función probarRelay() desde el editor.
 */

var NOMBRE_REMITENTE = 'Talento Impulsa Consulting';
var RESPONDER_A = 'hola@talentoimpulsa.com.ar';
var MAX_HTML = 100000;          // ~100 KB: un resultado del diagnóstico pesa ~5 KB
var MAX_ASUNTO = 200;
var REGEX_EMAIL = /^[^@\s<>"',;]+@[^@\s<>"',;]+\.[^@\s<>"',;]+$/;

function doPost(e) {
  try {
    var datos = JSON.parse((e && e.postData && e.postData.contents) || '{}');

    var tokenEsperado = PropertiesService.getScriptProperties().getProperty('RELAY_TOKEN');
    if (!tokenEsperado) {
      return responder_({ ok: false, error: 'relay sin configurar (falta RELAY_TOKEN)' });
    }
    if (!datos.token || !compararSeguro_(String(datos.token), tokenEsperado)) {
      return responder_({ ok: false, error: 'no autorizado' });
    }

    var para = String(datos.to || '').trim();
    var asunto = String(datos.subject || '').trim().slice(0, MAX_ASUNTO);
    var html = String(datos.html || '');

    if (!REGEX_EMAIL.test(para)) {
      return responder_({ ok: false, error: 'destinatario inválido' });
    }
    if (!asunto || !html) {
      return responder_({ ok: false, error: 'faltan asunto o contenido' });
    }
    if (html.length > MAX_HTML) {
      return responder_({ ok: false, error: 'contenido demasiado grande' });
    }
    if (MailApp.getRemainingDailyQuota() < 1) {
      return responder_({ ok: false, error: 'cuota diaria de mails agotada' });
    }

    // Si el backend no manda versión en texto plano, se arma desde el HTML:
    // un mail con las dos versiones es mejor recibido que uno solo HTML.
    var texto = datos.text ? String(datos.text) : htmlATexto_(html);

    // GmailApp rompe los caracteres fuera del plano básico de Unicode (📂 🎯 🚀
    // llegaban como "������"; ⏱ y ⚙️ no se rompen). En el HTML se mandan como
    // entidad numérica, que es ASCII puro y Gmail vuelve a mostrar como emoji;
    // en el texto plano se quitan. Lo mismo en el asunto, por las dudas.
    asunto = quitarAstrales_(asunto);
    texto = quitarAstrales_(texto);
    html = astralesAEntidades_(html);

    GmailApp.sendEmail(para, asunto, texto, {
      htmlBody: html,
      name: NOMBRE_REMITENTE,
      replyTo: RESPONDER_A
    });

    return responder_({ ok: true, cuota_restante: MailApp.getRemainingDailyQuota() });
  } catch (err) {
    console.error('Relay: error al enviar', err);
    return responder_({ ok: false, error: 'error interno al enviar' });
  }
}

// Si alguien abre la URL en el navegador, no revela nada.
function doGet() {
  return responder_({ ok: true, servicio: 'relay diagnóstico PCA' });
}

function responder_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Versión en texto plano del HTML del resultado: saltos de línea donde había
// bloques, sin etiquetas, con las entidades básicas decodificadas.
function htmlATexto_(html) {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|h[1-6]|li)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/[ \t]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

var REGEX_ASTRAL = /[\uD800-\uDBFF][\uDC00-\uDFFF]/g;

function astralesAEntidades_(s) {
  return s.replace(REGEX_ASTRAL, function (par) {
    return '&#' + par.codePointAt(0) + ';';
  });
}

function quitarAstrales_(s) {
  return s.replace(REGEX_ASTRAL, '').replace(/[ \t]{2,}/g, ' ').replace(/^ +/gm, '');
}

// Comparación en tiempo constante para no filtrar la clave por tiempos de respuesta.
function compararSeguro_(a, b) {
  if (a.length !== b.length) return false;
  var diferencia = 0;
  for (var i = 0; i < a.length; i++) {
    diferencia |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diferencia === 0;
}

/**
 * Prueba desde el editor (Ejecutar → probarRelay): manda un mail de prueba a
 * DESTINO_PRUEBA pasando por la misma validación que un pedido real.
 */
var DESTINO_PRUEBA = 'msoledadvila@gmail.com';

function probarRelay() {
  var token = PropertiesService.getScriptProperties().getProperty('RELAY_TOKEN');
  var evento = {
    postData: {
      contents: JSON.stringify({
        token: token,
        to: DESTINO_PRUEBA,
        subject: 'Prueba relay Diagnóstico PCA',
        html: '<p>Si te llegó este mail, el relay funciona.</p>' +
              '<p>Emojis: 📂 🎯 🚀 🧭 👥 🏛️ ⏱ ⚙️ 💬</p>'
      })
    }
  };
  var salida = doPost(evento).getContent();
  console.log(salida);
}
