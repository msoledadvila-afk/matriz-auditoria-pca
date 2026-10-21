/**
 * Prueba de entrega a Gmail — Relay Diagnóstico PCA™
 *
 * Archivo SOLO de diagnóstico. No toca doPost() ni la implementación publicada:
 * se ejecuta desde el editor (Ejecutar → probarEntregaGmail) y no hace falta
 * volver a implementar nada para correrlo.
 *
 * Manda 7 variantes del mail de resultados, una por una, a cada casilla de
 * DESTINOS. Cada asunto empieza con [P1]…[P7] para identificarlas en el
 * registro de correo de Admin y en la bandeja. Comparando cuáles entran y
 * cuáles rebotan se ve qué parte del mail dispara el rechazo de Gmail.
 *
 *  P1  texto plano, corto, asunto neutro
 *  P2  texto plano con todo el contenido del resultado, asunto neutro
 *  P3  HTML idéntico al del backend (emojis + degradé), asunto neutro
 *  P4  igual a P3 pero con el asunto real (con "—" y "™")
 *  P5  HTML simple: sin emojis, sin degradé, sin "™", asunto neutro
 *  P6  HTML idéntico a P3 + versión en texto plano (multiparte)
 *  P7  HTML idéntico a P3 sin nombre de remitente ni "responder a"
 *
 * Cuota: 7 mails por destino (Workspace permite ~1.500 por día).
 */

var DESTINOS = [
  'msoledadvila@gmail.com',
  'talentoimpulsa@outlook.com'
];

function probarEntregaGmail() {
  var variantes = armarVariantes_();
  var log = [];
  DESTINOS.forEach(function (para) {
    variantes.forEach(function (v) {
      var opciones = {
        to: para,
        subject: v.asunto,
        body: v.texto || ''
      };
      if (v.html) opciones.htmlBody = v.html;
      if (v.conRemitente) {
        opciones.name = 'Talento Impulsa Consulting';
        opciones.replyTo = 'hola@talentoimpulsa.com.ar';
      }
      try {
        MailApp.sendEmail(opciones);
        log.push('OK enviado ' + v.id + ' → ' + para);
      } catch (err) {
        log.push('ERROR ' + v.id + ' → ' + para + ': ' + err);
      }
      Utilities.sleep(3000); // espaciado para que no parezca un envío en ráfaga
    });
  });
  log.push('Cuota restante: ' + MailApp.getRemainingDailyQuota());
  console.log(log.join('\n'));
}

function armarVariantes_() {
  var hora = Utilities.formatDate(new Date(), 'America/Argentina/Buenos_Aires', 'HH:mm');
  var neutro = function (id) { return '[' + id + '] Resultado de tu diagnostico ' + hora; };
  var asuntoReal = '[P4] Tu Diagnóstico PCA — recomendamos Pack Autonomía PCA™ ' + hora;

  return [
    { id: 'P1', asunto: neutro('P1'), conRemitente: true,
      texto: 'Hola Sole, esta es una prueba corta en texto plano del relay de Talento Impulsa.' },
    { id: 'P2', asunto: neutro('P2'), conRemitente: true, texto: textoPlanoCompleto_() },
    { id: 'P3', asunto: neutro('P3'), conRemitente: true, html: htmlBackend_() },
    { id: 'P4', asunto: asuntoReal, conRemitente: true, html: htmlBackend_() },
    { id: 'P5', asunto: neutro('P5'), conRemitente: true, html: htmlSimple_() },
    { id: 'P6', asunto: neutro('P6'), conRemitente: true,
      html: htmlBackend_(), texto: textoPlanoCompleto_() },
    { id: 'P7', asunto: neutro('P7'), conRemitente: false, html: htmlBackend_() }
  ];
}

// ── Contenido de ejemplo (mismo texto que arma logica_recomendacion.py) ──

var CUELLOS = [
  { icono: '⚙️', cat: 'Procesos Operativos', pct: 40,
    texto: 'Procesos operativos: existen tareas repetitivas sin sistematizar y falta de documentación que genera retrabajo constante. La automatización inteligente puede liberar horas de trabajo manual semanal.' },
  { icono: '⏱', cat: 'Gestión del Tiempo', pct: 48,
    texto: 'Gestión del tiempo: se detecta pérdida significativa de horas en tareas operativas y búsqueda de información dispersa. Con IA y un sistema ordenado, estos procesos pueden acortarse de forma notable.' },
  { icono: '📂', cat: 'Gestión Documental', pct: 60,
    texto: 'Gestión documental: la información dispersa y la falta de síntesis generan fricción operativa y decisiones demoradas. Un sistema de procesamiento de documentos con IA puede cambiar esto radicalmente.' }
];

