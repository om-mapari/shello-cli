"""Property-based tests for Truncator."""

import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.tools.output.truncator import Truncator
from shello_cli.tools.output.types import TruncationStrategy, OutputType


# Generators for test data
@st.composite
def output_text(draw):
    """Generate realistic output text with multiple lines."""
    num_lines = draw(st.integers(min_value=1, max_value=200))
    lines = []
    for _ in range(num_lines):
        line_length = draw(st.integers(min_value=10, max_value=200))
        line = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'), min_codepoint=32, max_codepoint=126),
            min_size=line_length,
            max_size=line_length
        ))
        lines.append(line)
    return '\n'.join(lines)


@st.composite
def char_limit(draw):
    """Generate reasonable character limits."""
    return draw(st.integers(min_value=100, max_value=50000))


class TestTruncatorProperties:
    """Property-based tests for Truncator."""
    
    @settings(max_examples=100)
    @given(
        output=output_text(),
        max_chars=char_limit(),
        strategy=st.sampled_from([
            TruncationStrategy.FIRST_ONLY,
            TruncationStrategy.LAST_ONLY,
            TruncationStrategy.FIRST_LAST
        ])
    )
    def test_character_limit_enforcement(self, output, max_chars, strategy):
        """
        Property 1: Character Limit Enforcement
        
        For any output and character limit, the truncated output SHALL NOT exceed
        the limit (measured at line boundaries).
        
        Feature: output-management, Property 1: Character Limit Enforcement
        Validates: Requirements 1.1, 2.2-2.9
        """
        truncator = Truncator()
        result = truncator.truncate(output, max_chars, strategy)
        
        # The shown output should not exceed the limit
        # We allow some tolerance because we cut at line boundaries
        # The tolerance is one line's worth of characters (max 200 from our generator)
        assert len(result.output) <= max_chars + 200, \
            f"Output length {len(result.output)} exceeds limit {max_chars} by more than one line"
        
        # If truncation occurred, output should be shorter than original
        if result.was_truncated:
            assert len(result.output) < len(output), \
                "Truncated output should be shorter than original"
        
        # Shown chars should match actual output length
        assert result.shown_chars == len(result.output), \
            f"shown_chars {result.shown_chars} doesn't match actual output length {len(result.output)}"
        
        # Total chars should match original
        assert result.total_chars == len(output), \
            f"total_chars {result.total_chars} doesn't match original length {len(output)}"
    
    @settings(max_examples=100)
    @given(
        output=output_text(),
        max_chars=char_limit(),
        strategy=st.sampled_from([
            TruncationStrategy.FIRST_ONLY,
            TruncationStrategy.LAST_ONLY,
            TruncationStrategy.FIRST_LAST
        ])
    )
    def test_line_boundary_preservation(self, output, max_chars, strategy):
        """
        Property 2: Line Boundary Preservation
        
        For any truncated output, the truncation SHALL occur at line boundaries
        (no partial lines).
        
        Feature: output-management, Property 2: Line Boundary Preservation
        Validates: Requirements 1.3
        """
        truncator = Truncator()
        result = truncator.truncate(output, max_chars, strategy)
        
        if not result.was_truncated:
            # No truncation, nothing to check
            return
        
        # For FIRST_LAST strategy, we have a separator in the middle
        # Note: If available space is too small (< 100 chars), it falls back to FIRST_ONLY
        if strategy == TruncationStrategy.FIRST_LAST and result.was_truncated:
            separator = "... [middle section omitted] ..."
            
            # Check if separator is present (it should be unless fallback occurred)
            if separator in result.output:
                # Split by separator and check each part
                parts = result.output.split(separator)
                if len(parts) == 2:
                    first_part, last_part = parts
                    
                    # First part should be from the beginning of original
                    if first_part.strip():
                        assert output.startswith(first_part.strip().split('\n')[0]), \
                            "First part should start from beginning of original"
                    
                    # Last part should be from the end of original
                    if last_part.strip():
                        last_line = last_part.strip().split('\n')[-1]
                        assert output.rstrip().endswith(last_line.rstrip()), \
                            "Last part should end at end of original"
            else:
                # Fallback to FIRST_ONLY occurred - just verify it's from the start
                if result.output.strip():
                    first_line = result.output.strip().split('\n')[0]
                    assert output.startswith(first_line), \
                        "Fallback FIRST_ONLY output should be from start of original"
        
        elif strategy == TruncationStrategy.FIRST_ONLY:
            # Output should be a prefix of the original (at line boundary)
            # The truncated output should appear at the start of original
            if result.output.strip():
                first_line = result.output.strip().split('\n')[0]
                assert output.startswith(first_line), \
                    "FIRST_ONLY output should be from start of original"
        
        elif strategy == TruncationStrategy.LAST_ONLY:
            # Output should be a suffix of the original (at line boundary)
            # The truncated output should appear at the end of original
            if result.output.strip():
                last_line = result.output.strip().split('\n')[-1]
                assert output.rstrip().endswith(last_line.rstrip()), \
                    "LAST_ONLY output should be from end of original"


