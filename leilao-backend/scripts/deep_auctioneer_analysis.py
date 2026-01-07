#!/usr/bin/env python3
"""
ANÁLISE PROFUNDA DE LEILOEIROS COM ERRO - LEILOHUB
Diagnostica cada leiloeiro, verifica site, identifica problemas.
"""

import os
import sys
import json
import httpx
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# ═══════════════════════════════════════════════════════════
# CATEGORIAS DE DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════

DIAGNOSTICO = {
    "SITE_OFFLINE": "Site completamente offline ou domínio expirado",
    "DNS_FALHA": "DNS não resolve - domínio pode ter expirado",
    "TIMEOUT": "Site muito lento ou não responde",
    "CLOUDFLARE": "Bloqueado por Cloudflare/proteção anti-bot",
    "403_FORBIDDEN": "Acesso negado - pode precisar de headers especiais",
    "404_NOT_FOUND": "Página não encontrada - URL pode ter mudado",
    "500_SERVER_ERROR": "Erro interno do servidor",
    "SSL_ERROR": "Problema com certificado SSL",
    "REDIRECT_LOOP": "Loop de redirecionamento infinito",
    "SEM_IMOVEIS_LISTADOS": "Site funciona mas não há imóveis listados",
    "ESTRUTURA_MUDOU": "Site funciona mas estrutura HTML mudou",
    "SITE_EM_MANUTENCAO": "Site em manutenção ou construção",
    "CONTEUDO_DINAMICO": "Conteúdo carregado via JavaScript (precisa Playwright)",
    "PAGINACAO_QUEBRADA": "Paginação não funciona corretamente",
    "SCRAPER_DESATUALIZADO": "Scraper específico precisa de atualização",
    "URL_IMOVEIS_ERRADA": "URL de listagem de imóveis incorreta",
    "SITE_FUNCIONAL": "Site OK - problema pode ser no scraper",
    "DESCONHECIDO": "Erro não categorizado - requer análise manual"
}

# Padrões para detectar páginas de imóveis
IMOVEIS_PATTERNS = [
    r'im[oó]ve[il]s?',
    r'leil[aã]o',
    r'lote',
    r'propriedade',
    r'apartamento',
    r'casa',
    r'terreno',
    r'fazenda',
    r'comercial',
    r'residencial',
    r'lance',
    r'arremat',
]

# Padrões que indicam proteção/bloqueio
BLOCKED_PATTERNS = [
    'cloudflare',
    'checking your browser',
    'just a moment',
    'ddos protection',
    'access denied',
    'forbidden',
    'blocked',
    'captcha',
    'recaptcha',
    'hcaptcha',
]

# Padrões que indicam manutenção
MAINTENANCE_PATTERNS = [
    'manutenção',
    'em breve',
    'coming soon',
    'under construction',
    'em construção',
    'indisponível',
    'temporarily unavailable',
]

# ═══════════════════════════════════════════════════════════
# FUNÇÕES DE DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════

async def check_dns(domain: str) -> Tuple[bool, str]:
    """Verifica se o DNS resolve."""
    import socket
    try:
        socket.gethostbyname(domain)
        return True, "OK"
    except socket.gaierror:
        return False, "DNS não resolve"
    except Exception as e:
        return False, str(e)

async def fetch_page(client: httpx.AsyncClient, url: str) -> Dict:
    """Faz requisição HTTP e retorna diagnóstico."""
    result = {
        "url": url,
        "status_code": None,
        "redirect_url": None,
        "content_length": 0,
        "content_type": None,
        "error": None,
        "html_sample": None,
        "title": None,
    }
    
    try:
        response = await client.get(url, follow_redirects=True, timeout=20.0)
        result["status_code"] = response.status_code
        result["content_length"] = len(response.content)
        result["content_type"] = response.headers.get("content-type", "")
        result["redirect_url"] = str(response.url) if str(response.url) != url else None
        
        if response.status_code == 200 and "text/html" in result["content_type"]:
            result["html_sample"] = response.text[:5000]
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            result["title"] = title_tag.text.strip() if title_tag else None
            
    except httpx.TimeoutException:
        result["error"] = "TIMEOUT"
    except httpx.ConnectError as e:
        if "SSL" in str(e) or "certificate" in str(e).lower():
            result["error"] = "SSL_ERROR"
        else:
            result["error"] = "CONNECTION_ERROR"
    except httpx.TooManyRedirects:
        result["error"] = "REDIRECT_LOOP"
    except Exception as e:
        result["error"] = str(e)[:100]
    
    return result

