"""
Persistencia de leads del Diagnóstico PCA en Google Sheets.

Por qué Sheets y no el disco de Render: el free tier de Render es efímero
(el filesystem se resetea en cada redeploy y, a veces, en reinicios por
inactividad), así que cualquier dato que solo viva en estado/estado_<id>.json
se puede perder. Sheets es la planilla que Soledad ya usa, y sirve como
"base de datos" durable sin sumar infraestructura nueva.

Estrategia de columnas (una fila por lead, se va completando en dos momentos):
  A: fecha_hora_inicio     (se llena al arrancar la entrevista)
  B: session_id            (clave para encontrar la fila y completarla después)
  C: nombre
  D: email
  E: telefono              (vacío al inicio, se completa al terminar)
  F: pack_recomendado      (vacío al inicio, se completa al terminar)
  G: resumen_resultado     (vacío al inicio, se completa al terminar)
  H: fecha_hora_completado (vacío al inicio, se completa al terminar)
  I: utm_source            (de la URL del anuncio; vacío si no vino de uno)
  J: utm_medium
  K: utm_campaign
  L: utm_content
Las 4 columnas UTM van AL FINAL a propósito: así las columnas A-H (y el
update E:H de completar_lead) no cambian de lugar y las filas viejas siguen
siendo válidas, solo con I-L vacías.

Todas las funciones son "best effort": si falla la conexión con Sheets
(credenciales mal puestas, cuota, etc.) se loguea el error pero NUNCA se
interrumpe el flujo de la entrevista. Perder el guardado en Sheets es
recuperable (se puede reconstruir a mano); cortar la entrevista de un
visitante real, no.

Variables de entorno requeridas:
  GOOGLE_SERVICE_ACCOUNT_JSON  -> contenido completo del JSON de la service
                                   account (el archivo que descargás de
                                   Google Cloud Console), como string.
  GOOGLE_SHEET_ID               -> el ID de la planilla (el valor entre
                                   /d/ y /edit en la URL de la planilla).

Setup previo en Google Cloud (una sola vez, lo hace Soledad):
  1. Crear un proyecto (o reusar uno) en console.cloud.google.com
  2. Habilitar "Google Sheets API"
  3. Crear una Service Account (IAM & Admin > Service Accounts)
  4. Crear una key tipo JSON para esa service account y descargarla
  5. Compartir la planilla de Google Sheets con el email de la service
     account (algo como nombre@proyecto.iam.gserviceaccount.com), con
     permiso de Editor
  6. En Render: pegar el contenido del JSON descargado como valor de
     GOOGLE_SERVICE_ACCOUNT_JSON, y el ID de la planilla en GOOGLE_SHEET_ID
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

NOMBRE_HOJA = "Leads"  # nombre de la pestaña dentro de la planilla
COLUMNAS_UTM = ["utm_source", "utm_medium", "utm_campaign", "utm_content"]
ENCABEZADOS = [
    "fecha_hora_inicio", "session_id", "nombre", "email", "telefono",
    "pack_recomendado", "resumen_resultado", "fecha_hora_completado",
] + COLUMNAS_UTM


def _texto_seguro(valor, max_len=200):
    """Limpia un valor que viene de la URL (o sea, lo controla el visitante)
    antes de escribirlo en la planilla: saca caracteres de control/saltos de
    línea y lo acota. No hace falta escapar fórmulas: append_row/update de
    gspread 6.x escriben en modo RAW, así que un '=...' queda como texto."""
    texto = "".join(c for c in str(valor or "") if c.isprintable())
    return texto.strip()[:max_len]


def _valores_utm(utm):
    """Devuelve las 4 UTM en orden fijo (source, medium, campaign, content),
    con "" para las que no vinieron. Acepta None o un dict incompleto."""
    utm = utm if isinstance(utm, dict) else {}
    return [_texto_seguro(utm.get(clave)) for clave in COLUMNAS_UTM]


def _asegurar_columnas(hoja):
    """Si la pestaña se creó con menos columnas que las que necesitamos
    (por ejemplo, 8 columnas de una versión anterior), agrega las que faltan
    para que append_row no choque contra el borde de la grilla."""
    try:
        if hoja.col_count < len(ENCABEZADOS):
            hoja.add_cols(len(ENCABEZADOS) - hoja.col_count)
    except Exception:
        logger.exception("No se pudieron agregar columnas a la pestaña '%s'", NOMBRE_HOJA)


def _cliente_sheets():
    """Arma el cliente de gspread autenticado, o None si falta configuración."""
    credenciales_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if not credenciales_json or not sheet_id:
        logger.warning(
            "GOOGLE_SERVICE_ACCOUNT_JSON o GOOGLE_SHEET_ID no configuradas: "
            "no se van a guardar leads en Sheets."
        )
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        info = json.loads(credenciales_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credenciales = Credentials.from_service_account_info(info, scopes=scopes)
        cliente = gspread.authorize(credenciales)
        return cliente.open_by_key(sheet_id)
    except Exception:
        logger.exception("No se pudo autenticar contra Google Sheets")
        return None


def _hoja_leads(spreadsheet):
    """Devuelve la pestaña 'Leads', creándola con encabezados si no existe."""
    try:
        return spreadsheet.worksheet(NOMBRE_HOJA)
    except Exception:
        try:
            hoja = spreadsheet.add_worksheet(title=NOMBRE_HOJA, rows=1000, cols=len(ENCABEZADOS))
            hoja.append_row(ENCABEZADOS)
            return hoja
        except Exception:
            logger.exception("No se pudo crear/abrir la pestaña 'Leads'")
            return None


def registrar_lead_inicio(session_id, nombre, email, utm=None):
    """Agrega una fila nueva al arrancar la entrevista. No bloquea si falla.

    utm: dict opcional con utm_source/utm_medium/utm_campaign/utm_content.
    Si no viene (o viene incompleto), esas columnas quedan vacías."""
    spreadsheet = _cliente_sheets()
    if spreadsheet is None:
        return False
    hoja = _hoja_leads(spreadsheet)
    if hoja is None:
        return False
    _asegurar_columnas(hoja)
    try:
        fila = [
            datetime.now().isoformat(timespec="seconds"),
            session_id,
            nombre,
            email,
            "", "", "", "",
        ] + _valores_utm(utm)
        hoja.append_row(fila)
        logger.info("Lead registrado en Sheets (session_id=%s, email=%s)", session_id, email)
        return True
    except Exception:
        logger.exception("No se pudo registrar el lead inicial en Sheets (session_id=%s)", session_id)
        return False


def completar_lead(session_id, telefono, pack_nombre, resumen_resultado, utm=None):
    """Busca la fila por session_id y completa teléfono + resultado.

    Si por algún motivo no encuentra la fila (falló el registro inicial,
    o se limpió la planilla a mano), agrega una fila nueva con todo el
    lead completo en vez de perder el dato. En ese caso también incluye
    las UTM (si se las pasan) para no perder de qué anuncio vino.
    """
    spreadsheet = _cliente_sheets()
    if spreadsheet is None:
        return False
    hoja = _hoja_leads(spreadsheet)
    if hoja is None:
        return False
    _asegurar_columnas(hoja)

    try:
        celda = hoja.find(session_id)
    except Exception:
        celda = None

    ahora = datetime.now().isoformat(timespec="seconds")

    try:
        if celda:
            fila = celda.row
            # columnas E, F, G, H = telefono, pack_recomendado, resumen_resultado, fecha_hora_completado
            hoja.update(f"E{fila}:H{fila}", [[telefono or "", pack_nombre, resumen_resultado, ahora]])
        else:
            # No se encontró la fila de inicio (ej: falló registrar_lead_inicio) ->
            # agregamos una fila nueva con lo que tenemos, para no perder el lead.
            hoja.append_row(
                [ahora, session_id, "", "", telefono or "", pack_nombre, resumen_resultado, ahora]
                + _valores_utm(utm)
            )
        return True
    except Exception:
        logger.exception("No se pudo completar el lead en Sheets (session_id=%s)", session_id)
        return False
