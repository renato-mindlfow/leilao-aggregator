# 🚀 GUIA RÁPIDO - QUALIDADE DE DADOS

## ✅ STATUS ATUAL
- **Categorias:** ✅ 15 únicas (sem duplicatas)
- **Cidades:** ✅ 2,423 únicas (sem duplicatas)
- **Bairros:** ✅ 5,562 únicos (sem duplicatas)
- **Total:** ✅ 41,465 imóveis ativos

## 🔧 COMANDOS RÁPIDOS

### Verificar Qualidade dos Dados
```bash
cd leilao-backend
python verify_data_quality.py
```

### Corrigir Dados (se necessário)
```bash
cd leilao-backend
python fix_data_quality_v2.py
```

### Investigar Problemas Específicos
```bash
cd leilao-backend
python investigate_duplicates.py
```

## 💻 USO NO CÓDIGO

### Normalizar Dados ao Criar Propriedades
```python
from app.utils.category_normalizer import (
    normalize_category,
    normalize_city,
    normalize_neighborhood
)

# Em qualquer scraper ou API:
property_data = {
    "category": normalize_category(raw_category),
    "city": normalize_city(raw_city),
    "neighborhood": normalize_neighborhood(raw_neighborhood),
    # ... outros campos
}
```

### Validar Categoria
```python
from app.utils.category_normalizer import is_valid_category, get_valid_categories

# Verificar se categoria é válida
if is_valid_category(category):
    print("✅ Categoria válida!")

# Listar categorias válidas
valid_cats = get_valid_categories()
print(valid_cats)
# ['Apartamento', 'Casa', 'Terreno', 'Comercial', ...]
```

## 🗄️ SQL DIRETO (Supabase)

### Verificar Duplicatas
```sql
-- Categorias
SELECT LOWER(category), COUNT(DISTINCT category)
FROM properties
WHERE is_active = TRUE
GROUP BY LOWER(category)
HAVING COUNT(DISTINCT category) > 1;

-- Cidades
SELECT LOWER(city), COUNT(DISTINCT city)
FROM properties
WHERE is_active = TRUE
GROUP BY LOWER(city)
HAVING COUNT(DISTINCT city) > 1;
```

### Corrigir Manualmente
```sql
-- Normalizar tudo de uma vez
UPDATE properties
SET 
    category = CASE 
        WHEN LOWER(category) = 'apartamento' THEN 'Apartamento'
        WHEN LOWER(category) = 'casa' THEN 'Casa'
        -- ... outros casos
        ELSE category
    END,
    city = INITCAP(city),
    neighborhood = INITCAP(neighborhood),
    updated_at = CURRENT_TIMESTAMP
WHERE is_active = TRUE;
```

## 📊 CATEGORIAS VÁLIDAS

As categorias normalizadas aceitas são:
- Apartamento
- Casa
- Terreno
- Comercial
- Rural
- Galpão
- Loja
- Garagem
- Sala Comercial
- Área
- Prédio
- Chácara
- Sítio
- Fazenda
- Cobertura
- Kitnet
- Flat
- Box
- Vaga de Garagem
- Estacionamento
- Industrial
- Outro (para casos não classificados)

## 🛡️ PREVENÇÃO

### SEMPRE normalizar antes de salvar:
```python
# ❌ ERRADO
property.category = raw_data['category']  # Pode vir como "APARTAMENTO"

# ✅ CORRETO
property.category = normalize_category(raw_data['category'])  # Sempre "Apartamento"
```

## 📞 TROUBLESHOOTING

### Problema: Ainda vejo duplicatas
**Solução:** Execute o script de correção novamente
```bash
python fix_data_quality_v2.py
```

### Problema: Categoria inválida
**Solução:** Use o normalizador
```python
from app.utils.category_normalizer import normalize_category
correct_category = normalize_category(wrong_category)
```

### Problema: Valores NULL
**Solução:** O normalizador converte NULL para "Outro"
```python
normalize_category(None)  # Retorna "Outro"
```

## 📝 ARQUIVOS IMPORTANTES

- `fix_data_quality_v2.py` - Correção automática (RECOMENDADO)
- `verify_data_quality.py` - Verificação rápida
- `app/utils/category_normalizer.py` - Utilitário de normalização
- `sql_fix_data_quality.sql` - SQL puro para Supabase
- `RESUMO_CORRECAO_QUALIDADE_DADOS_FINAL.md` - Documentação completa

## ⚡ DICA PRO

Adicione ao seu `requirements.txt`:
```
psycopg>=3.0.0
python-dotenv>=0.19.0
```

E ao seu `.pre-commit-hook` (se usar):
```bash
python verify_data_quality.py
```

---

✅ **Dados limpos = Sistema feliz!** 🎉

