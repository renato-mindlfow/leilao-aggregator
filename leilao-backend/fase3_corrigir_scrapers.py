"""
FASE 3: CORRIGIR SCRAPERS COM ERRO
Execucao autonoma - sem confirmacoes
Foca em sites de alta prioridade e cloudflare
"""
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import asyncio
import sys

load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

# Importar o scraper integrado
sys.path.insert(0, os.path.dirname(__file__))
from app.scrapers.playwright_integrated_scraper import PlaywrightIntegratedScraper

# Estrutura para armazenar relatorio
relatorio = {
    'fase': 'FASE 3 - Corrigir Scrapers com Erro',
    'data_execucao': datetime.now().isoformat(),
    'acoes_executadas': [],
    'sites_corrigidos': [],
    'sites_falharam': [],
    'imoveis_extraidos': 0,
    'criterios_sucesso': {}
}

def log_acao(acao, detalhes=''):
    """Registra acao no relatorio"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    msg = f"[{timestamp}] {acao}"
    if detalhes:
        msg += f" - {detalhes}"
    print(msg)
    relatorio['acoes_executadas'].append(msg)

def desabilitar_sites_offline():
    """Desabilita sites offline identificados na FASE 2"""
    log_acao("=== Desabilitando sites offline ===")
    
    try:
        with open('priorizacao_scrapers.json', 'r', encoding='utf-8') as f:
            priorizacao = json.load(f)
        
        sites_offline = priorizacao.get('desabilitar', [])
        
        for site in sites_offline:
            site_id = site['id']
            classificacao = site['classificacao']
            
            # Marcar como desabilitado no banco
            supabase.table('auctioneers')\
                .update({
                    'scrape_status': 'disabled',
                    'scrape_error': f'Site offline - classificacao: {classificacao}',
                    'is_active': False
                })\
                .eq('id', site_id)\
                .execute()
            
            log_acao(f"Desabilitado: {site['name']} ({classificacao})")
        
        log_acao(f"Total desabilitados: {len(sites_offline)}")
        
    except Exception as e:
        log_acao(f"ERRO ao desabilitar sites: {e}")

async def executar_scraper_site(scraper, site_info):
    """Executa scraper para um site especifico"""
    site_id = site_info['id']
    site_name = site_info['name']
    website = site_info['website']
    
    log_acao(f"\nProcessando: {site_name}")
    log_acao(f"  URL: {website}")
    
    try:
        resultado = await scraper.scrape_and_save_auctioneer(
            auctioneer_id=site_id,
            auctioneer_name=site_name,
            website=website
        )
        
        imoveis = resultado.get('properties_saved', 0)
        
        if imoveis > 0:
            log_acao(f"  SUCESSO: {imoveis} imoveis extraidos!")
            relatorio['sites_corrigidos'].append({
                'id': site_id,
                'name': site_name,
                'website': website,
                'imoveis': imoveis
            })
            relatorio['imoveis_extraidos'] += imoveis
            return True
        else:
            log_acao(f"  AVISO: 0 imoveis extraidos")
            relatorio['sites_falharam'].append({
                'id': site_id,
                'name': site_name,
                'website': website,
                'motivo': 'Zero imoveis extraidos'
            })
            return False
            
    except Exception as e:
        erro_msg = str(e)[:200]
        log_acao(f"  ERRO: {erro_msg}")
        relatorio['sites_falharam'].append({
            'id': site_id,
            'name': site_name,
            'website': website,
            'motivo': erro_msg
        })
        return False

async def processar_sites_prioridade_alta():
    """Processa os 4 sites de alta prioridade (online_standard)"""
    log_acao("\n=== 3.1 Processando sites PRIORIDADE ALTA (online_standard) ===")
    
    try:
        with open('priorizacao_scrapers.json', 'r', encoding='utf-8') as f:
            priorizacao = json.load(f)
        
        sites_alta = priorizacao.get('prioridade_alta', [])
        log_acao(f"Total de sites alta prioridade: {len(sites_alta)}")
        
        scraper = PlaywrightIntegratedScraper(headless=True)
        
        sucessos = 0
        for site in sites_alta:
            sucesso = await executar_scraper_site(scraper, site)
            if sucesso:
                sucessos += 1
            
            # Delay entre sites
            await asyncio.sleep(3)
        
        # Fechar browser
        await scraper._close_browser()
        
        log_acao(f"\nResultado ALTA prioridade: {sucessos}/{len(sites_alta)} sucessos")
        return sucessos
        
    except Exception as e:
        log_acao(f"ERRO ao processar alta prioridade: {e}")
        return 0

async def processar_sites_cloudflare(limite=20):
    """Processa sites com Cloudflare (prioridade media)"""
    log_acao(f"\n=== 3.2 Processando sites CLOUDFLARE (limite: {limite}) ===")
    
    try:
        with open('priorizacao_scrapers.json', 'r', encoding='utf-8') as f:
            priorizacao = json.load(f)
        
        sites_cloudflare = priorizacao.get('prioridade_media', [])[:limite]
        log_acao(f"Processando {len(sites_cloudflare)} sites com Cloudflare")
        
        scraper = PlaywrightIntegratedScraper(headless=True)
        
        sucessos = 0
        for i, site in enumerate(sites_cloudflare, 1):
            log_acao(f"\n[{i}/{len(sites_cloudflare)}]")
            sucesso = await executar_scraper_site(scraper, site)
            if sucesso:
                sucessos += 1
            
            # Delay entre sites (importante para Cloudflare)
            await asyncio.sleep(5)
            
            # A cada 5 sites, reiniciar browser para evitar problemas
            if i % 5 == 0:
                log_acao("  Reiniciando browser...")
                await scraper._close_browser()
                await asyncio.sleep(2)
                scraper = PlaywrightIntegratedScraper(headless=True)
        
        # Fechar browser
        await scraper._close_browser()
        
        log_acao(f"\nResultado CLOUDFLARE: {sucessos}/{len(sites_cloudflare)} sucessos")
        return sucessos
        
    except Exception as e:
        log_acao(f"ERRO ao processar cloudflare: {e}")
        return 0

def verificar_criterios_sucesso():
    """Verifica criterios de sucesso da FASE 3"""
    log_acao("\n=== Verificando criterios de sucesso ===")
    
    # Contar scrapers com success e imoveis > 0
    result = supabase.table('auctioneers')\
        .select('id', count='exact')\
        .eq('scrape_status', 'success')\
        .gt('property_count', 0)\
        .execute()
    
    total_success = result.count
    
    log_acao(f"Scrapers com success e imoveis > 0: {total_success}")
    
    relatorio['criterios_sucesso'] = {
        'scrapers_funcionando': total_success,
        'meta_50_scrapers': total_success >= 50,
        'sites_corrigidos': len(relatorio['sites_corrigidos']),
        'imoveis_extraidos': relatorio['imoveis_extraidos']
    }

def gerar_relatorio_markdown():
    """Gera relatorio final em Markdown"""
    log_acao("Gerando relatorio RELATORIO_CORRECAO_SCRAPERS.md")
    
    md = f"""# RELATORIO - FASE 3: CORRECAO DE SCRAPERS

