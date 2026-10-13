# Optional: keep the monitor running while nobody is logged on.
#
# The scheduled task normally runs only inside your interactive session, so it
# pauses while you are logged off or while the PC sits at the login screen.
# This script switches the task to "run whether the user is logged on or not",
# without storing your password (S4U). The 3-hourly checks then continue right
# after a reboot, before you log in.
#
# Administrator rights are required, because Windows keeps task credentials
# outside the per-user scope. The schedule itself does not change: the next run
# stays on the existing 3-hour grid and no extra check is triggered.

$ErrorActionPreference = 'Stop'

$taskName = 'GitHubActivityEmailQQ'

$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Please run this script as Administrator (right-click -> Run as administrator), or use enable_run_when_logged_off.bat.'
}

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    throw "Scheduled task $taskName was not found. Run install_windows_task.bat first."
}

# Keep a copy of the current definition so the change can be undone.
$backup = Join-Path $PSScriptRoot 'data\task-backup.xml'
$backupDir = Split-Path -Parent $backup
if (-not (Test-Path -LiteralPath $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }
Export-ScheduledTask -TaskName $taskName | Set-Content -LiteralPath $backup -Encoding Unicode
Write-Host "Backed up the current task to $backup"

# Keep the existing grid: start at the next scheduled time, so that registering
# the task does not fire an extra check right now.
$startAt = (Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
if (-not $startAt -or $startAt -le (Get-Date)) { $startAt = (Get-Date).AddMinutes(5) }

$principal = New-ScheduledTaskPrincipal -UserId ('{0}\{1}' -f $env:USERDOMAIN, $env:USERNAME) -LogonType S4U -RunLevel Limited

$trigger = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval (New-TimeSpan -Hours 3)

Register-ScheduledTask -TaskName $taskName -Action $task.Actions -Trigger $trigger -Settings $task.Settings -Principal $principal -Description $task.Description -Force | Out-Null

$newTask = Get-ScheduledTask -TaskName $taskName
$newInfo = Get-ScheduledTaskInfo -TaskName $taskName

Write-Host ''
Write-Host 'Done. The monitor now also runs while you are logged off.' -ForegroundColor Green
Write-Host ('  Logon type: {0}' -f $newTask.Principal.LogonType)
Write-Host ('  Runs:       {0} {1}' -f $newTask.Actions[0].Execute, $newTask.Actions[0].Arguments)
Write-Host ('  Next run:   {0}' -f $newInfo.NextRunTime)
Write-Host ''
Write-Host 'To undo this, run install_windows_task.bat again (as Administrator if Windows asks).'
Write-Host ('The previous definition is also kept at {0}' -f $backup)
