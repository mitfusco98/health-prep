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

        # Trigger cascade cleanup if deactivating
        if not new_status:
            self._trigger_deactivation_cascade(base_name)

    def sync_single_variant_status(self, screening_type_id: int, new_status: bool) -> bool:
        """
        Sync status of a single variant and all its related variants

        Args:
            screening_type_id: ID of the screening type being changed
            new_status: New status (True for active, False for inactive)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the screening type being changed
            screening_type = ScreeningType.query.get(screening_type_id)
            if not screening_type:
                return False

            base_name = self.extract_base_name(screening_type.name)

            # Find all variants of this base name
            variants = self.find_screening_variants(base_name)

            # Update status for all variants
            for variant in variants:
                variant.is_active = new_status
                print(f"Setting {variant.name} (ID: {variant.id}) to {'active' if new_status else 'inactive'}")

            db.session.commit()
            print(f"Successfully synced {len(variants)} variants for base name '{base_name}' to {'active' if new_status else 'inactive'}")

            # Trigger cascade cleanup if deactivating
            if not new_status:
                self._trigger_deactivation_cascade(base_name)

            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error syncing variant status: {e}")
            return False

    def _trigger_deactivation_cascade(self, base_name: str):
        """Trigger cascade cleanup when variants are deactivated"""
        try:
            from automated_edge_case_handler import handle_screening_type_change

            # Clean up all existing screenings for this base name
            variants = self.find_screening_variants(base_name)
            for variant in variants:
                handle_screening_type_change(variant.id, False)
        except Exception as e:
            print(f"Warning: Could not trigger deactivation cascade for {base_name}: {e}")

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