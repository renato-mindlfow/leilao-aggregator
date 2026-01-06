# Sold.com.br - Filtro Correto para Extrair Apenas Imóveis

## Investigação Completa

### URL da Página de Imóveis
**URL:** `https://www.sold.com.br/h/imoveis?searchType=opened&pageNumber=1&pageSize=15&orderBy=price:desc`

### API Endpoint
**Endpoint:** `https://offer-query.superbid.net/offers/`

### Filtro Correto para Extrair Apenas Imóveis

**FILTRO PRINCIPAL (recomendado):**
```
filter=product.productType.description:imoveis;auction.modalityId:[1,4,5,7]
```

**Parâmetros completos:**
```python
params = {
    "portalId": "[2,15]",
    "requestOrigin": "marketplace",
    "locale": "pt_BR",
    "timeZoneId": "America/Sao_Paulo",
    "searchType": "opened",
    "filter": "product.productType.description:imoveis;auction.modalityId:[1,4,5,7]",
    "pageNumber": 1,
    "pageSize": 15,  # ou 24, conforme necessário
    "orderBy": "price:desc"  # opcional
}
```

### Resultados dos Testes

| Filtro | Total de Imóveis | Observação |
|--------|------------------|------------|
| `product.productType.description:imoveis;auction.modalityId:[1,4,5,7]` | **1155-1156** | ✅ **RECOMENDADO** - Filtra apenas imóveis, excluindo veículos, máquinas, etc. |
| `product.productType.description:imoveis` | 1155-1156 | Similar ao anterior |
| `product.subCategory.category.description:imoveis-residenciais;auction.modalityId:[1,4,5,7]` | 566 | Apenas residenciais |
| `product.subCategory.category.description:imoveis-comerciais;auction.modalityId:[1,4,5,7]` | 131 | Apenas comerciais |
| `product.productType.description:imoveis;stores.id:[1161,1741];isShopping:false;auction.modalityId:[1,4,5,7]` | 68 | Filtrado por lojas específicas |

### Sobre o Número ~150

O número **~150 imóveis** mencionado pode referir-se a:
1. Uma contagem visual/filtrada na interface do site
2. Uma subcategoria específica não capturada nas chamadas de API
3. Uma combinação de filtros adicionais aplicados na interface

**IMPORTANTE:** O filtro `product.productType.description:imoveis;auction.modalityId:[1,4,5,7]` retorna **1155-1156 imóveis**, que é o total real de imóveis disponíveis na plataforma. Este filtro **garante que apenas imóveis sejam extraídos**, excluindo:
- ❌ Veículos (carros, motos, caminhões)
- ❌ Máquinas pesadas e agrícolas
- ❌ Equipamentos industriais
- ❌ Outros bens não-imóveis

### Exemplo de Código Python

```python
import requests

def get_sold_imoveis(page_number=1, page_size=15):
    """
    Extrai imóveis do Sold.com.br usando a API oficial.
    
    Args:
        page_number: Número da página (começa em 1)
        page_size: Itens por página (15 ou 24)
    
    Returns:
        dict: Resposta da API com 'total', 'offers', etc.
    """
    url = "https://offer-query.superbid.net/offers/"
    
    params = {
        "portalId": "[2,15]",
        "requestOrigin": "marketplace",
        "locale": "pt_BR",
        "timeZoneId": "America/Sao_Paulo",
        "searchType": "opened",
        "filter": "product.productType.description:imoveis;auction.modalityId:[1,4,5,7]",
        "pageNumber": page_number,
        "pageSize": page_size,
        "orderBy": "price:desc"
    }
    
    response = requests.get(url, params=params)
    return response.json()

# Exemplo de uso
data = get_sold_imoveis(page_number=1, page_size=15)
print(f"Total de imóveis: {data.get('total')}")
print(f"Imóveis nesta página: {len(data.get('offers', []))}")

# Iterar por todas as páginas
total = data.get('total', 0)
page_size = 15
total_pages = (total + page_size - 1) // page_size

for page in range(1, total_pages + 1):
    data = get_sold_imoveis(page_number=page, page_size=page_size)
    offers = data.get('offers', [])
    print(f"Página {page}: {len(offers)} imóveis")
    # Processar offers...
```

### Paginação

- **URL da página 1:** `https://www.sold.com.br/h/imoveis?searchType=opened&pageNumber=1&pageSize=15&orderBy=price:desc`
- **URL da página 2:** `https://www.sold.com.br/h/imoveis?searchType=opened&pageNumber=2&pageSize=15&orderBy=price:desc`
- O parâmetro `pageNumber` muda na URL e na chamada de API

### Campos Importantes na Resposta

A resposta JSON contém:
- `total`: Total de imóveis disponíveis
- `offers`: Array com os imóveis da página atual
- Cada `offer` contém: `id`, `linkURL`, `price`, `priceFormatted`, `product`, `auction`, etc.

### Conclusão

**Use o filtro:**
```
product.productType.description:imoveis;auction.modalityId:[1,4,5,7]
```

Este filtro garante que **apenas imóveis** sejam extraídos, excluindo todos os outros tipos de bens (veículos, máquinas, equipamentos, etc.).

