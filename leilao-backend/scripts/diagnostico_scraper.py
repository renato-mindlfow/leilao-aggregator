#!/usr/bin/env python3
"""
Diagnóstico detalhado do LLMEnhancedScraper
Identifica por que sites não estão sendo extraídos
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from playwright.async_api import async_playwright

# Configurar logging detalhado
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Sites para diagnóstico
SITES_TESTE = [
    {"id": "megaleiloes", "name": "Mega Leilões", "url": "https://www.megaleiloes.com.br/imoveis"},
    {"id": "portalzuk", "name": "Portal Zuk", "url": "https://www.portalzuk.com.br/leilao-de-imoveis"},
    {"id": "superbid", "name": "Superbid", "url": "https://www.superbid.net/"},
    {"id": "sold", "name": "Sold", "url": "https://www.sold.com.br/"},
    {"id": "vivaleiloes", "name": "Viva Leilões", "url": "https://www.vivaleiloes.com.br/"},
]


async def diagnosticar_site(site: dict) -> dict:
    """Diagnóstico completo de um site."""
    resultado = {
        "site": site["name"],
        "url": site["url"],
        "etapas": [],
        "problema_detectado": None,
        "sugestao": None,
    }
    
    playwright = None
    browser = None
    
    try:
        print(f"\n{'='*60}")
        print(f"🔍 DIAGNOSTICANDO: {site['name']}")
        print(f"   URL: {site['url']}")
        print('='*60)
        
        # ETAPA 1: Iniciar Playwright
        print("\n[1/7] Iniciando Playwright...")
        playwright = await async_playwright().start()
        resultado["etapas"].append("✅ Playwright iniciado")
        
        # ETAPA 2: Lançar browser com stealth
        print("[2/7] Lançando browser com stealth mode...")
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
            ]
        )
        resultado["etapas"].append("✅ Browser lançado")
        
        # ETAPA 3: Criar contexto
        print("[3/7] Criando contexto do browser...")
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        
        # Injetar script anti-detecção
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        
        page = await context.new_page()
        resultado["etapas"].append("✅ Contexto criado com stealth")
        
        # ETAPA 4: Navegar para a página
        print("[4/7] Navegando para a página...")
        inicio = datetime.now()
        
        try:
            response = await page.goto(site["url"], wait_until='domcontentloaded', timeout=120000)
            tempo_navegacao = (datetime.now() - inicio).total_seconds()
            
            status_code = response.status if response else "N/A"
            print(f"   Status HTTP: {status_code}")
            print(f"   Tempo: {tempo_navegacao:.1f}s")
            
            if status_code == 403:
                resultado["problema_detectado"] = "BLOQUEIO 403 - Site detectou automação"
                resultado["sugestao"] = "Usar proxy rotativo ou stealth mais agressivo"
            elif status_code == 503:
                resultado["problema_detectado"] = "BLOQUEIO 503 - Cloudflare/WAF ativo"
                resultado["sugestao"] = "Usar ScrapingBee ou serviço anti-Cloudflare"
            elif status_code != 200:
                resultado["problema_detectado"] = f"Status HTTP inesperado: {status_code}"
                
            resultado["etapas"].append(f"✅ Navegação OK (HTTP {status_code}, {tempo_navegacao:.1f}s)")
            
        except Exception as e:
            resultado["etapas"].append(f"❌ Navegação falhou: {str(e)[:100]}")
            resultado["problema_detectado"] = "TIMEOUT ou erro de rede"
            resultado["sugestao"] = "Aumentar timeout ou verificar conectividade"
            return resultado
        
        # ETAPA 5: Aguardar JavaScript
        print("[5/7] Aguardando JavaScript carregar...")
        await asyncio.sleep(5)
        resultado["etapas"].append("✅ Aguardou 5s para JS")
        
        # ETAPA 6: Fazer scroll para lazy loading
        print("[6/7] Fazendo scroll para carregar conteúdo...")
        try:
            await page.evaluate("""
                async () => {
                    for (let i = 0; i < 5; i++) {
                        window.scrollBy(0, 500);
                        await new Promise(r => setTimeout(r, 500));
                    }
                    window.scrollTo(0, 0);
                }
            """)
            await asyncio.sleep(2)
            resultado["etapas"].append("✅ Scroll executado")
        except Exception as e:
            resultado["etapas"].append(f"⚠️ Scroll falhou: {str(e)[:50]}")
        
        # ETAPA 7: Analisar conteúdo da página
        print("[7/7] Analisando conteúdo da página...")
        
        html = await page.content()
        text = await page.evaluate("() => document.body.innerText")
        
        html_len = len(html)
        text_len = len(text)
        
        print(f"   HTML: {html_len} chars")
        print(f"   Texto visível: {text_len} chars")
        
        # Verificar sinais de bloqueio
        bloqueio_sinais = [
            "access denied",
            "blocked",
            "captcha",
            "cloudflare",
            "ray id",
            "forbidden",
            "não autorizado",
            "acesso negado",
            "verificação",
            "robô",
            "bot detected",
        ]
        
        text_lower = text.lower()
        for sinal in bloqueio_sinais:
            if sinal in text_lower:
                resultado["problema_detectado"] = f"BLOQUEIO DETECTADO: '{sinal}' encontrado na página"
                resultado["sugestao"] = "Site tem proteção anti-bot ativa"
                resultado["etapas"].append(f"❌ Bloqueio detectado: {sinal}")
                break
        
        # Verificar se há conteúdo de imóveis
        imoveis_sinais = [
            "apartamento",
            "casa",
            "terreno",
            "imóvel",
            "imovel",
            "leilão",
            "leilao",
            "lance",
            "avaliação",
            "avaliacao",
        ]
        
        imoveis_encontrados = sum(1 for s in imoveis_sinais if s in text_lower)
        print(f"   Sinais de imóveis: {imoveis_encontrados}/10")
        
        if imoveis_encontrados >= 3:
            resultado["etapas"].append(f"✅ Conteúdo de imóveis detectado ({imoveis_encontrados} sinais)")
            
            if not resultado["problema_detectado"]:
                resultado["problema_detectado"] = "Conteúdo carregou mas LLM não extraiu"
                resultado["sugestao"] = "Verificar prompt do LLM ou aumentar contexto"
        else:
            resultado["etapas"].append(f"⚠️ Poucos sinais de imóveis ({imoveis_encontrados})")
            
            if not resultado["problema_detectado"]:
                resultado["problema_detectado"] = "Conteúdo não carregou completamente"
                resultado["sugestao"] = "Aumentar tempo de espera ou scroll"
        
        # Salvar screenshot para debug
        screenshot_dir = Path("logs/scraper_audit/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"{site['id']}_{datetime.now().strftime('%H%M%S')}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        print(f"   Screenshot salvo: {screenshot_path}")
        resultado["etapas"].append(f"✅ Screenshot salvo")
        
        # Salvar HTML para análise
        html_path = screenshot_dir / f"{site['id']}_{datetime.now().strftime('%H%M%S')}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html[:50000])  # Primeiros 50k chars
        resultado["etapas"].append(f"✅ HTML salvo")
        
    except Exception as e:
        resultado["problema_detectado"] = f"ERRO GERAL: {str(e)[:200]}"
        resultado["etapas"].append(f"❌ Erro: {str(e)[:100]}")
        
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
    
    # Resumo
    print(f"\n📋 RESULTADO: {site['name']}")
    print(f"   Problema: {resultado['problema_detectado'] or 'Nenhum detectado'}")
    print(f"   Sugestão: {resultado['sugestao'] or 'N/A'}")
    
    return resultado


async def main():
    print("="*60)
    print("🔬 DIAGNÓSTICO DO LLMEnhancedScraper")
    print("="*60)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sites a diagnosticar: {len(SITES_TESTE)}")
    
    resultados = []
    
    for site in SITES_TESTE:
        resultado = await diagnosticar_site(site)
        resultados.append(resultado)
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DO DIAGNÓSTICO")
    print("="*60)
    
    for r in resultados:
        status = "✅" if "Nenhum" in str(r.get("problema_detectado", "")) else "❌"
        print(f"\n{status} {r['site']}")
        print(f"   Problema: {r.get('problema_detectado', 'Desconhecido')}")
        print(f"   Sugestão: {r.get('sugestao', 'N/A')}")
    
    print("\n" + "="*60)
    print("📁 Screenshots e HTML salvos em: logs/scraper_audit/screenshots/")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
