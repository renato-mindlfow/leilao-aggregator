# LeiloHub Aggregator - API de Leitura

## IMPORTANTE

Este servico e **SOMENTE LEITURA**.

Para inserir/atualizar dados no banco, use o **leilohub-scraper-final**
que possui validacao completa de qualidade.

## Arquitetura

```
[leilohub-scraper-final] --INSERT--> [Supabase] <--SELECT-- [Este servico]
     (com validacao)                   (banco)              (apenas leitura)
```

### Por que separar?

O scraper (`leilohub-scraper-final`) possui validacao rigorosa que:
- Verifica estados validos do Brasil
- Detecta e rejeita veiculos (carros, motos)
- Bloqueia titulos genericos inventados
- Valida cidades e URLs

O aggregator nao possui essa validacao, portanto foi convertido para somente leitura.

## Endpoints Disponiveis

### Leitura (ATIVOS)

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/properties` | GET | Lista imoveis com filtros |
| `/api/properties/{id}` | GET | Detalhe do imovel |
| `/api/stats` | GET | Estatisticas gerais |
| `/api/geocoding/status` | GET | Status do geocoding |
| `/healthz` | GET | Health check |

### Escrita (DESABILITADOS)

| Endpoint | Status | Mensagem |
|----------|--------|----------|
| `POST /api/sync/start` | 501 | Desabilitado |
| `POST /api/sync/caixa` | 501 | Desabilitado |
| `POST /api/properties` | 501 | Desabilitado |

## Deploy

Este servico roda no Fly.io:

```bash
cd leilao-backend
flyctl deploy --app leilao-backend-solitary-haze-9882
```

## Variaveis de Ambiente

- `DATABASE_URL` - URL de conexao PostgreSQL (Supabase)
- `SUPABASE_URL` - URL do projeto Supabase
- `SUPABASE_KEY` - Chave de acesso Supabase

## Health Check

```bash
curl https://leilao-backend-solitary-haze-9882.fly.dev/healthz
```

## Historico de Mudancas

### 2026-02-04
- Convertido para API somente leitura
- `add_property()` desabilitado com NotImplementedError
- Endpoints de sync retornam 501 Not Implemented
- Dados devem ser inseridos via leilohub-scraper-final
