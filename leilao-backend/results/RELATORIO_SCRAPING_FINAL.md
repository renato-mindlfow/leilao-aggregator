# RELATÓRIO DE SCRAPING FINAL - LEILOHUB

**Data de Execução:** 2026-01-05  
**Total de Imóveis Extraídos:** 9,221  
**Fontes Ativas:** 4/6  
**Taxa de Sucesso:** 66.7%

---

## 📊 RESULTADOS POR FONTE

| Fonte | Esperado | Extraído | Status | Arquivo |
|-------|----------|----------|--------|---------|
| Superbid Agregado | ~11.475 | 7,812 | ✅ | resultado_superbid_agregado.json |
| Portal Zukerman | ~949 | 947 | ✅ | resultado_portal_zuk.json |
| Mega Leilões | ~650 | 0 | ❌ | resultado_mega_leiloes.json |
| Lance Judicial | ~308 | 312 | ✅ | resultado_lance_judicial.json |
| Sold Leilões | ~143 | 150 | ✅ | resultado_sold.json |
| Sodré Santoro | ~28 | 0 | ❌ | resultado_sodre_santoro.json |

| **TOTAL** | **~13,553** | **9,221** | | |

---

## 📝 EXEMPLOS DE IMÓVEIS

### Superbid Agregado

1. **Apto 99,22m², 1 Vaga, Ocupado - no Bairro Figueira em Gaspar**
   - Preço: R$ 419.485,30
   - Localização: Gaspar - SC, Santa Catarina
   - URL: https://www.superbid.net/produto/2504932...

2. **Cota de Consórcio NÃO CONTEMPLADA nº 620 do Grupo nº 743, ad**
   - Preço: R$ 7.899,00
   - Localização: São Paulo - SP, São Paulo
   - URL: https://www.superbid.net/produto/2477555...

3. **Apto. 71m² no Rio do Ouro, São Gonçalo/RJ**
   - Preço: R$ 150.426,95
   - Localização: São Gonçalo - RJ, Rio de Janeiro
   - URL: https://www.superbid.net/produto/2505788...

### Portal Zukerman

1. ****
   - Preço: 
   - Localização: 
   - URL: https://www.portalzuk.com.br/imovel/pr/sao-mateus-do-sul/loteamento-vila-faty/ru...

2. ****
   - Preço: 
   - Localização: 
   - URL: https://www.portalzuk.com.br/imovel/rj/rio-de-janeiro/campo-grande/estrada-iaraq...

3. ****
   - Preço: 
   - Localização: 
   - URL: https://www.portalzuk.com.br/imovel/ms/campo-grande/jardim-colibri/rua-carrica-2...

### Lance Judicial

1. ****
   - Preço: 
   - Localização: 
   - URL: https://www.grupolance.com.br/imoveis/casas/sp/caraguatatuba/casa-at-400m2-sumar...

2. ****
   - Preço: 
   - Localização: 
   - URL: https://www.grupolance.com.br/imoveis/casas/sp/sao-carlos/imovel-residencial-138...

3. ****
   - Preço: 
   - Localização: 
   - URL: https://www.grupolance.com.br/imoveis/casas/sp/santa-cruz-do-rio-pardo/casa-320m...

### Sold Leilões

1. **Apto 99,22m², 1 Vaga, Ocupado - no Bairro Figueira em Gaspar**
   - Preço: R$ 419.485,30
   - Localização: Gaspar - SC, Santa Catarina
   - URL: https://www.sold.com.br/produto/2504932...

2. **Cota de Consórcio NÃO CONTEMPLADA nº 620 do Grupo nº 743, ad**
   - Preço: R$ 7.899,00
   - Localização: São Paulo - SP, São Paulo
   - URL: https://www.sold.com.br/produto/2477555...

3. **Apto. 71m² no Rio do Ouro, São Gonçalo/RJ**
   - Preço: R$ 150.426,95
   - Localização: São Gonçalo - RJ, Rio de Janeiro
   - URL: https://www.sold.com.br/produto/2505788...

---

## ⚠️ ERROS ENCONTRADOS

- superbid_agregado: Página 201: Server error '503 Service Unavailable' for url 'https://offer-query.superbid.net/offers/?portalId=2&filter=product.productType.description%3Aimoveis%3Bstores.id%3A%5B1161%5D&requestOrigin=store&pageSize=50&pageNumber=201'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503

---

## 📁 ARQUIVOS GERADOS

- `scraping_consolidado_final.json` - Dados consolidados
- `resultado_superbid_agregado.json` - Superbid Agregado
- `resultado_portal_zuk.json` - Portal Zukerman
- `resultado_mega_leiloes.json` - Mega Leilões
- `resultado_lance_judicial.json` - Lance Judicial
- `resultado_sold.json` - Sold Leilões
- `resultado_sodre_santoro.json` - Sodré Santoro
