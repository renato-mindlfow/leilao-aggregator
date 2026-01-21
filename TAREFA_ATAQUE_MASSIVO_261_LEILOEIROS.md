# 🚀 TAREFA: ATAQUE MASSIVO - COBRIR 261 LEILOEIROS

**Data:** 20/01/2026  
**Prioridade:** MÁXIMA  
**Objetivo:** Maximizar cobertura de leiloeiros no menor tempo possível

---

## 📊 SITUAÇÃO ATUAL

| Status | Sites | % | Ação |
|--------|-------|---|------|
| ✅ Funcionando | 28 | 9.7% | Manter |
| ⚠️ Já funcionaram | 32 | 11.1% | Re-crawl rápido |
| ❌ Nunca funcionaram | 102 | 35.3% | Investigar |
| ⏳ **NUNCA TENTADOS** | **127** | **43.9%** | **PRIORIDADE!** |
| **TOTAL GAP** | **261** | **90.3%** | - |

---

## 🎯 ESTRATÉGIA: 3 ONDAS DE ATAQUE

### ONDA 1: Sites PENDENTES (127) - Tempo: 1-2 horas
**Maior ROI - nunca foram tentados!**

```powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend

# 1. Extrair lista de URLs pendentes
python -c "
import csv
with open('../docs/LISTA_MESTRE_LEILOEIROS.csv', 'r') as f:
    reader = csv.DictReader(f)
    pendentes = [r['website'] for r in reader if r['scrape_status'] == 'pending']
    
with open('config/sites_pendentes.txt', 'w') as f:
    f.write('\n'.join(pendentes))
    
print(f'✅ {len(pendentes)} sites pendentes salvos em config/sites_pendentes.txt')
"

# 2. Descobrir paths automaticamente
python scripts/descobrir_paths.py --input config/sites_pendentes.txt --output config/paths_pendentes.json --batch-size 20

# 3. Executar TIER 1 (HTTP) nos sites descobertos
python scripts/extractors/extrator_tier1_http.py --config config/paths_pendentes.json --output logs/extracao_onda1/

# 4. Sites que falharam no TIER 1, enviar para TIER 2 (Playwright)
python scripts/extractors/extrator_tier2_stealth.py --failed logs/extracao_onda1/failed_tier1.json --output logs/extracao_onda1/
```

**Resultado esperado:** 60-80% dos 127 sites (~76-100 sites) funcionando

---

### ONDA 2: Sites com ERRO que JÁ funcionaram (32) - Tempo: 30 min
**Esses já extraíram antes - só precisam de recrawl**

```powershell
# 1. Extrair lista de sites que já funcionaram
python -c "
import csv
with open('../docs/LISTA_MESTRE_LEILOEIROS.csv', 'r') as f:
    reader = csv.DictReader(f)
    ja_funcionaram = [r['website'] for r in reader 
                      if r['scrape_status'] == 'error' 
                      and int(r['property_count'] or 0) > 0]
    
with open('config/sites_recrawl.txt', 'w') as f:
    f.write('\n'.join(ja_funcionaram))
    
print(f'✅ {len(ja_funcionaram)} sites para recrawl salvos')
"

# 2. Tentar recrawl direto (já temos os paths históricos)
python scripts/extractors/extrator_tier2_stealth.py --sites config/sites_recrawl.txt --output logs/extracao_onda2/
```

**Resultado esperado:** 80-90% dos 32 sites (~26-29 sites) funcionando

---

### ONDA 3: Sites que NUNCA funcionaram (102) - Tempo: 2-3 horas
**Esses são mais difíceis - análise necessária**

```powershell
# 1. Extrair lista
python -c "
import csv
with open('../docs/LISTA_MESTRE_LEILOEIROS.csv', 'r') as f:
    reader = csv.DictReader(f)
    nunca_funcionaram = [r['website'] for r in reader 
                         if r['scrape_status'] == 'error' 
                         and int(r['property_count'] or 0) == 0]
    
with open('config/sites_investigar.txt', 'w') as f:
    f.write('\n'.join(nunca_funcionaram))
    
print(f'✅ {len(nunca_funcionaram)} sites para investigar')
"

# 2. Primeiro: verificar se sites estão online
python scripts/verificar_sites_online.py --input config/sites_investigar.txt --output config/sites_online.json

# 3. Sites online: tentar descobrir paths
python scripts/descobrir_paths.py --input config/sites_online.json --output config/paths_investigar.json

# 4. Executar extração
python scripts/extractors/extrator_tier2_stealth.py --config config/paths_investigar.json --output logs/extracao_onda3/
```

**Resultado esperado:** 30-50% dos 102 sites (~30-50 sites) funcionando

---

## 📋 SCRIPT MESTRE: executar_ataque_massivo.py

