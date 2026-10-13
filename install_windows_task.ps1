# Registers the silent Windows scheduled task for the GitHub activity monitor.
#
# The task starts wscript.exe, which runs run_hidden.vbs, which runs
# pythonw.exe. None of those three can open a console window, so the
# 3-hourly check stays invisible while you work.

$ErrorActionPreference = 'Stop'

$taskName = 'GitHubActivityEmailQQ'
$intervalHours = 3
$projectDir = $PSScriptRoot
$launcherPath = Join-Path $projectDir 'run_hidden.vbs'
$wscriptPath = Join-Path $env:SystemRoot 'System32\wscript.exe'

if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "Cannot find $launcherPath"
}

if (-not (Test-Path -LiteralPath (Join-Path $projectDir '.venv\Scripts\pythonw.exe'))) {
    Write-Warning 'The virtual environment was not found. Run setup_venv.bat first.'
}

# Remove an older version of the task, for example the one created earlier by
# install_windows_task.bat that showed a console window on every run.
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute $wscriptPath `
    -Argument ('//B //Nologo "{0}"' -f $launcherPath) `
    -WorkingDirectory $projectDir

# Start in a minute, then repeat every 3 hours for as long as the task exists.
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Hours $intervalHours)

# IgnoreNew: never stack up two runs if one check takes unusually long.
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal `
    -UserId ('{0}\{1}' -f $env:USERDOMAIN, $env:USERNAME) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Checks a GitHub user public activity every 3 hours and emails new activity. Runs without any visible window.' `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $taskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName

Write-Host ''
Write-Host 'Scheduled task registered.' -ForegroundColor Green
Write-Host ('  Task name:  {0}' -f $task.TaskName)
Write-Host ('  Runs:       {0} {1}' -f $task.Actions[0].Execute, $task.Actions[0].Arguments)
Write-Host ('  Every:      {0} hours' -f $intervalHours)
Write-Host ('  Start in:   {0}' -f $projectDir)
Write-Host ('  Next run:   {0}' -f $taskInfo.NextRunTime)
Write-Host '  Window:     hidden (wscript.exe -> pythonw.exe)'
