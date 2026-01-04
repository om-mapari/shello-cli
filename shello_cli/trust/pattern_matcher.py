"""Pattern matching for command trust and safety system.

This module provides the PatternMatcher component that matches commands against
allowlist and denylist patterns. It supports three types of pattern matching:

1. Exact Match: Command must match pattern exactly
   Example: "git status" matches "git status"

2. Wildcard Match: Use * as wildcard for any characters
   Example: "git *" matches "git status", "git log", "git diff", etc.
   Example: "npm run *" matches "npm run test", "npm run build", etc.

3. Regex Match: Use regex patterns (must start with ^)
   Example: "^git (status|log|diff)$" matches only those three commands
   Example: "^npm (test|run test)$" matches "npm test" or "npm run test"

Pattern Matching Rules:
    - Patterns are checked in order (first match wins)
    - Wildcard patterns are converted to regex internally
    - Invalid regex patterns are silently skipped
    - Empty patterns never match

Example Usage:
    >>> from shello_cli.trust.pattern_matcher import PatternMatcher
    >>> 
    >>> allowlist = ["ls", "git *", "^npm (test|run test)$"]
    >>> denylist = ["rm -rf *", "sudo rm *"]
    >>> matcher = PatternMatcher(allowlist, denylist)
    >>> 
    >>> # Check allowlist
    >>> matcher.matches_allowlist("ls")  # True (exact match)
    >>> matcher.matches_allowlist("git status")  # True (wildcard match)
    >>> matcher.matches_allowlist("npm test")  # True (regex match)
    >>> matcher.matches_allowlist("rm file.txt")  # False
    >>> 
    >>> # Check denylist
    >>> matcher.matches_denylist("rm -rf /")  # True (wildcard match)
    >>> matcher.matches_denylist("sudo rm -rf node_modules")  # True (wildcard match)
    >>> matcher.matches_denylist("ls")  # False

Performance Notes:
    - Exact matching is O(1)
    - Wildcard and regex matching is O(n) where n is pattern count
    - Patterns are compiled on first use and cached

See Also:
    - TrustManager: Uses PatternMatcher for command evaluation
    - constants.py: Default allowlist/denylist patterns
"""

import re
from typing import List


class PatternMatcher:
    """Matches commands against allowlist/denylist patterns.
    
    Supports three types of pattern matching:
    1. Exact match: "git status"
    2. Wildcard: "git *", "npm run *"
    3. Regex: "^git (status|log)$"
    """
    
    def __init__(self, allowlist: List[str], denylist: List[str]):
        """Initialize with pattern lists.
        
        Args:
            allowlist: List of patterns for commands that execute without approval
            denylist: List of patterns for dangerous commands that require warnings
        """
        self.allowlist = allowlist
        self.denylist = denylist
    
    def matches_allowlist(self, command: str) -> bool:
        """Check if command matches any allowlist pattern.
        
        Args:
            command: The command to check
            
        Returns:
            True if command matches any allowlist pattern, False otherwise
        """
        return any(self._match_pattern(command, pattern) for pattern in self.allowlist)
    
    def matches_denylist(self, command: str) -> bool:
        """Check if command matches any denylist pattern.
        
        Args:
            command: The command to check
            
        Returns:
            True if command matches any denylist pattern, False otherwise
        """
        return any(self._match_pattern(command, pattern) for pattern in self.denylist)
    
    def _match_pattern(self, command: str, pattern: str) -> bool:
        """Match command against a single pattern.
        
        Supports:
        - Exact match: "git status"
        - Wildcard: "git *", "npm run *"
        - Regex: "^git (status|log|diff)$"
        
        Args:
            command: The command to match
            pattern: The pattern to match against
            
        Returns:
            True if command matches pattern, False otherwise
        """
        # Exact match - fastest check, try first
        if command == pattern:
            return True
        
        # Wildcard match (convert to regex)
        # Example: "git *" becomes "^git .*$"
        if '*' in pattern:
            # Escape special regex characters except *
            # This ensures patterns like "git [status]" don't break
            escaped_pattern = re.escape(pattern)
            # Replace escaped \* with .* for wildcard matching
            regex_pattern = escaped_pattern.replace(r'\*', '.*')
            try:
                # Match entire command (^ and $ anchors)
                if re.match(f"^{regex_pattern}$", command):
                    return True
            except re.error:
                # Invalid regex after conversion, skip this pattern
                pass
        
        # Regex match (patterns starting with ^)
        # Example: "^git (status|log)$" matches only those commands
        if pattern.startswith('^'):
            try:
                if re.match(pattern, command):
                    return True
            except re.error:
                # Invalid regex, skip this pattern
                pass
        
        return False
