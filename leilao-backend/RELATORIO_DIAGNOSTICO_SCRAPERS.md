# RELATÓRIO DE DIAGNÓSTICO DOS SCRAPERS
**Data:** 2026-01-22  
**LeiloHub - Análise Completa do Estado Atual**

---

## 📊 RESUMO EXECUTIVO

### Status Geral dos Leiloeiros (Total: 501)

| Status | Quantidade | Percentual | Ação Necessária |
|--------|-----------|-----------|-----------------|
| ✅ **Success** | 24 | 5% | Manutenção |
| ❌ **Error** | 132 | 26% | **CORRIGIR URGENTE** |
| ⏳ **Pending** | 332 | 66% | **IMPLEMENTAR** |
| 🚫 **Disabled** | 10 | 2% | Avaliar reativação |
| 🎭 **Needs Playwright** | 3 | 0.6% | Implementar Playwright |

### Distribuição de Imóveis no Banco (Total: ~36.400)

| Rank | Leiloeiro | Imóveis | % Total | Status |
|------|-----------|---------|---------|--------|
| 1 | **Caixa Econômica Federal** | 32.547 | **89.4%** | ✅ Funcionando |
| 2 | Mega Leilões | 2.050 | 5.6% | ✅ Funcionando |
| 3 | Turani Leilões | 397 | 1.1% | ✅ Funcionando |
| 4 | Tri Leilões | 367 | 1.0% | ✅ Funcionando |
| 5 | Lance Judicial | 307 | 0.8% | ✅ Funcionando |
| 6 | Realiza Leilões | 123 | 0.3% | ✅ Funcionando |
| 7 | Lut Leilões | 114 | 0.3% | ✅ Funcionando |
| 8 | Sodré Santoro | 111 | 0.3% | ✅ Funcionando |
| 9-30 | Outros 22 leiloeiros | 684 | 1.9% | Vários status |

**🚨 PROBLEMA CRÍTICO: 89.4% dos imóveis vêm de UMA ÚNICA FONTE (Caixa)**

---

## 🐛 ANÁLISE DOS ERROS (132 scrapers com erro)

### Tipos de Erros Encontrados

| Erro | Quantidade | % Erros | Causa Provável | Solução |
|------|-----------|---------|----------------|---------|
| **"Nenhum imóvel encontrado"** | 122 | 92.4% | Site sem leilões ativos OU scraper quebrado | Verificar cada site manualmente |
| **Duplicate key violation** | 4 | 3.0% | IDs duplicados | Corrigir geração de IDs únicos |
| **"'NoneType' object"** | 2 | 1.5% | Parsing falhou | Adicionar validações |
| **"value too long (2 chars)"** | 1 | 0.8% | Estado com mais de 2 caracteres | Validar antes de salvar |
| **Erro nulo/desconhecido** | 3 | 2.3% | Diversos | Investigar logs |

### Leiloeiros com Erro Mais Relevantes

**Com imóveis anteriormente coletados (precisam correção):**
- Allianceleiloes (54 imóveis, erro: "Nenhum imóvel")
- Alexandridisleiloes (37 imóveis, erro: "Nenhum imóvel")

**Erros de duplicação de ID (bugs de código):**
- Correaleiloes: Duplicate key "Lote 1"
- Centraljudicial: Duplicate key "352"
- Marangonileiloes: Duplicate key "Lote 1"
- Lancenoleilao: Duplicate key "24090"

---

## ⏳ SCRAPERS PENDENTES (332 - 66% do total)

**Motivos para Status "Pending":**
1. Nunca foram implementados
2. Foram desabilitados manualmente
3. Sites novos adicionados recentemente
4. Sites que mudaram de estrutura

**Estratégia de Implementação:**
1. **Priorizar por tamanho** (leiloeiros grandes primeiro)
2. **Agrupar por tecnologia** (mesma plataforma = código similar)
3. **Focar em diversificação** (reduzir dependência da Caixa)

---

## 🎯 PLANO DE AÇÃO - PARTE 3, 4 E 5

### FASE 3: Corrigir Scrapers com Erro (132 scrapers)

#### 3.1 - Corrigir Erros de Código (ALTA PRIORIDADE)
**Tempo estimado: 2-4 horas**

1. **Duplicate Key Errors (4 scrapers):**
   - [ ] Correaleiloes - Corrigir geração de ID único
   - [ ] Centraljudicial - Corrigir geração de ID único
   - [ ] Marangonileiloes - Corrigir geração de ID único
   - [ ] Lancenoleilao - Corrigir geração de ID único
   
   **Solução:** Adicionar timestamp ou hash ao ID para garantir unicidade

2. **Parsing Errors (3 scrapers):**
   - [ ] Scraper com erro "'NoneType' object has no attribute 'replace'"
   - [ ] Scraper com erro "'NoneType' object is not subscriptable"
   - [ ] Scraper com erro "value too long for type character varying(2)"
   
   **Solução:** Adicionar validações e try-except nos parsers

#### 3.2 - Verificar "Nenhum Imóvel Encontrado" (122 scrapers)
**Tempo estimado: 10-15 horas**

**Estratégia:**
1. Criar script de verificação automática que acessa cada site
2. Classificar em:
   - **Sites offline/inativos** → Marcar como "disabled"
   - **Sites sem leilões no momento** → Manter "pending" e re-verificar periodicamente
   - **Scraper quebrado** → Corrigir seletores CSS/lógica

**Script de Verificação:**
```python
# Para cada leiloeiro com erro "Nenhum imóvel":
# 1. Acessar website
# 2. Verificar se site está online
# 3. Verificar se há leilões listados manualmente
# 4. Comparar com o que o scraper extrai
# 5. Classificar e atualizar status
```

