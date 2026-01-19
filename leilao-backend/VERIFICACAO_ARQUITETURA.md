# Verificação de Arquitetura de Scraping

**Data da verificação:** 2026-01-19  
**Script:** `scripts/verificar_arquitetura.py`

## Resumo Executivo

**Status atual**: ❌ **Arquitetura recomendada NÃO está implementada**

- **Arquitetura recomendada**: Crawl4AI + GPT-4o-mini (95% sucesso)
- **Arquitetura atual**: Mix de Playwright, HTTP/BeautifulSoup, sem Crawl4AI

## Detalhes da Verificação

### 1. Dependências Instaladas

| Dependência | Status | Notas |
|-------------|--------|-------|
| crawl4ai | ❌ NÃO instalado | Necessário para arquitetura de 95% sucesso |
| openai | ❌ NÃO instalado | Necessário para GPT-4o-mini |
| playwright | ✅ Instalado | Usado por scrapers atuais |

### 2. UniversalScraper

- **Status**: ✅ Disponível
- **Usa Crawl4AI**: ❌ NÃO
- **Usa LLM/OpenAI**: ⚠️ SIM (mas OpenAI não está instalado)

**Observação**: O código menciona LLM mas não pode funcionar sem a biblioteca `openai` instalada.

### 3. Scrapers Específicos (20 arquivos)

**Métodos usados pelos scrapers existentes**:

| Scraper | Métodos |
|---------|---------|
| base_scraper.py | Selenium, BeautifulSoup |
| caixa_scraper.py | HTTP |
| configurable_scraper.py | HTTP, BeautifulSoup |
| generic_scraper.py | BeautifulSoup |
| httpx_scraper.py | HTTP, BeautifulSoup |
| inovaleilao_scraper.py | HTTP, BeautifulSoup |
| jeleiloes_scraper.py | Playwright |
| lancenoleilao_scraper.py | Playwright |
| leilaobrasil_scraper.py | Playwright |
| leilaovip_scraper.py | HTTP, BeautifulSoup |
| ... | (mais 10 scrapers) |

**Análise**:
- **0 scrapers** usam Crawl4AI
- **9 scrapers** usam Playwright
- **11 scrapers** usam HTTP + BeautifulSoup
- **1 scraper** usa Selenium

### 4. ScraperManager

**9 scrapers registrados e ativos**:
1. Portal Zuk
2. Superbid
3. Mega Leiloes
4. Sodré Santoro
5. Pestana Leilões
6. LF Leiloes
7. Lance Judicial
8. Flex Leilões
9. Sold Leilões

## Comparação com Arquitetura Recomendada

### Arquitetura Recomendada (ARQUITETURA_DEFINITIVA_SCRAPING.md)

**Taxa de sucesso: 95%** (testado em 116 leiloeiros)

```
1. Crawl4AI (extração HTML limpo)
2. GPT-4o-mini (parsing estruturado)
3. Prompts otimizados
```

**Vantagens**:
- ✅ 95% de sucesso em sites diversos
- ✅ Não precisa conhecer estrutura HTML
- ✅ Adapta-se automaticamente a mudanças
- ✅ Extrai dados estruturados sem seletores

### Arquitetura Atual

**Taxa de sucesso estimada: ~10-60%** (varia por scraper)

```
1. Playwright OU HTTP/BeautifulSoup
2. Seletores CSS/XPath hardcoded
3. Parsing manual por scraper
```

**Desvantagens**:
- ❌ Seletores quebram quando site muda
- ❌ Precisa scraper específico por site
- ❌ Manutenção manual constante
- ❌ Baixa taxa de sucesso em sites diversos

## Conclusão

### Status dos 9 Scrapers Ativos

Todos os 9 scrapers ativos usam **métodos tradicionais** (Playwright ou HTTP):

1. **Portal Zuk** - Playwright
2. **Superbid** - HTTP + JSON parsing
3. **Mega Leiloes** - HTTP + BeautifulSoup
4. **Sodré Santoro** - Playwright + Fallbacks
5. **Pestana Leilões** - Playwright
6. **LF Leiloes** - HTTP/Playwright
7. **Lance Judicial** - Playwright
8. **Flex Leilões** - Playwright
9. **Sold Leilões** - API (HTTP)

