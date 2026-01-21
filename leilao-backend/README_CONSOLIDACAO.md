# 📊 SISTEMA DE CONSOLIDAÇÃO E PERSISTÊNCIA

## 🎯 VISÃO GERAL

Sistema completo para descobrir paths, extrair imóveis e persistir no Supabase.

### FLUXO COMPLETO:

```
1. Descoberta de Paths    → 2. Extração Inteligente    → 3. Consolidação e Persistência
   (descobrir_paths_massivo.py)  (extrator_paths_descobertos.py)  (consolidar_e_persistir_lote2.py)
   
   Analisa HTML real            HTTP → Playwright              Deduplica → Normaliza → Supabase
   87.7% sucesso                56% sucesso                    Upsert inteligente
```

---

## 📁 SCRIPTS DISPONÍVEIS

### 1️⃣ **Descoberta de Paths** (Completado ✅)

**Script:** `scripts/descobrir_paths_massivo.py`

**O que faz:**
- Analisa 261 sites de leiloeiros
- Usa 3 métodos inteligentes:
  1. Testa paths conhecidos (`/imoveis`, `/busca`, etc)
  2. Analisa menu de navegação
  3. Procura botões de catálogo
- Gera checkpoints a cada 10 sites
- Salva paths descobertos em JSON

**Resultado:**
- ✅ 229 paths descobertos (87.7%)
- ⏱️ Duração: ~1h30m
- 📄 `logs/descoberta_paths/paths_descobertos_20260120_204941.json`

---

### 2️⃣ **Extração Inteligente** (Em andamento 🔄)

**Script:** `scripts/extrator_paths_descobertos.py`

**O que faz:**
- Carrega paths descobertos do checkpoint mais recente
- Tenta HTTP primeiro (rápido)
- Fallback para Playwright se necessário
- Extrai URLs de imóveis
- Salva resultados em JSON

**Execução:**
```bash
cd c:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts\extrator_paths_descobertos.py
```

**Resultado Esperado:**
- 228 sites sendo processados
- ~5,000-10,000 imóveis estimados
- ⏱️ Duração: 2-3 horas

---

### 3️⃣ **Consolidação e Persistência** (Pronto para uso ✅)

**Script:** `scripts/consolidar_e_persistir_lote2.py`

**O que faz:**
1. **Carrega** todos os arquivos de extração
2. **Normaliza** dados (Title Case, categorias, etc)
3. **Deduplica** por URL
4. **Une** com imóveis já existentes no Supabase
5. **Insere** via UPSERT (sem duplicatas)
6. **Relatório** completo de estatísticas

**Execução:**
```bash
cd c:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts\consolidar_e_persistir_lote2.py
```

**Credenciais Supabase:**
```
DATABASE_URL=postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

---

### 4️⃣ **Teste Rápido** (Opcional)

**Script:** `scripts/testar_consolidacao.py`

**O que faz:**
- Valida arquivos de extração
- Mostra estatísticas sem inserir no banco
- Lista top 10 sites

**Execução:**
```bash
python scripts\testar_consolidacao.py
```

---

## 🚀 COMO USAR (PASSO A PASSO)

### **SITUAÇÃO ATUAL:**

✅ **Passo 1 - Descoberta:** COMPLETADO
- 229 paths descobertos
- Arquivo: `logs/descoberta_paths/paths_descobertos_20260120_204941.json`

🔄 **Passo 2 - Extração:** EM ANDAMENTO
- Terminal: 518855
- 228 sites sendo processados
- ⏱️ ~2-3 horas restantes

⏳ **Passo 3 - Consolidação:** AGUARDANDO

---

### **QUANDO A EXTRAÇÃO TERMINAR:**

1. **Verificar resultados da extração:**
   ```bash
   python scripts\testar_consolidacao.py
   ```

2. **Consolidar e persistir no Supabase:**
   ```bash
   python scripts\consolidar_e_persistir_lote2.py
   ```

3. **Confirmar inserção quando solicitado:**
   ```
   ⚠️ Confirma inserção de X novos imóveis no Supabase? (s/n): s
   ```

---

## 📊 ESTATÍSTICAS ESPERADAS

### Lote 1 (Completado):
- Sites: 16
- Imóveis: 398
- Taxa de sucesso: 56.2%

### Lote 2 (Em andamento):
- Sites: 228
- Imóveis estimados: ~5,000-10,000
- Taxa de sucesso esperada: ~50-60%

### **TOTAL ESPERADO:**
- ✅ ~140-150 sites com sucesso
- ✅ ~5,500-10,500 imóveis extraídos
- ✅ Crescimento do banco: +400-800% (de 1,472 para ~7,000-12,000)

---

## 📁 ARQUIVOS GERADOS

### Descoberta:
- `logs/descoberta_paths/paths_descobertos_20260120_204941.json` (final)
- `logs/descoberta_paths/checkpoint_X.json` (26 checkpoints)

### Extração:
- `logs/extracao_paths_descobertos/extracao_YYYYMMDD_HHMMSS.json`

### Consolidação:
- Script cria relatório em tempo real
- Insere diretamente no Supabase

---

## 🔧 SOLUÇÃO DE PROBLEMAS

### Erro de conexão ao Supabase:
```bash
# Testar conexão:
python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres'); print('OK')"
```

### Extração travada:
- Verificar terminal: `C:\Users\renat\.cursor\projects\c-LeiloHub\terminals\518855.txt`
- Monitorar logs: `logs/extracao_paths_descobertos/`

### Duplicatas:
- Script automaticamente deduplica por URL
- Usa UPSERT (ON CONFLICT DO UPDATE)

---

## 🎯 PRÓXIMOS PASSOS

Após consolidação e persistência:

1. **Validar no Supabase:**
   - Acessar dashboard
   - Verificar contagem de properties
   - Conferir auctioneers atualizados

2. **Atualizar status dos leiloeiros:**
   ```sql
   UPDATE auctioneers 
   SET scrape_status = 'success', 
       property_count = (SELECT COUNT(*) FROM properties WHERE auctioneer = auctioneers.website),
       last_scrape = NOW()
   WHERE website IN (SELECT DISTINCT auctioneer FROM properties);
   ```

3. **Gerar relatório final:**
   - Total de imóveis
   - Cobertura de leiloeiros
   - Top leiloeiros por volume

---

## ✅ CHECKLIST DE EXECUÇÃO

- [x] Descoberta de paths (229/261 sites)
- [x] Extração Lote 1 (16 sites - 398 imóveis)
- [ ] Extração Lote 2 (228 sites - em andamento)
- [ ] Consolidação e persistência
- [ ] Validação no Supabase
- [ ] Atualização de status dos leiloeiros
- [ ] Relatório final

---

**Data:** 20/01/2026  
**Status:** Sistema preparado e aguardando conclusão da extração massiva
