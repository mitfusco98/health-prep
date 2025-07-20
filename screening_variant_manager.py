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

        # Normalize the name for comparison
        normalized_name = screening_name.strip().lower()
        
        # Special handling for common medical test variations
        # A1C/HbA1c variants - consolidate to "HbA1c Test"
        a1c_patterns = [
            r'^hba1c(\s+test)?$',
            r'^a1c(\s+test)?$', 
            r'^hemoglobin\s+a1c(\s+test)?$',
            r'^glycated\s+hemoglobin(\s+test)?$',
            r'^diabetes\s+a1c(\s+test)?$'
        ]
        
        for pattern in a1c_patterns:
            if re.match(pattern, normalized_name):
                return "HbA1c Test"
        
        # Mammography variants - consolidate to "Mammography" 
        mammography_patterns = [
            r'^mammography$',
            r'^mammogram(\s+screening)?$',
            r'^breast\s+imaging$',
            r'^breast\s+x-ray$'
        ]
        
        for pattern in mammography_patterns:
            if re.match(pattern, normalized_name):
                return "Mammography"
        
        # Colonoscopy variants - consolidate to "Colonoscopy"
        colonoscopy_patterns = [
            r'^colonoscopy(\s+screening)?$',
            r'^colo(\s+screening)?$',
            r'^lower\s+endoscopy$',
            r'^colorectal\s+screening$',
            r'^colon\s+cancer\s+screening$'
        ]
        
        for pattern in colonoscopy_patterns:
            if re.match(pattern, normalized_name):
                return "Colonoscopy"
        
        # Pap Smear variants - consolidate to "Pap Smear"
        pap_patterns = [
            r'^pap(\s+smear)?(\s+test)?$',
            r'^cervical\s+cancer\s+screening$',
            r'^pap\s+test$',
            r'^papanicolaou(\s+test)?$',
            r'^cervical\s+cytology$'
        ]
        
        for pattern in pap_patterns:
            if re.match(pattern, normalized_name):
                return "Pap Smear"
        
        # Bone Density variants - consolidate to "Bone Density Screening"
        bone_density_patterns = [
            r'^bone\s+density(\s+screening)?(\s+test)?$',
            r'^dxa(\s+scan)?$',
            r'^dexa(\s+scan)?$',
            r'^osteoporosis\s+screening$',
            r'^bone\s+scan$'
        ]
        
        for pattern in bone_density_patterns:
            if re.match(pattern, normalized_name):
                return "Bone Density Screening"
        
        # Eye Exam variants - consolidate to "Eye Exam"
        eye_exam_patterns = [
            r'^eye\s+exam(\s+screening)?$',
            r'^vision\s+screening$',
            r'^ophthalmology(\s+exam)?$',
            r'^retinal\s+screening$',
            r'^diabetic\s+eye\s+exam$',
            r'^glaucoma\s+screening$'
        ]
        
        for pattern in eye_exam_patterns:
            if re.match(pattern, normalized_name):
                return "Eye Exam"
        
        # Lipid Panel variants - consolidate to "Lipid Panel"
        lipid_patterns = [
            r'^lipid\s+panel(\s+test)?$',
            r'^cholesterol(\s+test)?(\s+panel)?$',
            r'^lipid\s+profile$',
            r'^cholesterol\s+screening$',
            r'^lipid\s+screening$'
        ]
        
        for pattern in lipid_patterns:
            if re.match(pattern, normalized_name):
                return "Lipid Panel"
        
        # Vaccination variants - consolidate to "Vaccination History"
        vaccination_patterns = [
            r'^vaccination(\s+history)?(\s+review)?$',
            r'^immunization(\s+history)?(\s+review)?$',
            r'^vaccine(\s+status)?(\s+review)?$',
            r'^immunizations$'
        ]
        
        for pattern in vaccination_patterns:
            if re.match(pattern, normalized_name):
                return "Vaccination History"
        
        # Blood Pressure variants - consolidate to "Blood Pressure Screening"
        bp_patterns = [
            r'^blood\s+pressure(\s+screening)?(\s+check)?$',
            r'^bp(\s+screening)?(\s+check)?$',
            r'^hypertension\s+screening$',
            r'^arterial\s+pressure$'
        ]
        
        for pattern in bp_patterns:
            if re.match(pattern, normalized_name):
                return "Blood Pressure Screening"
        
        # PSA variants - consolidate to "PSA Test"
        psa_patterns = [
            r'^psa(\s+test)?(\s+screening)?$',
            r'^prostate\s+specific\s+antigen(\s+test)?$',
            r'^prostate\s+cancer\s+screening$',
            r'^prostate\s+screening$'
        ]
        
        for pattern in psa_patterns:
            if re.match(pattern, normalized_name):
                return "PSA Test"
        
        # Try each variant pattern for other screenings
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
        """Find all screening type variants and duplicates for a base name"""
        variants = []
        all_screenings = ScreeningType.query.all()

        for screening in all_screenings:
            extracted_base = self.extract_base_name(screening.name).lower()
            
            # Match by extracted base name (handles pattern-based variants)
            if extracted_base == base_name.lower():
                variants.append(screening)
            # Also match by exact name (handles duplicate names)
            elif screening.name.lower() == base_name.lower():
                variants.append(screening)

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant.id not in seen:
                seen.add(variant.id)
                unique_variants.append(variant)

        return unique_variants

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

    def find_all_related_screening_types(self, screening_type_id: int) -> List[ScreeningType]:
        """Find all screening types related to the given one (variants + exact duplicates)"""
        screening_type = ScreeningType.query.get(screening_type_id)
        if not screening_type:
            return []
        
        related_screenings = []
        all_screenings = ScreeningType.query.all()
        
        base_name = self.extract_base_name(screening_type.name)
        original_name = screening_type.name
        
        for screening in all_screenings:
            # Include if it's a pattern-based variant
            if self.extract_base_name(screening.name).lower() == base_name.lower():
                related_screenings.append(screening)
            # Include if it's an exact name duplicate
            elif screening.name.lower() == original_name.lower():
                related_screenings.append(screening)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_screenings = []
        for screening in related_screenings:
            if screening.id not in seen:
                seen.add(screening.id)
                unique_screenings.append(screening)
        
        return unique_screenings

    def sync_single_variant_status(self, screening_type_id: int, new_status: bool) -> bool:
        """
        Sync status of a single variant and all its related variants and duplicates

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

            # Find ALL related screening types (variants + exact duplicates)
            related_screenings = self.find_all_related_screening_types(screening_type_id)

            # Update status for all related screening types
            for related_screening in related_screenings:
                related_screening.is_active = new_status
                print(f"Setting {related_screening.name} (ID: {related_screening.id}) to {'active' if new_status else 'inactive'}")

            db.session.commit()
            print(f"Successfully synced {len(related_screenings)} related screening types to {'active' if new_status else 'inactive'}")

            # Trigger cascade cleanup if deactivating
            if not new_status:
                self._trigger_deactivation_cascade_by_screenings(related_screenings)

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

    def _trigger_deactivation_cascade_by_screenings(self, screenings: List[ScreeningType]):
        """Trigger cascade cleanup when specific screening types are deactivated"""
        try:
            from automated_edge_case_handler import handle_screening_type_change
            
            # Clean up all existing screenings for these specific screening types
            for screening in screenings:
                handle_screening_type_change(screening.id, False)
        except Exception as e:
            print(f"Warning: Could not trigger deactivation cascade for screening types: {e}")

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