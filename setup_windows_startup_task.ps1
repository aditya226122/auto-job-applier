# PowerShell Script to register Auto Job Applier to run silently on Windows Startup
$TaskName = "AIJobApplicationAgent"
$ScriptPath = "$PSScriptRoot\launch_silent_background.vbs"

Write-Host "Registering Windows Background Task for AI Job Agent..." -ForegroundColor Cyan

# Action
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$ScriptPath`""

# Trigger on User Logon
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Register or update task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs AI Job Application Agent in background" -Force

Write-Host "✅ Successfully registered background task: $TaskName" -ForegroundColor Green
Write-Host "The agent will now run silently in the background whenever Windows starts up!" -ForegroundColor Yellow
