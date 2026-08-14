"""
API Flask del Agente de Diagnóstico PCA — Talento Impulsa Consulting

Envuelve la lógica de agente_diagnostico_pca.py (que fue pensada para un
loop de CLI con input()) en un endpoint POST /chat de request/response,
con sesión por visitante en vez de un único archivo de estado compartido.

Pensado para correr en Render, con el widget del sitio (Netlify) llamando
por fetch() a este backend.

Reutiliza SIN modificar: cargar_catalogo, crear_system_prompt, consultar_modelo,
extraer_puntaje, calcular_resultado — todas siguen siendo funciones puras o
casi puras del módulo original. Lo único que cambia es cómo se persiste y
recorre el estado: de variables vivas en un while True, a un archivo por
sesión que se lee y escribe en cada request.
"""

import json
import logging
import os
import re
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS

from agente_diagnostico_pca import (
    cargar_catalogo,
    crear_system_prompt,
    consultar_modelo,
    extraer_puntaje,
    calcular_resultado,
)
from sheets_leads import registrar_lead_inicio, completar_lead
from notificaciones_email import enviar_resultado_cliente

# Sin esto, algunos entornos no muestran los logger.warning()/logger.exception()
# de sheets_leads.py y notificaciones_email.py en la consola — con basicConfig
# quedan garantizados un handler y un formato explícitos.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# --- Configuración de estado por sesión ------------------------------------
# Cada visitante tiene su propio archivo: estado/estado_<session_id>.json
# En el CLI original era un único archivo (ARCHIVO_ESTADO) porque solo había
# un usuario a la vez. Acá puede haber muchos visitantes simultáneos, así
# que la clave de sesión reemplaza a "el único archivo posible".
CARPETA_ESTADO = "estado"
os.makedirs(CARPETA_ESTADO, exist_ok=True)


def _ruta_estado(session_id):
    # session_id lo generamos nosotros con uuid4, nunca viene directo del
    # cliente sin validar -> evita path traversal si algún día se acepta
    # un id externo.
    return os.path.join(CARPETA_ESTADO, f"estado_{session_id}.json")


def guardar_estado(session_id, historial, puntajes, contacto=None, resultado=None):
    with open(_ruta_estado(session_id), "w", encoding="utf-8") as f:
        json.dump({
            "historial": historial,
            "puntajes": puntajes,
            "contacto": contacto or {},
            "resultado": resultado,  # se completa cuando termina la entrevista
        }, f, ensure_ascii=False, indent=2)


def cargar_estado(session_id):
    ruta = _ruta_estado(session_id)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def borrar_estado(session_id):
    ruta = _ruta_estado(session_id)
    if os.path.exists(ruta):
        os.remove(ruta)


# --- Catálogo y system prompt: se cargan UNA sola vez al arrancar la app ---
# (no en cada request, igual que en el CLI se cargaban una vez al entrar a
# main(); acá "arrancar la app" es el equivalente a "correr el script").
catalogo = cargar_catalogo("catalogo_diagnostico.json")
if catalogo is None:
    raise RuntimeError("No se pudo cargar catalogo_diagnostico.json — revisá que esté en esta carpeta.")

SYSTEM_PROMPT = crear_system_prompt(catalogo)
TOTAL_PREGUNTAS = sum(len(c["preguntas"]) for c in catalogo["categorias"])

# --- Chequeo de configuración al arrancar: queda bien visible en los logs de
# Render apenas prende el servicio, sin tener que provocar un request para
# enterarse de si falta alguna variable de entorno. Solo confirma presencia
# (True/False), nunca imprime el valor real de una credencial.
def _log_estado_config():
    variables = ["GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_SHEET_ID", "SMTP_USER", "SMTP_APP_PASSWORD"]
    for var in variables:
        presente = bool(os.getenv(var))
        logger.info("Config %s: %s", var, "OK (presente)" if presente else "FALTA")

_log_estado_config()

# --- App Flask ---------------------------------------------------------------
app = Flask(__name__)

# Restringí el origin al dominio real de Netlify vía variable de entorno.
# Si ALLOWED_ORIGIN no está seteada, cae a "*" (útil para probar local, pero
# NO dejar así en producción).
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
CORS(app, resources={r"/chat": {"origins": ALLOWED_ORIGIN}})


@app.get("/health")
def health():
    # Endpoint simple para que Render (o quien sea) chequee que el servicio
    # está vivo sin gastar tokens de Groq.
    return jsonify({"status": "ok"})


