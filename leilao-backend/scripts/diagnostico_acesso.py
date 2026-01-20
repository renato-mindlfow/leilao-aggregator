#!/usr/bin/env python3
"""
DIAGNÓSTICO DE PROBLEMAS DE ACESSO
Testa 6 métodos diferentes para identificar causa raiz
"""

import asyncio
import httpx
import json
import time
import ssl
import socket
import sys
import codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("logs/diagnostico_acesso")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TesteResultado:
    """Resultado de um teste individual."""
    metodo: str
    sucesso: bool
    status_code: Optional[int]
    tempo_ms: int
    tamanho_bytes: int
    erro: Optional[str]
    detalhes: Dict


@dataclass 
class SiteDiagnostico:
    """Diagnóstico completo de um site."""
    nome: str
    url: str
    timestamp: str
    dns_ok: bool
    ssl_ok: bool
    testes: List[TesteResultado]
    diagnostico_final: str
    recomendacao: str


# ============================================
# SITES PARA TESTE
# ============================================

SITES_TESTE = [
    # GRUPO A: Controle (devem funcionar)
    ("Megaleiloes", "https://www.megaleiloes.com.br/imoveis"),
    ("Portalzuk", "https://www.portalzuk.com.br/leilao-de-imoveis"),
    ("Sold", "https://www.sold.com.br"),
    ("Frazaoleiloes", "https://www.frazaoleiloes.com.br"),
    ("Lancejudicial", "https://www.lancejudicial.com.br"),
    
    # GRUPO B: Marcados como OFFLINE
    ("Leiloes", "https://www.leiloes.com.br"),
    ("Milanleiloes", "https://www.milanleiloes.com.br"),
    ("Bestleiloes", "https://www.bestleiloes.com.br"),
    ("Francoleiloes", "https://www.francoleiloes.com.br"),
    ("Freitasleiloeiro", "https://www.freitasleiloeiro.com.br"),
    
    # GRUPO C: property_count > 0 mas error
    ("Sodresantoro", "https://www.sodresantoro.com.br"),
    ("Biasileiloes", "https://www.biasileiloes.com.br"),
    ("Leilaobrasil", "https://www.leilaobrasil.com.br"),
    ("Allianceleiloes", "https://www.allianceleiloes.com.br"),
    ("Depaulaonline", "https://www.depaulaonline.com.br"),
    
    # GRUPO D: Aleatórios
    ("Superbid", "https://www.superbid.net"),
    ("Vivaleiloes", "https://www.vivaleiloes.com.br"),
    ("Hastavip", "https://www.hastavip.com.br"),
    ("Leje", "https://www.leje.com.br"),
    ("Lut", "https://www.lut.com.br"),
]


# ============================================
# TESTE 0: DNS E SSL
# ============================================

def teste_dns(url: str) -> Tuple[bool, str]:
    """Verifica se o DNS resolve."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname
        ip = socket.gethostbyname(hostname)
        return True, f"DNS OK: {hostname} -> {ip}"
    except socket.gaierror as e:
        return False, f"DNS FALHOU: {e}"
    except Exception as e:
        return False, f"Erro DNS: {e}"


def teste_ssl(url: str) -> Tuple[bool, str]:
    """Verifica certificado SSL."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return True, f"SSL OK: {cert.get('subject', 'N/A')}"
    except ssl.SSLError as e:
        return False, f"SSL ERRO: {e}"
    except Exception as e:
        return False, f"Erro SSL: {e}"


# ============================================
# TESTE 1: HTTP SIMPLES (requests básico)
# ============================================

async def teste_http_simples(url: str) -> TesteResultado:
    """Requisição HTTP básica sem headers especiais."""
    inicio = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            tempo = int((time.time() - inicio) * 1000)
            
            return TesteResultado(
                metodo="HTTP_SIMPLES",
                sucesso=response.status_code == 200,
                status_code=response.status_code,
                tempo_ms=tempo,
                tamanho_bytes=len(response.content),
                erro=None if response.status_code == 200 else f"HTTP {response.status_code}",
                detalhes={
                    "headers_resposta": dict(response.headers),
                    "url_final": str(response.url),
                    "redirects": len(response.history),
                }
            )
    except Exception as e:
        return TesteResultado(
            metodo="HTTP_SIMPLES",
            sucesso=False,
            status_code=None,
            tempo_ms=int((time.time() - inicio) * 1000),
            tamanho_bytes=0,
            erro=str(e)[:200],
            detalhes={"exception_type": type(e).__name__}
        )


