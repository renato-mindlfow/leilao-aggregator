"""Teste do parsing do CSV da Caixa"""
import sys
import csv
import io
sys.path.insert(0, '.')

from scripts.sync_caixa import parse_csv_row

# Ler o CSV baixado manualmente
with open('teste_sp.csv', 'r', encoding='latin-1') as f:
    lines = f.readlines()

# Filtrar linhas válidas
data_lines = []
header_found = False
for line in lines:
    line = line.strip()
    if not line:
        continue
    if 'Nº do imóvel' in line or 'N do imvel' in line:
        data_lines.append(line)
        header_found = True
        continue
    if 'Lista de Imóveis' in line or 'Lista de Imveis' in line:
        continue
    if header_found and line:
        data_lines.append(line)

csv_content = '\n'.join(data_lines)
reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')

print("=" * 80)
print("TESTE DE PARSING DO CSV DA CAIXA")
print("=" * 80)
if reader.fieldnames:
    print(f"\nCabecalhos: {list(reader.fieldnames)}")
else:
    print("\nAVISO: Nao foi possivel detectar cabecalhos, tentando continuar...")

count = 0
errors = 0
for row in reader:
    parsed = parse_csv_row(row)
    if parsed:
        count += 1
        if count <= 5:
            print(f"\nExemplo {count}:")
            print(f"   ID: {parsed.get('id')}")
            print(f"   Cidade: {parsed.get('city')}, {parsed.get('state')}")
            addr = parsed.get('address', 'N/A')
            print(f"   Endereco: {addr[:60] if addr else 'N/A'}")
            preco = parsed.get('first_auction_value')
            if preco:
                print(f"   Preco: R$ {preco:,.2f}")
            else:
                print(f"   Preco: N/A")
            print(f"   Categoria: {parsed.get('category')}")
    else:
        errors += 1
        if errors <= 3:
            print(f"\nLinha ignorada: {dict(list(row.items())[:3])}")

print(f"\n{'=' * 80}")
print(f"Total de imoveis validos parseados: {count:,}")
print(f"Linhas ignoradas: {errors}")
print(f"{'=' * 80}")

