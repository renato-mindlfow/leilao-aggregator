# 📊 RELATÓRIO: Análise dos 4 Sites que Falharam no Scraping

**Data:** 2026-01-04  
**Objetivo:** Identificar seletores CSS, padrões de URL e paginação dos 4 sites que falharam

---

## 1. MEGA LEILÕES

**URL:** https://www.megaleiloes.com.br/imoveis

### ✅ Descobertas:

- **Cards encontrados:** 1.016 elementos com classe `.two-line`
- **Seletor CSS dos cards:** `.two-line` (mas provavelmente mais específico necessário)
- **Links encontrados:** 0 (precisa mais tempo de espera - SPA React/Next.js)
- **Paginação:** Sim, encontrada

### ⚠️ Problemas Identificados:

1. **SPA (Single Page Application):** Site usa React/Next.js, conteúdo renderizado via JavaScript
2. **Tempo de carregamento:** Precisa aguardar 10-15 segundos após `domcontentloaded` para conteúdo aparecer
3. **Seletores genéricos:** `.two-line` parece ser classe de menu, não cards de imóveis
4. **Links não encontrados:** Padrão provável: `/leilao/\d+` ou `/imovel/\d+`

### 📝 Recomendações:

1. **Aumentar tempo de espera:** Aguardar 15+ segundos após navegação
2. **Scroll extensivo:** Fazer scroll múltiplas vezes para carregar lazy loading
3. **Aguardar elemento específico:** Usar `page.wait_for_selector()` para aguardar cards aparecerem
4. **Seletores alternativos:** Tentar `[class*="card-auction"]`, `[class*="property-card"]`, `[data-testid*="card"]`
5. **Padrão URL:** `/leilao/\d+` ou `/imovel/\d+`

---

## 2. LANCE JUDICIAL

**URL:** https://www.lancejudicial.com.br/imoveis

### ✅ Descobertas:

- **Cloudflare:** ❌ NÃO detectado (passou sem challenge)
- **Cards encontrados:** 695 elementos
- **Seletor CSS dos cards:** `.card-item`
- **Links encontrados:** 0 (mas paginação existe)
- **Paginação:** Sim, encontrada com `.next`

### ⚠️ Problemas Identificados:

1. **Links não aparecem no HTML inicial:** Conteúdo deve ser carregado via JavaScript/AJAX
2. **Cards genéricos:** `.card-item` pode ser de navegação, não de imóveis
3. **Precisa scroll/interação:** Possivelmente scroll infinito ou carregamento lazy

### 📝 Recomendações:

1. **Aguardar mais tempo:** 10-15 segundos após carregamento
2. **Scroll para baixo:** Fazer scroll para carregar mais conteúdo
3. **Aguardar seletor específico:** `page.wait_for_selector('.card-item:has(a[href*="/leilao/"])')`
4. **Seletores de links:** `a[href*="/leilao/"]`, `a[href*="/imovel/"]`, `a[href*="/lote/"]`
5. **Paginação:** Usar `.pagination .next` ou parâmetro `?page=2`

---

## 3. PORTAL ZUKERMAN

**URL:** https://www.portalzuk.com.br/leilao-de-imoveis

### ✅ Descobertas:

- **Cards encontrados:** 687 elementos
- **Seletor CSS dos cards:** `.card-property` ✅
- **Links encontrados:** 30 ✅
- **Seletor dos links:** `a[href*="/imovel/"]` ✅
- **Padrão URL:** `/imovel/{estado}/{cidade}/{bairro}/{id}` ✅

### 📋 Detalhes do Padrão URL:

**Exemplo real:**
```
https://www.portalzuk.com.br/imovel/mg/patrocinio/morada-do-sol/rua-edson-brasiel-436/34946-215346
```

**Estrutura:**
- `/imovel/` - prefixo fixo
- `{estado}` - código do estado (mg, sp, rj, etc.)
- `{cidade}` - nome da cidade (patrocinio, são-paulo, etc.)
- `{bairro}` - nome do bairro (morada-do-sol, etc.)
- `{rua}` - nome da rua (opcional)
- `{id}` - ID único do imóvel (ex: 34946-215346)

**Regex sugerido:**
```regex
/imovel/[^/]+/[^/]+/[^/]+/.+?/(\d+-\d+)
```

- **Paginação:** Não encontrada (possivelmente scroll infinito ou paginação diferente)

### 📝 Recomendações:

1. ✅ **Usar seletor:** `.card-property` para cards
2. ✅ **Usar seletor:** `a[href*="/imovel/"]` para links
3. ✅ **Padrão URL confirmado:** `/imovel/{estado}/{cidade}/{bairro}/{id}`
4. **Paginação:** Investigar se é scroll infinito ou parâmetro query (ex: `?page=2`)
5. **ID do imóvel:** Extrair do final da URL (formato: `\d+-\d+`)

---