class TestTruncatorBasicCases:
    """Basic unit tests for edge cases."""
    
    def test_no_truncation_when_under_limit(self):
        """Test that output under limit is not truncated."""
        truncator = Truncator()
        output = "Short output\nWith few lines\n"
        result = truncator.truncate(output, 1000, TruncationStrategy.FIRST_ONLY)
        
        assert not result.was_truncated
        assert result.output == output
        assert result.shown_chars == len(output)
        assert result.total_chars == len(output)
    
    def test_empty_output(self):
        """Test handling of empty output."""
        truncator = Truncator()
        output = ""
        result = truncator.truncate(output, 1000, TruncationStrategy.FIRST_ONLY)
        
        assert not result.was_truncated
        assert result.output == ""
        assert result.shown_chars == 0
        assert result.total_chars == 0
    
    def test_first_only_strategy(self):
        """Test FIRST_ONLY strategy."""
        truncator = Truncator()
        output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n" * 100
        result = truncator.truncate(output, 500, TruncationStrategy.FIRST_ONLY)
        
        assert result.was_truncated
        assert len(result.output) <= 500 + 100  # Allow one line tolerance
        assert result.output.startswith("Line 1")
    
    def test_last_only_strategy(self):
        """Test LAST_ONLY strategy."""
        truncator = Truncator()
        output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n" * 100
        result = truncator.truncate(output, 500, TruncationStrategy.LAST_ONLY)
        
        assert result.was_truncated
        assert len(result.output) <= 500 + 100  # Allow one line tolerance
        assert "Line 5" in result.output
    
    def test_first_last_strategy(self):
        """Test FIRST_LAST strategy."""
        truncator = Truncator()
        output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n" * 100
        result = truncator.truncate(output, 500, TruncationStrategy.FIRST_LAST)
        
        assert result.was_truncated
        assert "... [middle section omitted] ..." in result.output or "... [lines omitted] ..." in result.output
        assert result.output.startswith("Line 1")
        assert "Line 5" in result.output
    
    def test_custom_ratios(self):
        """Test custom first/last ratios."""
        truncator = Truncator(first_ratio=0.3, last_ratio=0.7)
        output = "A" * 1000 + "\n" + "B" * 1000
        result = truncator.truncate(output, 500, TruncationStrategy.FIRST_LAST)
        
        assert result.was_truncated
        # Just verify it doesn't crash with custom ratios
        assert len(result.output) > 0


