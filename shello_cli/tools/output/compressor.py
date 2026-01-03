"""Progress bar compression for output management."""

import re
from typing import Tuple

from shello_cli.constants import PROGRESS_BAR_PATTERNS
from shello_cli.tools.output.types import CompressionStats


class ProgressBarCompressor:
    """Compresses repetitive progress bar output.
    
    Detects progress bar patterns and keeps only the final state of each
    progress sequence, removing intermediate updates.
    """
    
    def __init__(self):
        """Initialize compressor with patterns from constants."""
        self._patterns = [re.compile(pattern, re.IGNORECASE) for pattern in PROGRESS_BAR_PATTERNS]
    
    def _is_progress_line(self, line: str) -> bool:
        """Check if a line matches any progress bar pattern.
        
        Args:
            line: Line to check
            
        Returns:
            True if line matches a progress pattern
        """
        return any(pattern.search(line) for pattern in self._patterns)
    
    def compress(self, output: str) -> Tuple[str, CompressionStats]:
        """Compress progress bars, keeping only final state.
        
        Algorithm:
        1. Split output into lines
        2. Identify sequences of consecutive progress lines
        3. For each sequence, keep only the last line (final state)
        4. Preserve all non-progress lines
        
        Args:
            output: Original output string
            
        Returns:
            Tuple of (compressed_output, compression_stats)
        """
        if not output:
            return output, CompressionStats(
                lines_before=0,
                lines_after=0,
                lines_saved=0,
                sequences_compressed=0
            )
        
        lines = output.split('\n')
        lines_before = len(lines)
        
        compressed_lines = []
        current_sequence = []
        sequences_compressed = 0
        
        for line in lines:
            if self._is_progress_line(line):
                # Add to current progress sequence
                current_sequence.append(line)
            else:
                # Non-progress line - flush current sequence if any
                if current_sequence:
                    # Keep only the last line of the sequence (final state)
                    compressed_lines.append(current_sequence[-1])
                    sequences_compressed += 1
                    current_sequence = []
                
                # Add the non-progress line
                compressed_lines.append(line)
        
        # Flush any remaining progress sequence
        if current_sequence:
            compressed_lines.append(current_sequence[-1])
            sequences_compressed += 1
        
        compressed_output = '\n'.join(compressed_lines)
        lines_after = len(compressed_lines)
        lines_saved = lines_before - lines_after
        
        stats = CompressionStats(
            lines_before=lines_before,
            lines_after=lines_after,
            lines_saved=lines_saved,
            sequences_compressed=sequences_compressed
        )
        
        return compressed_output, stats
