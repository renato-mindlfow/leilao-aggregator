"""
Script de manutenção diária.
Executar via cron ou scheduler.

Tarefas:
1. Auditoria e correção de dados
2. Buscar imagens faltantes da Caixa (limite de 50 por execução)
3. Verificar e re-descobrir configs expiradas/problemáticas
"""

import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from scripts.audit_data_quality import audit_data_quality

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
        print(f"\n❌ Erro na manutenção de descoberta: {e}")
        import traceback
        traceback.print_exc()

def main():
    print(f"\n{'='*60}")
    print(f"MANUTENÇÃO DIÁRIA - {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    # Verificar variáveis de ambiente críticas
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERRO: DATABASE_URL não configurado!")
        print("Configure a variável de ambiente DATABASE_URL")
        return 1
    
    print("✅ Variáveis de ambiente OK")
    print(f"   DATABASE_URL: {'*' * 20}...{database_url[-10:] if len(database_url) > 10 else ''}")
    print()
    
    try:
        # 1. Auditoria com correção
        print("ETAPA 1: Auditoria de dados")
        print("-" * 40)
        audit_data_quality(fix=True)
        print("✅ Auditoria concluída\n")
    except Exception as e:
        print(f"❌ Erro na auditoria: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 2. Buscar imagens da Caixa (se o script existir)
    try:
        from scripts.fetch_caixa_images import fetch_and_update_images
        print("\nETAPA 2: Buscar imagens da Caixa")
        print("-" * 40)
        fetch_and_update_images(limit=50)
        print("✅ Busca de imagens concluída\n")
    except ImportError:
        print("\n⏭️ Script de imagens da Caixa não disponível")
    except Exception as e:
        print(f"❌ Erro ao buscar imagens: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Manutenção de descoberta
    try:
        asyncio.run(run_discovery_maintenance())
        print("✅ Manutenção de descoberta concluída\n")
    except Exception as e:
        print(f"❌ Erro na manutenção de descoberta: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print(f"\n{'='*60}")
    print("MANUTENÇÃO CONCLUÍDA COM SUCESSO")
    print(f"{'='*60}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())

