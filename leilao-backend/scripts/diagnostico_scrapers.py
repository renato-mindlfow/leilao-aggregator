#!/usr/bin/env python3
"""
Diagnostico completo do sistema de scrapers do LeiloHub.
"""
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY are not configured")
        sys.exit(1)
    return create_client(url, key)


def main():
    print("=" * 60)
    print("SCRAPER SYSTEM DIAGNOSTIC - LEILOHUB")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    supabase = get_supabase()

    # 1. Overall status
    print("\nAUCTIONEERS STATUS")
    print("-" * 40)
    result = supabase.table("auctioneers").select("scrape_status").execute()
    status_count = {}
    for row in result.data:
        status = row.get("scrape_status", "unknown")
        status_count[status] = status_count.get(status, 0) + 1

    total = sum(status_count.values())
    for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {status}: {count} ({pct:.1f}%)")
    print(f"  TOTAL: {total}")

    # 2. Top 20 by property count
    print("\nTOP 20 AUCTIONEERS BY PROPERTIES")
    print("-" * 40)
    result = (
        supabase.table("auctioneers")
        .select("name, property_count, scrape_status, last_scrape")
        .order("property_count", desc=True)
        .limit(20)
        .execute()
    )

    for i, row in enumerate(result.data, 1):
        last = row.get("last_scrape", "Never")
        if last and last != "Never":
            last = last[:10]
        print(
            f"  {i:2}. {row['name'][:25]:<25} {row['property_count']:>5} "
            f"props (last: {last})"
        )

    # 3. Properties by source
    print("\nPROPERTIES BY SOURCE (properties table)")
    print("-" * 40)
    result = supabase.rpc("get_properties_by_source").execute()
    if result.data:
        for row in result.data[:20]:
            print(f"  {row['auctioneer_name'][:30]:<30} {row['total']:>6} props")
    else:
        result = (
            supabase.table("properties")
            .select("auctioneer_name")
            .eq("is_active", True)
            .execute()
        )
        source_count = {}
        for row in result.data:
            source = row.get("auctioneer_name", "Unknown")
            source_count[source] = source_count.get(source, 0) + 1
        for source, count in sorted(source_count.items(), key=lambda x: -x[1])[:20]:
            print(f"  {source[:30]:<30} {count:>6} props")

    # 4. Recent scrapes (last 7 days)
    print("\nACTIVITY IN THE LAST 7 DAYS")
    print("-" * 40)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    result = (
        supabase.table("auctioneers")
        .select("name, last_scrape, property_count")
        .gte("last_scrape", week_ago)
        .order("last_scrape", desc=True)
        .limit(20)
        .execute()
    )
    if result.data:
        for row in result.data:
            last = row["last_scrape"][:16] if row.get("last_scrape") else "N/A"
            print(f"  {last} - {row['name'][:25]:<25} ({row['property_count']} props)")
    else:
        print("  No scrapes in the last 7 days")

    # 5. Auctioneers with errors
    print("\nAUCTIONEERS WITH ERRORS (sample)")
    print("-" * 40)
    result = (
        supabase.table("auctioneers")
        .select("name, scrape_error, website")
        .eq("scrape_status", "error")
        .not_.is_("scrape_error", "null")
        .limit(10)
        .execute()
    )
    for row in result.data:
        error = (row.get("scrape_error") or "N/A")[:50]
        print(f"  {row['name'][:20]:<20} - {error}")

    # 6. Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success = status_count.get("success", 0)
    error = status_count.get("error", 0)
    pending = status_count.get("pending", 0)

    if total > 0:
        print(f"  Success: {success} ({success / total * 100:.1f}%)")
        print(f"  Error: {error} ({error / total * 100:.1f}%)")
        print(f"  Pending: {pending} ({pending / total * 100:.1f}%)")
    else:
        print("  No auctioneers found")

    if total > 0 and success < total * 0.3:
        print("\n  ALERT: Less than 30% of scrapers are succeeding")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
