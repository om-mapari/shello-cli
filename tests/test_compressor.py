"""Property-based tests for ProgressBarCompressor.

Feature: output-management
Property 5: Progress Bar Compression Idempotence
Validates: Requirements 17.2, 17.3
"""

import pytest
from hypothesis import given, strategies as st

from shello_cli.tools.output.compressor import ProgressBarCompressor


class TestProgressBarCompressor:
    """Tests for ProgressBarCompressor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compressor = ProgressBarCompressor()
    
    # =========================================================================
    # Unit Tests
    # =========================================================================
    
    def test_empty_output(self):
        """Test compression of empty output."""
        output, stats = self.compressor.compress("")
        
        assert output == ""
        assert stats.lines_before == 0
        assert stats.lines_after == 0
        assert stats.lines_saved == 0
        assert stats.sequences_compressed == 0
    
    def test_no_progress_bars(self):
        """Test output with no progress bars remains unchanged."""
        output = "Line 1\nLine 2\nLine 3"
        compressed, stats = self.compressor.compress(output)
        
        assert compressed == output
        assert stats.lines_before == 3
        assert stats.lines_after == 3
        assert stats.lines_saved == 0
        assert stats.sequences_compressed == 0
    
    def test_single_progress_sequence(self):
        """Test compression of a single progress sequence."""
        output = """Starting download
Downloading... 10%
Downloading... 50%
Downloading... 100%
Download complete"""
        
        compressed, stats = self.compressor.compress(output)
        
        # Should keep first line, last progress line, and final line
        lines = compressed.split('\n')
        assert "Starting download" in lines
        assert "Downloading... 100%" in lines
        assert "Download complete" in lines
        assert "Downloading... 10%" not in lines
        assert "Downloading... 50%" not in lines
        
        assert stats.lines_before == 5
        assert stats.lines_after == 3
        assert stats.lines_saved == 2
        assert stats.sequences_compressed == 1
    
    def test_multiple_progress_sequences(self):
        """Test compression of multiple separate progress sequences."""
        output = """Task 1 starting
[####      ] 40%
[########  ] 80%
[##########] 100%
Task 1 complete
Task 2 starting
[##        ] 20%
[######    ] 60%
[##########] 100%
Task 2 complete"""
        
        compressed, stats = self.compressor.compress(output)
        
        lines = compressed.split('\n')
        assert "Task 1 starting" in lines
        assert "[##########] 100%" in compressed  # Should appear twice (once per sequence)
        assert "Task 1 complete" in lines
        assert "Task 2 starting" in lines
        assert "Task 2 complete" in lines
        
        # Should have removed intermediate progress lines
        assert "[####      ] 40%" not in lines
        assert "[########  ] 80%" not in lines
        assert "[##        ] 20%" not in lines
        assert "[######    ] 60%" not in lines
        
        assert stats.sequences_compressed == 2
        assert stats.lines_saved > 0
    
    def test_spinner_characters(self):
        """Test compression of spinner progress indicators."""
        output = """Processing...
⠋ Loading
⠙ Loading
⠹ Loading
⠸ Loading
Complete"""
        
        compressed, stats = self.compressor.compress(output)
        
        lines = compressed.split('\n')
        assert "Processing..." in lines
        assert "Complete" in lines
        # Should keep only the last spinner line
        assert lines.count("⠸ Loading") == 1
        
        assert stats.sequences_compressed == 1
        assert stats.lines_saved > 0
    
    def test_percentage_patterns(self):
        """Test compression of percentage-based progress."""
        output = """Installing packages
npm install 25%
npm install 50%
npm install 75%
npm install 100%
Installation complete"""
        
        compressed, stats = self.compressor.compress(output)
        
        lines = compressed.split('\n')
        assert "Installing packages" in lines
        assert "npm install 100%" in lines
        assert "Installation complete" in lines
        assert "npm install 25%" not in lines
        assert "npm install 50%" not in lines
        assert "npm install 75%" not in lines
        
        assert stats.sequences_compressed == 1
    
    def test_download_progress_pattern(self):
        """Test compression of download progress patterns."""
        output = """Fetching dependencies
downloading 1/10
downloading 5/10
downloading 10/10
All dependencies fetched"""
        
        compressed, stats = self.compressor.compress(output)
        
        lines = compressed.split('\n')
        assert "Fetching dependencies" in lines
        assert "downloading 10/10" in lines
        assert "All dependencies fetched" in lines
        assert "downloading 1/10" not in lines
        assert "downloading 5/10" not in lines
        
        assert stats.sequences_compressed == 1
    
    # =========================================================================
    # Property-Based Tests
    # =========================================================================
    
    @given(st.text())
    def test_property_compression_idempotence(self, output: str):
        """Property 5: Progress Bar Compression Idempotence.
        
        For any output, compressing twice SHALL produce the same result
        as compressing once.
        
        Feature: output-management
        Property 5: Progress Bar Compression Idempotence
        Validates: Requirements 17.2, 17.3
        """
        # Compress once
        compressed_once, stats_once = self.compressor.compress(output)
        
        # Compress the result again
        compressed_twice, stats_twice = self.compressor.compress(compressed_once)
        
        # Results should be identical (idempotence)
        assert compressed_once == compressed_twice, \
            "Compressing twice should produce same result as compressing once"
        
        # Second compression should not save any lines
        # (the output is already in its compressed form)
        assert stats_twice.lines_saved == 0, \
            "Second compression should not save any lines"
    
    @given(
        st.lists(
            st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=50
        )
    )
    def test_property_preserves_non_progress_lines(self, lines: list):
        """Property: Non-progress lines are always preserved.
        
        For any list of non-progress lines, compression should preserve
        all of them in the same order.
        """
        # Filter out any lines that might accidentally match progress patterns
        # by using simple text without numbers or special characters
        safe_lines = [f"Line {i}: text" for i in range(len(lines))]
        output = '\n'.join(safe_lines)
        
        compressed, stats = self.compressor.compress(output)
        
        # All non-progress lines should be preserved
        compressed_lines = compressed.split('\n') if compressed else []
        assert len(compressed_lines) == len(safe_lines), \
            "All non-progress lines should be preserved"
        
        for original, compressed_line in zip(safe_lines, compressed_lines):
            assert original == compressed_line, \
                "Non-progress lines should remain unchanged"
    
    @given(
        st.integers(min_value=2, max_value=100)
    )
    def test_property_progress_sequence_reduces_to_one(self, sequence_length: int):
        """Property: Progress sequence reduces to final state.
        
        For any sequence of progress lines, compression should keep only
        the last line (final state).
        """
        # Create a sequence of progress lines
        progress_lines = [f"Progress {i}%" for i in range(sequence_length)]
        output = '\n'.join(progress_lines)
        
        compressed, stats = self.compressor.compress(output)
        
        # Should keep only the last progress line
        compressed_lines = compressed.split('\n')
        assert len(compressed_lines) == 1, \
            "Progress sequence should reduce to single line"
        assert compressed_lines[0] == progress_lines[-1], \
            "Should keep the last line of the sequence"
        
        assert stats.sequences_compressed == 1
        assert stats.lines_saved == sequence_length - 1