def analyze_html_content(html: str) -> Dict:
    """Analisa o conteúdo HTML para identificar características."""
    analysis = {
        "has_imoveis_content": False,
        "has_blocked_content": False,
        "has_maintenance_content": False,
        "has_dynamic_loading": False,
        "imoveis_count_estimate": 0,
        "detected_patterns": [],
    }
    
    if not html:
        return analysis
    
    html_lower = html.lower()
    
    # Verificar conteúdo de imóveis
    for pattern in IMOVEIS_PATTERNS:
        if re.search(pattern, html_lower):
            analysis["has_imoveis_content"] = True
            analysis["detected_patterns"].append(pattern)
    
    # Verificar bloqueio
    for pattern in BLOCKED_PATTERNS:
        if pattern in html_lower:
            analysis["has_blocked_content"] = True
            break
    
    # Verificar manutenção
    for pattern in MAINTENANCE_PATTERNS:
        if pattern in html_lower:
            analysis["has_maintenance_content"] = True
            break
    
    # Verificar conteúdo dinâmico (JavaScript pesado)
    js_indicators = ['react', 'vue', 'angular', 'next', 'nuxt', '__NEXT_DATA__', 'window.__INITIAL_STATE__']
    for indicator in js_indicators:
        if indicator in html_lower:
            analysis["has_dynamic_loading"] = True
            break
    
    # Estimar quantidade de imóveis (heurística)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Procurar por cards/items de imóveis
    card_selectors = [
        'div[class*="imovel"]', 'div[class*="lote"]', 'div[class*="property"]',
        'div[class*="card"]', 'article', 'li[class*="item"]',
        'a[href*="imovel"]', 'a[href*="lote"]', 'a[href*="detalhe"]',
    ]
    
    for selector in card_selectors:
        items = soup.select(selector)
        if items and len(items) > analysis["imoveis_count_estimate"]:
            analysis["imoveis_count_estimate"] = len(items)
    
    return analysis

def determine_diagnosis(fetch_result: Dict, html_analysis: Dict, auctioneer: Dict) -> Tuple[str, str, int]:
    """Determina o diagnóstico final baseado em todos os dados."""
    
    error = fetch_result.get("error")
    status = fetch_result.get("status_code")
    scrape_error = auctioneer.get("scrape_error", "") or ""
    
    # Prioridade 1: Erros de conexão
    if error == "TIMEOUT":
        return "TIMEOUT", "Site não respondeu em 20 segundos", 3
    
    if error == "SSL_ERROR":
        return "SSL_ERROR", "Certificado SSL inválido ou expirado", 2
    
    if error == "CONNECTION_ERROR":
        return "DNS_FALHA", "Não foi possível conectar ao servidor", 1
    
    if error == "REDIRECT_LOOP":
        return "REDIRECT_LOOP", "Redirecionamento infinito detectado", 2
    
    # Prioridade 2: Status HTTP
    if status == 403:
        return "403_FORBIDDEN", "Acesso negado pelo servidor", 3
    
    if status == 404:
        return "404_NOT_FOUND", "Página não encontrada", 2
    
    if status and status >= 500:
        return "500_SERVER_ERROR", f"Erro interno do servidor (HTTP {status})", 2
    
    # Prioridade 3: Análise de conteúdo
    if html_analysis.get("has_blocked_content"):
        return "CLOUDFLARE", "Proteção anti-bot detectada (Cloudflare/similar)", 4
    
    if html_analysis.get("has_maintenance_content"):
        return "SITE_EM_MANUTENCAO", "Site em manutenção", 1
    
    # Prioridade 4: Conteúdo dinâmico
    if html_analysis.get("has_dynamic_loading") and not html_analysis.get("has_imoveis_content"):
        return "CONTEUDO_DINAMICO", "Conteúdo carregado via JavaScript - precisa Playwright", 4
    
    # Prioridade 5: Site funciona mas sem imóveis
    if status == 200:
        if html_analysis.get("has_imoveis_content"):
            if html_analysis.get("imoveis_count_estimate", 0) > 0:
                return "SCRAPER_DESATUALIZADO", f"Site OK com ~{html_analysis['imoveis_count_estimate']} itens - scraper precisa ajuste", 5
            else:
                return "SEM_IMOVEIS_LISTADOS", "Site funciona mas nenhum imóvel encontrado no momento", 3
        else:
            # Verificar erro do scraper
            if "sem imóveis" in scrape_error.lower() or "no properties" in scrape_error.lower():
                return "URL_IMOVEIS_ERRADA", "URL de listagem pode estar incorreta", 4
            return "ESTRUTURA_MUDOU", "Site funciona mas estrutura HTML pode ter mudado", 4
    
    return "DESCONHECIDO", f"Erro não categorizado: {error or 'status ' + str(status)}", 3

