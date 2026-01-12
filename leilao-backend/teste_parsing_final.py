"""Teste completo do parsing do CSV da Caixa com o arquivo teste_sp.csv"""
import sys
import csv
import io
sys.path.insert(0, '.')

from scripts.sync_caixa import parse_csv_row

print("=" * 80)
print("TESTE DE PARSING DO CSV DA CAIXA - teste_sp.csv")
print("=" * 80)

# Ler o CSV baixado manualmente
with open('teste_sp.csv', 'r', encoding='latin-1') as f:
    content = f.read()

print(f"\nTamanho do arquivo: {len(content):,} caracteres")
print(f"Primeiras 300 caracteres:")
print(repr(content[:300]))

# Processar CSV: encontrar cabeçalho real e dados
lines = content.split('\n')
header_line = None
data_lines = []

for i, line in enumerate(lines):
    line_stripped = line.strip()
    if not line_stripped:
        continue
    
    # Detectar linha de cabeçalho de dados (linha 3 do arquivo)
    # O cabeçalho tem espaços no início, então vamos procurar pelo padrão
    line_upper = line_stripped.upper()
    if ('Nº DO IMÓVEL' in line_upper or 'N DO IMVEL' in line_upper or 'NUMERO' in line_upper) and 'UF' in line_upper and 'CIDADE' in line_upper:
        header_line = line_stripped  # Cabeçalho real (sem espaços iniciais)
        print(f"\nCabeçalho encontrado na linha {i+1}:")
        print(repr(line_stripped))
        # Adicionar cabeçalho
        data_lines.append(line_stripped)
        continue
    
    # Pular linha de título
    if 'Lista de Imóveis' in line_stripped or 'Lista de Imveis' in line_stripped or 'Data de geração' in line_stripped or 'Data de geracao' in line_stripped:
        continue
    
    # Adicionar linhas de dados (após o cabeçalho)
    if header_line and line_stripped:
        data_lines.append(line_stripped)

print(f"\nTotal de linhas processadas: {len(data_lines)} (1 cabeçalho + {len(data_lines)-1} dados)")

print(f"\nTotal de linhas de dados: {len(data_lines)-1}")  # -1 porque uma é o cabeçalho

# Parsear com csv.DictReader
csv_content_clean = '\n'.join(data_lines)
reader = csv.DictReader(io.StringIO(csv_content_clean), delimiter=';')

print(f"\nCabeçalhos detectados pelo csv.DictReader:")
if reader.fieldnames:
    for i, header in enumerate(reader.fieldnames, 1):
        print(f"  {i}. {repr(header)}")
else:
    print("  NENHUM CABEÇALHO DETECTADO!")

# Testar parsing
print(f"\n{'=' * 80}")
print("TESTANDO PARSING DE IMÓVEIS")
print(f"{'=' * 80}")

count = 0
errors = 0
for row_num, row in enumerate(reader, 1):
    # Mostrar primeira linha raw
    if row_num == 1:
        print(f"\nPrimeira linha RAW (primeiros 3 campos):")
        items = list(row.items())[:3]
        for k, v in items:
            print(f"  {repr(k)}: {repr(v[:50] if v else '')}")
    
    parsed = parse_csv_row(row)
    if parsed:
        count += 1
        if count <= 3:
            print(f"\nOK - Exemplo {count} (linha {row_num}):")
            print(f"   ID: {parsed.get('id')}")
            print(f"   Cidade: {parsed.get('city')}, {parsed.get('state')}")
            addr = parsed.get('address', 'N/A')
            print(f"   Endereco: {addr[:70] if addr else 'N/A'}")
            preco = parsed.get('first_auction_value')
            if preco:
                print(f"   Preco: R$ {preco:,.2f}")
            else:
                print(f"   Preco: N/A")
            valor_aval = parsed.get('evaluation_value')
            if valor_aval:
                print(f"   Valor Avaliacao: R$ {valor_aval:,.2f}")
            desconto = parsed.get('discount_percentage')
            if desconto:
                print(f"   Desconto: {desconto}%")
            print(f"   Categoria: {parsed.get('category')}")
            print(f"   Link: {parsed.get('source_url', 'N/A')[:80]}")
    else:
        errors += 1
        if errors <= 3:
            print(f"\nERRO - Linha {row_num} ignorada:")
            print(f"   UF: {row.get('UF', 'N/A')}")
            print(f"   Cidade: {row.get('Cidade', 'N/A')}")
            print(f"   Primeiros campos: {dict(list(row.items())[:3])}")

print(f"\n{'=' * 80}")
print(f"RESULTADO FINAL:")
print(f"  OK - Imoveis validos parseados: {count:,}")
print(f"  ERRO - Linhas ignoradas: {errors}")
print(f"{'=' * 80}")

