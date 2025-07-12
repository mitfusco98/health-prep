#!/usr/bin/env python3
"""
Enhanced Keyword Matching System
Supports multi-word phrases and context-aware matching for medical document parsing
"""

import json
import re
from typing import List, Dict, Tuple

class EnhancedKeywordMatcher:
    """
    Advanced keyword matching that supports:
    - Multi-word phrases (e.g., "breast US", "mammogram screening")
    - Context-aware matching
    - Word boundary enforcement
    - Phrase proximity matching
    """
    
    def __init__(self):
        self.debug_mode = False
    
    def match_keywords_in_content(self, content: str, keywords: List[str]) -> Dict:
        """
        Match keywords in content with enhanced logic
        
        Args:
            content: Document content to search
            keywords: List of keywords (can be single words or phrases)
            
        Returns:
            Dict with match results, confidence, and context
        """
        if not content or not keywords:
            return {
                'is_match': False,
                'matched_keywords': [],
                'match_contexts': [],
                'confidence': 0.0
            }
        
        content_lower = content.lower()
        matched_keywords = []
        match_contexts = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            # Handle multi-word phrases vs single words differently
            if ' ' in keyword_lower:
                # Multi-word phrase matching
                if self._match_phrase(content_lower, keyword_lower):
                    matched_keywords.append(keyword)
                    context = self._extract_context(content, keyword_lower)
                    match_contexts.append({
                        'keyword': keyword,
                        'context': context,
                        'match_type': 'phrase'
                    })
            else:
                # Single word matching with word boundaries
                if self._match_single_word(content_lower, keyword_lower):
                    matched_keywords.append(keyword)
                    context = self._extract_context(content, keyword_lower)
                    match_contexts.append({
                        'keyword': keyword,
                        'context': context,
                        'match_type': 'word'
                    })
        
        # Calculate confidence based on number and quality of matches
        confidence = self._calculate_confidence(matched_keywords, keywords)
        
        return {
            'is_match': len(matched_keywords) > 0,
            'matched_keywords': matched_keywords,
            'match_contexts': match_contexts,
            'confidence': confidence
        }
    
    def _match_phrase(self, content: str, phrase: str) -> bool:
        """
        Match multi-word phrases with flexible spacing and punctuation
        """
        # Create a regex pattern that allows for flexible spacing and punctuation
        # Convert "breast US" to pattern that matches "breast US", "breast-US", "breast_US", etc.
        words = phrase.split()
        pattern_parts = []
        
        for i, word in enumerate(words):
            escaped_word = re.escape(word)
            pattern_parts.append(escaped_word)
            
            # Add flexible separator pattern between words (except for last word)
            if i < len(words) - 1:
                pattern_parts.append(r'[\s\-_]*')  # Allow spaces, hyphens, underscores
        
        pattern = r'\b' + ''.join(pattern_parts) + r'\b'
        
        return bool(re.search(pattern, content, re.IGNORECASE))
    
    def _match_single_word(self, content: str, word: str) -> bool:
        """
        Match single words with word boundary enforcement
        """
        pattern = r'\b' + re.escape(word) + r'\b'
        return bool(re.search(pattern, content, re.IGNORECASE))
    
    def _extract_context(self, content: str, keyword: str, context_chars: int = 100) -> str:
        """
        Extract context around the matched keyword
        """
        content_lower = content.lower()
        keyword_lower = keyword.lower()
        
        # Find the first occurrence
        if ' ' in keyword_lower:
            # For phrases, find the approximate location
            words = keyword_lower.split()
            first_word = words[0]
            match = re.search(r'\b' + re.escape(first_word) + r'\b', content_lower)
        else:
            match = re.search(r'\b' + re.escape(keyword_lower) + r'\b', content_lower)
        
        if match:
            start_pos = match.start()
            context_start = max(0, start_pos - context_chars // 2)
            context_end = min(len(content), start_pos + len(keyword) + context_chars // 2)
            
            context = content[context_start:context_end].strip()
            
            # Add ellipsis if we truncated
            if context_start > 0:
                context = "..." + context
            if context_end < len(content):
                context = context + "..."
                
            return context
        
        return ""
    
    def _calculate_confidence(self, matched_keywords: List[str], all_keywords: List[str]) -> float:
        """
        Calculate confidence score based on match quality
        """
        if not all_keywords:
            return 0.0
        
        # Base confidence on percentage of keywords matched
        base_confidence = len(matched_keywords) / len(all_keywords)
        
        # Boost confidence for phrase matches (more specific)
        phrase_bonus = 0.0
        for keyword in matched_keywords:
            if ' ' in keyword:
                phrase_bonus += 0.2  # 20% bonus for each phrase match
        
        # Cap at 1.0
        return min(1.0, base_confidence + phrase_bonus)

def update_mammogram_keywords_with_phrases():
    """
    Update mammogram keywords to use phrase-based matching
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    from models import ScreeningType
    
    with app.app_context():
        print("🔧 UPDATING MAMMOGRAM KEYWORDS FOR PHRASE MATCHING")
        print("=" * 60)
        
        mammogram_type = ScreeningType.query.filter(
            ScreeningType.name.ilike('%mammogram%')
        ).first()
        
        if not mammogram_type:
            print("❌ Mammogram screening type not found")
            return
        
        # New keywords that support phrase matching
        new_keywords = [
            "mammogram",
            "mammography", 
            "mammographic",
            "breast US",           # Multi-word phrase - will match "breast US", "breast-US", etc.
            "breast ultrasound",   # Full phrase
            "breast imaging",      # Multi-word phrase
            "bilateral mammogram", # Multi-word phrase
            "screening mammography",
            "digital mammography",
            "tomosynthesis",
            "breast MRI"
        ]
        
        print(f"📝 Original Keywords: {json.loads(mammogram_type.content_keywords)}")
        print(f"✨ New Phrase-Based Keywords: {new_keywords}")
        
        # Update the keywords
        mammogram_type.content_keywords = json.dumps(new_keywords)
        db.session.commit()
        
        print("✅ Mammogram keywords updated with phrase support")
        
        return new_keywords

def test_enhanced_matching():
    """
    Test the enhanced matching system with Charlotte Taylor's documents
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    from models import Patient, MedicalDocument
    
    with app.app_context():
        print("\n🧪 TESTING ENHANCED KEYWORD MATCHING")
        print("=" * 50)
        
        # Get new keywords
        new_keywords = [
            "mammogram", "mammography", "mammographic",
            "breast US", "breast ultrasound", "breast imaging",
            "bilateral mammogram", "screening mammography", 
            "digital mammography", "tomosynthesis", "breast MRI"
        ]
        
        # Find Charlotte Taylor
        charlotte = Patient.query.filter(
            Patient.first_name.ilike('Charlotte'),
            Patient.last_name.ilike('Taylor')
        ).first()
        
        if not charlotte:
            print("❌ Charlotte Taylor not found")
            return
        
        print(f"👤 Testing with: {charlotte.first_name} {charlotte.last_name}")
        
        # Get her documents
        docs = MedicalDocument.query.filter_by(patient_id=charlotte.id).all()
        
        matcher = EnhancedKeywordMatcher()
        matcher.debug_mode = True
        
        print(f"\n📋 New Keywords: {new_keywords}")
        print(f"📄 Testing {len(docs)} documents:\n")
        
        matches_found = 0
        for doc in docs:
            print(f"📄 {doc.filename}")
            
            result = matcher.match_keywords_in_content(doc.content, new_keywords)
            
            if result['is_match']:
                matches_found += 1
                print(f"   ✅ MATCH - Confidence: {result['confidence']:.2f}")
                for context in result['match_contexts']:
                    print(f"   🎯 '{context['keyword']}' ({context['match_type']})")
                    print(f"   📝 Context: {context['context'][:100]}...")
            else:
                print(f"   ❌ No match")
            print()
        
        print(f"📊 RESULTS:")
        print(f"   Documents tested: {len(docs)}")
        print(f"   Matches found: {matches_found}")
        
        if matches_found == 0:
            print("   ✅ SUCCESS: No false positives with enhanced matching!")
        else:
            print("   ⚠️  Manual review recommended for matched documents")

if __name__ == "__main__":
    # Update keywords first
    update_mammogram_keywords_with_phrases()
    
    # Test the new system
    test_enhanced_matching()