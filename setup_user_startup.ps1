$StartupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = Join-Path -Path $StartupDir -ChildPath "AIJobAgent.lnk"
$TargetFile = Join-Path -Path $PSScriptRoot -ChildPath "launch_silent_background.vbs"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$TargetFile`""
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.WindowStyle = 7 # Minimized / Silent
$Shortcut.Description = "AI Job Application Agent Silent Background Runner"
$Shortcut.Save()

Write-Host "✅ Created Windows User Startup Shortcut at: $ShortcutPath" -ForegroundColor Green
Write-Host "The agent will now automatically start in the background when you sign in!" -ForegroundColor Cyan
