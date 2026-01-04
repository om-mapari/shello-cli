"""
Tests for output utility functions.

Tests the strip_line_padding function that removes PowerShell column padding.
"""

import pytest
from shello_cli.utils.output_utils import strip_line_padding


class TestStripLinePadding:
    """Tests for strip_line_padding function."""
    
    def test_strips_trailing_whitespace_from_each_line(self):
        """Test that trailing whitespace is stripped from each line."""
        # Simulated PowerShell output with padding
        padded_output = "Name          \nfile1.txt     \nfile2.txt     \n"
        
        result = strip_line_padding(padded_output)
        
        assert result == "Name\nfile1.txt\nfile2.txt\n"
    
    def test_preserves_leading_whitespace(self):
        """Test that leading whitespace (indentation) is preserved."""
        output = "  indented line    \n    more indented    \n"
        
        result = strip_line_padding(output)
        
        assert result == "  indented line\n    more indented\n"
    
    def test_handles_empty_string(self):
        """Test that empty string returns empty string."""
        result = strip_line_padding("")
        
        assert result == ""
    
    def test_handles_none(self):
        """Test that None returns None."""
        result = strip_line_padding(None)
        
        assert result is None
    
    def test_handles_no_trailing_whitespace(self):
        """Test that output without trailing whitespace is unchanged."""
        output = "line1\nline2\nline3"
        
        result = strip_line_padding(output)
        
        assert result == output
    
    def test_handles_mixed_whitespace(self):
        """Test handling of mixed spaces and tabs."""
        output = "line1   \t  \nline2\t\t\nline3  "
        
        result = strip_line_padding(output)
        
        assert result == "line1\nline2\nline3"
    
    def test_powershell_directory_listing_simulation(self):
        """Test with simulated PowerShell directory listing format."""
        # Simulated PowerShell Get-ChildItem output with column padding
        padded = """
    Directory: C:\\REPO\\test                                                    

Mode                 LastWriteTime         Length Name                          
----                 -------------         ------ ----                          
d-----        01-01-2026  12:00 PM                folder1                       
-a----        01-01-2026  12:00 PM           1234 file1.txt                     
-a----        01-01-2026  12:00 PM           5678 file2.txt                     
"""
        
        result = strip_line_padding(padded)
        
        # Verify no trailing spaces on any line
        for line in result.split('\n'):
            assert line == line.rstrip(), f"Line still has trailing whitespace: '{line}'"
    
    def test_reduces_character_count(self):
        """Test that stripping reduces character count significantly."""
        # Create output with 50 chars of padding per line (10 lines)
        padded_lines = ["content" + " " * 50 for _ in range(10)]
        padded_output = "\n".join(padded_lines)
        
        result = strip_line_padding(padded_output)
        
        # Original: 10 lines * (7 content + 50 padding) + 9 newlines = 579 chars
        # After: 10 lines * 7 content + 9 newlines = 79 chars
        assert len(result) < len(padded_output)
        assert len(result) == 79  # 10 * 7 + 9 newlines
        assert len(padded_output) == 579
    
    def test_single_line_no_newline(self):
        """Test single line without trailing newline."""
        output = "single line with spaces   "
        
        result = strip_line_padding(output)
        
        assert result == "single line with spaces"
    
    def test_only_whitespace_lines(self):
        """Test lines that are only whitespace become empty."""
        output = "   \n\t\t\n     \n"
        
        result = strip_line_padding(output)
        
        assert result == "\n\n\n"
