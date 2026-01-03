"""Semantic line classification for intelligent truncation."""

import re
from typing import List, Tuple
from .types import LineImportance
from ...constants import IMPORTANCE_PATTERNS


class LineClassifier:
    """
    Classifies output lines by importance level.
    
    Applies to ALL output types - even list/search commands might have errors.
    """
    
    def __init__(self):
        """Initialize classifier with patterns from constants."""
        # Compile patterns for efficiency
        self.critical_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in IMPORTANCE_PATTERNS["critical"]
        ]
        self.high_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in IMPORTANCE_PATTERNS["high"]
        ]
        self.medium_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in IMPORTANCE_PATTERNS["medium"]
        ]
    
    def classify_line(self, line: str) -> LineImportance:
        """
        Classify a single line by importance.
        
        Args:
            line: Line of output to classify
        
        Returns:
            LineImportance level (CRITICAL, HIGH, MEDIUM, or LOW)
        """
        # Check CRITICAL patterns first (highest priority)
        for pattern in self.critical_patterns:
            if pattern.search(line):
                return LineImportance.CRITICAL
        
        # Check HIGH patterns
        for pattern in self.high_patterns:
            if pattern.search(line):
                return LineImportance.HIGH
        
        # Check MEDIUM patterns
        for pattern in self.medium_patterns:
            if pattern.search(line):
                return LineImportance.MEDIUM
        
        # Default to LOW
        return LineImportance.LOW
    
    def classify_lines(self, output: str) -> List[Tuple[str, LineImportance]]:
        """
        Classify all lines in output.
        
        Args:
            output: Full output string
        
        Returns:
            List of (line, importance) tuples
        """
        lines = output.split('\n')
        return [(line, self.classify_line(line)) for line in lines]
    
    def get_importance_stats(self, classified_lines: List[Tuple[str, LineImportance]]) -> dict:
        """
        Get statistics about line importance distribution.
        
        Args:
            classified_lines: List of (line, importance) tuples
        
        Returns:
            Dict with counts for each importance level
        """
        stats = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for _, importance in classified_lines:
            if importance == LineImportance.CRITICAL:
                stats["critical"] += 1
            elif importance == LineImportance.HIGH:
                stats["high"] += 1
            elif importance == LineImportance.MEDIUM:
                stats["medium"] += 1
            else:
                stats["low"] += 1
        
        return stats
