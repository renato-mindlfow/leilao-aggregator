# download_caixa_manual.ps1
# Executar manualmente quando necessario para baixar CSVs da Caixa

$ESTADOS = @("AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO")
$OUTPUT_DIR = "data/caixa"

# Criar diretorio se nao existir
if (-not (Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Path $OUTPUT_DIR | Out-Null
}

Write-Host "=========================================="
Write-Host "Download Manual - CSVs da Caixa"
Write-Host "=========================================="
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($UF in $ESTADOS) {
    Write-Host "Baixando $UF..."
    
    $url = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_$UF.csv"
    $outputFile = "$OUTPUT_DIR/Lista_imoveis_$UF.csv"
    
    try {
        $headers = @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        Invoke-WebRequest -Uri $url -OutFile $outputFile -Headers $headers -UseBasicParsing -ErrorAction Stop
        
        if (Test-Path $outputFile) {
            $fileInfo = Get-Item $outputFile
            $lineCount = (Get-Content $outputFile | Measure-Object -Line).Lines
            $sizeKB = [math]::Round($fileInfo.Length / 1KB, 2)
            Write-Host "  OK $UF : $lineCount linhas ($sizeKB KB)" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  ERRO $UF : falhou" -ForegroundColor Red
            $failCount++
        }
    } catch {
        Write-Host "  ERRO $UF : falhou - $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
    
    # Delay de 5 segundos entre downloads (exceto o ultimo)
    if ($UF -ne "TO") {
        Start-Sleep -Seconds 5
    }
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Download completo!"
Write-Host "  Sucesso: $successCount"
Write-Host "  Falhas: $failCount"
Write-Host "=========================================="
