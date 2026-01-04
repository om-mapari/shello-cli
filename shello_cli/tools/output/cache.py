"""Output caching for command results."""

import time
from typing import Dict, Optional
from .types import CacheEntry


class OutputCache:
    """
    Cache for command outputs with sequential IDs and LRU eviction.
    
    Cache IDs are sequential: cmd_001, cmd_002, cmd_003...
    Counter resets on app restart or new conversation (no persistence needed).
    
    Features:
    - Sequential cache IDs (cmd_001, cmd_002, ...)
    - No TTL expiration - cache persists for entire conversation
    - LRU eviction when size exceeds limit (default 100MB)
    - Automatic cleanup on conversation end (/new command or app exit)
    """
    
    def __init__(self, max_size_mb: int = 100):
        """Initialize the output cache.
        
        Args:
            max_size_mb: Maximum total cache size in megabytes (default: 100MB)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size_mb * 1024 * 1024  # Convert to bytes
        self._counter = 0  # Resets on restart or /new
        self._access_order: list[str] = []  # Track access order for LRU
    
    def _generate_cache_id(self) -> str:
        """Generate sequential cache ID: cmd_001, cmd_002, etc.
        
        Returns:
            Sequential cache ID string
        """
        self._counter += 1
        return f"cmd_{self._counter:03d}"
    
    def _get_total_size(self) -> int:
        """Calculate total size of all cached entries in bytes.
        
        Returns:
            Total size in bytes
        """
        return sum(entry.size_bytes for entry in self._cache.values())
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries until under size limit."""
        while self._get_total_size() > self._max_size and self._access_order:
            # Remove least recently used (first in list)
            lru_id = self._access_order.pop(0)
            if lru_id in self._cache:
                del self._cache[lru_id]
    
    def store(self, command: str, output: str) -> str:
        """Store output and return cache_id.
        
        Args:
            command: The command that generated the output
            output: The full command output to cache
            
        Returns:
            Cache ID for later retrieval (e.g., "cmd_001")
        """
        # Generate new cache ID
        cache_id = self._generate_cache_id()
        
        # Create cache entry
        entry = CacheEntry(
            output=output,
            command=command,
            created_at=time.time(),
            size_bytes=len(output.encode('utf-8'))
        )
        
        # Store entry
        self._cache[cache_id] = entry
        self._access_order.append(cache_id)
        
        # Evict LRU if over size limit
        self._evict_lru()
        
        return cache_id
    
    def get(self, cache_id: str) -> Optional[str]:
        """Get cached output or None if not found.
        
        Args:
            cache_id: The cache ID to retrieve
            
        Returns:
            Cached output string, or None if not found
        """
        # Check if entry exists
        if cache_id not in self._cache:
            return None
        
        # Update access order (move to end = most recently used)
        if cache_id in self._access_order:
            self._access_order.remove(cache_id)
        self._access_order.append(cache_id)
        
        return self._cache[cache_id].output
    
    def get_lines(self, cache_id: str, line_spec: str) -> Optional[str]:
        """Get specific lines from cached output.
        
        Args:
            cache_id: The cache ID to retrieve
            line_spec: Line specification:
                - "+N": First N lines
                - "-N": Last N lines
                - "+N,-M": First N + last M lines
                - "N-M": Lines N through M (1-indexed)
                
        Returns:
            Selected lines as string, or None if cache miss
        """
        output = self.get(cache_id)
        if output is None:
            return None
        
        lines = output.split('\n')
        total_lines = len(lines)
        
        # Parse line specification
        if line_spec.startswith('+') and ',' not in line_spec:
            # "+N" - First N lines
            n = int(line_spec[1:])
            selected_lines = lines[:n]
            return '\n'.join(selected_lines)
        
        elif line_spec.startswith('-') and ',' not in line_spec:
            # "-N" - Last N lines
            n = int(line_spec[1:])
            selected_lines = lines[-n:] if n <= total_lines else lines
            return '\n'.join(selected_lines)
        
        elif ',' in line_spec:
            # "+N,-M" - First N + last M lines
            parts = line_spec.split(',')
            first_n = int(parts[0][1:])  # Remove '+'
            last_m = int(parts[1][1:])   # Remove '-'
            
            first_lines = lines[:first_n]
            last_lines = lines[-last_m:] if last_m <= total_lines else []
            
            # Add omission indicator
            omitted = total_lines - first_n - last_m
            if omitted > 0:
                result = '\n'.join(first_lines)
                result += f"\n\n... ({omitted} lines omitted) ...\n\n"
                result += '\n'.join(last_lines)
                return result
            else:
                return '\n'.join(first_lines + last_lines)
        
        elif '-' in line_spec and not line_spec.startswith('-'):
            # "N-M" - Lines N through M (1-indexed)
            parts = line_spec.split('-')
            start = int(parts[0]) - 1  # Convert to 0-indexed
            end = int(parts[1])
            
            # Clamp to valid range
            start = max(0, min(start, total_lines))
            end = max(0, min(end, total_lines))
            
            selected_lines = lines[start:end]
            return '\n'.join(selected_lines)
        
        else:
            # Invalid format - return None
            return None
    
    def clear(self) -> None:
        """Clear all cached entries and reset counter."""
        self._cache.clear()
        self._access_order.clear()
        self._counter = 0  # Reset counter for new conversation
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'total_entries': len(self._cache),
            'total_size_bytes': self._get_total_size(),
            'total_size_mb': self._get_total_size() / (1024 * 1024),
            'max_size_mb': self._max_size / (1024 * 1024),
            'next_id': self._counter + 1
        }
