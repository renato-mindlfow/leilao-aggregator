# 🔧 TAREFA AUTÔNOMA: DIAGNÓSTICO E CORREÇÃO COMPLETA DO LEILOHUB

**Data:** 2025-12-28
**Prioridade:** CRÍTICA
**Objetivo:** Diagnosticar e corrigir TODOS os problemas que impedem o backend de funcionar

---

## 📋 CONTEXTO

O backend do LeiloHub não está iniciando devido a erro de conexão com o banco de dados PostgreSQL (Supabase). Várias tentativas manuais de correção falharam.

**Sintoma principal:**
```
psycopg.OperationalError: connection failed: FATAL: password authentication failed for user "postgres"
```

**Observação crítica:** O erro mostra conexão para `aws-1-sa-east-1.pooler.supabase.com:6543` mesmo após atualizar o `.env` para usar `db.nawbptwbmdgrkbpbwxzl.supabase.co:5432`. Isso indica que o código NÃO está lendo o `.env` corretamente.

---

## 🎯 SUA MISSÃO (CURSOR AGENT)

Executar as seguintes etapas DE FORMA AUTÔNOMA, sem parar para perguntar:

### FASE 1: DIAGNÓSTICO COMPLETO (5 min)

1. **Verificar estrutura do projeto:**
   ```bash
   ls -la
   cat .env
   ```

2. **Encontrar TODAS as referências a DATABASE_URL no código:**
   ```bash
   grep -r "DATABASE_URL" --include="*.py" .
   grep -r "pooler.supabase" --include="*.py" .
   grep -r "6543" --include="*.py" .
   ```

3. **Verificar como o dotenv é carregado:**
   ```bash
   grep -r "load_dotenv\|dotenv\|environ" --include="*.py" . | head -30
   ```

4. **Verificar o arquivo postgres_database.py:**
   ```bash
   cat app/services/postgres_database.py | head -50
   ```

5. **Verificar se há variáveis hardcoded ou fallbacks:**
   ```bash
   grep -r "aws-1-sa-east-1" --include="*.py" .
   ```

### FASE 2: IDENTIFICAR A CAUSA RAIZ (2 min)

Com base no diagnóstico, identificar:
- [ ] O `.env` está sendo lido?
- [ ] Há valores hardcoded no código?
- [ ] O `python-dotenv` está instalado?
- [ ] A variável está sendo sobrescrita em algum lugar?

### FASE 3: APLICAR CORREÇÕES (10 min)

**3.1. Garantir que python-dotenv está instalado:**
```bash
pip install python-dotenv
```

**3.2. Corrigir o carregamento do .env no código:**

O arquivo que carrega DATABASE_URL (provavelmente `postgres_database.py` ou `__init__.py`) DEVE ter:

```python
import os
from dotenv import load_dotenv

# Carregar .env ANTES de qualquer outra coisa
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada no .env")
```

**3.3. Remover QUALQUER valor hardcoded de DATABASE_URL**

Se encontrar algo como:
```python
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.xxx:senha@pooler...")
```

Remover o fallback e deixar apenas:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
```

**3.4. Garantir que o .env está correto:**

O arquivo `.env` DEVE conter EXATAMENTE:
```
SUPABASE_URL=https://nawbptwbmdgrkbpbwxzl.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5hd2JwdHdibWRncmticGJ3eHpsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU2MDAzMDMsImV4cCI6MjA4MTE3NjMwM30.xRv1OqaQILaS4exgKDwZjR2REeCS7IB0Bjs_0tkzSaY
DATABASE_URL=postgresql://postgres:LeiloHub2025Pass@db.nawbptwbmdgrkbpbwxzl.supabase.co:5432/postgres
```

**IMPORTANTE:** 
- Porta: `5432` (NÃO 6543)
- Host: `db.nawbptwbmdgrkbpbwxzl.supabase.co` (NÃO pooler)
- Usuário: `postgres` (NÃO postgres.xxx)
- Senha: `LeiloHub2025Pass`

### FASE 4: TESTAR CONEXÃO ISOLADAMENTE (3 min)

Criar um script de teste simples:

```python
# test_db_connection.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"DATABASE_URL carregada: {DATABASE_URL[:50]}...")

import psycopg
from psycopg.rows import dict_row

try:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    cursor = conn.execute("SELECT COUNT(*) as total FROM properties")
    result = cursor.fetchone()
    print(f"✅ Conexão OK! Total de imóveis: {result['total']}")
    conn.close()
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
```

Executar:
```bash
python test_db_connection.py
```

### FASE 5: INICIAR O SERVIDOR (2 min)

Se o teste de conexão passar:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### FASE 6: VALIDAR ENDPOINTS (5 min)

Testar os endpoints:
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/stats
curl http://localhost:8000/api/admin/geocoding/status
curl http://localhost:8000/api/admin/audit/stats
```

---

## 🚨 SE AINDA FALHAR

Se após todas as correções ainda houver erro de senha:

1. **A senha pode estar errada no Supabase**
   - O usuário precisa acessar https://supabase.com/dashboard
   - Settings → Database → Reset database password
   - Usar senha: `LeiloHub2025Pass`

2. **Pode haver firewall/IPv4**
   - O print mostrava "Not IPv4 compatible"
   - Tentar usar Session Pooler ao invés de Direct connection
   - Mudar Method para "Session pooler" no Supabase Dashboard e pegar a nova connection string

---

## 📁 ARQUIVOS QUE PROVAVELMENTE PRECISAM SER MODIFICADOS

1. `app/services/postgres_database.py` - Carregamento da DATABASE_URL
2. `app/services/__init__.py` - Inicialização do banco
3. `.env` - Credenciais corretas
4. Possivelmente `app/main.py` - Se houver import problemático

---

## ✅ CRITÉRIOS DE SUCESSO

A tarefa está completa quando:
- [ ] `python test_db_connection.py` mostra "✅ Conexão OK!"
- [ ] `python -m uvicorn app.main:app --port 8000` inicia sem erros
- [ ] `curl http://localhost:8000/healthz` retorna resposta válida
- [ ] `curl http://localhost:8000/stats` retorna dados do banco

---

## 📝 NOTAS PARA O CURSOR AGENT

1. **NÃO PARE** para perguntar - execute tudo autonomamente
2. **MOSTRE** cada comando executado e seu resultado
3. **SE ENCONTRAR** valores hardcoded, liste-os antes de modificar
4. **FAÇA BACKUP** antes de modificar arquivos críticos
5. **DOCUMENTE** todas as mudanças feitas em um resumo final

---

## 🔄 APÓS RESOLVER O PROBLEMA DE CONEXÃO

Uma vez que o backend estiver funcionando, verificar se as implementações anteriores estão corretas:

1. **Background Geocoding:** `app/services/background_geocoding.py` existe?
2. **Quality Auditor:** `app/utils/quality_auditor.py` existe?
3. **Image Blacklist:** `app/utils/image_blacklist.py` existe e tem os métodos corretos?

Se algum arquivo estiver faltando ou incompleto, consultar a tarefa anterior em:
`TAREFA_CURSOR_AGENT_PRIORIDADES_2025-12-28.md`

---

**COMECE AGORA - EXECUTE FASE POR FASE SEM INTERRUPÇÃO**
