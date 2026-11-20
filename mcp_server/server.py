"""
Servidor MCP de Draco 🐉
Permite que un agente de IA envíe mensajes por Telegram.
"""
import logging
import os

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


def enviar_mensaje(mensaje: str) -> str:
    """Envía el mensaje a la API de Telegram (función normal, fácil de probar)."""
    if not TOKEN or not CHAT_ID:
        return "Error: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el archivo .env"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    respuesta = httpx.post(url, json={"chat_id": CHAT_ID, "text": mensaje}, timeout=30)
    datos = respuesta.json()

    if datos.get("ok"):
        return "Mensaje enviado correctamente ✅"
    return f"Error de Telegram: {datos.get('description')}"


@mcp.tool()
def enviar_telegram(mensaje: str) -> str:
    """Envía un mensaje a Camilo por Telegram a través del bot Draco.
    Úsala para enviar reportes de tareas pendientes o avisos importantes."""
    return enviar_mensaje(mensaje)


if __name__ == "__main__":
    mcp.run()

    