# Diagnóstico PCA™ · Talento Impulsa Consulting

Diagnóstico conversacional del Modelo PCA™ — Productividad Consciente Aumentada: detecta dónde se pierde tiempo en un equipo y recomienda la línea de trabajo que corresponde.

**Estado:** Producción · público
**Demo:** [talentoimpulsa.com.ar/diagnostico](https://talentoimpulsa.com.ar/diagnostico)

## Qué hace

- Entrevista guiada por un agente de IA: 25 preguntas en 5 categorías (Gestión del Tiempo, Procesos Operativos, Comunicación, Gestión Documental y Toma de Decisiones)
- Puntaje de 1 a 5 por respuesta y detección de cuellos de botella por categoría
- Recomendación de la línea de trabajo según el resultado
- Registro del contacto y del resultado en Google Sheets
- Envío del informe por mail desde hola@talentoimpulsa.com.ar

## Lugar en el Modelo PCA™

El Modelo PCA™ trabaja en tres momentos: Ordenar → Delegar → Sostener. El diagnóstico es el primer paso de Ordenar: muestra el estado actual antes de proponer cambios.

> Los objetivos del Modelo PCA™ son recuperar entre 5 y 10 horas semanales y tener respuesta en 48 a 72 h. Son objetivos de trabajo, no resultados garantizados.

## Stack

| Capa | Tecnología |
| --- | --- |
| Frontend | HTML + JS vanilla (`diagnostico.html`), publicado en el sitio de Talento Impulsa |
| API | Python + Flask (`api_diagnostico.py`) en Render |
| Modelo de lenguaje | Groq; el modelo se elige por variable de entorno |
| Datos | Google Sheets vía cuenta de servicio (`sheets_leads.py`) |
| Mail | Relay en Google Apps Script (`relay_mail_apps_script/`), con SMTP como respaldo |

## Estructura

| Archivo | Para qué sirve |
| --- | --- |
| `api_diagnostico.py` | API: conversación, puntaje y cierre del lead |
| `agente_diagnostico_pca.py` | Lógica del agente y llamadas al modelo |
| `logica_recomendacion.py` | Cálculo de resultados y recomendación |
| `catalogo_diagnostico.json` | Categorías, preguntas, escalas y líneas de trabajo |
| `sheets_leads.py` | Persistencia en Google Sheets |
| `notificaciones_email.py` | Envío del informe por mail |
| `relay_mail_apps_script/` | Código del relay de mail (se despliega aparte en Apps Script) |
| `config.py` | Lectura de variables de entorno |

## Configuración

Las claves se cargan como variables de entorno en Render; nunca en el repo (`.env` está en `.gitignore`).

Variables de la API: `API_KEY_GROQ`, `MODEL_GROQ`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID`, `MAIL_RELAY_URL`, `MAIL_RELAY_TOKEN`, `SMTP_USER`, `SMTP_APP_PASSWORD`, `ALLOWED_ORIGIN`.

Propiedad del script del relay: `RELAY_TOKEN` (en Propiedades del script de Apps Script).

Instalación local: `pip install -r requirements.txt` y `python api_diagnostico.py`.

## Licencia

© 2026 Talento Impulsa Consulting. Todos los derechos reservados. Código visible solo como referencia; no se autoriza su reutilización comercial.

---

**Talento Impulsa Consulting** · [talentoimpulsa.com.ar](https://talentoimpulsa.com.ar)
hola@talentoimpulsa.com.ar · presupuestos@talentoimpulsa.com.ar
