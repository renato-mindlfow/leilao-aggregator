"""
Verifica rapidamente quais sites do Tier 2 têm sistema próprio vs Superbid.
"""
import httpx
import json
from pathlib import Path
from typing import Dict, List

SITES = [
    {"id": "superbid", "name": "Superbid", "url": "https://www.superbid.net"},
    {"id": "lancenoleilao", "name": "Lance no Leilão", "url": "https://www.lancenoleilao.com.br"},
    {"id": "lut", "name": "LUT", "url": "https://www.lut.com.br"},
    {"id": "bigleilao", "name": "Big Leilão", "url": "https://www.bigleilao.com.br"},
    {"id": "vialeiloes", "name": "Via Leilões", "url": "https://www.vialeiloes.com.br"},
    {"id": "freitasleiloeiro", "name": "Freitas Leiloeiro", "url": "https://www.freitasleiloeiro.com.br"},
    {"id": "frazaoleiloes", "name": "Frazão Leilões", "url": "https://www.frazaoleiloes.com.br"},
    {"id": "francoleiloes", "name": "Franco Leilões", "url": "https://www.francoleiloes.com.br"},
    {"id": "lancejudicial", "name": "Lance Judicial", "url": "https://www.lancejudicial.com.br"},
    {"id": "leiloesfreire", "name": "Leilões Freire", "url": "https://www.leiloesfreire.com.br"},
    {"id": "bfrcontabil", "name": "BFR Contábil", "url": "https://www.bfrcontabil.com.br"},
    {"id": "kronbergleiloes", "name": "Kronberg Leilões", "url": "https://www.kronbergleiloes.com.br"},
    {"id": "leilomaster", "name": "LeiloMaster", "url": "https://www.leilomaster.com.br"},
    {"id": "nossoleilao", "name": "Nossos Leilão", "url": "https://www.nossoleilao.com.br"},
    {"id": "liderleiloes", "name": "Líder Leilões", "url": "https://www.liderleiloes.com.br"},
]

def check_system_type(site: Dict) -> Dict:
    """Verifica se o site usa Superbid ou sistema próprio"""
    result = {
        "site": site['name'],
        "url": site['url'],
        "system_type": "unknown",
        "indicators": [],
        "api_endpoints": []
    }
    
    try:
        r = httpx.get(site['url'], timeout=10, follow_redirects=True, verify=False)
        html = r.text.lower()
        
        # Indicadores de Superbid
        superbid_indicators = [
            'offer-query.superbid.net',
            'superbid',
            'storeid',
            'portalid',
        ]
        
        # Indicadores de sistema próprio
        proprio_indicators = [
            '/leiloes/listar',
            '/leiloes/pesquisar',
            '/api/leiloes',
            'asp.net',
            'mvc',
            'sistema proprio',
        ]
        
        # Verificar Superbid
        for indicator in superbid_indicators:
            if indicator in html:
                result['indicators'].append(f"Superbid: {indicator}")
                result['system_type'] = "superbid"
        
        # Verificar sistema próprio
        for indicator in proprio_indicators:
            if indicator in html:
                result['indicators'].append(f"Proprio: {indicator}")
                if result['system_type'] == "unknown":
                    result['system_type'] = "proprio"
        
        # Procurar por endpoints de API
        import re
        api_patterns = [
            r'/leiloes/[a-z]+',
            r'/api/[a-z]+',
            r'/leilao/[a-z]+',
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html)
            if matches:
                result['api_endpoints'].extend(list(set(matches))[:5])
        
    except Exception as e:
        result['error'] = str(e)
        result['system_type'] = "error"
    
    return result

print("="*70)
print("VERIFICANDO TIPO DE SISTEMA - TIER 2")
print("="*70)

results = []
superbid_sites = []
proprio_sites = []

for site in SITES:
    print(f"\n{site['name']}...", end=" ", flush=True)
    result = check_system_type(site)
    results.append(result)
    
    if result['system_type'] == "superbid":
        print("[SUPERBID]")
        superbid_sites.append(site['id'])
    elif result['system_type'] == "proprio":
        print("[PROPRIO]")
        proprio_sites.append(site['id'])
    else:
        print(f"[{result['system_type'].upper()}]")

print("\n" + "="*70)
print("RESUMO")
print("="*70)
print(f"\nSites Superbid (cobertos por superbid_agregado): {len(superbid_sites)}")
for sid in superbid_sites:
    print(f"  - {sid}")

print(f"\nSites com sistema próprio (requerem config individual): {len(proprio_sites)}")
for sid in proprio_sites:
    print(f"  - {sid}")

print(f"\nSites não identificados: {len(SITES) - len(superbid_sites) - len(proprio_sites)}")

# Salvar resultado
output = {
    "superbid_sites": superbid_sites,
    "proprio_sites": proprio_sites,
    "details": results
}

with open("sistemas_verificados.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n[OK] Resultado salvo em: sistemas_verificados.json")

