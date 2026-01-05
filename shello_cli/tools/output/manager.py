"""OutputManager orchestrator for processing command output."""

import json
from typing import Optional, Iterator
from .types import TruncationResult, OutputType, TruncationStrategy
from .cache import OutputCache
from .type_detector import TypeDetector
from .compressor import ProgressBarCompressor
from .truncator import Truncator
from ...defaults import (
    DEFAULT_CHAR_LIMITS,
    DEFAULT_STRATEGIES,
)
from ...patterns import (
    JSON_ANALYZER_SUMMARY_TEMPLATE,
    TRUNCATION_SUMMARY_TEMPLATE,
)
from ...utils.output_utils import strip_line_padding


class OutputManager:
    """
    Orchestrates output processing with caching, type detection, compression, and truncation.
    
    Processing flow:
    1. Store in cache first
    2. Detect type
    3. Compress progress bars
    4. Check if JSON needs analyzer
    5. Apply truncation strategy
    6. Apply semantic if enabled
    7. Generate summary
    """
    
    def __init__(
        self,
        cache: Optional[OutputCache] = None,
        json_analyzer: Optional['JsonAnalyzerTool'] = None
    ):
        """
        Initialize OutputManager.
        
        Args:
            cache: Optional OutputCache instance (creates new if None)
            json_analyzer: Optional JsonAnalyzerTool for large JSON handling
        """
        self.cache = cache or OutputCache()
        self.type_detector = TypeDetector()
        self.compressor = ProgressBarCompressor()
        self.truncator = Truncator()
        self.json_analyzer = json_analyzer
    
    def process_output(self, output: str, command: str) -> TruncationResult:
        """
        Process command output with full pipeline.
        
        Args:
            output: Full command output
            command: Command that generated the output
        
        Returns:
            TruncationResult with processed output and metadata
        """
        # Step 0: Strip trailing whitespace from each line (removes PowerShell padding)
        # This preserves structure but removes unnecessary spaces that inflate char counts
        output = strip_line_padding(output)
        
        # Step 1: Store in cache first
        cache_id = self.cache.store(command, output)
        
        # Step 2: Detect type
        output_type = self.type_detector.detect(command, output)
        
        # Step 3: Compress progress bars
        compressed_output, compression_stats = self.compressor.compress(output)
        
        # Get limits and strategy for this type
        max_chars = DEFAULT_CHAR_LIMITS.get(output_type.value, DEFAULT_CHAR_LIMITS["default"])
        strategy_name = DEFAULT_STRATEGIES.get(output_type.value, DEFAULT_STRATEGIES["default"])
        strategy = TruncationStrategy(strategy_name)
        
        # Step 4: Check if JSON needs analyzer
        if output_type == OutputType.JSON and len(compressed_output) > max_chars:
            return self._handle_json_with_analyzer(
                compressed_output,
                cache_id,
                max_chars,
                compression_stats
            )
        
        # Step 5-6: Apply truncation strategy with semantic
        result = self.truncator.truncate(
            compressed_output,
            max_chars,
            strategy,
            output_type,
            use_semantic=True
        )
        
        # Step 7: Add cache_id and compression stats
        result.cache_id = cache_id
        result.compression_stats = compression_stats
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        return result
    
    def _handle_json_with_analyzer(
        self,
        output: str,
        cache_id: str,
        max_chars: int,
        compression_stats: Optional[dict]
    ) -> TruncationResult:
        """
        Handle JSON output that exceeds limit using json_analyzer_tool.
        
        ALWAYS use json_analyzer_tool if JSON exceeds limit (20K chars).
        If JSON parsing fails, fall back to regular truncation (treat as text).
        
        Args:
            output: JSON output string
            cache_id: Cache ID for retrieval
            max_chars: Character limit
            compression_stats: Progress bar compression stats
        
        Returns:
            TruncationResult with jq paths or truncated text
        """
        # Try to parse as JSON
        try:
            json.loads(output)
        except json.JSONDecodeError:
            # Not valid JSON - fall back to regular truncation
            return self._fallback_to_text_truncation(
                output,
                cache_id,
                max_chars,
                compression_stats
            )
        
        # Valid JSON exceeds limit - use json_analyzer_tool
        if self.json_analyzer is None:
            # No analyzer available - fall back to text truncation
            return self._fallback_to_text_truncation(
                output,
                cache_id,
                max_chars,
                compression_stats
            )
        
        # Use analyze_json_string() method for direct JSON analysis
        analyzer_result = self.json_analyzer.analyze_json_string(output)
        
        if not analyzer_result.success:
            # Analysis failed - fall back to text truncation
            return self._fallback_to_text_truncation(
                output,
                cache_id,
                max_chars,
                compression_stats
            )
        
        # Success - return jq paths
        total_chars = len(output)
        total_lines = output.count('\n') + (1 if output and not output.endswith('\n') else 0)
        shown_chars = len(analyzer_result.output)
        shown_lines = analyzer_result.output.count('\n') + 1
        
        result = TruncationResult(
            output=analyzer_result.output,
            was_truncated=True,
            total_chars=total_chars,
            shown_chars=shown_chars,
            total_lines=total_lines,
            shown_lines=shown_lines,
            output_type=OutputType.JSON,
            strategy=TruncationStrategy.FIRST_ONLY,  # Not really applicable
            cache_id=cache_id,
            compression_stats=compression_stats,
            semantic_stats=None,
            used_json_analyzer=True,
            summary=""
        )
        
        # Generate JSON-specific summary
        result.summary = self._generate_json_summary(result)
        
        return result
    
    def _fallback_to_text_truncation(
        self,
        output: str,
        cache_id: str,
        max_chars: int,
        compression_stats: Optional[dict]
    ) -> TruncationResult:
        """
        Fall back to regular text truncation when JSON handling fails.
        
        Args:
            output: Output string
            cache_id: Cache ID
            max_chars: Character limit
            compression_stats: Compression stats
        
        Returns:
            TruncationResult with text truncation
        """
        # Use FIRST_LAST strategy as default for failed JSON
        result = self.truncator.truncate(
            output,
            max_chars,
            TruncationStrategy.FIRST_LAST,
            OutputType.DEFAULT,  # Treat as default, not JSON
            use_semantic=True
        )
        
        result.cache_id = cache_id
        result.compression_stats = compression_stats
        result.summary = self._generate_summary(result)
        
        return result
    
    def _generate_summary(self, result: TruncationResult) -> str:
        """
        Generate truncation summary for regular output.
        
        Args:
            result: TruncationResult to summarize
        
        Returns:
            Formatted summary string
        """
        # Check if we have anything to report
        has_compression = (result.compression_stats and 
                          result.compression_stats.lines_saved > 0)
        
        if not result.was_truncated and not has_compression:
            return ""
        
        # If only compression (no truncation), show simpler summary
        if not result.was_truncated and has_compression:
            lines_saved = result.compression_stats.lines_saved
            return f"""
───────────────────────────────────────────────────────────
📊 OUTPUT SUMMARY
───────────────────────────────────────────────────────────
Optimizations: Progress bars compressed (saved {lines_saved} lines)

💾 Cache ID: {result.cache_id}
───────────────────────────────────────────────────────────
""".strip()
        
        # Build optimizations line
        optimizations = []
        if result.compression_stats:
            lines_saved = result.compression_stats.lines_saved
            if lines_saved > 0:
                optimizations.append(f"Progress bars compressed (saved {lines_saved} lines)")
        
        optimizations_str = "Optimizations: " + ", ".join(optimizations) if optimizations else ""
        
        # Build semantic stats line
        semantic_str = ""
        if result.semantic_stats:
            critical = result.semantic_stats.get('critical', 0)
            high = result.semantic_stats.get('high', 0)
            low = result.semantic_stats.get('low', 0)
            semantic_str = f"Semantic: {critical} critical, {high} high, {low} low importance lines shown"
        
        # Build suggestion based on output type
        suggestion = self._get_suggestion(result)
        
        # Format strategy name
        strategy_name = result.strategy.value.replace('_', ' ').upper()
        if result.strategy == TruncationStrategy.FIRST_LAST:
            strategy_name += " (20% first + 80% last)"
        
        return TRUNCATION_SUMMARY_TEMPLATE.format(
            total_chars=result.total_chars,
            total_lines=result.total_lines,
            shown_chars=result.shown_chars,
            shown_lines=result.shown_lines,
            strategy=strategy_name,
            optimizations=optimizations_str,
            semantic_stats=semantic_str,
            cache_id=result.cache_id,
            suggestion=suggestion
        ).strip()
    
    def _generate_json_summary(self, result: TruncationResult) -> str:
        """
        Generate summary for JSON that was analyzed.
        
        Args:
            result: TruncationResult with JSON analysis
        
        Returns:
            Formatted JSON summary string
        """
        return JSON_ANALYZER_SUMMARY_TEMPLATE.format(
            total_chars=result.total_chars,
            cache_id=result.cache_id
        ).strip()
    
    def _get_suggestion(self, result: TruncationResult) -> str:
        """
        Get appropriate suggestion for get_cached_output based on output type.
        
        Args:
            result: TruncationResult
        
        Returns:
            Suggestion string
        """
        cache_id = result.cache_id
        
        # Suggest based on strategy used
        if result.strategy == TruncationStrategy.LAST_ONLY:
            # For logs, suggest seeing more from the end
            return f'Use get_cached_output(cache_id="{cache_id}", lines="-200") to see last 200 lines'
        elif result.strategy == TruncationStrategy.FIRST_ONLY:
            # For lists/searches, suggest seeing more from start
            return f'Use get_cached_output(cache_id="{cache_id}", lines="+200") to see first 200 lines'
        else:
            # For FIRST_LAST (install/build/test), suggest seeing the end
            return f'Use get_cached_output(cache_id="{cache_id}", lines="-100") to see last 100 lines'
    
    def process_stream(
        self,
        stream: Iterator[str],
        command: str
    ) -> Iterator[str]:
        """
        Process streaming output.
        
        1. Yield chunks to user as they arrive (normal display)
        2. Accumulate full output in background
        3. After stream ends, cache full output
        4. Apply truncation and return summary
        
        User experience: See output streaming normally
        AI experience: Get truncated result with cache_id at end
        
        Args:
            stream: Iterator yielding output chunks
            command: Command being executed
        
        Yields:
            Output chunks as they arrive, then summary at end
        """
        accumulated = []
        
        for chunk in stream:
            accumulated.append(chunk)
            yield chunk  # User sees output normally
        
        # Stream complete - now process
        full_output = ''.join(accumulated)
        
        # Process through full pipeline
        result = self.process_output(full_output, command)
        
        # Yield summary at end (only if truncated)
        if result.was_truncated and result.summary:
            yield '\n' + result.summary
