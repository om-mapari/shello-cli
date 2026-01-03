"""Tests for GetCachedOutputTool."""

import pytest
from shello_cli.tools.get_cached_output_tool import GetCachedOutputTool
from shello_cli.tools.output.cache import OutputCache


class TestGetCachedOutputTool:
    """Test suite for GetCachedOutputTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = OutputCache()
        self.tool = GetCachedOutputTool(self.cache)
        
        # Store some test data
        self.test_output = "\n".join([f"Line {i}" for i in range(1, 101)])
        self.cache_id = self.cache.store("test command", self.test_output)
    
    def test_get_full_output(self):
        """Test retrieving full output without line specification."""
        result = self.tool.execute(self.cache_id)
        
        assert result.error is None
        assert result.output == self.test_output
    
    def test_get_first_n_lines(self):
        """Test retrieving first N lines with +N format."""
        result = self.tool.execute(self.cache_id, lines="+10")
        
        assert result.error is None
        expected = "\n".join([f"Line {i}" for i in range(1, 11)])
        assert result.output == expected
    
    def test_get_last_n_lines(self):
        """Test retrieving last N lines with -N format."""
        result = self.tool.execute(self.cache_id, lines="-10")
        
        assert result.error is None
        expected = "\n".join([f"Line {i}" for i in range(91, 101)])
        assert result.output == expected
    
    def test_get_first_and_last_lines(self):
        """Test retrieving first N + last M lines with +N,-M format."""
        result = self.tool.execute(self.cache_id, lines="+5,-5")
        
        assert result.error is None
        # Should have first 5 lines, omission indicator, and last 5 lines
        assert "Line 1" in result.output
        assert "Line 5" in result.output
        assert "Line 96" in result.output
        assert "Line 100" in result.output
        assert "omitted" in result.output.lower()
    
    def test_get_line_range(self):
        """Test retrieving specific line range with N-M format."""
        result = self.tool.execute(self.cache_id, lines="10-20")
        
        assert result.error is None
        # Range is inclusive: lines 10 through 20
        expected = "\n".join([f"Line {i}" for i in range(10, 21)])
        assert result.output == expected
    
    def test_cache_miss_expired(self):
        """Test handling of expired cache entries."""
        # Create cache with very short TTL
        short_cache = OutputCache(ttl_seconds=0)
        tool = GetCachedOutputTool(short_cache)
        
        cache_id = short_cache.store("test", "output")
        
        # Wait a moment for expiration
        import time
        time.sleep(0.1)
        
        result = tool.execute(cache_id)
        
        assert result.error is not None
        assert "Cache miss" in result.error
        assert "expired" in result.error.lower()
    
    def test_cache_miss_invalid_id(self):
        """Test handling of invalid cache ID."""
        result = self.tool.execute("invalid_id")
        
        assert result.error is not None
        assert "Cache miss" in result.error
    
    def test_invalid_cache_id_format(self):
        """Test handling of invalid cache_id format."""
        result = self.tool.execute("")
        
        assert result.error is not None
        assert "Invalid cache_id" in result.error
    
    def test_first_n_exceeds_total(self):
        """Test requesting more first lines than available."""
        result = self.tool.execute(self.cache_id, lines="+200")
        
        assert result.error is None
        # Should return all available lines
        assert result.output == self.test_output
    
    def test_last_n_exceeds_total(self):
        """Test requesting more last lines than available."""
        result = self.tool.execute(self.cache_id, lines="-200")
        
        assert result.error is None
        # Should return all available lines
        assert result.output == self.test_output
    
    def test_line_range_out_of_bounds(self):
        """Test line range that exceeds available lines."""
        result = self.tool.execute(self.cache_id, lines="90-200")
        
        assert result.error is None
        # Should clamp to available range
        expected = "\n".join([f"Line {i}" for i in range(90, 101)])
        assert result.output == expected
    
    def test_safety_limit_applied(self):
        """Test that safety limit is applied to full output retrieval."""
        # Create very large output
        large_output = "x" * 60000  # Exceeds safety limit of 50K
        cache_id = self.cache.store("large command", large_output)
        
        result = self.tool.execute(cache_id)
        
        assert result.error is None
        # Should be truncated
        assert len(result.output) < len(large_output)
        assert "truncated to safety limit" in result.output.lower()
    
    def test_safety_limit_not_applied_with_lines(self):
        """Test that safety limit is not applied when using lines parameter."""
        # Create very large output
        large_output = "\n".join([f"Line {i}" for i in range(1, 10001)])
        cache_id = self.cache.store("large command", large_output)
        
        # Request specific lines - should not apply safety limit
        result = self.tool.execute(cache_id, lines="+10")
        
        assert result.error is None
        expected = "\n".join([f"Line {i}" for i in range(1, 11)])
        assert result.output == expected
    
    def test_empty_output(self):
        """Test handling of empty cached output."""
        cache_id = self.cache.store("empty command", "")
        
        result = self.tool.execute(cache_id)
        
        assert result.error is None
        assert result.output == ""
    
    def test_single_line_output(self):
        """Test handling of single line output."""
        cache_id = self.cache.store("single line", "Single line")
        
        result = self.tool.execute(cache_id, lines="+1")
        
        assert result.error is None
        assert result.output == "Single line"
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        stats = self.tool.get_cache_stats()
        
        assert 'total_entries' in stats
        assert 'total_size_bytes' in stats
        assert 'ttl_seconds' in stats
        assert stats['total_entries'] >= 1  # At least our test entry
