param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
$portalRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $PythonPath) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $PythonPath = $pythonCommand.Source }
    else {
        $launcher = Get-Command py -ErrorAction Stop
        $PythonPath = & $launcher.Source -3 -c 'import sys; print(sys.executable)'
    }
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'Supply the full Python executable path using -PythonPath.' }
$portalScript = Join-Path $portalRoot 'server.py'
$taskAction = New-ScheduledTaskAction -Execute $PythonPath -Argument ('"' + $portalScript + '" --run-once') -WorkingDirectory $portalRoot
$taskTrigger = New-ScheduledTaskTrigger -Daily -At '09:00'
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Department Academic MIS Daily Check' -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Description 'Generate weekly faculty tasks and the previous month MIS report on or after the 2nd. Local files only.' -Force | Select-Object TaskName,State
