$pythonScript = "scripts/auditoria_todos_leiloeiros.py"
$args = "--modo", "rapido"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = "$pythonScript $($args -join ' ')"
$psi.WorkingDirectory = $PWD
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

$outputFile = "logs\auditoria_completa\auditoria_background_output.txt"
$errorFile = "logs\auditoria_completa\auditoria_background_error.txt"

Register-ObjectEvent -InputObject $process -EventName OutputDataReceived -Action {
    param($sender, $e)
    if ($e.Data) {
        Add-Content -Path $outputFile -Value $e.Data
    }
}

Register-ObjectEvent -InputObject $process -EventName ErrorDataReceived -Action {
    param($sender, $e)
    if ($e.Data) {
        Add-Content -Path $errorFile -Value $e.Data
    }
}

$process.Start() | Out-Null
$process.BeginOutputReadLine()
$process.BeginErrorReadLine()

Write-Output "Audit started in background with PID: $($process.Id)"
Write-Output "Output log: $outputFile"
Write-Output "Error log: $errorFile"
Write-Output "Main log: logs\auditoria_completa\auditoria_*.log"
Write-Output ""
Write-Output "The audit will run for approximately 2-4 hours."
Write-Output "Check progress with: type logs\auditoria_completa\progresso_*.json"
