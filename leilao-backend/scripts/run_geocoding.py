#!/usr/bin/env python3
"""
Script para executar geocoding manualmente.

Uso:
    python scripts/run_geocoding.py              # Processa todos pendentes
    python scripts/run_geocoding.py --batch 100  # Processa 100 por vez
    python scripts/run_geocoding.py --stats      # Mostra estatísticas
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description='Executa geocoding de imóveis')
    parser.add_argument('--batch', type=int, default=50, help='Tamanho do lote')
    parser.add_argument('--max-batches', type=int, default=100, help='Máximo de lotes')
    parser.add_argument('--stats', action='store_true', help='Mostra estatísticas')
    args = parser.parse_args()
    
    from app.services.async_geocoding_service import get_geocoding_service
    
    service = get_geocoding_service()
    
    if args.stats:
        stats = service.get_stats()
        pending = service.get_pending_count()
        
        print("\n" + "=" * 50)
        print("ESTATÍSTICAS DE GEOCODING")
        print("=" * 50)
        print(f"Pendentes: {pending}")
        print("\nPor status:")
        for status, count in sorted(stats.items()):
            print(f"  {status}: {count}")
        print("=" * 50)
        return
    
    print("\n" + "=" * 50)
    print("INICIANDO GEOCODING")
    print("=" * 50)
    print(f"Tamanho do lote: {args.batch}")
    print(f"Máximo de lotes: {args.max_batches}")
    
    pending = service.get_pending_count()
    print(f"Imóveis pendentes: {pending}")
    print("=" * 50 + "\n")
    
    if pending == 0:
        print("Nenhum imóvel pendente de geocoding!")
        return
    
    stats = await service.process_all_pending(max_batches=args.max_batches)
    
    print("\n" + "=" * 50)
    print("RESULTADO DO GEOCODING")
    print("=" * 50)
    print(f"Processados: {stats.get('processed', 0)}")
    print(f"Sucesso: {stats.get('success', 0)}")
    print(f"Falha: {stats.get('failed', 0)}")
    print(f"Ignorados: {stats.get('skipped', 0)}")
    print(f"Lotes: {stats.get('batches', 0)}")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())