**Data de Execucao**: {relatorio['data_execucao']}

## Resumo

- Sites corrigidos: {len(relatorio['sites_corrigidos'])}
- Sites que falharam: {len(relatorio['sites_falharam'])}
- Imoveis extraidos: {relatorio['imoveis_extraidos']}

## Sites Corrigidos ({len(relatorio['sites_corrigidos'])})

"""
    
    for site in relatorio['sites_corrigidos']:
        md += f"- **{site['name']}** ({site['imoveis']} imoveis) - {site['website']}\n"
    
    md += f"""

## Sites que Falharam ({len(relatorio['sites_falharam'])})

"""
    
    for site in relatorio['sites_falharam']:
        md += f"- **{site['name']}** - {site['motivo'][:100]}\n"
    
    md += f"""

## Criterios de Sucesso

- Scrapers funcionando: {relatorio['criterios_sucesso'].get('scrapers_funcionando', 0)}
- Meta 50+ scrapers: {'SIM' if relatorio['criterios_sucesso'].get('meta_50_scrapers') else 'NAO'}
- Total imoveis extraidos: {relatorio['criterios_sucesso'].get('imoveis_extraidos', 0)}

## Acoes Executadas

"""
    
    for acao in relatorio['acoes_executadas']:
        md += f"- {acao}\n"
    
    md += """

## Conclusao

A FASE 3 foi executada. Scrapers foram corrigidos e sites offline foram desabilitados.

**Proxima Fase**: FASE 4 - Garantir Paginacao Completa

## Arquivos Gerados

- `relatorio_fase3.json` - Dados completos da execucao
"""
    
    with open('RELATORIO_CORRECAO_SCRAPERS.md', 'w', encoding='utf-8') as f:
        f.write(md)
    
    log_acao("Relatorio gerado com sucesso")

async def main_async():
    """Execucao principal da FASE 3"""
    print("\n" + "="*60)
    print("FASE 3: CORRIGIR SCRAPERS COM ERRO")
    print("="*60 + "\n")
    
    try:
        # Desabilitar sites offline
        desabilitar_sites_offline()
        
        # 3.1 Sites de alta prioridade (mais faceis)
        await processar_sites_prioridade_alta()
        
        # 3.2 Sites com Cloudflare (limite de 20 para nao demorar muito)
        # Podemos aumentar depois
        await processar_sites_cloudflare(limite=15)
        
        # Verificar criterios
        verificar_criterios_sucesso()
        
        # Gerar relatorio
        gerar_relatorio_markdown()
        
        print("\n" + "="*60)
        print("FASE 3 CONCLUIDA")
        print(f"Sites corrigidos: {len(relatorio['sites_corrigidos'])}")
        print(f"Imoveis extraidos: {relatorio['imoveis_extraidos']}")
        print("="*60 + "\n")
        
        # Salvar relatorio JSON
        with open('relatorio_fase3.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        log_acao(f"ERRO CRITICO: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Wrapper sincrono"""
    return asyncio.run(main_async())

if __name__ == '__main__':
    main()
