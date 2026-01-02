"""
Script para limpar URLs de imagens inválidas do banco de dados.
Executa uma vez para corrigir dados existentes.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from app.utils.image_blacklist import is_valid_image_url

DATABASE_URL = os.getenv("DATABASE_URL")

def clean_invalid_images():
    """Remove URLs de imagens inválidas do banco."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Buscar todas as URLs de imagem
    cur.execute("SELECT id, image_url FROM properties WHERE image_url IS NOT NULL")
    rows = cur.fetchall()
    
    invalid_count = 0
    valid_count = 0
    
    for row in rows:
        prop_id, image_url = row
        
        if not is_valid_image_url(image_url):
            # Marcar como NULL
            cur.execute("UPDATE properties SET image_url = NULL WHERE id = %s", (prop_id,))
            invalid_count += 1
            print(f"❌ Removida imagem inválida: {image_url[:50]}...")
        else:
            valid_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ Limpeza concluída!")
    print(f"   Imagens válidas: {valid_count}")
    print(f"   Imagens removidas: {invalid_count}")

if __name__ == "__main__":
    clean_invalid_images()

