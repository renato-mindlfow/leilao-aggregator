# Configuração de Credenciais - LeiloHub

## ?? IMPORTANTE: Este arquivo NÃO contém secrets, apenas instruções!

## Variáveis de Ambiente Necessárias

O arquivo leilao-backend/.env deve conter:
`env
# Database (Supabase Transaction Pooler - porta 6543 para Fly.io)
DATABASE_URL=postgresql://postgres.PROJECT_ID:SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres

# Supabase
SUPABASE_URL=https://PROJECT_ID.supabase.co
SUPABASE_KEY=eyJ... (service_role key)

# OpenAI (para extração com IA)
OPENAI_API_KEY=sk-proj-...

# ScrapingBee (para bypass de Cloudflare)
SCRAPINGBEE_API_KEY=...
`

## Onde Obter as Credenciais

### 1. Supabase (SUPABASE_URL, SUPABASE_KEY, DATABASE_URL)
- Acesse: https://supabase.com/dashboard
- Projeto: nawbptwbmdgrkbpbwxzl
- Settings ? API ? Project URL (SUPABASE_URL)
- Settings ? API ? service_role key (SUPABASE_KEY)
- Settings ? Database ? Connection string ? Transaction pooler (DATABASE_URL)

### 2. OpenAI (OPENAI_API_KEY)
- Acesse: https://platform.openai.com/api-keys
- Crie uma nova key ou use existente

### 3. ScrapingBee (SCRAPINGBEE_API_KEY)
- Acesse: https://www.scrapingbee.com/
- Dashboard ? API Key

## Backup de Credenciais

As credenciais também existem em:
- C:\LeiloHub\leilohub-scraper-final\.env (backup local)
- Fly.io secrets: lyctl secrets list --app leilao-backend

## Verificar Fly.io Secrets
`powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
flyctl secrets list --app leilao-backend
`

Deve mostrar:
- DATABASE_URL
- SUPABASE_URL
- SUPABASE_KEY
- OPENAI_API_KEY
- SCRAPINGBEE_API_KEY

## Restaurar Credenciais (se perder)

1. Copiar do scraper Manus:
`powershell
Copy-Item "C:\LeiloHub\leilohub-scraper-final\.env" "C:\LeiloHub\leilao-aggregator-git\leilao-backend\.env"
`

2. Ou obter do Fly.io e recriar manualmente

## Atualizar Fly.io (após mudar .env local)
`powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
$env = Get-Content ".env" -Raw
# Extrair e enviar cada variável com flyctl secrets set
`

---
**Última atualização:** 2025-01-18
**Autor:** Claude (Engenheiro Chefe LeiloHub)
