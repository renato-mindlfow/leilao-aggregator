# Base de Conhecimento: Leiloeiros do Brasil

**DOCUMENTO DE REFERÊNCIA OBRIGATÓRIA**
**Última atualização:** 2025-01-19
**Autor:** Renato (Owner LeiloHub)

---

## ⚠️ IMPORTANTE

Este documento contém informações VALIDADAS pelo owner do projeto sobre os principais leiloeiros do Brasil. 

**REGRAS:**
1. Consultar este documento ANTES de criar/modificar scrapers
2. Não criar scrapers duplicados para o mesmo leiloeiro
3. Respeitar as estimativas de volume informadas
4. Atualizar este documento quando houver novas informações

---

## Principais Leiloeiros (por volume estimado)

### 1. Portal Zuk (antigo Zukerman)

| Campo | Valor |
|-------|-------|
| **Nome atual** | Portal Zuk |
| **Nome antigo** | Zukerman |
| **Website** | https://www.portalzuk.com.br |
| **Volume estimado** | ~1.000 imóveis |
| **Porte** | **MAIOR do Brasil** |
| **Source no banco** | `portalzuk` |
| **Scraper** | `PortalZukScraperV2` |

**IMPORTANTE:** 
- Zukerman e Portal Zuk são a MESMA empresa
- Usar APENAS `portalzuk` como source
- NÃO criar scraper separado para "zukerman"
- Se existir scraper "zukerman", REMOVER e migrar dados para `portalzuk`

---

### 2. Mega Leilões

| Campo | Valor |
|-------|-------|
| **Nome** | Mega Leilões |
| **Website** | https://www.megaleiloes.com.br |
| **Volume estimado** | 600-800 imóveis |
| **Porte** | Grande |
| **Source no banco** | `megaleiloes` |
| **Scraper** | `MegaleiloesScraper` |

---

### 3. Sodré Santoro

| Campo | Valor |
|-------|-------|
| **Nome** | Sodré Santoro |
| **Website** | https://www.sodresantoro.com.br |
| **Volume estimado** | A definir |
| **Porte** | Grande |
| **Source no banco** | `sodresantoro` |
| **Scraper** | `SodreSantoroScraper` |

---

### 4. Superbid

| Campo | Valor |
|-------|-------|
| **Nome** | Superbid |
| **Website** | https://www.superbid.net |
| **Volume estimado** | A definir |
| **Porte** | Grande (plataforma agregadora) |
| **Source no banco** | `superbid` |
| **Scraper** | `SuperbidScraper` |

---

### 5. Sold Leilões

| Campo | Valor |
|-------|-------|
| **Nome** | Sold Leilões |
| **Website** | https://www.sold.com.br |
| **Volume estimado** | A definir |
| **Porte** | Médio-Grande |
| **Source no banco** | `sold` |
| **Scraper** | `SoldPlaywrightScraper` |

**Observação:** API-based, muito rápido (150 imóveis em 8.5s)

---

### 6. Lance Judicial

| Campo | Valor |
|-------|-------|
| **Nome** | Lance Judicial |
| **Website** | https://www.lancejudicial.com.br |
| **Volume estimado** | A definir |
| **Porte** | Médio |
| **Source no banco** | `lancejudicial` |
| **Scraper** | `LanceJudicialPlaywrightScraper` |

---

### 7. Pestana Leilões

| Campo | Valor |
|-------|-------|
| **Nome** | Pestana Leilões |
| **Website** | https://www.pestanaleiloes.com.br |
| **Volume estimado** | A definir |
| **Porte** | Médio |
| **Source no banco** | `pestana` |
| **Scraper** | `PestanaScraper` |

---

### 8. Flex Leilões

| Campo | Valor |
|-------|-------|
| **Nome** | Flex Leilões |
| **Website** | https://www.flexleiloes.com.br |
| **Volume estimado** | A definir |
| **Porte** | Médio |
| **Source no banco** | `flexleiloes` |
| **Scraper** | `FlexLeiloesPlaywrightScraper` |

---

## Leiloeiros que NÃO são de imóveis

| Nome | Segmento | Ação |
|------|----------|------|
| LF Leilões | Gado/Rural | Ignorar ou criar categoria separada |

---

## Regras de Validação

### Volume mínimo esperado por scraper

Se um scraper retornar MUITO MENOS que o esperado, investigar:

| Leiloeiro | Mínimo esperado | Se retornar menos |
|-----------|-----------------|-------------------|
| Portal Zuk | 500 imóveis | Verificar paginação |
| Mega Leilões | 400 imóveis | Verificar paginação |
| Outros | 50 imóveis | Verificar se site mudou |

### Sinais de problema

1. **Volume muito baixo** → Paginação não está funcionando
2. **Dois scrapers para mesmo site** → Duplicação, remover um
3. **Source inconsistente** → Normalizar para lowercase sem espaços

---

## Histórico de Correções

| Data | Problema | Solução |
|------|----------|---------|
| 2025-01-19 | Zukerman e Portal Zuk duplicados | Unificar em `portalzuk` |
| 2025-01-19 | Portal Zuk com só 60 imóveis | Investigar paginação |

---

## Como Atualizar Este Documento

Quando o owner (Renato) fornecer novas informações sobre leiloeiros:

1. Atualizar este documento imediatamente
2. Commitar com mensagem: `docs: atualizar base de conhecimento leiloeiros`
3. Ajustar scrapers conforme necessário

**Este documento é a FONTE DA VERDADE sobre leiloeiros.**