@app.post("/chat")
def chat():
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    mensaje = body.get("mensaje")

    if session_id:
        estado = cargar_estado(session_id)
        if estado is None:
            return jsonify({"error": "sesión no encontrada o ya finalizada"}), 404
        historial = estado["historial"]
        puntajes = estado["puntajes"]
        contacto = estado.get("contacto", {})

        if not mensaje or not mensaje.strip():
            return jsonify({"error": "falta 'mensaje'"}), 400
        historial.append({"role": "user", "content": mensaje})
    else:
        # Primer request de esta visita: pedimos nombre y mail ANTES de arrancar
        # la entrevista (así no se pierde el lead si el visitante abandona a
        # mitad de camino). El teléfono se confirma/completa recién al final.
        nombre = (body.get("nombre") or "").strip()
        email = (body.get("email") or "").strip()

        if not nombre:
            return jsonify({"error": "falta 'nombre'"}), 400
        if not email or not REGEX_EMAIL.match(email):
            return jsonify({"error": "el mail no parece válido"}), 400

        session_id = str(uuid.uuid4())
        historial = [{"role": "user", "content": "Iniciá el diagnóstico."}]
        puntajes = {}
        contacto = {"nombre": nombre, "email": email, "telefono": ""}

        # Best-effort: si Sheets no está configurado o falla, no cortamos la
        # entrevista — el lead igual se puede recuperar al completar_lead()
        # (agrega la fila si no la encuentra) o revisando logs de Render.
        registrar_lead_inicio(session_id, nombre, email)

    respuesta_modelo = consultar_modelo(historial, SYSTEM_PROMPT)
    if respuesta_modelo is None:
        # Guardamos igual lo que había (el turno del usuario, si lo hubo) para
        # no perder progreso: el frontend puede reintentar con el mismo
        # session_id sin repetir la entrevista desde cero.
        guardar_estado(session_id, historial, puntajes, contacto)
        return jsonify({
            "session_id": session_id,
            "error": "error al consultar el modelo, intentá de nuevo",
        }), 502

    pregunta_id, puntaje, texto_limpio = extraer_puntaje(respuesta_modelo)
    if pregunta_id:
        puntajes[pregunta_id] = puntaje
    historial.append({"role": "assistant", "content": respuesta_modelo})

    if len(puntajes) >= TOTAL_PREGUNTAS:
        resultado = calcular_resultado(catalogo, puntajes)
        # OJO: todavía NO borramos el estado ni mandamos nada a Sheets/mail acá.
        # Falta confirmar el teléfono (paso siguiente en el frontend), y recién
        # con eso completamos el lead y mandamos el mail. Guardamos el resultado
        # para no tener que recalcularlo en /completar-lead.
        guardar_estado(session_id, historial, puntajes, contacto, resultado)
        return jsonify({
            "session_id": session_id,
            "terminado": True,
            "mensaje": texto_limpio,
            "resultado": resultado,
        })

    guardar_estado(session_id, historial, puntajes, contacto)
    return jsonify({
        "session_id": session_id,
        "terminado": False,
        "mensaje": texto_limpio,
        "progreso": {"respondidas": len(puntajes), "total": TOTAL_PREGUNTAS},
    })


@app.post("/completar-lead")
def completar_lead_endpoint():
    """Se llama una sola vez, después de terminado:true, cuando el frontend
    ya mostró/pidió el teléfono. Completa la fila en Sheets y manda el mail
    con el resultado al cliente. Es best-effort: si Sheets o el mail fallan,
    igual respondemos ok (el cliente ya está viendo el resultado en pantalla,
    no tiene sentido bloquearlo por un error de infraestructura interna).
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    telefono = (body.get("telefono") or "").strip()

    if not session_id:
        return jsonify({"error": "falta 'session_id'"}), 400

    estado = cargar_estado(session_id)
    if estado is None or estado.get("resultado") is None:
        return jsonify({"error": "sesión no encontrada o entrevista no finalizada"}), 404

    contacto = estado.get("contacto", {})
    resultado = estado["resultado"]

    pack_nombre = resultado["pack"]["nombre"]
    resumen = resultado["razon"]

    sheets_ok = completar_lead(session_id, telefono, pack_nombre, resumen)
    mail_ok = enviar_resultado_cliente(contacto.get("email"), contacto.get("nombre"), resultado)

    borrar_estado(session_id)

    return jsonify({"ok": True, "sheet_actualizado": sheets_ok, "mail_enviado": mail_ok})


if __name__ == "__main__":
    # host 0.0.0.0 para que Render pueda enrutar tráfico externo al contenedor.
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
