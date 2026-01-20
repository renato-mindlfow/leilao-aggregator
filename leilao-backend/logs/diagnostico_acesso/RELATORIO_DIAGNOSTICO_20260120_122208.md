# 🔬 RELATÓRIO DE DIAGNÓSTICO - ACESSO AOS LEILOEIROS

**Data**: 20/01/2026 12:22
**Sites Testados**: 20
**Métodos**: HTTP Simples, HTTP+Headers, Playwright (3 modos), CURL

---

## 📊 RESUMO POR DIAGNÓSTICO

| Diagnóstico | Qtd | % | Recomendação |
|-------------|-----|---|--------------|
| CLOUDFLARE_BYPASS_OK | 9 | 45.0% | Cloudflare detectado mas Playwright Stealth funcio... |
| CLOUDFLARE_BLOQUEIO | 5 | 25.0% | Cloudflare bloqueando - considerar proxy residenci... |
| REQUER_JAVASCRIPT | 2 | 10.0% | Site requer JavaScript - usar Playwright |
| CAPTCHA_BLOQUEIO | 2 | 10.0% | Site requer CAPTCHA - considerar serviço de resolu... |
| ANTI_BOT_FORTE | 1 | 5.0% | Anti-bot forte - considerar undetected-chromedrive... |
| PARCIAL_4_METODOS | 1 | 5.0% | Funciona com: HTTP_SIMPLES, HTTP_HEADERS_BROWSER, ... |

---

## 📋 DETALHES POR SITE

### Megaleiloes

- **URL**: https://www.megaleiloes.com.br/imoveis
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 8116ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 3518ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 23001ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 16634ms | - |
| CURL | ✅ | 200 | 673ms | - |

### Portalzuk

- **URL**: https://www.portalzuk.com.br/leilao-de-imoveis
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 2862ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 2314ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ✅ | 200 | 8733ms | - |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 8765ms | - |
| CURL | ✅ | 200 | 517ms | - |

### Sold

- **URL**: https://www.sold.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BLOQUEIO`
- **Recomendação**: Cloudflare bloqueando - considerar proxy residencial

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 1355ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1444ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 7214ms | CAPTCHA |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 11646ms | CAPTCHA |
| CURL | ✅ | 200 | 535ms | - |

### Frazaoleiloes

- **URL**: https://www.frazaoleiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `REQUER_JAVASCRIPT`
- **Recomendação**: Site requer JavaScript - usar Playwright

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ❌ | 403 | 1226ms | HTTP 403 |
| HTTP_HEADERS_BROWSER | ✅ | 200 | 1831ms | - |
| PLAYWRIGHT_HEADLESS | ✅ | 200 | 8693ms | - |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 8768ms | - |
| CURL | ✅ | 200 | 3301ms | - |

### Lancejudicial

- **URL**: https://www.lancejudicial.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 3357ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 2572ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 8797ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 9529ms | - |
| CURL | ✅ | 200 | 1294ms | - |

### Leiloes

- **URL**: https://www.leiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `ANTI_BOT_FORTE`
- **Recomendação**: Anti-bot forte - considerar undetected-chromedriver

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 2351ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1409ms | BOT_DETECTION |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 10902ms | BROWSER_CHECK |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 14022ms | BROWSER_CHECK |
| CURL | ✅ | 200 | 642ms | - |

### Milanleiloes

- **URL**: https://www.milanleiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BLOQUEIO`
- **Recomendação**: Cloudflare bloqueando - considerar proxy residencial

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ❌ | 403 | 923ms | HTTP 403 |
| HTTP_HEADERS_BROWSER | ❌ | 403 | 1306ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 403 | 5933ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ❌ | 403 | 8948ms | CLOUDFLARE_CHALLENGE |
| PLAYWRIGHT_HEADED | ❌ | 403 | 15508ms | SEM_CONTEUDO |
| CURL | ❌ | 403 | 196ms | HTTP 403 |

### Bestleiloes

- **URL**: https://www.bestleiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ❌ | 410 | 1824ms | HTTP 410 |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 2927ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 8304ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 9689ms | CLOUDFLARE_CHALLENGE |
| PLAYWRIGHT_HEADED | ✅ | 200 | 9883ms | - |
| CURL | ✅ | 200 | 1507ms | - |

### Francoleiloes

- **URL**: https://www.francoleiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BLOQUEIO`
- **Recomendação**: Cloudflare bloqueando - considerar proxy residencial

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 1550ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1347ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 7102ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 8041ms | CLOUDFLARE_CHALLENGE |
| CURL | ✅ | 200 | 214ms | - |