## 4. SOLD LEILÕES

**URL HTML:** https://www.sold.com.br/h/imoveis  
**API:** https://offer-query.superbid.net/offers/

### ✅ Descobertas - API:

**Teste 1: Filtro de Imóveis**
- ✅ **Status:** 200 OK
- ✅ **Total:** 46.885 ofertas de imóveis
- ✅ **Retornadas:** 10 (configurável)
- ✅ **Filtro funcionando:** `product.productType.description:imoveis`

**Teste 2: Store ID Sold**
- ✅ **Status:** 200 OK  
- ✅ **Total:** 373.278 ofertas (todos os tipos)
- ✅ **Retornadas:** 10

### 📋 Estrutura da API:

**URL Base:**
```
https://offer-query.superbid.net/offers/
```

**Parâmetros:**
- `portalId=2` - ID do portal (2 = Sold)
- `filter=product.productType.description:imoveis` - Filtro para imóveis
- `pageNumber=1` - Número da página
- `pageSize=50` - Itens por página (máximo recomendado: 50)

**Headers necessários:**
```http
Accept: application/json
Origin: https://www.sold.com.br
Referer: https://www.sold.com.br/
```

### 📋 Estrutura da Resposta JSON:

```json
{
  "total": 46885,
  "start": 0,
  "limit": 10,
  "offers": [
    {
      "id": 1234567,
      "price": 130319.34,
      "priceFormatted": "R$ 130.319,34",
      "store": {
        "id": 1161,
        "name": "SOLD"
      },
      "product": {
        "shortDesc": "...",
        "thumbnailUrl": "..."
      },
      "auction": {
        "address": {
          "city": "São Paulo",
          "stateCode": "SP"
        }
      }
    }
  ]
}
```

### ⚠️ Problemas com HTML:

- **Material-UI:** Site usa Material-UI (classes Mui*)
- **SPA:** Conteúdo renderizado via JavaScript
- **Links não encontrados:** Padrão provável: `/leilao/\d+` ou `/produto/\d+`

### 📝 Recomendações:

#### ✅ **RECOMENDAÇÃO PRINCIPAL: USAR API REST**

1. ✅ **Usar API:** `https://offer-query.superbid.net/offers/`
2. ✅ **Filtro:** `product.productType.description:imoveis`
3. ✅ **Paginação:** `pageNumber` e `pageSize`
4. ✅ **Total disponível:** 46.885 imóveis
5. ✅ **Método:** HTTP GET direto (não precisa Playwright)

**Exemplo de URL completa:**
```
https://offer-query.superbid.net/offers/?portalId=2&filter=product.productType.description:imoveis&pageNumber=1&pageSize=50
```

**Alternativa (se precisar HTML):**
1. Aguardar 15+ segundos após navegação
2. Scroll extensivo
3. Seletores Material-UI: `[class*="MuiCard"]`, `[class*="MuiCardContent"]`
4. Links: `a[href*="/leilao/"]`, `a[href*="/produto/"]`

---

## 📊 RESUMO COMPARATIVO

| Site | Cards Encontrados | Links Encontrados | Método Recomendado | Status |
|------|-------------------|-------------------|-------------------|--------|
| **Mega Leilões** | 1.016 (genéricos) | 0 | Playwright + 15s espera + scroll | ⚠️ Precisa ajuste |
| **Lance Judicial** | 695 (.card-item) | 0 | Playwright + scroll + wait selector | ⚠️ Precisa ajuste |
| **Portal Zukerman** | 687 (.card-property) | 30 ✅ | Playwright + seletores corretos | ✅ Funcionando |
| **Sold Leilões** | N/A | N/A | **API REST** ✅ | ✅ Funcionando |

---

## ✅ PRÓXIMOS PASSOS

### 1. Portal Zukerman (PRIORITÁRIO)
- ✅ Seletores identificados: `.card-property` e `a[href*="/imovel/"]`
- ✅ Padrão URL confirmado: `/imovel/{estado}/{cidade}/{bairro}/{id}`
- 🔧 **Ação:** Atualizar scraper com seletores corretos

### 2. Sold Leilões (PRIORITÁRIO)
- ✅ API funcionando perfeitamente
- ✅ 46.885 imóveis disponíveis
- 🔧 **Ação:** Implementar scraper baseado em API REST (já configurado)

### 3. Mega Leilões
- ⚠️ Precisa mais tempo de espera (15+ segundos)
- ⚠️ Scroll extensivo necessário
- 🔧 **Ação:** Ajustar scraper com wait_selector e scroll

### 4. Lance Judicial
- ⚠️ Precisa scroll para carregar conteúdo
- ⚠️ Aguardar seletor específico
- 🔧 **Ação:** Ajustar scraper com scroll e wait_selector

---

**Gerado em:** 2026-01-04  
**Arquivo de dados:** `analise_sites_falhados_detalhada.json`

