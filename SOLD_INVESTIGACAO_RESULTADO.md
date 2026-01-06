# Investigação Sold.com.br - Filtros de Imóveis

## Resumo da Investigação

### 1. Navegação e Categorias

**URL da página de imóveis:** `https://www.sold.com.br/h/imoveis`

**Categorias encontradas na página inicial:**
- **Imóveis: 143** (mostrado na seção "Navegue por categorias")
- Carro & Moto: 90
- Caminhões & Ônibus: 164
- Máquina Pesada & Agrícola: 381
- Movimentação & Transporte: 662
- Industrial, Máquina & Equipamento: 998
- Tecnologia: 132
- Móveis e Decoração: 733
- Bola, Caneta, Joia e Relógio: 2
- Sucata, Material & Resíduo: 75
- Embarcações & Aeronave: 2
- Eletrodoméstico: 36
- Material para Construção Civil: 135
- Cozinha e Restaurante: 17
- Alimento e Bebida: 10
- Oportunidade: 50
- Arte, Decoração & Colecionismo: 5
- Parte e Peça: 275

### 2. API Endpoint

**Endpoint:** `https://offer-query.superbid.net/offers/`

**Parâmetros principais:**
- `portalId`: `[2,15]`
- `requestOrigin`: `marketplace` ou `store`
- `locale`: `pt_BR` ou `undefined`
- `timeZoneId`: `America/Sao_Paulo`
- `searchType`: `opened`
- `filter`: (varia conforme necessidade)
- `pageNumber`: número da página
- `pageSize`: itens por página (geralmente 24)

### 3. Filtros Testados e Resultados

| Filtro | Total de Resultados |
|--------|---------------------|
| `product.productType.description:imoveis` | 1155-1156 |
| `product.productType.description:imoveis;auction.modalityId:[1,4,5,7]` | 1156 |
| `product.subCategory.category.description:imoveis-residenciais` | 566-567 |
| `product.subCategory.category.description:imoveis-residenciais;auction.modalityId:[1,4,5,7]` | 567 |
| `product.subCategory.category.description:imoveis-comerciais` | 131 |
| `product.subCategory.category.description:imoveis-comerciais;auction.modalityId:[1,4,5,7]` | 131 |

### 4. Observações Importantes

1. **Discrepância de números:**
   - A página inicial mostra **143 imóveis** na categoria
   - A API retorna **1155-1156** imóveis com o filtro `product.productType.description:imoveis`
   - Isso sugere que o número 143 pode ser:
     - Uma contagem visual/filtrada na interface
     - Apenas imóveis "em destaque" ou com alguma condição específica
     - Uma contagem de uma subcategoria específica

2. **Filtro mais específico:**
   - `product.subCategory.category.description:imoveis-comerciais` = 131 imóveis
   - `product.subCategory.category.description:imoveis-residenciais` = 567 imóveis
   - Total: 698 imóveis (ainda não corresponde a 142/143)

3. **Filtro de modalidade:**
   - `auction.modalityId:[1,4,5,7]` parece não afetar significativamente a contagem
   - Provavelmente representa tipos de leilão (Leilão, Tomada de preço, Mercado Balcão, etc.)

### 5. Recomendações

Para extrair apenas os **142-143 imóveis** mostrados na interface:

1. **Opção 1:** Usar o filtro mais restritivo que encontramos:
   ```
   filter=product.subCategory.category.description:imoveis-comerciais;auction.modalityId:[1,4,5,7]
   ```
   Retorna: 131 imóveis (mais próximo de 142)

2. **Opção 2:** Investigar se há filtros adicionais na interface que não estão sendo capturados:
   - Filtros de status (aberto/fechado)
   - Filtros de data
   - Filtros de loja específica
   - Filtros de canal (Corporativo, PME, Judicial)

3. **Opção 3:** Usar o filtro completo que a página usa quando acessa `/h/imoveis`:
   ```
   filter=product.productType.description:imoveis;auction.modalityId:[1,4,5,7]
   ```
   E depois filtrar no código para manter apenas os que correspondem aos critérios visuais.

### 6. Exemplo de Uso da API

```python
import requests

params = {
    "portalId": "[2,15]",
    "requestOrigin": "marketplace",
    "locale": "pt_BR",
    "timeZoneId": "America/Sao_Paulo",
    "searchType": "opened",
    "filter": "product.productType.description:imoveis;auction.modalityId:[1,4,5,7]",
    "pageNumber": 1,
    "pageSize": 24,
    "orderBy": "endDate:asc;price:desc"
}

response = requests.get("https://offer-query.superbid.net/offers/", params=params)
data = response.json()
total = data.get("total", 0)
offers = data.get("offers", [])

print(f"Total de imóveis: {total}")
```

### 7. Próximos Passos Sugeridos

1. Verificar se há filtros adicionais na interface que não foram capturados
2. Testar combinações de filtros de subcategoria (residenciais + comerciais)
3. Verificar se o número 143 corresponde a uma contagem específica de lojas ou canais
4. Comparar os resultados da API com o que aparece visualmente na página

