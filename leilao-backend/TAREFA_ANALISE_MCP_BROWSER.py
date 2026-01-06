# ============================================================
# TAREFA: Usar MCP Web Browser para Analisar os 4 Sites
# ============================================================
# Para: Cursor Agent
# Modo: INTERATIVO com MCP
# Ferramenta: @web-browser
# ============================================================

"""
╔══════════════════════════════════════════════════════════════╗
║  OBJETIVO                                                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Usar o MCP @web-browser como "olhos" para:                  ║
║  1. Acessar cada site problemático                           ║
║  2. Ver o HTML renderizado (pós-JavaScript)                  ║
║  3. Identificar seletores CSS corretos                       ║
║  4. Encontrar padrão de paginação                            ║
║  5. Atualizar configs com seletores precisos                 ║
║                                                              ║
║  Sites a analisar:                                           ║
║  1. Mega Leilões    - /imoveis                               ║
║  2. Lance Judicial  - /imoveis                               ║
║  3. Portal Zukerman - /leilao-de-imoveis                     ║
║  4. Sold Leilões    - /h/imoveis (também testar API)         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

INSTRUÇÕES PARA O CURSOR AGENT:
===============================

Para CADA site abaixo, execute os passos usando @web-browser MCP.

"""

# ============================================================
# SITE 1: MEGA LEILÕES
# ============================================================
MEGA_LEILOES = """
╔══════════════════════════════════════════════════════════════╗
║  SITE 1: MEGA LEILÕES                                        ║
╚══════════════════════════════════════════════════════════════╝

PASSO 1: Acessar página de listagem
───────────────────────────────────
Use @web-browser para acessar:
https://www.megaleiloes.com.br/imoveis

PASSO 2: Analisar estrutura da listagem
───────────────────────────────────────
Responda:
□ A página carregou conteúdo? (ou ficou em branco/loading?)
□ Quantos cards/itens de imóveis aparecem?
□ Qual o seletor CSS dos cards? (ex: .card, .item, article)
□ Qual o seletor dos links para página do imóvel?
□ Os links têm padrão? (ex: /leilao/12345, /imovel/12345)

PASSO 3: Analisar paginação
───────────────────────────
Responda:
□ Tem paginação visível? (números, setas, "carregar mais")
□ Qual o seletor do botão/link de próxima página?
□ A URL muda com paginação? (ex: ?page=2)
□ É scroll infinito?

PASSO 4: Acessar página de UM imóvel
────────────────────────────────────
Clique em um imóvel e analise a página de detalhes:
□ Qual seletor do título? (h1, .titulo, etc)
□ Qual seletor do preço? (.preco, .valor, etc)
□ Qual seletor da localização? (cidade/estado)
□ Qual seletor da imagem principal?
□ Qual seletor da área (m²)?

PASSO 5: Documentar descobertas
───────────────────────────────
Preencha o JSON abaixo com os seletores encontrados:

{
  "id": "megaleiloes",
  "listing_url": "/imoveis",
  "selectors": {
    "property_card": "SELETOR_DO_CARD",
    "property_link": "SELETOR_DO_LINK",
    "next_page": "SELETOR_PROXIMA_PAGINA",
    "title": "SELETOR_TITULO",
    "price": "SELETOR_PRECO",
    "location": "SELETOR_LOCALIZACAO",
    "image": "SELETOR_IMAGEM",
    "area": "SELETOR_AREA"
  },
  "pagination": {
    "type": "query|path|scroll|button",
    "param": "page",
    "pattern": "URL_PATTERN"
  },
  "link_pattern": "REGEX_DO_LINK"
}
"""

# ============================================================
# SITE 2: LANCE JUDICIAL
# ============================================================
LANCE_JUDICIAL = """
╔══════════════════════════════════════════════════════════════╗
║  SITE 2: LANCE JUDICIAL                                      ║
╚══════════════════════════════════════════════════════════════╝

PASSO 1: Acessar página de listagem
───────────────────────────────────
Use @web-browser para acessar:
https://www.lancejudicial.com.br/imoveis

ATENÇÃO: Este site tem Cloudflare. Aguarde carregar completamente.

PASSO 2: Analisar estrutura da listagem
───────────────────────────────────────
Responda:
□ Passou pelo Cloudflare? (ou ficou na tela de verificação?)
□ Quantos cards/itens de imóveis aparecem?
□ Qual o seletor CSS dos cards?
□ Qual o seletor dos links para página do imóvel?
□ Os links têm padrão?

PASSO 3: Analisar paginação
───────────────────────────
Responda:
□ Tem paginação visível?
□ Qual o seletor do botão/link de próxima página?
□ A URL muda com paginação?

PASSO 4: Acessar página de UM imóvel
────────────────────────────────────
Clique em um imóvel e analise:
□ Qual seletor do título?
□ Qual seletor do preço?
□ Qual seletor da localização?
□ Qual seletor da imagem?

PASSO 5: Documentar descobertas
───────────────────────────────
{
  "id": "lancejudicial",
  "listing_url": "/imoveis",
  "cloudflare": true|false,
  "selectors": {
    "property_card": "SELETOR",
    "property_link": "SELETOR",
    "next_page": "SELETOR",
    "title": "SELETOR",
    "price": "SELETOR",
    "location": "SELETOR",
    "image": "SELETOR"
  },
  "pagination": {
    "type": "query|path|scroll|button",
    "param": "page"
  },
  "link_pattern": "REGEX"
}
"""

