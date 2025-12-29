#!/usr/bin/env python3
"""
Script de validação completa do sistema LeiloHub.
Executa todas as verificações da FASE 1 e FASE 2.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Adiciona diretório raiz ao path
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

def check_phase1():
    """FASE 1: Diagnóstico Completo"""
    print_header("FASE 1: DIAGNOSTICO COMPLETO")
    
    # 1.1 Verificar estrutura de arquivos
    print("\n1.1 Verificando estrutura de arquivos...")
    
    required_files = [
        "app/api/properties.py",
        "app/api/sync.py",
        "app/api/geocoding.py",
        "app/services/async_geocoding_service.py",
        "app/services/sync_service.py",
        "app/scrapers/caixa_scraper.py",
        "app/scrapers/generic_scraper.py",
        "app/utils/fetcher.py",
        "app/utils/image_extractor.py",
        "app/utils/image_blacklist.py",
        "app/utils/paginator.py",
        "scripts/run_geocoding.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            print_success(f"{file_path} existe")
        else:
            print_error(f"{file_path} NAO ENCONTRADO")
            missing_files.append(file_path)
    
    if missing_files:
        print_warning(f"Total de arquivos faltando: {len(missing_files)}")
        return False
    
    # 1.2 Verificar variáveis de ambiente
    print("\n1.2 Verificando variaveis de ambiente...")
    
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "DATABASE_URL"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mascara valores sensíveis
            if "KEY" in var or "PASS" in var:
                masked = value[:10] + "..." if len(value) > 10 else "***"
                print_success(f"{var}={masked}")
            else:
                print_success(f"{var}={value}")
        else:
            print_error(f"{var} nao configurado")
            missing_vars.append(var)
    
    if missing_vars:
        print_warning(f"Total de variaveis faltando: {len(missing_vars)}")
        return False
    
    # 1.3 Verificar conexão com banco de dados
    print("\n1.3 Verificando conexao com banco de dados...")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print_error("SUPABASE_URL ou SUPABASE_KEY nao configurados")
            return False
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Contar imóveis
        result = supabase.table("properties").select("id", count="exact").execute()
        total = result.count or 0
        
        print_success(f"Conexao com banco OK")
        print_success(f"Total de imoveis no banco: {total}")
        
        if total < 1000:
            print_warning(f"Poucos imoveis no banco ({total}). Esperado: 29.000+")
        
        # Verificar status de geocoding
        geocoding_result = supabase.table("properties").select("geocoding_status").execute()
        geocoding_stats = {}
        for row in geocoding_result.data or []:
            status = row.get("geocoding_status", "unknown")
            geocoding_stats[status] = geocoding_stats.get(status, 0) + 1
        
        print("\nStatus de geocoding:")
        for status, count in sorted(geocoding_stats.items()):
            print(f"  {status}: {count}")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao conectar com banco: {e}")
        return False

def check_phase2():
    """FASE 2: Verificação da API"""
    print_header("FASE 2: VERIFICACAO DA API")
    
    # 2.1 Verificar registro de routers no main.py
    print("\n2.1 Verificando registro de routers...")
    
    try:
        main_path = Path(__file__).parent / "app" / "main.py"
        main_content = main_path.read_text(encoding="utf-8")
        
        required_routers = [
            "properties_router",
            "sync_router",
            "geocoding_router"
        ]
        
        for router in required_routers:
            if f"include_router({router})" in main_content or f"include_router({router.replace('_router', '_router')})" in main_content:
                print_success(f"Router {router} registrado")
            else:
                print_error(f"Router {router} NAO registrado")
                return False
        
        # Verificar health endpoint
        if "@app.get(\"/health\")" in main_content or "@app.get('/health')" in main_content:
            print_success("Endpoint /health existe")
        else:
            print_warning("Endpoint /health nao encontrado")
        
        # Verificar CORS
        if "CORSMiddleware" in main_content:
            print_success("CORS configurado")
        else:
            print_warning("CORS nao configurado")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao verificar API: {e}")
        return False

def main():
    """Executa todas as validações"""
    print_header("VALIDACAO COMPLETA DO SISTEMA LEILOHUB")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    phase1_ok = check_phase1()
    phase2_ok = check_phase2()
    
    print_header("RESUMO")
    
    if phase1_ok:
        print_success("FASE 1: Diagnostico completo - OK")
    else:
        print_error("FASE 1: Diagnostico completo - FALHOU")
    
    if phase2_ok:
        print_success("FASE 2: Verificacao da API - OK")
    else:
        print_error("FASE 2: Verificacao da API - FALHOU")
    
    if phase1_ok and phase2_ok:
        print("\n" + "=" * 60)
        print("VALIDACAO BASICA CONCLUIDA COM SUCESSO!")
        print("=" * 60)
        print("\nProximos passos:")
        print("1. Testar API localmente: uvicorn app.main:app --reload --port 8000")
        print("2. Testar scrapers (FASE 3)")
        print("3. Testar sincronizacao (FASE 4)")
        return 0
    else:
        print("\n" + "=" * 60)
        print("VALIDACAO FALHOU - CORRIJA OS ERROS ANTES DE CONTINUAR")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())

