"""
Servidor MCP de Draco 🐉
Permite que un agente de IA envíe mensajes y archivos por Telegram.
"""
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

# Evita que httpx imprima las URLs (que contienen el token)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Carga las variables del archivo .env (está en la carpeta principal del proyecto)
RUTA_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(RUTA_ENV)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Crea el servidor MCP
mcp = MCPServer("draco")


# ---------------------------------------------------------------------------
# Funciones normales (fáciles de probar sin la IA)
# ---------------------------------------------------------------------------

def enviar_mensaje(mensaje: str) -> str:
    """Envía un mensaje de texto a la API de Telegram."""
    if not TOKEN or not CHAT_ID:
        return "Error: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el archivo .env"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    respuesta = httpx.post(url, json={"chat_id": CHAT_ID, "text": mensaje}, timeout=30)
    datos = respuesta.json()

    if datos.get("ok"):
        return "Mensaje enviado correctamente ✅"
    return f"Error de Telegram: {datos.get('description')}"


def enviar_documento(ruta: str, descripcion: str = "") -> str:
    """Sube un archivo a la API de Telegram."""
    if not TOKEN or not CHAT_ID:
        return "Error: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el archivo .env"

    archivo = Path(ruta)
    if not archivo.is_file():
        return f"Error: no existe el archivo {ruta}"
    if archivo.stat().st_size > 50 * 1024 * 1024:
        return "Error: el archivo pesa más de 50 MB (límite de Telegram para bots)"

    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    with archivo.open("rb") as f:
        respuesta = httpx.post(
            url,
            data={"chat_id": CHAT_ID, "caption": descripcion[:1024]},
            files={"document": (archivo.name, f)},
            timeout=120,
        )
    datos = respuesta.json()

    if datos.get("ok"):
        return f"Archivo {archivo.name} enviado correctamente ✅"
    return f"Error de Telegram: {datos.get('description')}"


# ---------------------------------------------------------------------------
# Herramientas MCP (las que usa la IA)
# ---------------------------------------------------------------------------

@mcp.tool()
def enviar_telegram(mensaje: str) -> str:
    """Envía un mensaje de texto a Camilo por Telegram a través del bot Draco.
    Úsala para enviar reportes de tareas pendientes o avisos importantes.
    Máximo 4096 caracteres por mensaje: si el texto es más largo, divídelo en varios."""
    return enviar_mensaje(mensaje)


@mcp.tool()
def enviar_archivo(ruta: str, descripcion: str = "") -> str:
    """Envía un archivo (PDF, Word, Excel, etc.) a Camilo por Telegram.
    'ruta' es la ruta completa del archivo en la computadora.
    'descripcion' es un texto corto que acompaña al archivo (máx. 1024 caracteres),
    por ejemplo: entidad, número de proceso y fecha de cierre."""
    return enviar_documento(ruta, descripcion)


if __name__ == "__main__":
    mcp.run()