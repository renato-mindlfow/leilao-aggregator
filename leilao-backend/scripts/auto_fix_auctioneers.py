#!/usr/bin/env python3
"""
CORREÇÃO AUTOMÁTICA DE LEILOEIROS - LEILOHUB
Aplica correções automáticas baseadas na análise.
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from glob import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def main():
    """Aplica correções automáticas baseadas na análise."""
    
    logger.info("=" * 70)
    logger.info("CORREÇÃO AUTOMÁTICA DE LEILOEIROS")
    logger.info("=" * 70)
    
    # Encontrar arquivo de análise mais recente
    analysis_files = glob("analise_leiloeiros_*.json")
    if not analysis_files:
        logger.error("Nenhum arquivo de análise encontrado. Execute deep_auctioneer_analysis.py primeiro.")
        return
    
    latest_file = max(analysis_files)
    logger.info(f"Usando análise: {latest_file}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    # Contadores
    updated_urls = 0
    deactivated = 0
    marked_for_playwright = 0
    reset_for_retry = 0
    
    for item in results:
        auctioneer_id = item.get("id")
        diagnosis = item.get("diagnosis")
        discovered_url = item.get("discovered_url")
        
        # 1. Atualizar URLs descobertas
        if discovered_url:
            logger.info(f"  Atualizando URL: {item.get('name')} -> {discovered_url}")
            supabase.table("auctioneers") \
                .update({
                    "website": discovered_url,
                    "scrape_status": "pending",
                    "scrape_error": None,
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("id", auctioneer_id) \
                .execute()
            updated_urls += 1
        
        # 2. Desativar sites offline/DNS falha
        if diagnosis in ["DNS_FALHA", "SITE_OFFLINE"]:
            logger.info(f"  Desativando: {item.get('name')} ({diagnosis})")
            supabase.table("auctioneers") \
                .update({
                    "is_active": False,
                    "scrape_status": "disabled",
                    "scrape_error": f"Desativado automaticamente: {diagnosis}",
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("id", auctioneer_id) \
                .execute()
            deactivated += 1
        
        # 3. Marcar para Playwright
        if diagnosis in ["CLOUDFLARE", "CONTEUDO_DINAMICO"]:
            logger.info(f"  Marcando para Playwright: {item.get('name')}")
            supabase.table("auctioneers") \
                .update({
                    "scrape_status": "needs_playwright",
                    "scrape_error": f"Requer Playwright: {diagnosis}",
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("id", auctioneer_id) \
                .execute()
            marked_for_playwright += 1
        
        # 4. Resetar para retry os que parecem temporários
        if diagnosis in ["TIMEOUT", "500_SERVER_ERROR", "SITE_EM_MANUTENCAO"]:
            logger.info(f"  Resetando para retry: {item.get('name')} ({diagnosis})")
            supabase.table("auctioneers") \
                .update({
                    "scrape_status": "pending",
                    "scrape_error": f"Reset para retry: {diagnosis}",
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("id", auctioneer_id) \
                .execute()
            reset_for_retry += 1
    
    logger.info(f"\n{'=' * 70}")
    logger.info("CORREÇÕES APLICADAS:")
    logger.info(f"  URLs atualizadas: {updated_urls}")
    logger.info(f"  Desativados: {deactivated}")
    logger.info(f"  Marcados para Playwright: {marked_for_playwright}")
    logger.info(f"  Resetados para retry: {reset_for_retry}")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()

