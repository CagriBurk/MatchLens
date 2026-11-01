$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu -u main -- /home/main/projects/MatchLens/scripts/daily_update.sh"
$trigger = New-ScheduledTaskTrigger -Daily -At 07:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "MatchLens Daily Update" -Action $action -Trigger $trigger -Settings $settings -Description "MatchLens daily ESPN update, prediction log and settlement" -Force | Out-Null
Get-ScheduledTask -TaskName "MatchLens Daily Update" | Select-Object TaskName, State
