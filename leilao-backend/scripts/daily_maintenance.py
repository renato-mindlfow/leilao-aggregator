"""
Script de manutenção diária.
Executar via cron ou scheduler.

Tarefas:
1. Auditoria e correção de dados
2. Buscar imagens faltantes da Caixa (limite de 50 por execução)
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from scripts.audit_data_quality import audit_data_quality

def main():
    print(f"\n{'='*60}")
    print(f"MANUTENÇÃO DIÁRIA - {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    # 1. Auditoria com correção
    print("ETAPA 1: Auditoria de dados")
    print("-" * 40)
    audit_data_quality(fix=True)
    
    # 2. Buscar imagens da Caixa (se o script existir)
    try:
        from scripts.fetch_caixa_images import fetch_and_update_images
        print("\nETAPA 2: Buscar imagens da Caixa")
        print("-" * 40)
        fetch_and_update_images(limit=50)
    except ImportError:
        print("\n⏭️ Script de imagens da Caixa não disponível")
    
    print(f"\n{'='*60}")
    print("MANUTENÇÃO CONCLUÍDA")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

