@echo off
chcp 65001 >nul 2>&1
title ANgesLAB - Compilador de Instalador
color 0E

echo.
echo ================================================================
echo     ANgesLAB - Generador de Instalador
echo     Powered by Inno Setup 6
echo ================================================================
echo.
echo  Este script compilara el instalador de ANgesLAB.
echo  Requisito: Inno Setup 6 debe estar instalado.
echo.
echo ----------------------------------------------------------------
echo.

:: Buscar Inno Setup en ubicaciones comunes
SET "ISCC="

:: Ruta 1: Program Files (x86) - instalacion tipica
IF EXIST "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    SET "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto :found
)

:: Ruta 2: Program Files - instalacion 64-bit
IF EXIST "C:\Program Files\Inno Setup 6\ISCC.exe" (
    SET "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto :found
)

:: Ruta 3: Buscar en PATH
where ISCC.exe >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET "ISCC=ISCC.exe"
    goto :found
)

:: No encontrado
echo  [ERROR] Inno Setup 6 no fue encontrado en su sistema.
echo.
echo  Para generar el instalador, necesita instalar Inno Setup 6:
echo.
echo    1. Descargue Inno Setup 6 (gratuito) desde:
echo       https://jrsoftware.org/isdl.php
echo.
echo    2. Instale con las opciones por defecto.
echo.
echo    3. Ejecute este script nuevamente.
echo.
echo ================================================================
echo.
pause
exit /b 1

:found
echo  [OK] Inno Setup encontrado: %ISCC%
echo.
echo  Compilando ANgesLAB_Setup.iss ...
echo.
echo ----------------------------------------------------------------
echo.

:: Crear carpeta output si no existe
if not exist "output" mkdir "output"

:: Compilar el script .iss
"%ISCC%" "ANgesLAB_Setup.iss"

:: Verificar resultado
echo.
echo ----------------------------------------------------------------
IF %ERRORLEVEL% EQU 0 (
    echo.
    echo  ============================================================
    echo  [EXITO] Instalador generado correctamente!
    echo  ============================================================
    echo.
    echo  Archivo: output\ANgesLAB_Setup_v2.1.exe
    echo.
    echo  Este archivo es el instalador listo para distribuir
    echo  a los clientes. Contiene todo lo necesario para
    echo  instalar ANgesLAB en el equipo del laboratorio.
    echo.
    echo  ============================================================
) ELSE (
    echo.
    echo  [ERROR] La compilacion fallo con codigo: %ERRORLEVEL%
    echo.
    echo  Revise los mensajes de error arriba para mas detalles.
    echo  Problemas comunes:
    echo    - Archivos fuente faltantes (verifique la carpeta ..)
    echo    - Permisos insuficientes
    echo    - Error de sintaxis en ANgesLAB_Setup.iss
)

echo.
pause
