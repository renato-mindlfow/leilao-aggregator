#!/usr/bin/env python3
"""
🚀 ATAQUE MASSIVO - COBERTURA DE 261 LEILOEIROS
Executa 3 ondas de extração priorizadas para maximizar cobertura
"""

import os
import sys
import json
import csv
import time
import asyncio
import codecs
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
from urllib.parse import urlparse

# Fix encoding for Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração de diretórios
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs" / "ataque_massivo" / datetime.now().strftime("%Y%m%d_%H%M%S")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Importar extratores
sys.path.insert(0, str(BASE_DIR / "scripts"))
sys.path.insert(0, str(BASE_DIR / "scripts" / "extractors"))

try:
    from extrator_tier1_http import ExtratorTier1
    from extrator_tier2_stealth import ExtratorTier2
except ImportError as e:
    logger.error(f"❌ Erro ao importar extratores: {e}")
    logger.error("Certifique-se de que os arquivos extrator_tier1_http.py e extrator_tier2_stealth.py existem em scripts/extractors/")
    sys.exit(1)


def carregar_leiloeiros_csv() -> List[Dict]:
    """Carrega lista mestre de leiloeiros do CSV."""
    csv_path = BASE_DIR / "LISTA_MESTRE_LEILOEIROS.csv"
    
    if not csv_path.exists():
        logger.error(f"❌ Arquivo não encontrado: {csv_path}")
        sys.exit(1)
    
    leiloeiros = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leiloeiros.append(row)
    
    logger.info(f"✅ {len(leiloeiros)} leiloeiros carregados do CSV")
    return leiloeiros


