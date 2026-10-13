' Runs github_activity_email.py once, completely hidden (no console window).
'
' The Windows scheduled task "GitHubActivityEmailQQ" calls this file through
' wscript.exe, so the 3-hourly check never flashes a window on screen.
'
' You can also run it by hand:
'   wscript.exe //B run_hidden.vbs --dry-run
' Extra arguments are passed straight to github_activity_email.py.

Option Explicit

Dim fso, shell, here, pythonwPath, scriptPath, extraArgs, i, commandText, exitCode

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = fso.BuildPath(here, ".venv\Scripts\pythonw.exe")
scriptPath = fso.BuildPath(here, "github_activity_email.py")

If Not fso.FileExists(pythonwPath) Then
  LogProblem "Cannot find .venv\Scripts\pythonw.exe. Run setup_venv.bat first."
  WScript.Quit 1
End If

If Not fso.FileExists(scriptPath) Then
  LogProblem "Cannot find github_activity_email.py next to this script."
  WScript.Quit 1
End If

extraArgs = ""
For i = 0 To WScript.Arguments.Count - 1
  extraArgs = extraArgs & " " & Quote(WScript.Arguments(i))
Next

shell.CurrentDirectory = here
commandText = Quote(pythonwPath) & " " & Quote(scriptPath) & extraArgs

' 0 = hidden window, True = wait until the monitor finishes.
On Error Resume Next
exitCode = shell.Run(commandText, 0, True)
If Err.Number <> 0 Then
  LogProblem "Failed to start the monitor: " & Err.Description
  WScript.Quit 1
End If
On Error GoTo 0

WScript.Quit exitCode

Function Quote(textValue)
  Quote = """" & textValue & """"
End Function

Sub LogProblem(messageText)
  Dim stream
  On Error Resume Next
  Set stream = fso.OpenTextFile(fso.BuildPath(here, "data\hidden_run.log"), 8, True)
  If Err.Number = 0 Then
    stream.WriteLine Now & " [launcher] " & messageText
    stream.Close
  End If
  On Error GoTo 0
End Sub
