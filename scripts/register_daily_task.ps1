$script = Join-Path $PSScriptRoot "daily_update.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 07:30
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At 07:30 -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Hours 16)).Repetition
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "MatchLens Daily Update" -Action $action -Trigger $trigger -Settings $settings -Description "MatchLens daily ESPN update, odds twins pool, prediction log and settlement. Retries hourly until the day's update succeeds." -Force | Out-Null
Get-ScheduledTask -TaskName "MatchLens Daily Update" | Select-Object TaskName, State