var RECO = [
  'El diagnóstico muestra un perfil con potencial de mejora significativo. Las áreas con mayor oportunidad de mejora son: procesos operativos, gestión del tiempo, gestión documental.',
  'Con el Pack Autonomía PCA™, implementaremos un sistema personalizado que ataca directamente estos cuellos de botella. A través de prompts validados, protocolos de delegación inteligente y sesiones de implementación práctica, el objetivo del Modelo PCA™ es que recuperes horas de tu semana que hoy se van en operativa.',
  'Resultado esperado: Ahorro estimado de 5 a 10 horas semanales desde la primera semana.'
];

function textoPlanoCompleto_() {
  var t = 'Hola Sole:\n\nAcá tenés el resultado completo de tu Diagnóstico PCA con Talento Impulsa Consulting.\n\n';
  t += 'PRINCIPALES CUELLOS DE BOTELLA\n';
  CUELLOS.forEach(function (c) {
    t += '\n- ' + c.cat + ' (' + c.pct + '% eficiencia)\n  ' + c.texto + '\n';
  });
  t += '\nRECOMENDADO PARA VOS: Pack Autonomía PCA\n\n' + RECO.join('\n\n') + '\n\n';
  t += '¿Querés avanzar con este pack o tenés dudas? Respondé este mismo mail y coordinamos.\n';
  return t;
}

// Réplica exacta de _armar_html() en notificaciones_email.py
function htmlBackend_() {
  var cuellos = CUELLOS.map(function (c) {
    return '<div style="padding:10px 0;border-top:1px solid #E5DFD2;">' +
      '<div style="font-weight:600;font-size:14px;color:#1A1814;">' + c.icono + ' ' + c.cat +
      ' — ' + c.pct + '% eficiencia</div>' +
      '<div style="font-size:13px;color:#6E6859;margin-top:3px;line-height:1.5;">' + c.texto + '</div></div>';
  }).join('');
  return '<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1A1814;">' +
    '<h2 style="color:#75582A;">¡Hola, Sole!</h2>' +
    '<p>Acá tenés el resultado completo de tu Diagnóstico PCA con Talento Impulsa Consulting.</p>' +
    '<h3 style="color:#75582A;margin-top:24px;">Principales cuellos de botella</h3>' + cuellos +
    '<div style="background:linear-gradient(135deg,#75582A,#9A7B3D);color:#fff;border-radius:12px;padding:20px 22px;margin-top:22px;">' +
    '<div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.85;">Recomendado para vos</div>' +
    '<h3 style="margin:8px 0 12px;">🚀 Pack Autonomía PCA™</h3>' +
    '<p style="font-size:13.5px;line-height:1.6;opacity:.95;">' + RECO.join('<br><br>') + '</p></div>' +
    '<p style="margin-top:24px;font-size:13px;color:#6E6859;">¿Querés avanzar con este pack o tenés dudas? Respondé este mismo mail y coordinamos.</p>' +
    '</div>';
}

// Misma información, sin emojis, sin degradé y sin "™"
function htmlSimple_() {
  var cuellos = CUELLOS.map(function (c) {
    return '<p style="margin:12px 0 0;"><strong>' + c.cat + ' (' + c.pct + '% eficiencia)</strong><br>' + c.texto + '</p>';
  }).join('');
  var reco = RECO.map(function (p) { return p.replace(/™/g, ''); });
  return '<div style="font-family:Arial,sans-serif;max-width:560px;color:#1A1814;">' +
    '<p>Hola Sole:</p>' +
    '<p>Acá tenés el resultado completo de tu Diagnóstico PCA con Talento Impulsa Consulting.</p>' +
    '<p><strong>Principales cuellos de botella</strong></p>' + cuellos +
    '<p style="margin-top:20px;"><strong>Recomendado para vos: Pack Autonomía PCA</strong></p>' +
    '<p>' + reco.join('</p><p>') + '</p>' +
    '<p>¿Querés avanzar con este pack o tenés dudas? Respondé este mismo mail y coordinamos.</p>' +
    '</div>';
}
