@echo off
chcp 65001 >nul
title Actualizador ANgesLAB - Indice TyG + Imagen Profesional
cd /d "%~dp0"

echo.
echo ==================================================================
echo    ACTUALIZADOR ANgesLAB
echo    Aplica las mejoras recientes SIN borrar su trabajo
echo ==================================================================
echo.
echo  Antes de continuar, CIERRE ANgesLAB si esta abierto.
echo.
pause

rem --- Buscar Python en el sistema ---
where python >nul 2>&1
if %errorlevel%==0 (
    python "%~dp0aplicar_actualizacion.py" %*
    goto fin
)
where py >nul 2>&1
if %errorlevel%==0 (
    py "%~dp0aplicar_actualizacion.py" %*
    goto fin
)

echo.
echo [ERROR] No se encontro Python en este equipo.
echo         ANgesLAB requiere Python; si el programa ya funciona,
echo         Python esta instalado pero no en el PATH.
echo         Contacte a soporte tecnico de ANgesLAB.
echo.

:fin
echo.
echo ------------------------------------------------------------------
echo  Proceso finalizado. Puede cerrar esta ventana.
echo ------------------------------------------------------------------
pause
