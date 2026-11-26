"""
Inicia sesión en SISCAE y UCN Virtual con las credenciales del .env
y guarda la sesión para que Draco (Playwright MCP) la use.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

PROYECTO = Path(__file__).resolve().parent.parent
load_dotenv(PROYECTO / ".env")

ESTADO = PROYECTO / "sesiones" / "estado.json"
VER_NAVEGADOR = os.getenv("DRACO_VER_NAVEGADOR") == "1"

SITIOS = [
    {
        "nombre": "SISCAE",
        "url": "https://www.gestion.nicaraguacompra.gob.ni/siscae/portal",
        "usuario": os.getenv("SISCAE_USUARIO"),
        "clave": os.getenv("SISCAE_CLAVE"),
    },
    {
        "nombre": "UCN",
        "url": "https://ucnvirtual.edu.ni/grado/login/index.php",
        "usuario": os.getenv("UCN_USUARIO"),
        "clave": os.getenv("UCN_CLAVE"),
    },
]


def iniciar_sesion(pagina, sitio) -> str:
    nombre = sitio["nombre"]
    if not sitio["usuario"] or not sitio["clave"]:
        return f"⚠️ {nombre}: faltan usuario o clave en el .env"

    pagina.goto(sitio["url"], wait_until="domcontentloaded", timeout=60000)

    # Busca el campo de contraseña visible
    campo_clave = pagina.locator("input[type=password]:visible").first
    try:
        campo_clave.wait_for(timeout=15000)
    except PlaywrightTimeout:
        return f"✅ {nombre}: no apareció formulario (sesión ya iniciada)"

    # El campo de usuario es el input de texto que está justo antes de la contraseña
    campo_usuario = campo_clave.locator(
        "xpath=preceding::input[@type='text' or @type='email' or not(@type)][1]"
    )
    campo_usuario.fill(sitio["usuario"])
    campo_clave.fill(sitio["clave"])
    campo_clave.press("Enter")

    try:
        pagina.wait_for_load_state("networkidle", timeout=60000)
    except PlaywrightTimeout:
        pass

    if pagina.locator("input[type=password]:visible").count() > 0:
        return f"❌ {nombre}: no se pudo iniciar sesión (revisa usuario/clave o si hay captcha)"
    return f"✅ {nombre}: sesión iniciada"


def main() -> None:
    ESTADO.parent.mkdir(exist_ok=True)
    resultados = []

    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome", headless=not VER_NAVEGADOR)
        contexto = navegador.new_context()
        pagina = contexto.new_page()

        for sitio in SITIOS:
            try:
                resultados.append(iniciar_sesion(pagina, sitio))
            except Exception as error:
                resultados.append(f"❌ {sitio['nombre']}: error inesperado: {error}")

        contexto.storage_state(path=str(ESTADO))
        navegador.close()

    print("\n".join(resultados))
    if any(r.startswith("❌") for r in resultados):
        sys.exit(1)


if __name__ == "__main__":
    main()