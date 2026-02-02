"""
Limpa imagens invalidas (logos, placeholders) do banco de dados.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Importar blacklist
from app.utils.image_blacklist import is_valid_image_url, ImageBlacklist

def main():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    )

    print("=" * 60)
    print("LIMPEZA DE IMAGENS INVALIDAS")
    print("=" * 60)

    # Buscar imoveis com imagem
    print("\nBuscando imoveis com imagens...")

    # Buscar em lotes de 1000
    all_properties = []
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table("properties") \
            .select("id, image_url") \
            .not_.is_("image_url", "null") \
            .neq("image_url", "") \
            .range(offset, offset + batch_size - 1) \
            .execute()

        if not result.data:
            break

        all_properties.extend(result.data)
        offset += batch_size
        print(f"  Carregados: {len(all_properties)}")

        if len(result.data) < batch_size:
            break

    total = len(all_properties)
    print(f"Total com imagens: {total}")

    # Criar instancia do blacklist
    blacklist = ImageBlacklist()

    # Filtrar invalidas
    invalidas = []
    exemplos_invalidos = []

    for prop in all_properties:
        url = prop.get('image_url', '')
        if url and blacklist.is_blocked(url):
            invalidas.append(prop['id'])
            if len(exemplos_invalidos) < 10:
                exemplos_invalidos.append(url[:100])

    print(f"Imagens invalidas encontradas: {len(invalidas)}")

    if exemplos_invalidos:
        print("\nExemplos de imagens invalidas:")
        for ex in exemplos_invalidos:
            print(f"  - {ex}")

    if not invalidas:
        print("\nNenhuma imagem invalida encontrada!")
        return

    # Limpeza
    print(f"\nLimpando {len(invalidas)} imagens invalidas...")

    # Atualizar em lotes de 100
    batch_size = 100
    cleaned = 0
    errors = 0

    for i in range(0, len(invalidas), batch_size):
        batch = invalidas[i:i+batch_size]

        for prop_id in batch:
            try:
                supabase.table("properties") \
                    .update({"image_url": None}) \
                    .eq("id", prop_id) \
                    .execute()
                cleaned += 1
            except Exception as e:
                print(f"Erro ao limpar {prop_id}: {e}")
                errors += 1

        print(f"  Progresso: {cleaned}/{len(invalidas)} (erros: {errors})")

    print(f"\nLimpeza concluida! {cleaned} imagens removidas, {errors} erros.")

if __name__ == "__main__":
    main()
