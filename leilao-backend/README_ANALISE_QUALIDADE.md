# 📊 GUIA DE ANÁLISE DE QUALIDADE E GEOCODING

## 🎯 VISÃO GERAL

Scripts para análise de qualidade, geocoding e dashboard após a consolidação dos dados.

**Executar APÓS:** `consolidar_e_persistir_lote2.py`

---

## 📁 SCRIPTS DISPONÍVEIS

### 1️⃣ **analisar_qualidade_dados.py** ✅
**Propósito:** Análise completa da qualidade dos dados no Supabase

**O que faz:**
1. ✅ Analisa campos obrigatórios (título, URL, estado, preço, etc)
2. ✅ Verifica qualidade de localização (estado, cidade, geocoding)
3. ✅ Analisa preços (estatísticas, suspeitos, outliers)
4. ✅ Calcula score de qualidade por leiloeiro
5. ✅ Detecta duplicatas
6. ✅ Mostra imóveis recentes (24h, 7 dias)
7. ✅ Gera recomendações de melhoria

**Execução:**
```bash
cd c:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts\analisar_qualidade_dados.py
```

**Saída:**
```
======================================================================
ANALISE DE QUALIDADE DOS DADOS - LEILOHUB
======================================================================

1. ANALISE DE CAMPOS OBRIGATORIOS
   Campo                  | Preenchidos | Vazios | % Qualidade
   ----------------------------------------------------------------------
   Titulo                 |       9,856 |    144 |   98.6%
   URL                    |      10,000 |      0 |  100.0%
   Estado (UF)            |       7,234 |  2,766 |   72.3%
   ...
   SCORE GERAL DE QUALIDADE: 78.5%

2. ANALISE DE LOCALIZACAO
   Imoveis sem Estado:     2,766 (27.7%)
   Imoveis sem Cidade:     3,123 (31.2%)
   Imoveis sem Geocoding:  8,945 (89.4%)
   
   DISTRIBUICAO POR ESTADO (Top 10):
   SP: 3,245 imoveis
   RJ: 1,567 imoveis
   ...

3. ANALISE DE PRECOS
   Imoveis com preco:       5,678 (56.8%)
   Imoveis sem preco:       4,322 (43.2%)
   
   ESTATISTICAS DE PRECO:
   Media:    R$ 345,678.90
   Mediana:  R$ 250,000.00
   ...

4. SCORE DE QUALIDADE POR LEILOEIRO
   Leiloeiro                      | Total | Estado | Cidade | Preco | Score
   --------------------------------------------------------------------------------
   Caixa                          | 1,472 |  100% |  100% |  95% |  98%
   Leilaobrasil                   |   177 |   85% |   80% |  70% |  78%
   ...

7. RECOMENDACOES DE MELHORIA
   1. LOCALIZACAO: 2,766 imoveis sem estado
      Acao: Melhorar extracao de localizacao dos scrapers
   
   2. GEOCODING: 8,945 imoveis sem coordenadas (89.4%)
      Acao: Executar script de geocoding em lote
```

---

### 2️⃣ **preparar_geocoding.py** ✅
**Propósito:** Prepara batches para geocoding em lote

**O que faz:**
1. ✅ Lista imóveis sem latitude/longitude
2. ✅ Prioriza estados importantes (SP, RJ, MG, PR, RS, SC, BA, PE, CE, DF)
3. ✅ Cria batches JSON por estado (até 500 por estado)
4. ✅ Gera batch consolidado (top 1000 imóveis)
5. ✅ Cria script executável `executar_geocoding.py`

**Execução:**
```bash
python scripts\preparar_geocoding.py
```

**Saída:**
- `logs/geocoding/batch_SP_TIMESTAMP.json`
- `logs/geocoding/batch_RJ_TIMESTAMP.json`
- ...
- `logs/geocoding/batch_consolidado_TIMESTAMP.json`
- `logs/geocoding/executar_geocoding.py` (script gerado)

**Próximo passo:**
```bash
# Instalar dependência
pip install geopy

# Executar geocoding
python logs\geocoding\executar_geocoding.py
```

**⚠️ IMPORTANTE:**
- Nominatim tem limite de **1 requisição/segundo**
- Tempo estimado: ~15-20 minutos para 1000 imóveis
- Alternativas mais rápidas:
  - Google Maps API (paga)
  - HERE API (freemium)
  - OpenCage API (freemium)

---

### 3️⃣ **queries_dashboard.sql** ✅
**Propósito:** Queries SQL prontas para dashboard e analytics

**Categorias:**
1. **Visão Geral** - Total de imóveis, leiloeiros, novos hoje/semana
2. **Distribuição por Estado** - Top 10, completo com médias
3. **Distribuição por Categoria** - Tipos de imóvel, categorias
4. **Ranking de Leiloeiros** - Top 20 por volume, por qualidade
5. **Timeline** - Novos por dia (30 dias), por hora (24h)
6. **Análise de Preços** - Estatísticas, faixas, por estado
7. **Qualidade dos Dados** - Completude dos campos
8. **Imóveis Destacados** - Maior desconto, mais valiosos, recentes
9. **Busca e Filtros** - Por estado, cidade, faixa de preço
10. **Geocoding** - Status, priorização
11. **Views Úteis** - Resumos pré-calculados

**Uso:**

