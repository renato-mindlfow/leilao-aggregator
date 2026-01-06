# 🔍 RESULTADO: Investigação Lance Judicial

**Data:** 2026-01-05  
**Objetivo:** Descobrir a estrutura real do site e corrigir o scraper

---

## ✅ DESCOBERTAS

### 1. Redirecionamento
- **URL original:** `https://www.lancejudicial.com.br`
- **Redireciona para:** `https://www.grupolance.com.br`
- **URL final de imóveis:** `https://www.grupolance.com.br/imoveis`

### 2. Estrutura da Página
- **Total de imóveis:** **308 itens**
- **Paginação:** Página 1 de 10 (32 itens por página)
- **Método:** Paginação tradicional por query parameter (`?page=2`, `?page=3`, etc.)

### 3. Seletores CSS
- **Cards de imóveis:** `.card a` ou `[class*="card"] a`
- **Links encontrados:** 162 links (32 são de imóveis individuais)
- **Outros links:** Categorias, filtros, etc.

### 4. Padrão de URL dos Imóveis

**Estrutura:**
```
/imoveis/categoria/estado/cidade/nome-do-imovel-lugar-estado-numero
```

**Exemplos reais:**
- `/imoveis/casas/mg/belo-horizonte/casa-at-396m2-esplanada-belo-horizonte-mg-26947`
- `/imoveis/terrenos-e-lotes/sc/florianopolis/terreno-at-22759m2-corrego-grande-florianopolis-sc-27007`
- `/imoveis/apartamentos/rn/natal/apartamento-3-quartos-tirol-natal-rn-25676`
- `/imoveis/imoveis-industriais/rj/rio-de-janeiro/imovel-industrial-at-4100m2-tomas-coelho-rio-de-janeiro-rj-26916`

**Padrão Regex:**
```
/imoveis/[^/]+/[^/]+/[^/]+/[^/]+-\d+
```

### 5. Características
- ✅ Links terminam com número (ID do leilão)
- ✅ Estrutura: categoria / estado / cidade / descrição-número
- ✅ URLs são relativas (começam com `/imoveis/`)
- ✅ Não usa API/AJAX - dados estão no HTML inicial
- ✅ Paginação simples por query parameter `?page=2`

---

## 🔧 CONFIGURAÇÃO ATUALIZADA

```python
{
    "id": "lancejudicial",
    "name": "Lance Judicial",
    "website": "https://www.grupolance.com.br",  # ✅ ATUALIZADO
    "listing_url": "/imoveis",
    "method": "playwright",
    "pagination": {
        "type": "query",
        "param": "page",
        "start": 1,
    },
    "selectors": {
        "property_link": ".card a, [class*='card'] a",  # ✅ ATUALIZADO
        "property_card": ".card, [class*='card']",
    },
    "link_patterns": [
        r"/imoveis/[^/]+/[^/]+/[^/]+/[^/]+-\d+",  # ✅ ATUALIZADO
    ],
    "max_pages": 10,  # ✅ ATUALIZADO (308 itens / 32 por página)
    "items_per_page": 32,  # ✅ ATUALIZADO
    "max_items": 308,  # ✅ ATUALIZADO
}
```

---

## 📊 RESUMO

| Item | Valor |
|------|-------|
| **URL correta** | `https://www.grupolance.com.br/imoveis` |
| **Total de imóveis** | 308 |
| **Itens por página** | 32 |
| **Total de páginas** | 10 |
| **Seletor de links** | `.card a` |
| **Padrão de URL** | `/imoveis/[categoria]/[estado]/[cidade]/[nome]-[número]` |
| **Método de paginação** | Query parameter `?page=N` |

---

## ✅ PRÓXIMOS PASSOS

1. ✅ Configuração atualizada no código
2. ⏳ Testar scraping com nova configuração
3. ⏳ Verificar se extrai os 308 imóveis corretamente

