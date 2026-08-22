@echo off
chcp 65001 >nul
title ANgesLAB - Restablecer acceso 'developer'
cd /d "%~dp0"

echo.
echo ==================================================================
echo    ANgesLAB  -  RESTABLECER ACCESO DEL USUARIO 'developer'
echo    (Solo personal tecnico de ANgesLAB)
echo ==================================================================
echo.
echo  Esta herramienta SOLO cambia la contrasena del usuario
echo  'developer' en la instalacion de este equipo. No modifica el
echo  programa ni los datos del cliente.
echo.
echo  Antes de continuar, CIERRE ANgesLAB si esta abierto.
echo.
pause

rem --- Buscar Python en el sistema ---
where python >nul 2>&1
if %errorlevel%==0 (
    python "%~dp0aplicar_actualizacion.py" --solo-dev %*
    goto fin
)
where py >nul 2>&1
if %errorlevel%==0 (
    py "%~dp0aplicar_actualizacion.py" --solo-dev %*
    goto fin
)

echo.
echo [ERROR] No se encontro Python en este equipo.
echo         Si ANgesLAB funciona, Python esta instalado pero no en PATH.
echo         Contacte a soporte tecnico de ANgesLAB.

:fin
echo.
echo ------------------------------------------------------------------
echo  Proceso finalizado. Puede cerrar esta ventana.
echo ------------------------------------------------------------------
pause