### Taxa de Sucesso Atual

- **9 scrapers funcionando** (de ~500 leiloeiros conhecidos)
- **Taxa de cobertura**: ~1.8%
- **132 leiloeiros com erro** (26%)
- **333 leiloeiros pendentes** (66%)

### Impacto Potencial da Migração

Se migrar para **Crawl4AI + GPT-4o-mini**:

| Métrica | Antes | Depois (estimado) | Melhoria |
|---------|-------|-------------------|----------|
| Scrapers funcionando | 9 | 450+ | **50x** |
| Taxa de cobertura | 1.8% | 90%+ | **50x** |
| Taxa de sucesso | ~60% | 95% | **1.6x** |
| Leiloeiros com erro | 132 | ~25 | **-81%** |

## ⚠️ AÇÃO NECESSÁRIA

**A arquitetura atual NÃO usa Crawl4AI + LLM (que teve 95% de sucesso).**

### Próximo passo: Migrar para Arquitetura Recomendada

#### 1. Instalar Dependências

```bash
pip install crawl4ai
pip install openai
```

#### 2. Configurar Variável de Ambiente

```bash
# No arquivo .env
OPENAI_API_KEY=sua_chave_aqui
```

#### 3. Testar UniversalScraper com Crawl4AI

```python
# scripts/testar_crawl4ai.py
from app.services.universal_scraper import UniversalScraper

scraper = UniversalScraper()
properties = scraper.scrape_auctioneer({
    'name': 'Vivaleiloes',
    'website': 'https://www.vivaleiloes.com.br'
})

print(f"Extraídos: {len(properties)} imóveis")
```

#### 4. Migrar Scrapers Gradualmente

**Prioridade 1**: Leiloeiros com erro (132)
- Usar UniversalScraper com Crawl4AI
- Testar em lote de 10
- Comparar resultados

**Prioridade 2**: Leiloeiros pendentes (333)
- Aplicar Crawl4AI diretamente
- Evitar criar scrapers específicos

**Prioridade 3**: Substituir scrapers atuais
- Apenas se Crawl4AI tiver melhor resultado
- Manter scrapers atuais como fallback

### Estimativa de Impacto

**Esforço**: Baixo (instalar 2 dependências + configurar API key)  
**Benefício**: Alto (50x mais cobertura, 95% sucesso vs ~60%)  
**Risco**: Baixo (pode manter scrapers atuais como fallback)

### ROI Esperado

- **Custo da API OpenAI**: ~$0.001/leiloeiro (GPT-4o-mini é barato)
- **Custo para 500 leiloeiros**: ~$0.50
- **Economia de tempo**: Elimina necessidade de criar 450+ scrapers específicos
- **Manutenção**: Reduz drasticamente (sem seletores para quebrar)

## Teste da Arquitetura LLM (2026-01-19 15:38-15:44)

### Configuração do Teste

**Método testado**: Requests + BeautifulSoup + GPT-4o-mini  
**Observação**: Crawl4AI não pôde ser instalado (erro de compilação lxml no Windows)  
**Script**: `scripts/testar_llm_leiloeiros.py`  
**Modelo**: GPT-4o-mini  
**Leiloeiros**: 10 (escolhidos da lista de erros)

### Resultados

| Métrica | Valor |
|---------|-------|
| **Taxa de sucesso** | 40% (4 de 10) |
| **Imóveis extraídos** | 47 total |
| **Tokens usados** | 37,018 |
| **Custo estimado** | $0.0139 |
| **Tempo total** | ~6 minutos |

### Detalhamento por Leiloeiro

| Leiloeiro | Status | Imóveis | Observação |
|-----------|--------|---------|------------|
| Viva Leilões | ✗ Falha | 0 | HTML muito reduzido (166 chars) - site em JS |
| Unileilões | ✓ Sucesso | 11 | Funcionou bem |
| De Paula Online | ✓ Sucesso | 18 | Funcionou bem |
| Picelli Leilões | ✗ Falha | 0 | LLM gerou JSON malformado |
| Alliance Leilões | ✗ Falha | 0 | LLM gerou JSON malformado |
| Morales Leilões | ✗ Falha | 0 | HTML muito reduzido (231 chars) - site em JS |
| Spencer Leilões | ✓ Sucesso | 8 | Funcionou bem |
| Biasi Leilões | ✓ Sucesso | 10 | Funcionou bem |
| Ana Brasil Leilões | ✗ Falha | 0 | Site retornou 404 |
| Horizonte Leilões | ✗ Falha | 0 | HTML muito reduzido (18 chars) - site em JS |

