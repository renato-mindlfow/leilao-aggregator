#!/usr/bin/env python3
"""
Script de Manutencao Diaria do LeiloHub
Executa diariamente as 3:00 AM BRT
"""
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import asyncio

load_dotenv()

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

async def limpar_imoveis_expirados():
    """Remove imoveis com leilao ha mais de 30 dias"""
    print("1. Limpando imoveis expirados...")
    
    # Data limite (30 dias atras)
    data_limite = (datetime.now() - timedelta(days=30)).isoformat()
    
    # Marcar como inativos
    result = supabase.table('properties')\
        .update({'is_active': False})\
        .lt('first_auction_date', data_limite)\
        .eq('is_active', True)\
        .execute()
    
    print(f"   Imoveis marcados como inativos: verificar logs")
    return True

async def re_executar_scrapers_ativos():
    """Re-executa scrapers com success"""
    print("2. Re-executando scrapers ativos...")
    
    # Buscar scrapers com success
    scrapers = supabase.table('auctioneers')\
        .select('id, name, website')\
        .eq('scrape_status', 'success')\
        .gt('property_count', 0)\
        .limit(10)\
        .execute()
    
    print(f"   Scrapers ativos: {len(scrapers.data)}")
    print("   Re-execucao: implementar com PlaywrightIntegratedScraper")
    
    return True

async def verificar_scrapers_falhados():
    """Verifica scrapers que falharam"""
    print("3. Verificando scrapers falhados...")
    
    # Buscar scrapers com erro
    erros = supabase.table('auctioneers')\
        .select('id, name, scrape_error')\
        .eq('scrape_status', 'error')\
        .limit(5)\
        .execute()
    
    print(f"   Scrapers com erro: {len(erros.data)}")
    return True

async def atualizar_metricas():
    """Atualiza metricas do sistema"""
    print("4. Atualizando metricas...")
    
    # Total de imoveis ativos
    total = supabase.table('properties')\
        .select('id', count='exact')\
        .eq('is_active', True)\
        .execute()
    
    # Total de scrapers success
    scrapers_success = supabase.table('auctioneers')\
        .select('id', count='exact')\
        .eq('scrape_status', 'success')\
        .gt('property_count', 0)\
        .execute()
    
    print(f"   Total imoveis ativos: {total.count}")
    print(f"   Scrapers funcionando: {scrapers_success.count}")
    
    return {
        'total_imoveis': total.count,
        'scrapers_success': scrapers_success.count,
        'data': datetime.now().isoformat()
    }

async def enviar_relatorio():
    """Envia relatorio diario"""
    print("5. Gerando relatorio diario...")
    print("   (Implementar: envio por email ou webhook)")
    return True

async def main():
    """Execucao principal"""
    print("\n" + "="*60)
    print("MANUTENCAO DIARIA LEILOHUB")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    try:
        await limpar_imoveis_expirados()
        await re_executar_scrapers_ativos()
        await verificar_scrapers_falhados()
        metricas = await atualizar_metricas()
        await enviar_relatorio()
        
        print("\n" + "="*60)
        print("MANUTENCAO CONCLUIDA")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    asyncio.run(main())
