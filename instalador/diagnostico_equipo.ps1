# =============================================================================
#  ANgesLAB - Diagnostico del equipo antes de instalar
#
#  Se ejecuta en el equipo del CLIENTE antes de lanzar el instalador.
#  No modifica nada: solo lee y reporta.
#
#  Comprueba lo que el instalador NO comprueba: que la arquitectura de Python
#  y la del motor de Access coincidan. Es la causa numero uno de que ANgesLAB
#  se instale sin errores y luego no abra la base de datos.
# =============================================================================

$ErrorActionPreference = 'SilentlyContinue'

function Write-Titulo($texto) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-OK($texto)     { Write-Host "  [OK]    $texto" -ForegroundColor Green }
function Write-Falta($texto)  { Write-Host "  [FALTA] $texto" -ForegroundColor Red }
function Write-Aviso($texto)  { Write-Host "  [AVISO] $texto" -ForegroundColor Yellow }
function Write-Info($texto)   { Write-Host "          $texto" -ForegroundColor Gray }

$problemas = New-Object System.Collections.ArrayList
$avisos    = New-Object System.Collections.ArrayList

Clear-Host
Write-Host ""
Write-Host "  ANgesLAB v2.4 - Diagnostico del equipo" -ForegroundColor White
Write-Host "  Fecha: $(Get-Date -Format 'dd/MM/yyyy HH:mm')" -ForegroundColor Gray
Write-Host "  Equipo: $env:COMPUTERNAME" -ForegroundColor Gray

# -----------------------------------------------------------------------------
Write-Titulo "1. SISTEMA OPERATIVO"

$os = Get-CimInstance Win32_OperatingSystem
$esX64 = [Environment]::Is64BitOperatingSystem

Write-Info "$($os.Caption) - Build $($os.BuildNumber)"

if ($esX64) {
    Write-OK "Windows de 64 bits"
} else {
    Write-Falta "Windows de 32 bits - ANgesLAB requiere 64 bits"
    [void]$problemas.Add("El sistema operativo es de 32 bits. ANgesLAB requiere Windows 64 bits.")
}

if ($os.BuildNumber -lt 10240) {
    Write-Falta "Version de Windows anterior a Windows 10"
    [void]$problemas.Add("Se requiere Windows 10 o superior.")
} else {
    Write-OK "Version de Windows compatible"
}

# -----------------------------------------------------------------------------
Write-Titulo "2. PYTHON"

$pythonExe   = $null
$pythonBits  = $null
$pythonVer   = $null
$pythonEnPath = $false

# Buscar primero en el PATH
$cmd = Get-Command python.exe
if ($cmd) {
    $pythonExe = $cmd.Source
    $pythonEnPath = $true
} else {
    # Rutas habituales de instalacion por usuario y por maquina
    $rutas = @()
    foreach ($v in 315,314,313,312,311,310) {
        $rutas += "$env:LOCALAPPDATA\Programs\Python\Python$v\python.exe"
        $rutas += "C:\Python$v\python.exe"
        $rutas += "C:\Program Files\Python$v\python.exe"
    }
    foreach ($r in $rutas) {
        if (Test-Path $r) { $pythonExe = $r; break }
    }
}

if ($pythonExe) {
    $pythonVer  = (& $pythonExe --version 2>&1) -replace 'Python\s*',''
    $pythonBits = & $pythonExe -c "import struct;print(struct.calcsize('P')*8)"
    $pythonBits = [int]($pythonBits -replace '\D','')

    Write-OK "Python $pythonVer encontrado"
    Write-Info "Ruta: $pythonExe"
    Write-Info "Arquitectura: $pythonBits bits"

    if (-not $pythonEnPath) {
        Write-Aviso "Python NO esta en el PATH del sistema"
        Write-Info  "pip fallara desde la consola. El instalador lo detecta igual."
        [void]$avisos.Add("Python no esta en el PATH: use 'py -m pip' en vez de 'pip'.")
    }

    $verNum = [version]($pythonVer -replace '[^\d\.].*','')
    if ($verNum -lt [version]'3.8') {
        Write-Falta "Python $pythonVer es demasiado antiguo (se requiere 3.8+)"
        [void]$problemas.Add("Actualice Python a 3.8 o superior.")
    }
} else {
    Write-Falta "Python NO esta instalado"
    [void]$problemas.Add("Instale Python 3 de 64 bits desde python.org marcando 'Add python.exe to PATH'.")
}