```sql
-- Conectar ao Supabase (pgAdmin, DBeaver, etc)
-- Copiar e executar queries conforme necessidade

-- Exemplo: Total por estado
SELECT 
    state as uf,
    COUNT(*) as total,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM properties) * 100, 1) as percentual
FROM properties
WHERE state IS NOT NULL AND state != ''
GROUP BY state
ORDER BY total DESC
LIMIT 10;
```

**Criar Views:**
```sql
-- Executar seção 11 do arquivo para criar views úteis
CREATE OR REPLACE VIEW vw_leiloeiros_resumo AS ...
CREATE OR REPLACE VIEW vw_estados_resumo AS ...
CREATE OR REPLACE VIEW vw_imoveis_recentes AS ...
```

---

## 🚀 FLUXO COMPLETO PÓS-CONSOLIDAÇÃO

### **PASSO 1: Consolidar Dados** ✅ (Já feito)
```bash
python scripts\consolidar_e_persistir_lote2.py
```

### **PASSO 2: Analisar Qualidade** 📊
```bash
python scripts\analisar_qualidade_dados.py
```

**Verificar:**
- Score geral de qualidade
- Campos faltantes
- Qualidade por leiloeiro
- Recomendações

### **PASSO 3: Preparar Geocoding** 🗺️
```bash
python scripts\preparar_geocoding.py
```

**Resultado:**
- Batches JSON gerados
- Script executável criado

### **PASSO 4: Executar Geocoding** 🌍
```bash
# Instalar dependência
pip install geopy

# Executar
python logs\geocoding\executar_geocoding.py
```

**Monitorar:**
- Progresso a cada 50 imóveis
- Taxa de sucesso
- Tempo estimado

### **PASSO 5: Validar Melhorias** ✅
```bash
# Rodar análise novamente
python scripts\analisar_qualidade_dados.py
```

**Comparar:**
- Score de qualidade antes/depois
- Quantidade de imóveis com geocoding
- Melhorias por leiloeiro

### **PASSO 6: Dashboard** 📈
```sql
-- Usar queries_dashboard.sql
-- Criar views no Supabase
-- Visualizar métricas
```

---

## 📊 MÉTRICAS ESPERADAS

### **Antes da Consolidação:**
- Total: 1,472 imóveis
- Leiloeiros: 28 ativos
- Qualidade: ~85-90%

### **Após Consolidação (Projetado):**
- Total: ~5,500-10,500 imóveis
- Leiloeiros: ~140-150 ativos
- Qualidade inicial: ~60-70% (muitos campos vazios)

### **Após Geocoding:**
- Imóveis com coordenadas: +1,000-2,000
- Melhoria de qualidade: +10-15%
- Score final esperado: ~75-85%

---

## 🔧 SOLUÇÃO DE PROBLEMAS

### **Erro de conexão ao Supabase:**
```bash
# Testar conexão
python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres.nawbptwbmdgrkbpbwxzl:LeilaoAggregator2025SecurePass@aws-1-sa-east-1.pooler.supabase.com:6543/postgres'); print('OK')"
```

### **Geocoding muito lento:**
**Problema:** Nominatim tem limite de 1 req/seg  
**Solução:**
1. Usar batch consolidado (top 1000)
2. Considerar API paga (Google Maps)
3. Processar em lotes menores

### **Score de qualidade baixo:**
**Causas comuns:**
- Scrapers não extraem localização
- Campos opcionais vazios
- URLs sem metadados

**Soluções:**
1. Melhorar scrapers existentes
2. Adicionar parsers de localização
3. Enriquecer dados com APIs externas

---

## 📁 ESTRUTURA DE ARQUIVOS

```
scripts/
├── analisar_qualidade_dados.py    ✅ Análise completa
├── preparar_geocoding.py           ✅ Preparação de batches
└── queries_dashboard.sql           ✅ Queries prontas

logs/
└── geocoding/
    ├── batch_SP_TIMESTAMP.json     (gerado)
    ├── batch_RJ_TIMESTAMP.json     (gerado)
    ├── batch_consolidado.json      (gerado)
    └── executar_geocoding.py       (gerado)
```

---

## 🎯 CHECKLIST PÓS-CONSOLIDAÇÃO

- [ ] Executar análise de qualidade
- [ ] Revisar score geral (deve ser >60%)
- [ ] Identificar leiloeiros com baixa qualidade
- [ ] Preparar batches de geocoding
- [ ] Executar geocoding prioritário (SP, RJ, MG)
- [ ] Validar melhorias
- [ ] Criar views no Supabase
- [ ] Configurar dashboard
- [ ] Monitorar métricas diárias

---

## 📈 PRÓXIMAS MELHORIAS

### **Curto Prazo:**
1. ✅ Geocoding automático em lote
2. ✅ Dashboard de métricas
3. ⏳ Parser de endereços melhorado
4. ⏳ Detecção de categoria automática

### **Médio Prazo:**
1. ⏳ Enriquecimento com APIs externas
2. ⏳ Validação de preços (outliers)
3. ⏳ Normalização de categorias
4. ⏳ Deduplicação avançada (fuzzy matching)

### **Longo Prazo:**
1. ⏳ Machine Learning para categorização
2. ⏳ Predição de descontos
3. ⏳ Alertas automáticos de oportunidades
4. ⏳ API pública de dados

---

**Preparado por:** AI Assistant  
**Data:** 20/01/2026  
**Versão:** 1.0