# ============================================
# TESTE 2: HTTP COM HEADERS DE BROWSER
# ============================================

async def teste_http_headers_browser(url: str) -> TesteResultado:
    """Requisição HTTP com headers completos de browser."""
    inicio = time.time()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            tempo = int((time.time() - inicio) * 1000)
            
            # Detectar bloqueios comuns
            content_lower = response.text[:5000].lower()
            bloqueio_detectado = None
            
            if 'cloudflare' in content_lower or 'cf-ray' in str(response.headers).lower():
                bloqueio_detectado = "CLOUDFLARE"
            elif 'captcha' in content_lower or 'recaptcha' in content_lower:
                bloqueio_detectado = "CAPTCHA"
            elif 'blocked' in content_lower or 'denied' in content_lower:
                bloqueio_detectado = "WAF/BLOCKED"
            elif 'robot' in content_lower or 'bot' in content_lower:
                bloqueio_detectado = "BOT_DETECTION"
            
            return TesteResultado(
                metodo="HTTP_HEADERS_BROWSER",
                sucesso=response.status_code == 200 and not bloqueio_detectado,
                status_code=response.status_code,
                tempo_ms=tempo,
                tamanho_bytes=len(response.content),
                erro=bloqueio_detectado,
                detalhes={
                    "bloqueio_detectado": bloqueio_detectado,
                    "content_preview": response.text[:500],
                    "url_final": str(response.url),
                }
            )
    except Exception as e:
        return TesteResultado(
            metodo="HTTP_HEADERS_BROWSER",
            sucesso=False,
            status_code=None,
            tempo_ms=int((time.time() - inicio) * 1000),
            tamanho_bytes=0,
            erro=str(e)[:200],
            detalhes={"exception_type": type(e).__name__}
        )


# ============================================
# TESTE 3: PLAYWRIGHT HEADLESS (padrão)
# ============================================

async def teste_playwright_headless(url: str) -> TesteResultado:
    """Playwright em modo headless padrão."""
    inicio = time.time()
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            page = await context.new_page()
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)  # Aguardar JS
            
            content = await page.content()
            tempo = int((time.time() - inicio) * 1000)
            
            # Detectar bloqueios
            content_lower = content.lower()
            bloqueio = None
            if 'cloudflare' in content_lower:
                bloqueio = "CLOUDFLARE"
            elif 'captcha' in content_lower:
                bloqueio = "CAPTCHA"
            elif 'navegador incompatível' in content_lower:
                bloqueio = "BROWSER_CHECK"
            
            # Verificar se tem conteúdo real
            text = await page.evaluate("() => document.body.innerText")
            tem_conteudo = len(text) > 500
            
            await browser.close()
            
            return TesteResultado(
                metodo="PLAYWRIGHT_HEADLESS",
                sucesso=response.status == 200 and tem_conteudo and not bloqueio,
                status_code=response.status if response else None,
                tempo_ms=tempo,
                tamanho_bytes=len(content),
                erro=bloqueio,
                detalhes={
                    "bloqueio_detectado": bloqueio,
                    "tem_conteudo": tem_conteudo,
                    "texto_tamanho": len(text),
                    "content_preview": text[:300] if text else "",
                }
            )
    except Exception as e:
        return TesteResultado(
            metodo="PLAYWRIGHT_HEADLESS",
            sucesso=False,
            status_code=None,
            tempo_ms=int((time.time() - inicio) * 1000),
            tamanho_bytes=0,
            erro=str(e)[:200],
            detalhes={"exception_type": type(e).__name__}
        )


# ============================================
# TESTE 4: PLAYWRIGHT COM STEALTH
# ============================================

