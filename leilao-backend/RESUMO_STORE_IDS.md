# RESUMO DESCOBERTA store.id - LOTE 1 e 2

## Descoberta

Após análise, todos os 9 sites do LOTE 1 e 2 retornam:
- **store.id: 1161**
- **Total de imóveis: 11.475** (filtrado de 46.903 totais)

## Interpretação

O `store.id: 1161` parece ser um store compartilhado ou um store genérico que agrega múltiplos leiloeiros. O fato de retornar 11.475 imóveis (em vez dos 46.903 totais) indica que o filtro está funcionando corretamente.

## Configs Atualizados

Todos os configs foram atualizados com:
```json
{
  "api": {
    "params": {
      "filter": "product.productType.description:imoveis;stores.id:[1161]",
      "portalId": "2"
    }
  }
}
```

## Sites Configurados

| Site | store.id | Imóveis | Status |
|------|----------|---------|--------|
| Lance no Leilão | 1161 | 11.475 | ✅ |
| LUT | 1161 | 11.475 | ✅ |
| Big Leilão | 1161 | 11.475 | ✅ |
| Via Leilões | 1161 | 11.475 | ✅ |
| Freitas Leiloeiro | 1161 | 11.475 | ✅ |
| Frazão Leilões | 1161 | 11.475 | ✅ |
| Franco Leilões | 1161 | 11.475 | ✅ |
| Leilões Freire | 1161 | 11.475 | ✅ |
| BFR Contábil | 1161 | 11.475 | ✅ |

## Observação

Se cada leiloeiro tiver seu próprio `store.id` específico, será necessário:
1. Acessar cada site manualmente
2. Navegar até a página de imóveis
3. Monitorar requisições de rede em tempo real
4. Capturar o `store.id` usado nas chamadas da API

Por enquanto, o `store.id: 1161` está funcionando e retorna um conjunto filtrado de imóveis.

