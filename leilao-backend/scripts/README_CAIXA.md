# 📋 Guia de Uso: Sincronização Caixa Econômica Federal

## 🎯 Visão Geral

Este sistema permite sincronizar imóveis da Caixa Econômica Federal de duas formas:

1. **Download Manual** (recomendado): Baixa CSVs via script bash que funciona melhor
2. **Sync Automático**: Processa os CSVs baixados e sincroniza com o banco

---

## 📥 Método 1: Download Manual + Sync Local

### Passo 1: Baixar CSVs Manualmente

Execute o script bash para baixar todos os 27 estados:

```bash
cd leilao-aggregator-git/leilao-backend
bash scripts/download_caixa_manual.sh
```

**O que o script faz:**
- Baixa CSVs de todos os 27 estados (AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO)
- Salva em `data/caixa/Lista_imoveis_{UF}.csv`
- Delay de 5 segundos entre cada download
- Mostra progresso e estatísticas

**Tempo estimado:** ~2-3 minutos (27 estados × 5 segundos)

### Passo 2: Sincronizar com Banco

Após baixar os CSVs, sincronize com o banco:

```bash
# Modo dry-run (teste sem salvar)
python scripts/sync_caixa.py --dry-run --local data/caixa

# Sincronização real
python scripts/sync_caixa.py --local data/caixa
```

---

## 🔄 Método 2: Download Automático (pode ser bloqueado)

Se preferir tentar download automático:

```bash
# Modo dry-run
python scripts/sync_caixa.py --dry-run

# Sincronização real
python scripts/sync_caixa.py
```

**⚠️ Nota:** O site da Caixa pode bloquear requisições automáticas. Se isso acontecer, use o Método 1.

---

## 📊 Opções do Script

### `sync_caixa.py`

```bash
python scripts/sync_caixa.py [opções]
```

**Opções:**
- `--dry-run`: Apenas parsear CSV, não salvar no banco (útil para testes)
- `--local DIR`: Ler CSVs locais do diretório especificado (ex: `data/caixa`)

**Exemplos:**
```bash
# Testar parsing com CSVs locais
python scripts/sync_caixa.py --dry-run --local data/caixa

# Sincronizar com CSVs locais
python scripts/sync_caixa.py --local data/caixa

# Tentar download automático (pode falhar)
python scripts/sync_caixa.py --dry-run
```

---

## 📁 Estrutura de Arquivos

```
leilao-aggregator-git/leilao-backend/
├── scripts/
│   ├── sync_caixa.py              # Script principal de sincronização
│   ├── download_caixa_manual.sh   # Script bash para download manual
│   └── README_CAIXA.md            # Este arquivo
└── data/
    └── caixa/
        ├── Lista_imoveis_AC.csv
        ├── Lista_imoveis_AL.csv
        ├── ...
        └── Lista_imoveis_TO.csv
```

---

## 🔍 Verificação de Resultados

Após sincronização, verifique no banco:

```sql
-- Contar imóveis da Caixa
SELECT COUNT(*) FROM properties WHERE auctioneer_id = 'caixa_federal';

-- Ver distribuição por estado
SELECT state, COUNT(*) as total 
FROM properties 
WHERE auctioneer_id = 'caixa_federal'
GROUP BY state 
ORDER BY total DESC;

-- Verificar leiloeiro
SELECT * FROM auctioneers WHERE id = 'caixa_federal';
```

---

## ⚠️ Troubleshooting

### Problema: Download bloqueado

**Solução:** Use o script bash `download_caixa_manual.sh` que funciona melhor com curl.

### Problema: CSVs não encontrados

**Solução:** Verifique se os arquivos estão em `data/caixa/` e se têm o formato `Lista_imoveis_{UF}.csv`.

### Problema: Parsing falha

**Solução:** Verifique se os CSVs estão em encoding latin-1 e têm delimitador `;` (ponto e vírgula).

---

## 🚀 Workflow Recomendado

1. **Download manual** (1x por dia ou quando necessário):
   ```bash
   bash scripts/download_caixa_manual.sh
   ```

2. **Sincronizar com banco** (via GitHub Actions ou manualmente):
   ```bash
   python scripts/sync_caixa.py --local data/caixa
   ```

3. **Verificar resultados** no Supabase

---

## 📝 Notas Técnicas

- **Encoding:** latin-1 (ISO-8859-1)
- **Delimitador:** `;` (ponto e vírgula)
- **Formato:** CSV com cabeçalho na linha 3
- **Estados:** 27 estados brasileiros
- **Volume esperado:** ~25.000-30.000 imóveis

---

**Última atualização:** 09/01/2026

