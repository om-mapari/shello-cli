"""Tests for semantic line classification."""

import pytest
from shello_cli.tools.output.semantic import LineClassifier
from shello_cli.tools.output.types import LineImportance


class TestLineClassifier:
    """Tests for LineClassifier."""
    
    def test_classify_critical_lines(self):
        """Test classification of critical lines."""
        classifier = LineClassifier()
        
        critical_lines = [
            "ERROR: Something went wrong",
            "FATAL: System crash",
            "Exception occurred in module",
            "FAILURE: Test failed",
            "panic: runtime error",
            "Traceback (most recent call last):",
            "  at module.function (file.py:123:45)",
        ]
        
        for line in critical_lines:
            importance = classifier.classify_line(line)
            assert importance == LineImportance.CRITICAL, \
                f"Line '{line}' should be classified as CRITICAL"
    
    def test_classify_high_lines(self):
        """Test classification of high importance lines."""
        classifier = LineClassifier()
        
        high_lines = [
            "WARNING: Deprecated function",
            "Success: Operation completed",
            "Done processing",
            "Finished successfully",
            "Summary: 10 tests passed",
            "Total: 100 items",
            "===================================",
            "-----------------------------------",
        ]
        
        for line in high_lines:
            importance = classifier.classify_line(line)
            assert importance == LineImportance.HIGH, \
                f"Line '{line}' should be classified as HIGH"
    
    def test_classify_medium_lines(self):
        """Test classification of medium importance lines."""
        classifier = LineClassifier()
        
        medium_lines = [
            "✓ Test passed",
            "✗ Test failed",
            "❌ Error indicator",
            "[OK] Status check",
            "[FAIL] Validation",
            "PASS: Unit test",
        ]
        
        for line in medium_lines:
            importance = classifier.classify_line(line)
            # Note: Some lines might be CRITICAL if they contain error/fail keywords
            # The emoji/status indicators are MEDIUM, but words take precedence
            assert importance in [LineImportance.MEDIUM, LineImportance.CRITICAL], \
                f"Line '{line}' should be classified as MEDIUM or CRITICAL, got {importance}"
    
    def test_classify_low_lines(self):
        """Test classification of low importance lines."""
        classifier = LineClassifier()
        
        low_lines = [
            "Normal output line",
            "Processing item 1",
            "Loading configuration",
            "Starting service",
        ]
        
        for line in low_lines:
            importance = classifier.classify_line(line)
            assert importance == LineImportance.LOW, \
                f"Line '{line}' should be classified as LOW"
    
    def test_classify_lines_batch(self):
        """Test batch classification of lines."""
        classifier = LineClassifier()
        
        output = """Normal line 1
ERROR: Critical error
Normal line 2
WARNING: Deprecation warning
Normal line 3"""
        
        classified = classifier.classify_lines(output)
        
        assert len(classified) == 5
        assert classified[0][1] == LineImportance.LOW
        assert classified[1][1] == LineImportance.CRITICAL
        assert classified[2][1] == LineImportance.LOW
        assert classified[3][1] == LineImportance.HIGH
        assert classified[4][1] == LineImportance.LOW
    
    def test_get_importance_stats(self):
        """Test importance statistics calculation."""
        classifier = LineClassifier()
        
        output = """Normal line 1
ERROR: Critical error
Normal line 2
WARNING: Warning message
Normal line 3
FAILURE: Another critical
✓ Test passed"""
        
        classified = classifier.classify_lines(output)
        stats = classifier.get_importance_stats(classified)
        
        assert stats["critical"] == 2  # ERROR and FAILURE
        assert stats["high"] == 1      # WARNING
        assert stats["medium"] == 1    # ✓ Test passed
        assert stats["low"] == 3       # Normal lines
    
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        classifier = LineClassifier()
        
        # Test various cases
        assert classifier.classify_line("error: something") == LineImportance.CRITICAL
        assert classifier.classify_line("ERROR: something") == LineImportance.CRITICAL
        assert classifier.classify_line("Error: something") == LineImportance.CRITICAL
        
        assert classifier.classify_line("warning: something") == LineImportance.HIGH
        assert classifier.classify_line("WARNING: something") == LineImportance.HIGH
        assert classifier.classify_line("Warning: something") == LineImportance.HIGH
    
    def test_empty_output(self):
        """Test handling of empty output."""
        classifier = LineClassifier()
        
        classified = classifier.classify_lines("")
        assert len(classified) == 1  # Empty string creates one empty line
        assert classified[0][0] == ""
        assert classified[0][1] == LineImportance.LOW
        
        stats = classifier.get_importance_stats(classified)
        assert stats["critical"] == 0
        assert stats["high"] == 0
        assert stats["medium"] == 0
        assert stats["low"] == 1
