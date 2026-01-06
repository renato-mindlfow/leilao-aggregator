# RELATÓRIO DE TESTE: 5 SITES DO TIER 3

**Data:** 2026-01-05 20:22:26

## Resumo Executivo

| Site | Esperado | Extraído | Status | Páginas |
|------|----------|-----------|--------|---------|
| Super Leilões | ~527 | 40 | SUCESSO | 1 |
| Leilões Judiciais | ~270 | 40 | SUCESSO | 1 |
| Leilões Online | ~167 | 0 | FALHA | 0 |
| Zukerman | ~127 | 36 | SUCESSO | 1 |
| Leilo Master | ~1 | 1 | SUCESSO | 1 |

| **TOTAL** | **~1.092** | **117** | | |

## Detalhes por Site

### Super Leilões

- **Website:** https://www.superleiloes.com.br
- **URL de Listagem:** /imovel
- **Esperado:** ~527 imóveis
- **Extraído:** 40 imóveis
- **Páginas:** 1
- **Status:** SUCESSO
- **Início:** 2026-01-05T20:17:31.076038
- **Fim:** 2026-01-05T20:18:33.260323

**Exemplos de Imóveis:**

1. ****
   - Preço: R$ 182.800
   - Localização: Galpão

Zona Oeste
São Paulo/SP
   - URL: https://www.superleiloes.com.br/imovel/alugar/galpao-em-condominio-logistico-nova-santa-rita-rs/3sb-parque-logistico/35004414

1. ****
   - Preço: R$ 182.800
   - Localização: Galpão

Zona Oeste
São Paulo/SP
   - URL: https://www.superleiloes.com.br/imovel/alugar/galpao-em-osasco-sp/35007392

1. ****
   - Preço: R$ 182.800
   - Localização: Galpão

Zona Oeste
São Paulo/SP
   - URL: https://www.superleiloes.com.br/imovel/alugar/galpao-em-condominio-logistico-seropedica-rj/xplog-seropedica/32857520

### Leilões Judiciais

- **Website:** https://www.leiloesjudiciais.com.br
- **URL de Listagem:** /imoveis
- **Esperado:** ~270 imóveis
- **Extraído:** 40 imóveis
- **Páginas:** 1
- **Status:** SUCESSO
- **Início:** 2026-01-05T20:18:38.344750
- **Fim:** 2026-01-05T20:19:53.920157

**Exemplos de Imóveis:**

1. **LEILÃO PÚBLICO DE VENDA DE IMÓVEIS - CONSOLIDAÇÃO DE PROPRIEDADE - CAIXA ECONÔMICA FEDERAL - Nº 0080/0225**
   - Preço: R$ 1.034.086,01
   - Localização: Várzea Grande/MT
   - URL: https://www.leiloesjudiciais.com.br/lote/33609/115897

1. **JUSTIÇA ESTADUAL DE GOIATUBA/GO - 2ª VARA CÍVEL**
   - Preço: R$ 8.790.000,00
   - Localização: JUSTIÇA ESTADUAL DE GOIATUBA/GO
   - URL: https://www.leiloesjudiciais.com.br/lote/33729/116544

1. **VENDA DE IMÓVEIS RESIDENCIAIS E COMERCIAIS DE GRANDE EMPRESA/BANCO**
   - Preço: R$ 40.000.000,00
   - Localização: São Paulo/SP
   - URL: https://www.leiloesjudiciais.com.br/lote/33075/112085

### Leilões Online

- **Website:** https://www.leiloesonline.com.br
- **URL de Listagem:** /imoveis
- **Esperado:** ~167 imóveis
- **Extraído:** 0 imóveis
- **Páginas:** 0
- **Status:** FALHA
- **Início:** 2026-01-05T20:19:59.007025
- **Fim:** None

**Erros:**
- Page.goto: Timeout 30000ms exceeded.
Call log:
  - navigating to "https://www.leiloesonline.com.br/imoveis", waiting until "domcontentloaded"


### Zukerman

- **Website:** https://www.zukerman.com.br
- **URL de Listagem:** /imoveis
- **Esperado:** ~127 imóveis
- **Extraído:** 36 imóveis
- **Páginas:** 1
- **Status:** SUCESSO
- **Início:** 2026-01-05T20:20:38.225939
- **Fim:** 2026-01-05T20:21:51.690040

**Exemplos de Imóveis:**

1. **Casa à venda em leilão**
   - Preço: R$ 547.200,00
   - Localização: Porto Alegre/RS
   - URL: https://www.portalzuk.com.br/imovel/rs/porto-alegre/hipica/rua-corticeira-551/35025-215975

1. **Casa à venda em leilão**
   - Preço: R$ 540.000,00
   - Localização: Porto Alegre/RS
   - URL: https://www.portalzuk.com.br/imovel/rs/porto-alegre/campo-novo/rua-hortencio-rodrigues-barbosa-54/35025-215877

1. **Casa à venda em leilão**
   - Preço: R$ 487.160,00
   - Localização: Porto Alegre/RS
   - URL: https://www.portalzuk.com.br/imovel/rs/porto-alegre/teresopolis/rua-otavio-faria-53/35025-215938

### Leilo Master

- **Website:** https://www.leilomaster.com.br
- **URL de Listagem:** /imoveis
- **Esperado:** ~1 imóveis
- **Extraído:** 1 imóveis
- **Páginas:** 1
- **Status:** SUCESSO
- **Início:** 2026-01-05T20:21:56.800184
- **Fim:** 2026-01-05T20:22:21.539396

**Exemplos de Imóveis:**

1. **Oportunidades em Leilão**
   - Preço: R$ 0
   - Localização: os
close
Cidade
remove
Goiânia/GO
   - URL: https://www.leilomaster.com.br/leilao


## Arquivos Gerados

- `resultado_superleiles.json`
- `resultado_leilesjudiciais.json`
- `resultado_leilesonline.json`
- `resultado_zukerman.json`
- `resultado_leilomaster.json`

## Conclusão

Total de imóveis extraídos: **117** de ~1.092 esperados.

Sites com sucesso: **4/5**
