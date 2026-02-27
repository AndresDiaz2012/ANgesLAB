@echo off
chcp 65001 >nul 2>&1
title ANgesLAB - Instalacion de Dependencias IA Clinica
color 0D

echo.
echo ================================================================
echo     ANgesLAB v2.1 - Instalando Dependencias de IA Clinica
echo ================================================================
echo.
echo  Este proceso instalara las librerias necesarias para las
echo  funcionalidades de Inteligencia Artificial e Historial Avanzado:
echo.
echo    - matplotlib  : Graficas de evolucion de parametros clinicos
echo    - requests    : Comunicacion con Ollama (LLM local)
echo    - anthropic   : Integracion con Claude IA (online, opcional)
echo.
echo  Requiere conexion a internet activa.
echo.
echo ----------------------------------------------------------------

echo.
echo  [1/3] Instalando matplotlib (graficas de evolucion clinica)...
echo        Esto puede tomar unos minutos (~30 MB de descarga)...
pip install matplotlib --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [AVISO] No se pudo instalar matplotlib.
    echo         Las graficas de evolucion no estaran disponibles.
    echo         Puede instalarlo manualmente: pip install matplotlib
) else (
    echo         [OK] matplotlib instalado correctamente.
)

echo.
echo  [2/3] Instalando requests (comunicacion con Ollama LLM local)...
pip install requests --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [AVISO] No se pudo instalar requests.
    echo         La integracion con Ollama no estara disponible.
) else (
    echo         [OK] requests instalado correctamente.
)

echo.
echo  [3/3] Instalando anthropic (Claude IA - interpretacion online)...
pip install anthropic --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [AVISO] No se pudo instalar anthropic.
    echo         La integracion con Claude IA online no estara disponible.
    echo         Puede instalarlo manualmente: pip install anthropic
) else (
    echo         [OK] anthropic instalado correctamente.
)

echo.
echo ----------------------------------------------------------------
echo.
echo  Instalacion de dependencias de IA completada.
echo.
echo  NOTA: Las funcionalidades de IA se encuentran en:
echo    Historial Clinico  ^>  Tab "Graficas"    (graficas matplotlib)
echo    Historial Clinico  ^>  Tab "IA Clinica"  (interpretacion IA)
echo.
echo  Para usar Ollama (LLM local sin internet):
echo    1. Descargue Ollama desde: https://ollama.com
echo    2. Ejecute: ollama pull llama3.2
echo    3. Configure en ANgesLAB: IA Clinica ^> Config. IA
echo.
echo  Para usar Claude IA (online):
echo    1. Obtenga API Key en: https://console.anthropic.com
echo    2. Configure en ANgesLAB: IA Clinica ^> Config. IA
echo.
echo  Si hubo errores, asegurese de:
echo    1. Tener conexion a internet activa
echo    2. Tener Python correctamente instalado
echo    3. Ejecutar como Administrador si es necesario
echo.
echo ================================================================
echo.
