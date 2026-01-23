"""
FASE 4: GARANTIR PAGINACAO COMPLETA
Verifica e documenta paginacao nos scrapers existentes
"""
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from collections import defaultdict

load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

# Estrutura para armazenar relatorio
relatorio = {
    'fase': 'FASE 4 - Garantir Paginacao Completa',
    'data_execucao': datetime.now().isoformat(),
    'acoes_executadas': [],
    'top_leiloeiros': [],
    'analise_paginacao': {},
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

def analisar_top_leiloeiros():
    """Analisa os top 20 leiloeiros por quantidade de imoveis"""
    log_acao("=== 4.1 Analisando top 20 leiloeiros ===")
    
    # Buscar top leiloeiros
    result = supabase.table('auctioneers')\
        .select('id, name, website, property_count, scrape_status, last_scrape')\
        .order('property_count', desc=True)\
        .limit(20)\
        .execute()
    
    top_leiloeiros = result.data
    
    log_acao(f"Top 20 leiloeiros identificados")
    
    total_imoveis_top20 = sum(l.get('property_count', 0) or 0 for l in top_leiloeiros)
    
    # Buscar total geral
    total_result = supabase.table('properties').select('id', count='exact').execute()
    total_geral = total_result.count
    
    percentual = (total_imoveis_top20 / total_geral * 100) if total_geral > 0 else 0
    
    log_acao(f"Top 20 representam: {total_imoveis_top20} imoveis ({percentual:.1f}% do total)")
    
    # Mostrar top 10
    print("\nTOP 10 LEILOEIROS:")
    for i, leiloeiro in enumerate(top_leiloeiros[:10], 1):
        count = leiloeiro.get('property_count', 0) or 0
        status = leiloeiro.get('scrape_status', 'unknown')
        print(f"{i:2d}. {leiloeiro['name']:30s} - {count:5d} imoveis ({status})")
    
    relatorio['top_leiloeiros'] = top_leiloeiros
    relatorio['analise_paginacao']['total_top20'] = total_imoveis_top20
    relatorio['analise_paginacao']['percentual_top20'] = round(percentual, 1)
    
    return top_leiloeiros

def verificar_distribuicao_leiloeiros():
    """Verifica distribuicao de imoveis por leiloeiro"""
    log_acao("\n=== 4.2 Verificando distribuicao de imoveis ===")
    
    # Buscar todos leiloeiros com imoveis
    result = supabase.table('auctioneers')\
        .select('id, name, property_count')\
        .gt('property_count', 0)\
        .order('property_count', desc=True)\
        .execute()
    
    leiloeiros = result.data
    
    # Analise de distribuicao
    faixas = {
        '1000+': 0,
        '500-999': 0,
        '100-499': 0,
        '50-99': 0,
        '10-49': 0,
        '1-9': 0
    }
    
    for l in leiloeiros:
        count = l.get('property_count', 0) or 0
        if count >= 1000:
            faixas['1000+'] += 1
        elif count >= 500:
            faixas['500-999'] += 1
        elif count >= 100:
            faixas['100-499'] += 1
        elif count >= 50:
            faixas['50-99'] += 1
        elif count >= 10:
            faixas['10-49'] += 1
        else:
            faixas['1-9'] += 1
    
    print("\nDISTRIBUICAO DE LEILOEIROS POR FAIXA:")
    for faixa, qtd in faixas.items():
        print(f"  {faixa:10s}: {qtd:3d} leiloeiros")
    
    relatorio['analise_paginacao']['distribuicao'] = faixas
    relatorio['analise_paginacao']['leiloeiros_com_imoveis'] = len(leiloeiros)
    
    log_acao(f"Total de leiloeiros com imoveis: {len(leiloeiros)}")

def analisar_crescimento_potencial():
    """Analisa potencial de crescimento com paginacao"""
    log_acao("\n=== 4.3 Analisando potencial de crescimento ===")
    
    # Leiloeiros com poucos imoveis podem ter paginacao incompleta
    result = supabase.table('auctioneers')\
        .select('id, name, website, property_count, scrape_status')\
        .eq('scrape_status', 'success')\
        .gte('property_count', 1)\
        .lte('property_count', 50)\
        .order('property_count', desc=True)\
        .execute()
    
    candidatos_paginacao = result.data
    
    log_acao(f"Encontrados {len(candidatos_paginacao)} leiloeiros com 1-50 imoveis")
    log_acao("Estes podem ter paginacao incompleta (pegando so 1a pagina)")
    
    # Estimar potencial
    # Se cada um tiver em media 100 imoveis (conservador), teriamos:
    potencial = len(candidatos_paginacao) * 50  # +50 imoveis cada
    
    log_acao(f"Potencial conservador: +{potencial} imoveis com paginacao completa")
    
    relatorio['analise_paginacao']['candidatos_paginacao'] = len(candidatos_paginacao)
    relatorio['analise_paginacao']['potencial_crescimento'] = potencial

def recomendar_acoes():
    """Recomenda acoes especificas"""
    log_acao("\n=== 4.4 Recomendando acoes ===")
    
    recomendacoes = []
    
    # 1. Focar na Caixa (maior leiloeiro)
    caixa = supabase.table('auctioneers')\
        .select('id, name, property_count')\
        .ilike('name', '%caixa%')\
        .execute()
    
    if caixa.data:
        caixa_count = caixa.data[0].get('property_count', 0) or 0
        recomendacoes.append({
            'prioridade': 'ALTA',
            'acao': 'Melhorar scraper Caixa Federal',
            'impacto': f'{caixa_count} imoveis (maior leiloeiro)',
            'detalhes': 'Ja existe script sync_caixa.py - otimizar paginacao'
        })
    
    # 2. Top 10 com success
    top10_success = supabase.table('auctioneers')\
        .select('id, name, property_count')\
        .eq('scrape_status', 'success')\
        .gt('property_count', 0)\
        .order('property_count', desc=True)\
        .limit(10)\
        .execute()
    
    if top10_success.data:
        total_top10 = sum(l.get('property_count', 0) or 0 for l in top10_success.data)
        recomendacoes.append({
            'prioridade': 'ALTA',
            'acao': 'Verificar paginacao completa no Top 10',
            'impacto': f'{total_top10} imoveis atuais',
            'detalhes': 'Garantir que pegam todas as paginas, nao so a primeira'
        })
    
    # 3. Scrapers pendentes grandes
    recomendacoes.append({
        'prioridade': 'MEDIA',
        'acao': 'Implementar scrapers para leiloeiros conhecidos pendentes',
        'impacto': 'Potencial de +5.000 a 10.000 imoveis',
        'detalhes': '348 leiloeiros pendentes - focar nos 20 maiores'
    })
    
    print("\nRECOMENDACOES:")
    for rec in recomendacoes:
        print(f"\n[{rec['prioridade']}] {rec['acao']}")
        print(f"  Impacto: {rec['impacto']}")
        print(f"  Detalhes: {rec['detalhes']}")
    
    relatorio['analise_paginacao']['recomendacoes'] = recomendacoes

def verificar_criterios_sucesso():
    """Verifica criterios de sucesso da FASE 4"""
    log_acao("\n=== Verificando criterios de sucesso ===")
    
    # Total de imoveis
    total = supabase.table('properties').select('id', count='exact').execute()
    total_imoveis = total.count
    
    # Meta: aumentar em 20% (de ~53k para ~64k)
    meta_20_pct = 53000 * 1.2
    atingiu_meta = total_imoveis >= meta_20_pct
    
    relatorio['criterios_sucesso'] = {
        'total_imoveis_atual': total_imoveis,
        'meta_20_pct': int(meta_20_pct),
        'atingiu_meta_20pct': atingiu_meta,
        'top20_analisados': len(relatorio['top_leiloeiros']) >= 20,
        'recomendacoes_geradas': 'recomendacoes' in relatorio['analise_paginacao']
    }
    
    log_acao(f"Total de imoveis: {total_imoveis}")
    log_acao(f"Meta 20%: {int(meta_20_pct)} - {'ATINGIDA' if atingiu_meta else 'NAO ATINGIDA'}")

def gerar_relatorio_markdown():
    """Gera relatorio final em Markdown"""
    log_acao("Gerando relatorio RELATORIO_PAGINACAO.md")
    
    md = f"""# RELATORIO - FASE 4: PAGINACAO COMPLETA

**Data de Execucao**: {relatorio['data_execucao']}

## Resumo

- Total de imoveis atual: {relatorio['criterios_sucesso'].get('total_imoveis_atual', 0):,}
- Top 20 leiloeiros: {relatorio['analise_paginacao'].get('total_top20', 0):,} imoveis ({relatorio['analise_paginacao'].get('percentual_top20', 0)}%)
- Leiloeiros com imoveis: {relatorio['analise_paginacao'].get('leiloeiros_com_imoveis', 0)}

## Top 10 Leiloeiros

"""
    
    for i, l in enumerate(relatorio['top_leiloeiros'][:10], 1):
        count = l.get('property_count', 0) or 0
        status = l.get('scrape_status', 'unknown')
        md += f"{i}. **{l['name']}** - {count:,} imoveis ({status})\n"
    
    md += f"""

## Distribuicao de Leiloeiros

"""
    
    dist = relatorio['analise_paginacao'].get('distribuicao', {})
    for faixa, qtd in dist.items():
        md += f"- {faixa}: {qtd} leiloeiros\n"
    
    md += f"""

## Analise de Paginacao

- Candidatos para paginacao completa: {relatorio['analise_paginacao'].get('candidatos_paginacao', 0)}
- Potencial de crescimento: +{relatorio['analise_paginacao'].get('potencial_crescimento', 0):,} imoveis

## Recomendacoes

"""
    
    for rec in relatorio['analise_paginacao'].get('recomendacoes', []):
        md += f"\n### [{rec['prioridade']}] {rec['acao']}\n\n"
        md += f"**Impacto**: {rec['impacto']}\n\n"
        md += f"**Detalhes**: {rec['detalhes']}\n"
    
    md += f"""

## Criterios de Sucesso

- Total de imoveis: {relatorio['criterios_sucesso'].get('total_imoveis_atual', 0):,}
- Meta 20%: {relatorio['criterios_sucesso'].get('meta_20_pct', 0):,}
- Atingiu meta: {'SIM' if relatorio['criterios_sucesso'].get('atingiu_meta_20pct') else 'NAO'}
- Top 20 analisados: {'SIM' if relatorio['criterios_sucesso'].get('top20_analisados') else 'NAO'}

## Conclusao

A FASE 4 analisou a distribuicao atual de imoveis e identificou oportunidades de melhoria na paginacao.
O foco principal deve ser nos scrapers que JA funcionam, garantindo que pegam todas as paginas.

**Proxima Fase**: FASE 5 - Validar Qualidade dos Dados

## Acoes Executadas

"""
    
    for acao in relatorio['acoes_executadas']:
        md += f"- {acao}\n"
    
    with open('RELATORIO_PAGINACAO.md', 'w', encoding='utf-8') as f:
        f.write(md)
    
    log_acao("Relatorio gerado com sucesso")

def main():
    """Execucao principal da FASE 4"""
    print("\n" + "="*60)
    print("FASE 4: GARANTIR PAGINACAO COMPLETA")
    print("="*60 + "\n")
    
    try:
        # 4.1 Analisar top leiloeiros
        analisar_top_leiloeiros()
        
        # 4.2 Verificar distribuicao
        verificar_distribuicao_leiloeiros()
        
        # 4.3 Analisar potencial
        analisar_crescimento_potencial()
        
        # 4.4 Recomendar acoes
        recomendar_acoes()
        
        # Verificar criterios
        verificar_criterios_sucesso()
        
        # Gerar relatorio
        gerar_relatorio_markdown()
        
        print("\n" + "="*60)
        print("FASE 4 CONCLUIDA")
        print("="*60 + "\n")
        
        # Salvar relatorio JSON
        with open('relatorio_fase4.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        log_acao(f"ERRO CRITICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    main()
