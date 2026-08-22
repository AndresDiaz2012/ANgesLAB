' ============================================================
' ANgesLAB v2.0 - Lanzador silencioso (sin ventana de consola)
' Copyright (c) 2024-2026 ANgesLAB Solutions
' ============================================================
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "pythonw ANgesLAB.pyw", 0, False
