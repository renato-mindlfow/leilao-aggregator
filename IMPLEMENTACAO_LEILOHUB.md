# 📋 Guia de Implementação - Sistema Completo LeiloHub

Este documento contém as instruções finais para completar a implementação do sistema de autenticação, pagamentos e analytics do LeiloHub.

## ✅ O que já foi implementado

### Backend
- ✅ Serviço Asaas (`leilao-backend/app/services/asaas_service.py`)
- ✅ Endpoints de usuário, pagamento e analytics (`leilao-backend/app/main.py`)
- ✅ Dependência `httpx` adicionada ao `pyproject.toml`

### Frontend
- ✅ AuthContext (`leilao-frontend/src/contexts/AuthContext.tsx`)
- ✅ LoginModal (`leilao-frontend/src/components/auth/LoginModal.tsx`)
- ✅ PricingModal (`leilao-frontend/src/components/auth/PricingModal.tsx`)
- ✅ TrialBanner (`leilao-frontend/src/components/auth/TrialBanner.tsx`)
- ✅ AdminPanel (`leilao-frontend/src/components/admin/AdminPanel.tsx`)
- ✅ Integração no App.tsx com controle de acesso

## 🔧 O que falta fazer

### 1. Banco de Dados (Supabase SQL Editor)

Execute o SQL fornecido no documento `TAREFA_CURSOR_SISTEMA_COMPLETO_LEILOHUB.md` (FASE 1) no Supabase SQL Editor. Isso criará:
- Tabela `user_profiles`
- Tabela `search_logs`
- Tabela `property_views`
- Tabela `user_favorites`
- Funções e triggers necessários
- Row Level Security (RLS)

### 2. Instalar dependências do frontend

```bash
cd leilao-frontend
npm install @supabase/supabase-js
```

### 3. Configurar variáveis de ambiente

Crie/atualize o arquivo `leilao-frontend/.env`:

```env
VITE_SUPABASE_URL=https://nawbptwbmdgrkbpbwxzl.supabase.co
VITE_SUPABASE_ANON_KEY=sua-anon-key-aqui
VITE_API_URL=https://leilao-backend-solitary-haze-9882.fly.dev
```

**Importante:** Obtenha a `VITE_SUPABASE_ANON_KEY` no painel do Supabase (Settings > API > anon/public key).

### 4. Configurar Google OAuth no Supabase

1. Acesse o painel do Supabase
2. Vá em Authentication > Providers > Google
3. Configure:
   - Client ID: `728599943839-8pnhh8se9lfg0451ioalfoglv05np0nv.apps.googleusercontent.com`
   - Client Secret: `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`
   - Redirect URL: `https://nawbptwbmdgrkbpbwxzl.supabase.co/auth/v1/callback`
   - Enable Google provider

### 5. Configurar variável de ambiente no Fly.io

Configure a API key do Asaas no Fly.io:

```bash
cd leilao-backend
flyctl secrets set ASAAS_API_KEY=sua-api-key-do-asaas
```

### 6. Configurar Webhook do Asaas

No painel do Asaas, configure o webhook para:
- URL: `https://leilao-backend-solitary-haze-9882.fly.dev/api/asaas/webhook`
- Eventos: `PAYMENT_CONFIRMED`, `PAYMENT_RECEIVED`, `PAYMENT_OVERDUE`, `SUBSCRIPTION_DELETED`, `SUBSCRIPTION_INACTIVATED`

### 7. Instalar dependências do backend

```bash
cd leilao-backend
poetry install
```

Ou se usar pip:

```bash
pip install httpx
```

### 8. Criar usuário admin (SQL no Supabase)

Após criar sua conta, execute no Supabase SQL Editor:

```sql
UPDATE user_profiles SET role = 'admin' WHERE email = 'seu-email@exemplo.com';
```

## 🧪 Testes

### Fluxo de teste completo:

1. **Usuário não logado:**
   - Pesquisar imóveis ✓
   - Clicar em "Detalhes" → Modal de Login aparece ✓

2. **Cadastro novo usuário:**
   - Criar conta → Trial de 10 dias ativado automaticamente ✓
   - Ver até 20 imóveis ✓
   - Banner de trial aparece no topo ✓

3. **Trial expirado:**
   - Tentar ver detalhes → Modal de Preços aparece ✓
   - Escolher plano → Redireciona para checkout Asaas ✓

4. **Usuário pagante:**
   - Acesso ilimitado ✓
   - Sem banners de trial ✓

5. **Admin:**
   - Botão "Admin" aparece no header ✓
   - Acesso ao painel administrativo ✓
   - Visualiza analytics de uso ✓

## 📝 Observações importantes

1. **O SQL do banco de dados DEVE ser executado primeiro**, antes de testar o sistema
2. As variáveis de ambiente são críticas - sem elas, o sistema não funcionará
3. O Google OAuth precisa ser configurado no Supabase para funcionar
4. O webhook do Asaas é necessário para ativar assinaturas automaticamente
5. Certifique-se de que o backend está rodando e acessível na URL configurada

## 🐛 Possíveis problemas

### Frontend não conecta ao Supabase
- Verifique `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY` no `.env`
- Reinicie o servidor de desenvolvimento após mudar `.env`

### Erro ao criar checkout
- Verifique se `ASAAS_API_KEY` está configurada no Fly.io
- Verifique se o serviço Asaas está funcionando

### Webhook não funciona
- Verifique se a URL está correta no painel do Asaas
- Verifique os logs do backend no Fly.io

### Usuário não recebe trial automático
- Verifique se o trigger `on_auth_user_created` foi criado no banco
- Verifique os logs do Supabase

## 📚 Documentação adicional

Consulte o arquivo `TAREFA_CURSOR_SISTEMA_COMPLETO_LEILOHUB.md` para detalhes completos de cada fase.


