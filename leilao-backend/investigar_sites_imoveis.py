"""
Script para investigar se sites têm imóveis próprios ou são agregadores.
Acessa cada site e tenta encontrar a página de imóveis.
"""
import httpx
import json
from pathlib import Path
from urllib.parse import urljoin

SITES = [
    {"id": "lancenoleilao", "name": "Lance no Leilão", "url": "https://www.lancenoleilao.com.br"},
    {"id": "freitasleiloeiro", "name": "Freitas Leiloeiro", "url": "https://www.freitasleiloeiro.com.br"},
]

def test_imoveis_urls(site):
    """Testa diferentes URLs de imóveis"""
    urls_to_test = [
        "/imoveis",
        "/leilao-de-imoveis",
        "/leiloes/imoveis",
        "/categoria/imoveis",
        "/busca?tipo=imoveis",
        "/leiloes?categoria=imoveis",
    ]
    
    results = []
    for path in urls_to_test:
        try:
            full_url = urljoin(site['url'], path)
            r = httpx.get(full_url, timeout=10, follow_redirects=True, verify=False)
            if r.status_code == 200:
                html = r.text.lower()
                # Verifica se parece ser página de listagem
                if any(term in html for term in ['imovel', 'leilao', 'lote', 'lance', 'propriedade']):
                    # Contar quantos cards/items aparecem (aproximado)
                    card_count = html.count('card') + html.count('item') + html.count('lote')
                    results.append({
                        "url": path,
                        "status": 200,
                        "has_content": True,
                        "card_indicators": card_count
                    })
        except Exception as e:
            results.append({
                "url": path,
                "status": "error",
                "error": str(e)
            })
    
    return results

def check_if_uses_superbid_api(site):
    """Verifica se o site usa API Superbid olhando o HTML"""
    try:
        r = httpx.get(site['url'], timeout=10, verify=False)
        html = r.text
        
        # Procurar por referências à API Superbid
        indicators = [
            'offer-query.superbid.net',
            'superbid',
            'storeId',
            'portalId',
        ]
        
        found = []
        for indicator in indicators:
            if indicator.lower() in html.lower():
                found.append(indicator)
        
        return found
    except:
        return []

print("="*70)
print("INVESTIGAÇÃO: Sites têm imóveis próprios ou são agregadores?")
print("="*70)

for site in SITES:
    print(f"\n{site['name']} ({site['url']})")
    print("-" * 70)
    
    # 1. Verificar se usa API Superbid
    print("  [1/3] Verificando uso de API Superbid...")
    api_indicators = check_if_uses_superbid_api(site)
    if api_indicators:
        print(f"    [OK] Encontrados indicadores: {', '.join(api_indicators)}")
        print(f"    → Provável agregador da Superbid")
    else:
        print(f"    [INFO] Nenhum indicador de API Superbid encontrado")
    
    # 2. Testar URLs de imóveis
    print("  [2/3] Testando URLs de imóveis...")
    url_results = test_imoveis_urls(site)
    if url_results:
        valid_urls = [r for r in url_results if r.get('has_content')]
        if valid_urls:
            print(f"    [OK] Encontradas {len(valid_urls)} URLs válidas:")
            for r in valid_urls:
                print(f"      - {r['url']} (indicadores: {r.get('card_indicators', 0)})")
        else:
            print(f"    [WARN] URLs testadas mas nenhuma com conteúdo de imóveis")
    else:
        print(f"    [WARN] Nenhuma URL de imóveis encontrada")
    
    # 3. Conclusão
    print("  [3/3] Conclusão:")
    if api_indicators:
        print(f"    [AGREGADOR] Usa API Superbid, provavelmente sem inventario proprio")
    else:
        print(f"    [POSSIVEL PROPRIO] Nao encontrou indicadores de API Superbid")

