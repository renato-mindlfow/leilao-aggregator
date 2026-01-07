import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def main():
    print("=" * 70)
    print("AUDITORIA DE QUALIDADE DA BASE DE DADOS")
    print("=" * 70)
    
    # 1. Imóveis sem cidade
    r1 = supabase.table("properties").select("id", count="exact") \
        .or_("city.is.null,city.eq.") \
        .execute()
    sem_cidade = r1.count or 0
    
    # 2. Imóveis sem estado
    r2 = supabase.table("properties").select("id", count="exact") \
        .or_("state.is.null,state.eq.") \
        .execute()
    sem_estado = r2.count or 0
    
    # 3. Imóveis categoria "Outro" (pode indicar dados ruins)
    r3 = supabase.table("properties").select("id", count="exact") \
        .eq("category", "Outro") \
        .execute()
    categoria_outro = r3.count or 0
    
    # 4. Imóveis sem nenhum valor (avaliação, 1º leilão, 2º leilão)
    r4 = supabase.table("properties").select("id", count="exact") \
        .is_("evaluation_value", "null") \
        .is_("first_auction_value", "null") \
        .is_("second_auction_value", "null") \
        .execute()
    sem_valores = r4.count or 0
    
    # 5. Imóveis sem source_url
    r5 = supabase.table("properties").select("id", count="exact") \
        .or_("source_url.is.null,source_url.eq.") \
        .execute()
    sem_url = r5.count or 0
    
    # 6. Total de imóveis
    r_total = supabase.table("properties").select("id", count="exact").execute()
    total = r_total.count or 0
    
    # 7. Imóveis com dados mínimos OK
    imoveis_ok = total - max(sem_cidade, sem_estado, sem_valores)
    
    print(f"\nRESUMO DA AUDITORIA:")
    print("-" * 50)
    print(f"Total de imóveis:              {total:,}")
    print(f"Sem cidade:                    {sem_cidade:,} ({sem_cidade*100/total:.1f}%)" if total > 0 else f"Sem cidade:                    {sem_cidade:,}")
    print(f"Sem estado:                    {sem_estado:,} ({sem_estado*100/total:.1f}%)" if total > 0 else f"Sem estado:                    {sem_estado:,}")
    print(f"Categoria 'Outro':             {categoria_outro:,} ({categoria_outro*100/total:.1f}%)" if total > 0 else f"Categoria 'Outro':             {categoria_outro:,}")
    print(f"Sem nenhum valor:              {sem_valores:,} ({sem_valores*100/total:.1f}%)" if total > 0 else f"Sem nenhum valor:              {sem_valores:,}")
    print(f"Sem URL de origem:             {sem_url:,} ({sem_url*100/total:.1f}%)" if total > 0 else f"Sem URL de origem:             {sem_url:,}")
    print("-" * 50)
    
    # 8. Buscar amostra dos piores casos
    print(f"\nAMOSTRA DE IMÓVEIS PROBLEMATICOS:")
    print("-" * 50)
    
    sample = supabase.table("properties") \
        .select("id, title, city, state, category, evaluation_value, source_url, auctioneer_name") \
        .or_("city.is.null,city.eq.") \
        .limit(10) \
        .execute()
    
    for prop in sample.data:
        print(f"\nID: {prop.get('id')}")
        print(f"  Título: {(prop.get('title') or 'N/A')[:50]}")
        print(f"  Cidade: {prop.get('city') or '[VAZIO]'}")
        print(f"  Estado: {prop.get('state') or '[VAZIO]'}")
        print(f"  Categoria: {prop.get('category') or '[VAZIO]'}")
        print(f"  Valor: {prop.get('evaluation_value') or '[VAZIO]'}")
        print(f"  Leiloeiro: {prop.get('auctioneer_name') or '[VAZIO]'}")
    
    # Retornar estatísticas para uso posterior
    return {
        "total": total,
        "sem_cidade": sem_cidade,
        "sem_estado": sem_estado,
        "categoria_outro": categoria_outro,
        "sem_valores": sem_valores,
        "sem_url": sem_url
    }

if __name__ == "__main__":
    stats = main()
    print("\n" + "=" * 70)
    print("AUDITORIA CONCLUÍDA")
    print("=" * 70)
