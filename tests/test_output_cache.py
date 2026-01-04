"""
Property-based tests for OutputCache.

Feature: output-management
Tests cache storage, retrieval, TTL expiration, and LRU eviction.
"""

import pytest
import time
from hypothesis import given, strategies as st, settings, assume
from shello_cli.tools.output.cache import OutputCache


class TestOutputCacheProperties:
    """Property-based tests for OutputCache."""
    
    @given(
        command=st.text(min_size=1, max_size=100),
        output=st.text(min_size=0, max_size=10000)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_cache_round_trip(self, command, output):
        """
        Feature: output-management, Property 3: Cache Round-Trip
        
        For any cached output, retrieving with get(cache_id) SHALL return 
        the original full output.
        
        Validates: Requirements 14.1, 15.1
        """
        cache = OutputCache(max_size_mb=10)
        
        # Store output
        cache_id = cache.store(command, output)
        
        # Retrieve output
        retrieved = cache.get(cache_id)
        
        # Should get back exactly what we stored
        assert retrieved == output, \
            f"Cache round-trip failed: stored {len(output)} chars, got {len(retrieved) if retrieved else 0} chars"
        
        # Cache ID should follow sequential format
        assert cache_id.startswith("cmd_"), \
            f"Cache ID should start with 'cmd_', got: {cache_id}"
        
        # Cache ID should be 3-digit padded
        assert len(cache_id) == 7, \
            f"Cache ID should be 7 chars (cmd_XXX), got: {cache_id}"


class TestOutputCacheTTL:
    """Tests for cache persistence (no TTL expiration)."""
    
    def test_no_ttl_expiration(self):
        """Test that entries persist indefinitely (no TTL)."""
        cache = OutputCache(max_size_mb=10)
        
        cache_id = cache.store("test command", "test output")
        
        # Should be retrievable immediately
        assert cache.get(cache_id) == "test output"
        
        # Wait a bit
        time.sleep(1.1)
        
        # Should still be available (no TTL expiration)
        assert cache.get(cache_id) == "test output"
    
    def test_cache_persists_across_gets(self):
        """Test that entries persist across multiple get operations."""
        cache = OutputCache(max_size_mb=10)
        
        cache_id = cache.store("test command", "test output")
        
        # Multiple gets should all succeed
        for _ in range(5):
            time.sleep(0.1)
            assert cache.get(cache_id) == "test output"


class TestOutputCacheLRU:
    """Tests for LRU eviction."""
    
    def test_lru_eviction_on_size_limit(self):
        """Test that LRU eviction occurs when size limit is exceeded."""
        # Small cache: 1KB max
        cache = OutputCache(max_size_mb=0.001)
        
        # Store first entry (should fit)
        cache_id_1 = cache.store("cmd1", "x" * 500)  # 500 bytes
        
        # Store second entry (should fit)
        cache_id_2 = cache.store("cmd2", "y" * 500)  # 500 bytes
        
        # Store third entry (should trigger eviction of first)
        cache_id_3 = cache.store("cmd3", "z" * 500)  # 500 bytes
        
        # First entry should be evicted (LRU)
        assert cache.get(cache_id_1) is None, "Oldest entry should be evicted"
        
        # Second and third should still exist
        assert cache.get(cache_id_2) == "y" * 500
        assert cache.get(cache_id_3) == "z" * 500
    
    def test_lru_access_updates_order(self):
        """Test that accessing an entry updates its position in LRU order."""
        # Small cache: 1KB max
        cache = OutputCache(max_size_mb=0.001)
        
        # Store two entries
        cache_id_1 = cache.store("cmd1", "x" * 500)
        cache_id_2 = cache.store("cmd2", "y" * 500)
        
        # Access first entry (moves it to end of LRU)
        cache.get(cache_id_1)
        
        # Store third entry (should evict second, not first)
        cache_id_3 = cache.store("cmd3", "z" * 500)
        
        # First should still exist (was accessed recently)
        assert cache.get(cache_id_1) == "x" * 500
        
        # Second should be evicted (was LRU)
        assert cache.get(cache_id_2) is None
        
        # Third should exist
        assert cache.get(cache_id_3) == "z" * 500


class TestOutputCacheLineSelection:
    """Tests for line selection functionality."""
    
    def test_get_lines_first_n(self):
        """Test getting first N lines with +N format."""
        cache = OutputCache()
        output = "line1\nline2\nline3\nline4\nline5"
        cache_id = cache.store("test", output)
        
        result = cache.get_lines(cache_id, "+3")
        assert result == "line1\nline2\nline3"
    
    def test_get_lines_last_n(self):
        """Test getting last N lines with -N format."""
        cache = OutputCache()
        output = "line1\nline2\nline3\nline4\nline5"
        cache_id = cache.store("test", output)
        
        result = cache.get_lines(cache_id, "-2")
        assert result == "line4\nline5"
    
    def test_get_lines_first_and_last(self):
        """Test getting first N and last M lines with +N,-M format."""
        cache = OutputCache()
        output = "line1\nline2\nline3\nline4\nline5\nline6\nline7"
        cache_id = cache.store("test", output)
        
        result = cache.get_lines(cache_id, "+2,-2")
        assert "line1" in result
        assert "line2" in result
        assert "line6" in result
        assert "line7" in result
        assert "omitted" in result.lower()
    
    def test_get_lines_range(self):
        """Test getting line range with N-M format."""
        cache = OutputCache()
        output = "line1\nline2\nline3\nline4\nline5"
        cache_id = cache.store("test", output)
        
        result = cache.get_lines(cache_id, "2-4")
        assert result == "line2\nline3\nline4"
    
    def test_get_lines_invalid_cache_id(self):
        """Test that invalid cache ID returns None."""
        cache = OutputCache()
        result = cache.get_lines("invalid_id", "+10")
        assert result is None


class TestOutputCacheSequentialIDs:
    """Tests for sequential cache ID generation."""
    
    def test_sequential_ids(self):
        """Test that cache IDs are sequential."""
        cache = OutputCache()
        
        id1 = cache.store("cmd1", "output1")
        id2 = cache.store("cmd2", "output2")
        id3 = cache.store("cmd3", "output3")
        
        assert id1 == "cmd_001"
        assert id2 == "cmd_002"
        assert id3 == "cmd_003"
    
    def test_id_counter_increments(self):
        """Test that counter increments and resets on clear."""
        cache = OutputCache(max_size_mb=10)
        
        id1 = cache.store("cmd1", "output1")
        assert id1 == "cmd_001"
        
        id2 = cache.store("cmd2", "output2")
        assert id2 == "cmd_002"
        
        # Clear cache (simulates /new command)
        cache.clear()
        
        # Counter should reset after clear
        id3 = cache.store("cmd3", "output3")
        assert id3 == "cmd_001"  # Resets to 001


class TestOutputCacheStats:
    """Tests for cache statistics."""
    
    def test_get_stats(self):
        """Test that stats are accurate."""
        cache = OutputCache(max_size_mb=10)
        
        # Empty cache
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
        assert stats['total_size_bytes'] == 0
        
        # Add entries
        cache.store("cmd1", "x" * 100)
        cache.store("cmd2", "y" * 200)
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['total_size_bytes'] == 300
        assert stats['next_id'] == 3
    
    def test_clear(self):
        """Test that clear removes all entries and resets counter."""
        cache = OutputCache()
        
        cache.store("cmd1", "output1")
        cache.store("cmd2", "output2")
        
        assert cache.get_stats()['total_entries'] == 2
        
        cache.clear()
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
        assert stats['total_size_bytes'] == 0
        assert stats['next_id'] == 1  # Counter reset
