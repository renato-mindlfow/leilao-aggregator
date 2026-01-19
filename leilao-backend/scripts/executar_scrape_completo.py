"""
Executa scrape de todos os leiloeiros registrados e salva no Supabase
"""
import os
import sys
import io
import time
import hashlib
import asyncio
import re
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from supabase import create_client  # noqa: E402
from app.scrapers.scraper_manager import ScraperManager  # noqa: E402

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
manager = ScraperManager()

MAX_PER_SCRAPER = int(os.getenv("MAX_PER_SCRAPER", "200"))  # Volume aumentado para popular banco
SLEEP_BETWEEN_SCRAPERS = float(os.getenv("SLEEP_BETWEEN_SCRAPERS", "2"))
SCRAPERS_FILTER = [s.strip().lower() for s in os.getenv("SCRAPERS_FILTER", "").split(",") if s.strip()]

print("=" * 60)
print(f"SCRAPE COMPLETO - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)
print(f"Scrapers registrados: {len(manager.scrapers)}")
print(f"Max por scraper: {MAX_PER_SCRAPER}")

resultados = {}
total_extraidos = 0
total_salvos = 0

def normalize_properties(raw_properties):
    if raw_properties is None:
        return []
    if hasattr(raw_properties, "complete_properties"):
        raw_properties = raw_properties.complete_properties
    if not isinstance(raw_properties, list):
        return []
    normalized = []
    for prop in raw_properties:
        if isinstance(prop, dict):
            normalized.append(prop)
            continue
        if hasattr(prop, "model_dump"):
            normalized.append(prop.model_dump())
            continue
        if hasattr(prop, "dict"):
            normalized.append(prop.dict())
            continue
    return normalized


def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serialize_value(v) for v in value]
    return value


def serialize_property(prop):
    return serialize_value(prop)

for nome, scraper in manager.scrapers.items():
    if SCRAPERS_FILTER:
        normalized = nome.lower().replace(" ", "_")
        normalized_no_underscore = normalized.replace("_", "")
        auctioneer_id = getattr(scraper, "AUCTIONEER_ID", "").lower()
        auctioneer_no_underscore = auctioneer_id.replace("_", "")
        if (
            normalized not in SCRAPERS_FILTER
            and normalized_no_underscore not in SCRAPERS_FILTER
            and auctioneer_id not in SCRAPERS_FILTER
            and auctioneer_no_underscore not in SCRAPERS_FILTER
        ):
            continue
    print(f"\n[{nome.upper()}]")

    try:
        inicio = time.time()
        raw_properties = scraper.scrape_properties(max_properties=MAX_PER_SCRAPER)
        if asyncio.iscoroutine(raw_properties):
            raw_properties = asyncio.run(raw_properties)
        properties = normalize_properties(raw_properties)
        tempo = time.time() - inicio
        print(f"  Extraidos: {len(properties)} em {tempo:.1f}s")

        # Salvar no Supabase
        salvos = 0
        erros = 0
        for prop in properties:
            try:
                prop = serialize_property(prop)
                # Garantir campos obrigatorios
                prop["updated_at"] = datetime.now().isoformat()
                if not prop.get("created_at"):
                    prop["created_at"] = datetime.now().isoformat()

                # Gerar ID a partir do source_url
                source_url = prop.get("source_url")
                if source_url and not prop.get("id"):
                    digest = hashlib.md5(source_url.encode("utf-8")).hexdigest()[:16]
                    prop["id"] = f"{prop.get('auctioneer_id', 'scraper')}-{digest}"

                # Upsert baseado em id com retry para colunas inexistentes
                if prop.get("id"):
                    attempt = 0
                    while True:
                        try:
                            supabase.table("properties").upsert(
                                prop,
                                on_conflict="id",
                            ).execute()
                            salvos += 1
                            break
                        except Exception as e:
                            attempt += 1
                            msg = str(e)
                            missing_match = re.search(r"Could not find the '([^']+)' column", msg)
                            if missing_match and attempt <= 3:
                                missing_col = missing_match.group(1)
                                prop.pop(missing_col, None)
                                continue
                            raise
            except Exception as e:
                erros += 1
                if erros <= 3:
                    print(f"  Erro ao salvar: {str(e)[:50]}")

        print(f"  Salvos: {salvos}, Erros: {erros}")

        resultados[nome] = {
            "extraidos": len(properties),
            "salvos": salvos,
            "erros": erros,
            "tempo": tempo,
        }
        total_extraidos += len(properties)
        total_salvos += salvos

    except Exception as e:
        print(f"  ERRO: {e}")
        resultados[nome] = {"erro": str(e)}

    # Pausa entre scrapers para não sobrecarregar
    if SLEEP_BETWEEN_SCRAPERS > 0:
        time.sleep(SLEEP_BETWEEN_SCRAPERS)

# Resumo final
print("\n" + "=" * 60)
print("RESUMO FINAL")
print("=" * 60)
print(f"Total extraidos: {total_extraidos}")
print(f"Total salvos: {total_salvos}")
print("\nPor scraper:")
for nome, res in resultados.items():
    if "erro" in res:
        print(f"  {nome}: ERRO - {res['erro'][:30]}")
    else:
        print(f"  {nome}: {res['salvos']}/{res['extraidos']} salvos ({res['tempo']:.1f}s)")

# Atualizar status dos auctioneers
print("\nAtualizando status dos leiloeiros...")
for nome, res in resultados.items():
    try:
        status = "success" if res.get("salvos", 0) > 0 else "error"
        error_msg = res.get("erro", None)

        supabase.table("auctioneers").update(
            {
                "scrape_status": status,
                "scrape_error": error_msg,
                "last_scrape": datetime.now().isoformat(),
                "property_count": res.get("salvos", 0),
            }
        ).eq("name", nome.title()).execute()
    except Exception:
        pass

print("\nConcluido!")
