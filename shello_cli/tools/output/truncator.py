"""Truncator for applying character-based truncation strategies."""

from typing import Tuple, List, Optional
from .types import TruncationStrategy, TruncationResult, OutputType, LineImportance
from .semantic import LineClassifier
from ...defaults import DEFAULT_FIRST_RATIO, DEFAULT_LAST_RATIO


class Truncator:
    """
    Applies truncation strategies with character-based limits.
    
    All truncation happens at line boundaries - never mid-line.
    """
    
    def __init__(self, first_ratio: float = DEFAULT_FIRST_RATIO, last_ratio: float = DEFAULT_LAST_RATIO):
        """
        Initialize truncator with first/last ratios.
        
        Args:
            first_ratio: Ratio of budget for first section (default 0.2 = 20%)
            last_ratio: Ratio of budget for last section (default 0.8 = 80%)
        """
        self.first_ratio = first_ratio
        self.last_ratio = last_ratio
        self.classifier = LineClassifier()
    
    def truncate(
        self,
        output: str,
        max_chars: int,
        strategy: TruncationStrategy,
        output_type: OutputType = OutputType.DEFAULT,
        use_semantic: bool = True
    ) -> TruncationResult:
        """
        Truncate output using specified strategy.
        
        Args:
            output: Full output string
            max_chars: Maximum characters to keep
            strategy: Truncation strategy to use
            output_type: Type of output (for metadata)
            use_semantic: Whether to apply semantic truncation (default True)
        
        Returns:
            TruncationResult with truncated output and metadata
        """
        total_chars = len(output)
        total_lines = output.count('\n') + (1 if output and not output.endswith('\n') else 0)
        
        # No truncation needed
        if total_chars <= max_chars:
            # Still compute semantic stats if requested
            semantic_stats = None
            if use_semantic:
                classified_lines = self.classifier.classify_lines(output)
                semantic_stats = self.classifier.get_importance_stats(classified_lines)
            
            return TruncationResult(
                output=output,
                was_truncated=False,
                total_chars=total_chars,
                shown_chars=total_chars,
                total_lines=total_lines,
                shown_lines=total_lines,
                output_type=output_type,
                strategy=strategy,
                semantic_stats=semantic_stats
            )
        
        # Apply semantic truncation if enabled
        semantic_stats = None
        if use_semantic:
            truncated, shown_chars, semantic_stats = self._truncate_with_semantic(
                output, max_chars, strategy
            )
        else:
            # Apply strategy without semantic analysis
            if strategy == TruncationStrategy.FIRST_ONLY:
                truncated, shown_chars = self._truncate_first_only(output, max_chars)
            elif strategy == TruncationStrategy.LAST_ONLY:
                truncated, shown_chars = self._truncate_last_only(output, max_chars)
            elif strategy == TruncationStrategy.FIRST_LAST:
                truncated, shown_chars = self._truncate_first_last(output, max_chars)
            else:
                # SEMANTIC strategy
                truncated, shown_chars = self._truncate_first_last(output, max_chars)
        
        shown_lines = truncated.count('\n') + (1 if truncated and not truncated.endswith('\n') else 0)
        
        return TruncationResult(
            output=truncated,
            was_truncated=True,
            total_chars=total_chars,
            shown_chars=shown_chars,
            total_lines=total_lines,
            shown_lines=shown_lines,
            output_type=output_type,
            strategy=strategy,
            semantic_stats=semantic_stats
        )
    
    def _truncate_first_only(self, output: str, max_chars: int) -> Tuple[str, int]:
        """
        Take first N chars at line boundary.
        
        Args:
            output: Full output string
            max_chars: Maximum characters to keep
        
        Returns:
            Tuple of (truncated_output, actual_chars_shown)
        """
        if len(output) <= max_chars:
            return output, len(output)
        
        # Find the last newline before max_chars
        truncate_at = output.rfind('\n', 0, max_chars)
        
        # If no newline found, take up to max_chars but try to break at last space
        if truncate_at == -1:
            truncate_at = output.rfind(' ', 0, max_chars)
            if truncate_at == -1:
                truncate_at = max_chars
        
        truncated = output[:truncate_at]
        return truncated, len(truncated)
    
    def _truncate_last_only(self, output: str, max_chars: int) -> Tuple[str, int]:
        """
        Take last N chars at line boundary.
        
        Args:
            output: Full output string
            max_chars: Maximum characters to keep
        
        Returns:
            Tuple of (truncated_output, actual_chars_shown)
        """
        if len(output) <= max_chars:
            return output, len(output)
        
        # Start from position that would give us max_chars
        start_pos = len(output) - max_chars
        
        # Find the first newline after start_pos
        truncate_from = output.find('\n', start_pos)
        
        # If no newline found, try to break at first space
        if truncate_from == -1:
            truncate_from = output.find(' ', start_pos)
            if truncate_from == -1:
                truncate_from = start_pos
        else:
            # Skip the newline character itself
            truncate_from += 1
        
        truncated = output[truncate_from:]
        return truncated, len(truncated)
    
    def _truncate_first_last(self, output: str, max_chars: int) -> Tuple[str, int]:
        """
        Take 20% first + 80% last with separator.
        
        Args:
            output: Full output string
            max_chars: Maximum characters to keep
        
        Returns:
            Tuple of (truncated_output, actual_chars_shown)
        """
        if len(output) <= max_chars:
            return output, len(output)
        
        # Calculate budgets
        separator = "\n\n... [middle section omitted] ...\n\n"
        separator_len = len(separator)
        
        # Reserve space for separator
        available_chars = max_chars - separator_len
        if available_chars < 100:  # Too small, fall back to first only
            return self._truncate_first_only(output, max_chars)
        
        first_budget = int(available_chars * self.first_ratio)
        last_budget = int(available_chars * self.last_ratio)
        
        # Get first section
        first_end = output.rfind('\n', 0, first_budget)
        if first_end == -1:
            first_end = output.rfind(' ', 0, first_budget)
            if first_end == -1:
                first_end = first_budget
        first_section = output[:first_end]
        
        # Get last section
        last_start_pos = len(output) - last_budget
        last_start = output.find('\n', last_start_pos)
        if last_start == -1:
            last_start = output.find(' ', last_start_pos)
            if last_start == -1:
                last_start = last_start_pos
        else:
            last_start += 1  # Skip the newline
        last_section = output[last_start:]
        
        # Combine sections
        truncated = first_section + separator + last_section
        return truncated, len(truncated)
    
    def _truncate_with_semantic(
        self,
        output: str,
        max_chars: int,
        strategy: TruncationStrategy
    ) -> Tuple[str, int, dict]:
        """
        Apply semantic truncation with importance-based line selection.
        
        Always includes ALL critical lines regardless of position.
        Includes HIGH importance lines if budget allows.
        Adjusts first/last budgets to accommodate important middle lines.
        
        Args:
            output: Full output string
            max_chars: Maximum characters to keep
            strategy: Base truncation strategy to use
        
        Returns:
            Tuple of (truncated_output, actual_chars_shown, semantic_stats)
        """
        # Classify all lines
        classified_lines = self.classifier.classify_lines(output)
        
        # Get stats for reporting
        stats = self.classifier.get_importance_stats(classified_lines)
        
        # Separate lines by importance
        critical_lines = []
        high_lines = []
        other_lines = []
        
        for idx, (line, importance) in enumerate(classified_lines):
            if importance == LineImportance.CRITICAL:
                critical_lines.append((idx, line))
            elif importance == LineImportance.HIGH:
                high_lines.append((idx, line))
            else:
                other_lines.append((idx, line))
        
        # If no critical or high lines, fall back to regular truncation
        if not critical_lines and not high_lines:
            if strategy == TruncationStrategy.FIRST_ONLY:
                truncated, shown_chars = self._truncate_first_only(output, max_chars)
            elif strategy == TruncationStrategy.LAST_ONLY:
                truncated, shown_chars = self._truncate_last_only(output, max_chars)
            else:
                truncated, shown_chars = self._truncate_first_last(output, max_chars)
            return truncated, shown_chars, stats
        
        # Calculate space needed for critical lines (ALWAYS included)
        critical_chars = sum(len(line) + 1 for _, line in critical_lines)  # +1 for newline
        
        # If critical lines alone exceed budget, include them anyway (requirement 16.5)
        if critical_chars >= max_chars:
            # Just return all critical lines
            result_lines = [line for _, line in sorted(critical_lines, key=lambda x: x[0])]
            truncated = '\n'.join(result_lines)
            return truncated, len(truncated), stats
        
        # Calculate remaining budget after critical lines
        remaining_budget = max_chars - critical_chars
        
        # Try to include HIGH importance lines if budget allows
        high_chars = sum(len(line) + 1 for _, line in high_lines)
        include_high = high_chars <= remaining_budget * 0.3  # Use up to 30% of remaining for HIGH
        
        if include_high:
            remaining_budget -= high_chars
            selected_lines = critical_lines + high_lines
        else:
            selected_lines = critical_lines
        
        # Use remaining budget for first/last sections based on strategy
        if remaining_budget > 100:  # Need reasonable space for first/last
            # Get indices of selected important lines
            important_indices = set(idx for idx, _ in selected_lines)
            
            # Apply base strategy to non-important lines
            if strategy == TruncationStrategy.FIRST_ONLY:
                first_budget = remaining_budget
                last_budget = 0
            elif strategy == TruncationStrategy.LAST_ONLY:
                first_budget = 0
                last_budget = remaining_budget
            else:  # FIRST_LAST
                first_budget = int(remaining_budget * self.first_ratio)
                last_budget = int(remaining_budget * self.last_ratio)
            
            # Collect first section lines
            first_section_lines = []
            first_chars = 0
            for idx, line in other_lines:
                if idx not in important_indices and first_chars < first_budget:
                    line_len = len(line) + 1
                    if first_chars + line_len <= first_budget:
                        first_section_lines.append((idx, line))
                        first_chars += line_len
                    else:
                        break
            
            # Collect last section lines
            last_section_lines = []
            last_chars = 0
            for idx, line in reversed(other_lines):
                if idx not in important_indices and last_chars < last_budget:
                    line_len = len(line) + 1
                    if last_chars + line_len <= last_budget:
                        last_section_lines.insert(0, (idx, line))
                        last_chars += line_len
                    else:
                        break
            
            # Combine all selected lines
            all_selected = selected_lines + first_section_lines + last_section_lines
        else:
            # Not enough budget for first/last, just use important lines
            all_selected = selected_lines
        
        # Sort by original index to maintain order
        all_selected.sort(key=lambda x: x[0])
        
        # Build output with separators where gaps exist
        result_lines = []
        prev_idx = -1
        for idx, line in all_selected:
            # Add separator if there's a gap
            if prev_idx >= 0 and idx > prev_idx + 1:
                result_lines.append("... [lines omitted] ...")
            result_lines.append(line)
            prev_idx = idx
        
        truncated = '\n'.join(result_lines)
        
        return truncated, len(truncated), stats