#### 3.3 - Leiloeiros com Imóveis Anteriores (PRIORIDADE ALTA)

Estes scrapers JÁ extraíram dados antes, então sabemos que funcionavam:
- Allianceleiloes (54 imóveis históricos)
- Alexandridisleiloes (37 imóveis históricos)
- Vários outros na lista

**Ação:** Investigar por que pararam de funcionar (mudança de site, bloqueio, etc.)

---

### FASE 4: Implementar Scrapers Pendentes (332 scrapers)

#### 4.1 - Identificar Leiloeiros Grandes (TOP 50)
**Objetivo:** Maximizar número de imóveis com menos esforço

**Critérios de priorização:**
1. Sites com >100 imóveis listados
2. Sites de leiloeiros conhecidos nacionalmente
3. Sites com múltiplas filiais

#### 4.2 - Agrupar por Plataforma
Muitos leiloeiros usam as mesmas plataformas:
- **Superbid** → Código reutilizável
- **Lance Agora** → Código reutilizável
- **Hanzo** → Código reutilizável
- **Sites WordPress customizados** → Padrões similares

#### 4.3 - Criar Templates por Tipo
1. **Template Superbid** → Aplicar em todos os leiloeiros Superbid
2. **Template Lance Agora** → Aplicar em todos da plataforma
3. **Template Genérico WordPress**
4. **Template Site Estático**

---

### FASE 5: Garantir Paginação Completa

#### 5.1 - Verificar Paginação em Scrapers Existentes
**Problema:** Alguns scrapers podem estar pegando só a 1ª página

**Checklist para cada scraper:**
- [ ] Identifica número total de páginas?
- [ ] Loop de paginação implementado?
- [ ] Condição de parada correta?
- [ ] Limite de segurança (max 100 páginas)?

#### 5.2 - Testar Scrapers Grandes
Focar nos top 10 leiloeiros:
```bash
# Para cada leiloeiro top 10:
python -c "from app.scrapers.NOME_scraper import NOMEScraper; \
           s = NOMEScraper(); \
           props = s.scrape_properties(max_properties=None); \
           print(f'Total: {len(props)} imóveis')"
```

Compare com número mostrado no site do leiloeiro.

---

## 📈 METAS E MÉTRICAS DE SUCESSO

### Meta 1: Reduzir Dependência da Caixa
**Estado Atual:** 89.4% dos imóveis de 1 fonte  
**Meta:** <50% de uma única fonte  
**Como:** Implementar top 20 leiloeiros pendentes

### Meta 2: Taxa de Sucesso dos Scrapers
**Estado Atual:** 5% (24/501)  
**Meta Fase 1:** 20% (100/501) - Implementar top 76  
**Meta Fase 2:** 50% (250/501) - Implementar bulk dos pendentes  
**Meta Final:** 80% (400/501) - Sites ativos e funcionando

### Meta 3: Total de Imóveis Únicos
**Estado Atual:** ~36.400 imóveis  
**Meta Fase 1:** >50.000 imóveis (+38%)  
**Meta Fase 2:** >100.000 imóveis (+175%)  
**Meta Final:** >200.000 imóveis (cobertura nacional)

### Meta 4: Cobertura Geográfica
**Objetivo:** Imóveis em TODOS os 27 estados brasileiros  
**Prioridade:** Estados com poucos imóveis atualmente

---

## 🚀 PRÓXIMOS PASSOS IMEDIATOS

### Hoje (2-3 horas):
1. ✅ Backend corrigido e funcionando
2. ✅ Diagnóstico completo realizado
3. [ ] Corrigir 4 scrapers com erro de duplicate key
4. [ ] Corrigir 3 scrapers com erro de parsing
5. [ ] Criar script de verificação automática de sites

### Esta Semana:
1. [ ] Verificar os 122 scrapers com "Nenhum imóvel encontrado"
2. [ ] Classificar sites ativos vs inativos
3. [ ] Implementar top 10 leiloeiros pendentes (grandes)
4. [ ] Testar paginação em todos os scrapers Success

### Este Mês:
1. [ ] Implementar top 50 leiloeiros pendentes
2. [ ] Atingir 100 scrapers funcionando (20% de sucesso)
3. [ ] Ultrapassar 50.000 imóveis no banco
4. [ ] Reduzir dependência da Caixa para <70%

---

## 📊 DASHBOARD DE ACOMPANHAMENTO

Criar dashboard com métricas em tempo real:
- Total de scrapers por status (gráfico pizza)
- Top 20 fontes de imóveis (gráfico barras)
- Evolução temporal do número de imóveis
- Mapa de calor de cobertura geográfica
- Taxa de sucesso dos scrapers

**URL para consultas:** `https://leilao-backend-solitary-haze-9882.fly.dev/api/diagnostics/`

---

## ✅ CONCLUSÃO

O diagnóstico revelou que:

1. **O backend está funcionando perfeitamente** ✅
2. **95% dos scrapers NÃO estão funcionando** ❌
3. **89% dos dados vêm de UMA fonte** ⚠️
4. **A maioria dos erros é "Nenhum imóvel encontrado"** (sites vazios ou scrapers quebrados)
5. **Há grande potencial de crescimento** 🚀

**Foco principal:** Implementar rapidamente os top 50 leiloeiros pendentes para diversificar fontes e multiplicar o volume de dados.

**Ações críticas:**
1. Corrigir erros de código (7 scrapers) - HOJE
2. Verificar sites "sem imóveis" (122 scrapers) - ESTA SEMANA  
3. Implementar top 50 pendentes - ESTE MÊS

Com essas ações, podemos sair de 36k para 100k+ imóveis em poucas semanas.
