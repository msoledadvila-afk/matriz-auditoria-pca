"""
Envío por mail del resultado del Diagnóstico PCA al cliente.

Usa SMTP de Gmail con un "App Password" (no la contraseña normal de la
cuenta — Gmail requiere una contraseña de aplicación de 16 caracteres
para acceso SMTP con 2FA activado, que se genera en
myaccount.google.com/apppasswords).

Variables de entorno requeridas:
  SMTP_USER          -> la casilla de Gmail que envía (ej. tu@talentoimpulsa.com
                         o una @gmail.com)
  SMTP_APP_PASSWORD  -> el App Password de 16 caracteres (sin espacios)

Igual que sheets_leads.py: todas las funciones son "best effort". Si el
mail falla, se loguea pero no se corta el flujo — el cliente ya está
viendo el resultado en pantalla de todos modos.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


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

    saludo = f"¡Hola{', ' + nombre if nombre else ''}!"

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


def enviar_resultado_cliente(email_destino, nombre, resultado):
    """Manda el resultado del diagnóstico por mail. Devuelve True/False."""
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")

    if not smtp_user or not smtp_password:
        logger.warning("SMTP_USER o SMTP_APP_PASSWORD no configuradas: no se envía mail al cliente.")
        return False

    if not email_destino:
        return False

    try:
        pack_nombre = resultado["pack"]["nombre"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Tu Diagnóstico PCA — recomendamos {pack_nombre}"
        msg["From"] = smtp_user
        msg["To"] = email_destino

        html = _armar_html(nombre, resultado)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [email_destino], msg.as_string())
        return True
    except Exception:
        logger.exception("No se pudo enviar el mail de resultado a %s", email_destino)
        return False
