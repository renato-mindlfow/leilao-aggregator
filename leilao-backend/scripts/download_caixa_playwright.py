"""
Script para baixar CSVs da Caixa usando Playwright com stealth mode.
Contorna proteção anti-bot usando navegador real.
"""

import asyncio
from playwright.async_api import async_playwright
import os
import time

ESTADOS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
OUTPUT_DIR = "data/caixa"

async def download_estado(page, uf):
    """Baixa CSV de um estado usando navegador real"""
    url = f"https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
    filepath = f"{OUTPUT_DIR}/Lista_imoveis_{uf}.csv"
    
    try:
        # Tentar usar request direto primeiro (mais rápido e usa cookies da sessão)
        response = await page.request.get(url, timeout=30000)
        
        if not response.ok:
            print(f"ERRO {uf}: HTTP {response.status}")
            return False
        
        content = await response.body()
        
        # Salvar arquivo
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Verificar se é CSV válido (não HTML)
        content_str = content.decode('latin-1', errors='ignore')
        
        if '<html' in content_str.lower() or 'captcha' in content_str.lower() or 'bot manager' in content_str.lower():
            print(f"ERRO {uf}: Bloqueado (HTML/CAPTCHA recebido)")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
        
        # Verificar se tem cabeçalho CSV esperado
        if 'Nº do imóvel' in content_str or 'N do imvel' in content_str or 'NUMERO' in content_str.upper():
            lines = len(content_str.split('\n'))
            size_kb = len(content) / 1024
            print(f"OK {uf}: {lines} linhas ({size_kb:.2f} KB)")
            return True
        else:
            print(f"ERRO {uf}: Arquivo nao parece ser CSV valido")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"ERRO {uf}: {error_msg[:80]}")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        return False

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("Download CSVs da Caixa usando Playwright")
    print("=" * 60)
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            viewport={'width': 1920, 'height': 1080},
            timezone_id='America/Sao_Paulo',
        )
        
        # Stealth scripts para ocultar automação
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });
        """)
        
        page = await context.new_page()
        
        # Primeiro, visitar a página principal para pegar cookies e estabelecer sessão
        print("Acessando pagina principal para estabelecer sessao...")
        try:
            await page.goto("https://venda-imoveis.caixa.gov.br/", wait_until='domcontentloaded', timeout=60000)
            
            # Aguardar e interagir com a página para parecer mais humano
            await asyncio.sleep(2)
            
            # Tentar rolar a página (simula interação humana)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)
            
            # Aguardar mais tempo para validação anti-bot processar
            await asyncio.sleep(5)
            
            print("Sessao estabelecida. Iniciando downloads...\n")
        except Exception as e:
            print(f"Aviso: Erro ao acessar pagina principal: {str(e)[:80]}")
            print("Continuando mesmo assim...\n")
        
        sucesso = 0
        falha = 0
        
        for i, uf in enumerate(ESTADOS):
            if await download_estado(page, uf):
                sucesso += 1
            else:
                falha += 1
            
            # Delay de 5 segundos entre downloads (exceto o último)
            if i < len(ESTADOS) - 1:
                await asyncio.sleep(5)
        
        await browser.close()
    
    print()
    print("=" * 60)
    print(f"Download completo!")
    print(f"  Sucesso: {sucesso}")
    print(f"  Falhas: {falha}")
    print("=" * 60)
    
    # Mostrar estatísticas dos arquivos baixados
    if sucesso > 0:
        print()
        print("Arquivos válidos baixados:")
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
    asyncio.run(main())

