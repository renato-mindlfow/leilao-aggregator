"""
Executa geocoding em lotes de forma standalone.
Pode ser executado via cron ou manualmente.
"""
import os
import sys
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from app.services.async_geocoding_service import AsyncGeocodingService

async def main():
    print("=" * 60)
    print("GEOCODING EM LOTES")
    print("=" * 60)

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    )

    # Verificar quantos precisam de geocoding
    result = supabase.table("properties") \
        .select("id", count="exact") \
        .eq("geocoding_status", "pending") \
        .execute()

    pending = result.count or 0
    print(f"\nImoveis pendentes de geocoding: {pending}")

    if pending == 0:
        # Verificar imoveis sem coordenadas
        result2 = supabase.table("properties") \
            .select("id", count="exact") \
            .is_("latitude", "null") \
            .neq("state", "XX") \
            .execute()

        sem_coords = result2.count or 0
        if sem_coords > 0:
            print(f"Imoveis sem coordenadas (latitude NULL): {sem_coords}")
            print("\nNota: Esses imoveis podem nao ter geocoding_status='pending'.")
            print("Execute o script de normalizacao primeiro se necessario.")
        else:
            print("Todos os imoveis ja tem coordenadas!")
        return

    # Inicializar servico
    service = AsyncGeocodingService()

    print(f"\nIniciando processamento...")
    print(f"   Lotes de 50 imoveis")
    print(f"   Maximo de 20 lotes por execucao")
    print(f"   Delay de 1s entre requisicoes (Nominatim rate limit)")

    stats = await service.process_all_pending(max_batches=20)

    print(f"\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Lotes processados: {stats.get('batches', 0)}")
    print(f"Total processados: {stats['processed']}")
    print(f"Sucesso (preciso): {stats['success']}")
    print(f"Pulados (invalidos): {stats['skipped']}")
    print(f"Falhas: {stats['failed']}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