async def teste_playwright_stealth(url: str) -> TesteResultado:
    """Playwright com técnicas de stealth anti-detecção."""
    inicio = time.time()
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-web-security',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                extra_http_headers={
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                }
            )
            
            page = await context.new_page()
            
            # Injetar scripts de stealth
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                delete navigator.__proto__.webdriver;
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            """)
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            content = await page.content()
            text = await page.evaluate("() => document.body.innerText")
            tempo = int((time.time() - inicio) * 1000)
            
            # Detectar bloqueios
            content_lower = content.lower()
            bloqueio = None
            if 'cloudflare' in content_lower and 'challenge' in content_lower:
                bloqueio = "CLOUDFLARE_CHALLENGE"
            elif 'captcha' in content_lower:
                bloqueio = "CAPTCHA"
            elif 'navegador incompatível' in content_lower:
                bloqueio = "BROWSER_CHECK"
            
            tem_conteudo = len(text) > 500
            
            await browser.close()
            
            return TesteResultado(
                metodo="PLAYWRIGHT_STEALTH",
                sucesso=response.status == 200 and tem_conteudo and not bloqueio,
                status_code=response.status if response else None,
                tempo_ms=tempo,
                tamanho_bytes=len(content),
                erro=bloqueio,
                detalhes={
                    "bloqueio_detectado": bloqueio,
                    "tem_conteudo": tem_conteudo,
                    "texto_tamanho": len(text),
                }
            )
    except Exception as e:
        return TesteResultado(
            metodo="PLAYWRIGHT_STEALTH",
            sucesso=False,
            status_code=None,
            tempo_ms=int((time.time() - inicio) * 1000),
            tamanho_bytes=0,
            erro=str(e)[:200],
            detalhes={"exception_type": type(e).__name__}
        )


# ============================================
# TESTE 5: PLAYWRIGHT HEADED (visível)
# ============================================

async def teste_playwright_headed(url: str) -> TesteResultado:
    """Playwright com browser visível (não headless)."""
    inicio = time.time()
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # VISÍVEL
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            
            page = await context.new_page()
            
            # Stealth
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
            """)
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            content = await page.content()
            text = await page.evaluate("() => document.body.innerText")
            tempo = int((time.time() - inicio) * 1000)
            
            tem_conteudo = len(text) > 500
            
            # Screenshot para análise
            screenshot_path = OUTPUT_DIR / f"headed_{url.split('//')[1].split('/')[0].replace('.', '_')}.png"
            await page.screenshot(path=str(screenshot_path))
            
            await browser.close()
            
            return TesteResultado(
                metodo="PLAYWRIGHT_HEADED",
                sucesso=response.status == 200 and tem_conteudo,
                status_code=response.status if response else None,
                tempo_ms=tempo,
                tamanho_bytes=len(content),
                erro=None if tem_conteudo else "SEM_CONTEUDO",
                detalhes={
                    "tem_conteudo": tem_conteudo,
                    "texto_tamanho": len(text),
                    "screenshot": str(screenshot_path),
                }
            )
    except Exception as e:
        return TesteResultado(
            metodo="PLAYWRIGHT_HEADED",
            sucesso=False,
            status_code=None,
            tempo_ms=int((time.time() - inicio) * 1000),
            tamanho_bytes=0,
            erro=str(e)[:200],
            detalhes={"exception_type": type(e).__name__}
        )


# ============================================
# TESTE 6: CURL SIMULADO (via subprocess)
# ============================================

async def teste_curl(url: str) -> TesteResultado:
    """Simula curl via linha de comando."""
    inicio = time.time()
    
    try:
        import subprocess
        
        # Windows usa curl.exe no PATH
        result = subprocess.run(
            [
                'curl', '-s', '-o', 'NUL' if sys.platform == 'win32' else '/dev/null', '-w', 
                '{"status":%{http_code},"time":%{time_total},"size":%{size_download}}',
                '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-L',  # Follow redirects
                '--max-time', '30',
                url
            ],
            capture_output=True,
            text=True,
            timeout=35
        )
        
        tempo = int((time.time() - inicio) * 1000)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return TesteResultado(
                metodo="CURL",
                sucesso=data['status'] == 200,
                status_code=data['status'],
                tempo_ms=int(data['time'] * 1000),
                tamanho_bytes=int(data['size']),
                erro=None if data['status'] == 200 else f"HTTP {data['status']}",
                detalhes=data
            )
        else:
            return TesteResultado(
                metodo="CURL",
                sucesso=False,
                status_code=None,
                tempo_ms=tempo,
                tamanho_bytes=0,
                erro=result.stderr[:200] if result.stderr else "Curl falhou",
                detalhes={"returncode": result.returncode}
            )
    except FileNotFoundError:
        return TesteResultado(
            metodo="CURL",
            sucesso=False,
            status_code=None,
            tempo_ms=0,
            tamanho_bytes=0,
            erro="CURL_NAO_INSTALADO",
            detalhes={}
        )
    except Exception as e:
        return TesteResultado(
            metodo="CURL",
            sucesso=False,
            status_code=None,
            tempo_ms=int((time.time() - inicio) * 1000),
            tamanho_bytes=0,
            erro=str(e)[:200],
            detalhes={"exception_type": type(e).__name__}
        )


