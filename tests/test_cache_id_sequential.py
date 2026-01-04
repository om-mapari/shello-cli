"""
Tests for cache ID sequential generation bug.

Bug: Cache IDs are skipping numbers (cmd_002, cmd_004, cmd_006 instead of cmd_001, cmd_002, cmd_003)
Root cause: Double store() calls in certain code paths.

This test file verifies:
1. OutputCache generates sequential IDs correctly (isolated)
2. OutputManager doesn't double-store
3. BashTool.execute() generates sequential IDs
4. BashTool.execute_stream() generates sequential IDs (suspected bug location)
"""

import pytest
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.tools.bash_tool import BashTool


class TestCacheIdSequential:
    """Tests for sequential cache ID generation."""
    
    def test_output_cache_sequential_ids_isolated(self):
        """Test that OutputCache generates sequential IDs when used directly."""
        cache = OutputCache()
        
        id1 = cache.store("cmd1", "output1")
        id2 = cache.store("cmd2", "output2")
        id3 = cache.store("cmd3", "output3")
        
        assert id1 == "cmd_001", f"First ID should be cmd_001, got {id1}"
        assert id2 == "cmd_002", f"Second ID should be cmd_002, got {id2}"
        assert id3 == "cmd_003", f"Third ID should be cmd_003, got {id3}"
    
    def test_output_manager_sequential_ids(self):
        """Test that OutputManager generates sequential IDs (single store per call)."""
        cache = OutputCache()
        manager = OutputManager(cache=cache)
        
        result1 = manager.process_output("output1", "cmd1")
        result2 = manager.process_output("output2", "cmd2")
        result3 = manager.process_output("output3", "cmd3")
        
        assert result1.cache_id == "cmd_001", f"First ID should be cmd_001, got {result1.cache_id}"
        assert result2.cache_id == "cmd_002", f"Second ID should be cmd_002, got {result2.cache_id}"
        assert result3.cache_id == "cmd_003", f"Third ID should be cmd_003, got {result3.cache_id}"
    
    def test_bash_tool_execute_sequential_ids(self):
        """Test that BashTool.execute() generates sequential IDs."""
        bash_tool = BashTool()
        
        result1 = bash_tool.execute("echo test1")
        result2 = bash_tool.execute("echo test2")
        result3 = bash_tool.execute("echo test3")
        
        # All should succeed
        assert result1.success, f"Command 1 failed: {result1.error}"
        assert result2.success, f"Command 2 failed: {result2.error}"
        assert result3.success, f"Command 3 failed: {result3.error}"
        
        # Check sequential IDs
        assert result1.truncation_info.cache_id == "cmd_001", \
            f"First ID should be cmd_001, got {result1.truncation_info.cache_id}"
        assert result2.truncation_info.cache_id == "cmd_002", \
            f"Second ID should be cmd_002, got {result2.truncation_info.cache_id}"
        assert result3.truncation_info.cache_id == "cmd_003", \
            f"Third ID should be cmd_003, got {result3.truncation_info.cache_id}"
    
    def test_bash_tool_execute_stream_sequential_ids(self):
        """
        Test that BashTool.execute_stream() generates sequential IDs.
        
        This is the suspected bug location - execute_stream() may be calling
        process_output() twice (once in process_stream and once explicitly).
        """
        bash_tool = BashTool()
        
        # Execute streaming commands
        def run_stream(command):
            gen = bash_tool.execute_stream(command)
            # Consume all output
            output_chunks = []
            try:
                while True:
                    chunk = next(gen)
                    output_chunks.append(chunk)
            except StopIteration as e:
                return e.value  # Returns ToolResult
        
        result1 = run_stream("echo stream1")
        result2 = run_stream("echo stream2")
        result3 = run_stream("echo stream3")
        
        # All should succeed
        assert result1.success, f"Stream 1 failed: {result1.error}"
        assert result2.success, f"Stream 2 failed: {result2.error}"
        assert result3.success, f"Stream 3 failed: {result3.error}"
        
        # Check sequential IDs - THIS IS WHERE THE BUG MANIFESTS
        # Bug: IDs skip by 2 (cmd_002, cmd_004, cmd_006)
        # Expected: Sequential (cmd_001, cmd_002, cmd_003)
        assert result1.truncation_info.cache_id == "cmd_001", \
            f"First stream ID should be cmd_001, got {result1.truncation_info.cache_id}"
        assert result2.truncation_info.cache_id == "cmd_002", \
            f"Second stream ID should be cmd_002, got {result2.truncation_info.cache_id}"
        assert result3.truncation_info.cache_id == "cmd_003", \
            f"Third stream ID should be cmd_003, got {result3.truncation_info.cache_id}"
    
    def test_mixed_execute_and_stream_sequential_ids(self):
        """Test that mixing execute() and execute_stream() maintains sequential IDs."""
        bash_tool = BashTool()
        
        def run_stream(command):
            gen = bash_tool.execute_stream(command)
            output_chunks = []
            try:
                while True:
                    chunk = next(gen)
                    output_chunks.append(chunk)
            except StopIteration as e:
                return e.value
        
        # Mix of execute and stream
        result1 = bash_tool.execute("echo exec1")
        result2 = run_stream("echo stream1")
        result3 = bash_tool.execute("echo exec2")
        result4 = run_stream("echo stream2")
        
        # All should succeed
        assert result1.success and result2.success and result3.success and result4.success
        
        # Check sequential IDs
        assert result1.truncation_info.cache_id == "cmd_001", \
            f"ID 1 should be cmd_001, got {result1.truncation_info.cache_id}"
        assert result2.truncation_info.cache_id == "cmd_002", \
            f"ID 2 should be cmd_002, got {result2.truncation_info.cache_id}"
        assert result3.truncation_info.cache_id == "cmd_003", \
            f"ID 3 should be cmd_003, got {result3.truncation_info.cache_id}"
        assert result4.truncation_info.cache_id == "cmd_004", \
            f"ID 4 should be cmd_004, got {result4.truncation_info.cache_id}"


