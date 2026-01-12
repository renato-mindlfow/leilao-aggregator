"""Script temporário para analisar o formato do CSV da Caixa"""
import csv

with open('teste_sp.csv', 'r', encoding='latin-1', errors='ignore') as f:
    lines = f.readlines()
    
print("=" * 80)
print("ANÁLISE DO CSV DA CAIXA")
print("=" * 80)
print(f"\nTotal de linhas no arquivo: {len(lines):,}")
print("\nPrimeiras 5 linhas:")
for i, line in enumerate(lines[:5], 1):
    print(f"\nLinha {i}:")
    print(repr(line[:200]))
    
print("\n" + "=" * 80)
print("Tentando parsear como CSV com delimitador ';':")
print("=" * 80)

# Pular as primeiras 2 linhas (cabeçalho especial)
f = open('teste_sp.csv', 'r', encoding='latin-1', errors='ignore')
for _ in range(2):
    next(f, None)

reader = csv.DictReader(f, delimiter=';')
headers = reader.fieldnames
print(f"\nCabeçalhos encontrados: {headers}")

count = 0
for row in reader:
    count += 1
    if count <= 3:
        print(f"\n--- Linha {count} ---")
        for k, v in row.items():
            if k and v:
                print(f"  {k}: {v[:80] if len(str(v)) > 80 else v}")

print(f"\n{'=' * 80}")
print(f"Total de imóveis encontrados: {count:,}")
print(f"{'=' * 80}")

f.close()