# ============================================
# FUNÇÃO PRINCIPAL DE DIAGNÓSTICO
# ============================================

async def diagnosticar_site(nome: str, url: str) -> SiteDiagnostico:
    """Executa todos os testes em um site."""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔬 DIAGNOSTICANDO: {nome}")
    logger.info(f"   URL: {url}")
    logger.info(f"{'='*60}")
    
    # Teste DNS
    dns_ok, dns_msg = teste_dns(url)
    logger.info(f"   DNS: {'✅' if dns_ok else '❌'} {dns_msg}")
    
    if not dns_ok:
        return SiteDiagnostico(
            nome=nome,
            url=url,
            timestamp=datetime.now().isoformat(),
            dns_ok=False,
            ssl_ok=False,
            testes=[],
            diagnostico_final="DNS_FALHOU",
            recomendacao="Verificar se o domínio existe ou foi descontinuado"
        )
    
    # Teste SSL
    ssl_ok, ssl_msg = teste_ssl(url)
    logger.info(f"   SSL: {'✅' if ssl_ok else '⚠️'} {ssl_msg}")
    
    # Executar todos os testes
    testes = []
    
    # Teste 1: HTTP Simples
    logger.info(f"   [1/6] HTTP Simples...")
    resultado = await teste_http_simples(url)
    testes.append(resultado)
    logger.info(f"         {'✅' if resultado.sucesso else '❌'} {resultado.status_code or resultado.erro}")
    
    # Teste 2: HTTP com Headers
    logger.info(f"   [2/6] HTTP com Headers Browser...")
    resultado = await teste_http_headers_browser(url)
    testes.append(resultado)
    logger.info(f"         {'✅' if resultado.sucesso else '❌'} {resultado.status_code or resultado.erro}")
    
    # Teste 3: Playwright Headless
    logger.info(f"   [3/6] Playwright Headless...")
    resultado = await teste_playwright_headless(url)
    testes.append(resultado)
    logger.info(f"         {'✅' if resultado.sucesso else '❌'} {resultado.erro or 'OK'}")
    
    # Teste 4: Playwright Stealth
    logger.info(f"   [4/6] Playwright Stealth...")
    resultado = await teste_playwright_stealth(url)
    testes.append(resultado)
    logger.info(f"         {'✅' if resultado.sucesso else '❌'} {resultado.erro or 'OK'}")
    
    # Teste 5: Playwright Headed (apenas se os anteriores falharam)
    if not any(t.sucesso for t in testes):
        logger.info(f"   [5/6] Playwright Headed (visível)...")
        resultado = await teste_playwright_headed(url)
        testes.append(resultado)
        logger.info(f"         {'✅' if resultado.sucesso else '❌'} {resultado.erro or 'OK'}")
    else:
        logger.info(f"   [5/6] Playwright Headed - PULADO (já teve sucesso)")
    
    # Teste 6: Curl
    logger.info(f"   [6/6] CURL...")
    resultado = await teste_curl(url)
    testes.append(resultado)
    logger.info(f"         {'✅' if resultado.sucesso else '❌'} {resultado.status_code or resultado.erro}")
    
    # Análise final
    diagnostico, recomendacao = analisar_resultados(testes)
    
    logger.info(f"\n   📊 DIAGNÓSTICO: {diagnostico}")
    logger.info(f"   💡 RECOMENDAÇÃO: {recomendacao}")
    
    return SiteDiagnostico(
        nome=nome,
        url=url,
        timestamp=datetime.now().isoformat(),
        dns_ok=dns_ok,
        ssl_ok=ssl_ok,
        testes=testes,
        diagnostico_final=diagnostico,
        recomendacao=recomendacao
    )


