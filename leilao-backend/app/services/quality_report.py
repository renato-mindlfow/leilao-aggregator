"""
Quality Report Service - Generates quality reports after scraping runs.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from app.services import db
from app.services.postgres_database import PostgresDatabase

logger = logging.getLogger(__name__)


class QualityReportService:
    """Service for generating quality reports after scraping."""
    
    def __init__(self):
        self.db = db
    
    def generate_report(self, auctioneer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate quality report for properties.
        
        Args:
            auctioneer_name: Optional auctioneer name to filter by
            
        Returns:
            Dictionary with quality metrics
        """
        try:
            if isinstance(self.db, PostgresDatabase):
                return self._generate_postgres_report(auctioneer_name)
            else:
                return self._generate_in_memory_report(auctioneer_name)
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return {"error": str(e)}
    
    def _generate_postgres_report(self, auctioneer_name: Optional[str]) -> Dict[str, Any]:
        """Generate report using PostgreSQL database."""
        with self.db._get_connection() as conn:
            with conn.cursor() as cur:
                # Build query
                conditions = ["is_duplicate = FALSE"]
                params = []
                
                if auctioneer_name:
                    conditions.append("auctioneer_name = %s")
                    params.append(auctioneer_name)
                
                where_clause = " AND ".join(conditions)
                
                # Total properties
                cur.execute(f"SELECT COUNT(*) as count FROM properties WHERE {where_clause}", params)
                total = cur.fetchone()['count']
                
                if total == 0:
                    return {
                        "auctioneer": auctioneer_name or "All",
                        "total": 0,
                        "message": "No properties found"
                    }
                
                # Properties with photo
                cur.execute(
                    f"SELECT COUNT(*) as count FROM properties WHERE {where_clause} AND image_url IS NOT NULL AND image_url != ''",
                    params
                )
                with_photo = cur.fetchone()['count']
                
                # Properties with price
                cur.execute(
                    f"SELECT COUNT(*) as count FROM properties WHERE {where_clause} AND (second_auction_value > 0 OR first_auction_value > 0)",
                    params
                )
                with_price = cur.fetchone()['count']
                
                # Properties with description
                cur.execute(
                    f"SELECT COUNT(*) as count FROM properties WHERE {where_clause} AND description IS NOT NULL AND description != ''",
                    params
                )
                with_description = cur.fetchone()['count']
                
                # Properties with auction date
                cur.execute(
                    f"SELECT COUNT(*) as count FROM properties WHERE {where_clause} AND (first_auction_date IS NOT NULL OR second_auction_date IS NOT NULL)",
                    params
                )
                with_date = cur.fetchone()['count']
                
                # Properties with address
                cur.execute(
                    f"SELECT COUNT(*) as count FROM properties WHERE {where_clause} AND address IS NOT NULL AND address != ''",
                    params
                )
                with_address = cur.fetchone()['count']
                
                # Properties by category
                cur.execute(
                    f"SELECT category, COUNT(*) as count FROM properties WHERE {where_clause} GROUP BY category",
                    params
                )
                by_category = {row['category']: row['count'] for row in cur.fetchall()}
                
                # Properties by state
                cur.execute(
                    f"SELECT state, COUNT(*) as count FROM properties WHERE {where_clause} GROUP BY state ORDER BY count DESC LIMIT 10",
                    params
                )
                by_state = {row['state']: row['count'] for row in cur.fetchall()}
                
                return {
                    "auctioneer": auctioneer_name or "All",
                    "generated_at": datetime.now().isoformat(),
                    "total": total,
                    "with_photo": with_photo,
                    "with_photo_percentage": round((with_photo / total * 100), 1) if total > 0 else 0,
                    "with_price": with_price,
                    "with_price_percentage": round((with_price / total * 100), 1) if total > 0 else 0,
                    "with_description": with_description,
                    "with_description_percentage": round((with_description / total * 100), 1) if total > 0 else 0,
                    "with_auction_date": with_date,
                    "with_auction_date_percentage": round((with_date / total * 100), 1) if total > 0 else 0,
                    "with_address": with_address,
                    "with_address_percentage": round((with_address / total * 100), 1) if total > 0 else 0,
                    "by_category": by_category,
                    "by_state": by_state,
                }
    
    def _generate_in_memory_report(self, auctioneer_name: Optional[str]) -> Dict[str, Any]:
        """Generate report using in-memory database."""
        properties = list(self.db.properties.values())
        
        if auctioneer_name:
            properties = [p for p in properties if p.auctioneer_name == auctioneer_name and not p.is_duplicate]
        else:
            properties = [p for p in properties if not p.is_duplicate]
        
        total = len(properties)
        if total == 0:
            return {
                "auctioneer": auctioneer_name or "All",
                "total": 0,
                "message": "No properties found"
            }
        
        with_photo = sum(1 for p in properties if p.image_url)
        with_price = sum(1 for p in properties if (p.second_auction_value and p.second_auction_value > 0) or (p.first_auction_value and p.first_auction_value > 0))
        with_description = sum(1 for p in properties if p.description)
        with_date = sum(1 for p in properties if p.first_auction_date or p.second_auction_date)
        with_address = sum(1 for p in properties if p.address)
        
        by_category = defaultdict(int)
        for p in properties:
            if p.category:
                by_category[p.category.value] += 1
        
        by_state = defaultdict(int)
        for p in properties:
            if p.state:
                by_state[p.state] += 1
        
        return {
            "auctioneer": auctioneer_name or "All",
            "generated_at": datetime.now().isoformat(),
            "total": total,
            "with_photo": with_photo,
            "with_photo_percentage": round((with_photo / total * 100), 1) if total > 0 else 0,
            "with_price": with_price,
            "with_price_percentage": round((with_price / total * 100), 1) if total > 0 else 0,
            "with_description": with_description,
            "with_description_percentage": round((with_description / total * 100), 1) if total > 0 else 0,
            "with_auction_date": with_date,
            "with_auction_date_percentage": round((with_date / total * 100), 1) if total > 0 else 0,
            "with_address": with_address,
            "with_address_percentage": round((with_address / total * 100), 1) if total > 0 else 0,
            "by_category": dict(by_category),
            "by_state": dict(sorted(by_state.items(), key=lambda x: x[1], reverse=True)[:10]),
        }


# Singleton instance
_quality_report_service: Optional[QualityReportService] = None


def get_quality_report_service() -> QualityReportService:
    """Get the singleton quality report service instance."""
    global _quality_report_service
    if _quality_report_service is None:
        _quality_report_service = QualityReportService()
    return _quality_report_service

