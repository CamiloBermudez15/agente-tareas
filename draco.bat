@echo off
chcp 65001 > nul
cd /d "%~dp0.."
if not exist logs mkdir logs

set TIPO=%1
if "%TIPO%"=="" set TIPO=todo

echo ===== %date% %time% - %TIPO% ===== >> logs\draco.log

REM 1) Iniciar sesion en SISCAE y UCN
".venv\Scripts\python.exe" scripts\iniciar_sesiones.py >> logs\draco.log 2>&1

REM 2) Ejecutar a Draco segun el tipo de reporte
if "%TIPO%"=="siscae" (
    "%USERPROFILE%\.local\bin\claude.exe" -p "Revisa la seccion SISCAE de config/paginas.md, todos los departamentos, siguiendo CLAUDE.md. Aplica la regla de reportes automaticos del SISCAE: SOLO envia mensajes al canal ventas si hay procesos NUEVOS o si hubo un error. Si no hay nada nuevo, no envies nada." >> logs\draco.log 2>&1
) else if "%TIPO%"=="ucn" (
    "%USERPROFILE%\.local\bin\claude.exe" -p "Revisa la seccion UCN de config/paginas.md siguiendo CLAUDE.md. Aplica la regla de reportes automaticos de la UCN: revisa el estado de entrega de cada tarea y SOLO envia mensajes al canal ucn si hay tareas nuevas, tareas pendientes que vencen hoy o manana, tareas vencidas sin entregar o un error. Si no hay nada de eso, no envies nada." >> logs\draco.log 2>&1
) else (
    "%USERPROFILE%\.local\bin\claude.exe" -p "Dame el reporte completo siguiendo CLAUDE.md" >> logs\draco.log 2>&1
)

echo ===== Fin %date% %time% ===== >> logs\draco.log