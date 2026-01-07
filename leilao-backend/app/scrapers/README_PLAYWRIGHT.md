# Scrapers Playwright para Sites com Cloudflare

## 📋 Visão Geral

Esta implementação adiciona suporte a scraping de sites de leilões que utilizam proteção Cloudflare/anti-bot através do Playwright com técnicas de stealth mode.

## 🎯 Leiloeiros Implementados

### ✅ Funcionando
- **Flex Leilões** (`flexleiloes_playwright.py`) - ✅ TESTADO E FUNCIONANDO
  - URL: https://www.flexleiloes.com.br/imoveis
  - Extrai: título, preço, localização, imagem, categoria
  - Status: **Pronto para produção**

### 🚧 Em Desenvolvimento
- **Sold Leilões** (`sold_playwright.py`) - 🚧 INFRAESTRUTURA PRONTA
  - URL: https://www.sold.com.br/leiloes
  - Desafio: SPA React com carregamento dinâmico via API
  - Próximo passo: Identificar e usar API REST diretamente
  
- **Lance Judicial** (`lancejudicial_playwright.py`) - 🚧 INFRAESTRUTURA PRONTA
  - URL: https://www.grupolance.com.br/buscar?category=imoveis
  - Desafio: Seletores CSS precisam ser ajustados
  - Próximo passo: Debug visual para identificar seletores corretos

## 🏗️ Arquitetura

### Base Class: `PlaywrightBaseScraper`
Classe base em `playwright_base.py` com funcionalidades:
- ✅ Configuração de browser com stealth mode
- ✅ Bypass automático de Cloudflare
- ✅ Scroll automático para lazy-loading
- ✅ Parse de preços em formato brasileiro
- ✅ Extração de estado/cidade
- ✅ Determinação automática de categoria
- ✅ Suporte a execução assíncrona e síncrona

### Configurações de Stealth
```python
- User-Agent real (Chrome 120)
- Remoção de indicadores de automação (webdriver)
- Headers HTTP realistas
- Locale e timezone brasileiros
- Desabilita features que expõem automação
```

## 📦 Instalação

```bash
# Instalar Playwright
pip install playwright

# Instalar browser Chromium
playwright install chromium
```

## 🧪 Testes

### Teste Rápido
```bash
cd leilao-backend/scripts
python test_playwright_scrapers.py
```

### Debug de Sites Problemáticos
```bash
cd leilao-backend/scripts
python debug_sold_lance.py
```

## 📊 Resultados dos Testes

```
✅ Flex Leilões: 5 propriedades extraídas
   - Título, preço, localização, imagem funcionando
   - Tempo médio: ~15 segundos

❌ Sold Leilões: 0 propriedades (SPA/API issue)
❌ Lance Judicial: 0 propriedades (seletores incorretos)
```

## 🔧 Como Adicionar Novo Leiloeiro

1. Criar novo arquivo em `app/scrapers/nomeleiloeiro_playwright.py`
2. Herdar de `PlaywrightBaseScraper`
3. Definir constantes:
   ```python
   BASE_URL = "https://..."
   AUCTIONEER_ID = "id_unico"
   AUCTIONEER_NAME = "Nome do Leiloeiro"
   LISTING_URL = "https://.../listagem"
   ```
4. Definir `SELECTORS` dict com seletores CSS
5. Implementar `_extract_property_data(card)` method
6. Adicionar ao `test_playwright_scrapers.py`

## 🐛 Debug

### Problemas Comuns

**Site não carrega:**
- Aumentar timeout em `goto()`
- Verificar se Cloudflare está bloqueando
- Testar com `headless=False` para debug visual

**Não encontra elementos:**
- Verificar se é SPA (aguardar mais tempo)
- Usar `debug_site_structure.py` para analisar HTML
- Testar seletores CSS no DevTools do browser

**Cloudflare Challenge:**
- Aguardar mais tempo em `_wait_for_cloudflare()`
- Verificar se stealth está configurado corretamente
- Considerar usar proxy residencial

## 📁 Arquivos

```
app/scrapers/
├── playwright_base.py              # Classe base
├── flexleiloes_playwright.py       # Flex Leilões ✅
├── sold_playwright.py              # Sold Leilões 🚧
├── lancejudicial_playwright.py     # Lance Judicial 🚧
└── README_PLAYWRIGHT.md            # Este arquivo

scripts/
├── test_playwright_scrapers.py     # Testes automatizados
├── debug_site_structure.py         # Debug de estrutura HTML
└── debug_sold_lance.py             # Debug visual avançado
```

## 🚀 Próximos Passos

1. **Sold Leilões:**
   - [ ] Identificar API endpoint
   - [ ] Implementar client HTTP direto
   - [ ] Ou aguardar seletores específicos carregarem

2. **Lance Judicial:**
   - [ ] Executar debug visual
   - [ ] Identificar seletores corretos
   - [ ] Implementar extração de dados

3. **Melhorias Gerais:**
   - [ ] Adicionar retry com backoff exponencial
   - [ ] Implementar cache de sessão
   - [ ] Adicionar métricas de performance
   - [ ] Suporte a múltiplas páginas de listagem

## 📝 Notas Técnicas

- **Performance:** Playwright é mais lento que requests/BeautifulSoup mas necessário para sites com Cloudflare
- **Recursos:** Cada browser consome ~100-200MB RAM
- **Timeout:** Sites podem levar 10-30 segundos para carregar completamente
- **Manutenção:** Seletores CSS podem mudar quando sites são atualizados

## 🔗 Referências

- [Playwright Python Docs](https://playwright.dev/python/)
- [Cloudflare Bot Management](https://www.cloudflare.com/products/bot-management/)
- [Web Scraping Best Practices](https://www.scraperapi.com/blog/web-scraping-best-practices/)

