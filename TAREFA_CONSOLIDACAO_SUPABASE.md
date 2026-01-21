# 📋 TAREFA: Consolidação, Normalização e Persistência dos Imóveis

**Data:** 20/01/2026  
**Prioridade:** Alta  
**Tempo Estimado:** 2-3 horas  
**Custo:** $0

---

## 🎯 OBJETIVO

Consolidar todos os imóveis extraídos (TIER 1 + TIER 2), remover duplicatas, normalizar dados, validar imagens e persistir no Supabase.

---

## 📊 CONTEXTO ATUAL

| Fonte | Imóveis | Arquivo |
|-------|---------|---------|
| TIER 1 | 505 | `logs/extracao_fase2/tier1/tier1_resultados_*.json` |
| TIER 2 (original) | 1.088 | `logs/extracao_fase2/tier2/tier2_resultados_*.json` |
| TIER 2 (corrigido) | 531 | `logs/extracao_fase2/tier2/*_paths_corrigidos_*.json` |
| **TOTAL BRUTO** | **2.124** | - |

**Estimativa após deduplicação:** ~1.800-2.000 imóveis únicos

---

## ✅ FASE 1: CONSOLIDAÇÃO E DEDUPLICAÇÃO

### 1.1 Unir todos os arquivos JSON

```python
# Criar script: scripts/consolidar_imoveis.py

import json
import os
from glob import glob
from datetime import datetime

def carregar_todos_imoveis():
    """Carrega todos os imóveis de todos os tiers."""
    todos = []
    
    # Caminhos dos arquivos
    paths = [
        "logs/extracao_fase2/tier1/tier1_resultados_*.json",
        "logs/extracao_fase2/tier2/tier2_resultados_*.json",
        "logs/extracao_fase2/tier2/*_paths_corrigidos_*.json",
    ]
    
    for pattern in paths:
        for filepath in glob(pattern):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Pode ser lista ou dict com chave 'imoveis'
                    if isinstance(data, list):
                        todos.extend(data)
                    elif isinstance(data, dict):
                        imoveis = data.get('imoveis', data.get('properties', []))
                        if isinstance(imoveis, list):
                            todos.extend(imoveis)
                print(f"✅ Carregado: {filepath} ({len(data) if isinstance(data, list) else '?'} itens)")
            except Exception as e:
                print(f"❌ Erro ao carregar {filepath}: {e}")
    
    return todos

imoveis = carregar_todos_imoveis()
print(f"\n📊 Total bruto carregado: {len(imoveis)} imóveis")
```

### 1.2 Deduplicar por URL e Título

```python
def deduplicar_imoveis(imoveis):
    """Remove duplicatas por source_url e título normalizado."""
    
    vistos_url = set()
    vistos_titulo = set()
    unicos = []
    duplicatas = 0
    
    for imovel in imoveis:
        # Chave primária: source_url
        url = imovel.get('source_url', '').strip().lower()
        
        # Chave secundária: título normalizado + cidade + estado
        titulo = imovel.get('title', '').strip().lower()
        cidade = imovel.get('city', '').strip().lower()
        estado = imovel.get('state', '').strip().upper()
        chave_titulo = f"{titulo}|{cidade}|{estado}"
        
        # Verificar duplicata por URL
        if url and url in vistos_url:
            duplicatas += 1
            continue
        
        # Verificar duplicata por título+localização (se não tiver URL)
        if not url and chave_titulo in vistos_titulo:
            duplicatas += 1
            continue
        
        # Marcar como visto
        if url:
            vistos_url.add(url)
        if chave_titulo:
            vistos_titulo.add(chave_titulo)
        
        unicos.append(imovel)
    
    print(f"📊 Deduplicação: {len(imoveis)} → {len(unicos)} ({duplicatas} duplicatas removidas)")
    return unicos

imoveis_unicos = deduplicar_imoveis(imoveis)
```

### 1.3 Salvar arquivo consolidado

