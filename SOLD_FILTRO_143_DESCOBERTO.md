# Sold.com.br - Filtro Correto para 143 Imóveis Ativos

## Descoberta

A interface do Sold.com.br mostra **143 imóveis ativos**, mas a API retorna **1156** quando usamos apenas `product.productType.description:imoveis`.

## Filtro Correto

O filtro que retorna exatamente **143 imóveis** é:

```
filter=product.productType.description:imoveis;stores.id:[1161,1741]
```

### Parâmetros Completos

```python
params = {
    "portalId": "[2,15]",
    "requestOrigin": "store",  # IMPORTANTE: "store" não "marketplace"
    "locale": "pt_BR",
    "timeZoneId": "America/Sao_Paulo",
    "searchType": "opened",
    "filter": "product.productType.description:imoveis;stores.id:[1161,1741]",
    "geoLocation": "true",  # Opcional, mas presente na chamada da interface
    "pageNumber": 1,
    "pageSize": 50,
}
```

### Resultados dos Testes

| Filtro | Total | Observação |
|--------|-------|------------|
| `product.productType.description:imoveis;stores.id:[1161,1741]` | **143** | ✅ **CORRETO** |
| `product.productType.description:imoveis;auction.modalityId:[1,4,5,7];stores.id:[1161,1741]` | **142** | Muito próximo |
| `product.productType.description:imoveis` | 1156 | Sem filtro de loja |
| `product.productType.description:imoveis;auction.modalityId:[1,4,5,7]` | 1156 | Sem filtro de loja |

## Explicação

O filtro `stores.id:[1161,1741]` filtra apenas imóveis de lojas específicas que aparentemente têm apenas leilões ativos. Essas lojas (1161 e 1741) podem ser:
- Lojas que vendem apenas imóveis ativos
- Lojas filtradas pela interface para mostrar apenas leilões abertos
- Lojas principais do marketplace

## Diferenças Importantes

1. **requestOrigin**: Deve ser `"store"` (não `"marketplace"`)
2. **stores.id**: Obrigatório `[1161,1741]` para retornar 143
3. **geoLocation**: Presente na chamada da interface (pode ser opcional)

## Código Python Atualizado

```python
import requests

def get_sold_imoveis_ativos(page_number=1, page_size=50):
    """
    Extrai imóveis ATIVOS do Sold.com.br (143 imóveis).
    
    Args:
        page_number: Número da página (começa em 1)
        page_size: Itens por página
    
    Returns:
        dict: Resposta da API com 'total', 'offers', etc.
    """
    url = "https://offer-query.superbid.net/offers/"
    
    params = {
        "portalId": "[2,15]",
        "requestOrigin": "store",  # IMPORTANTE
        "locale": "pt_BR",
        "timeZoneId": "America/Sao_Paulo",
        "searchType": "opened",
        "filter": "product.productType.description:imoveis;stores.id:[1161,1741]",
        "geoLocation": "true",
        "pageNumber": page_number,
        "pageSize": page_size,
    }
    
    response = requests.get(url, params=params)
    return response.json()

# Exemplo de uso
data = get_sold_imoveis_ativos(page_number=1, page_size=50)
print(f"Total de imóveis ativos: {data.get('total')}")  # Deve ser 143
print(f"Imóveis nesta página: {len(data.get('offers', []))}")
```

## Observação

O parâmetro `searchType=opened` sozinho não filtra corretamente - retorna 1156. O filtro `stores.id:[1161,1741]` é essencial para obter apenas os 143 imóveis ativos que a interface mostra.

## Problema de Duplicados Resolvido

**Problema**: Um leilão pode ter múltiplas ofertas (lotes). Ao usar `auction.id` para construir a URL, todas as ofertas do mesmo leilão geravam a mesma URL e eram marcadas como duplicadas.

**Solução**: Priorizar `offer.id` em vez de `auction.id` para construir a URL. Cada oferta tem seu próprio `offer.id` único, gerando URLs únicas como `/produto/{offer_id}`.

**Resultado**: Agora extrai corretamente todos os 143 imóveis, sem duplicados.

