@echo off
chcp 65001 >nul 2>&1
title ANgesLAB - Instalacion de Dependencias
color 0B

echo.
echo ================================================================
echo     ANgesLAB v2.1 - Instalando Dependencias de Python
echo ================================================================
echo.
echo  Este proceso instalara las librerias necesarias para el
echo  funcionamiento de ANgesLAB. Por favor espere...
echo.
echo ----------------------------------------------------------------

echo.
echo  [1/3] Instalando reportlab (generacion de reportes PDF)...
pip install reportlab --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar reportlab.
    echo         Verifique su conexion a internet e intente nuevamente.
) else (
    echo         [OK] reportlab instalado correctamente.
)

echo.
echo  [2/3] Instalando Pillow (procesamiento de imagenes)...
pip install Pillow --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar Pillow.
    echo         Verifique su conexion a internet e intente nuevamente.
) else (
    echo         [OK] Pillow instalado correctamente.
)

echo.
echo  [3/3] Instalando pypiwin32 (integracion Windows/COM)...
pip install pypiwin32 --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo instalar pypiwin32.
    echo         Verifique su conexion a internet e intente nuevamente.
) else (
    echo         [OK] pypiwin32 instalado correctamente.
)

echo.
echo ----------------------------------------------------------------
echo.
echo  Instalacion de dependencias completada.
echo.
echo  Si hubo errores, asegurese de:
echo    1. Tener conexion a internet activa
echo    2. Tener Python correctamente instalado
echo    3. Ejecutar como Administrador si es necesario
echo.
echo ================================================================
echo.
pause