```python
def salvar_consolidado(imoveis, output_path):
    """Salva arquivo consolidado com metadados."""
    
    resultado = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_imoveis": len(imoveis),
            "fonte": "TIER 1 + TIER 2 (original + corrigido)",
            "deduplicado": True
        },
        "imoveis": imoveis
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Salvo: {output_path} ({len(imoveis)} imóveis)")

salvar_consolidado(imoveis_unicos, "logs/extracao_fase2/imoveis_consolidados_final.json")
```

---

## ✅ FASE 2: NORMALIZAÇÃO DE DADOS

### 2.1 Normalizar Title Case

```python
import re

def normalizar_titulo(texto):
    """Converte para Title Case inteligente."""
    if not texto:
        return texto
    
    # Palavras que devem ficar minúsculas (exceto início)
    excecoes = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'na', 'no', 'nas', 'nos', 'para', 'por', 'com'}
    
    palavras = texto.lower().split()
    resultado = []
    
    for i, palavra in enumerate(palavras):
        if i == 0 or palavra not in excecoes:
            resultado.append(palavra.capitalize())
        else:
            resultado.append(palavra)
    
    return ' '.join(resultado)

def normalizar_estado(estado):
    """Normaliza UF para 2 letras maiúsculas."""
    if not estado:
        return None
    
    estado = estado.strip().upper()
    
    # Mapeamento de nomes completos para siglas
    mapa_estados = {
        'ACRE': 'AC', 'ALAGOAS': 'AL', 'AMAPA': 'AP', 'AMAZONAS': 'AM',
        'BAHIA': 'BA', 'CEARA': 'CE', 'DISTRITO FEDERAL': 'DF', 'ESPIRITO SANTO': 'ES',
        'GOIAS': 'GO', 'MARANHAO': 'MA', 'MATO GROSSO': 'MT', 'MATO GROSSO DO SUL': 'MS',
        'MINAS GERAIS': 'MG', 'PARA': 'PA', 'PARAIBA': 'PB', 'PARANA': 'PR',
        'PERNAMBUCO': 'PE', 'PIAUI': 'PI', 'RIO DE JANEIRO': 'RJ', 'RIO GRANDE DO NORTE': 'RN',
        'RIO GRANDE DO SUL': 'RS', 'RONDONIA': 'RO', 'RORAIMA': 'RR', 'SANTA CATARINA': 'SC',
        'SAO PAULO': 'SP', 'SERGIPE': 'SE', 'TOCANTINS': 'TO'
    }
    
    # Se já é sigla válida
    estados_validos = set(mapa_estados.values())
    if estado in estados_validos:
        return estado
    
    # Tentar mapear nome completo
    if estado in mapa_estados:
        return mapa_estados[estado]
    
    # Inválido
    if estado == 'XX' or len(estado) != 2:
        return None
    
    return estado

def normalizar_categoria(categoria):
    """Normaliza categoria para padrão."""
    if not categoria:
        return 'Outro'
    
    categoria = categoria.strip().lower()
    
    mapa_categorias = {
        'apartamento': 'Apartamento',
        'apto': 'Apartamento',
        'apt': 'Apartamento',
        'casa': 'Casa',
        'residencia': 'Casa',
        'residencial': 'Casa',
        'terreno': 'Terreno',
        'lote': 'Terreno',
        'comercial': 'Comercial',
        'loja': 'Comercial',
        'sala': 'Comercial',
        'galpao': 'Comercial',
        'galpão': 'Comercial',
        'rural': 'Rural',
        'fazenda': 'Rural',
        'sitio': 'Rural',
        'sítio': 'Rural',
        'chacara': 'Rural',
        'chácara': 'Rural',
        'industrial': 'Industrial',
        'garagem': 'Garagem',
        'vaga': 'Garagem',
    }
    
    for chave, valor in mapa_categorias.items():
        if chave in categoria:
            return valor
    
    return 'Outro'

def normalizar_imovel(imovel):
    """Aplica todas as normalizações em um imóvel."""
    
    # Title Case
    if imovel.get('title'):
        imovel['title'] = normalizar_titulo(imovel['title'])
    if imovel.get('city'):
        imovel['city'] = normalizar_titulo(imovel['city'])
    if imovel.get('neighborhood'):
        imovel['neighborhood'] = normalizar_titulo(imovel['neighborhood'])
    
    # Estado (UF)
    if imovel.get('state'):
        imovel['state'] = normalizar_estado(imovel['state'])
    
    # Categoria
    if imovel.get('category'):
        imovel['category'] = normalizar_categoria(imovel['category'])
    
    # Limpar valores numéricos
    for campo in ['evaluation_value', 'first_auction_value', 'second_auction_value', 'area_total']:
        valor = imovel.get(campo)
        if valor and isinstance(valor, str):
            try:
                # Remover R$, pontos, trocar vírgula por ponto
                valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
                imovel[campo] = float(valor) if valor else None
            except:
                imovel[campo] = None
    
    return imovel

# Aplicar normalização em todos
imoveis_normalizados = [normalizar_imovel(im) for im in imoveis_unicos]
print(f"✅ Normalizados: {len(imoveis_normalizados)} imóveis")
```

