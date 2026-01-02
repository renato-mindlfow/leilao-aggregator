#!/usr/bin/env python3
"""
FASE 4: Sincronização de Dados
Testa serviço de sincronização e salvamento
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def print_success(text):
    print(f"[OK] {text}")

def print_error(text):
    print(f"[ERRO] {text}")

def print_warning(text):
    print(f"[AVISO] {text}")

async def test_sync_service_structure():
    """Verifica estrutura do serviço de sincronização"""
    print_header("4.1 Verificando Servico de Sincronizacao")
    
    try:
        # Valida apenas a estrutura do arquivo
        sync_path = Path(__file__).parent / "app" / "services" / "sync_service.py"
        
        if not sync_path.exists():
            print_error("Arquivo sync_service.py nao encontrado")
            return False
        
        print_success("Arquivo sync_service.py existe")
        
        # Lê o arquivo e verifica classes/funções
        content = sync_path.read_text(encoding="utf-8")
        
        if "class SyncService" in content:
            print_success("Classe SyncService definida")
        else:
            print_error("Classe SyncService nao encontrada")
            return False
        
        if "def get_sync_service" in content:
            print_success("Funcao get_sync_service definida")
        else:
            print_error("Funcao get_sync_service nao encontrada")
            return False
        
        if "async def sync_all" in content:
            print_success("Metodo sync_all existe")
        else:
            print_warning("Metodo sync_all nao encontrado")
        
        if "async def sync_caixa_only" in content:
            print_success("Metodo sync_caixa_only existe")
        else:
            print_warning("Metodo sync_caixa_only nao encontrado")
        
        print_success("Estrutura do servico de sincronizacao validada")
        return True
            
    except Exception as e:
        print_error(f"Erro na validacao: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_save_property():
    """Testa salvamento de propriedade no banco"""
    print_header("4.2 Testando Salvamento no Banco")
    
    try:
        from supabase import create_client
        import time
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print_error("SUPABASE_URL ou SUPABASE_KEY nao configurados")
            return False
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Cria propriedade de teste
        test_id = f"TEST_{int(time.time())}"
        test_prop = {
            'id': test_id,
            'title': 'IMOVEL DE TESTE - PODE DELETAR',
            'category': 'Casa',
            'state': 'SP',
            'city': 'Sao Paulo',
            'first_auction_value': 100000,
            'source_url': 'https://teste.com/imovel',
            'auctioneer_name': 'Teste',
            'auctioneer_id': 'test',
            'is_active': True,
        }
        
        print(f"Salvando imovel de teste (ID: {test_id})...")
        
        # Salva usando upsert
        result = supabase.table("properties").upsert(
            test_prop,
            on_conflict="id"
        ).execute()
        
        if result.data:
            print_success("Imovel salvo com sucesso!")
            print(f"   ID: {test_id}")
            
            # Verifica se foi salvo
            check = supabase.table("properties").select("*").eq("id", test_id).execute()
            if check.data:
                print_success("Imovel encontrado no banco")
                
                # Limpa o teste
                supabase.table("properties").delete().eq("id", test_id).execute()
                print_success("Imovel de teste removido")
                return True
            else:
                print_error("Imovel nao encontrado apos salvamento")
                return False
        else:
            print_error("Falha ao salvar imovel")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sync_stats():
    """Testa estatísticas do banco"""
    print_header("4.3 Verificando Estatisticas do Banco")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print_error("SUPABASE_URL ou SUPABASE_KEY nao configurados")
            return False
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Total de imóveis
        total_result = supabase.table("properties").select("id", count="exact").execute()
        total = total_result.count or 0
        
        print(f"Total de imoveis no banco: {total}")
        
        if total > 0:
            print_success(f"Banco contem {total} imoveis")
        else:
            print_error("Banco esta vazio")
            return False
        
        # Por fonte
        sources_result = supabase.table("properties").select("auctioneer_name").execute()
        sources = {}
        for row in sources_result.data or []:
            source = row.get("auctioneer_name", "Desconhecido")
            sources[source] = sources.get(source, 0) + 1
        
        print("\nPor fonte/leiloeiro (top 5):")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {source}: {count}")
        
        # Por estado
        states_result = supabase.table("properties").select("state").execute()
        states = {}
        for row in states_result.data or []:
            state = row.get("state", "XX")
            if state and len(state) == 2:
                states[state] = states.get(state, 0) + 1
        
        print("\nPor estado (top 5):")
        for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {state}: {count}")
        
        return True
        
    except Exception as e:
        print_error(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print_header("FASE 4: SINCRONIZACAO DE DADOS")
    
    test1 = await test_sync_service_structure()
    test2 = await test_save_property()
    test3 = await test_sync_stats()
    
    print_header("RESUMO FASE 4")
    
    if test1:
        print_success("Teste 4.1: Servico de sincronizacao - OK")
    else:
        print_error("Teste 4.1: Servico de sincronizacao - FALHOU")
    
    if test2:
        print_success("Teste 4.2: Salvamento no banco - OK")
    else:
        print_error("Teste 4.2: Salvamento no banco - FALHOU")
    
    if test3:
        print_success("Teste 4.3: Estatisticas do banco - OK")
    else:
        print_error("Teste 4.3: Estatisticas do banco - FALHOU")
    
    if test1 and test2 and test3:
        print("\n" + "=" * 60)
        print("FASE 4 CONCLUIDA COM SUCESSO!")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("FASE 4 COM FALHAS - REVISAR TESTES")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

