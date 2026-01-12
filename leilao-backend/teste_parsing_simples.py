"""Teste simples do parsing - corrigido"""
import sys
import csv
import io
sys.path.insert(0, '.')

from scripts.sync_caixa import parse_csv_row

# Ler CSV
with open('teste_sp.csv', 'r', encoding='latin-1') as f:
    content = f.read()

# Processar: encontrar cabeçalho (linha 3) e dados
lines = content.split('\n')
header_line = None
data_lines = []

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        continue
    
    # Cabeçalho está na linha 3: " Nº do imóvel;UF;Cidade;..."
    if i == 2:  # Linha 3 (índice 2)
        header_line = stripped
        data_lines.append(stripped)
        print(f"Cabeçalho encontrado: {stripped[:100]}")
        continue
    
    # Pular título
    if 'Lista de Im' in stripped or 'Data de ger' in stripped:
        continue
    
    # Adicionar dados após cabeçalho
    if header_line and stripped:
        data_lines.append(stripped)

# Parsear
csv_content = '\n'.join(data_lines)
reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')

print(f"\nCabeçalhos: {list(reader.fieldnames)}")
print(f"\nTestando parsing...\n")

count = 0
for row in reader:
    parsed = parse_csv_row(row)
    if parsed:
        count += 1
        if count <= 3:
            print(f"Exemplo {count}:")
            print(f"  ID: {parsed.get('id')}")
            print(f"  Cidade: {parsed.get('city')}, {parsed.get('state')}")
            print(f"  Endereco: {parsed.get('address', 'N/A')[:60]}")
            preco = parsed.get('first_auction_value')
            if preco:
                print(f"  Preco: R$ {preco:,.2f}")
            print(f"  Categoria: {parsed.get('category')}")
            print()

print(f"Total parseado: {count} imoveis")

