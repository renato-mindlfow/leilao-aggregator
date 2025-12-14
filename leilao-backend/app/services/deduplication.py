"""
Deduplication service for identifying duplicate property listings.
Uses address + city + state as the primary deduplication key.
"""

from typing import Dict, List, Set, Optional
from difflib import SequenceMatcher
import re
from app.models.property import Property


class DeduplicationService:
    def __init__(self):
        # Cache of dedup keys to property IDs
        self.dedup_index: Dict[str, List[str]] = {}
    
    def normalize_address(self, address: str) -> str:
        """Normalize address for comparison."""
        if not address:
            return ""
        
        # Convert to lowercase
        normalized = address.lower().strip()
        
        # Common abbreviations in Brazilian addresses
        replacements = {
            r'\brua\b': 'r',
            r'\bavenida\b': 'av',
            r'\btravessa\b': 'tv',
            r'\bpraça\b': 'pc',
            r'\balargar\b': 'lg',
            r'\bestrada\b': 'estr',
            r'\brodovia\b': 'rod',
            r'\bnúmero\b': 'n',
            r'\bnº\b': 'n',
            r'\bn\.\b': 'n',
            r'\bapartamento\b': 'apto',
            r'\bapt\b': 'apto',
            r'\bbloco\b': 'bl',
            r'\bedifício\b': 'ed',
            r'\bcondomínio\b': 'cond',
            r'\bconjunto\b': 'conj',
            r'\bquadra\b': 'qd',
            r'\blote\b': 'lt',
            r'\bsala\b': 'sl',
            r'\bandar\b': 'and',
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove punctuation except numbers
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized.strip()
    
    def generate_dedup_key(self, property_data: dict) -> str:
        """Generate a deduplication key for a property."""
        address = self.normalize_address(property_data.get('address', ''))
        city = property_data.get('city', '').lower().strip()
        state = property_data.get('state', '').lower().strip()
        
        return f"{address}|{city}|{state}"
    
    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings."""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def is_duplicate(
        self,
        new_property: dict,
        existing_properties: List[Property],
        threshold: float = 0.85
    ) -> Optional[str]:
        """
        Check if a property is a duplicate of an existing one.
        Returns the ID of the original property if duplicate, None otherwise.
        """
        new_key = self.generate_dedup_key(new_property)
        new_address = self.normalize_address(new_property.get('address', ''))
        new_city = new_property.get('city', '').lower().strip()
        new_state = new_property.get('state', '').lower().strip()
        
        for existing in existing_properties:
            # Skip if different state
            if existing.state.lower().strip() != new_state:
                continue
            
            # Skip if different city
            if existing.city.lower().strip() != new_city:
                continue
            
            # Check exact match first
            existing_key = existing.dedup_key or self.generate_dedup_key({
                'address': existing.address,
                'city': existing.city,
                'state': existing.state
            })
            
            if new_key == existing_key:
                return existing.id
            
            # Check fuzzy match on address
            existing_address = self.normalize_address(existing.address or '')
            if new_address and existing_address:
                similarity = self.similarity_score(new_address, existing_address)
                if similarity >= threshold:
                    return existing.id
        
        return None
    
    def find_duplicates_in_batch(
        self,
        properties: List[Property],
        threshold: float = 0.85
    ) -> Dict[str, List[str]]:
        """
        Find all duplicates in a batch of properties.
        Returns a dict mapping original property IDs to lists of duplicate IDs.
        """
        duplicates: Dict[str, List[str]] = {}
        processed: Set[str] = set()
        
        # Group by city and state first for efficiency
        location_groups: Dict[str, List[Property]] = {}
        for prop in properties:
            key = f"{prop.city.lower()}|{prop.state.lower()}"
            if key not in location_groups:
                location_groups[key] = []
            location_groups[key].append(prop)
        
        # Find duplicates within each location group
        for location_key, group in location_groups.items():
            for i, prop1 in enumerate(group):
                if prop1.id in processed:
                    continue
                
                prop1_address = self.normalize_address(prop1.address or '')
                
                for prop2 in group[i + 1:]:
                    if prop2.id in processed:
                        continue
                    
                    prop2_address = self.normalize_address(prop2.address or '')
                    
                    # Check for duplicate
                    if prop1_address and prop2_address:
                        similarity = self.similarity_score(prop1_address, prop2_address)
                        if similarity >= threshold:
                            if prop1.id not in duplicates:
                                duplicates[prop1.id] = []
                            duplicates[prop1.id].append(prop2.id)
                            processed.add(prop2.id)
        
        return duplicates
    
    def mark_duplicates(
        self,
        properties: Dict[str, Property],
        threshold: float = 0.85
    ) -> int:
        """
        Mark duplicate properties in the database.
        Returns the number of duplicates found.
        """
        props_list = list(properties.values())
        duplicates = self.find_duplicates_in_batch(props_list, threshold)
        
        duplicate_count = 0
        for original_id, dup_ids in duplicates.items():
            for dup_id in dup_ids:
                if dup_id in properties:
                    properties[dup_id].is_duplicate = True
                    properties[dup_id].original_id = original_id
                    duplicate_count += 1
        
        return duplicate_count
    
    def get_deduplication_stats(self, properties: Dict[str, Property]) -> dict:
        """Get statistics about duplicates in the database."""
        total = len(properties)
        duplicates = sum(1 for p in properties.values() if p.is_duplicate)
        unique = total - duplicates
        
        # Group duplicates by original
        duplicate_groups: Dict[str, int] = {}
        for prop in properties.values():
            if prop.is_duplicate and prop.original_id:
                duplicate_groups[prop.original_id] = duplicate_groups.get(prop.original_id, 0) + 1
        
        return {
            "total_properties": total,
            "unique_properties": unique,
            "duplicate_properties": duplicates,
            "duplicate_percentage": round((duplicates / total * 100) if total > 0 else 0, 2),
            "duplicate_groups": len(duplicate_groups),
            "max_duplicates_per_property": max(duplicate_groups.values()) if duplicate_groups else 0,
        }