def classificar_leiloeiros(leiloeiros: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Classifica leiloeiros por prioridade de ataque.
    
    ONDA 1: pending - Nunca foram tentados (maior ROI)
    ONDA 2: error com property_count > 0 - Já funcionaram, só precisam recrawl
    ONDA 3: error com property_count = 0 - Nunca funcionaram (mais difíceis)
    """
    classificados = {
        'pendentes': [],      # ONDA 1
        'recrawl': [],        # ONDA 2  
        'investigar': [],     # ONDA 3
        'ja_funcionando': []  # Ignorar (success)
    }
    
    for l in leiloeiros:
        status = l.get('scrape_status', '').strip().lower()
        property_count = int(l.get('property_count') or 0)
        
        if status == 'pending':
            classificados['pendentes'].append(l)
        elif status == 'error' and property_count > 0:
            classificados['recrawl'].append(l)
        elif status == 'error' and property_count == 0:
            classificados['investigar'].append(l)
        elif status == 'success':
            classificados['ja_funcionando'].append(l)
    
    return classificados


def extrair_dominio(url: str) -> str:
    """Extrai domínio limpo de uma URL."""
    parsed = urlparse(url)
    dominio = parsed.netloc or parsed.path
    # Remover www. se existir
    dominio = dominio.replace('www.', '')
    return dominio


async def processar_onda(
    nome: str,
    sites: List[Dict],
    numero_onda: int,
    extrator_tier1: ExtratorTier1,
    extrator_tier2: ExtratorTier2
) -> Dict:
    """
    Processa uma onda de sites com estratégia tier1 -> tier2.
    """
    print(f"\n{'='*70}")
    print(f"🌊 ONDA {numero_onda}: {nome} ({len(sites)} sites)")
    print(f"{'='*70}\n")
    
    if not sites:
        logger.warning(f"⚠️ Nenhum site para processar na {nome}")
        return {
            'total': 0,
            'sucesso_tier1': 0,
            'sucesso_tier2': 0,
            'falha': 0,
            'imoveis': 0,
            'detalhes': []
        }
    
    resultados = {
        'total': len(sites),
        'sucesso_tier1': 0,
        'sucesso_tier2': 0,
        'falha': 0,
        'imoveis': 0,
        'detalhes': [],
        'inicio': datetime.now().isoformat()
    }
    
    # Setup browser para Tier 2
    await extrator_tier2.setup_browser()
    
    try:
        for i, site in enumerate(sites, 1):
            url = site.get('website', '')
            nome_site = site.get('name', 'Desconhecido')
            site_id = site.get('id', '')
            
            if not url:
                logger.warning(f"[{i}/{len(sites)}] ⚠️ Site sem URL: {nome_site}")
                continue
            
            dominio = extrair_dominio(url)
            
            print(f"\n[{i}/{len(sites)}] {'-'*50}")
            print(f"📍 Site: {nome_site}")
            print(f"🌐 URL: {url}")
            print(f"🔑 ID: {site_id}")
            
            try:
                # TENTAR TIER 1 PRIMEIRO (HTTP simples - mais rápido)
                logger.info(f"   🔄 Tentando TIER 1 (HTTP)...")
                resultado_t1 = await extrator_tier1.extrair_site(dominio, None)
                
                if resultado_t1.get('sucesso') and resultado_t1.get('total_imoveis', 0) > 0:
                    # SUCESSO no TIER 1!
                    imoveis_encontrados = resultado_t1.get('total_imoveis', 0)
                    resultados['sucesso_tier1'] += 1
                    resultados['imoveis'] += imoveis_encontrados
                    resultados['detalhes'].append({
                        'id': site_id,
                        'nome': nome_site,
                        'url': url,
                        'dominio': dominio,
                        'tier': 1,
                        'imoveis': imoveis_encontrados,
                        'status': 'success',
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"   ✅ TIER 1 SUCESSO: {imoveis_encontrados} imóveis extraídos")
                    
                    # Salvar resultado parcial
                    await salvar_resultado_parcial(resultados, numero_onda, nome)
                    
                    # Pausa entre sites
                    await asyncio.sleep(2)
                    continue
                
                # TIER 1 FALHOU - Tentar TIER 2 (Playwright Stealth)
                logger.info(f"   🔄 TIER 1 falhou. Tentando TIER 2 (Playwright)...")
                resultado_t2 = await extrator_tier2.extrair_site(dominio, None)
                
                if resultado_t2.get('sucesso') and resultado_t2.get('total_imoveis', 0) > 0:
                    # SUCESSO no TIER 2!
                    imoveis_encontrados = resultado_t2.get('total_imoveis', 0)
                    resultados['sucesso_tier2'] += 1
                    resultados['imoveis'] += imoveis_encontrados
                    resultados['detalhes'].append({
                        'id': site_id,
                        'nome': nome_site,
                        'url': url,
                        'dominio': dominio,
                        'tier': 2,
                        'imoveis': imoveis_encontrados,
                        'status': 'success',
                        'bloqueio': resultado_t2.get('bloqueio_detectado'),
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"   ✅ TIER 2 SUCESSO: {imoveis_encontrados} imóveis extraídos")
                    
                    # Salvar resultado parcial
                    await salvar_resultado_parcial(resultados, numero_onda, nome)
                    
                    # Pausa entre sites
                    await asyncio.sleep(2)
                    continue
                
                # FALHA EM AMBOS OS TIERS
                resultados['falha'] += 1
                erro_t2 = resultado_t2.get('erro', 'Desconhecido')
                bloqueio = resultado_t2.get('bloqueio_detectado')
                
                resultados['detalhes'].append({
                    'id': site_id,
                    'nome': nome_site,
                    'url': url,
                    'dominio': dominio,
                    'tier': None,
                    'imoveis': 0,
                    'status': 'failed',
                    'erro': erro_t2,
                    'bloqueio': bloqueio,
                    'timestamp': datetime.now().isoformat()
                })
                
                if bloqueio:
                    print(f"   ❌ FALHOU (Bloqueio detectado: {bloqueio})")
                else:
                    print(f"   ❌ FALHOU em ambos tiers: {erro_t2}")
                
            except Exception as e:
                # Erro inesperado
                resultados['falha'] += 1
                resultados['detalhes'].append({
                    'id': site_id,
                    'nome': nome_site,
                    'url': url,
                    'dominio': dominio,
                    'tier': None,
                    'imoveis': 0,
                    'status': 'error',
                    'erro': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                logger.error(f"   ❌ ERRO INESPERADO: {e}")
            
            # Pausa entre sites
            await asyncio.sleep(2)
    
    finally:
        # Fechar browser do Tier 2
        if extrator_tier2.browser:
            await extrator_tier2.browser.close()
    
    resultados['fim'] = datetime.now().isoformat()
    return resultados


async def salvar_resultado_parcial(resultados: Dict, numero_onda: int, nome_onda: str):
    """Salva resultado parcial da onda em progresso."""
    arquivo = LOGS_DIR / f"onda{numero_onda}_parcial.json"
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump({
            'onda': numero_onda,
            'nome': nome_onda,
            'timestamp': datetime.now().isoformat(),
            'resultados': resultados
        }, f, ensure_ascii=False, indent=2)


async def main():
    """Função principal - executa as 3 ondas de ataque."""
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         🚀 ATAQUE MASSIVO - COBERTURA DE LEILOEIROS 🚀     ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Objetivo: Maximizar cobertura no menor tempo possível       ║
    ║  Estratégia: 3 ondas de ataque priorizadas                   ║
    ║  Método: TIER 1 (HTTP) → TIER 2 (Playwright)                ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    inicio_total = datetime.now()
    
    # 1. CARREGAR E CLASSIFICAR LEILOEIROS
    print(f"\n{'='*70}")
    print("📋 CARREGANDO E CLASSIFICANDO LEILOEIROS...")
    print(f"{'='*70}\n")
    
    leiloeiros = carregar_leiloeiros_csv()
    classificados = classificar_leiloeiros(leiloeiros)
    
    print(f"📊 Classificação:")
    print(f"   • ONDA 1 - Pendentes (nunca tentados):     {len(classificados['pendentes'])} sites")
    print(f"   • ONDA 2 - Recrawl (já funcionaram):       {len(classificados['recrawl'])} sites")
    print(f"   • ONDA 3 - Investigar (nunca funcionaram): {len(classificados['investigar'])} sites")
    print(f"   • Já funcionando (ignorar):                {len(classificados['ja_funcionando'])} sites")
    print(f"   • TOTAL A PROCESSAR:                       {len(classificados['pendentes']) + len(classificados['recrawl']) + len(classificados['investigar'])} sites")
    
    # 2. INICIALIZAR EXTRATORES
    extrator_tier1 = ExtratorTier1()
    extrator_tier2 = ExtratorTier2()
    
    resultados_totais = {
        'inicio': inicio_total.isoformat(),
        'logs_dir': str(LOGS_DIR),
        'ondas': {}
    }
    
    # 3. ONDA 1: PENDENTES (Maior ROI - nunca foram tentados)
    if classificados['pendentes']:
        resultados_totais['ondas']['onda1_pendentes'] = await processar_onda(
            "PENDENTES (Nunca Tentados) - MAIOR ROI",
            classificados['pendentes'],
            1,
            extrator_tier1,
            extrator_tier2
        )
        
        # Salvar checkpoint
        with open(LOGS_DIR / 'checkpoint_onda1.json', 'w', encoding='utf-8') as f:
            json.dump(resultados_totais, f, ensure_ascii=False, indent=2)
    
    # 4. ONDA 2: RECRAWL (Já funcionaram - alta taxa de sucesso esperada)
    if classificados['recrawl']:
        resultados_totais['ondas']['onda2_recrawl'] = await processar_onda(
            "RECRAWL (Já Funcionaram)",
            classificados['recrawl'],
            2,
            extrator_tier1,
            extrator_tier2
        )
        
        # Salvar checkpoint
        with open(LOGS_DIR / 'checkpoint_onda2.json', 'w', encoding='utf-8') as f:
            json.dump(resultados_totais, f, ensure_ascii=False, indent=2)
    
    # 5. ONDA 3: INVESTIGAR (Nunca funcionaram - mais difíceis)
    if classificados['investigar']:
        resultados_totais['ondas']['onda3_investigar'] = await processar_onda(
            "INVESTIGAR (Nunca Funcionaram)",
            classificados['investigar'],
            3,
            extrator_tier1,
            extrator_tier2
        )
        
        # Salvar checkpoint
        with open(LOGS_DIR / 'checkpoint_onda3.json', 'w', encoding='utf-8') as f:
            json.dump(resultados_totais, f, ensure_ascii=False, indent=2)
    
    fim_total = datetime.now()
    resultados_totais['fim'] = fim_total.isoformat()
    duracao_total = (fim_total - inicio_total).total_seconds()
    resultados_totais['duracao_segundos'] = duracao_total
    resultados_totais['duracao_formatada'] = f"{duracao_total // 3600:.0f}h {(duracao_total % 3600) // 60:.0f}m {duracao_total % 60:.0f}s"
    
    # 6. SALVAR RESULTADOS FINAIS
    arquivo_final = LOGS_DIR / 'resultados_ataque_massivo_FINAL.json'
    with open(arquivo_final, 'w', encoding='utf-8') as f:
        json.dump(resultados_totais, f, ensure_ascii=False, indent=2)
    
    # 7. GERAR RELATÓRIO FINAL
    print("\n" + "="*70)
    print("📊 RESUMO DO ATAQUE MASSIVO - RESULTADO FINAL")
    print("="*70)
    
    total_sites_processados = 0
    total_sucesso_tier1 = 0
    total_sucesso_tier2 = 0
    total_falhas = 0
    total_imoveis = 0
    
    for nome_onda, res in resultados_totais['ondas'].items():
        total_sites_processados += res.get('total', 0)
        total_sucesso_tier1 += res.get('sucesso_tier1', 0)
        total_sucesso_tier2 += res.get('sucesso_tier2', 0)
        total_falhas += res.get('falha', 0)
        total_imoveis += res.get('imoveis', 0)
        
        sucesso_total = res.get('sucesso_tier1', 0) + res.get('sucesso_tier2', 0)
        taxa = (sucesso_total / res.get('total', 1)) * 100 if res.get('total', 0) > 0 else 0
        
        print(f"\n{nome_onda.upper().replace('_', ' ')}:")
        print(f"   Total sites:      {res.get('total', 0)}")
        print(f"   Sucesso TIER 1:   {res.get('sucesso_tier1', 0)}")
        print(f"   Sucesso TIER 2:   {res.get('sucesso_tier2', 0)}")
        print(f"   Falhas:           {res.get('falha', 0)}")
        print(f"   Imóveis extraídos:{res.get('imoveis', 0):,}")
        print(f"   Taxa de sucesso:  {taxa:.1f}%")
    
    total_sucesso = total_sucesso_tier1 + total_sucesso_tier2
    taxa_final = (total_sucesso / total_sites_processados) * 100 if total_sites_processados > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"🎯 RESULTADO CONSOLIDADO FINAL:")
    print(f"{'='*70}")
    print(f"   Sites processados:        {total_sites_processados}")
    print(f"   Sites com SUCESSO:        {total_sucesso} ({taxa_final:.1f}%)")
    print(f"      ├─ TIER 1 (HTTP):      {total_sucesso_tier1}")
    print(f"      └─ TIER 2 (Playwright):{total_sucesso_tier2}")
    print(f"   Sites com FALHA:          {total_falhas}")
    print(f"   TOTAL de IMÓVEIS:         {total_imoveis:,}")
    print(f"   Duração total:            {resultados_totais['duracao_formatada']}")
    print(f"{'='*70}")
    print(f"\n📁 Logs e resultados salvos em:")
    print(f"   {LOGS_DIR}")
    print(f"\n📄 Arquivo final:")
    print(f"   {arquivo_final}")
    print(f"\n{'='*70}")
    print("✅ ATAQUE MASSIVO CONCLUÍDO!")
    print(f"{'='*70}\n")
    
    # 8. GERAR CSV DE RESULTADOS PARA FÁCIL ANÁLISE
    csv_file = LOGS_DIR / 'resultados_por_site.csv'
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Nome', 'URL', 'Onda', 'Tier', 'Status', 'Imóveis', 'Erro', 'Bloqueio'])
        
        for nome_onda, res in resultados_totais['ondas'].items():
            for detalhe in res.get('detalhes', []):
                writer.writerow([
                    detalhe.get('id', ''),
                    detalhe.get('nome', ''),
                    detalhe.get('url', ''),
                    nome_onda,
                    detalhe.get('tier', ''),
                    detalhe.get('status', ''),
                    detalhe.get('imoveis', 0),
                    detalhe.get('erro', ''),
                    detalhe.get('bloqueio', '')
                ])
    
    print(f"📊 CSV de resultados gerado: {csv_file}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Execução interrompida pelo usuário")
        print(f"📁 Resultados parciais salvos em: {LOGS_DIR}")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        print(f"\n❌ Erro fatal: {e}")
        print(f"📁 Logs salvos em: {LOGS_DIR}")
        sys.exit(1)
