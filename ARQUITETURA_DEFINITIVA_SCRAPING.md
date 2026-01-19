# ARQUITETURA DEFINITIVA DE SCRAPING - LEILOHUB

**Documento Canônico** - Esta é a fonte única de verdade sobre a arquitetura de scraping.
**Última Atualização:** 2026-01-19
**Responsável:** Engenheiro Chefe LeiloHub

---

## ⚠️ LEIA ISTO PRIMEIRO

Este documento existe porque o projeto tinha **3 arquiteturas diferentes documentadas** em lugares diferentes, causando confusão. 

**REGRA:** Antes de implementar ou modificar qualquer scraper, consulte este documento.

---

## 🏆 ARQUITETURA OFICIAL (APROVADA)

### Crawl4AI + LLM (GPT-4o-mini)

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUXO DE EXTRAÇÃO                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   URL do Leiloeiro                                          │
│         │                                                   │
│         ▼                                                   │
│   ┌─────────────┐                                           │
│   │  Crawl4AI   │  ← Renderiza JavaScript, obtém HTML       │
│   └──────┬──────┘                                           │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────────────┐                                   │
│   │ PruningContentFilter │  ← Remove ruído (nav, footer)    │
│   │   threshold=0.48     │                                  │
│   └──────────┬──────────┘                                   │
│              │                                              │
│              ▼                                              │
│   ┌─────────────────────────┐                               │
│   │ LLMExtractionStrategy   │  ← Extrai dados estruturados  │
│   │   + GPT-4o-mini         │                               │
│   └──────────┬──────────────┘                               │
│              │                                              │
│              ▼                                              │
│   ┌─────────────────────┐                                   │
│   │ Regex Fallback      │  ← Extrai fotos (mais confiável)  │
│   │   para URLs de      │                                   │
│   │   imagens           │                                   │
│   └──────────┬──────────┘                                   │
│              │                                              │
│              ▼                                              │
│   ┌─────────────────────┐                                   │
│   │ Normalização        │  ← Title Case, validações         │
│   │   + Validação       │                                   │
│   └──────────┬──────────┘                                   │
│              │                                              │
│              ▼                                              │
│        Supabase                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Por que esta arquitetura?

| Critério | Resultado |
|----------|-----------|
| **Taxa de Sucesso** | 95% (testado em 116 leiloeiros) |
| **Custo Mensal** | ~$0.10 (OpenAI) |
| **Manutenção** | Baixa (não precisa de seletores CSS por site) |
| **Adaptabilidade** | Alta (LLM entende diferentes estruturas) |

### Configurações Otimizadas

```python
# Crawl4AI
chunk_token_threshold = 8000  # Era 4000, aumentado para reduzir tokens
overlap_rate = 0.1            # Era 0.2, reduzido para economia

# PruningContentFilter
threshold = 0.48              # Otimizado para remover navegação sem perder conteúdo

# LLM
model = "gpt-4o-mini"         # Melhor custo-benefício
fit_markdown = True           # Usar fit_markdown ao invés de raw_markdown
```

---

## ❌ ARQUITETURAS DESCARTADAS

### 1. Multi-Layer HTTP Puro

```
Layer 1: Fetch direto (httpx)
Layer 2: Headers avançados
Layer 3: Jina.ai
Layer 4: ScrapingBee
```

**Documentada em:** `ARQUITETURA_TECNICA_E_INFRA.md`, `ESTRATEGIA_MULTI_FALLBACK.txt`

**Por que foi descartada:**
- Foco apenas em OBTER o HTML, não em EXTRAIR dados
- Requer seletores CSS específicos por site (alta manutenção)
- Não testada em escala
- Não resolve o problema de sites com estruturas diferentes

**Quando usar (parcialmente):**
- As camadas de fetch PODEM ser usadas como fallback para obter HTML quando Crawl4AI falhar
- Jina.ai é útil para sites com Cloudflare pesado

### 2. Adaptadores Manus (ScrapingBee Principal)

```
ScrapingBee → Adaptadores (default, white_label, elementor) → Fallback IA
```

**Documentada em:** `GUIA_IMPLEMENTACAO.md`, `HANDOVER_TO_CLAUDE_V2.md`

**Por que foi descartada:**
- Taxa de sucesso: apenas 58.7%
- Custo: $49/mês (ScrapingBee)
- Requer adaptadores específicos por tipo de site
- Mais complexa de manter

**Quando usar (parcialmente):**
- Adaptador `white_label_v1` para sites Superbid Exchange (API JSON interna)
- ScrapingBee como fallback para sites com proteção anti-bot severa

---

## 📊 HISTÓRICO DE TESTES

### Teste em Escala - 23/12/2025

| Batch | Leiloeiros | Sucesso | Taxa |
|-------|------------|---------|------|
| Batch 1 | 28 | 25 | 89% |
| Batch 2 | 48 | 46 | 96% |
| Batch 3 | 40 | 39 | 97.5% |
| **TOTAL** | **116** | **110** | **95%** |

**Arquitetura testada:** Crawl4AI + GPT-4o-mini

