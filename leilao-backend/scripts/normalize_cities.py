"""
Script para normalizar nomes de cidades no banco de dados.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from app.utils.text_normalizer import normalize_city_name, normalize_neighborhood

DATABASE_URL = os.getenv("DATABASE_URL")

def normalize_cities():
    """Normaliza nomes de cidades e bairros no banco."""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Buscar cidades distintas
    cur.execute("SELECT DISTINCT city FROM properties WHERE city IS NOT NULL")
    cities = cur.fetchall()
    
    updated_count = 0
    
    for (city,) in cities:
        normalized = normalize_city_name(city)
        
        if normalized and normalized != city:
            cur.execute(
                "UPDATE properties SET city = %s WHERE city = %s",
                (normalized, city)
            )
            count = cur.rowcount
            updated_count += count
            print(f"✅ '{city}' → '{normalized}' ({count} registros)")
    
    # Normalizar bairros
    cur.execute("SELECT DISTINCT neighborhood FROM properties WHERE neighborhood IS NOT NULL")
    neighborhoods = cur.fetchall()
    
    for (neighborhood,) in neighborhoods:
        normalized = normalize_neighborhood(neighborhood)
        
        if normalized and normalized != neighborhood:
            cur.execute(
                "UPDATE properties SET neighborhood = %s WHERE neighborhood = %s",
                (normalized, neighborhood)
            )
            count = cur.rowcount
            updated_count += count
            print(f"✅ Bairro: '{neighborhood}' → '{normalized}' ({count} registros)")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ Normalização concluída! {updated_count} registros atualizados.")

if __name__ == "__main__":
    normalize_cities()





