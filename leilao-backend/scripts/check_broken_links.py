import os
import httpx
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

async def check_url(client: httpx.AsyncClient, url: str) -> tuple[str, bool, str]:
    """Verifica se uma URL está acessível."""
    try:
        response = await client.head(url, timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            return url, True, "OK"
        elif response.status_code == 404:
            return url, False, "404 - Não encontrado"
        else:
            return url, False, f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        return url, False, "Timeout"
    except Exception as e:
        return url, False, str(e)[:50]

async def main():
    print("=" * 70)
    print("VERIFICAÇÃO DE LINKS QUEBRADOS")
    print("=" * 70)
    
    # Buscar amostra de URLs para verificar (limitado para não sobrecarregar)
    # Focar em imóveis da Caixa que são os mais propensos a expirar
    try:
        response = supabase.table("properties") \
            .select("id, source_url, title") \
            .eq("auctioneer_id", "caixa") \
            .eq("is_active", True) \
            .limit(100) \
            .execute()
    except Exception as e:
        # Se auctioneer_id não existir, tentar por auctioneer_name
        print(f"Tentando buscar por auctioneer_name...")
        response = supabase.table("properties") \
            .select("id, source_url, title, auctioneer_name") \
            .ilike("auctioneer_name", "%caixa%") \
            .eq("is_active", True) \
            .limit(100) \
            .execute()
    
    if not response.data:
        print("Nenhum imóvel encontrado para verificar.")
        return 0
    
    print(f"\nVerificando {len(response.data)} URLs da Caixa...")
    
    links_quebrados = []
    links_ok = 0
    
    async with httpx.AsyncClient() as client:
        # Verificar em lotes de 10
        for i in range(0, len(response.data), 10):
            batch = response.data[i:i+10]
            tasks = [check_url(client, p["source_url"]) for p in batch if p.get("source_url")]
            results = await asyncio.gather(*tasks)
            
            for url, is_ok, status in results:
                if is_ok:
                    links_ok += 1
                else:
                    # Encontrar o imóvel correspondente
                    prop = next((p for p in batch if p.get("source_url") == url), None)
                    if prop:
                        links_quebrados.append({
                            "id": prop["id"],
                            "url": url,
                            "title": prop.get("title", "")[:50],
                            "status": status
                        })
            
            print(f"  Processados: {min(i+10, len(response.data))}/{len(response.data)}")
            await asyncio.sleep(0.5)  # Rate limiting
    
    print(f"\nRESULTADO:")
    print("-" * 50)
    print(f"Links OK:       {links_ok}")
    print(f"Links quebrados: {len(links_quebrados)}")
    
    if links_quebrados:
        print(f"\nLINKS QUEBRADOS ENCONTRADOS:")
        for link in links_quebrados[:10]:
            print(f"  - {link['title']}")
            print(f"    Status: {link['status']}")
            print(f"    URL: {link['url'][:70]}...")
        
        # Desativar imóveis com links quebrados
        print(f"\nDesativando {len(links_quebrados)} imoveis com links quebrados...")
        for link in links_quebrados:
            supabase.table("properties") \
                .update({
                    "is_active": False, 
                    "deactivated_at": datetime.now().isoformat()
                }) \
                .eq("id", link["id"]) \
                .execute()
        print(f"[OK] {len(links_quebrados)} imoveis desativados")
    
    print("\n" + "=" * 70)
    print("VERIFICAÇÃO CONCLUÍDA")
    print("=" * 70)
    
    return len(links_quebrados)

if __name__ == "__main__":
    asyncio.run(main())