---

## ✅ FASE 3: VALIDAÇÃO DE IMAGENS

### 3.1 Integrar image_validator.py

```python
# Usar o validador de imagens criado
# Copiar image_blacklist.json e image_validator.py para o projeto

from image_validator import ImageValidator

validator = ImageValidator('config/image_blacklist.json')

def validar_imagens(imoveis):
    """Valida e limpa URLs de imagens inválidas."""
    
    stats = {'validas': 0, 'invalidas': 0, 'sem_imagem': 0}
    
    for imovel in imoveis:
        url = imovel.get('image_url')
        
        if not url:
            stats['sem_imagem'] += 1
            continue
        
        is_valid, reason = validator.validate_url(url)
        
        if is_valid:
            stats['validas'] += 1
        else:
            stats['invalidas'] += 1
            imovel['image_url'] = None
            imovel['image_validation_error'] = reason
    
    print(f"📊 Validação de imagens:")
    print(f"   ✅ Válidas: {stats['validas']}")
    print(f"   ❌ Inválidas: {stats['invalidas']}")
    print(f"   ⚪ Sem imagem: {stats['sem_imagem']}")
    
    return imoveis

imoveis_validados = validar_imagens(imoveis_normalizados)
```

---

## ✅ FASE 4: PERSISTIR NO SUPABASE

### 4.1 Conectar ao Supabase

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados no .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Conectado ao Supabase")
```

### 4.2 Mapear para schema do banco

```python
import hashlib
from datetime import datetime

def gerar_id_unico(imovel):
    """Gera ID único baseado na URL ou título+localização."""
    url = imovel.get('source_url', '')
    if url:
        return hashlib.md5(url.encode()).hexdigest()[:32]
    
    # Fallback: título + cidade + estado
    chave = f"{imovel.get('title', '')}|{imovel.get('city', '')}|{imovel.get('state', '')}"
    return hashlib.md5(chave.encode()).hexdigest()[:32]

def mapear_para_schema(imovel):
    """Mapeia imóvel para schema da tabela properties."""
    
    return {
        'id': gerar_id_unico(imovel),
        'title': imovel.get('title'),
        'category': imovel.get('category', 'Outro'),
        'auction_type': imovel.get('auction_type', 'Extrajudicial'),
        'state': imovel.get('state'),
        'city': imovel.get('city'),
        'neighborhood': imovel.get('neighborhood'),
        'address': imovel.get('address'),
        'description': imovel.get('description'),
        'area_total': imovel.get('area_total'),
        'area_privativa': imovel.get('area_privativa'),
        'evaluation_value': imovel.get('evaluation_value'),
        'first_auction_value': imovel.get('first_auction_value'),
        'first_auction_date': imovel.get('first_auction_date'),
        'second_auction_value': imovel.get('second_auction_value'),
        'second_auction_date': imovel.get('second_auction_date'),
        'discount_percentage': imovel.get('discount_percentage'),
        'image_url': imovel.get('image_url'),
        'auctioneer_id': imovel.get('auctioneer_id'),
        'auctioneer_name': imovel.get('auctioneer_name'),
        'auctioneer_url': imovel.get('auctioneer_url'),
        'source_url': imovel.get('source_url'),
        'source': imovel.get('source', 'scraper_fase2'),
        'is_active': True,
        'is_duplicate': False,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'last_seen_at': datetime.utcnow().isoformat(),
    }