# -----------------------------------------------------------------------------
Write-Titulo "3. MOTOR DE BASE DE DATOS (Microsoft Access Database Engine)"

# El proveedor se registra como COM. Cada arquitectura tiene su propia vista
# del registro: la de 64 bits en Classes, la de 32 bits en WOW6432Node.
$ace64 = Test-Path 'HKLM:\SOFTWARE\Classes\Microsoft.ACE.OLEDB.12.0'
$ace32 = Test-Path 'HKLM:\SOFTWARE\WOW6432Node\Classes\Microsoft.ACE.OLEDB.12.0'

$aceBits = $null
if ($ace64 -and $ace32) {
    Write-OK "Motor ACE instalado en 64 y 32 bits"
    $aceBits = 'ambas'
} elseif ($ace64) {
    Write-OK "Motor ACE instalado (64 bits)"
    $aceBits = 64
} elseif ($ace32) {
    Write-OK "Motor ACE instalado (32 bits)"
    $aceBits = 32
} else {
    Write-Falta "Motor ACE NO instalado"
    [void]$problemas.Add("Instale Microsoft Access Database Engine 2016 (redistribuible).")
}

# Office instalado condiciona que redistribuible se puede instalar
$office = Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Office' 2>$null | Select-Object -First 1
$officeC2R = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration' 2>$null
if ($officeC2R) {
    Write-Info "Office instalado: $($officeC2R.Platform) ($($officeC2R.ProductReleaseIds))"
    if ($officeC2R.Platform -eq 'x86') {
        Write-Aviso "Office es de 32 bits: el redistribuible ACE de 64 bits se negara a instalar"
        Write-Info  "Solucion: instalarlo con el modificador  /quiet"
        [void]$avisos.Add("Office de 32 bits presente: instale ACE con /quiet o use ACE+Python de 32 bits.")
    }
} elseif ($office) {
    Write-Info "Hay una instalacion de Office en el equipo"
}

# -----------------------------------------------------------------------------
Write-Titulo "4. COMPATIBILIDAD PYTHON <-> ACE   (la comprobacion critica)"

if ($pythonBits -and $aceBits) {
    if ($aceBits -eq 'ambas' -or $aceBits -eq $pythonBits) {
        Write-OK "Arquitecturas compatibles: Python $pythonBits bits con ACE $aceBits bits"
        Write-Info "ANgesLAB podra abrir la base de datos."
    } else {
        Write-Falta "INCOMPATIBLES: Python es de $pythonBits bits y ACE de $aceBits bits"
        Write-Info  "ANgesLAB se instalara sin errores pero fallara al abrir la base con"
        Write-Info  "'Proveedor Microsoft.ACE.OLEDB.12.0 no registrado'."
        [void]$problemas.Add("Python ($pythonBits bits) y ACE ($aceBits bits) no coinciden. Reinstale uno de los dos para que ambos sean de la misma arquitectura.")
    }
} else {
    Write-Aviso "No se puede comprobar: falta Python o falta ACE"
}

# Prueba real de conexion, que es la unica prueba que no admite discusion
if ($pythonExe -and $aceBits) {
    Write-Host ""
    Write-Info "Probando conexion real con el proveedor..."
    $prueba = & $pythonExe -c "import win32com.client as w; c=w.Dispatch('ADODB.Connection'); print('PROVEEDOR_OK')" 2>&1
    if ($prueba -match 'PROVEEDOR_OK') {
        Write-OK "ADODB responde correctamente"
    } elseif ($prueba -match 'No module named') {
        Write-Aviso "Falta pywin32 (se instala con las dependencias, es normal antes de instalar)"
    } else {
        Write-Falta "ADODB no responde"
        Write-Info  "$prueba"
    }
}