### Análise das Falhas

**Categorias de erro**:
- **Sites em JavaScript** (3): HTML reduzido porque `requests` não executa JS
  - Viva Leilões (166 chars)
  - Morales Leilões (231 chars)
  - Horizonte Leilões (18 chars)
- **JSON malformado** (2): LLM gerou JSON com strings não terminadas
  - Picelli Leilões
  - Alliance Leilões
- **Site offline** (1): 404 Not Found
  - Ana Brasil Leilões

### Comparação: Expectativa vs Realidade

| Aspecto | ARQUITETURA_DEFINITIVA | Teste Real |
|---------|------------------------|------------|
| **Método** | Crawl4AI + GPT-4o-mini | Requests + GPT-4o-mini |
| **Taxa de sucesso** | 95% (116/116) | 40% (4/10) |
| **Execução JS** | ✓ Sim (via Playwright) | ✗ Não (requests simples) |
| **Custo/leiloeiro** | ~$0.001 | ~$0.0014 |

### Diagnóstico

**Por que 40% em vez de 95%?**

1. **Falta de Crawl4AI**: Principal diferença
   - Crawl4AI usa Playwright internamente (executa JavaScript)
   - `requests` simples não carrega conteúdo dinâmico
   - 3 dos 6 fracassos foram por HTML vazio (JavaScript)

2. **JSON malformado**: Problema do LLM
   - 2 casos onde GPT-4o-mini gerou JSON inválido
   - Possível solução: usar Function Calling em vez de text completion
   - Ou adicionar retry logic para JSON parsing

3. **Site offline**: Não é problema da arquitetura (1 caso)

### Conclusões

**✓ O que funcionou**:
- LLM conseguiu extrair dados estruturados de 4 sites
- Extraiu 47 imóveis com campos corretos
- Custo baixo ($0.0139 para 10 sites)
- Arquitetura é viável para sites estáticos/SSR

**✗ O que não funcionou**:
- Sites com JavaScript (60% dos testados usam JS)
- JSON parsing não é 100% confiável
- Sem Crawl4AI, perdemos a execução de JS

**⚠️ Recomendações**:

1. **Curto prazo**: Usar arquitetura híbrida
   - UniversalScraper com Playwright (sites JS)
   - LLM para parsing estruturado
   - Mantém scrapers específicos como fallback

2. **Médio prazo**: Resolver instalação do Crawl4AI
   - Tentar em Linux/WSL (mais fácil compilar dependências)
   - Ou usar Playwright + LLM diretamente (similar ao Crawl4AI)

3. **Melhorias imediatas**:
   - Adicionar retry para JSON parsing
   - Usar OpenAI Function Calling (JSON garantido)
   - Pre-filtrar sites offline antes de testar

### Próximos Passos

1. ✓ **Testar LLM básico** - Concluído (40% sucesso)
2. ⏸ **Instalar Crawl4AI** - Bloqueado (erro compilação Windows)
3. 🔄 **Alternativa**: Criar wrapper Playwright + LLM
4. 🔄 **Melhorar**: Adicionar Function Calling para JSON
5. 🔄 **Testar**: Arquitetura híbrida em mais 20 leiloeiros

## Referências

- **Documento oficial**: `ARQUITETURA_DEFINITIVA_SCRAPING.md`
- **Script de verificação**: `scripts/verificar_arquitetura.py`
- **Script de teste LLM**: `scripts/testar_llm_leiloeiros.py`
- **Teste original**: 116 leiloeiros testados (95% sucesso) - método completo com Crawl4AI
- **Teste real**: 10 leiloeiros testados (40% sucesso) - método parcial sem Crawl4AI
- **Data**: 2026-01-19
