; ============================================================================
; ANgesLAB v2.0 - Script de Instalacion (Inno Setup 6)
; Sistema de Gestion de Laboratorio Clinico
; Copyright 2024-2026 ANgesLAB Solutions
; ============================================================================

#define MyAppName "ANgesLAB"
#define MyAppFullName "ANgesLAB - Sistema de Gestion de Laboratorio Clinico"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "ANgesLAB Solutions"
#define MyAppURL "https://angeslab.com"
#define MyAppSupportURL "https://angeslab.com/soporte"
#define MyAppContact "soporte@angeslab.com"
#define MyAppExeName "ANgesLAB.pyw"
#define MyAppCopyright "Copyright 2024-2026 ANgesLAB Solutions"

; ============================================================================
; [Setup] - Configuracion General del Instalador
; ============================================================================
[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppFullName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppContact={#MyAppContact}
AppCopyright={#MyAppCopyright}
AppComments=Software profesional para la gestion integral de laboratorios clinicos. Incluye gestion de pacientes, solicitudes, resultados, facturacion, reportes y mas.
DefaultDirName=C:\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=licencia.txt
InfoBeforeFile=info_antes.txt
OutputDir=output
OutputBaseFilename=ANgesLAB_Setup_v2.1
SetupIconFile=..\angeslab_icon.ico
UninstallDisplayIcon={app}\angeslab_icon.ico
UninstallDisplayName={#MyAppFullName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupLogging=yes
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador de {#MyAppFullName}
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DisableWelcomePage=no
ShowLanguageDialog=no

; ============================================================================
; [Languages] - Idioma Espanol
; ============================================================================
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; ============================================================================
; [Messages] - Mensajes Personalizados del Wizard
; ============================================================================
[Messages]
spanish.BeveledLabel=ANgesLAB Solutions
spanish.WelcomeLabel1=Bienvenido al Asistente de Instalacion de {#MyAppName}
spanish.WelcomeLabel2=Este asistente lo guiara durante la instalacion de {#MyAppFullName} v{#MyAppVersion} en su equipo.%n%nCreado por: {#MyAppPublisher}%n%nSe recomienda cerrar todas las aplicaciones antes de continuar.%n%nHaga clic en Siguiente para continuar, o en Cancelar para salir del asistente.
spanish.FinishedHeadingLabel=Instalacion de {#MyAppName} Completada
spanish.FinishedLabel=El asistente ha completado la instalacion de {#MyAppFullName} en su equipo.%n%nPuede ejecutar la aplicacion haciendo doble clic en el acceso directo del escritorio.
spanish.FinishedRestartLabel=Para completar la instalacion de {#MyAppName}, el asistente debe reiniciar su equipo. Desea reiniciar ahora?
spanish.StatusExtractFiles=Extrayendo archivos del sistema...
spanish.StatusCreateIcons=Creando accesos directos...
spanish.StatusCreateDir=Creando directorios...
spanish.StatusRollback=Deshaciendo cambios...

; ============================================================================
; [CustomMessages] - Mensajes Personalizados Adicionales
; ============================================================================
[CustomMessages]
spanish.DesktopIcon=Crear acceso directo en el &Escritorio
spanish.StartMenuIcon=Crear grupo en el Menu &Inicio
spanish.LaunchAfterInstall=&Ejecutar ANgesLAB ahora
spanish.InstallDeps=Instalando dependencias de Python...
spanish.AppDescription=Sistema profesional de gestion de laboratorio clinico
spanish.RequirementsTitle=Verificacion de Requisitos del Sistema
spanish.RequirementsSubtitle=El instalador verificara que su equipo cumple con los requisitos minimos
spanish.PythonFound=Python detectado correctamente
spanish.PythonNotFound=Python NO detectado en el sistema
spanish.OLEDBFound=Microsoft Access Database Engine detectado
spanish.OLEDBNotFound=Microsoft Access Database Engine NO detectado
spanish.SystemOK=Su sistema cumple con los requisitos minimos
spanish.SystemWarning=Atencion: Algunos requisitos no se cumplen

; ============================================================================
; [Types] - Tipos de Instalacion
; ============================================================================
[Types]
Name: "full"; Description: "Instalacion Completa (recomendada)"
Name: "custom"; Description: "Instalacion Personalizada"; Flags: iscustom

; ============================================================================
; [Components] - Componentes Instalables
; ============================================================================
[Components]
Name: "main"; Description: "Aplicacion Principal ANgesLAB"; Types: full custom; Flags: fixed
Name: "database"; Description: "Base de Datos (solo primera instalacion)"; Types: full custom
Name: "resources"; Description: "Recursos Graficos (imagenes y logos)"; Types: full custom
Name: "modules"; Description: "Modulos del Sistema (28 modulos)"; Types: full custom; Flags: fixed
Name: "ia"; Description: "IA Clinica - Interpretacion inteligente de resultados (matplotlib, graficas, Ollama/Claude)"; Types: full custom

; ============================================================================
; [Tasks] - Tareas Opcionales
; ============================================================================
[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "Accesos directos:"; Flags: checked
Name: "startmenuicon"; Description: "{cm:StartMenuIcon}"; GroupDescription: "Accesos directos:"; Flags: checked
Name: "installia"; Description: "Instalar librerias de IA avanzada (requiere internet, ~50 MB: matplotlib, requests, anthropic)"; GroupDescription: "Funcionalidades adicionales:"; Flags: checked; Components: ia

; ============================================================================
; [Dirs] - Directorios a Crear
; ============================================================================
[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\modulos"; Permissions: users-modify
Name: "{app}\logos"; Permissions: users-modify
Name: "{app}\reportes"; Permissions: users-modify
Name: "{app}\respaldos"; Permissions: users-modify
Name: "{app}\firmas"; Permissions: users-modify

; ============================================================================
; [Files] - Archivos a Instalar
; ============================================================================
[Files]
; --- Aplicacion Principal ---
Source: "..\ANgesLAB.pyw"; DestDir: "{app}"; Components: main; Flags: ignoreversion; \
  AfterInstall: SetProgressMessage('Instalando aplicacion principal...')
Source: "..\angeslab_icon.ico"; DestDir: "{app}"; Components: main; Flags: ignoreversion

; --- Base de Datos ---
Source: "..\ANgesLAB.accdb"; DestDir: "{app}"; Components: database; Flags: onlyifdoesntexist uninsneveruninstall; \
  AfterInstall: SetProgressMessage('Configurando base de datos...')

; --- Recursos Graficos ---
Source: "..\fondo.png"; DestDir: "{app}"; Components: resources; Flags: ignoreversion; \
  AfterInstall: SetProgressMessage('Instalando recursos graficos...')
Source: "..\laboratorio-clinico-2.png"; DestDir: "{app}"; Components: resources; Flags: ignoreversion
Source: "..\microscopio_login.png"; DestDir: "{app}"; Components: resources; Flags: ignoreversion
Source: "..\microscopio_logo.png"; DestDir: "{app}"; Components: resources; Flags: ignoreversion

; --- Logos ---
Source: "..\logos\logo_laboratorio.jpg"; DestDir: "{app}\logos"; Components: resources; Flags: ignoreversion
Source: "..\logos\logo_laboratorio.png"; DestDir: "{app}\logos"; Components: resources; Flags: ignoreversion

; --- Configuracion IA (archivo JSON, preservar si existe) ---
Source: "..\config_ia.json"; DestDir: "{app}"; Components: ia; Flags: onlyifdoesntexist uninsneveruninstall

; --- Modulos del Sistema (28 modulos) ---
Source: "..\modulos\__init__.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion; \
  AfterInstall: SetProgressMessage('Instalando modulos del sistema...')
Source: "..\modulos\calculos_automaticos.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\config_administrativa.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\config_numeracion.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\demo_config.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\demo_seed_db.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\envio_resultados.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\facturacion_fiscal.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\flujo_trabajo.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\form_inf_config.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\gestor_solicitudes.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\gtt_captura.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\gtt_reporte.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\historial_clinico.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\modulo_administrativo.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\plantillas_reportes.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\reportes_especificaciones.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\reportes_resultados.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\seguridad_db.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\splash_screen.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\utilidades_db.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\ventana_administrativa.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\ventana_config_administrativa.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\ventana_config_numeracion.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\ventana_configuracion_completa.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion
Source: "..\modulos\veterinario.py"; DestDir: "{app}\modulos"; Components: modules; Flags: ignoreversion

; --- Modulos de IA e Historial Avanzado ---
Source: "..\modulos\graficas_historial.py"; DestDir: "{app}\modulos"; Components: ia; Flags: ignoreversion; \
  AfterInstall: SetProgressMessage('Instalando modulo de graficas clinicas...')
Source: "..\modulos\ia_interpretacion.py"; DestDir: "{app}\modulos"; Components: ia; Flags: ignoreversion; \
  AfterInstall: SetProgressMessage('Instalando motor de IA clinica...')

; --- Scripts de Dependencias (se eliminan despues de usarse) ---
Source: "instalar_dependencias.bat"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
Source: "instalar_dependencias_ia.bat"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall; Components: ia

; ============================================================================
; [Icons] - Accesos Directos
; ============================================================================
[Icons]
; Acceso directo en el Escritorio
Name: "{autodesktop}\ANgesLAB"; \
  Filename: "{code:GetPythonwPath}"; \
  Parameters: """{app}\{#MyAppExeName}"""; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\angeslab_icon.ico"; \
  Comment: "{#MyAppFullName} v{#MyAppVersion}"; \
  Tasks: desktopicon

; Menu Inicio - Aplicacion
Name: "{group}\ANgesLAB"; \
  Filename: "{code:GetPythonwPath}"; \
  Parameters: """{app}\{#MyAppExeName}"""; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\angeslab_icon.ico"; \
  Comment: "Iniciar {#MyAppFullName}"; \
  Tasks: startmenuicon

; Menu Inicio - Desinstalar
Name: "{group}\Desinstalar ANgesLAB"; \
  Filename: "{uninstallexe}"; \
  IconFilename: "{app}\angeslab_icon.ico"; \
  Comment: "Desinstalar {#MyAppName} de su equipo"; \
  Tasks: startmenuicon

; Menu Inicio - Carpeta de Instalacion
Name: "{group}\Abrir Carpeta ANgesLAB"; \
  Filename: "{app}"; \
  Comment: "Abrir la carpeta donde esta instalado ANgesLAB"; \
  Tasks: startmenuicon

; ============================================================================
; [Run] - Acciones Post-Instalacion
; ============================================================================
[Run]
; Instalar dependencias base de Python
Filename: "{sys}\cmd.exe"; \
  Parameters: "/c ""{app}\instalar_dependencias.bat"""; \
  WorkingDir: "{app}"; \
  StatusMsg: "Instalando librerias base de Python (reportlab, Pillow, pypiwin32)..."; \
  Flags: runhidden waituntilterminated; \
  Description: "Instalar dependencias base de Python"

; Instalar dependencias de IA Clinica (solo si el componente IA fue seleccionado)
Filename: "{sys}\cmd.exe"; \
  Parameters: "/c ""{app}\instalar_dependencias_ia.bat"""; \
  WorkingDir: "{app}"; \
  StatusMsg: "Instalando librerias de IA Clinica (matplotlib, requests, anthropic)..."; \
  Flags: runhidden waituntilterminated; \
  Components: ia; \
  Tasks: installia; \
  Description: "Instalar dependencias de IA Clinica (graficas e interpretacion)"

; Opcion para ejecutar ANgesLAB al finalizar
Filename: "{code:GetPythonwPath}"; \
  Parameters: """{app}\{#MyAppExeName}"""; \
  WorkingDir: "{app}"; \
  Description: "{cm:LaunchAfterInstall}"; \
  Flags: nowait postinstall skipifsilent shellexec

; ============================================================================
; [UninstallDelete] - Limpieza al Desinstalar
; ============================================================================
[UninstallDelete]
Type: filesandordirs; Name: "{app}\modulos\__pycache__"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\modulos\*.pyc"
Type: files; Name: "{app}\*.pyc"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\config_ia.json"
Type: dirifempty; Name: "{app}\reportes"
Type: dirifempty; Name: "{app}\respaldos"
Type: dirifempty; Name: "{app}\firmas"
; NOTA: NO se elimina ANgesLAB.accdb para preservar datos del cliente

; ============================================================================
; [Registry] - Entradas de Registro
; ============================================================================
[Registry]
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; ============================================================================
; [Code] - Pascal Script (Logica del Instalador)
; ============================================================================
[Code]

var
  RequirementsPage: TWizardPage;
  PythonStatusLabel: TNewStaticText;
  OLEDBStatusLabel: TNewStaticText;
  SystemStatusLabel: TNewStaticText;
  PythonPath: String;
  PythonFound: Boolean;
  OLEDBFound: Boolean;

// -----------------------------------------------------------------------
// Funcion auxiliar: Mostrar mensaje de progreso durante la instalacion
// -----------------------------------------------------------------------
procedure SetProgressMessage(Msg: String);
begin
  WizardForm.StatusLabel.Caption := Msg;
end;

// -----------------------------------------------------------------------
// Detectar Python en el sistema
// Busca en PATH, rutas comunes y registro de Windows
// -----------------------------------------------------------------------
function DetectPython(): Boolean;
var
  PythonExe: String;
  ResultCode: Integer;
  VersionOutput: AnsiString;
  SearchPaths: array of String;
  I: Integer;
begin
  Result := False;
  PythonPath := '';

  // Intentar 'python' en PATH
  if Exec('cmd.exe', '/c python --version > "%TEMP%\python_ver.txt" 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      if LoadStringFromFile(ExpandConstant('{tmp}\python_ver.txt'), VersionOutput) then
      begin
        // No necesitamos verificar la salida exacta, si ejecuto sin error Python esta presente
      end;
      // Buscar ruta de pythonw.exe
      if Exec('cmd.exe', '/c where pythonw.exe > "%TEMP%\pythonw_path.txt" 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        if LoadStringFromFile(ExpandConstant('{tmp}\pythonw_path.txt'), VersionOutput) then
        begin
          PythonPath := Trim(String(VersionOutput));
          // Tomar solo la primera linea si hay multiples
          if Pos(#13, PythonPath) > 0 then
            PythonPath := Copy(PythonPath, 1, Pos(#13, PythonPath) - 1);
          if Pos(#10, PythonPath) > 0 then
            PythonPath := Copy(PythonPath, 1, Pos(#10, PythonPath) - 1);
        end;
      end;
      Result := True;
      Exit;
    end;
  end;

  // Buscar en rutas comunes de instalacion
  SetLength(SearchPaths, 8);
  SearchPaths[0] := ExpandConstant('{localappdata}\Programs\Python\Python314\pythonw.exe');
  SearchPaths[1] := ExpandConstant('{localappdata}\Programs\Python\Python313\pythonw.exe');
  SearchPaths[2] := ExpandConstant('{localappdata}\Programs\Python\Python312\pythonw.exe');
  SearchPaths[3] := ExpandConstant('{localappdata}\Programs\Python\Python311\pythonw.exe');
  SearchPaths[4] := ExpandConstant('{localappdata}\Programs\Python\Python310\pythonw.exe');
  SearchPaths[5] := 'C:\Python314\pythonw.exe';
  SearchPaths[6] := 'C:\Python313\pythonw.exe';
  SearchPaths[7] := 'C:\Python312\pythonw.exe';

  for I := 0 to GetArrayLength(SearchPaths) - 1 do
  begin
    if FileExists(SearchPaths[I]) then
    begin
      PythonPath := SearchPaths[I];
      Result := True;
      Exit;
    end;
  end;

  // Buscar en registro de Windows
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.14\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then
    begin
      Result := True;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.13\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then
    begin
      Result := True;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.12\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then
    begin
      Result := True;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.14\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then
    begin
      Result := True;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.13\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then
    begin
      Result := True;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.12\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

// -----------------------------------------------------------------------
// Detectar Microsoft Access OLEDB Provider
// -----------------------------------------------------------------------
function DetectOLEDB(): Boolean;
var
  SubKey: String;
begin
  Result := False;
  SubKey := 'SOFTWARE\Classes\Microsoft.ACE.OLEDB.12.0';
  if RegKeyExists(HKLM, SubKey) then
  begin
    Result := True;
    Exit;
  end;
  // Tambien buscar en el proveedor de 16 bits
  SubKey := 'SOFTWARE\Classes\Microsoft.ACE.OLEDB.16.0';
  if RegKeyExists(HKLM, SubKey) then
  begin
    Result := True;
    Exit;
  end;
end;

// -----------------------------------------------------------------------
// Funcion para obtener la ruta de pythonw.exe (usada en [Icons])
// -----------------------------------------------------------------------
function GetPythonwPath(Param: String): String;
begin
  if PythonPath <> '' then
    Result := PythonPath
  else
    Result := 'pythonw.exe';
end;

// -----------------------------------------------------------------------
// Crear pagina personalizada de Verificacion de Requisitos
// -----------------------------------------------------------------------
procedure CreateRequirementsPage();
var
  TitleLabel: TNewStaticText;
  SeparatorLabel: TNewStaticText;
  ReqLabel: TNewStaticText;
  YPos: Integer;
begin
  RequirementsPage := CreateCustomPage(wpWelcome,
    ExpandConstant('{cm:RequirementsTitle}'),
    ExpandConstant('{cm:RequirementsSubtitle}'));

  YPos := 8;

  // --- Titulo de seccion ---
  TitleLabel := TNewStaticText.Create(RequirementsPage);
  TitleLabel.Parent := RequirementsPage.Surface;
  TitleLabel.Caption := 'ESTADO DE REQUISITOS DEL SISTEMA';
  TitleLabel.Font.Style := [fsBold];
  TitleLabel.Font.Size := 10;
  TitleLabel.Left := 0;
  TitleLabel.Top := YPos;
  YPos := YPos + 30;

  // --- Separador ---
  SeparatorLabel := TNewStaticText.Create(RequirementsPage);
  SeparatorLabel.Parent := RequirementsPage.Surface;
  SeparatorLabel.Caption := '________________________________________________________________';
  SeparatorLabel.Font.Color := clGray;
  SeparatorLabel.Left := 0;
  SeparatorLabel.Top := YPos;
  YPos := YPos + 28;

  // --- Estado de Python ---
  PythonStatusLabel := TNewStaticText.Create(RequirementsPage);
  PythonStatusLabel.Parent := RequirementsPage.Surface;
  PythonStatusLabel.Left := 0;
  PythonStatusLabel.Top := YPos;
  PythonStatusLabel.Font.Size := 9;
  PythonStatusLabel.AutoSize := True;
  if PythonFound then
  begin
    PythonStatusLabel.Caption := '  [OK]  Python detectado: ' + PythonPath;
    PythonStatusLabel.Font.Color := clGreen;
  end
  else
  begin
    PythonStatusLabel.Caption := '  [X]  Python NO detectado. Descargue desde: python.org/downloads';
    PythonStatusLabel.Font.Color := clRed;
  end;
  YPos := YPos + 26;

  // --- Estado de OLEDB ---
  OLEDBStatusLabel := TNewStaticText.Create(RequirementsPage);
  OLEDBStatusLabel.Parent := RequirementsPage.Surface;
  OLEDBStatusLabel.Left := 0;
  OLEDBStatusLabel.Top := YPos;
  OLEDBStatusLabel.Font.Size := 9;
  OLEDBStatusLabel.AutoSize := True;
  if OLEDBFound then
  begin
    OLEDBStatusLabel.Caption := '  [OK]  Microsoft Access Database Engine detectado';
    OLEDBStatusLabel.Font.Color := clGreen;
  end
  else
  begin
    OLEDBStatusLabel.Caption := '  [!]  Access Database Engine no detectado (necesario para la BD)';
    OLEDBStatusLabel.Font.Color := $000080FF; // Naranja
  end;
  YPos := YPos + 26;

  // --- Separador 2 ---
  SeparatorLabel := TNewStaticText.Create(RequirementsPage);
  SeparatorLabel.Parent := RequirementsPage.Surface;
  SeparatorLabel.Caption := '________________________________________________________________';
  SeparatorLabel.Font.Color := clGray;
  SeparatorLabel.Left := 0;
  SeparatorLabel.Top := YPos;
  YPos := YPos + 28;

  // --- Estado General ---
  SystemStatusLabel := TNewStaticText.Create(RequirementsPage);
  SystemStatusLabel.Parent := RequirementsPage.Surface;
  SystemStatusLabel.Left := 0;
  SystemStatusLabel.Top := YPos;
  SystemStatusLabel.Font.Size := 9;
  SystemStatusLabel.Font.Style := [fsBold];
  SystemStatusLabel.AutoSize := True;
  if PythonFound then
  begin
    SystemStatusLabel.Caption := '  Su sistema cumple con los requisitos. Puede continuar la instalacion.';
    SystemStatusLabel.Font.Color := clGreen;
  end
  else
  begin
    SystemStatusLabel.Caption := '  ATENCION: Instale Python antes de continuar.';
    SystemStatusLabel.Font.Color := clRed;
  end;
  YPos := YPos + 40;

  // --- Requisitos Minimos (informacion) ---
  TitleLabel := TNewStaticText.Create(RequirementsPage);
  TitleLabel.Parent := RequirementsPage.Surface;
  TitleLabel.Caption := 'REQUISITOS MINIMOS:';
  TitleLabel.Font.Style := [fsBold];
  TitleLabel.Font.Size := 9;
  TitleLabel.Left := 0;
  TitleLabel.Top := YPos;
  YPos := YPos + 24;

  ReqLabel := TNewStaticText.Create(RequirementsPage);
  ReqLabel.Parent := RequirementsPage.Surface;
  ReqLabel.Left := 16;
  ReqLabel.Top := YPos;
  ReqLabel.Font.Size := 9;
  ReqLabel.AutoSize := True;
  ReqLabel.Caption :=
    '  - Sistema Operativo: Windows 10 / Windows 11 (64-bit)' + #13#10 +
    '  - Procesador: Intel Core i3 o superior' + #13#10 +
    '  - Memoria RAM: 4 GB minimo (recomendado 8 GB)' + #13#10 +
    '  - Espacio en disco: 100 MB disponibles' + #13#10 +
    '  - Pantalla: Resolucion minima 1366 x 768' + #13#10 +
    '  - Python 3.8 o superior (python.org)' + #13#10 +
    '  - Microsoft Access Database Engine 2016' + #13#10 +
    '  - Conexion a internet (para instalar dependencias)';
end;

// -----------------------------------------------------------------------
// InitializeSetup - Se ejecuta al iniciar el instalador
// -----------------------------------------------------------------------
function InitializeSetup(): Boolean;
begin
  // Detectar requisitos del sistema
  PythonFound := DetectPython();
  OLEDBFound := DetectOLEDB();

  // Si Python no esta instalado, mostrar advertencia pero permitir continuar
  if not PythonFound then
  begin
    if MsgBox(
      'ANgesLAB requiere Python 3.8 o superior para funcionar.' + #13#10 +
      #13#10 +
      'Python NO fue detectado en su sistema.' + #13#10 +
      #13#10 +
      'Puede descargar Python desde:' + #13#10 +
      'https://www.python.org/downloads/' + #13#10 +
      #13#10 +
      'IMPORTANTE: Al instalar Python, marque la casilla' + #13#10 +
      '"Add Python to PATH".' + #13#10 +
      #13#10 +
      'Desea continuar con la instalacion de todas formas?' + #13#10 +
      '(Podra instalar Python posteriormente)',
      mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;

  Result := True;
end;

// -----------------------------------------------------------------------
// InitializeWizard - Configura el wizard
// -----------------------------------------------------------------------
procedure InitializeWizard();
begin
  // Crear la pagina de requisitos del sistema
  CreateRequirementsPage();

  // Personalizar apariencia del wizard
  WizardForm.WelcomeLabel1.Font.Size := 12;
  WizardForm.WelcomeLabel1.Font.Color := $00993300; // Azul oscuro
end;

// -----------------------------------------------------------------------
// NextButtonClick - Validaciones al presionar Siguiente
// -----------------------------------------------------------------------
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  // En la pagina de requisitos, advertir si Python no esta instalado
  if CurPageID = RequirementsPage.ID then
  begin
    if not PythonFound then
    begin
      if MsgBox(
        'Python no fue detectado en su sistema.' + #13#10 +
        'ANgesLAB no podra ejecutarse sin Python.' + #13#10 +
        #13#10 +
        'Desea continuar con la instalacion de todas formas?',
        mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end;

    if not OLEDBFound then
    begin
      MsgBox(
        'Microsoft Access Database Engine no fue detectado.' + #13#10 +
        #13#10 +
        'Este componente es necesario para la base de datos.' + #13#10 +
        'Descargue e instale desde:' + #13#10 +
        'https://www.microsoft.com/en-us/download/details.aspx?id=54920' + #13#10 +
        #13#10 +
        'Puede continuar la instalacion y configurar este componente despues.',
        mbInformation, MB_OK);
    end;
  end;
end;

// -----------------------------------------------------------------------
// CurPageChanged - Eventos al cambiar de pagina
// -----------------------------------------------------------------------
procedure CurPageChanged(CurPageID: Integer);
begin
  // En la pagina de finalizacion, mostrar informacion adicional
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption :=
      'ANgesLAB v' + '{#MyAppVersion}' + ' se ha instalado correctamente en su equipo.' + #13#10 +
      #13#10 +
      'Ubicacion: ' + ExpandConstant('{app}') + #13#10 +
      #13#10 +
      'Credenciales iniciales:' + #13#10 +
      '  Usuario: admin' + #13#10 +
      '  Contrasena: admin123' + #13#10 +
      #13#10 +
      'NOVEDADES v2.1:' + #13#10 +
      '  - Graficas de evolucion clinica (Historial > Graficas)' + #13#10 +
      '  - Interpretacion IA de resultados (Historial > IA Clinica)' + #13#10 +
      '  - Reportes PDF con interpretacion clinica' + #13#10 +
      #13#10 +
      'IMPORTANTE: Cambie la contrasena del administrador' + #13#10 +
      'despues del primer inicio de sesion.' + #13#10 +
      #13#10 +
      'Haga clic en Finalizar para cerrar el asistente.';
  end;
end;

// -----------------------------------------------------------------------
// CurStepChanged - Eventos por paso de instalacion
// -----------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Registrar la instalacion exitosa
    SaveStringToFile(ExpandConstant('{app}\install.log'),
      'ANgesLAB v' + '{#MyAppVersion}' + ' instalado exitosamente.' + #13#10 +
      'Fecha: ' + GetDateTimeString('yyyy/mm/dd hh:nn:ss', '-', ':') + #13#10 +
      'Directorio: ' + ExpandConstant('{app}') + #13#10,
      False);
  end;
end;

// -----------------------------------------------------------------------
// Confirmacion de desinstalacion
// -----------------------------------------------------------------------
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox(
    'Esta a punto de desinstalar ANgesLAB de su equipo.' + #13#10 +
    #13#10 +
    'NOTA: La base de datos (ANgesLAB.accdb) con toda la' + #13#10 +
    'informacion de pacientes y resultados NO sera eliminada.' + #13#10 +
    'Puede encontrarla en la carpeta de instalacion.' + #13#10 +
    #13#10 +
    'Desea continuar con la desinstalacion?',
    mbConfirmation, MB_YESNO) = IDYES;
end;
