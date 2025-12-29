# TAREFA: Corrigir Qualidade do Geocoding

## CONTEXTO
O geocoding processou 3.459 imóveis mas teve apenas 22% de sucesso (762).
A causa principal NÃO é o serviço de geocoding, mas sim a **qualidade dos endereços**.

## PROBLEMAS IDENTIFICADOS

### 1. Endereços com texto promocional
```
DENTRE OUTRAS, ENTRE EM CONTATO CONOSCO ATRAVÉS DO SITE: WWW.GRUPOLANCE.COM.BR...
```

### 2. Endereço do escritório do leiloeiro repetido
```
Rua Serra de Botucatu, 880, sala 1208, Vila Gomes Cardim - CEP: 03317-000
```
Aparece ~30 vezes para diferentes cidades (Guarujá, Caraguatatuba, Adamantina).

### 3. Formato sujo
```
Bady Bassitt, 650, Rodovia BR-153 - - - Bady Bassitt /SP
```

---

## TAREFA 1: Marcar Endereços Inválidos no Banco

Execute no Supabase (SQL Editor):

```sql
-- 1. Marcar endereços com texto promocional
UPDATE properties
SET geocoding_status = 'invalid_address'
WHERE address ILIKE '%ENTRE EM CONTATO%'
   OR address ILIKE '%WHATSAPP%'
   OR address ILIKE '%WWW.%'
   OR address ILIKE '%GRUPOLANCE%'
   OR address ILIKE '%MAIS INFORMAÇÕES%';

-- 2. Marcar endereços de escritórios de leiloeiros
UPDATE properties
SET geocoding_status = 'invalid_address'
WHERE address ILIKE '%Serra de Botucatu, 880%';

-- 3. Verificar quantos foram marcados
SELECT geocoding_status, COUNT(*) 
FROM properties 
GROUP BY geocoding_status;
```

---

## TAREFA 2: Modificar Serviço de Geocoding

### Arquivo: `leilao-backend/app/services/geocoding_service.py`

Adicionar ANTES da função que faz geocoding:

```python
import re

# Padrões que indicam endereço inválido
ENDERECO_BLACKLIST = [
    'ENTRE EM CONTATO',
    'WHATSAPP',
    'WWW.',
    '.COM.BR',
    'DENTRE OUTRAS',
    'MAIS INFORMAÇÕES',
    'GRUPOLANCE',
]

# Endereços de escritórios conhecidos (não são imóveis)
ESCRITORIOS_LEILOEIROS = [
    'rua serra de botucatu, 880',
    'sala 1208, vila gomes cardim',
]

def validar_endereco_para_geocoding(endereco: str) -> tuple[bool, str]:
    """
    Valida se endereço é adequado para geocoding.
    Retorna (is_valid, motivo_se_invalido)
    """
    if not endereco or len(endereco.strip()) < 10:
        return False, "Endereço muito curto ou vazio"
    
    endereco_upper = endereco.upper()
    
    # Verificar blacklist
    for pattern in ENDERECO_BLACKLIST:
        if pattern in endereco_upper:
            return False, f"Contém texto promocional: {pattern}"
    
    # Verificar escritórios de leiloeiros
    endereco_lower = endereco.lower()
    for escritorio in ESCRITORIOS_LEILOEIROS:
        if escritorio in endereco_lower:
            return False, "Endereço de escritório de leiloeiro"
    
    return True, ""


def limpar_endereco(endereco: str) -> str:
    """
    Limpa formato do endereço antes de enviar ao Nominatim.
    """
    # Remover " - - -" e variações
    endereco = re.sub(r'\s*-\s*-\s*-\s*', ' ', endereco)
    
    # Remover "/UF" no final (ex: /SP, /RJ)
    endereco = re.sub(r'\s*/[A-Z]{2}\s*$', '', endereco)
    
    # Remover CEP do meio do texto (já vai no query)
    endereco = re.sub(r'\s*-?\s*CEP:?\s*[\d.-]+', '', endereco)
    
    # Remover espaços múltiplos
    endereco = re.sub(r'\s+', ' ', endereco).strip()
    
    return endereco
```

### Modificar a função de geocoding para usar validação:

```python
async def geocode_property(property_data: dict) -> dict:
    """
    Geocodifica um imóvel com validação prévia.
    """
    endereco = property_data.get('address', '')
    cidade = property_data.get('city', '')
    estado = property_data.get('state', '')
    
    # VALIDAR ANTES DE CHAMAR API
    is_valid, motivo = validar_endereco_para_geocoding(endereco)
    if not is_valid:
        logger.warning(f"Endereço inválido para geocoding: {motivo}")
        return {
            'success': False,
            'status': 'invalid_address',
            'error': motivo,
            'latitude': None,
            'longitude': None
        }
    
    # LIMPAR ENDEREÇO
    endereco_limpo = limpar_endereco(endereco)
    
    # Continuar com geocoding normal...
    query = f"{endereco_limpo}, {cidade}, {estado}, Brasil"
    # ... resto do código
```

---

## TAREFA 3: Adicionar Cache de Geocoding

### No mesmo arquivo, adicionar:

```python
from functools import lru_cache

# Cache em memória para evitar chamadas duplicadas
@lru_cache(maxsize=10000)
def _geocode_cached(query: str) -> tuple:
    """
    Cache de geocoding. Retorna (lat, lon, success).
    """
    # Esta função é chamada internamente
    pass

# Alternativa: Cache persistente no banco
async def verificar_cache_geocoding(endereco: str, cidade: str, estado: str) -> dict:
    """
    Verifica se já temos geocoding para este endereço.
    """
    # Criar hash do endereço
    cache_key = f"{endereco}|{cidade}|{estado}".lower()
    
    # Buscar no banco se já existe imóvel com mesmo endereço E coordenadas
    # ...
```

---

## CRITÉRIOS DE SUCESSO

1. [ ] Imóveis com texto promocional marcados como `invalid_address`
2. [ ] Imóveis com endereço de escritório marcados como `invalid_address`
3. [ ] Validação de endereço implementada no serviço de geocoding
4. [ ] Limpeza de endereço implementada
5. [ ] Próximo batch de geocoding deve ter taxa > 50%

---

## COMANDOS DE VERIFICAÇÃO

```bash
# Verificar quantos endereços são inválidos
SELECT COUNT(*) FROM properties WHERE geocoding_status = 'invalid_address';

# Verificar taxa de sucesso após correções
SELECT geocoding_status, COUNT(*) 
FROM properties 
WHERE geocoding_status IS NOT NULL
GROUP BY geocoding_status;

# Listar endereços problemáticos restantes
SELECT DISTINCT LEFT(address, 100) as endereco_truncado, COUNT(*)
FROM properties
WHERE geocoding_status = 'failed'
GROUP BY LEFT(address, 100)
ORDER BY COUNT(*) DESC
LIMIT 20;
```

---

## INSTRUÇÕES PARA CURSOR AGENT

1. Execute AUTONOMAMENTE sem parar para perguntar
2. Faça as modificações SQL primeiro (via Supabase Dashboard)
3. Depois modifique o código Python
4. Teste localmente antes de fazer deploy
5. Documente as alterações feitas

---

**Prioridade:** 🔴 ALTA
**Tempo estimado:** 1-2 horas
**Impacto:** Aumentar taxa de geocoding de 22% para 50%+
