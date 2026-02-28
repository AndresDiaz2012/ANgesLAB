; ============================================================================
; ANgesLAB DEMO v1.0 - Script de Instalacion (Inno Setup 6)
; Version DEMO para evaluacion comercial
; Copyright 2024-2026 ANgesLAB Solutions
; ============================================================================

#define MyAppName "ANgesLAB-Demo"
#define MyAppFullName "ANgesLAB DEMO - Sistema de Gestion de Laboratorio Clinico"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ANgesLAB Solutions"
#define MyAppURL "https://angeslab.com"
#define MyAppExeName "ANgesLAB_Demo.pyw"
#define MyAppCopyright "Copyright 2024-2026 ANgesLAB Solutions"

; ============================================================================
; [Setup] - Configuracion General
; ============================================================================
[Setup]
; GUID diferente al de produccion para no conflictar
AppId={{B2C3D4E5-F6A7-8901-BCDE-F12345678901}
AppName={#MyAppFullName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppCopyright={#MyAppCopyright}
AppComments=Version DEMO para evaluacion. Limitada a 15 dias, 5 pacientes y 10 solicitudes.
DefaultDirName=C:\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=ANgesLAB_Demo_Setup_v1.0
SetupIconFile=..\assets\angeslab_icon.ico
UninstallDisplayIcon={app}\assets\angeslab_icon.ico
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
VersionInfoDescription=Instalador DEMO de {#MyAppFullName}
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DisableWelcomePage=no
ShowLanguageDialog=no

; ============================================================================
; [Languages]
; ============================================================================
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; ============================================================================
; [Messages]
; ============================================================================
[Messages]
spanish.BeveledLabel=ANgesLAB Solutions - VERSION DEMO
spanish.WelcomeLabel1=Bienvenido a ANgesLAB DEMO
spanish.WelcomeLabel2=Este asistente instalara la version DEMO de ANgesLAB en su equipo.%n%nLa version demo le permite evaluar el software durante 15 dias.%n%nLimitaciones:%n  - Maximo 5 pacientes nuevos%n  - Maximo 10 solicitudes nuevas%n  - Modulos de configuracion deshabilitados%n  - Marca de agua DEMO en PDFs%n%nPara adquirir la licencia completa:%n  Tel: +574147204006%n  Email: diabel92@hotmail.com%n%nHaga clic en Siguiente para continuar.
spanish.FinishedHeadingLabel=Instalacion de {#MyAppName} Completada
spanish.FinishedLabel=ANgesLAB DEMO se ha instalado correctamente.

; ============================================================================
; [Tasks]
; ============================================================================
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; Flags: checked
Name: "startmenuicon"; Description: "Crear grupo en el Menu Inicio"; Flags: checked

; ============================================================================
; [Dirs]
; ============================================================================
[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\modulos"; Permissions: users-modify
Name: "{app}\logos"; Permissions: users-modify
Name: "{app}\reportes"; Permissions: users-modify

; ============================================================================
; [Files] - Archivos a Instalar
; ============================================================================
[Files]
; --- Launcher Demo (punto de entrada) ---
Source: "..\ANgesLAB_Demo.pyw"; DestDir: "{app}"; Flags: ignoreversion

; --- Aplicacion Principal (dependencia del launcher) ---
Source: "..\ANgesLAB.pyw"; DestDir: "{app}"; Flags: ignoreversion

; --- Base de Datos DEMO (siempre reemplazar con datos frescos) ---
Source: "..\ANgesLAB_Demo.accdb"; DestDir: "{app}"; Flags: ignoreversion

; --- Icono ---
Source: "..\assets\angeslab_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

; --- Recursos Graficos ---
Source: "..\assets\fondo.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\laboratorio-clinico-2.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\microscopio_login.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\microscopio_logo.png"; DestDir: "{app}\assets"; Flags: ignoreversion

; --- Logos ---
Source: "..\logos\logo_laboratorio.jpg"; DestDir: "{app}\logos"; Flags: ignoreversion
Source: "..\logos\logo_laboratorio.png"; DestDir: "{app}\logos"; Flags: ignoreversion

; --- Todos los modulos (incluyendo demo_config.py) ---
Source: "..\modulos\__init__.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\calculos_automaticos.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\config_administrativa.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\config_numeracion.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\demo_config.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\envio_resultados.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\facturacion_fiscal.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\flujo_trabajo.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\form_inf_config.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\gestor_solicitudes.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\historial_clinico.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\modulo_administrativo.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\plantillas_reportes.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\reportes_especificaciones.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\reportes_resultados.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\seguridad_db.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\splash_screen.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\utilidades_db.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\ventana_administrativa.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\ventana_config_administrativa.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\ventana_config_numeracion.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\ventana_configuracion_completa.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\veterinario.py"; DestDir: "{app}\modulos"; Flags: ignoreversion

; --- Modulos de IA e Historial Avanzado ---
Source: "..\modulos\graficas_historial.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\ia_interpretacion.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\gtt_captura.py"; DestDir: "{app}\modulos"; Flags: ignoreversion
Source: "..\modulos\gtt_reporte.py"; DestDir: "{app}\modulos"; Flags: ignoreversion

; --- Configuracion IA ---
Source: "..\config_ia.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

; --- Scripts de Dependencias (se eliminan despues de usarse) ---
Source: "instalar_dependencias_demo.bat"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall

; ============================================================================
; [Icons] - Accesos Directos (apuntan al Demo, no al original)
; ============================================================================
[Icons]
Name: "{autodesktop}\ANgesLAB DEMO"; \
  Filename: "{code:GetPythonwPath}"; \
  Parameters: """{app}\{#MyAppExeName}"""; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\assets\angeslab_icon.ico"; \
  Comment: "{#MyAppFullName}"; \
  Tasks: desktopicon

Name: "{group}\ANgesLAB DEMO"; \
  Filename: "{code:GetPythonwPath}"; \
  Parameters: """{app}\{#MyAppExeName}"""; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\assets\angeslab_icon.ico"; \
  Comment: "Iniciar {#MyAppFullName}"; \
  Tasks: startmenuicon

Name: "{group}\Desinstalar ANgesLAB DEMO"; \
  Filename: "{uninstallexe}"; \
  IconFilename: "{app}\assets\angeslab_icon.ico"; \
  Tasks: startmenuicon

; ============================================================================
; [Run] - Post-Instalacion
; ============================================================================
[Run]
; Instalar dependencias
Filename: "{sys}\cmd.exe"; \
  Parameters: "/c ""{app}\instalar_dependencias_demo.bat"""; \
  WorkingDir: "{app}"; \
  StatusMsg: "Instalando librerias de Python..."; \
  Flags: runhidden waituntilterminated

; Ejecutar demo al finalizar
Filename: "{code:GetPythonwPath}"; \
  Parameters: """{app}\{#MyAppExeName}"""; \
  WorkingDir: "{app}"; \
  Description: "Ejecutar ANgesLAB DEMO ahora"; \
  Flags: nowait postinstall skipifsilent shellexec

; ============================================================================
; [UninstallDelete]
; ============================================================================
[UninstallDelete]
Type: filesandordirs; Name: "{app}\modulos\__pycache__"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\modulos\*.pyc"
Type: files; Name: "{app}\*.pyc"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\demo_state.json"
Type: dirifempty; Name: "{app}\reportes"
; En demo, la BD se puede eliminar (no tiene datos reales)
Type: files; Name: "{app}\ANgesLAB_Demo.accdb"

; ============================================================================
; [Registry]
; ============================================================================
[Registry]
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; ============================================================================
; [Code] - Pascal Script
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

procedure SetProgressMessage(Msg: String);
begin
  WizardForm.StatusLabel.Caption := Msg;
end;

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

  if Exec('cmd.exe', '/c python --version > "%TEMP%\python_ver.txt" 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      if Exec('cmd.exe', '/c where pythonw.exe > "%TEMP%\pythonw_path.txt" 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        if LoadStringFromFile(ExpandConstant('{tmp}\pythonw_path.txt'), VersionOutput) then
        begin
          PythonPath := Trim(String(VersionOutput));
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

  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.14\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then begin Result := True; Exit; end;
  end;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.13\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then begin Result := True; Exit; end;
  end;
  if RegQueryStringValue(HKLM, 'Software\Python\PythonCore\3.12\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then begin Result := True; Exit; end;
  end;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.14\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then begin Result := True; Exit; end;
  end;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.13\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then begin Result := True; Exit; end;
  end;
  if RegQueryStringValue(HKCU, 'Software\Python\PythonCore\3.12\InstallPath', '', PythonExe) then
  begin
    PythonPath := PythonExe + 'pythonw.exe';
    if FileExists(PythonPath) then begin Result := True; Exit; end;
  end;
end;

function DetectOLEDB(): Boolean;
begin
  Result := False;
  if RegKeyExists(HKLM, 'SOFTWARE\Classes\Microsoft.ACE.OLEDB.12.0') then
  begin Result := True; Exit; end;
  if RegKeyExists(HKLM, 'SOFTWARE\Classes\Microsoft.ACE.OLEDB.16.0') then
  begin Result := True; Exit; end;
end;

function GetPythonwPath(Param: String): String;
begin
  if PythonPath <> '' then
    Result := PythonPath
  else
    Result := 'pythonw.exe';
end;

procedure CreateRequirementsPage();
var
  TitleLabel: TNewStaticText;
  SeparatorLabel: TNewStaticText;
  ReqLabel: TNewStaticText;
  YPos: Integer;
begin
  RequirementsPage := CreateCustomPage(wpWelcome,
    'Verificacion de Requisitos del Sistema',
    'El instalador verificara que su equipo cumple con los requisitos minimos');

  YPos := 8;

  TitleLabel := TNewStaticText.Create(RequirementsPage);
  TitleLabel.Parent := RequirementsPage.Surface;
  TitleLabel.Caption := 'ESTADO DE REQUISITOS DEL SISTEMA';
  TitleLabel.Font.Style := [fsBold];
  TitleLabel.Font.Size := 10;
  TitleLabel.Left := 0;
  TitleLabel.Top := YPos;
  YPos := YPos + 30;

  SeparatorLabel := TNewStaticText.Create(RequirementsPage);
  SeparatorLabel.Parent := RequirementsPage.Surface;
  SeparatorLabel.Caption := '________________________________________________________________';
  SeparatorLabel.Font.Color := clGray;
  SeparatorLabel.Left := 0;
  SeparatorLabel.Top := YPos;
  YPos := YPos + 28;

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
    OLEDBStatusLabel.Font.Color := $000080FF;
  end;
  YPos := YPos + 26;

  SeparatorLabel := TNewStaticText.Create(RequirementsPage);
  SeparatorLabel.Parent := RequirementsPage.Surface;
  SeparatorLabel.Caption := '________________________________________________________________';
  SeparatorLabel.Font.Color := clGray;
  SeparatorLabel.Left := 0;
  SeparatorLabel.Top := YPos;
  YPos := YPos + 28;

  SystemStatusLabel := TNewStaticText.Create(RequirementsPage);
  SystemStatusLabel.Parent := RequirementsPage.Surface;
  SystemStatusLabel.Left := 0;
  SystemStatusLabel.Top := YPos;
  SystemStatusLabel.Font.Size := 9;
  SystemStatusLabel.Font.Style := [fsBold];
  SystemStatusLabel.AutoSize := True;
  if PythonFound then
  begin
    SystemStatusLabel.Caption := '  Su sistema cumple con los requisitos. Puede continuar.';
    SystemStatusLabel.Font.Color := clGreen;
  end
  else
  begin
    SystemStatusLabel.Caption := '  ATENCION: Instale Python antes de continuar.';
    SystemStatusLabel.Font.Color := clRed;
  end;
  YPos := YPos + 40;

  ReqLabel := TNewStaticText.Create(RequirementsPage);
  ReqLabel.Parent := RequirementsPage.Surface;
  ReqLabel.Left := 0;
  ReqLabel.Top := YPos;
  ReqLabel.Font.Size := 9;
  ReqLabel.AutoSize := True;
  ReqLabel.Caption :=
    'REQUISITOS MINIMOS:' + #13#10 +
    '  - Windows 10/11 (64-bit)' + #13#10 +
    '  - Python 3.8+ (python.org)' + #13#10 +
    '  - Microsoft Access Database Engine 2016' + #13#10 +
    '  - 100 MB de espacio libre' + #13#10 +
    '  - Conexion a internet (para dependencias)';
end;

function InitializeSetup(): Boolean;
begin
  PythonFound := DetectPython();
  OLEDBFound := DetectOLEDB();

  if not PythonFound then
  begin
    if MsgBox(
      'ANgesLAB DEMO requiere Python 3.8 o superior.' + #13#10 +
      #13#10 +
      'Python NO fue detectado en su sistema.' + #13#10 +
      'Descargue desde: python.org/downloads' + #13#10 +
      #13#10 +
      'IMPORTANTE: Marque "Add Python to PATH" al instalar.' + #13#10 +
      #13#10 +
      'Desea continuar de todas formas?',
      mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;

  Result := True;
end;

procedure InitializeWizard();
begin
  CreateRequirementsPage();
  WizardForm.WelcomeLabel1.Font.Size := 12;
  WizardForm.WelcomeLabel1.Font.Color := $00993300;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = RequirementsPage.ID then
  begin
    if not PythonFound then
    begin
      if MsgBox(
        'Python no fue detectado.' + #13#10 +
        'ANgesLAB no podra ejecutarse sin Python.' + #13#10 +
        #13#10 +
        'Desea continuar?',
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
        'Descargue desde:' + #13#10 +
        'microsoft.com/download/details.aspx?id=54920' + #13#10 +
        #13#10 +
        'Puede instalarlo despues.',
        mbInformation, MB_OK);
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption :=
      'ANgesLAB DEMO se ha instalado correctamente.' + #13#10 +
      #13#10 +
      'El demo inicia automaticamente sin pedir credenciales.' + #13#10 +
      'Incluye datos de ejemplo pre-cargados.' + #13#10 +
      #13#10 +
      'LIMITACIONES DE LA VERSION DEMO:' + #13#10 +
      '  - Maximo 5 pacientes nuevos' + #13#10 +
      '  - Maximo 10 solicitudes nuevas' + #13#10 +
      '  - Expira en 15 dias' + #13#10 +
      '  - Marca de agua en PDFs' + #13#10 +
      #13#10 +
      'Para la licencia completa:' + #13#10 +
      '  Tel: +574147204006' + #13#10 +
      '  Email: diabel92@hotmail.com' + #13#10 +
      #13#10 +
      'Haga clic en Finalizar para cerrar el asistente.';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    SaveStringToFile(ExpandConstant('{app}\install.log'),
      'ANgesLAB DEMO v' + '{#MyAppVersion}' + ' instalado.' + #13#10 +
      'Fecha: ' + GetDateTimeString('yyyy/mm/dd hh:nn:ss', '-', ':') + #13#10 +
      'Directorio: ' + ExpandConstant('{app}') + #13#10,
      False);
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := MsgBox(
    'Desea desinstalar ANgesLAB DEMO?' + #13#10 +
    #13#10 +
    'Se eliminaran todos los archivos de la demo.',
    mbConfirmation, MB_YESNO) = IDYES;
end;
