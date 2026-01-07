import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def main():
    print("=" * 70)
    print("LIMPEZA DE IMOVEIS COM DADOS CRITICOS FALTANDO")
    print("=" * 70)
    
    # Critérios para DESATIVAR (não deletar) um imóvel:
    # 1. Sem cidade E sem estado
    # 2. Sem nenhum valor (avaliação, 1º leilão, 2º leilão)
    # 3. Sem URL de origem
    
    total_desativados = 0
    
    # 1. Desativar imóveis sem cidade E sem estado
    print("\n1. Desativando imoveis sem cidade E sem estado...")
    
    # Buscar IDs primeiro - precisamos verificar ambos os campos
    r1 = supabase.table("properties") \
        .select("id") \
        .or_("city.is.null,city.eq.") \
        .or_("state.is.null,state.eq.") \
        .eq("is_active", True) \
        .limit(1000) \
        .execute()
    
    if r1.data:
        ids = [p["id"] for p in r1.data]
        # Filtrar apenas os que não têm cidade E não têm estado
        filtered_ids = []
        for prop_id in ids:
            prop = supabase.table("properties").select("city, state").eq("id", prop_id).execute()
            if prop.data:
                p = prop.data[0]
                if (not p.get("city") or p.get("city") == "") and (not p.get("state") or p.get("state") == ""):
                    filtered_ids.append(prop_id)
        
        if filtered_ids:
            for id in filtered_ids:
                supabase.table("properties") \
                    .update({"is_active": False, "deactivated_at": datetime.now().isoformat()}) \
                    .eq("id", id) \
                    .execute()
            print(f"   [OK] {len(filtered_ids)} imoveis desativados")
            total_desativados += len(filtered_ids)
        else:
            print("   [OK] Nenhum imovel encontrado nesta categoria")
    else:
        print("   [OK] Nenhum imovel encontrado nesta categoria")
    
    # 2. Desativar imóveis sem nenhum valor
    print("\n2. Desativando imoveis sem nenhum valor monetario...")
    
    r2 = supabase.table("properties") \
        .select("id") \
        .is_("evaluation_value", "null") \
        .is_("first_auction_value", "null") \
        .is_("second_auction_value", "null") \
        .eq("is_active", True) \
        .limit(1000) \
        .execute()
    
    if r2.data:
        ids = [p["id"] for p in r2.data]
        # Verificar se realmente não têm nenhum valor
        filtered_ids = []
        for prop_id in ids:
            prop = supabase.table("properties").select("evaluation_value, first_auction_value, second_auction_value").eq("id", prop_id).execute()
            if prop.data:
                p = prop.data[0]
                if (not p.get("evaluation_value") and not p.get("first_auction_value") and not p.get("second_auction_value")):
                    filtered_ids.append(prop_id)
        
        if filtered_ids:
            for id in filtered_ids:
                supabase.table("properties") \
                    .update({"is_active": False, "deactivated_at": datetime.now().isoformat()}) \
                    .eq("id", id) \
                    .execute()
            print(f"   [OK] {len(filtered_ids)} imoveis desativados")
            total_desativados += len(filtered_ids)
        else:
            print("   [OK] Nenhum imovel encontrado nesta categoria")
    else:
        print("   [OK] Nenhum imovel encontrado nesta categoria")
    
    # 3. Desativar imóveis sem URL de origem
    print("\n3. Desativando imoveis sem URL de origem...")
    
    r3 = supabase.table("properties") \
        .select("id") \
        .or_("source_url.is.null,source_url.eq.") \
        .eq("is_active", True) \
        .limit(1000) \
        .execute()
    
    if r3.data:
        ids = [p["id"] for p in r3.data]
        for id in ids:
            supabase.table("properties") \
                .update({"is_active": False, "deactivated_at": datetime.now().isoformat()}) \
                .eq("id", id) \
                .execute()
        print(f"   [OK] {len(ids)} imoveis desativados")
        total_desativados += len(ids)
    else:
        print("   [OK] Nenhum imovel encontrado nesta categoria")
    
    print("\n" + "=" * 70)
    print(f"LIMPEZA CONCLUIDA: {total_desativados} imoveis desativados")
    print("=" * 70)
    print("\nNota: Os imoveis foram DESATIVADOS (is_active=false), nao deletados.")
    print("Isso permite recupera-los se necessario.")
    
    return total_desativados

if __name__ == "__main__":
    main()

