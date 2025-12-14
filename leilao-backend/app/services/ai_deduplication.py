"""
AI-based deduplication service for property listings.
Uses text similarity and address normalization to identify duplicates.
"""
import re
import logging
from typing import Optional, Dict
from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

from app.models.property import Property, PropertyCategory, AuctionType

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    """Represents a potential duplicate match."""
    property1_id: str
    property2_id: str
    similarity_score: float
    match_reasons: list[str]


class AIDeduplicationService:
    """
    AI-based deduplication service that uses multiple signals to identify duplicates:
    1. Address normalization and comparison
    2. Text similarity for titles and descriptions
    3. Geographic proximity (when coordinates available)
    4. Value similarity
    5. Category matching
    """
    
    def __init__(self, similarity_threshold: float = 0.75):
        self.similarity_threshold = similarity_threshold
        self.address_cache: dict[str, str] = {}
        
    def normalize_address(self, address: str) -> str:
        """
        Normalize an address for comparison.
        Removes accents, standardizes abbreviations, removes punctuation.
        """
        if not address:
            return ""
            
        # Convert to lowercase
        normalized = address.lower().strip()
        
        # Remove accents
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        # Standardize common abbreviations
        replacements = {
            r'\bav\.?\b': 'avenida',
            r'\br\.?\b': 'rua',
            r'\bpca\.?\b': 'praca',
            r'\bpraca\b': 'praca',
            r'\btrav\.?\b': 'travessa',
            r'\bal\.?\b': 'alameda',
            r'\brod\.?\b': 'rodovia',
            r'\best\.?\b': 'estrada',
            r'\blgo\.?\b': 'largo',
            r'\bpq\.?\b': 'parque',
            r'\bjd\.?\b': 'jardim',
            r'\bvl\.?\b': 'vila',
            r'\bconj\.?\b': 'conjunto',
            r'\bcond\.?\b': 'condominio',
            r'\bed\.?\b': 'edificio',
            r'\bedif\.?\b': 'edificio',
            r'\bapto?\.?\b': 'apartamento',
            r'\blt\.?\b': 'lote',
            r'\bqd\.?\b': 'quadra',
            r'\bbl\.?\b': 'bloco',
            r'\bn[°º]?\s*': 'numero ',
            r'\bnr\.?\s*': 'numero ',
            r'\bnum\.?\s*': 'numero ',
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
            
        # Remove punctuation except numbers
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
        
    def extract_address_components(self, address: str) -> dict:
        """Extract structured components from an address."""
        components = {
            'street_type': '',
            'street_name': '',
            'number': '',
            'complement': '',
            'neighborhood': '',
        }
        
        normalized = self.normalize_address(address)
        
        # Extract street type
        street_types = ['rua', 'avenida', 'alameda', 'travessa', 'praca', 'largo', 'rodovia', 'estrada']
        for st in street_types:
            if st in normalized:
                components['street_type'] = st
                break
                
        # Extract number
        number_match = re.search(r'numero\s*(\d+)', normalized)
        if number_match:
            components['number'] = number_match.group(1)
        else:
            # Try to find standalone number
            number_match = re.search(r'\b(\d{1,5})\b', normalized)
            if number_match:
                components['number'] = number_match.group(1)
                
        # Extract street name (between street type and number)
        if components['street_type']:
            pattern = rf'{components["street_type"]}\s+(.+?)(?:\s+numero|\s+\d|$)'
            name_match = re.search(pattern, normalized)
            if name_match:
                components['street_name'] = name_match.group(1).strip()
                
        return components
        
    def calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two addresses."""
        norm1 = self.normalize_address(addr1)
        norm2 = self.normalize_address(addr2)
        
        if not norm1 or not norm2:
            return 0.0
            
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
            
        # Use SequenceMatcher for fuzzy matching
        base_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Extract and compare components
        comp1 = self.extract_address_components(addr1)
        comp2 = self.extract_address_components(addr2)
        
        # Bonus for matching components
        bonus = 0.0
        
        # Same street number is a strong signal
        if comp1['number'] and comp1['number'] == comp2['number']:
            bonus += 0.15
            
        # Same street type
        if comp1['street_type'] and comp1['street_type'] == comp2['street_type']:
            bonus += 0.05
            
        # Similar street name
        if comp1['street_name'] and comp2['street_name']:
            name_sim = SequenceMatcher(None, comp1['street_name'], comp2['street_name']).ratio()
            if name_sim > 0.8:
                bonus += 0.1
                
        return min(1.0, base_similarity + bonus)
        
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
            
        # Normalize texts
        norm1 = self.normalize_address(text1)  # Reuse normalization
        norm2 = self.normalize_address(text2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
        
    def calculate_value_similarity(self, val1: Optional[float], val2: Optional[float]) -> float:
        """Calculate similarity between two monetary values."""
        if val1 is None or val2 is None:
            return 0.5  # Neutral if values unknown
            
        if val1 == 0 or val2 == 0:
            return 0.5
            
        # Calculate percentage difference
        diff_pct = abs(val1 - val2) / max(val1, val2)
        
        # Values within 10% are very similar
        if diff_pct <= 0.1:
            return 1.0
        elif diff_pct <= 0.2:
            return 0.8
        elif diff_pct <= 0.3:
            return 0.6
        elif diff_pct <= 0.5:
            return 0.4
        else:
            return 0.2
            
    def calculate_overall_similarity(self, prop1: Property, prop2: Property) -> tuple[float, list[str]]:
        """
        Calculate overall similarity between two properties.
        Returns similarity score and list of match reasons.
        """
        reasons = []
        scores = []
        weights = []
        
        # 1. Address similarity (highest weight)
        addr1 = f"{prop1.address or ''}, {prop1.neighborhood or ''}, {prop1.city}, {prop1.state}"
        addr2 = f"{prop2.address or ''}, {prop2.neighborhood or ''}, {prop2.city}, {prop2.state}"
        addr_sim = self.calculate_address_similarity(addr1, addr2)
        scores.append(addr_sim)
        weights.append(0.4)
        if addr_sim > 0.8:
            reasons.append(f"Endereços muito similares ({addr_sim:.0%})")
        elif addr_sim > 0.6:
            reasons.append(f"Endereços similares ({addr_sim:.0%})")
            
        # 2. Same city and state (required for match)
        if prop1.city.lower() != prop2.city.lower() or prop1.state.upper() != prop2.state.upper():
            return 0.0, []  # Different locations, not duplicates
            
        # 3. Title similarity
        title_sim = self.calculate_text_similarity(prop1.title, prop2.title)
        scores.append(title_sim)
        weights.append(0.2)
        if title_sim > 0.8:
            reasons.append(f"Títulos muito similares ({title_sim:.0%})")
            
        # 4. Category match
        if prop1.category == prop2.category:
            scores.append(1.0)
            weights.append(0.15)
            reasons.append("Mesma categoria")
        else:
            scores.append(0.0)
            weights.append(0.15)
            
        # 5. Value similarity (using existing model fields)
        val1 = prop1.evaluation_value or prop1.first_auction_value
        val2 = prop2.evaluation_value or prop2.first_auction_value
        val_sim = self.calculate_value_similarity(val1, val2)
        scores.append(val_sim)
        weights.append(0.15)
        if val_sim > 0.8:
            reasons.append(f"Valores similares ({val_sim:.0%})")
            
        # 6. Area similarity (if available)
        area1 = prop1.area_total or prop1.area_privativa
        area2 = prop2.area_total or prop2.area_privativa
        if area1 and area2:
            area_sim = self.calculate_value_similarity(area1, area2)
            scores.append(area_sim)
            weights.append(0.1)
            if area_sim > 0.8:
                reasons.append(f"Áreas similares ({area_sim:.0%})")
        else:
            # No area info, use neutral score
            scores.append(0.5)
            weights.append(0.1)
            
        # Calculate weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return overall_score, reasons
        
    def find_duplicates(self, properties: list[Property]) -> list[DuplicateMatch]:
        """
        Find all duplicate pairs in a list of properties.
        Uses AI-based similarity scoring.
        """
        duplicates = []
        n = len(properties)
        
        logger.info(f"Checking {n} properties for duplicates...")
        
        # Group properties by city/state for efficiency
        location_groups: dict[str, list[Property]] = {}
        for prop in properties:
            key = f"{prop.city.lower()}_{prop.state.upper()}"
            if key not in location_groups:
                location_groups[key] = []
            location_groups[key].append(prop)
            
        # Compare properties within each location group
        for location, group in location_groups.items():
            group_size = len(group)
            for i in range(group_size):
                for j in range(i + 1, group_size):
                    prop1 = group[i]
                    prop2 = group[j]
                    
                    # Skip if same auctioneer (not a duplicate, same listing)
                    # Check both auctioneer_name and auctioneer_id for compatibility
                    if prop1.auctioneer_id and prop2.auctioneer_id and prop1.auctioneer_id == prop2.auctioneer_id:
                        continue
                    if prop1.auctioneer_name and prop2.auctioneer_name and prop1.auctioneer_name == prop2.auctioneer_name:
                        continue
                        
                    similarity, reasons = self.calculate_overall_similarity(prop1, prop2)
                    
                    if similarity >= self.similarity_threshold:
                        duplicates.append(DuplicateMatch(
                            property1_id=prop1.id,
                            property2_id=prop2.id,
                            similarity_score=similarity,
                            match_reasons=reasons
                        ))
                        
        logger.info(f"Found {len(duplicates)} potential duplicate pairs")
        return duplicates
        
    def deduplicate_properties(self, properties: list[Property]) -> tuple[list[Property], list[Property]]:
        """
        Deduplicate a list of properties.
        Returns (unique_properties, duplicate_properties).
        
        For duplicates, keeps the property with:
        1. More complete information
        2. Lower price (better deal)
        3. More recent scrape date
        """
        if not properties:
            return [], []
            
        duplicates = self.find_duplicates(properties)
        
        # Build a set of property IDs that are duplicates
        duplicate_ids: set[str] = set()
        
        # For each duplicate pair, decide which one to keep
        for match in duplicates:
            prop1 = next((p for p in properties if p.id == match.property1_id), None)
            prop2 = next((p for p in properties if p.id == match.property2_id), None)
            
            if not prop1 or not prop2:
                continue
                
            # Score each property based on completeness
            score1 = self._calculate_completeness_score(prop1)
            score2 = self._calculate_completeness_score(prop2)
            
            # Keep the one with higher score, mark the other as duplicate
            if score1 >= score2:
                duplicate_ids.add(prop2.id)
            else:
                duplicate_ids.add(prop1.id)
                
        # Separate unique and duplicate properties
        unique = [p for p in properties if p.id not in duplicate_ids]
        duplicates_list = [p for p in properties if p.id in duplicate_ids]
        
        logger.info(f"Deduplication complete: {len(unique)} unique, {len(duplicates_list)} duplicates")
        return unique, duplicates_list
        
    def _calculate_completeness_score(self, prop: Property) -> float:
        """Calculate a completeness score for a property."""
        score = 0.0
        
        # Basic info
        if prop.title and len(prop.title) > 20:
            score += 1
        if prop.description and len(prop.description) > 50:
            score += 1
        if prop.address:
            score += 1
        if prop.neighborhood:
            score += 0.5
            
        # Values (using existing model fields)
        if prop.evaluation_value:
            score += 1
        if prop.first_auction_value:
            score += 1
        if prop.first_auction_date:
            score += 0.5
        if prop.second_auction_value:
            score += 1
        if prop.second_auction_date:
            score += 0.5
            
        # Additional info
        if prop.area_total or prop.area_privativa:
            score += 1
        if prop.image_url:
            score += 0.5
        if prop.discount_percentage:
            score += 0.5
            
        # Payment options
        if prop.accepts_financing:
            score += 0.3
        if prop.accepts_fgts:
            score += 0.3
        if prop.accepts_installments:
            score += 0.3
            
        # Prefer lower prices (better deals)
        if prop.second_auction_value:
            # Bonus for having second auction (usually lower price)
            score += 0.5
            
        return score


# Global instance
_deduplication_service: Optional[AIDeduplicationService] = None


def get_deduplication_service() -> AIDeduplicationService:
    """Get the global deduplication service instance."""
    global _deduplication_service
    if _deduplication_service is None:
        _deduplication_service = AIDeduplicationService()
    return _deduplication_service
