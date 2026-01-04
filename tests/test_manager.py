"""Tests for OutputManager orchestrator."""

import json
import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.tools.output.manager import OutputManager
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from shello_cli.tools.output.types import OutputType
from shello_cli.types import ToolResult


class TestOutputManager:
    """Test suite for OutputManager."""
    
    def test_basic_output_processing(self):
        """Test basic output processing without truncation."""
        manager = OutputManager()
        output = "Hello, world!"
        command = "echo 'Hello, world!'"
        
        result = manager.process_output(output, command)
        
        assert result.output == output
        assert not result.was_truncated
        assert result.cache_id is not None
        assert result.cache_id.startswith("cmd_")
    
    def test_json_detection_and_analyzer_usage(self):
        """Test that large JSON triggers json_analyzer_tool."""
        # Create a large JSON that exceeds 20K chars
        large_json = json.dumps({
            "items": [{"id": i, "name": f"item_{i}", "data": "x" * 100} for i in range(300)]
        }, indent=2)
        
        assert len(large_json) > 20000, "Test JSON should exceed 20K chars"
        
        # Create manager with json_analyzer
        analyzer = JsonAnalyzerTool()
        manager = OutputManager(json_analyzer=analyzer)
        
        command = "aws lambda list-functions"
        result = manager.process_output(large_json, command)
        
        # Should be truncated and use json_analyzer
        assert result.was_truncated
        assert result.used_json_analyzer
        assert "jq path" in result.output
        assert result.cache_id is not None
        assert "json_analyzer_tool" in result.summary.lower()
    
    def test_json_without_analyzer_falls_back(self):
        """Test that JSON without analyzer falls back to text truncation."""
        # Create a large JSON that exceeds 20K chars
        large_json = json.dumps({
            "items": [{"id": i, "name": f"item_{i}", "data": "x" * 100} for i in range(300)]
        }, indent=2)
        
        # Create manager WITHOUT json_analyzer
        manager = OutputManager(json_analyzer=None)
        
        command = "aws lambda list-functions"
        result = manager.process_output(large_json, command)
        
        # Should be truncated but NOT use json_analyzer
        assert result.was_truncated
        assert not result.used_json_analyzer
        assert result.cache_id is not None
    
    def test_invalid_json_falls_back_to_text(self):
        """Test that invalid JSON falls back to text truncation."""
        # Create invalid JSON that exceeds 20K chars
        invalid_json = '{"invalid": "json"' + ("x" * 20000)
        
        analyzer = JsonAnalyzerTool()
        manager = OutputManager(json_analyzer=analyzer)
        
        command = "cat broken.json"
        result = manager.process_output(invalid_json, command)
        
        # Should be truncated but NOT use json_analyzer (invalid JSON)
        assert result.was_truncated
        assert not result.used_json_analyzer
        assert result.cache_id is not None
    
    def test_small_json_not_analyzed(self):
        """Test that small JSON is not analyzed."""
        small_json = json.dumps({"key": "value", "number": 42})
        
        analyzer = JsonAnalyzerTool()
        manager = OutputManager(json_analyzer=analyzer)
        
        command = "echo '{\"key\": \"value\"}'"
        result = manager.process_output(small_json, command)
        
        # Should NOT be truncated or analyzed
        assert not result.was_truncated
        assert not result.used_json_analyzer
        assert result.output == small_json
    
    def test_caching_integration(self):
        """Test that output is cached correctly."""
        cache = OutputCache()
        manager = OutputManager(cache=cache)
        
        output = "Test output"
        command = "echo 'Test'"
        
        result = manager.process_output(output, command)
        
        # Should be cached
        cached = cache.get(result.cache_id)
        assert cached == output
    
    def test_progress_bar_compression(self):
        """Test that progress bars are compressed."""
        output_with_progress = "\n".join([
            "Downloading...",
            "Progress: 10%",
            "Progress: 20%",
            "Progress: 30%",
            "Progress: 100%",
            "Done!"
        ])
        
        manager = OutputManager()
        command = "npm install"
        
        result = manager.process_output(output_with_progress, command)
        
        # Should have compression stats
        assert result.compression_stats is not None
        if result.compression_stats.lines_saved > 0:
            assert "compressed" in result.summary.lower()


