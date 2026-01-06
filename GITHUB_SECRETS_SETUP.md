# Configuração de Secrets do GitHub Actions

Este documento lista todos os secrets necessários para os workflows do GitHub Actions funcionarem corretamente.

## Secrets Obrigatórios

### DATABASE_URL
- **Descrição**: URL de conexão com o banco de dados PostgreSQL
- **Formato**: `postgresql://usuario:senha@host:porta/database`
- **Onde é usado**: 
  - `daily-maintenance.yml`
  - `daily-sync.yml`
  - Outros workflows que acessam o banco

### SUPABASE_URL (Opcional)
- **Descrição**: URL do projeto Supabase
- **Formato**: `https://xxxxx.supabase.co`
- **Onde é usado**: 
  - `daily-maintenance.yml` (se houver integração com Supabase)

### SUPABASE_KEY (Opcional)
- **Descrição**: Chave de API do Supabase (service role key)
- **Formato**: String de chave JWT
- **Onde é usado**: 
  - `daily-maintenance.yml` (se houver integração com Supabase)
  - `scraping-diario.yml`

### FLY_API_TOKEN (Obrigatório para Deploy)
- **Descrição**: Token de API do Fly.io para fazer deploy
- **Formato**: String de token de acesso pessoal
- **Onde é usado**: 
  - `deploy.yml` (workflow de deploy automático)
- **Como obter**:
  1. Acesse https://fly.io/user/personal_access_tokens
  2. Crie um novo token de acesso pessoal
  3. Copie o token e adicione como secret no GitHub
- **⚠️ CRÍTICO**: Sem este secret, o deploy automático falhará

### API_URL (Obrigatório para Daily Sync)
- **Descrição**: URL base da API para sincronização
- **Formato**: `https://seu-app.fly.dev` ou `http://localhost:8000` (desenvolvimento)
- **Onde é usado**: 
  - `daily-sync.yml` (workflow de sincronização diária)
- **Observação**: Deve apontar para a URL onde a API está rodando

## Como Configurar

1. Acesse o repositório no GitHub
2. Vá em **Settings** → **Secrets and variables** → **Actions**
3. Clique em **New repository secret**
4. Adicione cada secret com o nome e valor correspondente

## Verificação

Para verificar se os secrets estão configurados corretamente:

1. Execute o workflow manualmente via `workflow_dispatch`
2. Verifique os logs para erros relacionados a variáveis de ambiente
3. Se aparecer erro de "secret not found", adicione o secret faltante

## Notas

- **DATABASE_URL** é obrigatório para a maioria dos workflows
- **FLY_API_TOKEN** é obrigatório para o workflow de deploy (`deploy.yml`)
- **API_URL** é obrigatório para o workflow de sincronização (`daily-sync.yml`)
- **SUPABASE_URL** e **SUPABASE_KEY** são opcionais e só são necessários se o código usar Supabase
- Nunca commite secrets no código ou em arquivos de configuração
- Use sempre GitHub Secrets para informações sensíveis

## Resumo de Secrets por Workflow

| Workflow | Secrets Necessários |
|----------|---------------------|
| `daily-maintenance.yml` | DATABASE_URL, SUPABASE_URL, SUPABASE_KEY |
| `daily-sync.yml` | API_URL |
| `deploy.yml` | FLY_API_TOKEN |
| `scraping-diario.yml` | SUPABASE_URL, SUPABASE_KEY |

