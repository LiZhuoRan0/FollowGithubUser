' Keeps checking GitHub every 3 hours with no window at all.
'
' This is the silent version of run_monitor_loop.bat, and an alternative to
' the Windows scheduled task. Nothing is shown on screen, so stop it again
' with stop_hidden_monitor.bat when you want it gone.

Option Explicit

Dim fso, shell, here, pythonwPath, scriptPath, commandText

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = fso.BuildPath(here, ".venv\Scripts\pythonw.exe")
scriptPath = fso.BuildPath(here, "github_activity_email.py")

If Not fso.FileExists(pythonwPath) Then
  MsgBox "Cannot find .venv\Scripts\pythonw.exe." & vbCrLf & _
         "Run setup_venv.bat first.", 16, "GitHub Activity Monitor"
  WScript.Quit 1
End If

shell.CurrentDirectory = here
commandText = Quote(pythonwPath) & " " & Quote(scriptPath)

Do
  ' 0 = hidden window, True = wait until this check finishes.
  shell.Run commandText, 0, True
  ' Wait 3 hours before the next check.
  WScript.Sleep 3 * 60 * 60 * 1000
Loop

Function Quote(textValue)
  Quote = """" & textValue & """"
End Function
