"""Unit tests for PatternMatcher component."""

import pytest
from shello_cli.trust.pattern_matcher import PatternMatcher


class TestPatternMatcherExactMatching:
    """Test exact string matching."""
    
    def test_exact_match_allowlist(self):
        """Test exact match in allowlist."""
        matcher = PatternMatcher(
            allowlist=["git status", "ls", "pwd"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status") is True
        assert matcher.matches_allowlist("ls") is True
        assert matcher.matches_allowlist("pwd") is True
    
    def test_exact_match_denylist(self):
        """Test exact match in denylist."""
        matcher = PatternMatcher(
            allowlist=[],
            denylist=["rm -rf /", "dd if=/dev/zero"]
        )
        assert matcher.matches_denylist("rm -rf /") is True
        assert matcher.matches_denylist("dd if=/dev/zero") is True
    
    def test_no_match_when_different(self):
        """Test that similar but different commands don't match."""
        matcher = PatternMatcher(
            allowlist=["git status"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status ") is False  # trailing space
        assert matcher.matches_allowlist("git statuses") is False
        assert matcher.matches_allowlist("git") is False
    
    def test_case_sensitive_matching(self):
        """Test that matching is case-sensitive."""
        matcher = PatternMatcher(
            allowlist=["git status"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status") is True
        assert matcher.matches_allowlist("Git Status") is False
        assert matcher.matches_allowlist("GIT STATUS") is False


class TestPatternMatcherWildcardMatching:
    """Test wildcard pattern matching."""
    
    def test_wildcard_at_end(self):
        """Test wildcard at end of pattern."""
        matcher = PatternMatcher(
            allowlist=["git *", "npm run *"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status") is True
        assert matcher.matches_allowlist("git log") is True
        assert matcher.matches_allowlist("git diff --cached") is True
        assert matcher.matches_allowlist("npm run test") is True
        assert matcher.matches_allowlist("npm run build") is True
    
    def test_wildcard_at_start(self):
        """Test wildcard at start of pattern."""
        matcher = PatternMatcher(
            allowlist=["* --help"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git --help") is True
        assert matcher.matches_allowlist("npm --help") is True
        assert matcher.matches_allowlist("python --help") is True
    
    def test_wildcard_in_middle(self):
        """Test wildcard in middle of pattern."""
        matcher = PatternMatcher(
            allowlist=["git * --help"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status --help") is True
        assert matcher.matches_allowlist("git log --help") is True
        assert matcher.matches_allowlist("git diff --help") is True
    
    def test_multiple_wildcards(self):
        """Test multiple wildcards in pattern."""
        matcher = PatternMatcher(
            allowlist=["* run * test"],
            denylist=[]
        )
        assert matcher.matches_allowlist("npm run my test") is True
        assert matcher.matches_allowlist("yarn run integration test") is True
    
    def test_wildcard_matches_empty(self):
        """Test that wildcard can match empty string."""
        matcher = PatternMatcher(
            allowlist=["ls*"],
            denylist=[]
        )
        assert matcher.matches_allowlist("ls") is True
        assert matcher.matches_allowlist("ls -la") is True
    
    def test_wildcard_no_match(self):
        """Test wildcard patterns that don't match."""
        matcher = PatternMatcher(
            allowlist=["git *"],
            denylist=[]
        )
        assert matcher.matches_allowlist("npm status") is False
        assert matcher.matches_allowlist("gi status") is False


class TestPatternMatcherRegexMatching:
    """Test regex pattern matching."""
    
    def test_regex_alternation(self):
        """Test regex with alternation (|)."""
        matcher = PatternMatcher(
            allowlist=["^git (status|log|diff)$"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status") is True
        assert matcher.matches_allowlist("git log") is True
        assert matcher.matches_allowlist("git diff") is True
        assert matcher.matches_allowlist("git push") is False
    
    def test_regex_optional_groups(self):
        """Test regex with optional groups."""
        matcher = PatternMatcher(
            allowlist=["^ls( -[la]+)?$"],
            denylist=[]
        )
        assert matcher.matches_allowlist("ls") is True
        assert matcher.matches_allowlist("ls -l") is True
        assert matcher.matches_allowlist("ls -la") is True
        assert matcher.matches_allowlist("ls -al") is True
        assert matcher.matches_allowlist("ls -R") is False
    
    def test_regex_character_classes(self):
        """Test regex with character classes."""
        matcher = PatternMatcher(
            allowlist=["^git log -[0-9]$"],  # Single digit only
            denylist=[]
        )
        assert matcher.matches_allowlist("git log -1") is True
        assert matcher.matches_allowlist("git log -5") is True
        assert matcher.matches_allowlist("git log -10") is False  # Two digits, doesn't match
    
    def test_regex_anchors(self):
        """Test regex anchors (^ and $)."""
        matcher = PatternMatcher(
            allowlist=["^git status$"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git status") is True
        assert matcher.matches_allowlist("git status ") is False
        assert matcher.matches_allowlist(" git status") is False
    
    def test_invalid_regex_ignored(self):
        """Test that invalid regex patterns are ignored."""
        matcher = PatternMatcher(
            allowlist=["^git (status$"],  # Invalid: unclosed group
            denylist=[]
        )
        # Should not raise exception, just return False
        assert matcher.matches_allowlist("git status") is False


class TestPatternMatcherEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_pattern_lists(self):
        """Test with empty allowlist and denylist."""
        matcher = PatternMatcher(allowlist=[], denylist=[])
        assert matcher.matches_allowlist("any command") is False
        assert matcher.matches_denylist("any command") is False
    
    def test_empty_command(self):
        """Test matching empty command."""
        matcher = PatternMatcher(
            allowlist=["", "git status"],
            denylist=[]
        )
        assert matcher.matches_allowlist("") is True
        assert matcher.matches_allowlist("git status") is True
    
    def test_special_characters_in_command(self):
        """Test commands with special regex characters."""
        matcher = PatternMatcher(
            allowlist=["echo $PATH", "grep [a-z]"],
            denylist=[]
        )
        # Exact match should work
        assert matcher.matches_allowlist("echo $PATH") is True
        assert matcher.matches_allowlist("grep [a-z]") is True
    
    def test_special_characters_in_wildcard(self):
        """Test wildcard patterns with special characters."""
        matcher = PatternMatcher(
            allowlist=["echo *"],
            denylist=[]
        )
        # Should match commands with special characters
        assert matcher.matches_allowlist("echo $PATH") is True
        assert matcher.matches_allowlist("echo [test]") is True
        assert matcher.matches_allowlist("echo (hello)") is True
    
    def test_pattern_priority_first_match(self):
        """Test that first matching pattern is used."""
        matcher = PatternMatcher(
            allowlist=["git status", "git *"],
            denylist=[]
        )
        # Both patterns match, but order shouldn't matter for boolean result
        assert matcher.matches_allowlist("git status") is True
    
    def test_whitespace_in_patterns(self):
        """Test patterns with various whitespace."""
        matcher = PatternMatcher(
            allowlist=["git  status", "ls   -la"],  # Multiple spaces
            denylist=[]
        )
        # Exact match requires same whitespace
        assert matcher.matches_allowlist("git  status") is True
        assert matcher.matches_allowlist("git status") is False
        assert matcher.matches_allowlist("ls   -la") is True
        assert matcher.matches_allowlist("ls -la") is False
    
    def test_newlines_and_tabs(self):
        """Test commands with newlines and tabs."""
        matcher = PatternMatcher(
            allowlist=["git\tstatus", "ls\n"],
            denylist=[]
        )
        assert matcher.matches_allowlist("git\tstatus") is True
        assert matcher.matches_allowlist("ls\n") is True
    
    def test_very_long_command(self):
        """Test matching very long commands."""
        long_command = "git log " + " ".join([f"--option{i}" for i in range(100)])
        matcher = PatternMatcher(
            allowlist=["git log *"],
            denylist=[]
        )
        assert matcher.matches_allowlist(long_command) is True
    
    def test_unicode_characters(self):
        """Test commands with unicode characters."""
        matcher = PatternMatcher(
            allowlist=["echo 你好", "ls *"],
            denylist=[]
        )
        assert matcher.matches_allowlist("echo 你好") is True
        assert matcher.matches_allowlist("ls 文件") is True


class TestPatternMatcherBothLists:
    """Test interactions between allowlist and denylist."""
    
    def test_command_in_both_lists(self):
        """Test command that matches both allowlist and denylist."""
        matcher = PatternMatcher(
            allowlist=["rm *"],
            denylist=["rm -rf /"]
        )
        # Both methods should return True for their respective lists
        assert matcher.matches_allowlist("rm -rf /") is True
        assert matcher.matches_denylist("rm -rf /") is True
    
    def test_independent_matching(self):
        """Test that allowlist and denylist are independent."""
        matcher = PatternMatcher(
            allowlist=["git status"],
            denylist=["rm -rf /"]
        )
        assert matcher.matches_allowlist("git status") is True
        assert matcher.matches_denylist("git status") is False
        assert matcher.matches_allowlist("rm -rf /") is False
        assert matcher.matches_denylist("rm -rf /") is True
