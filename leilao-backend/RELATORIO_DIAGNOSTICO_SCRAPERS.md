# RELATORIO - FASE 2: DIAGNOSTICO COMPLETO DOS SCRAPERS

**Data de Execucao**: 2026-01-22T22:44:08.525891

## Status dos Scrapers

- **success**: 58 leiloeiros (33926 imoveis)
- **error**: 47 leiloeiros (951 imoveis)
- **pending**: 348 leiloeiros (1993 imoveis)
- **needs_playwright**: 24 leiloeiros (1024 imoveis)
- **null**: 0 leiloeiros (0 imoveis)


## Problemas Identificados

- Success mas 0 imoveis: 33
- Scrapers com erro: 47
- Nao rodou ha 7+ dias: 108
- Nunca rodou: 347


## Classificacao de Sites

### online_cloudflare (81 sites)

- Vivaleiloes - https://www.vivaleiloes.com.br
- Unileiloes - https://www.unileiloes.com.br
- Depaulaonline - https://www.depaulaonline.com.br
- Lancetotal - https://www.lancetotal.com.br
- Moralesleiloes - https://www.moralesleiloes.com.br
- Spencerleiloes - https://www.spencerleiloes.com.br
- Webleiloes - https://www.webleiloes.com.br
- Oleiloes - https://www.oleiloes.com.br
- Santoseborinleiloes - https://www.santoseborinleiloes.com.br
- Leiloes61 - https://www.leiloes61.com.br
- ... e mais 71 sites

### offline (8 sites)

- Freitasleiloeiro - https://www.freitasleiloeiro.com.br
- Sumareleiloes - https://www.sumareleiloes.com.br
- Josequencaleiloeiro - https://www.josequencaleiloeiro.com.br
- Ten Leilões - https://www.tenleiloes.com.br
- Fabiano Ayupp Leiloeiro - https://www.fabianoayupp.com.br
- Klockner Leilões - https://www.klocknerleiloes.com.br
- Aline Marques Leiloeira - https://www.alinemarques.com.br
- Superlanceleilao - https://www.superlanceleilao.com.br

### requires_login (3 sites)

- Frazaoleiloes - https://www.frazaoleiloes.com.br
- Leilaovip - https://www.leilaovip.com.br
- Gilson Leilões - https://www.gilsonleiloes.com.br

### online_outro (1 sites)

- Anabrasilleiloes - https://www.anabrasilleiloes.com.br

### online_standard (4 sites)

- Leiloes - https://www.leiloes.com.br
- Onildo Bastos Leiloeiro - https://www.onildobastos.com.br
- GP Leilões - https://www.gpleiloes.com.br
- Baldissera Leiloeiros - https://www.baldisseraleiloeiros.com.br



## Criterios de Sucesso

- [SIM] Leiloeiros Classificados
- [SIM] Lista Categorizada
- [SIM] Priorizacao Definida


## Acoes Executadas

- [22:44:08] === 2.1 Consultando status de todos os leiloeiros ===
- [22:44:09] Status success: 58 leiloeiros, 33926 imoveis
- [22:44:10] Status error: 47 leiloeiros, 951 imoveis
- [22:44:10] Status pending: 348 leiloeiros, 1993 imoveis
- [22:44:10] Status needs_playwright: 24 leiloeiros, 1024 imoveis
- [22:44:10] Status null: 0 leiloeiros, 0 imoveis
- [22:44:10] TOTAL: 499 leiloeiros, 52989 imoveis
- [22:44:10] === 2.2 Identificando scrapers com problemas ===
- [22:44:10] Buscando scrapers com success mas 0 imoveis...
- [22:44:10] Encontrados 33 scrapers com success mas 0 imoveis
- [22:44:10] Buscando scrapers com erro...
- [22:44:10] Encontrados 47 scrapers com erro
- [22:44:10] Buscando scrapers que nao rodam ha mais de 7 dias...
- [22:44:11] Encontrados 108 scrapers sem rodar ha 7+ dias
- [22:44:11] Buscando scrapers que nunca rodaram...
- [22:44:11] Encontrados 347 scrapers que nunca rodaram
- [22:44:11] === 2.3 Classificando sites por tipo ===
- [22:44:11] Classificando 97 sites...
- [22:44:11]   Verificando batch 1 (10 sites)...
- [22:44:29]   Verificando batch 2 (10 sites)...
- [22:44:44]   Verificando batch 3 (10 sites)...
- [22:44:56]   Verificando batch 4 (10 sites)...
- [22:45:12]   Verificando batch 5 (10 sites)...
- [22:45:26]   Verificando batch 6 (10 sites)...
- [22:45:42]   Verificando batch 7 (10 sites)...
- [22:45:53]   Verificando batch 8 (10 sites)...
- [22:46:02]   Verificando batch 9 (10 sites)...
- [22:46:14]   Verificando batch 10 (7 sites)...
- [22:46:22] 
RESUMO DA CLASSIFICACAO:
- [22:46:22]   online_cloudflare: 81 sites
- [22:46:22]   offline: 8 sites
- [22:46:22]   requires_login: 3 sites
- [22:46:22]   online_outro: 1 sites
- [22:46:22]   online_standard: 4 sites
- [22:46:22] === Definindo priorizacao ===
- [22:46:22] Prioridade ALTA: 4 sites
- [22:46:22] Prioridade MEDIA: 81 sites
- [22:46:22] Prioridade BAIXA: 3 sites
- [22:46:22] Desabilitar: 9 sites
- [22:46:22] Verificando criterios de sucesso...
- [22:46:22] Criterios de sucesso verificados
- [22:46:22] Gerando relatorio RELATORIO_DIAGNOSTICO_SCRAPERS.md


## Conclusao

A FASE 2 foi executada com sucesso. Todos os scrapers foram diagnosticados e classificados.

**Proxima Fase**: FASE 3 - Corrigir Scrapers com Erro

## Arquivos Gerados

- `problemas_scrapers.json` - Detalhes de todos os problemas
- `classificacao_sites.json` - Classificacao completa de sites
- `priorizacao_scrapers.json` - Ordem de prioridade para correcao
