/**
 * Relay de mail del Diagnóstico PCA™ — Talento Impulsa Consulting
 *
 * Por qué existe: el plan gratuito de Render bloquea las conexiones salientes
 * a los puertos SMTP (25, 465 y 587), así que el backend no puede mandar mail
 * por smtp.gmail.com. Este script se publica como app web desde la casilla
 * hola@talentoimpulsa.com.ar: el backend le hace un POST por HTTPS (puerto
 * 443, que sí está permitido) y el script envía el mail con MailApp.
 *
 * Seguridad:
 *  - Solo acepta pedidos que traigan la clave guardada en Propiedades del
 *    script (RELAY_TOKEN). La clave NUNCA va escrita en este archivo.
 *  - Valida destinatario, asunto y tamaño del HTML.
 *  - Se publica con "Ejecutar como: Yo" y "Quién tiene acceso: Cualquier
 *    persona": la clave es lo que protege el envío.
 *
 * Configuración (una sola vez):
 *  1. Configuración del proyecto (engranaje) → Propiedades del script →
 *     agregar RELAY_TOKEN con una clave larga al azar.
 *  2. Implementar → Nueva implementación → Aplicación web →
 *     Ejecutar como: Yo · Acceso: Cualquier persona → Implementar.
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

    MailApp.sendEmail({
      to: para,
      subject: asunto,
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
 * Prueba desde el editor (Ejecutar → probarRelay): se manda un mail de prueba
 * a la propia casilla, pasando por la misma validación que un pedido real.
 * La primera vez pide autorizar permisos para enviar mail.
 */
function probarRelay() {
  var token = PropertiesService.getScriptProperties().getProperty('RELAY_TOKEN');
  var evento = {
    postData: {
      contents: JSON.stringify({
        token: token,
        to: Session.getActiveUser().getEmail(),
        subject: 'Prueba relay Diagnóstico PCA',
        html: '<p>Si te llegó este mail, el relay funciona.</p>'
      })
    }
  };
  var salida = doPost(evento).getContent();
  console.log(salida);
}
