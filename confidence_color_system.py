#!/usr/bin/env python3
"""
Confidence-Based Color System for Document Matching
Provides color coding for document links based on confidence scores
"""

from typing import Dict, Optional, Tuple
import json

class ConfidenceColorSystem:
    """
    Manages confidence-based color coding for document matches
    """
    
    # Default confidence thresholds
    DEFAULT_HIGH_THRESHOLD = 0.8
    DEFAULT_MEDIUM_THRESHOLD = 0.5
    
    # Color schemes
    COLORS = {
        'high': {
            'class': 'confidence-high',
            'color': '#28a745',  # Green
            'bg_color': '#d4edda',
            'border_color': '#c3e6cb',
            'text_color': '#155724'
        },
        'medium': {
            'class': 'confidence-medium', 
            'color': '#ffc107',  # Yellow
            'bg_color': '#fff3cd',
            'border_color': '#ffeaa7',
            'text_color': '#856404'
        },
        'low': {
            'class': 'confidence-low',
            'color': '#dc3545',  # Red
            'bg_color': '#f8d7da',
            'border_color': '#f5c6cb',
            'text_color': '#721c24'
        }
    }
    
    def __init__(self, high_threshold=DEFAULT_HIGH_THRESHOLD, medium_threshold=DEFAULT_MEDIUM_THRESHOLD):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
    
    def get_confidence_level(self, confidence_score: float) -> str:
        """
        Determine confidence level based on score
        
        Args:
            confidence_score: Confidence score between 0.0 and 1.0
            
        Returns:
            'high', 'medium', or 'low'
        """
        if confidence_score >= self.high_threshold:
            return 'high'
        elif confidence_score >= self.medium_threshold:
            return 'medium'
        else:
            return 'low'
    
    def get_color_data(self, confidence_score: float) -> Dict:
        """
        Get color data for a confidence score
        
        Args:
            confidence_score: Confidence score between 0.0 and 1.0
            
        Returns:
            Dictionary with color information
        """
        level = self.get_confidence_level(confidence_score)
        color_data = self.COLORS[level].copy()
        color_data['confidence_score'] = confidence_score
        color_data['level'] = level
        return color_data
    
    def get_css_class(self, confidence_score: float) -> str:
        """Get CSS class for confidence level"""
        level = self.get_confidence_level(confidence_score)
        return self.COLORS[level]['class']
    
    def get_inline_style(self, confidence_score: float) -> str:
        """Get inline CSS style for confidence level"""
        color_data = self.get_color_data(confidence_score)
        return f"color: {color_data['text_color']}; background-color: {color_data['bg_color']}; border-color: {color_data['border_color']};"
    
    def get_badge_html(self, confidence_score: float, show_score=True) -> str:
        """
        Generate HTML badge for confidence level
        
        Args:
            confidence_score: Confidence score
            show_score: Whether to show numerical score
            
        Returns:
            HTML string for confidence badge
        """
        color_data = self.get_color_data(confidence_score)
        score_text = f" ({confidence_score:.1%})" if show_score else ""
        
        return f'''<span class="badge {color_data['class']}" 
                         style="{self.get_inline_style(confidence_score)}"
                         title="Match confidence: {confidence_score:.1%}">
                    {color_data['level'].title()}{score_text}
                   </span>'''
    
    @classmethod
    def load_thresholds_from_settings(cls, settings_data: Optional[str] = None) -> 'ConfidenceColorSystem':
        """
        Load confidence thresholds from checklist settings
        
        Args:
            settings_data: JSON string with threshold settings
            
        Returns:
            ConfidenceColorSystem instance with custom thresholds
        """
        high_threshold = cls.DEFAULT_HIGH_THRESHOLD
        medium_threshold = cls.DEFAULT_MEDIUM_THRESHOLD
        
        if settings_data:
            try:
                settings = json.loads(settings_data)
                high_threshold = settings.get('confidence_high_threshold', high_threshold)
                medium_threshold = settings.get('confidence_medium_threshold', medium_threshold)
            except (json.JSONDecodeError, AttributeError):
                pass  # Use defaults if parsing fails
        
        return cls(high_threshold=high_threshold, medium_threshold=medium_threshold)
    
    def to_settings_dict(self) -> Dict:
        """Export thresholds as settings dictionary"""
        return {
            'confidence_high_threshold': self.high_threshold,
            'confidence_medium_threshold': self.medium_threshold
        }

# Global instance with default thresholds
default_confidence_system = ConfidenceColorSystem()

# CSS for confidence classes
CONFIDENCE_CSS = """
.confidence-high {
    color: #155724 !important;
    background-color: #d4edda !important;
    border: 1px solid #c3e6cb !important;
}

.confidence-medium {
    color: #856404 !important;
    background-color: #fff3cd !important;
    border: 1px solid #ffeaa7 !important;
}

.confidence-low {
    color: #721c24 !important;
    background-color: #f8d7da !important;
    border: 1px solid #f5c6cb !important;
}

.confidence-high:hover {
    opacity: 0.8;
}

.confidence-medium:hover {
    opacity: 0.8;
}

.confidence-low:hover {
    opacity: 0.8;
}
"""