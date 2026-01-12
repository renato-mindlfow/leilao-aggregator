"""
Script para baixar CSVs da Caixa usando ScrapingBee para bypass de proteção anti-bot.
"""

import os
import httpx
import time

# Tentar carregar de .env se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv não instalado, usar apenas variáveis de ambiente

SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")
ESTADOS = ["SP", "RJ", "MG", "PR", "RS", "BA", "GO", "SC", "PE", "CE", "DF", "ES", "MA", "MT", "MS", "PB", "RN", "PI", "AL", "SE", "RO", "TO", "AC", "AP", "AM", "PA", "RR"]
OUTPUT_DIR = "data/caixa"

def download_via_scrapingbee(uf):
    """Baixa CSV usando ScrapingBee para bypass de proteção"""
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'false',
        'premium_proxy': 'true',
        'country_code': 'br',
    }
    
    try:
        response = httpx.get(
            "https://app.scrapingbee.com/api/v1/",
            params=params,
            timeout=60
        )
        
        response.raise_for_status()
        
        # Ler conteúdo com encoding correto (latin-1 para CSVs da Caixa)
        try:
            content = response.content.decode('latin-1')
        except UnicodeDecodeError:
            # Fallback para UTF-8 se latin-1 não funcionar
            content = response.text
        
        # Verificar se é CSV (não HTML)
        if content.startswith('<!') or '<html' in content.lower()[:500] or 'captcha' in content.lower()[:500]:
            print(f"ERRO {uf}: Bloqueado (HTML/CAPTCHA retornado)")
            return False
        
        # Verificar se tem cabeçalho CSV esperado
        # O CSV usa "N° do imóvel" (símbolo de grau °) e não "Nº do imóvel" (ordinal º)
        header_variants = [
            'N° do imóvel',  # Símbolo de grau (o correto)
            'Nº do imóvel',  # Símbolo ordinal (variação)
            'N do imvel',    # Sem símbolo e sem acentos
            'N do imovel',   # Sem símbolo e sem acento no ó
            'NUMERO',        # Maiúsculas
            'Número',        # Com acento
            'Lista de Imóveis da Caixa',  # Título do arquivo
        ]
        
        # Verificar se algum dos padrões está presente
        content_upper = content.upper()[:1000]
        has_valid_header = any(
            variant in content or variant.upper() in content_upper 
            for variant in header_variants
        )
        
        if not has_valid_header:
            print(f"ERRO {uf}: Arquivo nao parece ser CSV valido")
            print(f"  Primeiros 200 chars: {repr(content[:200])}")
            return False
        
        # Salvar CSV
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = f"{OUTPUT_DIR}/Lista_imoveis_{uf}.csv"
        with open(filepath, 'w', encoding='latin-1') as f:
            f.write(content)
        
        lines = len(content.split('\n'))
        size_kb = len(content.encode('latin-1')) / 1024
        print(f"OK {uf}: {lines} linhas ({size_kb:.2f} KB)")
        return True
        
    except httpx.HTTPStatusError as e:
        print(f"ERRO {uf}: HTTP {e.response.status_code}")
        if e.response.status_code == 401:
            print("  -> Verifique se SCRAPINGBEE_API_KEY esta correta")
        return False
    except Exception as e:
        print(f"ERRO {uf}: {str(e)[:80]}")
        return False

def main():
    print("=" * 60)
    print("Download CSVs da Caixa usando ScrapingBee")
    print("=" * 60)
    print()
    
    if not SCRAPINGBEE_API_KEY:
        print("ERRO: Configure SCRAPINGBEE_API_KEY")
        print("  Exemplo: export SCRAPINGBEE_API_KEY='sua-chave-aqui'")
        print("  Ou no Windows: $env:SCRAPINGBEE_API_KEY='sua-chave-aqui'")
        return
    
    print(f"API Key configurada: {SCRAPINGBEE_API_KEY[:10]}...")
    print(f"Total de estados: {len(ESTADOS)}")
    print()
    
    sucesso = 0
    falha = 0
    
    for i, uf in enumerate(ESTADOS):
        print(f"[{i+1}/{len(ESTADOS)}] Processando {uf}...", end=" ")
        if download_via_scrapingbee(uf):
            sucesso += 1
        else:
            falha += 1
        
        # Rate limiting: 2 segundos entre requisições
        if i < len(ESTADOS) - 1:
            time.sleep(2)
    
    print()
    print("=" * 60)
    print(f"Download completo!")
    print(f"  Sucesso: {sucesso}")
    print(f"  Falhas: {falha}")
    print("=" * 60)
    
    # Mostrar estatísticas dos arquivos baixados
    if sucesso > 0:
        print()
        print("Arquivos validos baixados:")
        print("-" * 60)
        total_lines = 0
        total_size = 0
        
        for uf in ESTADOS:
            filepath = f"{OUTPUT_DIR}/Lista_imoveis_{uf}.csv"
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        lines = sum(1 for _ in f)
                    size = os.path.getsize(filepath)
                    size_mb = size / (1024 * 1024)
                    total_lines += lines
                    total_size += size
                    print(f"  {uf}: {lines:>6} linhas  {size_mb:>6.2f} MB")
                except:
                    pass
        
        print("-" * 60)
        print(f"  TOTAL: {total_lines:>6} linhas  {total_size/(1024*1024):>6.2f} MB")

if __name__ == "__main__":
    main()

