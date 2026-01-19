"""
Testa sites que reportaram 'nenhum imovel encontrado'
"""
import os
import sys
import io
import json
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# Carregar categorias
json_path = os.path.join(os.path.dirname(__file__), "leiloeiros_erro_categorizados.json")
with open(json_path, "r", encoding="utf-8") as f:
    categorias = json.load(f)

sites = categorias.get("nenhum_imovel", [])[:10]  # Top 10

print("=" * 70)
print("TESTANDO SITES 'NENHUM IMOVEL ENCONTRADO'")
print("=" * 70)

resultados = {
    "tem_imoveis": [],
    "sem_imoveis": [],
    "erro_acesso": []
}

for site in sites:
    print(f"\n[{site['nome']}]")
    print(f"  URL: {site['website']}")
    
    try:
        # Tentar acessar o site
        response = httpx.get(site['website'], timeout=30, follow_redirects=True)
        print(f"  Status: {response.status_code}")
        
        if response.status_code != 200:
            resultados["erro_acesso"].append(site)
            print(f"  ERRO: Status {response.status_code}")
            continue
        
        # Verificar se tem palavras-chave de imóveis
        content = response.text.lower()
        keywords = ['imóvel', 'imovel', 'leilão', 'leilao', 'apartamento', 'casa', 'terreno', 'lote']
        found = [k for k in keywords if k in content]
        
        # Contagens
        count_imovel = content.count('imóvel') + content.count('imovel')
        count_leilao = content.count('leilão') + content.count('leilao')
        
        if found and (count_imovel > 5 or count_leilao > 5):
            resultados["tem_imoveis"].append(site)
            print(f"  ✓ Keywords encontradas: {found}")
            print(f"  ✓ Contagens: imovel={count_imovel}, leilao={count_leilao}")
            print(f"  ACAO: CORRIGIR SCRAPER - Site parece ter imóveis")
        else:
            resultados["sem_imoveis"].append(site)
            print(f"  ✗ Poucas/nenhuma keyword de imoveis")
            print(f"  ✗ Contagens: imovel={count_imovel}, leilao={count_leilao}")
            print(f"  ACAO: Provavelmente sem imóveis ativos ou outro segmento")
            
    except Exception as e:
        resultados["erro_acesso"].append(site)
        print(f"  ✗ ERRO ao acessar: {e}")
        print(f"  ACAO: Site pode estar offline ou bloqueando acesso")

print("\n" + "=" * 70)
print("RESUMO")
print("=" * 70)
print(f"\nCom imóveis (para corrigir): {len(resultados['tem_imoveis'])}")
for site in resultados['tem_imoveis']:
    print(f"  - {site['nome']}: {site['website']}")

print(f"\nSem imóveis (ignorar): {len(resultados['sem_imoveis'])}")
for site in resultados['sem_imoveis']:
    print(f"  - {site['nome']}: {site['website']}")

print(f"\nErro de acesso: {len(resultados['erro_acesso'])}")
for site in resultados['erro_acesso']:
    print(f"  - {site['nome']}: {site['website']}")

# Salvar resultados
output_path = os.path.join(os.path.dirname(__file__), "leiloeiros_testados.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)
print(f"\nResultados salvos em: {output_path}")