class TestCacheCounterState:
    """Tests for cache counter state tracking."""
    
    def test_cache_counter_after_stores(self):
        """Test that cache counter reflects actual number of stores."""
        cache = OutputCache()
        
        cache.store("cmd1", "output1")
        cache.store("cmd2", "output2")
        cache.store("cmd3", "output3")
        
        stats = cache.get_stats()
        assert stats['next_id'] == 4, f"Next ID should be 4 after 3 stores, got {stats['next_id']}"
        assert stats['total_entries'] == 3, f"Should have 3 entries, got {stats['total_entries']}"
    
    def test_bash_tool_cache_counter_after_executes(self):
        """Test that BashTool's cache counter reflects actual number of commands."""
        bash_tool = BashTool()
        
        bash_tool.execute("echo test1")
        bash_tool.execute("echo test2")
        bash_tool.execute("echo test3")
        
        stats = bash_tool.get_output_cache().get_stats()
        # Should be 4 (next ID after 3 commands)
        # Bug: If double-storing, this would be 7 (next ID after 6 stores)
        assert stats['next_id'] == 4, \
            f"Next ID should be 4 after 3 commands, got {stats['next_id']} (indicates double-storing)"
        assert stats['total_entries'] == 3, \
            f"Should have 3 entries, got {stats['total_entries']}"
    
    def test_bash_tool_stream_cache_counter(self):
        """Test that BashTool's cache counter is correct after streaming commands."""
        bash_tool = BashTool()
        
        def run_stream(command):
            gen = bash_tool.execute_stream(command)
            try:
                while True:
                    next(gen)
            except StopIteration as e:
                return e.value
        
        run_stream("echo stream1")
        run_stream("echo stream2")
        run_stream("echo stream3")
        
        stats = bash_tool.get_output_cache().get_stats()
        # Bug: If double-storing in execute_stream, next_id would be 7 instead of 4
        assert stats['next_id'] == 4, \
            f"Next ID should be 4 after 3 stream commands, got {stats['next_id']} (indicates double-storing)"
