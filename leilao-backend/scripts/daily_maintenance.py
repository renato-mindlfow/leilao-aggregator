"""
Script de manutenção diária.
Executar via cron ou scheduler.

Tarefas:
1. Auditoria de qualidade de dados
2. Limpeza de imóveis com dados críticos faltando
3. Verificação de links quebrados (amostra)
4. Buscar imagens faltantes da Caixa (limite de 50 por execução)
5. Verificar e re-descobrir configs expiradas/problemáticas
"""

import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

async def run_discovery_maintenance():
    """Executa manutenção de descoberta de estrutura"""
    try:
        from app.services.discovery_orchestrator import discovery_orchestrator
        
        print("\nETAPA 3: Verificando leiloeiros para re-descoberta")
        print("-" * 40)
        
        # Re-descoberta para configs problemáticas
        rediscovery_result = await discovery_orchestrator.run_rediscovery(limit=20)
        print(f"   Verificados: {rediscovery_result['checked']}")
        print(f"   Re-descobertos: {rediscovery_result['rediscovered']}")
        print(f"   Falhas: {rediscovery_result['failed']}")
        
        if rediscovery_result['reasons']:
            print(f"   Razões: {rediscovery_result['reasons']}")
        
        # Estatísticas
        stats = discovery_orchestrator.get_discovery_stats()
        print(f"\n   Status de descoberta: {stats['discovery_status']}")
        print(f"   Tipos de site: {stats['site_types']}")
        
    except Exception as e:
        print(f"\n[ERRO] Erro na manutencao de descoberta: {e}")
        import traceback
        traceback.print_exc()

def main():
    print(f"\n{'='*60}")
    print(f"MANUTENÇÃO DIÁRIA - {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    # Verificar variáveis de ambiente críticas
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERRO] DATABASE_URL nao configurado!")
        print("Configure a variável de ambiente DATABASE_URL")
        return 1
    
    print("[OK] Variaveis de ambiente OK")
    print(f"   DATABASE_URL: {'*' * 20}...{database_url[-10:] if len(database_url) > 10 else ''}")
    print()
    
    try:
        # 1. Auditoria de qualidade de dados
        print("ETAPA 1: Auditoria de qualidade de dados")
        print("-" * 40)
        from scripts.audit_data_quality import main as audit_main
        stats = audit_main()
        print("[OK] Auditoria concluida\n")
    except Exception as e:
        print(f"[ERRO] Erro na auditoria: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    try:
        # 2. Limpeza de imóveis com dados ruins
        print("ETAPA 2: Limpeza de imóveis com dados críticos faltando")
        print("-" * 40)
        from scripts.cleanup_bad_properties import main as cleanup_main
        desativados = cleanup_main()
        print(f"[OK] Limpeza concluida: {desativados} imoveis desativados\n")
    except Exception as e:
        print(f"[ERRO] Erro na limpeza: {e}")
        import traceback
        traceback.print_exc()
        # Não retornar erro aqui, continuar com outras tarefas
    
    try:
        # 3. Verificação de links quebrados (amostra)
        print("ETAPA 3: Verificação de links quebrados (amostra)")
        print("-" * 40)
        from scripts.check_broken_links import main as check_links_main
        links_quebrados = asyncio.run(check_links_main())
        print(f"[OK] Verificacao de links concluida: {links_quebrados} links quebrados encontrados\n")
    except Exception as e:
        print(f"[ERRO] Erro na verificacao de links: {e}")
        import traceback
        traceback.print_exc()
        # Não retornar erro aqui, continuar com outras tarefas
    
    # 4. Buscar imagens da Caixa (se o script existir)
    try:
        from scripts.fetch_caixa_images import fetch_and_update_images
        print("\nETAPA 4: Buscar imagens da Caixa")
        print("-" * 40)
        fetch_and_update_images(limit=50)
        print("[OK] Busca de imagens concluida\n")
    except ImportError:
        print("\n[SKIP] Script de imagens da Caixa nao disponivel")
    except Exception as e:
        print(f"[ERRO] Erro ao buscar imagens: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Manutenção de descoberta
    try:
        asyncio.run(run_discovery_maintenance())
        print("[OK] Manutencao de descoberta concluida\n")
    except Exception as e:
        print(f"[ERRO] Erro na manutencao de descoberta: {e}")
        import traceback
        traceback.print_exc()
        # Não retornar erro aqui, apenas logar
    
    print(f"\n{'='*60}")
    print("MANUTENÇÃO CONCLUÍDA COM SUCESSO")
    print(f"{'='*60}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())