# -----------------------------------------------------------------------------
Write-Titulo "5. INSTALACION EXISTENTE DE ANgesLAB"

$rutaApp = 'C:\ANgesLAB'
if (Test-Path $rutaApp) {
    $ver = 'desconocida'
    if (Test-Path "$rutaApp\VERSION") { $ver = (Get-Content "$rutaApp\VERSION" -Raw).Trim() }
    Write-Aviso "YA EXISTE una instalacion (version $ver) en $rutaApp"
    Write-Host ""
    Write-Host "  >>> NO ejecute el instalador .exe <<<" -ForegroundColor Yellow
    Write-Host "  Use  actualizador\ACTUALIZAR_ANgesLAB.bat  para conservar" -ForegroundColor Yellow
    Write-Host "  pacientes, resultados y facturacion del laboratorio." -ForegroundColor Yellow

    $bd = Get-Item "$rutaApp\ANgesLAB.accdb" 2>$null
    if ($bd) {
        $mb = [math]::Round($bd.Length / 1MB, 1)
        Write-Info "Base de datos: $mb MB, modificada $($bd.LastWriteTime.ToString('dd/MM/yyyy HH:mm'))"
    }
    [void]$avisos.Add("Equipo con ANgesLAB $ver ya instalado: use el ACTUALIZADOR, no el instalador.")
} else {
    Write-OK "Equipo limpio: corresponde instalacion nueva con el .exe"
}

# -----------------------------------------------------------------------------
Write-Titulo "6. RECURSOS E IMPRESORAS"

$disco = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$libreGB = [math]::Round($disco.FreeSpace / 1GB, 1)
if ($libreGB -lt 2) {
    Write-Falta "Espacio libre en C: $libreGB GB (se recomiendan al menos 2 GB)"
    [void]$problemas.Add("Libere espacio en disco C:.")
} else {
    Write-OK "Espacio libre en C: $libreGB GB"
}

$impresoras = Get-CimInstance Win32_Printer | Select-Object -ExpandProperty Name
if ($impresoras) {
    Write-OK "Impresoras detectadas: $($impresoras.Count)"
    foreach ($i in $impresoras) { Write-Info "- $i" }
    Write-Info "Recuerde asignarlas por funcion en Configuracion tras instalar."
} else {
    Write-Aviso "No hay impresoras instaladas"
    [void]$avisos.Add("Sin impresoras: los informes solo se podran guardar como PDF.")
}

# -----------------------------------------------------------------------------
Write-Titulo "RESUMEN"

if ($problemas.Count -eq 0) {
    Write-Host ""
    Write-Host "  EQUIPO LISTO PARA INSTALAR" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  RESUELVA ESTO ANTES DE INSTALAR:" -ForegroundColor Red
    Write-Host ""
    $n = 1
    foreach ($p in $problemas) {
        Write-Host "   $n. $p" -ForegroundColor Red
        $n++
    }
    Write-Host ""
}

if ($avisos.Count -gt 0) {
    Write-Host "  Tenga en cuenta:" -ForegroundColor Yellow
    foreach ($a in $avisos) { Write-Host "   - $a" -ForegroundColor Yellow }
    Write-Host ""
}

# Deja constancia en un archivo por si hay que revisarlo despues
$log = "$env:USERPROFILE\Desktop\ANgesLAB_diagnostico.txt"
$resumen = @()
$resumen += "ANgesLAB - Diagnostico $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
$resumen += "Equipo: $env:COMPUTERNAME"
$resumen += "SO: $($os.Caption) x64=$esX64"
$resumen += "Python: $pythonVer ($pythonBits bits) en $pythonExe"
$resumen += "ACE: $aceBits bits"
$resumen += "Instalacion previa: $(Test-Path $rutaApp)"
$resumen += ""
$resumen += "PROBLEMAS:"
$resumen += $problemas
$resumen += ""
$resumen += "AVISOS:"
$resumen += $avisos
$resumen | Out-File -FilePath $log -Encoding utf8

Write-Host "  Informe guardado en: $log" -ForegroundColor Gray
Write-Host ""
Write-Host "  Pulse una tecla para cerrar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