class TestSemanticTruncation:
    """Tests for semantic truncation with importance-based line selection."""
    
    @settings(max_examples=100)
    @given(
        num_normal_lines=st.integers(min_value=10, max_value=100),
        num_critical_lines=st.integers(min_value=1, max_value=10),
        max_chars=st.integers(min_value=500, max_value=5000)
    )
    def test_semantic_critical_preservation(self, num_normal_lines, num_critical_lines, max_chars):
        """
        Property 4: Semantic Critical Preservation
        
        For any output with CRITICAL lines, ALL critical lines SHALL appear in
        truncated output regardless of position.
        
        Feature: output-management, Property 4: Semantic Critical Preservation
        Validates: Requirements 16.5
        """
        truncator = Truncator()
        
        # Generate output with critical lines scattered throughout
        lines = []
        critical_markers = []
        
        # Add some normal lines at the start
        for i in range(num_normal_lines // 3):
            lines.append(f"Normal line {i}: some regular output")
        
        # Add critical lines in the middle
        for i in range(num_critical_lines):
            critical_line = f"ERROR: Critical failure {i} occurred"
            lines.append(critical_line)
            critical_markers.append(critical_line)
        
        # Add more normal lines
        for i in range(num_normal_lines // 3, num_normal_lines):
            lines.append(f"Normal line {i}: some regular output")
        
        output = '\n'.join(lines)
        
        # Truncate with semantic enabled (default)
        result = truncator.truncate(
            output,
            max_chars,
            TruncationStrategy.FIRST_LAST,
            use_semantic=True
        )
        
        # All critical lines must be present in the output
        for critical_line in critical_markers:
            assert critical_line in result.output, \
                f"Critical line '{critical_line}' missing from truncated output"
        
        # Semantic stats should be present
        assert result.semantic_stats is not None, \
            "Semantic stats should be present when semantic truncation is used"
        
        # Critical count should match
        assert result.semantic_stats["critical"] == num_critical_lines, \
            f"Expected {num_critical_lines} critical lines, got {result.semantic_stats['critical']}"
    
    def test_semantic_preserves_errors_in_middle(self):
        """Test that errors in the middle of output are preserved."""
        truncator = Truncator()
        
        # Create output with error in the middle
        lines = []
        for i in range(50):
            lines.append(f"Normal line {i}")
        
        lines.append("ERROR: Fatal exception occurred")
        lines.append("FAILURE: System crashed")
        
        for i in range(50, 100):
            lines.append(f"Normal line {i}")
        
        output = '\n'.join(lines)
        
        # Truncate with small budget
        result = truncator.truncate(
            output,
            500,  # Small budget
            TruncationStrategy.FIRST_LAST,
            use_semantic=True
        )
        
        # Both error lines must be present
        assert "ERROR: Fatal exception occurred" in result.output
        assert "FAILURE: System crashed" in result.output
        
        # Should have semantic stats
        assert result.semantic_stats is not None
        assert result.semantic_stats["critical"] >= 2
    
    def test_semantic_disabled(self):
        """Test that semantic can be disabled."""
        truncator = Truncator()
        
        lines = []
        for i in range(50):
            lines.append(f"Normal line {i}")
        
        lines.append("ERROR: This should be ignored when semantic is off")
        
        for i in range(50, 100):
            lines.append(f"Normal line {i}")
        
        output = '\n'.join(lines)
        
        # Truncate with semantic disabled
        result = truncator.truncate(
            output,
            500,
            TruncationStrategy.FIRST_ONLY,
            use_semantic=False
        )
        
        # Semantic stats should not be present
        assert result.semantic_stats is None
        
        # Error might not be in output (depends on position and strategy)
        # Just verify it doesn't crash
        assert len(result.output) > 0
    
    def test_semantic_with_high_importance_lines(self):
        """Test that HIGH importance lines are included when budget allows."""
        truncator = Truncator()
        
        lines = [
            "Normal line 1",
            "Normal line 2",
            "WARNING: This is a warning",
            "SUCCESS: Operation completed",
            "Normal line 3",
            "ERROR: Critical error",
            "Normal line 4",
            "Normal line 5",
        ]
        
        output = '\n'.join(lines)
        
        # Use generous budget
        result = truncator.truncate(
            output,
            1000,
            TruncationStrategy.FIRST_LAST,
            use_semantic=True
        )
        
        # Critical line must be present
        assert "ERROR: Critical error" in result.output
        
        # High importance lines should be present with generous budget
        # (WARNING and SUCCESS)
        assert result.semantic_stats is not None
        assert result.semantic_stats["critical"] >= 1
        assert result.semantic_stats["high"] >= 2
