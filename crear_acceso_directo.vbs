' ============================================================
' ANgesLAB v2.0 - Crear acceso directo en el escritorio
' Ejecutar una vez despues de la instalacion
' Copyright (c) 2024-2026 ANgesLAB Solutions
' ============================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Ruta del escritorio del usuario
strDesktop = WshShell.SpecialFolders("Desktop")

' Ruta de la carpeta donde esta este script
strAppDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Crear acceso directo
Set oShortcut = WshShell.CreateShortcut(strDesktop & "\ANgesLAB.lnk")
oShortcut.TargetPath = strAppDir & "\ANgesLAB.vbs"
oShortcut.WorkingDirectory = strAppDir
oShortcut.IconLocation = strAppDir & "\assets\angeslab_icon.ico, 0"
oShortcut.Description = "ANgesLAB - Sistema de Gestion de Laboratorio Clinico"
oShortcut.WindowStyle = 7
oShortcut.Save

MsgBox "Acceso directo creado en el escritorio." & vbCrLf & vbCrLf & _
       "Haga doble clic en 'ANgesLAB' para iniciar el sistema.", _
       vbInformation, "ANgesLAB v2.0"