def analisar_resultados(testes: List[TesteResultado]) -> Tuple[str, str]:
    """Analisa os resultados e determina o diagnóstico."""
    
    # Contar sucessos por método
    sucessos = {t.metodo: t.sucesso for t in testes}
    erros = {t.metodo: t.erro for t in testes if t.erro}
    
    # Caso 1: Todos funcionam
    if all(sucessos.values()):
        return "SITE_OK", "Site funciona com todos os métodos"
    
    # Caso 2: HTTP falha mas Playwright funciona
    if not sucessos.get("HTTP_SIMPLES") and sucessos.get("PLAYWRIGHT_STEALTH"):
        return "REQUER_JAVASCRIPT", "Site requer JavaScript - usar Playwright"
    
    # Caso 3: Detectado Cloudflare
    if any("CLOUDFLARE" in str(e) for e in erros.values() if e):
        if sucessos.get("PLAYWRIGHT_STEALTH") or sucessos.get("PLAYWRIGHT_HEADED"):
            return "CLOUDFLARE_BYPASS_OK", "Cloudflare detectado mas Playwright Stealth funciona"
        return "CLOUDFLARE_BLOQUEIO", "Cloudflare bloqueando - considerar proxy residencial"
    
    # Caso 4: Captcha detectado
    if any("CAPTCHA" in str(e) for e in erros.values() if e):
        return "CAPTCHA_BLOQUEIO", "Site requer CAPTCHA - considerar serviço de resolução"
    
    # Caso 5: Browser check
    if any("BROWSER" in str(e) for e in erros.values() if e):
        if sucessos.get("PLAYWRIGHT_HEADED"):
            return "HEADLESS_DETECTADO", "Site detecta headless - usar modo headed ou melhorar stealth"
        return "ANTI_BOT_FORTE", "Anti-bot forte - considerar undetected-chromedriver"
    
    # Caso 6: Apenas Playwright Headed funciona
    if not any(t.sucesso for t in testes[:-1]) and sucessos.get("PLAYWRIGHT_HEADED"):
        return "ANTI_BOT_DETECTA_HEADLESS", "Site detecta automação - usar browser real"
    
    # Caso 7: Nenhum funciona
    if not any(sucessos.values()):
        return "SITE_INACESSIVEL", "Site parece realmente offline ou bloqueando completamente"
    
    # Caso padrão
    metodos_ok = [m for m, s in sucessos.items() if s]
    return f"PARCIAL_{len(metodos_ok)}_METODOS", f"Funciona com: {', '.join(metodos_ok)}"


# ============================================
# MAIN
# ============================================

async def main():
    """Executa diagnóstico em todos os sites de teste."""
    
    logger.info("\n" + "="*70)
    logger.info("🔬 DIAGNÓSTICO DE PROBLEMAS DE ACESSO - LEILOEIROS")
    logger.info("="*70)
    logger.info(f"Sites a testar: {len(SITES_TESTE)}")
    logger.info(f"Métodos: 6 (HTTP, Headers, Playwright x3, CURL)")
    logger.info("="*70 + "\n")
    
    resultados = []
    
    for i, (nome, url) in enumerate(SITES_TESTE, 1):
        logger.info(f"\n[{i}/{len(SITES_TESTE)}] Processando {nome}...")
        resultado = await diagnosticar_site(nome, url)
        resultados.append(resultado)
        
        # Pausa entre sites
        await asyncio.sleep(2)
    
    # Salvar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # JSON completo
    json_file = OUTPUT_DIR / f"diagnostico_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in resultados], f, ensure_ascii=False, indent=2, default=str)
    
    # Relatório Markdown
    md_file = OUTPUT_DIR / f"RELATORIO_DIAGNOSTICO_{timestamp}.md"
    gerar_relatorio_md(resultados, md_file)
    
    # Resumo no console
    gerar_resumo_console(resultados)
    
    logger.info(f"\n📁 Arquivos salvos em: {OUTPUT_DIR}")
    logger.info(f"   - {json_file.name}")
    logger.info(f"   - {md_file.name}")


