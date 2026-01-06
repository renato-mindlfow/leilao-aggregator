"""
Investigar como acessar imóveis no Freitas Leiloeiro.
"""
import httpx
import json

BASE_URL = "https://www.freitasleiloeiro.com.br"

# Testar diferentes abordagens
print("="*70)
print("INVESTIGANDO IMÓVEIS - FREITAS LEILOEIRO")
print("="*70)

headers = {
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0',
    'Referer': BASE_URL + '/',
    'X-Requested-With': 'XMLHttpRequest',
}

# 1. Testar endpoint de destaques com diferentes tipos
print("\n[1/4] Testando tipos de destaques...")
for tipo in [1, 2, 3, 4, 5]:
    try:
        url = f"{BASE_URL}/Leiloes/ListarLeiloesDestaques?tipoDestaque={tipo}"
        r = httpx.get(url, headers=headers, timeout=10, verify=False)
        if r.status_code == 200 and 'json' in r.headers.get('content-type', ''):
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"  Tipo {tipo}: {len(data)} leilões")
                # Verificar se tem imóveis nos lotes
                total_lotes = sum(len(l.get('lotes', [])) for l in data)
                print(f"    Total lotes: {total_lotes}")
    except:
        pass

# 2. Testar PesquisarDestaques com parâmetros
print("\n[2/4] Testando PesquisarDestaques...")
# Parâmetros vistos nas requisições de rede
test_url = f"{BASE_URL}/Leiloes/PesquisarDestaques?LeilaoId=7596&Nome=&Categoria=0&TipoLoteId=0&FaixaValor=0&Condicao=&PatioId=0&AnoModeloMin=0&AnoModeloMax=0&ArCondicionado=false&DirecaoAssistida=false&Estado=&Cidade=&ClienteSclId=0&PageNumber=1&TopRows=12&LotesDestaque=1%2C11%2C30%2C31%2C615%2C755%2C634%2C684%2C708%2C709"
try:
    r = httpx.get(test_url, headers=headers, timeout=10, verify=False)
    if r.status_code == 200:
        if 'json' in r.headers.get('content-type', ''):
            data = r.json()
            print(f"  [OK] Retornou JSON: {type(data)}")
            if isinstance(data, list):
                print(f"    Itens: {len(data)}")
            elif isinstance(data, dict):
                print(f"    Keys: {list(data.keys())[:10]}")
        else:
            print(f"  [INFO] Retornou HTML ({len(r.text)} bytes)")
except Exception as e:
    print(f"  [ERRO] {e}")

# 3. Testar URLs de imóveis
print("\n[3/4] Testando URLs de imóveis...")
imoveis_urls = [
    "/imoveis",
    "/Leiloes/Imoveis",
    "/Leiloes?Categoria=3",
    "/Leiloes?TipoLoteId=3",
]

for path in imoveis_urls:
    try:
        url = BASE_URL + path
        r = httpx.get(url, timeout=10, verify=False, follow_redirects=True)
        if r.status_code == 200:
            html = r.text.lower()
            if any(term in html for term in ['imovel', 'lote', 'leilao']):
                print(f"  [OK] {path} - parece ter conteúdo de imóveis")
                # Contar indicadores
                count = html.count('lote') + html.count('imovel')
                print(f"    Indicadores: {count}")
    except:
        pass

# 4. Verificar estrutura de dados dos destaques
print("\n[4/4] Analisando estrutura de dados...")
try:
    url = f"{BASE_URL}/Leiloes/ListarLeiloesDestaques?tipoDestaque=1"
    r = httpx.get(url, headers=headers, timeout=10, verify=False)
    if r.status_code == 200 and 'json' in r.headers.get('content-type', ''):
        data = r.json()
        if data and isinstance(data, list):
            primeiro = data[0]
            print(f"  Estrutura do primeiro leilão:")
            print(f"    Keys: {list(primeiro.keys())}")
            if 'lotes' in primeiro:
                lotes = primeiro['lotes']
                if lotes and len(lotes) > 0:
                    print(f"    Primeiro lote keys: {list(lotes[0].keys())[:10]}")
                    # Verificar se tem categoria ou tipo
                    primeiro_lote = lotes[0]
                    if 'categoria' in primeiro_lote or 'tipo' in primeiro_lote:
                        print(f"    Categoria/Tipo: {primeiro_lote.get('categoria') or primeiro_lote.get('tipo')}")
except Exception as e:
    print(f"  [ERRO] {e}")

