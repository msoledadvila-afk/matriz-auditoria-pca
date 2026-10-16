"""
Envío por mail del resultado del Diagnóstico PCA al cliente.

Dos caminos, en este orden:

1. RELAY de Apps Script (por HTTPS) — el que se usa en producción.
   El plan gratuito de Render bloquea las conexiones salientes a los puertos
   SMTP (25, 465 y 587), así que smtp.gmail.com da "Network is unreachable".
   El relay es una app web de Apps Script publicada desde la casilla que
   envía (hola@talentoimpulsa.com.ar); el código está en
   relay_mail_apps_script/Codigo.gs. Variables de entorno:
     MAIL_RELAY_URL    -> URL de la app web (termina en /exec)
     MAIL_RELAY_TOKEN  -> la misma clave cargada como RELAY_TOKEN en el script

2. SMTP de Gmail con App Password — queda como respaldo (local, o si algún
   día el servicio pasa a un plan pago que permita SMTP). Variables:
     SMTP_USER          -> la casilla de Gmail que envía
     SMTP_APP_PASSWORD  -> el App Password de 16 caracteres (sin espacios)

Igual que sheets_leads.py: todo es "best effort". Si el mail falla, se
loguea pero no se corta el flujo — el cliente ya está viendo el resultado en
pantalla de todos modos.
"""

import html as html_lib
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
RELAY_TIMEOUT = 25  # Apps Script tarda unos segundos en arrancar y enviar


def _armar_html(nombre, resultado):
    pack = resultado["pack"]

    cuellos_html = ""
    for cb in resultado["cuellos_de_botella"]:
        cuellos_html += f"""
        <div style="padding:10px 0;border-top:1px solid #E5DFD2;">
          <div style="font-weight:600;font-size:14px;color:#1A1814;">
            {cb['icono']} {cb['categoria']} — {round(cb['pct'] * 100)}% eficiencia
          </div>
          <div style="font-size:13px;color:#6E6859;margin-top:3px;line-height:1.5;">
            {cb['texto']}
          </div>
        </div>"""

    texto_recomendacion_html = resultado["texto_recomendacion"].replace("\n\n", "<br><br>")

    # El nombre lo escribe el visitante: se escapa para que no pueda meter HTML
    # en un mail que sale desde la casilla de Talento Impulsa.
    nombre_seguro = html_lib.escape((nombre or "").strip()[:60])
    saludo = f"¡Hola{', ' + nombre_seguro if nombre_seguro else ''}!"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1A1814;">
      <h2 style="color:#75582A;">{saludo}</h2>
      <p>Acá tenés el resultado completo de tu Diagnóstico PCA con Talento Impulsa Consulting.</p>

      <h3 style="color:#75582A;margin-top:24px;">Principales cuellos de botella</h3>
      {cuellos_html}

      <div style="background:linear-gradient(135deg,#75582A,#9A7B3D);color:#fff;
                  border-radius:12px;padding:20px 22px;margin-top:22px;">
        <div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.85;">
          Recomendado para vos
        </div>
        <h3 style="margin:8px 0 12px;">{pack['emoji']} {pack['nombre']}</h3>
        <p style="font-size:13.5px;line-height:1.6;opacity:.95;">{texto_recomendacion_html}</p>
      </div>

      <p style="margin-top:24px;font-size:13px;color:#6E6859;">
        ¿Querés avanzar con este pack o tenés dudas? Respondé este mismo mail y coordinamos.
      </p>
    </div>
    """


def _enviar_por_relay(url, token, email_destino, asunto, html):
    """POST al relay de Apps Script. Devuelve True solo si el script confirma ok."""
    try:
        # Apps Script responde con un 302 a script.googleusercontent.com, donde
        # queda el resultado: requests sigue la redirección (como GET) solo.
        resp = requests.post(
            url,
            json={"token": token, "to": email_destino, "subject": asunto, "html": html},
            timeout=RELAY_TIMEOUT,
        )
        try:
            datos = resp.json()
        except ValueError:
            logger.error("Relay de mail: respuesta no JSON (HTTP %s)", resp.status_code)
            return False
        if datos.get("ok"):
            logger.info("Relay de mail: enviado (cuota restante: %s)", datos.get("cuota_restante"))
            return True
        logger.error("Relay de mail rechazó el envío: %s", datos.get("error"))
        return False
    except Exception:
        logger.exception("Relay de mail: no se pudo conectar")
        return False


def _enviar_por_smtp(smtp_user, smtp_password, email_destino, asunto, html):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = smtp_user
        msg["To"] = email_destino
        msg.attach(MIMEText(html, "html"))

        # timeout=10: sin esto, una conexión SMTP colgada puede trabar el
        # servicio entero (Flask atiende un pedido a la vez).
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [email_destino], msg.as_string())
        return True
    except Exception:
        logger.exception("SMTP: no se pudo enviar el mail a %s", email_destino)
        return False


def enviar_resultado_cliente(email_destino, nombre, resultado):
    """Manda el resultado del diagnóstico por mail. Devuelve True/False."""
    if not email_destino:
        return False

    try:
        asunto = f"Tu Diagnóstico PCA — recomendamos {resultado['pack']['nombre']}"
        html = _armar_html(nombre, resultado)
    except Exception:
        logger.exception("No se pudo armar el mail de resultado")
        return False

    relay_url = os.getenv("MAIL_RELAY_URL")
    relay_token = os.getenv("MAIL_RELAY_TOKEN")
    if relay_url and relay_token:
        return _enviar_por_relay(relay_url, relay_token, email_destino, asunto, html)

    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if smtp_user and smtp_password:
        return _enviar_por_smtp(smtp_user, smtp_password, email_destino, asunto, html)

    logger.warning("Sin MAIL_RELAY_URL/MAIL_RELAY_TOKEN ni SMTP configurados: no se envía mail.")
    return False