```

### 4.3 Inserir em lotes (batch)

```python
def inserir_no_supabase(imoveis, batch_size=100):
    """Insere imóveis no Supabase em lotes."""
    
    total = len(imoveis)
    inseridos = 0
    erros = 0
    
    for i in range(0, total, batch_size):
        batch = imoveis[i:i+batch_size]
        registros = [mapear_para_schema(im) for im in batch]
        
        try:
            # Upsert: insere ou atualiza se já existir
            response = supabase.table('properties').upsert(
                registros,
                on_conflict='id'
            ).execute()
            
            inseridos += len(batch)
            print(f"✅ Lote {i//batch_size + 1}: {len(batch)} imóveis ({inseridos}/{total})")
            
        except Exception as e:
            erros += len(batch)
            print(f"❌ Erro no lote {i//batch_size + 1}: {e}")
    
    print(f"\n📊 Resultado final:")
    print(f"   ✅ Inseridos: {inseridos}")
    print(f"   ❌ Erros: {erros}")
    print(f"   📊 Total: {total}")
    
    return inseridos, erros

# Executar inserção
inseridos, erros = inserir_no_supabase(imoveis_validados)
```

---

## ✅ FASE 5: EXPANDIR DESCOBERTA DE PATHS (17 sites restantes)

### 5.1 Identificar sites pendentes

```python
# Listar os 17 sites que ainda não foram processados com paths corretos
# Usar o script descobrir_paths.py já criado

# Executar:
# python scripts/descobrir_paths.py --sites sites_pendentes.txt --output config/paths_adicionais.json
```

### 5.2 Re-executar TIER 2 nos sites descobertos

```python
# Após descobrir os paths, executar:
# python scripts/executar_tier2_paths_corrigidos.py --config config/paths_adicionais.json
```

---

## 📋 CHECKLIST DE EXECUÇÃO

### Fase 1: Consolidação
- [ ] Carregar todos os JSONs (TIER 1 + TIER 2)
- [ ] Deduplicar por URL e título
- [ ] Salvar arquivo consolidado
- [ ] Verificar: ~1.800-2.000 imóveis únicos

### Fase 2: Normalização
- [ ] Aplicar Title Case (título, cidade, bairro)
- [ ] Normalizar UF (2 letras maiúsculas)
- [ ] Normalizar categorias (Apartamento, Casa, etc.)
- [ ] Limpar valores numéricos

### Fase 3: Validação de Imagens
- [ ] Copiar image_blacklist.json para config/
- [ ] Copiar image_validator.py para scripts/
- [ ] Executar validação
- [ ] Verificar: ~10-20% imagens removidas (logos, placeholders)

### Fase 4: Supabase
- [ ] Verificar .env com credenciais
- [ ] Testar conexão
- [ ] Inserir em lotes de 100
- [ ] Verificar no Supabase Dashboard

### Fase 5: Expansão (Opcional)
- [ ] Identificar 17 sites pendentes
- [ ] Executar descobrir_paths.py
- [ ] Re-executar TIER 2
- [ ] Consolidar novos imóveis (+300-500 esperados)

---

## 📊 RESULTADO ESPERADO

| Métrica | Valor |
|---------|-------|
| Imóveis únicos | ~1.800-2.000 |
| Normalizados | 100% |
| Imagens validadas | ~80-90% |
| Persistidos no Supabase | 100% |
| Sites adicionais (Fase 5) | +17 |
| Imóveis adicionais (Fase 5) | +300-500 |

---

## 🚀 COMANDO PARA INICIAR

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# Executar script completo de consolidação
python scripts/consolidar_e_persistir.py
```

---

## ⚠️ PONTOS DE ATENÇÃO

1. **Backup**: Fazer backup dos JSONs antes de processar
2. **Supabase**: Verificar se a tabela `properties` existe com schema correto
3. **Duplicatas**: Usar UPSERT para não duplicar se rodar novamente
4. **Logs**: Salvar log de execução para auditoria

---

**FIM DA TAREFA**
