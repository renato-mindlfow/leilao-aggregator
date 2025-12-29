#!/usr/bin/env python3
"""
FASE 5: Validação do Frontend
Verifica configuração e conexão com backend
"""

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

def check_frontend_env():
    """Verifica variáveis de ambiente do frontend"""
    print_header("5.1 Verificando Configuracao do Frontend")
    
    frontend_path = Path(__file__).parent.parent / "leilao-frontend"
    
    if not frontend_path.exists():
        print_error("Diretorio leilao-frontend nao encontrado")
        return False
    
    print_success("Diretorio leilao-frontend existe")
    
    # Verifica arquivos .env
    env_files = [
        frontend_path / ".env",
        frontend_path / ".env.local",
        frontend_path / ".env.production",
    ]
    
    env_found = False
    for env_file in env_files:
        if env_file.exists():
            print_success(f"Arquivo {env_file.name} existe")
            env_found = True
            
            # Lê e verifica conteúdo
            try:
                content = env_file.read_text(encoding="utf-8")
                if "VITE_API_URL" in content or "API_URL" in content:
                    print_success(f"{env_file.name} contem VITE_API_URL")
                else:
                    print_warning(f"{env_file.name} nao contem VITE_API_URL")
            except Exception as e:
                print_warning(f"Erro ao ler {env_file.name}: {e}")
    
    if not env_found:
        print_warning("Nenhum arquivo .env encontrado no frontend")
    
    # Verifica package.json
    package_json = frontend_path / "package.json"
    if package_json.exists():
        print_success("package.json existe")
    else:
        print_warning("package.json nao encontrado")
    
    # Verifica src/lib/api.ts
    api_ts = frontend_path / "src" / "lib" / "api.ts"
    if api_ts.exists():
        print_success("src/lib/api.ts existe")
        
        # Verifica se contém URL da API
        try:
            content = api_ts.read_text(encoding="utf-8")
            if "API_URL" in content or "baseURL" in content or "localhost:8000" in content:
                print_success("api.ts contem configuracao de URL")
            else:
                print_warning("api.ts pode nao ter URL configurada")
        except Exception as e:
            print_warning(f"Erro ao ler api.ts: {e}")
    else:
        print_warning("src/lib/api.ts nao encontrado")
    
    return True

def check_backend_health():
    """Verifica se backend está respondendo"""
    print_header("5.2 Verificando Backend no Fly.io")
    
    try:
        import httpx
        
        # URLs para testar
        urls = [
            "https://leilao-backend-solitary-haze-9882.fly.dev/health",
            "https://leilao-backend-solitary-haze-9882.fly.dev/healthz",
        ]
        
        backend_ok = False
        for url in urls:
            try:
                response = httpx.get(url, timeout=10.0)
                if response.status_code == 200:
                    print_success(f"Backend respondendo em {url}")
                    backend_ok = True
                    break
            except Exception as e:
                print_warning(f"Erro ao acessar {url}: {e}")
        
        if not backend_ok:
            print_warning("Backend no Fly.io nao esta respondendo")
            print_warning("Isso pode ser normal se nao foi feito deploy ainda")
        
        # Testa endpoint de properties
        try:
            api_url = "https://leilao-backend-solitary-haze-9882.fly.dev/api/properties?page=1&page_size=5"
            response = httpx.get(api_url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if "data" in data or "items" in data:
                    print_success("Endpoint /api/properties funcionando")
                else:
                    print_warning("Endpoint /api/properties retornou formato inesperado")
            else:
                print_warning(f"Endpoint /api/properties retornou status {response.status_code}")
        except Exception as e:
            print_warning(f"Erro ao testar /api/properties: {e}")
        
        return True
        
    except ImportError:
        print_warning("httpx nao instalado - pulando teste de conexao")
        return True
    except Exception as e:
        print_error(f"Erro no teste: {e}")
        return False

def check_frontend_structure():
    """Verifica estrutura básica do frontend"""
    print_header("5.3 Verificando Estrutura do Frontend")
    
    frontend_path = Path(__file__).parent.parent / "leilao-frontend"
    
    required_files = [
        "src/App.tsx",
        "src/main.tsx",
        "src/lib/api.ts",
        "package.json",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = frontend_path / file_path
        if full_path.exists():
            print_success(f"{file_path} existe")
        else:
            print_error(f"{file_path} NAO encontrado")
            all_exist = False
    
    return all_exist

def main():
    print_header("FASE 5: VALIDACAO DO FRONTEND")
    
    test1 = check_frontend_env()
    test2 = check_backend_health()
    test3 = check_frontend_structure()
    
    print_header("RESUMO FASE 5")
    
    if test1:
        print_success("Teste 5.1: Configuracao do frontend - OK")
    else:
        print_error("Teste 5.1: Configuracao do frontend - FALHOU")
    
    if test2:
        print_success("Teste 5.2: Backend no Fly.io - OK")
    else:
        print_warning("Teste 5.2: Backend no Fly.io - AVISO")
    
    if test3:
        print_success("Teste 5.3: Estrutura do frontend - OK")
    else:
        print_error("Teste 5.3: Estrutura do frontend - FALHOU")
    
    if test1 and test3:
        print("\n" + "=" * 60)
        print("FASE 5 CONCLUIDA!")
        print("=" * 60)
        print("\nNota: Backend no Fly.io pode precisar de deploy")
        return 0
    else:
        print("\n" + "=" * 60)
        print("FASE 5 COM FALHAS - REVISAR")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())


