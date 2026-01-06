# Investigação Lance Judicial (Grupo Lance)

## Descobertas

### 1. Redirecionamento
- **URL original:** https://www.lancejudicial.com.br
- **Redireciona para:** https://www.grupolance.com.br
- **URL de imóveis:** https://www.grupolance.com.br/imoveis

### 2. Estrutura da Página
- **Total de imóveis:** 308 itens
- **Paginação:** Página 1 de 10 (32 itens por página)
- **Método:** Paginação tradicional por URL (?page=2, ?page=3, etc.)

### 3. Seletores CSS
- **Cards de imóveis:** `.card a` ou `[class*="card"] a`
- **Links encontrados:** 162 links (32 são de imóveis individuais)
- **Outros links:** Categorias, filtros, etc.

### 4. Padrão de URL dos Imóveis
```
/imoveis/categoria/estado/cidade/nome-do-imovel-lugar-estado-numero
```

**Exemplos:**
- `/imoveis/casas/mg/belo-horizonte/casa-at-396m2-esplanada-belo-horizonte-mg-26947`
- `/imoveis/terrenos-e-lotes/sc/florianopolis/terreno-at-22759m2-corrego-grande-florianopolis-sc-27007`
- `/imoveis/apartamentos/rn/natal/apartamento-3-quartos-tirol-natal-rn-25676`

**Padrão Regex:**
```
/imoveis/[^/]+/[^/]+/[^/]+/[^/]+-\d+
```

### 5. Características
- Links terminam com número (ID do leilão)
- Estrutura: categoria / estado / cidade / descrição-número
- URLs são relativas (começam com `/imoveis/`)

## Configuração Recomendada

```python
{
    "id": "lancejudicial",
    "name": "Lance Judicial",
    "website": "https://www.grupolance.com.br",  # ATUALIZADO
    "listing_url": "/imoveis",
    "method": "playwright",
    "pagination": {
        "type": "query",
        "param": "page",
        "start": 1,
    },
    "selectors": {
        "property_link": ".card a, [class*='card'] a",  # ATUALIZADO
        "property_card": ".card, [class*='card']",
    },
    "link_patterns": [
        r"/imoveis/[^/]+/[^/]+/[^/]+/[^/]+-\d+",  # ATUALIZADO
    ],
    "max_pages": 10,
    "items_per_page": 32,
    "max_items": 308,
}
```

## Observações
- Não usa API/AJAX - dados estão no HTML inicial
- Paginação simples por query parameter `?page=2`
- 32 itens por página × 10 páginas = 320 (mas site mostra 308, então última página tem menos)

