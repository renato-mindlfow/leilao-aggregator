# INVESTIGACAO SCRAPERS - FASE 1 (2025-01-18)

## 1) Resultado da analise de sources
Script executado: `leilao-backend/scripts/analisar_sources.py`

Resumo (amostra limitada a 10.000 registros):
- Total de imoveis: 50.486
- Sources encontrados: 77
- NULL/VAZIO: 560 (5,6% da amostra)
- Top sources (amostra):
  - caixa: 5.423 (54,2%)
  - superbid_agregado: 1.984 (19,8%)
  - megaleiloes: 845 (8,5%)
  - NULL/VAZIO: 560 (5,6%)
  - scraper_v45: 548 (5,5%)
  - Turanileiloes: 206 (2,1%)
  - sodresantoro: 91 (0,9%)
  - sold: 48 (0,5%)
  - Megaleiloes (case diferente): 11 (0,1%)

Distribuicao por auctioneer_id (amostra):
- auctioneer_id encontrados: 126
- Top auctioneer_id:
  - caixa: 4.638 (46,4%)
  - caixa_federal: 2.432 (24,3%)
  - 2: 481 (4,8%)
  - 166: 397 (4,0%)
  - 150: 367 (3,7%)
  - 46: 307 (3,1%)

Imoveis sem source E sem auctioneer_id:
- 0 (amostra)

Observacao: a amostra limitada NAO confirma 94% sem source. Ha muitos sources preenchidos, mas com inconsistencias de padrao (ex: "megaleiloes" vs "Megaleiloes").

## 2) Estrutura dos scrapers
Scrapers existentes em `app/scrapers` (parcial):
- base_scraper.py, caixa_scraper.py, configurable_scraper.py
- generic_scraper.py, httpx_scraper.py
- megaleiloes_scraper.py, megaleiloes_playwright.py
- portalzuk_scraper.py, portalzuk_scraper_playwright.py, portalzuk_scraper_v2.py
- sodresantoro_scraper.py, sodresantoro_verified.py
- sold_playwright.py, superbid_scraper.py
- universal_scraper_v2.py, etc.

ScraperManager (`app/scrapers/scraper_manager.py`):
- Nao registra scrapers automaticamente no __init__.
- `ScraperManager().scrapers` inicia vazio; precisa de `register_scraper`.
- Existe `run_all_scrapers()` (funcao global) que importa scrapers e executa sem limite.

UniversalScraper (`app/services/universal_scraper.py`):
- Classe `UniversalScraper` com estrategias HTTP direto + Jina.
- Nao e o service usado pelos endpoints principais.

UniversalScraperService (`app/services/universal_scraper_service.py`):
- Orquestra TODOS leiloeiros do banco.
- Usa scrapers especificos quando `auctioneer_id` bate em:
  - portal_zuk, superbid, megaleiloes, leilaovip, inovaleilao, pestana
- Caso contrario, cai no `GenericScraper` (config dinamica).

Endpoints relevantes em `app/main.py`:
- `/api/scrapers/run/{auctioneer_id}` e `/api/scrapers/run-all` (UniversalScraperService)
- `/api/scrapers/bulk-import` (scrapers especificos sequenciais)
- `/scrape/all` (usa `run_all_scrapers` do scraper_manager)
- `/api/scraper/run-all`, `/api/scraper/run-single/{auctioneer_id}` (scraper_orchestrator)

## 3) Resultado do teste Megaleiloes
Script executado: `leilao-backend/scripts/testar_megaleiloes_detalhado.py`

Resultado (max_properties=5, verify_urls=False):
- 5 completos, 0 incompletos, 5 total
- Exemplo:
  - Apartamento 142 m2 - Manaus/AM - preco 1033507.83 - source megaleiloes
  - Apartamento 40 m2 - Sao Bernardo do Campo/SP - preco 237500.56 - source megaleiloes
  - Casa 82 m2 - Rio de Janeiro/RJ - preco 573621.13 - source megaleiloes

## 4) Problemas identificados (e correcoes aplicadas)
1) Filtro de links no Megaleiloes estava incluindo URLs nao-imovel:
   - Condicao: `if '/imoveis/' in href and '-x' in href.lower() or '-j' in href.lower()`
   - Isso aceitava qualquer URL com "-j" (ex: /leiloes-judiciais).
   - Corrigido para exigir `/imoveis/` e (`-x` ou `-j`).
2) `source` nao era preenchido no MegaleiloesScraper:
   - Corrigido para `source="megaleiloes"`.
3) `ScraperManager` inicia sem scrapers registrados:
   - Qualquer uso direto do manager sem registrar resulta em 0 imoveis.
4) Inconsistencias de padrao em `source` (case):
   - Ex: "megaleiloes" e "Megaleiloes" aparecem na amostra.

## 5) Proximos passos recomendados
- Padronizar `source` em TODOS os scrapers (ex: sempre lowercase).
- Conferir auctioneer_id no banco para grandes leiloeiros (megaleiloes, portal_zuk, sodresantoro) e alinhar com `SPECIFIC_SCRAPERS`.
- Rodar `analisar_sources.py` sem limite (ou aumentar limites) para validar o % real de NULL.
- Revisar quais endpoints/rotas estao rodando em producao e garantir que usam os scrapers corretos.
