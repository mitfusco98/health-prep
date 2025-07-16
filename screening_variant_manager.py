
"""
Screening Type Variant Management System
Handles consolidation of screening variants with same base names
"""

import re
from typing import List, Dict, Optional, Set
from models import ScreeningType
from app import db


class ScreeningVariantManager:
    """Manages screening type variants and their consolidation"""
    
    def __init__(self):
        self.variant_patterns = [
            r'^(.+?)\s*-\s*(.+)$',  # "A1c - Diabetes Management"
            r'^(.+?)\s*\((.+)\)$',  # "A1c (Diabetes)"
            r'^(.+?)\s*for\s*(.+)$',  # "A1c for Diabetes"
            r'^(.+?)\s*:\s*(.+)$',   # "A1c: Diabetes"
        ]
    
    def extract_base_name(self, screening_name: str) -> str:
        """Extract base screening name from variant name"""
        if not screening_name:
            return ""
            
        # Try each variant pattern
        for pattern in self.variant_patterns:
            match = re.match(pattern, screening_name, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # If no pattern matches, return original name
        return screening_name.strip()
    
    def get_variant_suffix(self, screening_name: str) -> Optional[str]:
        """Extract variant suffix from screening name"""
        for pattern in self.variant_patterns:
            match = re.match(pattern, screening_name, re.IGNORECASE)
            if match:
                return match.group(2).strip()
        return None
    
    def find_screening_variants(self, base_name: str) -> List[ScreeningType]:
        """Find all screening type variants for a base name"""
        variants = []
        all_screenings = ScreeningType.query.all()
        
        for screening in all_screenings:
            if self.extract_base_name(screening.name).lower() == base_name.lower():
                variants.append(screening)
        
        return variants
    
    def get_consolidated_screening_groups(self) -> Dict[str, List[ScreeningType]]:
        """Get all screening types grouped by base name"""
        groups = {}
        all_screenings = ScreeningType.query.all()
        
        for screening in all_screenings:
            base_name = self.extract_base_name(screening.name)
            if base_name not in groups:
                groups[base_name] = []
            groups[base_name].append(screening)
        
        return groups
    
    def get_primary_screening_for_base(self, base_name: str) -> Optional[ScreeningType]:
        """Get the primary (original) screening for a base name"""
        variants = self.find_screening_variants(base_name)
        
        if not variants:
            return None
        
        # Find the one that matches the base name exactly (primary)
        for variant in variants:
            if variant.name.lower() == base_name.lower():
                return variant
        
        # If no exact match, return first variant
        return variants[0]
    
    def sync_variant_statuses(self, base_name: str, new_status: bool):
        """Sync active status across all variants of a base screening type"""
        variants = self.find_screening_variants(base_name)
        
        for variant in variants:
            if variant.is_active != new_status:
                variant.is_active = new_status
        
        db.session.commit()
        return len(variants)
    
    def get_consolidated_status(self, base_name: str) -> bool:
        """Get the consolidated active status for a base screening type"""
        variants = self.find_screening_variants(base_name)
        
        if not variants:
            return False
        
        # Return True if ANY variant is active
        return any(variant.is_active for variant in variants)
    
    def should_show_unified_button(self, base_name: str) -> bool:
        """Check if we should show unified status button for this base name"""
        variants = self.find_screening_variants(base_name)
        return len(variants) > 1
        
        # Primary is the one with exact name match or shortest name
        primary_candidates = [v for v in variants if v.name.lower() == base_name.lower()]
        if primary_candidates:
            return primary_candidates[0]
        
        # If no exact match, return the shortest name (likely the original)
        return min(variants, key=lambda x: len(x.name))
    
    def get_consolidated_status(self, base_name: str) -> bool:
        """Get consolidated active status for all variants of a base screening"""
        variants = self.find_screening_variants(base_name)
        
        if not variants:
            return False
        
        # If ANY variant is active, the consolidated screening is considered active
        return any(variant.is_active for variant in variants)
    
    def sync_variant_statuses(self, base_name: str, new_status: bool):
        """Synchronize all variants to have the same status"""
        variants = self.find_screening_variants(base_name)
        
        for variant in variants:
            variant.is_active = new_status
        
        db.session.commit()
    
    def get_variant_display_info(self, screening: ScreeningType) -> Dict[str, str]:
        """Get display information for a screening variant"""
        base_name = self.extract_base_name(screening.name)
        variant_suffix = self.get_variant_suffix(screening.name)
        
        return {
            'base_name': base_name,
            'variant_suffix': variant_suffix,
            'full_name': screening.name,
            'is_variant': variant_suffix is not None
        }


# Global instance
variant_manager = ScreeningVariantManager()
