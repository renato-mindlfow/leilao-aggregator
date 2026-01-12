import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SCRAPINGBEE_API_KEY")
url = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_SP.csv"

params = {
    'api_key': API_KEY,
    'url': url,
    'render_js': 'false',
    'premium_proxy': 'true',
    'country_code': 'br',
}

print(f"Baixando SP via ScrapingBee...")
response = httpx.get("https://app.scrapingbee.com/api/v1/", params=params, timeout=60)

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
print(f"Tamanho: {len(response.content)} bytes")

# Detectar encoding
content_bytes = response.content
try:
    # Tentar UTF-8 primeiro
    content_text = content_bytes.decode('utf-8')
    encoding = 'utf-8'
except UnicodeDecodeError:
    try:
        # Tentar Latin-1 (compatível com todos os bytes)
        content_text = content_bytes.decode('latin-1')
        encoding = 'latin-1'
    except:
        # Fallback para ISO-8859-1
        content_text = content_bytes.decode('iso-8859-1')
        encoding = 'iso-8859-1'

print(f"Encoding detectado: {encoding}")

# Salvar resposta bruta primeiro
os.makedirs("data/caixa", exist_ok=True)
with open("data/caixa/debug_sp_raw.txt", "w", encoding="utf-8", errors='replace') as f:
    f.write(content_text)

# Tentar mostrar primeiros caracteres de forma segura
try:
    safe_preview = content_text[:500].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    print(f"\nPrimeiros 500 caracteres:")
    print(safe_preview)
except:
    print(f"\nPrimeiros 500 bytes (hex):")
    print(content_bytes[:500].hex())

try:
    safe_tail = content_text[-200:].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    print(f"\n\nÚltimos 200 caracteres:")
    print(safe_tail)
except:
    print(f"\n\nÚltimos 200 bytes (hex):")
    print(content_bytes[-200:].hex())

print(f"\nResposta salva em data/caixa/debug_sp_raw.txt")