```python
#!/usr/bin/env python
"""
ATAQUE MASSIVO - Cobrir todos os 261 leiloeiros pendentes
"""

import os
import sys
import json
import csv
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Configuração
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs" / "ataque_massivo" / datetime.now().strftime("%Y%m%d_%H%M%S")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Importar extratores
sys.path.insert(0, str(BASE_DIR / "scripts"))
from extractors.extrator_tier1_http import ExtratorTier1
from extractors.extrator_tier2_stealth import ExtratorTier2
from descobrir_paths import descobrir_path_automatico

def carregar_leiloeiros_csv():
    """Carrega lista mestre de leiloeiros."""
    csv_path = BASE_DIR.parent / "docs" / "LISTA_MESTRE_LEILOEIROS.csv"
    leiloeiros = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leiloeiros.append(row)
    return leiloeiros

def classificar_leiloeiros(leiloeiros):
    """Classifica leiloeiros por prioridade de ataque."""
    return {
        'pendentes': [l for l in leiloeiros if l['scrape_status'] == 'pending'],
        'recrawl': [l for l in leiloeiros if l['scrape_status'] == 'error' and int(l['property_count'] or 0) > 0],
        'investigar': [l for l in leiloeiros if l['scrape_status'] == 'error' and int(l['property_count'] or 0) == 0],
    }

async def processar_onda(nome, sites, tier1, tier2):
    """Processa uma onda de sites."""
    print(f"\n{'='*60}")
    print(f"🌊 ONDA: {nome} ({len(sites)} sites)")
    print(f"{'='*60}")
    
    resultados = {
        'total': len(sites),
        'sucesso_tier1': 0,
        'sucesso_tier2': 0,
        'falha': 0,
        'imoveis': 0,
        'detalhes': []
    }
    
    for i, site in enumerate(sites, 1):
        url = site['website']
        print(f"\n[{i}/{len(sites)}] {url}")
        
        # Tentar descobrir path
        path = await descobrir_path_automatico(url)
        if not path:
            path = '/imoveis'  # fallback
        
        url_completa = url.rstrip('/') + path
        
        # Tentar TIER 1 primeiro
        resultado_t1 = await tier1.extrair(url_completa)
        
        if resultado_t1['sucesso'] and resultado_t1['imoveis'] > 0:
            resultados['sucesso_tier1'] += 1
            resultados['imoveis'] += resultado_t1['imoveis']
            resultados['detalhes'].append({
                'url': url,
                'tier': 1,
                'imoveis': resultado_t1['imoveis']
            })
            print(f"   ✅ TIER 1: {resultado_t1['imoveis']} imóveis")
            continue
        
        # Se TIER 1 falhou, tentar TIER 2
        resultado_t2 = await tier2.extrair(url_completa)
        
        if resultado_t2['sucesso'] and resultado_t2['imoveis'] > 0:
            resultados['sucesso_tier2'] += 1
            resultados['imoveis'] += resultado_t2['imoveis']
            resultados['detalhes'].append({
                'url': url,
                'tier': 2,
                'imoveis': resultado_t2['imoveis']
            })
            print(f"   ✅ TIER 2: {resultado_t2['imoveis']} imóveis")
            continue
        
        # Falha em ambos
        resultados['falha'] += 1
        resultados['detalhes'].append({
            'url': url,
            'tier': None,
            'erro': resultado_t2.get('erro', 'Desconhecido')
        })
        print(f"   ❌ Falhou em ambos tiers")
        
        # Pequena pausa entre sites
        await asyncio.sleep(1)
    
    return resultados

async def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     🚀 ATAQUE MASSIVO - COBERTURA DE LEILOEIROS 🚀     ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Objetivo: Maximizar cobertura no menor tempo possível   ║
    ║  Estratégia: 3 ondas de ataque priorizadas               ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Carregar e classificar
    leiloeiros = carregar_leiloeiros_csv()
    classificados = classificar_leiloeiros(leiloeiros)
    
    print(f"📊 Sites carregados:")
    print(f"   • Pendentes (nunca tentados): {len(classificados['pendentes'])}")
    print(f"   • Recrawl (já funcionaram): {len(classificados['recrawl'])}")
    print(f"   • Investigar (nunca funcionaram): {len(classificados['investigar'])}")
    
    # Inicializar extratores
    tier1 = ExtratorTier1()
    tier2 = ExtratorTier2()
    
    resultados_totais = {
        'inicio': datetime.now().isoformat(),
        'ondas': {}
    }
    
    # ONDA 1: Pendentes (maior ROI)
    if classificados['pendentes']:
        resultados_totais['ondas']['pendentes'] = await processar_onda(
            "PENDENTES (Nunca Tentados)",
            classificados['pendentes'],
            tier1, tier2
        )
    
    # ONDA 2: Recrawl (já funcionaram)
    if classificados['recrawl']:
        resultados_totais['ondas']['recrawl'] = await processar_onda(
            "RECRAWL (Já Funcionaram)",
            classificados['recrawl'],
            tier1, tier2
        )
    
    # ONDA 3: Investigar (nunca funcionaram)
    if classificados['investigar']:
        resultados_totais['ondas']['investigar'] = await processar_onda(
            "INVESTIGAR (Nunca Funcionaram)",
            classificados['investigar'],
            tier1, tier2
        )
    
    resultados_totais['fim'] = datetime.now().isoformat()
    
    # Salvar resultados
    with open(LOGS_DIR / 'resultados_ataque.json', 'w', encoding='utf-8') as f:
        json.dump(resultados_totais, f, ensure_ascii=False, indent=2)
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DO ATAQUE MASSIVO")
    print("="*60)
    
    total_sucesso = 0
    total_imoveis = 0
    
    for nome, res in resultados_totais['ondas'].items():
        sucesso = res['sucesso_tier1'] + res['sucesso_tier2']
        total_sucesso += sucesso
        total_imoveis += res['imoveis']
        
        print(f"\n{nome.upper()}:")
        print(f"   Total: {res['total']}")
        print(f"   Sucesso TIER 1: {res['sucesso_tier1']}")
        print(f"   Sucesso TIER 2: {res['sucesso_tier2']}")
        print(f"   Falhas: {res['falha']}")
        print(f"   Imóveis: {res['imoveis']}")
        print(f"   Taxa: {sucesso/res['total']*100:.1f}%")
    
    print(f"\n{'='*60}")
    print(f"🎯 RESULTADO FINAL:")
    print(f"   Sites com sucesso: {total_sucesso}")
    print(f"   Imóveis extraídos: {total_imoveis}")
    print(f"   Logs salvos em: {LOGS_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎯 RESULTADO ESPERADO

| Onda | Sites | Taxa Esperada | Sucesso | Imóveis |
|------|-------|---------------|---------|---------|
| 1. Pendentes | 127 | 60-80% | ~76-100 | ~2.000-5.000 |
| 2. Recrawl | 32 | 80-90% | ~26-29 | ~500-1.000 |
| 3. Investigar | 102 | 30-50% | ~30-50 | ~500-1.500 |
| **TOTAL** | **261** | **50-70%** | **~130-180** | **~3.000-7.500** |

---

## ⏱️ TEMPO ESTIMADO

| Fase | Tempo |
|------|-------|
| Setup | 5 min |
| Onda 1 (127 sites) | 60-90 min |
| Onda 2 (32 sites) | 20-30 min |
| Onda 3 (102 sites) | 60-120 min |
| Consolidação | 10 min |
| **TOTAL** | **2.5-4 horas** |

---

## 📋 CHECKLIST DE EXECUÇÃO

### Preparação
- [ ] Verificar se scripts de extração estão funcionando
- [ ] Criar diretório de logs
- [ ] Exportar lista de leiloeiros atualizada

### Onda 1 - Pendentes
- [ ] Extrair 127 URLs pendentes
- [ ] Descobrir paths automaticamente
- [ ] Executar TIER 1
- [ ] Executar TIER 2 nos que falharam
- [ ] Consolidar resultados

### Onda 2 - Recrawl
- [ ] Extrair 32 URLs que já funcionaram
- [ ] Executar extração direta
- [ ] Consolidar resultados

### Onda 3 - Investigar
- [ ] Extrair 102 URLs problemáticas
- [ ] Verificar quais estão online
- [ ] Descobrir paths
- [ ] Executar extração
- [ ] Consolidar resultados

### Finalização
- [ ] Unir todos os imóveis
- [ ] Deduplicar
- [ ] Normalizar
- [ ] Persistir no Supabase
- [ ] Atualizar status na tabela auctioneers

---

## 🔧 SCRIPTS AUXILIARES NECESSÁRIOS

1. **verificar_sites_online.py** - Verifica se sites estão acessíveis
2. **atualizar_status_leiloeiros.py** - Atualiza status no banco após processamento

---

## 💡 DICAS DE OTIMIZAÇÃO

1. **Paralelizar**: Rodar TIER 1 em paralelo (até 10 sites simultâneos)
2. **Cache de paths**: Salvar paths descobertos para reuso
3. **Skip sites offline**: Não perder tempo com sites fora do ar
4. **Batch Supabase**: Inserir em lotes de 100-200 para performance

---

## 🚨 PONTOS DE ATENÇÃO

1. **Rate limiting**: Não bombardear sites (pausa de 1-2s entre requests)
2. **CloudFlare**: 40-50% dos sites podem ter proteção
3. **Sites offline**: Alguns podem estar fora do ar permanentemente
4. **Estrutura variada**: Cada site tem estrutura diferente

---

**FIM DA TAREFA**

**Comando para iniciar:**
```powershell
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/executar_ataque_massivo.py
```
