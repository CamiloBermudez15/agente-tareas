"""
Servidor MCP de Draco 🐉
Herramientas para que un agente de IA envíe reportes y archivos por Telegram,
y procese documentos (ZIP/RAR, PDF, Word, Excel).
"""
import logging
import os
import subprocess
import zipfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

# Evita que httpx imprima las URLs (que contienen el token)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Rutas del proyecto
CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_EXTRAIDOS = CARPETA_PROYECTO / "descargas" / "extraidos"

# Carga las variables del archivo .env
load_dotenv(CARPETA_PROYECTO / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Chats por canal (si un canal no está configurado, usa el chat personal)
CHATS = {
    "general": CHAT_ID,
    "ventas": os.getenv("TELEGRAM_CHAT_ID_VENTAS") or CHAT_ID,
    "ucn": os.getenv("TELEGRAM_CHAT_ID_UCN") or CHAT_ID,
}

mcp = MCPServer("draco")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _buscar_programa(rutas: list[str]) -> str | None:
    """Devuelve la primera ruta de programa que exista en la PC."""
    for ruta in rutas:
        if Path(ruta).is_file():
            return ruta
    return None


def _chat_de(canal: str) -> str | None:
    return CHATS.get(canal.lower().strip(), CHAT_ID)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def enviar_mensaje(mensaje: str, canal: str = "general") -> str:
    """Envía un mensaje de texto a Telegram."""
    chat = _chat_de(canal)
    if not TOKEN or not chat:
        return "Error: faltan TELEGRAM_BOT_TOKEN o el chat ID en el archivo .env"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    respuesta = httpx.post(url, json={"chat_id": chat, "text": mensaje}, timeout=30)
    datos = respuesta.json()

    if datos.get("ok"):
        return f"Mensaje enviado correctamente al canal '{canal}' ✅"
    return f"Error de Telegram: {datos.get('description')}"


def enviar_documento(ruta: str, descripcion: str = "", canal: str = "general") -> str:
    """Sube un archivo a Telegram."""
    chat = _chat_de(canal)
    if not TOKEN or not chat:
        return "Error: faltan TELEGRAM_BOT_TOKEN o el chat ID en el archivo .env"

    archivo = Path(ruta)
    if not archivo.is_file():
        return f"Error: no existe el archivo {ruta}"
    if archivo.stat().st_size > 50 * 1024 * 1024:
        return "Error: el archivo pesa más de 50 MB (límite de Telegram para bots)"

    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    with archivo.open("rb") as f:
        respuesta = httpx.post(
            url,
            data={"chat_id": chat, "caption": descripcion[:1024]},
            files={"document": (archivo.name, f)},
            timeout=120,
        )
    datos = respuesta.json()

    if datos.get("ok"):
        return f"Archivo {archivo.name} enviado al canal '{canal}' ✅"
    return f"Error de Telegram: {datos.get('description')}"


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------

def extraer(ruta: str) -> str:
    """Extrae un ZIP, RAR o 7Z y devuelve la lista de archivos."""
    archivo = Path(ruta)
    if not archivo.is_file():
        return f"Error: no existe el archivo {ruta}"

    destino = CARPETA_EXTRAIDOS / archivo.stem
    destino.mkdir(parents=True, exist_ok=True)
    extension = archivo.suffix.lower()

    try:
        if extension == ".zip":
            with zipfile.ZipFile(archivo) as comprimido:
                comprimido.extractall(destino)
        elif extension in (".rar", ".7z"):
            siete_zip = _buscar_programa([
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
            ])
            unrar = _buscar_programa([
                r"C:\Program Files\WinRAR\UnRAR.exe",
                r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
            ])
            if siete_zip:
                comando = [siete_zip, "x", "-y", f"-o{destino}", str(archivo)]
            elif unrar and extension == ".rar":
                comando = [unrar, "x", "-y", str(archivo), str(destino) + "\\"]
            else:
                # Windows 11 incluye un tar que también abre RAR
                comando = [r"C:\Windows\System32\tar.exe", "-xf", str(archivo), "-C", str(destino)]

            resultado = subprocess.run(comando, capture_output=True, text=True, timeout=180)
            if resultado.returncode != 0:
                return f"Error al extraer: {resultado.stderr or resultado.stdout}"
        else:
            return f"Error: formato no soportado ({extension}). Usa .zip, .rar o .7z"
    except Exception as error:
        return f"Error al extraer: {error}"

    archivos = [str(p) for p in destino.rglob("*") if p.is_file()]
    if not archivos:
        return "El comprimido está vacío."
    return "Archivos extraídos:\n" + "\n".join(archivos)


def leer_texto(ruta: str, max_caracteres: int = 3000) -> str:
    """Devuelve el texto inicial de un PDF o Word."""
    archivo = Path(ruta)
    if not archivo.is_file():
        return f"Error: no existe el archivo {ruta}"

    extension = archivo.suffix.lower()
    try:
        if extension == ".pdf":
            from pypdf import PdfReader
            lector = PdfReader(str(archivo))
            texto = "\n".join((pagina.extract_text() or "") for pagina in lector.pages[:3])
        elif extension == ".docx":
            import docx
            documento = docx.Document(str(archivo))
            partes = [p.text for p in documento.paragraphs]
            for tabla in documento.tables:
                for fila in tabla.rows:
                    partes.append(" | ".join(celda.text for celda in fila.cells))
            texto = "\n".join(partes)
        else:
            return (f"No puedo leer {extension} directamente. "
                    "Conviértelo primero con convertir_a_pdf y luego léelo.")
    except Exception as error:
        return f"Error al leer el documento: {error}"

    if not texto.strip():
        return ("No se pudo extraer texto (puede ser un PDF escaneado como imagen). "
                "Decide por el nombre del archivo.")
    return texto[:max_caracteres]


def convertir_pdf(ruta: str) -> str:
    """Convierte Word o Excel a PDF usando Microsoft Office o LibreOffice."""
    archivo = Path(ruta).resolve()
    if not archivo.is_file():
        return f"Error: no existe el archivo {ruta}"

    extension = archivo.suffix.lower()
    if extension == ".pdf":
        return f"Ya es PDF: {archivo}"

    pdf = archivo.with_suffix(".pdf")

    # 1) Intentar con Microsoft Office
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            if extension in (".doc", ".docx", ".rtf"):
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                documento = word.Documents.Open(str(archivo), ReadOnly=True)
                documento.SaveAs(str(pdf), FileFormat=17)
                documento.Close(False)
                word.Quit()
            elif extension in (".xls", ".xlsx"):
                excel = win32com.client.DispatchEx("Excel.Application")
                excel.Visible = False
                libro = excel.Workbooks.Open(str(archivo), ReadOnly=True)
                libro.ExportAsFixedFormat(0, str(pdf))
                libro.Close(False)
                excel.Quit()
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        pass

    # 2) Si no funcionó, intentar con LibreOffice
    if not pdf.is_file():
        soffice = _buscar_programa([
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ])
        if soffice:
            subprocess.run(
               [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(archivo.parent),
                    str(archivo),
                ],
                capture_output=True,
                timeout=180,
            )

            
    if pdf.is_file():
        return f"PDF creado: {pdf}"
    return "Error: no se pudo convertir a PDF. Se necesita Microsoft Office o LibreOffice instalado."


# ---------------------------------------------------------------------------
# Herramientas MCP (las que usa la IA)
# ---------------------------------------------------------------------------

@mcp.tool()
def enviar_telegram(mensaje: str, canal: str = "general") -> str:
    """Envía un mensaje de texto a Camilo por Telegram.
    canal: "ventas" para reportes del SISCAE, "ucn" para el aula virtual, "general" para lo demás.
    Máximo 4096 caracteres por mensaje: si el texto es más largo, divídelo en varios."""
    return enviar_mensaje(mensaje, canal)


@mcp.tool()
def enviar_archivo(ruta: str, descripcion: str = "", canal: str = "general") -> str:
    """Envía un archivo a Camilo por Telegram.
    ruta: ruta completa del archivo. Para SISCAE envía SIEMPRE un PDF.
    descripcion: texto corto (máx. 1024 caracteres), ej.: entidad, N.º de proceso y fecha de cierre.
    canal: "ventas", "ucn" o "general"."""
    return enviar_documento(ruta, descripcion, canal)


@mcp.tool()
def extraer_comprimido(ruta: str) -> str:
    """Extrae un archivo .zip, .rar o .7z y devuelve la lista de archivos que contiene."""
    return extraer(ruta)


@mcp.tool()
def leer_documento(ruta: str) -> str:
    """Lee el texto inicial de un PDF o Word (.docx).
    Úsala para identificar cuál archivo es la INVITACIÓN de un proceso
    (la que tiene lugar de entrega, plazo de entrega y tabla de ítems)."""
    return leer_texto(ruta)


@mcp.tool()
def convertir_a_pdf(ruta: str) -> str:
    """Convierte un archivo Word (.doc, .docx, .rtf) o Excel (.xls, .xlsx) a PDF
    y devuelve la ruta del PDF creado."""
    return convertir_pdf(ruta)


if __name__ == "__main__":
    mcp.run()