# ============================================================
# SITE 3: PORTAL ZUKERMAN
# ============================================================
PORTAL_ZUKERMAN = """
╔══════════════════════════════════════════════════════════════╗
║  SITE 3: PORTAL ZUKERMAN                                     ║
╚══════════════════════════════════════════════════════════════╝

PASSO 1: Acessar página de listagem
───────────────────────────────────
Use @web-browser para acessar:
https://www.portalzuk.com.br/leilao-de-imoveis

PASSO 2: Analisar estrutura da listagem
───────────────────────────────────────
Responda:
□ A página carregou?
□ Quantos cards de imóveis aparecem?
□ Qual o seletor CSS dos cards?
□ Qual o seletor dos links?
□ Padrão dos links? (ex: /imovel/sp/cidade/bairro/123)

PASSO 3: Analisar filtros/subcategorias
───────────────────────────────────────
Responda:
□ Tem filtros visíveis? (tipo, estado, cidade)
□ Tem abas de subcategorias? (apartamentos, casas, terrenos)
□ A URL muda ao filtrar?

PASSO 4: Analisar paginação
───────────────────────────
Responda:
□ Tem paginação?
□ É scroll infinito ou botões?
□ Qual o padrão da URL de paginação?

PASSO 5: Acessar página de UM imóvel
────────────────────────────────────
Clique em um imóvel e analise:
□ Qual seletor do título?
□ Qual seletor do preço/lance mínimo?
□ Onde está cidade/estado? (breadcrumb? header?)
□ Qual seletor da imagem?
□ Qual seletor da área?

PASSO 6: Documentar descobertas
───────────────────────────────
{
  "id": "portalzuk",
  "listing_url": "/leilao-de-imoveis",
  "selectors": {
    "property_card": "SELETOR",
    "property_link": "SELETOR",
    "next_page": "SELETOR",
    "title": "SELETOR",
    "price": "SELETOR",
    "location": "SELETOR",
    "image": "SELETOR",
    "area": "SELETOR"
  },
  "pagination": {
    "type": "TYPE",
    "pattern": "PATTERN"
  },
  "link_pattern": "REGEX"
}
"""

# ============================================================
# SITE 4: SOLD LEILÕES
# ============================================================
SOLD_LEILOES = """
╔══════════════════════════════════════════════════════════════╗
║  SITE 4: SOLD LEILÕES                                        ║
╚══════════════════════════════════════════════════════════════╝

NOTA: Sold usa plataforma Superbid com API REST. 
      Vamos analisar AMBOS: HTML e API.

PARTE A: ANALISAR PÁGINA HTML
─────────────────────────────

PASSO 1: Acessar página de listagem
Use @web-browser para acessar:
https://www.sold.com.br/h/imoveis

PASSO 2: Analisar estrutura
Responda:
□ A página carregou? (é SPA React)
□ Quantos cards aparecem?
□ Qual o seletor dos cards? (Material-UI usa classes dinâmicas)
□ Qual o seletor dos links?

PASSO 3: Analisar paginação
Responda:
□ Tem paginação? Onde?
□ Qual o padrão? (?pageNumber=2)

PARTE B: TESTAR API REST
────────────────────────

PASSO 4: Testar API descoberta
Use @web-browser para acessar diretamente:
https://offer-query.superbid.net/offers/?portalId=[2,15]&filter=stores.id:[1161]&pageNumber=1&pageSize=10

Responda:
□ Retornou JSON?
□ Qual o campo "total"? (quantidade de ofertas)
□ Estrutura do objeto "offers"?

PASSO 5: Testar filtro de imóveis
Acesse:
https://offer-query.superbid.net/offers/?portalId=[2,15]&filter=stores.id:[1161];product.productType.description:Imóveis&pageNumber=1&pageSize=10

Responda:
□ Retornou apenas imóveis?
□ Quantos no total?
□ Se não funcionou, qual erro?

PASSO 6: Buscar filtro correto
Se o filtro acima não funcionou, acesse a página de categorias:
https://offer-query.superbid.net/categories/?portalId=[2,15]&filter=stores.id:[1161]

Responda:
□ Quais categorias existem?
□ Qual o ID/nome da categoria de imóveis?
□ Qual o filtro correto?

PASSO 7: Documentar descobertas
{
  "id": "sold",
  "method": "api_rest",
  "api_base": "https://offer-query.superbid.net",
  "endpoints": {
    "offers": "/offers/",
    "categories": "/categories/"
  },
  "filters": {
    "store_id": 1161,
    "portal_id": "[2,15]",
    "imoveis_filter": "FILTRO_CORRETO_AQUI"
  },
  "pagination": {
    "param_page": "pageNumber",
    "param_size": "pageSize",
    "max_size": 50
  },
  "response_structure": {
    "total_field": "total",
    "items_field": "offers",
    "price_field": "price",
    "title_field": "product.shortDesc"
  }
}
"""

