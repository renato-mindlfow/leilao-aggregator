"""
Encontra e corrige todas as ocorrências de .replace() sem verificação de None
"""
import os
import re
import sys

def encontrar_arquivos_python(diretorio):
    """Encontra todos os arquivos .py"""
    arquivos = []
    for root, dirs, files in os.walk(diretorio):
        # Ignorar __pycache__ e .git
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', '.venv', 'node_modules']]
        for file in files:
            if file.endswith('.py'):
                arquivos.append(os.path.join(root, file))
    return arquivos

def analisar_arquivo(filepath):
    """Analisa arquivo em busca de .replace() problemáticos"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.split('\n')
    
    problemas = []
    
    # Padrões problemáticos
    patterns = [
        (r'(\w+)\.replace\(', 'replace'),
        (r'(\w+)\.lower\(\)', 'lower'),
        (r'(\w+)\.upper\(\)', 'upper'),
        (r'(\w+)\.strip\(\)', 'strip'),
        (r'(\w+)\.split\(', 'split'),
        (r'(\w+)\.title\(\)', 'title'),
    ]
    
    for i, line in enumerate(lines, 1):
        for pattern, method_name in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                variavel = match.group(1)
                
                # Verificar se há check de None nas linhas anteriores (contexto de 10 linhas)
                context_start = max(0, i - 10)
                context = '\n'.join(lines[context_start:i])
                
                # Verificar se já tem proteção
                has_protection = any([
                    f'if {variavel}' in context,
                    f'if not {variavel}' in context,
                    f'{variavel} is None' in context,
                    f'{variavel} is not None' in context,
                    f'isinstance({variavel}' in context,
                    f'{variavel} or' in context,
                    f'{variavel} and' in context,
                    f'if {variavel}:' in context,
                    f'if not {variavel}:' in context,
                ])
                
                # Verificar se a variável pode ser None baseado no contexto
                # Ignorar se for uma string literal ou número
                if variavel.startswith('"') or variavel.startswith("'") or variavel.isdigit():
                    continue
                
                if not has_protection:
                    problemas.append({
                        'linha': i,
                        'variavel': variavel,
                        'codigo': line.strip(),
                        'method': method_name
                    })
    
    return problemas

def main():
    print("="*60)
    print("ANÁLISE DE .replace() SEM VERIFICAÇÃO DE None")
    print("="*60)
    
    # Buscar no diretório app
    app_dir = os.path.join(os.path.dirname(__file__), '..', 'app')
    arquivos = encontrar_arquivos_python(app_dir)
    
    total_problemas = 0
    problemas_por_arquivo = {}
    
    for arquivo in arquivos:
        rel_path = os.path.relpath(arquivo, app_dir)
        problemas = analisar_arquivo(arquivo)
        
        if problemas:
            problemas_por_arquivo[rel_path] = problemas
            total_problemas += len(problemas)
    
    # Exibir resultados
    if problemas_por_arquivo:
        print(f"\n📁 Arquivos com potenciais problemas:\n")
        for arquivo, problemas in sorted(problemas_por_arquivo.items()):
            print(f"  {arquivo} ({len(problemas)} ocorrências)")
            for p in problemas[:3]:  # Mostrar apenas os 3 primeiros
                print(f"    Linha {p['linha']}: {p['variavel']}.{p['method']}()")
                print(f"      {p['codigo'][:80]}")
            if len(problemas) > 3:
                print(f"    ... e mais {len(problemas) - 3} ocorrências")
            print()
    
    print(f"{'='*60}")
    print(f"Total de potenciais problemas: {total_problemas}")
    print("="*60)
    
    if total_problemas > 0:
        print("\n💡 RECOMENDAÇÃO: Revisar cada ocorrência e adicionar verificação:")
        print("   if not var or not isinstance(var, str):")
        print("       return None ou var = ''")
        print("\n   Ou usar:")
        print("   var = (var or '').replace(...)")
    else:
        print("\n✅ Nenhum problema encontrado!")

if __name__ == "__main__":
    main()

