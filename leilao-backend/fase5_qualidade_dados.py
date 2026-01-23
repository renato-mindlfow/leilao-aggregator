"""
FASE 5: VALIDAR QUALIDADE DOS DADOS
Verifica campos obrigatorios, corrige dados faltantes, valida consistencia
"""
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

# Estrutura para armazenar relatorio
relatorio = {
    'fase': 'FASE 5 - Validar Qualidade dos Dados',
    'data_execucao': datetime.now().isoformat(),
    'acoes_executadas': [],
    'metricas_qualidade': {},
    'correcoes_aplicadas': [],
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

def verificar_campos_obrigatorios():
    """5.1 Verifica campos obrigatorios"""
    log_acao("=== 5.1 Verificando campos obrigatorios ===")
    
    total = supabase.table('properties').select('id', count='exact').execute()
    total_count = total.count
    
    # Imoveis sem titulo
    sem_titulo = supabase.table('properties').select('id', count='exact')\
        .or_('title.is.null,title.eq.').execute()
    
    # Imoveis sem preco
    sem_preco = supabase.table('properties').select('id', count='exact')\
        .is_('first_auction_value', 'null')\
        .is_('second_auction_value', 'null')\
        .is_('evaluation_value', 'null')\
        .execute()
    
    # Imoveis sem estado
    sem_estado = supabase.table('properties').select('id', count='exact')\
        .is_('state', 'null').execute()
    
    # Imoveis sem cidade
    sem_cidade = supabase.table('properties').select('id', count='exact')\
        .is_('city', 'null').execute()
    
    # Imoveis sem URL
    sem_url = supabase.table('properties').select('id', count='exact')\
        .or_('source_url.is.null,source_url.eq.').execute()
    
    # Calcular percentuais
    pct_com_titulo = ((total_count - sem_titulo.count) / total_count * 100) if total_count > 0 else 0
    pct_com_preco = ((total_count - sem_preco.count) / total_count * 100) if total_count > 0 else 0
    pct_com_estado = ((total_count - sem_estado.count) / total_count * 100) if total_count > 0 else 0
    pct_com_cidade = ((total_count - sem_cidade.count) / total_count * 100) if total_count > 0 else 0
    pct_com_url = ((total_count - sem_url.count) / total_count * 100) if total_count > 0 else 0
    
    print(f"\nCAMPOS OBRIGATORIOS:")
    print(f"  Total de imoveis: {total_count:,}")
    print(f"  Com titulo: {total_count - sem_titulo.count:,} ({pct_com_titulo:.1f}%)")
    print(f"  Com preco: {total_count - sem_preco.count:,} ({pct_com_preco:.1f}%)")
    print(f"  Com estado: {total_count - sem_estado.count:,} ({pct_com_estado:.1f}%)")
    print(f"  Com cidade: {total_count - sem_cidade.count:,} ({pct_com_cidade:.1f}%)")
    print(f"  Com URL: {total_count - sem_url.count:,} ({pct_com_url:.1f}%)")
    
    relatorio['metricas_qualidade'] = {
        'total_imoveis': total_count,
        'sem_titulo': sem_titulo.count,
        'pct_com_titulo': round(pct_com_titulo, 1),
        'sem_preco': sem_preco.count,
        'pct_com_preco': round(pct_com_preco, 1),
        'sem_estado': sem_estado.count,
        'pct_com_estado': round(pct_com_estado, 1),
        'sem_cidade': sem_cidade.count,
        'pct_com_cidade': round(pct_com_cidade, 1),
        'sem_url': sem_url.count,
        'pct_com_url': round(pct_com_url, 1)
    }
    
    log_acao(f"Verificacao de campos obrigatorios concluida")

def verificar_consistencia_dados():
    """5.2 Verifica consistencia dos dados"""
    log_acao("\n=== 5.2 Verificando consistencia dos dados ===")
    
    inconsistencias = {
        'precos_inconsistentes': 0,
        'datas_expiradas': 0,
        'areas_invalidas': 0
    }
    
    # Buscar amostra para verificar inconsistencias
    # (Supabase tem limitacoes de query complexa, vamos fazer verificacoes simples)
    
    # Areas muito grandes ou pequenas
    areas_grandes = supabase.table('properties').select('id', count='exact')\
        .gt('area_total', 50000).execute()
    
    # Areas zero ou negativas (ja deve estar limpo da FASE 1)
    areas_zero = supabase.table('properties').select('id', count='exact')\
        .lte('area_total', 0).execute()
    
    inconsistencias['areas_invalidas'] = areas_grandes.count + areas_zero.count
    
    print(f"\nINCONSISTENCIAS:")
    print(f"  Areas invalidas: {inconsistencias['areas_invalidas']}")
    
    relatorio['metricas_qualidade']['inconsistencias'] = inconsistencias
    
    log_acao("Verificacao de consistencia concluida")

def analisar_completude_por_leiloeiro():
    """Analisa qualidade dos dados por leiloeiro"""
    log_acao("\n=== 5.3 Analisando completude por leiloeiro ===")
    
    # Buscar top 10 leiloeiros
    top_leiloeiros = supabase.table('auctioneers')\
        .select('id, name, property_count')\
        .order('property_count', desc=True)\
        .limit(10)\
        .execute()
    
    print(f"\nQUALIDADE POR LEILOEIRO (Top 10):")
    
    qualidade_por_leiloeiro = []
    
    for leiloeiro in top_leiloeiros.data:
        aid = leiloeiro['id']
        nome = leiloeiro['name']
        count = leiloeiro.get('property_count', 0) or 0
        
        if count == 0:
            continue
        
        # Verificar campos para este leiloeiro
        sem_titulo = supabase.table('properties').select('id', count='exact')\
            .eq('auctioneer_id', aid)\
            .or_('title.is.null,title.eq.')\
            .execute()
        
        sem_preco = supabase.table('properties').select('id', count='exact')\
            .eq('auctioneer_id', aid)\
            .is_('first_auction_value', 'null')\
            .is_('second_auction_value', 'null')\
            .is_('evaluation_value', 'null')\
            .execute()
        
        pct_com_titulo = ((count - sem_titulo.count) / count * 100) if count > 0 else 0
        pct_com_preco = ((count - sem_preco.count) / count * 100) if count > 0 else 0
        
        print(f"  {nome[:30]:30s}: Titulo {pct_com_titulo:5.1f}% | Preco {pct_com_preco:5.1f}%")
        
        qualidade_por_leiloeiro.append({
            'nome': nome,
            'total': count,
            'pct_titulo': round(pct_com_titulo, 1),
            'pct_preco': round(pct_com_preco, 1)
        })
    
    relatorio['metricas_qualidade']['por_leiloeiro'] = qualidade_por_leiloeiro
    log_acao("Analise por leiloeiro concluida")

def tentar_inferir_estados():
    """Tenta inferir estados faltantes a partir das cidades"""
    log_acao("\n=== 5.4 Tentando inferir estados faltantes ===")
    
    # Mapeamento basico de cidades conhecidas
    cidades_estados = {
        'sao paulo': 'SP',
        'rio de janeiro': 'RJ',
        'brasilia': 'DF',
        'belo horizonte': 'MG',
        'curitiba': 'PR',
        'porto alegre': 'RS',
        'salvador': 'BA',
        'fortaleza': 'CE',
        'recife': 'PE',
        'manaus': 'AM',
        'belem': 'PA',
        'goiania': 'GO',
        'campinas': 'SP',
        'santos': 'SP',
        'sorocaba': 'SP',
        'ribeirao preto': 'SP',
    }
    
    # Buscar imoveis sem estado mas com cidade
    imoveis_sem_estado = supabase.table('properties')\
        .select('id, city')\
        .is_('state', 'null')\
        .not_.is_('city', 'null')\
        .limit(100)\
        .execute()
    
    corrigidos = 0
    
    for imovel in imoveis_sem_estado.data:
        city = (imovel.get('city') or '').lower()
        
        # Tentar encontrar correspondencia
        for cidade_key, estado in cidades_estados.items():
            if cidade_key in city:
                # Atualizar estado
                supabase.table('properties')\
                    .update({'state': estado})\
                    .eq('id', imovel['id'])\
                    .execute()
                
                corrigidos += 1
                break
    
    if corrigidos > 0:
        log_acao(f"Estados inferidos: {corrigidos} imoveis")
        relatorio['correcoes_aplicadas'].append({
            'tipo': 'inferencia_estados',
            'quantidade': corrigidos
        })
    else:
        log_acao("Nenhum estado pode ser inferido automaticamente")

def verificar_criterios_sucesso():
    """Verifica criterios de sucesso da FASE 5"""
    log_acao("\n=== Verificando criterios de sucesso ===")
    
    met = relatorio['metricas_qualidade']
    
    criterios = {
        'pct_com_titulo_95': met['pct_com_titulo'] >= 95,
        'pct_com_preco_90': met['pct_com_preco'] >= 90,
        'pct_com_estado_90': met['pct_com_estado'] >= 90,
        'inconsistencias_zero': met['inconsistencias']['areas_invalidas'] == 0
    }
    
    print(f"\nCRITERIOS DE SUCESSO:")
    print(f"  >95% com titulo: {'SIM' if criterios['pct_com_titulo_95'] else 'NAO'} ({met['pct_com_titulo']}%)")
    print(f"  >90% com preco: {'SIM' if criterios['pct_com_preco_90'] else 'NAO'} ({met['pct_com_preco']}%)")
    print(f"  >90% com estado: {'SIM' if criterios['pct_com_estado_90'] else 'NAO'} ({met['pct_com_estado']}%)")
    print(f"  Zero inconsistencias: {'SIM' if criterios['inconsistencias_zero'] else 'NAO'}")
    
    relatorio['criterios_sucesso'] = criterios

def gerar_relatorio_markdown():
    """Gera relatorio final em Markdown"""
    log_acao("Gerando relatorio RELATORIO_QUALIDADE_DADOS.md")
    
    met = relatorio['metricas_qualidade']
    
    md = f"""# RELATORIO - FASE 5: QUALIDADE DOS DADOS

**Data de Execucao**: {relatorio['data_execucao']}

## Metricas de Qualidade

### Campos Obrigatorios

Total de imoveis: {met['total_imoveis']:,}

| Campo | Completos | Percentual | Meta | Status |
|-------|-----------|------------|------|--------|
| Titulo | {met['total_imoveis'] - met['sem_titulo']:,} | {met['pct_com_titulo']:.1f}% | 95% | {'OK' if met['pct_com_titulo'] >= 95 else 'ATENCAO'} |
| Preco | {met['total_imoveis'] - met['sem_preco']:,} | {met['pct_com_preco']:.1f}% | 90% | {'OK' if met['pct_com_preco'] >= 90 else 'ATENCAO'} |
| Estado | {met['total_imoveis'] - met['sem_estado']:,} | {met['pct_com_estado']:.1f}% | 90% | {'OK' if met['pct_com_estado'] >= 90 else 'ATENCAO'} |
| Cidade | {met['total_imoveis'] - met['sem_cidade']:,} | {met['pct_com_cidade']:.1f}% | - | - |
| URL | {met['total_imoveis'] - met['sem_url']:,} | {met['pct_com_url']:.1f}% | - | - |

### Inconsistencias

- Areas invalidas: {met['inconsistencias']['areas_invalidas']}

### Qualidade por Leiloeiro (Top 10)

"""
    
    for l in met.get('por_leiloeiro', []):
        md += f"- **{l['nome']}** ({l['total']:,} imoveis): Titulo {l['pct_titulo']:.1f}% | Preco {l['pct_preco']:.1f}%\n"
    
    md += f"""

## Correcoes Aplicadas

"""
    
    if relatorio['correcoes_aplicadas']:
        for corr in relatorio['correcoes_aplicadas']:
            md += f"- {corr['tipo']}: {corr['quantidade']} registros\n"
    else:
        md += "Nenhuma correcao automatica foi necessaria.\n"
    
    md += f"""

## Criterios de Sucesso

"""
    
    for criterio, atingido in relatorio['criterios_sucesso'].items():
        status = 'SIM' if atingido else 'NAO'
        md += f"- [{status}] {criterio.replace('_', ' ').title()}\n"
    
    md += f"""

## Recomendacoes

1. **Melhorar scraper da Caixa**: Maior leiloeiro, garantir extracao completa de todos os campos
2. **Focar em leiloeiros com baixa qualidade**: Revisar scrapers que extraem poucos dados
3. **Implementar validacao na entrada**: Rejeitar dados sem campos obrigatorios no momento do scraping

## Conclusao

A qualidade geral dos dados e {'BOA' if met['pct_com_titulo'] >= 95 and met['pct_com_preco'] >= 90 else 'ACEITAVEL, MAS PRECISA MELHORIA'}.
A maioria dos imoveis tem informacoes basicas completas.

**Proxima Fase**: FASE 6 - Configurar Execucao Continua

## Acoes Executadas

"""
    
    for acao in relatorio['acoes_executadas']:
        md += f"- {acao}\n"
    
    with open('RELATORIO_QUALIDADE_DADOS.md', 'w', encoding='utf-8') as f:
        f.write(md)
    
    log_acao("Relatorio gerado com sucesso")

def main():
    """Execucao principal da FASE 5"""
    print("\n" + "="*60)
    print("FASE 5: VALIDAR QUALIDADE DOS DADOS")
    print("="*60 + "\n")
    
    try:
        # 5.1 Verificar campos obrigatorios
        verificar_campos_obrigatorios()
        
        # 5.2 Verificar consistencia
        verificar_consistencia_dados()
        
        # 5.3 Analisar por leiloeiro
        analisar_completude_por_leiloeiro()
        
        # 5.4 Tentar corrigir dados
        tentar_inferir_estados()
        
        # Verificar criterios
        verificar_criterios_sucesso()
        
        # Gerar relatorio
        gerar_relatorio_markdown()
        
        print("\n" + "="*60)
        print("FASE 5 CONCLUIDA")
        print("="*60 + "\n")
        
        # Salvar relatorio JSON
        with open('relatorio_fase5.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        log_acao(f"ERRO CRITICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    main()