# ═══════════════════════════════════════════════════════════
# FUNÇÕES DE DESCOBERTA DE URLs CORRETAS
# ═══════════════════════════════════════════════════════════

async def discover_imoveis_url(client: httpx.AsyncClient, base_url: str) -> Optional[str]:
    """Tenta descobrir a URL correta de listagem de imóveis."""
    
    common_paths = [
        '/imoveis',
        '/leiloes',
        '/leilao',
        '/lotes',
        '/catalogo',
        '/busca',
        '/pesquisa',
        '/properties',
        '/leilao-de-imoveis',
        '/leiloes-de-imoveis',
        '/venda',
        '/oportunidades',
        '/disponiveis',
        '/ativos',
    ]
    
    for path in common_paths:
        try:
            test_url = base_url.rstrip('/') + path
            response = await client.get(test_url, follow_redirects=True, timeout=10.0)
            
            if response.status_code == 200:
                html_lower = response.text.lower()
                # Verificar se parece ter imóveis
                imovel_indicators = ['apartamento', 'casa', 'terreno', 'lote', 'imóvel', 'imovel']
                if any(ind in html_lower for ind in imovel_indicators):
                    return test_url
        except:
            continue
    
    return None

# ═══════════════════════════════════════════════════════════
# ANÁLISE PRINCIPAL
# ═══════════════════════════════════════════════════════════

