# ✅ CHECKLIST DE VALIDAÇÃO COMPLETA - LEILOHUB

**Data:** 28/12/2025
**Objetivo:** Certificar que TODOS os problemas foram de fato resolvidos

---

## 🔧 INSTRUÇÕES PARA O CURSOR AGENT

Execute esta validação completa e reporte o resultado de cada item.

```
Leia o arquivo CHECKLIST_VALIDACAO_COMPLETA.md e execute TODOS os testes listados.
Para cada teste, indique: ✅ PASSOU ou ❌ FALHOU (com detalhes do erro).
```

---

## FASE 1: VALIDAÇÃO DE ARQUIVOS E CONFIGURAÇÃO

### 1.1 Verificar que .env existe e está correto
```bash
cd leilao-backend
cat .env
```

**Esperado:**
- [ ] Arquivo existe
- [ ] Contém SUPABASE_URL
- [ ] Contém SUPABASE_KEY  
- [ ] Contém DATABASE_URL com porta 5432 (NÃO 6543)
- [ ] DATABASE_URL usa host `db.xxx.supabase.co` (NÃO pooler)

### 1.2 Verificar que NÃO há valores hardcoded
```bash
grep -r "pooler.supabase" --include="*.py" .
grep -r ":6543" --include="*.py" .
grep -r "DEFAULT_DATABASE_URL" --include="*.py" .
```

**Esperado:**
- [ ] Nenhum resultado (0 matches)

### 1.3 Verificar que load_dotenv está presente
```bash
grep -l "load_dotenv" app/services/postgres_database.py app/services/__init__.py app/main.py
```

**Esperado:**
- [ ] Todos os 3 arquivos listados

---

## FASE 2: VALIDAÇÃO DE CONEXÃO COM BANCO

### 2.1 Teste de conexão isolado
```bash
cd leilao-backend
python test_db_connection.py
```

**Esperado:**
- [ ] Mensagem "✅ Conexão OK!"
- [ ] Mostra quantidade de imóveis (ex: 29.901)

### 2.2 Verificar que a conexão usa as credenciais do .env
```bash
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
url = os.getenv('DATABASE_URL')
print('Host:', 'db.' in url)
print('Porta 5432:', ':5432' in url)
print('Não usa pooler:', 'pooler' not in url)
"
```

**Esperado:**
- [ ] Host: True
- [ ] Porta 5432: True
- [ ] Não usa pooler: True

---

## FASE 3: VALIDAÇÃO DO SERVIDOR

### 3.1 Iniciar servidor
```bash
cd leilao-backend
python -m uvicorn app.main:app --port 8000 &
sleep 5
```

**Esperado:**
- [ ] Servidor inicia sem erros
- [ ] Mensagem "Uvicorn running on http://127.0.0.1:8000"

### 3.2 Testar endpoint de health
```bash
curl -s http://localhost:8000/healthz | head -100
```

**Esperado:**
- [ ] Retorna JSON válido
- [ ] Status OK ou similar

### 3.3 Testar endpoint de stats
```bash
curl -s http://localhost:8000/stats | head -100
```

**Esperado:**
- [ ] Retorna JSON com estatísticas
- [ ] Mostra total de imóveis

---

## FASE 4: VALIDAÇÃO DAS NOVAS FUNCIONALIDADES

### 4.1 Verificar arquivos de novas funcionalidades existem
```bash
ls -la app/services/background_geocoding.py 2>/dev/null && echo "✅ background_geocoding.py existe" || echo "❌ background_geocoding.py NÃO existe"
ls -la app/utils/quality_auditor.py 2>/dev/null && echo "✅ quality_auditor.py existe" || echo "❌ quality_auditor.py NÃO existe"
ls -la app/utils/image_blacklist.py 2>/dev/null && echo "✅ image_blacklist.py existe" || echo "❌ image_blacklist.py NÃO existe"
```

**Esperado:**
- [ ] background_geocoding.py existe
- [ ] quality_auditor.py existe
- [ ] image_blacklist.py existe

### 4.2 Testar endpoint de geocoding (se implementado)
```bash
curl -s http://localhost:8000/api/admin/geocoding/status 2>/dev/null | head -100
```

**Esperado:**
- [ ] Retorna JSON com status do geocoding
- [ ] OU retorna 404 (endpoint não implementado ainda)