**Problemas resolvidos durante testes:**
1. LLM não extraía fotos → Regex fallback implementado
2. Título incorreto ("Navegue pelos lotes") → PruningContentFilter ajustado
3. Valores com HTML entities → html.unescape() adicionado
4. Modalidade sempre "Leilão" → Regex específico para Judicial/Extrajudicial
5. 106k tokens por propriedade → Otimização para 8k tokens

---

## 🔧 IMPLEMENTAÇÃO ATUAL (Janeiro 2026)

### Status dos Scrapers

Os scrapers em `leilao-backend/app/scrapers/` usam uma **mistura de abordagens**:

| Scraper | Método | Status |
|---------|--------|--------|
| MegaleiloesScraper | Requests + BeautifulSoup | ✅ Funcionando |
| PortalZukScraperV2 | Requests + BeautifulSoup | ✅ Funcionando |
| SodreSantoroScraper | Requests + ScrapingBee fallback | ✅ Funcionando |
| SuperbidScraper | Requests + BeautifulSoup | ✅ Funcionando |
| PestanaScraper | Playwright + Stealth | ✅ Funcionando |
| UniversalScraper | Crawl4AI + LLM | ⚠️ Disponível mas subutilizado |

### Problema Identificado

A arquitetura testada com 95% de sucesso (Crawl4AI + LLM) está **disponível mas não é a principal**.

Os scrapers específicos usam métodos variados, o que explica:
- 122 leiloeiros com erro "Nenhum imóvel encontrado"
- 127 leiloeiros pendentes (nunca executados)
- Apenas 28 funcionando (10%)

### Recomendação

**Migrar scrapers para usar UniversalScraper (Crawl4AI + LLM) como padrão**, mantendo scrapers específicos apenas para casos especiais (white_label, Playwright para sites com proteção).

---

## 📁 ARQUIVOS RELACIONADOS

### Código Principal
- `leilao-backend/app/services/universal_scraper.py` - Implementação Crawl4AI + LLM
- `leilao-backend/app/scrapers/scraper_manager.py` - Orquestrador
- `leilao-backend/adaptadores/default.py` - AdaptadorDefaultV2 (Manus)

### Documentação (DEPRECADA - usar este documento)
- `ARQUITETURA_TECNICA_E_INFRA.md` - Descreve Multi-Layer HTTP (não testada)
- `ESTRATEGIA_MULTI_FALLBACK.txt` - Ordem das camadas (conflitante)
- `GUIA_IMPLEMENTACAO.md` - Adaptadores Manus (58.7% sucesso)
- `HANDOVER_LEILOHUB_2025-12-23.md` - Descreve arquitetura correta (95% sucesso)

### Configuração
- `.env` - Credenciais (OPENAI_API_KEY, SCRAPINGBEE_API_KEY, etc.)

---

## ✅ CHECKLIST PARA NOVOS SCRAPERS

Antes de criar um novo scraper:

1. [ ] Consultar este documento
2. [ ] Verificar se UniversalScraper (Crawl4AI + LLM) funciona para o site
3. [ ] Se não funcionar, documentar POR QUE e qual alternativa usar
4. [ ] Atualizar este documento com a decisão

---

## 📝 REGISTRO DE DECISÕES

### 2025-12-23: Escolha da Arquitetura Principal

**Decisão:** Usar Crawl4AI + GPT-4o-mini como arquitetura principal.

**Alternativas consideradas:**
1. Multi-Layer HTTP (não testada)
2. Adaptadores Manus + ScrapingBee (58.7% sucesso, $49/mês)
3. Crawl4AI + GPT-4o-mini (95% sucesso, ~$0.10/mês)

**Razão:** Maior taxa de sucesso, menor custo, menor manutenção.

**Responsável:** Equipe de desenvolvimento

---

### 2026-01-19: Identificação de Inconsistência

**Problema:** Projeto tinha 3 arquiteturas documentadas em lugares diferentes, causando confusão.

**Decisão:** Criar este documento como fonte única de verdade.

**Ação:** Consolidar informações e deprecar documentos conflitantes.

**Responsável:** Engenheiro Chefe

---

## 🚨 ALERTAS

### Não faça isso:
- ❌ Criar scraper com fetch simples sem tentar Crawl4AI primeiro
- ❌ Usar ScrapingBee como primeira opção (custa $$$)
- ❌ Adicionar seletores CSS específicos sem documentar por quê
- ❌ Ignorar este documento e usar arquiteturas antigas

### Faça isso:
- ✅ Sempre tentar UniversalScraper primeiro
- ✅ Documentar decisões neste arquivo
- ✅ Atualizar taxa de sucesso após novos testes
- ✅ Manter histórico de problemas e soluções

---

## 📞 DÚVIDAS?

Se houver dúvidas sobre qual abordagem usar:

1. Consulte a seção "ARQUITETURA OFICIAL"
2. Verifique o "HISTÓRICO DE TESTES"
3. Se ainda houver dúvida, documente a situação e a decisão tomada

---

**Este documento é a fonte única de verdade para arquitetura de scraping do LeiloHub.**
