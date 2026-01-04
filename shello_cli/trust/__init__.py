"""Trust and safety module for command execution."""

from shello_cli.trust.pattern_matcher import PatternMatcher
from shello_cli.trust.trust_manager import TrustManager, TrustConfig, EvaluationResult
from shello_cli.trust.approval_dialog import ApprovalDialog

__all__ = [
    "PatternMatcher",
    "TrustManager",
    "TrustConfig",
    "EvaluationResult",
    "ApprovalDialog",
]