### Freitasleiloeiro

- **URL**: https://www.freitasleiloeiro.com.br
- **DNS**: ✅
- **SSL**: ⚠️
- **Diagnóstico**: `REQUER_JAVASCRIPT`
- **Recomendação**: Site requer JavaScript - usar Playwright

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ❌ | - | 1131ms | [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1077) |
| HTTP_HEADERS_BROWSER | ❌ | - | 1093ms | [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1077) |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 7511ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 9236ms | - |
| CURL | ✅ | 200 | 823ms | - |

### Sodresantoro

- **URL**: https://www.sodresantoro.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CAPTCHA_BLOQUEIO`
- **Recomendação**: Site requer CAPTCHA - considerar serviço de resolução

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ❌ | 403 | 1272ms | HTTP 403 |
| HTTP_HEADERS_BROWSER | ✅ | 200 | 1307ms | - |
| PLAYWRIGHT_HEADLESS | ❌ | 403 | 4709ms | - |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 6468ms | CAPTCHA |
| CURL | ❌ | 403 | 2862ms | HTTP 403 |

### Biasileiloes

- **URL**: https://www.biasileiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CAPTCHA_BLOQUEIO`
- **Recomendação**: Site requer CAPTCHA - considerar serviço de resolução

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ❌ | 403 | 1178ms | HTTP 403 |
| HTTP_HEADERS_BROWSER | ✅ | 200 | 1607ms | - |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 7675ms | CAPTCHA |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 8599ms | CAPTCHA |
| CURL | ✅ | 200 | 719ms | - |

### Leilaobrasil

- **URL**: https://www.leilaobrasil.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 2870ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 2626ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 10351ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 11311ms | - |
| CURL | ✅ | 200 | 1696ms | - |

### Allianceleiloes

- **URL**: https://www.allianceleiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 1614ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1431ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 9504ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 9133ms | - |
| CURL | ✅ | 200 | 457ms | - |

### Depaulaonline

- **URL**: https://www.depaulaonline.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 2432ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 2290ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 10292ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 10603ms | - |
| CURL | ✅ | 200 | 929ms | - |

### Superbid

- **URL**: https://www.superbid.net
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BLOQUEIO`
- **Recomendação**: Cloudflare bloqueando - considerar proxy residencial

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 1950ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1531ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 10853ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 12588ms | CLOUDFLARE_CHALLENGE |
| CURL | ✅ | 200 | 938ms | - |

### Vivaleiloes

- **URL**: https://www.vivaleiloes.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BLOQUEIO`
- **Recomendação**: Cloudflare bloqueando - considerar proxy residencial

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 1179ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1333ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 7138ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ❌ | 200 | 8302ms | CLOUDFLARE_CHALLENGE |
| CURL | ✅ | 200 | 180ms | - |

### Hastavip

- **URL**: https://www.hastavip.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `PARCIAL_4_METODOS`
- **Recomendação**: Funciona com: HTTP_SIMPLES, HTTP_HEADERS_BROWSER, PLAYWRIGHT_HEADLESS, PLAYWRIGHT_STEALTH

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 8175ms | - |
| HTTP_HEADERS_BROWSER | ✅ | 200 | 8921ms | - |
| PLAYWRIGHT_HEADLESS | ✅ | 200 | 14757ms | - |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 14494ms | - |
| CURL | ❌ | - | 11067ms | Curl falhou |

### Leje

- **URL**: https://www.leje.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 1033ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 1119ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ❌ | 200 | 11982ms | CLOUDFLARE |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 12724ms | - |
| CURL | ✅ | 200 | 395ms | - |

### Lut

- **URL**: https://www.lut.com.br
- **DNS**: ✅
- **SSL**: ✅
- **Diagnóstico**: `CLOUDFLARE_BYPASS_OK`
- **Recomendação**: Cloudflare detectado mas Playwright Stealth funciona

| Método | Sucesso | Status | Tempo | Erro |
|--------|---------|--------|-------|------|
| HTTP_SIMPLES | ✅ | 200 | 3122ms | - |
| HTTP_HEADERS_BROWSER | ❌ | 200 | 2240ms | CLOUDFLARE |
| PLAYWRIGHT_HEADLESS | ✅ | 200 | 10678ms | - |
| PLAYWRIGHT_STEALTH | ✅ | 200 | 9638ms | - |
| CURL | ✅ | 200 | 459ms | - |

