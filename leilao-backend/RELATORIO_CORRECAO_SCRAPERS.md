# Relatorio de Correcao dos Scrapers

## Scrapers corrigidos
- megaleiloes
- portal_zuk
- sodresantoro
- superbid
- pestana_leiloes
- zukerman
- lancejudicial
- flexleiloes
- sold

## Problemas encontrados e solucoes
- ScraperManager iniciava sem scrapers registrados.
  - Solucao: registro automatico de scrapers principais e execucao flexivel para metodos `scrape_listings` e `scrape_properties`.
- Normalizacao do campo `source` inconsistentes.
  - Solucao: `source` padronizado para lowercase e fallback para `auctioneer_id`.
- Portal Zuk retornava propriedades sem preco em alguns casos.
  - Solucao: fallback para extrair `price` a partir de outros campos e regex de moeda.
- Sodre Santoro bloqueado com 403 e listagem sem links.
  - Solucao: fallback com ScrapingBee + links conhecidos, extraindo titulo, cidade/estado e preco a partir do HTML de detalhes.
- Pestana com extracao de cidade/estado incorreta em titulos sem separador.
  - Solucao: parse robusto com regex de UF e fallback em string completa.
- Lance Judicial com Playwright lento e dados incompletos.
  - Solucao: fallback com MultiLayerFetcher + HTML para listar categorias e extrair detalhes.
- Flex Leiloes retornava "SOMENTE ONLINE" como cidade.
  - Solucao: limpeza de cidade/estado e fallback para "Nao informado".
- Sold ignorava `max_properties` e retornava pagina cheia.
  - Solucao: limitar `max_items` e retorno ao `max_properties`.
- Zukerman redireciona para Portal Zuk.
  - Solucao: fallback para PortalZukScraperV2 com normalizacao de `source` e `auctioneer_id`.
- LF Leiloes com listagem JS e sem links diretos.
  - Solucao parcial: tentativa com fetcher + Playwright (ainda sem links).

## Testes executados
- `MegaleiloesScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=megaleiloes`.
- `PortalZukScraperV2().scrape_properties(max_properties=5)` -> 5 imoveis, `source=portal_zuk`, preco preenchido.
- `SodreSantoroScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=sodresantoro`, cidade/estado e preco preenchidos.
- `SuperbidScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=superbid`.
- `PestanaScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=pestana_leiloes`.
- `ZukermanScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=zukerman`.
- `LanceJudicialPlaywrightScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=lancejudicial`.
- `FlexLeiloesPlaywrightScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=flexleiloes`.
- `SoldPlaywrightScraper().scrape_properties(max_properties=5)` -> 5 imoveis, `source=sold`.

## Scrapers que ainda precisam de trabalho
- lfreiloes
- demais scrapers nao prioritarios

## Resultados do scrape completo (2026-01-19)

### Scrape inicial (MAX_PER_SCRAPER=25-60):
- **MegaLeiloes**: 25/25 salvos no Supabase (81.6s)
- **Portal Zuk**: 25/25 salvos no Supabase (188.2s)
- **Sodre Santoro**: 18/18 salvos no Supabase (389.5s)
- **Superbid**: 25/25 salvos no Supabase (260.9s)
- **Pestana Leiloes**: 9/9 salvos no Supabase (210.0s)
- **Zukerman**: 25/25 salvos no Supabase (239.1s)
- **Lance Judicial**: 25/25 salvos no Supabase (67.1s)
- **Flex Leiloes**: 15/15 salvos no Supabase (23.5s)
- **Sold Leiloes**: 60/60 salvos no Supabase (5.3s)
**Total inicial**: 227 imoveis

### Scrape com volume aumentado (MAX_PER_SCRAPER=100-200):
- **MegaLeiloes**: 100/100 salvos no Supabase (262.2s)
- **Portal Zuk**: 30/100 salvos (limite do site) (171.0s)
- **Lance Judicial**: 100/100 salvos no Supabase (338.0s)
- **Sold Leiloes**: 150/200 salvos (limite do site) (8.5s)
- **Zukerman**: 100/100 salvos no Supabase (292.5s)
- **Sodre Santoro**: 18/50 salvos (limite do fallback) (374.2s)
- **Pestana Leiloes**: 12/100 salvos (limite do site) (126.5s)
- **Superbid**: timeout (parsing issues)
- **Flex Leiloes**: timeout (performance issues)
**Total volume aumentado**: 510 imoveis

### Total geral:
- **~810 imoveis novos** adicionados ao Supabase
- **7 scrapers** executados com sucesso em volume alto
- Banco cresceu de 50,724 para 51,534 imoveis
- Tempo total: ~50 minutos (execucao em lotes)

### Distribuicao de sources no banco (apos scrape de volume):
- megaleiloes: 1045 imoveis (10.4% da amostra)
- sold: 274 imoveis (2.7%)
- superbid: 236 imoveis (2.4%)
- lancejudicial: 147 imoveis (1.5%)
- zukerman: 127 imoveis (1.3%)
- sodresantoro: 109 imoveis (1.1%)
- portal_zuk: 60 imoveis (0.6%)
- flexleiloes: 39 imoveis (0.4%)
- pestana_leiloes: 13 imoveis (0.1%)

### Status dos leiloeiros:
- success: 23 leiloeiros
- error: 132 leiloeiros
- pending: 333 leiloeiros
- disabled: 10 leiloeiros
- needs_playwright: 3 leiloeiros

### Observações:
- Superbid tem problemas de parsing (__NEXT_DATA__ None.get()) que causam lentidão
- Flex Leiloes tem problemas de performance que causam timeouts
- Portal Zuk, Pestana e Sodre Santoro tem limites de volume disponivel nos sites
- Sold é o scraper mais rápido (API-based)
- Rate limiting (HTTP 429) afeta Portal Zuk e Zukerman em volumes altos

## Proximos passos
- Expandir correcoes para scrapers nao priorizados.
- Refinar parser de Sodre Santoro para descobrir listagem diretamente via API quando possivel.
- Corrigir erros de parse no Superbid (__NEXT_DATA__ None.get()).
- Adicionar mais scrapers para cobrir os 333 leiloeiros pendentes.
