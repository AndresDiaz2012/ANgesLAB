@echo off
chcp 65001 >nul 2>&1
title ANgesLAB DEMO - Instalacion de Dependencias
color 0B

echo.
echo ================================================================
echo     ANgesLAB DEMO - Instalando Dependencias de Python
echo ================================================================
echo.

echo  [1/7] Instalando reportlab (generacion de reportes PDF)...
pip install reportlab --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar reportlab.
) else (
    echo         [OK] reportlab instalado correctamente.
)

echo.
echo  [2/7] Instalando Pillow (procesamiento de imagenes)...
pip install Pillow --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar Pillow.
) else (
    echo         [OK] Pillow instalado correctamente.
)

echo.
echo  [3/7] Instalando pypiwin32 (integracion Windows/COM)...
pip install pypiwin32 --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar pypiwin32.
) else (
    echo         [OK] pypiwin32 instalado correctamente.
)

echo.
echo  [4/7] Instalando pypdf (marca de agua en PDFs demo)...
pip install pypdf --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar pypdf.
) else (
    echo         [OK] pypdf instalado correctamente.
)

echo.
echo  [5/7] Instalando matplotlib (graficas de evolucion clinica)...
pip install matplotlib --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [AVISO] No se pudo instalar matplotlib.
    echo         Las graficas de evolucion no estaran disponibles.
) else (
    echo         [OK] matplotlib instalado correctamente.
)

echo.
echo  [6/7] Instalando requests (comunicacion con Ollama LLM local)...
pip install requests --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [AVISO] No se pudo instalar requests.
) else (
    echo         [OK] requests instalado correctamente.
)

echo.
echo  [7/7] Instalando anthropic (Claude IA online)...
pip install anthropic --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [AVISO] No se pudo instalar anthropic.
    echo         La integracion con Claude IA no estara disponible.
) else (
    echo         [OK] anthropic instalado correctamente.
)

echo.
echo ================================================================
echo  Dependencias instaladas. ANgesLAB DEMO esta listo.
echo ================================================================
echo.
