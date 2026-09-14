@echo off
chcp 65001 >nul 2>&1
title ANgesLAB - Diagnostico del equipo

rem ============================================================================
rem  Lanzador del diagnostico. Se ejecuta en el equipo del cliente ANTES de
rem  instalar. No modifica nada: solo lee el estado del equipo y reporta que
rem  falta.
rem
rem  -ExecutionPolicy Bypass es necesario porque en un equipo de cliente la
rem  politica por defecto (Restricted) impide ejecutar cualquier .ps1.
rem ============================================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnostico_equipo.ps1"

if %errorlevel% neq 0 (
    echo.
    echo  No se pudo ejecutar el diagnostico.
    echo  Pruebe con clic derecho ^> Ejecutar como administrador.
    echo.
    pause
)
