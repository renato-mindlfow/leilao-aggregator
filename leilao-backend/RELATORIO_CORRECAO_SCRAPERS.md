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

## Proximos passos
- Expandir correcoes para scrapers nao priorizados.
- Refinar parser de Sodre Santoro para descobrir listagem diretamente via API quando possivel.