async def analyze_auctioneer(client: httpx.AsyncClient, auctioneer: Dict) -> Dict:
    """Analisa um leiloeiro específico."""
    
    website = auctioneer.get("website", "")
    name = auctioneer.get("name", "")
    auctioneer_id = auctioneer.get("id", "")
    scrape_error = auctioneer.get("scrape_error", "")
    
    result = {
        "id": auctioneer_id,
        "name": name,
        "website": website,
        "scrape_error_original": scrape_error,
        "diagnosis": None,
        "diagnosis_detail": None,
        "priority": 0,
        "suggested_action": None,
        "discovered_url": None,
        "fetch_result": None,
        "html_analysis": None,
    }
    
    if not website:
        result["diagnosis"] = "URL_IMOVEIS_ERRADA"
        result["diagnosis_detail"] = "Nenhum website cadastrado"
        result["priority"] = 1
        result["suggested_action"] = "Pesquisar e cadastrar website correto"
        return result
    
    # Normalizar URL
    if not website.startswith('http'):
        website = 'https://' + website
    
    # Verificar DNS
    domain = urlparse(website).netloc
    dns_ok, dns_msg = await check_dns(domain)
    
    if not dns_ok:
        result["diagnosis"] = "DNS_FALHA"
        result["diagnosis_detail"] = f"Domínio {domain} não resolve: {dns_msg}"
        result["priority"] = 1
        result["suggested_action"] = "Verificar se domínio mudou ou expirou"
        return result
    
    # Fazer requisição
    fetch_result = await fetch_page(client, website)
    result["fetch_result"] = fetch_result
    
    # Analisar HTML
    html_analysis = analyze_html_content(fetch_result.get("html_sample", ""))
    result["html_analysis"] = html_analysis
    
    # Determinar diagnóstico
    diagnosis, detail, priority = determine_diagnosis(fetch_result, html_analysis, auctioneer)
    result["diagnosis"] = diagnosis
    result["diagnosis_detail"] = detail
    result["priority"] = priority
    
    # Sugerir ação
    actions = {
        "SITE_OFFLINE": "Remover leiloeiro ou marcar como inativo permanentemente",
        "DNS_FALHA": "Pesquisar novo domínio do leiloeiro",
        "TIMEOUT": "Tentar novamente mais tarde; pode ser instabilidade temporária",
        "CLOUDFLARE": "Implementar scraper com Playwright + stealth mode",
        "403_FORBIDDEN": "Adicionar headers customizados ou usar proxy",
        "404_NOT_FOUND": "Descobrir nova URL de listagem de imóveis",
        "500_SERVER_ERROR": "Aguardar correção pelo leiloeiro; tentar novamente em 24h",
        "SSL_ERROR": "Tentar com http:// ou ignorar verificação SSL",
        "REDIRECT_LOOP": "Investigar redirecionamentos e ajustar URL base",
        "SEM_IMOVEIS_LISTADOS": "Leiloeiro pode não ter imóveis ativos no momento; manter monitoramento",
        "ESTRUTURA_MUDOU": "Atualizar seletores CSS do scraper",
        "SITE_EM_MANUTENCAO": "Aguardar e tentar novamente em alguns dias",
        "CONTEUDO_DINAMICO": "Migrar para scraper com Playwright",
        "SCRAPER_DESATUALIZADO": "Atualizar seletores e lógica de extração",
        "URL_IMOVEIS_ERRADA": "Descobrir URL correta de listagem",
        "SITE_FUNCIONAL": "Revisar lógica do scraper",
        "DESCONHECIDO": "Análise manual necessária",
    }
    result["suggested_action"] = actions.get(diagnosis, "Análise manual necessária")
    
    # Tentar descobrir URL correta para alguns casos
    if diagnosis in ["URL_IMOVEIS_ERRADA", "SEM_IMOVEIS_LISTADOS", "ESTRUTURA_MUDOU"]:
        base_url = f"{urlparse(website).scheme}://{urlparse(website).netloc}"
        discovered = await discover_imoveis_url(client, base_url)
        if discovered and discovered != website:
            result["discovered_url"] = discovered
            result["suggested_action"] += f" | URL sugerida: {discovered}"
    
    return result