# ============================================================
# RESUMO FINAL
# ============================================================
RESUMO = """
╔══════════════════════════════════════════════════════════════╗
║  APÓS ANALISAR TODOS OS 4 SITES                              ║
╚══════════════════════════════════════════════════════════════╝

1. Crie/atualize os arquivos de config em app/configs/sites/:
   - megaleiloes.json
   - lancejudicial.json
   - portalzuk.json
   - sold.json

2. Cada config deve ter:
   - id, name, website
   - listing_url (URL raiz de imóveis)
   - method (playwright_stealth ou api_rest)
   - selectors (todos os seletores identificados)
   - pagination (tipo e padrão)
   - link_pattern (regex para identificar links de imóveis)

3. Marque enabled: true apenas para sites que você conseguiu
   analisar completamente e tem confiança nos seletores.

4. Apresente um resumo:

   | Site            | Método     | Cards | Links | Paginação | Status |
   |-----------------|------------|-------|-------|-----------|--------|
   | Mega Leilões    | playwright | ?     | ?     | ?         | ?      |
   | Lance Judicial  | playwright | ?     | ?     | ?         | ?      |
   | Portal Zukerman | playwright | ?     | ?     | ?         | ?      |
   | Sold Leilões    | api_rest   | N/A   | N/A   | ?         | ?      |

"""

# ============================================================
# INSTRUÇÕES FINAIS
# ============================================================

print("""
╔══════════════════════════════════════════════════════════════╗
║  TAREFA: ANÁLISE COM MCP WEB-BROWSER                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Esta tarefa requer uso do @web-browser MCP no Cursor.       ║
║                                                              ║
║  COLE NO CURSOR:                                             ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║                                                              ║
║  @Cursor                                                     ║
║                                                              ║
║  Use o servidor MCP @web-browser para analisar os 4 sites    ║
║  que falharam no scraping. Para CADA site:                   ║
║                                                              ║
║  1. MEGA LEILÕES                                             ║
║     Acesse: https://www.megaleiloes.com.br/imoveis           ║
║     Identifique: seletores de cards, links, paginação        ║
║     Acesse 1 imóvel e identifique: título, preço, local      ║
║                                                              ║
║  2. LANCE JUDICIAL                                           ║
║     Acesse: https://www.lancejudicial.com.br/imoveis         ║
║     Verifique se passa Cloudflare                            ║
║     Identifique: seletores de cards, links, paginação        ║
║                                                              ║
║  3. PORTAL ZUKERMAN                                          ║
║     Acesse: https://www.portalzuk.com.br/leilao-de-imoveis   ║
║     Identifique: seletores, paginação, padrão de URL         ║
║                                                              ║
║  4. SOLD LEILÕES                                             ║
║     Acesse: https://www.sold.com.br/h/imoveis                ║
║     TAMBÉM teste a API:                                      ║
║     https://offer-query.superbid.net/offers/?portalId=[2,15] ║
║     &filter=stores.id:[1161]&pageNumber=1&pageSize=10        ║
║                                                              ║
║  Para CADA site, documente:                                  ║
║  - Seletores CSS encontrados                                 ║
║  - Padrão de paginação                                       ║
║  - Regex dos links de imóveis                                ║
║                                                              ║
║  Ao final, atualize os configs em app/configs/sites/         ║
║  com os seletores corretos identificados.                    ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

print(MEGA_LEILOES)
print(LANCE_JUDICIAL)
print(PORTAL_ZUKERMAN)
print(SOLD_LEILOES)
print(RESUMO)
