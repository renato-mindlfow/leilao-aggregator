#!/bin/bash
# download_caixa_manual.sh
# Executar manualmente quando necessário para baixar CSVs da Caixa

ESTADOS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO"
OUTPUT_DIR="data/caixa"
mkdir -p $OUTPUT_DIR

echo "=========================================="
echo "Download Manual - CSVs da Caixa"
echo "=========================================="
echo ""

for UF in $ESTADOS; do
    echo "Baixando $UF..."
    curl -L -o "$OUTPUT_DIR/Lista_imoveis_$UF.csv" \
        "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_$UF.csv" \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
        -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
        --silent --show-error
    
    if [ -f "$OUTPUT_DIR/Lista_imoveis_$UF.csv" ]; then
        LINES=$(wc -l < "$OUTPUT_DIR/Lista_imoveis_$UF.csv" 2>/dev/null || echo "0")
        SIZE=$(du -h "$OUTPUT_DIR/Lista_imoveis_$UF.csv" | cut -f1)
        echo "  ✓ $UF: $LINES linhas ($SIZE)"
    else
        echo "  ✗ $UF: falhou"
    fi
    
    # Delay de 5 segundos entre downloads
    if [ "$UF" != "TO" ]; then
        sleep 5
    fi
done

echo ""
echo "=========================================="
echo "Download completo. Arquivos em $OUTPUT_DIR/"
echo "=========================================="
ls -lh $OUTPUT_DIR/ | grep -v "^total"