### 4.3 Testar endpoint de auditoria (se implementado)
```bash
curl -s http://localhost:8000/api/admin/audit/stats 2>/dev/null | head -100
```

**Esperado:**
- [ ] Retorna JSON com estatísticas de auditoria
- [ ] OU retorna 404 (endpoint não implementado ainda)

### 4.4 Testar endpoint de imagens (se implementado)
```bash
curl -s http://localhost:8000/api/admin/images/stats 2>/dev/null | head -100
```

**Esperado:**
- [ ] Retorna JSON com estatísticas de filtro
- [ ] OU retorna 404 (endpoint não implementado ainda)

---

## FASE 5: VALIDAÇÃO DE DADOS NO BANCO

### 5.1 Contar imóveis totais
```bash
python -c "
from dotenv import load_dotenv
import os
import psycopg
from psycopg.rows import dict_row

load_dotenv()
conn = psycopg.connect(os.getenv('DATABASE_URL'), row_factory=dict_row)
result = conn.execute('SELECT COUNT(*) as total FROM properties').fetchone()
print(f'Total de imóveis: {result[\"total\"]}')
conn.close()
"
```

**Esperado:**
- [ ] Mostra total de imóveis (aproximadamente 29.901)

### 5.2 Verificar imóveis com estado válido
```bash
python -c "
from dotenv import load_dotenv
import os
import psycopg
from psycopg.rows import dict_row

load_dotenv()
conn = psycopg.connect(os.getenv('DATABASE_URL'), row_factory=dict_row)
result = conn.execute(\"\"\"
    SELECT state, COUNT(*) as total 
    FROM properties 
    WHERE state = 'XX' OR state IS NULL OR state = ''
    GROUP BY state
\"\"\").fetchall()
if result:
    print(f'⚠️ Imóveis com estado inválido: {result}')
else:
    print('✅ Nenhum imóvel com estado inválido')
conn.close()
"
```

**Esperado:**
- [ ] Nenhum ou poucos imóveis com estado 'XX'

### 5.3 Verificar imóveis sem coordenadas
```bash
python -c "
from dotenv import load_dotenv
import os
import psycopg
from psycopg.rows import dict_row

load_dotenv()
conn = psycopg.connect(os.getenv('DATABASE_URL'), row_factory=dict_row)
result = conn.execute(\"\"\"
    SELECT COUNT(*) as total 
    FROM properties 
    WHERE latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
\"\"\").fetchone()
print(f'Imóveis sem coordenadas: {result[\"total\"]}')
conn.close()
"
```

**Esperado:**
- [ ] Mostra quantidade (informativo, não é erro)

---

## FASE 6: LIMPEZA E FINALIZAÇÃO

### 6.1 Parar servidor de teste
```bash
pkill -f "uvicorn app.main:app" 2>/dev/null || echo "Servidor já parado"
```

### 6.2 Verificar que não há processos órfãos
```bash
ps aux | grep uvicorn | grep -v grep || echo "✅ Nenhum processo uvicorn rodando"
```

---

## 📊 RESUMO DA VALIDAÇÃO

Preencher após executar todos os testes:

| Fase | Testes | Passou | Falhou |
|------|--------|--------|--------|
| 1. Arquivos e Configuração | 3 | _ | _ |
| 2. Conexão com Banco | 2 | _ | _ |
| 3. Servidor | 3 | _ | _ |
| 4. Novas Funcionalidades | 4 | _ | _ |
| 5. Dados no Banco | 3 | _ | _ |
| 6. Limpeza | 2 | _ | _ |
| **TOTAL** | **17** | **_** | **_** |

---

## 🚨 SE ALGUM TESTE FALHAR

1. **Documente o erro exato**
2. **Identifique a fase que falhou**
3. **Crie uma tarefa específica** para o Cursor Agent corrigir
4. **Re-execute a validação** após a correção

---

## ✅ CRITÉRIOS DE SUCESSO FINAL

A validação é considerada **COMPLETA** quando:

- [ ] Todos os testes da Fase 1 passam (configuração correta)
- [ ] Teste de conexão com banco funciona (Fase 2)
- [ ] Servidor inicia sem erros (Fase 3)
- [ ] Pelo menos os arquivos das novas funcionalidades existem (Fase 4)
- [ ] Consultas ao banco funcionam (Fase 5)

---

**Execute esta validação e reporte os resultados!**