def gerar_relatorio_md(resultados: List[SiteDiagnostico], filepath: Path):
    """Gera relatório em Markdown."""
    
    # Agrupar por diagnóstico
    por_diagnostico = {}
    for r in resultados:
        diag = r.diagnostico_final
        if diag not in por_diagnostico:
            por_diagnostico[diag] = []
        por_diagnostico[diag].append(r)
    
    md = f"""# 🔬 RELATÓRIO DE DIAGNÓSTICO - ACESSO AOS LEILOEIROS

**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Sites Testados**: {len(resultados)}
**Métodos**: HTTP Simples, HTTP+Headers, Playwright (3 modos), CURL

---

## 📊 RESUMO POR DIAGNÓSTICO

| Diagnóstico | Qtd | % | Recomendação |
|-------------|-----|---|--------------|
"""
    
    for diag, sites in sorted(por_diagnostico.items(), key=lambda x: -len(x[1])):
        pct = len(sites) / len(resultados) * 100
        rec = sites[0].recomendacao[:50] + "..." if len(sites[0].recomendacao) > 50 else sites[0].recomendacao
        md += f"| {diag} | {len(sites)} | {pct:.1f}% | {rec} |\n"
    
    md += "\n---\n\n## 📋 DETALHES POR SITE\n\n"
    
    for r in resultados:
        md += f"### {r.nome}\n\n"
        md += f"- **URL**: {r.url}\n"
        md += f"- **DNS**: {'✅' if r.dns_ok else '❌'}\n"
        md += f"- **SSL**: {'✅' if r.ssl_ok else '⚠️'}\n"
        md += f"- **Diagnóstico**: `{r.diagnostico_final}`\n"
        md += f"- **Recomendação**: {r.recomendacao}\n\n"
        
        md += "| Método | Sucesso | Status | Tempo | Erro |\n"
        md += "|--------|---------|--------|-------|------|\n"
        for t in r.testes:
            md += f"| {t.metodo} | {'✅' if t.sucesso else '❌'} | {t.status_code or '-'} | {t.tempo_ms}ms | {t.erro or '-'} |\n"
        md += "\n"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md)


def gerar_resumo_console(resultados: List[SiteDiagnostico]):
    """Gera resumo para o console."""
    
    logger.info("\n" + "="*70)
    logger.info("📊 RESUMO DO DIAGNÓSTICO")
    logger.info("="*70)
    
    # Agrupar por diagnóstico
    por_diagnostico = {}
    for r in resultados:
        diag = r.diagnostico_final
        if diag not in por_diagnostico:
            por_diagnostico[diag] = []
        por_diagnostico[diag].append(r)
    
    for diag, sites in sorted(por_diagnostico.items(), key=lambda x: -len(x[1])):
        pct = len(sites) / len(resultados) * 100
        logger.info(f"\n{diag}: {len(sites)} sites ({pct:.1f}%)")
        for s in sites:
            logger.info(f"   - {s.nome}")
    
    # Conclusão
    site_ok = len(por_diagnostico.get("SITE_OK", []))
    requer_js = len(por_diagnostico.get("REQUER_JAVASCRIPT", []))
    cloudflare = len([s for k in por_diagnostico for s in por_diagnostico[k] if "CLOUDFLARE" in k])
    inacessivel = len(por_diagnostico.get("SITE_INACESSIVEL", []))
    
    logger.info("\n" + "="*70)
    logger.info("💡 CONCLUSÕES")
    logger.info("="*70)
    logger.info(f"   ✅ Sites OK (sem proteção): {site_ok}")
    logger.info(f"   🔧 Requer JavaScript: {requer_js}")
    logger.info(f"   ☁️ Cloudflare: {cloudflare}")
    logger.info(f"   ❌ Inacessíveis: {inacessivel}")
    
    if requer_js > site_ok:
        logger.info("\n   📌 PRINCIPAL CAUSA: Sites requerem JavaScript")
        logger.info("   📌 SOLUÇÃO: Usar Playwright como método padrão")
    elif cloudflare > 0:
        logger.info("\n   📌 PRINCIPAL CAUSA: Cloudflare bloqueando")
        logger.info("   📌 SOLUÇÃO: Melhorar stealth ou usar proxies residenciais")


if __name__ == "__main__":
    asyncio.run(main())