class TestJSONAnalyzerFallback:
    """Property-based tests for JSON analyzer fallback behavior."""
    
    @given(
        json_size=st.integers(min_value=20001, max_value=30000),
        has_analyzer=st.booleans()
    )
    @settings(max_examples=5, deadline=None)
    def test_property_json_analyzer_fallback(self, json_size, has_analyzer):
        """
        Property 7: JSON Analyzer Fallback
        
        For any JSON output exceeding limit (20K chars):
        - If json_analyzer is available, it SHALL be used and jq paths returned
        - If json_analyzer is NOT available, SHALL fall back to text truncation
        
        Validates: Requirements 5.1, 5.2
        """
        # Generate valid JSON of specified size
        # Each item is roughly 100 chars, so we need more items to reach the target size
        items_needed = (json_size // 100) + 50  # Add buffer to ensure we exceed the limit
        large_json = json.dumps({
            "items": [{"id": i, "data": "x" * 50} for i in range(items_needed)]
        }, indent=2)
        
        # Ensure it exceeds 20K by adding more items if needed
        while len(large_json) < 20001:
            items_needed += 10
            large_json = json.dumps({
                "items": [{"id": i, "data": "x" * 50} for i in range(items_needed)]
            }, indent=2)
        
        # Verify the JSON is actually large enough
        assert len(large_json) > 20000, f"Generated JSON is only {len(large_json)} chars"
        
        # Create manager with or without analyzer
        analyzer = JsonAnalyzerTool() if has_analyzer else None
        manager = OutputManager(json_analyzer=analyzer)
        
        command = "cat data.json"
        result = manager.process_output(large_json, command)
        
        # Should always be truncated (exceeds limit)
        assert result.was_truncated, f"JSON exceeding 20K should be truncated (size: {len(large_json)})"
        
        if has_analyzer:
            # Should use json_analyzer
            assert result.used_json_analyzer, "Should use json_analyzer when available"
            assert "jq path" in result.output or "jq" in result.output.lower(), \
                "Should return jq paths when analyzer is used"
            assert "json_analyzer" in result.summary.lower(), \
                "Summary should mention json_analyzer usage"
        else:
            # Should fall back to text truncation
            assert not result.used_json_analyzer, "Should NOT use json_analyzer when unavailable"
            # Output should be truncated text, not jq paths
            assert "jq path" not in result.output, \
                "Should not return jq paths without analyzer"
        
        # Should always have cache_id
        assert result.cache_id is not None, "Should always cache output"
        assert result.cache_id.startswith("cmd_"), "Cache ID should have correct format"
    
    @given(
        valid_json=st.booleans()
    )
    @settings(max_examples=5, deadline=None)
    def test_property_invalid_json_fallback(self, valid_json):
        """
        Property: Invalid JSON Fallback
        
        For any output that looks like JSON but is invalid:
        - SHALL fall back to text truncation
        - SHALL NOT use json_analyzer
        - SHALL still cache the output
        
        Validates: Requirements 5.1, 5.2
        """
        base_size = 25000  # Fixed size to avoid timeout
        
        if valid_json:
            # Create valid JSON
            output = json.dumps({
                "data": "x" * (base_size // 2)
            })
        else:
            # Create invalid JSON (looks like JSON but isn't)
            output = '{"invalid": "json"' + ("x" * base_size)
        
        analyzer = JsonAnalyzerTool()
        manager = OutputManager(json_analyzer=analyzer)
        
        command = "cat file.json"
        result = manager.process_output(output, command)
        
        if valid_json and len(output) > 20000:
            # Valid large JSON should use analyzer
            assert result.used_json_analyzer, "Valid large JSON should use analyzer"
        else:
            # Invalid JSON should fall back to text truncation
            assert not result.used_json_analyzer, "Invalid JSON should not use analyzer"
        
        # Should always cache
        assert result.cache_id is not None
        
        # Should always be truncated if exceeds limit
        if len(output) > 20000:
            assert result.was_truncated


class TestSummaryCompleteness:
    """Property-based tests for truncation summary completeness."""
    
    @given(
        output_size=st.integers(min_value=10000, max_value=50000),
        command_type=st.sampled_from(['list', 'install', 'log', 'test', 'build'])
    )
    @settings(max_examples=5, deadline=None)
    def test_property_summary_completeness(self, output_size, command_type):
        """
        Property 8: Summary Completeness
        
        For any truncated output, the summary SHALL contain:
        - cache_id
        - statistics (total/shown chars and lines)
        - strategy used
        - optimizations applied (if any)
        - suggestion for get_cached_output with appropriate line range
        
        Validates: Requirements 12.1-12.7, 19.1-19.6
        """
        # Generate output that will be truncated
        output = "Line " + str(output_size) + "\n" + ("x" * output_size)
        
        # Map command type to actual command
        command_map = {
            'list': 'ls -la',
            'install': 'npm install',
            'log': 'tail -f app.log',
            'test': 'pytest',
            'build': 'npm run build'
        }
        command = command_map[command_type]
        
        manager = OutputManager()
        result = manager.process_output(output, command)
        
        # If truncated, summary must be complete
        if result.was_truncated:
            summary = result.summary
            
            # Must have cache_id
            assert result.cache_id is not None, "Truncated output must have cache_id"
            assert result.cache_id in summary, "Summary must contain cache_id"
            assert result.cache_id.startswith("cmd_"), "Cache ID must have correct format"
            
            # Must have statistics
            assert "Total:" in summary, "Summary must show total stats"
            assert "Shown:" in summary, "Summary must show shown stats"
            assert "chars" in summary, "Summary must mention characters"
            assert "lines" in summary, "Summary must mention lines"
            
            # Must show actual numbers
            assert str(result.total_chars) in summary or f"{result.total_chars:,}" in summary, \
                "Summary must show total_chars"
            assert str(result.shown_chars) in summary or f"{result.shown_chars:,}" in summary, \
                "Summary must show shown_chars"
            
            # Must have strategy
            assert "Strategy:" in summary, "Summary must show strategy"
            strategy_name = result.strategy.value.replace('_', ' ').upper()
            assert strategy_name in summary, f"Summary must show strategy name: {strategy_name}"
            
            # Must have cache ID (no expiration - persists for conversation)
            assert "Cache ID:" in summary, "Summary must show cache ID"
            assert result.cache_id in summary, f"Summary must show cache_id: {result.cache_id}"
            
            # Must have suggestion for get_cached_output
            assert "get_cached_output" in summary, "Summary must suggest get_cached_output"
            assert "cache_id=" in summary, "Summary must show how to use cache_id"
            assert "lines=" in summary, "Summary must show lines parameter"
            
            # Suggestion should be appropriate for command type
            if command_type in ['install', 'build', 'test']:
                # Should suggest last N lines
                assert '"-' in summary or "'-" in summary, \
                    f"For {command_type}, should suggest last N lines"
            elif command_type == 'log':
                # Should suggest last N lines
                assert '"-' in summary or "'-" in summary, \
                    "For logs, should suggest last N lines"
            elif command_type == 'list':
                # Should suggest first N lines
                assert '"+' in summary or "'+", \
                    "For lists, should suggest first N lines"
    
    @given(
        has_compression=st.booleans(),
        has_semantic=st.booleans()
    )
    @settings(max_examples=5, deadline=None)
    def test_property_summary_optimizations(self, has_compression, has_semantic):
        """
        Property: Summary shows optimizations applied
        
        For any truncated output with optimizations:
        - If progress bars compressed, summary SHALL mention it
        - If semantic truncation applied, summary SHALL show importance counts
        
        Validates: Requirements 12.5, 19.4
        """
        # Create output with or without progress bars
        if has_compression:
            output = "\n".join([
                "Starting...",
                "Progress: 10%",
                "Progress: 20%",
                "Progress: 30%",
                "Progress: 100%",
                "Done!"
            ] + ["x" * 100 for _ in range(100)])  # Make it large enough to truncate
        else:
            output = "\n".join(["Line " + str(i) for i in range(200)])
        
        # Add critical lines if semantic is tested
        if has_semantic:
            output += "\nERROR: Something failed\nWARNING: Check this\n"
        
        manager = OutputManager()
        command = "npm install"  # Use install to trigger truncation
        result = manager.process_output(output, command)
        
        if result.was_truncated:
            summary = result.summary
            
            # Check compression mention
            if has_compression and result.compression_stats and result.compression_stats.lines_saved > 0:
                assert "compressed" in summary.lower(), \
                    "Summary should mention compression when applied"
                assert "saved" in summary.lower(), \
                    "Summary should mention lines saved"
            
            # Check semantic stats
            if has_semantic and result.semantic_stats:
                critical = result.semantic_stats.get('critical', 0)
                high = result.semantic_stats.get('high', 0)
                
                if critical > 0 or high > 0:
                    assert "Semantic:" in summary or "semantic" in summary.lower(), \
                        "Summary should mention semantic truncation when applied"
                    
                    if critical > 0:
                        assert "critical" in summary.lower(), \
                            "Summary should show critical line count"
    
    def test_summary_format_consistency(self):
        """Test that summary format is consistent and well-formatted."""
        output = "x" * 10000
        command = "echo test"
        
        manager = OutputManager()
        result = manager.process_output(output, command)
        
        if result.was_truncated:
            summary = result.summary
            
            # Should have clear section markers
            assert "─" in summary, "Summary should have visual separators"
            assert "📊" in summary or "OUTPUT SUMMARY" in summary, \
                "Summary should have clear header"
            
            # Should have cache icon
            assert "💾" in summary or "Cache ID:" in summary, \
                "Summary should clearly mark cache ID"
            
            # Should have suggestion icon
            assert "💡" in summary or "Use get_cached_output" in summary, \
                "Summary should clearly mark suggestion"
    
    def test_json_summary_format(self):
        """Test that JSON analyzer summary has correct format."""
        # Create large JSON
        large_json = json.dumps({
            "items": [{"id": i, "data": "x" * 100} for i in range(300)]
        }, indent=2)
        
        analyzer = JsonAnalyzerTool()
        manager = OutputManager(json_analyzer=analyzer)
        
        command = "cat data.json"
        result = manager.process_output(large_json, command)
        
        if result.used_json_analyzer:
            summary = result.summary
            
            # Must mention json_analyzer_tool
            assert "json_analyzer" in summary.lower(), \
                "JSON summary must mention json_analyzer_tool"
            
            # Must have cache_id
            assert result.cache_id in summary, \
                "JSON summary must contain cache_id"
            
            # Must suggest get_cached_output for raw JSON
            assert "get_cached_output" in summary, \
                "JSON summary must suggest get_cached_output"
            
            # Should mention jq paths
            assert "jq" in summary.lower(), \
                "JSON summary should mention jq paths"


class TestStreamingOutput:
    """Tests for streaming output processing."""
    
    def test_basic_streaming(self):
        """Test basic streaming output processing."""
        manager = OutputManager()
        
        # Create a simple stream
        def generate_stream():
            yield "Line 1\n"
            yield "Line 2\n"
            yield "Line 3\n"
        
        command = "echo test"
        
        # Process stream
        chunks = list(manager.process_stream(generate_stream(), command))
        
        # Should yield all chunks
        assert len(chunks) >= 3, "Should yield at least the input chunks"
        assert "Line 1\n" in chunks
        assert "Line 2\n" in chunks
        assert "Line 3\n" in chunks
    
    def test_streaming_with_truncation(self):
        """Test that streaming accumulates and truncates at the end."""
        manager = OutputManager()
        
        # Create a large stream that will be truncated
        def generate_large_stream():
            for i in range(200):
                yield f"Line {i}: " + ("x" * 100) + "\n"
        
        command = "cat large_file.txt"
        
        # Process stream
        chunks = list(manager.process_stream(generate_large_stream(), command))
        
        # Should yield all original chunks plus summary at end
        assert len(chunks) > 200, "Should yield all chunks plus summary"
        
        # Last chunk should be the summary (if truncated)
        last_chunk = chunks[-1]
        if "OUTPUT SUMMARY" in last_chunk or "📊" in last_chunk:
            # Was truncated - check summary
            assert "cache_id" in last_chunk.lower() or "cmd_" in last_chunk
            assert "get_cached_output" in last_chunk
    
    def test_streaming_caches_full_output(self):
        """Test that streaming caches the full accumulated output."""
        cache = OutputCache()
        manager = OutputManager(cache=cache)
        
        # Create a stream
        def generate_stream():
            yield "Part 1\n"
            yield "Part 2\n"
            yield "Part 3\n"
        
        command = "echo test"
        
        # Process stream and collect chunks
        chunks = list(manager.process_stream(generate_stream(), command))
        
        # Extract cache_id from summary (if present)
        cache_id = None
        for chunk in chunks:
            if "cmd_" in chunk:
                # Try to extract cache_id
                import re
                match = re.search(r'cmd_\d+', chunk)
                if match:
                    cache_id = match.group(0)
                    break
        
        if cache_id:
            # Verify full output is cached
            cached = cache.get(cache_id)
            assert cached is not None, "Full output should be cached"
            assert "Part 1" in cached
            assert "Part 2" in cached
            assert "Part 3" in cached
    
    def test_streaming_user_sees_normal_output(self):
        """Test that user sees output normally during streaming."""
        manager = OutputManager()
        
        # Create a stream
        def generate_stream():
            yield "Starting...\n"
            yield "Processing...\n"
            yield "Done!\n"
        
        command = "npm install"
        
        # Process stream
        chunks = list(manager.process_stream(generate_stream(), command))
        
        # User should see all original chunks in order
        # (summary comes at the end)
        assert chunks[0] == "Starting...\n"
        assert chunks[1] == "Processing...\n"
        assert chunks[2] == "Done!\n"
    
    def test_streaming_with_progress_bars(self):
        """Test that streaming handles progress bars correctly."""
        manager = OutputManager()
        
        # Create stream with progress bars
        def generate_stream():
            yield "Downloading...\n"
            yield "Progress: 10%\n"
            yield "Progress: 50%\n"
            yield "Progress: 100%\n"
            yield "Complete!\n"
        
        command = "npm install"
        
        # Process stream
        chunks = list(manager.process_stream(generate_stream(), command))
        
        # Should yield all chunks (compression happens at the end)
        assert "Downloading...\n" in chunks
        assert "Complete!\n" in chunks
        
        # If there's a summary, it might mention compression
        summary_chunks = [c for c in chunks if "OUTPUT SUMMARY" in c or "📊" in c]
        if summary_chunks:
            summary = summary_chunks[0]
            # May or may not mention compression depending on whether it was applied
            # Just verify it's a valid summary
            assert "cache" in summary.lower() or "cmd_" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