async def main():
    """Executa análise completa de todos os leiloeiros com erro."""
    
    logger.info("=" * 70)
    logger.info("ANÁLISE PROFUNDA DE LEILOEIROS COM ERRO")
    logger.info("=" * 70)
    
    # Buscar leiloeiros com erro
    response = supabase.table("auctioneers") \
        .select("*") \
        .eq("scrape_status", "error") \
        .execute()
    
    auctioneers = response.data or []
    logger.info(f"\nTotal de leiloeiros com erro: {len(auctioneers)}")
    
    if not auctioneers:
        logger.info("Nenhum leiloeiro com erro encontrado!")
        return
    
    results = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for i, auctioneer in enumerate(auctioneers):
            logger.info(f"\n[{i+1}/{len(auctioneers)}] Analisando: {auctioneer.get('name', 'N/A')}")
            
            result = await analyze_auctioneer(client, auctioneer)
            results.append(result)
            
            logger.info(f"  Diagnóstico: {result['diagnosis']}")
            logger.info(f"  Detalhe: {result['diagnosis_detail']}")
            
            # Rate limiting
            await asyncio.sleep(1.0)
    
    # ═══════════════════════════════════════════════════════════
    # GERAR RELATÓRIO
    # ═══════════════════════════════════════════════════════════
    
    # Agrupar por diagnóstico
    by_diagnosis = {}
    for r in results:
        diag = r["diagnosis"]
        if diag not in by_diagnosis:
            by_diagnosis[diag] = []
        by_diagnosis[diag].append(r)
    
    # Ordenar por prioridade
    priority_order = sorted(by_diagnosis.keys(), key=lambda x: -max(r["priority"] for r in by_diagnosis[x]))
    
    # Gerar relatório markdown
    report = f"""# 📊 ANÁLISE PROFUNDA DE LEILOEIROS COM ERRO

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Analisado:** {len(results)} leiloeiros

## Resumo por Diagnóstico

| Diagnóstico | Quantidade | % | Prioridade |
|-------------|------------|---|------------|
"""
    
    for diag in priority_order:
        items = by_diagnosis[diag]
        pct = len(items) * 100 / len(results)
        avg_priority = sum(r["priority"] for r in items) / len(items)
        report += f"| {diag} | {len(items)} | {pct:.1f}% | {avg_priority:.1f} |\n"
    
    report += f"""
## Legenda de Prioridade

- **5**: Alta - Scraper precisa de ajuste urgente (site funciona)
- **4**: Média-Alta - Requer implementação técnica (Playwright, headers)
- **3**: Média - Problema temporário ou site sem imóveis
- **2**: Baixa - Problema no servidor do leiloeiro
- **1**: Muito Baixa - Site offline/domínio expirado

---

## Detalhamento por Categoria

"""
    
    for diag in priority_order:
        items = by_diagnosis[diag]
        report += f"""
### {diag} ({len(items)} leiloeiros)

**Descrição:** {DIAGNOSTICO.get(diag, 'N/A')}

**Ação Recomendada:** {items[0]['suggested_action']}

| Leiloeiro | Website | Erro Original |
|-----------|---------|---------------|
"""
        for item in items[:20]:  # Limitar a 20 por categoria
            name = item.get('name', 'N/A')[:30]
            website = item.get('website', 'N/A')[:40]
            error = (item.get('scrape_error_original') or 'N/A')[:50]
            report += f"| {name} | {website} | {error} |\n"
        
        if len(items) > 20:
            report += f"\n*... e mais {len(items) - 20} leiloeiros*\n"
    
    report += """
---

## Plano de Ação Priorizado

### Fase 1: Quick Wins (Prioridade 5)
Leiloeiros cujo site funciona mas o scraper precisa ajuste. Maior ROI.

"""
    
    phase1 = [r for r in results if r["priority"] == 5]
    for item in phase1[:10]:
        report += f"- **{item['name']}**: {item['diagnosis_detail']}\n"
        if item.get('discovered_url'):
            report += f"  - URL descoberta: {item['discovered_url']}\n"
    
    report += """
### Fase 2: Implementação Técnica (Prioridade 4)
Requer Playwright, headers especiais ou análise de API.

"""
    
    phase2 = [r for r in results if r["priority"] == 4]
    for item in phase2[:10]:
        report += f"- **{item['name']}**: {item['diagnosis_detail']}\n"
    
    report += """
### Fase 3: Monitoramento (Prioridade 3)
Problemas temporários ou sites sem imóveis no momento.

"""
    
    phase3 = [r for r in results if r["priority"] == 3]
    report += f"- {len(phase3)} leiloeiros para monitorar\n"
    
    report += """
### Fase 4: Baixa Prioridade (Prioridade 1-2)
Sites com problemas estruturais ou offline.

"""
    
    phase4 = [r for r in results if r["priority"] <= 2]
    report += f"- {len(phase4)} leiloeiros (considerar desativar temporariamente)\n"
    
    report += """
---

## URLs Descobertas

Novas URLs de listagem de imóveis encontradas automaticamente:

| Leiloeiro | URL Atual | URL Sugerida |
|-----------|-----------|--------------|
"""
    
    discovered = [r for r in results if r.get('discovered_url')]
    for item in discovered:
        report += f"| {item['name']} | {item['website']} | {item['discovered_url']} |\n"
    
    if not discovered:
        report += "| *Nenhuma nova URL descoberta* | | |\n"
    
    # Salvar relatório
    report_path = f"RELATORIO_ANALISE_LEILOEIROS_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"\n{'=' * 70}")
    logger.info(f"Relatório salvo: {report_path}")
    
    # Salvar JSON com dados completos
    json_path = f"analise_leiloeiros_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Dados completos salvos: {json_path}")
    logger.info("=" * 70)
    
    # Resumo final
    logger.info("\n📊 RESUMO FINAL:")
    logger.info(f"  Total analisado: {len(results)}")
    logger.info(f"  Prioridade Alta (5): {len([r for r in results if r['priority'] == 5])}")
    logger.info(f"  Prioridade Média (4): {len([r for r in results if r['priority'] == 4])}")
    logger.info(f"  Prioridade Baixa (1-3): {len([r for r in results if r['priority'] <= 3])}")
    logger.info(f"  URLs descobertas: {len(discovered)}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())

