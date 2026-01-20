# TAREFA AUTÔNOMA: Ativar e Corrigir Scripts Existentes

**Prioridade:** 🔴 CRÍTICA  
**Tempo estimado:** 30-45 minutos  
**Execução:** AUTÔNOMA (não parar para perguntar)

---

## CONTEXTO

JÁ EXISTEM scripts prontos que NÃO ESTÃO SENDO USADOS:
- `fetch_caixa_images.py` - busca fotos dos imóveis da Caixa (55% sucesso)
- `audit_data_quality.py` - auditoria de qualidade
- `daily-maintenance.yml` - workflow às 4h BRT

**PROBLEMA:** 81% dos imóveis estão sem foto porque esses scripts não estão rodando.

---

## PARTE 1: LOCALIZAR E VERIFICAR SCRIPTS EXISTENTES

```bash
# 1. Encontrar fetch_caixa_images.py
find . -name "fetch_caixa_images.py" -type f 2>/dev/null

# 2. Encontrar audit_data_quality.py  
find . -name "audit_data_quality.py" -type f 2>/dev/null

# 3. Encontrar daily-maintenance.yml
find . -name "daily-maintenance.yml" -type f 2>/dev/null

# 4. Ver conteúdo do workflow
cat .github/workflows/daily-maintenance.yml 2>/dev/null
```

---

## PARTE 2: VERIFICAR SE WORKFLOW ESTÁ ATIVO

```bash
# Ver todos os workflows
ls -la .github/workflows/

# Ver histórico de execuções (via GitHub CLI se disponível)
gh run list --workflow=daily-maintenance.yml --limit 5 2>/dev/null || echo "GitHub CLI não disponível"
```

---

## PARTE 3: VERIFICAR O SCRIPT fetch_caixa_images.py

```bash
# Ver o script
cat leilao-backend/scripts/fetch_caixa_images.py

# Testar execução local (1 lote apenas)
cd leilao-backend
python scripts/fetch_caixa_images.py --help 2>/dev/null || python scripts/fetch_caixa_images.py --max-batches 1
```

---

## PARTE 4: GARANTIR QUE O WORKFLOW CHAMA O SCRIPT

O `daily-maintenance.yml` DEVE ter um step assim:

```yaml
- name: Fetch Caixa images
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
  run: |
    cd leilao-backend
    python scripts/fetch_caixa_images.py --max-batches 50
```

**Se não tiver, ADICIONAR.**

---

## PARTE 5: EXECUTAR FETCH DE IMAGENS AGORA

Se o script existe e funciona, rodar manualmente para recuperar as fotos:

```bash
cd leilao-backend

# Primeiro, testar com poucos
python scripts/fetch_caixa_images.py --max-batches 2

# Se funcionar, rodar mais
python scripts/fetch_caixa_images.py --max-batches 50
```

---

## PARTE 6: VERIFICAR RESULTADO

```bash
# Conectar no Supabase e verificar
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

result = supabase.table('properties').select('id', count='exact').eq('is_active', True).not_.is_('image_url', 'null').execute()
print(f'Imóveis com foto: {result.count}')

result2 = supabase.table('properties').select('id', count='exact').eq('is_active', True).is_('image_url', 'null').execute()
print(f'Imóveis sem foto: {result2.count}')
"
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Script `fetch_caixa_images.py` localizado e testado
- [ ] Workflow `daily-maintenance.yml` verificado e corrigido se necessário
- [ ] Pelo menos 1 lote de imagens buscado com sucesso
- [ ] Número de imóveis com foto aumentou

---

## APÓS CONCLUSÃO

Reportar:
1. Localização exata do script
2. Se o workflow estava chamando o script ou não
3. Quantas fotos foram buscadas no teste
4. Erros encontrados (se houver)
