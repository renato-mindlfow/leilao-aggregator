# Check audit progress
$progressDir = "logs\auditoria_completa"

Write-Output "=== AUDIT PROGRESS CHECK ==="
Write-Output ""

# Find latest progress file
$progressFiles = Get-ChildItem "$progressDir\progresso_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if ($progressFiles) {
    $latest = $progressFiles[0]
    Write-Output "Latest progress file: $($latest.Name)"
    Write-Output "Last modified: $($latest.LastWriteTime)"
    
    try {
        $data = Get-Content $latest.FullName -Raw | ConvertFrom-Json
        Write-Output "Processed: $($data.processados) / $($data.total)"
        $percent = [math]::Round(($data.processados / $data.total) * 100, 1)
        Write-Output "Progress: $percent%"
    } catch {
        Write-Output "Could not parse progress file"
    }
    Write-Output ""
}

# Count screenshots
$screenshots = Get-ChildItem "$progressDir\screenshots\*.png" -ErrorAction SilentlyContinue
if ($screenshots) {
    Write-Output "Screenshots generated: $($screenshots.Count)"
}

# Latest log file
$logs = Get-ChildItem "$progressDir\auditoria_*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if ($logs) {
    $latestLog = $logs[0]
    Write-Output ""
    Write-Output "Latest log: $($latestLog.Name)"
    Write-Output "Last modified: $($latestLog.LastWriteTime)"
    Write-Output ""
    Write-Output "Last 10 lines:"
    Get-Content $latestLog.FullName -Tail 10 -ErrorAction SilentlyContinue
}

Write-Output ""
Write-Output "=== END OF PROGRESS CHECK ==="
