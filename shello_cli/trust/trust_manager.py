"""Trust manager for command execution safety.

This module provides the core TrustManager component that evaluates command safety
before execution. It integrates with the pattern matcher and approval dialog to
provide a comprehensive trust and safety system.

Key Components:
    - TrustManager: Central component for command evaluation
    - TrustConfig: Configuration dataclass for trust settings
    - EvaluationResult: Result of command safety evaluation
    - validate_config: Configuration validation function
    - TrustConfigError: Exception for invalid configuration

Evaluation Flow:
    1. Check if trust system is disabled
    2. Check denylist (highest priority - always shows warning)
    3. Check YOLO mode (bypass checks if enabled)
    4. Check allowlist (auto-execute safe commands)
    5. Apply approval_mode logic with AI safety flag
    6. Show approval dialog if needed

Example Usage:
    >>> from shello_cli.trust.trust_manager import TrustManager, TrustConfig
    >>> 
    >>> # Create trust manager with default config
    >>> config = TrustConfig()
    >>> manager = TrustManager(config)
    >>> 
    >>> # Evaluate a command
    >>> result = manager.evaluate("git status")
    >>> if result.requires_approval:
    ...     approved = manager.handle_approval_dialog(
    ...         command="git status",
    ...         warning_message=result.warning_message,
    ...         current_directory="/home/user/project"
    ...     )
    ...     if not approved:
    ...         print("Command denied")
    >>> 
    >>> # Evaluate with AI safety flag
    >>> result = manager.evaluate("rm -rf node_modules", is_safe=False)
    >>> # Will require approval with AI warning

Configuration Example:
    >>> config = TrustConfig(
    ...     enabled=True,
    ...     yolo_mode=False,
    ...     approval_mode="user_driven",
    ...     allowlist=["ls", "git status", "npm test"],
    ...     denylist=["rm -rf *", "sudo rm *"]
    ... )
    >>> manager = TrustManager(config)

See Also:
    - PatternMatcher: Pattern matching for allowlist/denylist
    - ApprovalDialog: Interactive approval UI component
    - constants.py: Default allowlist/denylist patterns
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from shello_cli.defaults import DEFAULT_ALLOWLIST, DEFAULT_DENYLIST, DEFAULT_APPROVAL_MODE
from shello_cli.trust.pattern_matcher import PatternMatcher
from shello_cli.trust.approval_dialog import ApprovalDialog

# Logger for trust decisions
logger = logging.getLogger("shello.trust")


class TrustConfigError(Exception):
    """Raised when trust configuration is invalid."""
    pass


def validate_config(config: 'TrustConfig') -> None:
    """Validate trust configuration.
    
    Validates:
    - approval_mode is either "ai_driven" or "user_driven"
    - All regex patterns in allowlist and denylist are valid
    
    Args:
        config: Trust configuration to validate
        
    Raises:
        TrustConfigError: If configuration is invalid
        
    Examples:
        >>> config = TrustConfig(approval_mode="invalid")
        >>> validate_config(config)  # Raises TrustConfigError
        
        >>> config = TrustConfig(allowlist=["^[invalid"])
        >>> validate_config(config)  # Raises TrustConfigError
    """
    # Validate approval_mode
    valid_modes = ["ai_driven", "user_driven"]
    if config.approval_mode not in valid_modes:
        raise TrustConfigError(
            f"Invalid approval_mode: '{config.approval_mode}'. "
            f"Must be one of: {', '.join(valid_modes)}"
        )
    
    # Validate regex patterns in allowlist
    for pattern in config.allowlist:
        if pattern.startswith('^'):
            try:
                re.compile(pattern)
            except re.error as e:
                raise TrustConfigError(
                    f"Invalid regex pattern in allowlist: '{pattern}' - {e}"
                )
    
    # Validate regex patterns in denylist
    for pattern in config.denylist:
        if pattern.startswith('^'):
            try:
                re.compile(pattern)
            except re.error as e:
                raise TrustConfigError(
                    f"Invalid regex pattern in denylist: '{pattern}' - {e}"
                )


@dataclass
class TrustConfig:
    """Trust system configuration."""
    enabled: bool = True
    yolo_mode: bool = False
    approval_mode: str = DEFAULT_APPROVAL_MODE
    allowlist: List[str] = field(default_factory=lambda: DEFAULT_ALLOWLIST.copy())
    denylist: List[str] = field(default_factory=lambda: DEFAULT_DENYLIST.copy())


@dataclass
class EvaluationResult:
    """Result of command safety evaluation."""
    should_execute: bool
    requires_approval: bool
    warning_message: Optional[str] = None
    matched_pattern: Optional[str] = None
    decision_reason: str = ""


class TrustManager:
    """Central component that evaluates command safety and manages approval workflows."""
    
    def __init__(self, config: TrustConfig):
        """Initialize with configuration.
        
        Args:
            config: Trust system configuration
        """
        self.config = config
        self._pattern_matcher = PatternMatcher(
            allowlist=config.allowlist,
            denylist=config.denylist
        )
        self._approval_dialog = ApprovalDialog()
    
    def evaluate(
        self,
        command: str,
        is_safe: Optional[bool] = None,
        current_directory: Optional[str] = None
    ) -> EvaluationResult:
        """Evaluate command safety and return decision.
        
        Evaluation flow:
        1. Check if trust system is disabled
        2. Check denylist (highest priority)
        3. Check YOLO mode
        4. Check allowlist
        5. Apply approval_mode logic with AI safety flag
        
        Args:
            command: The command to evaluate
            is_safe: Optional AI safety flag
            current_directory: Current working directory for context
            
        Returns:
            EvaluationResult with decision and metadata
        """
        # Step 1: Check if trust system is disabled
        # When disabled, all commands execute without any checks
        if not self.config.enabled:
            result = EvaluationResult(
                should_execute=True,
                requires_approval=False,
                decision_reason="trust_system_disabled"
            )
            logger.info(
                f"Command evaluation: command='{command}', "
                f"is_safe={is_safe}, decision={result.decision_reason}, "
                f"requires_approval={result.requires_approval}, "
                f"directory='{current_directory}'"
            )
            return result
        
        # Step 2: Check denylist (highest priority)
        # Denylist commands ALWAYS require approval, regardless of other settings
        # This ensures critical safety patterns cannot be bypassed
        if self._pattern_matcher.matches_denylist(command):
            result = EvaluationResult(
                should_execute=False,
                requires_approval=True,
                warning_message="⚠️ CRITICAL: This command is in DENYLIST!",
                decision_reason="denylist_match"
            )
            logger.warning(
                f"DENYLIST MATCH: command='{command}', "
                f"is_safe={is_safe}, decision={result.decision_reason}, "
                f"requires_approval={result.requires_approval}, "
                f"directory='{current_directory}'"
            )
            return result
        
        # Step 3: Check YOLO mode
        # YOLO mode bypasses all checks except denylist
        # Useful for automation and CI/CD environments
        if self.config.yolo_mode:
            result = EvaluationResult(
                should_execute=True,
                requires_approval=False,
                decision_reason="yolo_mode"
            )
            logger.info(
                f"Command evaluation: command='{command}', "
                f"is_safe={is_safe}, decision={result.decision_reason}, "
                f"requires_approval={result.requires_approval}, "
                f"directory='{current_directory}'"
            )
            return result
        
        # Step 4: Check allowlist
        # Allowlist commands execute without approval in most cases
        # Exception: In ai_driven mode, AI can override allowlist with is_safe=False
        if self._pattern_matcher.matches_allowlist(command):
            # In ai_driven mode, AI can override allowlist for safety
            if self.config.approval_mode == "ai_driven" and is_safe == False:
                result = EvaluationResult(
                    should_execute=False,
                    requires_approval=True,
                    warning_message="⚠️ AI WARNING: This command may be dangerous!",
                    decision_reason="ai_override_allowlist"
                )
                logger.warning(
                    f"AI SAFETY FLAG FALSE: command='{command}', "
                    f"is_safe={is_safe}, decision={result.decision_reason}, "
                    f"requires_approval={result.requires_approval}, "
                    f"directory='{current_directory}' (AI overrode allowlist)"
                )
                return result
            result = EvaluationResult(
                should_execute=True,
                requires_approval=False,
                decision_reason="allowlist_match"
            )
            logger.info(
                f"Command evaluation: command='{command}', "
                f"is_safe={is_safe}, decision={result.decision_reason}, "
                f"requires_approval={result.requires_approval}, "
                f"directory='{current_directory}'"
            )
            return result
        
        # Step 5: Apply approval_mode logic
        # Commands that don't match allowlist/denylist are evaluated based on approval_mode
        if self.config.approval_mode == "ai_driven":
            # In ai_driven mode, trust AI safety flags
            if is_safe == True:
                # AI says it's safe, execute without approval
                result = EvaluationResult(
                    should_execute=True,
                    requires_approval=False,
                    decision_reason="ai_approved"
                )
                logger.info(
                    f"Command evaluation: command='{command}', "
                    f"is_safe={is_safe}, decision={result.decision_reason}, "
                    f"requires_approval={result.requires_approval}, "
                    f"directory='{current_directory}'"
                )
                return result
            else:
                # is_safe is False or None - require approval
                warning = "⚠️ AI WARNING: This command may be dangerous!" if is_safe == False else None
                result = EvaluationResult(
                    should_execute=False,
                    requires_approval=True,
                    warning_message=warning,
                    decision_reason="ai_requires_approval"
                )
                # Log with warning level if AI flagged as unsafe
                if is_safe == False:
                    logger.warning(
                        f"AI SAFETY FLAG FALSE: command='{command}', "
                        f"is_safe={is_safe}, decision={result.decision_reason}, "
                        f"requires_approval={result.requires_approval}, "
                        f"directory='{current_directory}'"
                    )
                else:
                    logger.info(
                        f"Command evaluation: command='{command}', "
                        f"is_safe={is_safe}, decision={result.decision_reason}, "
                        f"requires_approval={result.requires_approval}, "
                        f"directory='{current_directory}'"
                    )
                return result
        else:  # user_driven mode
            # In user_driven mode, always prompt for non-allowlist commands
            # AI safety flag is shown as additional information but doesn't affect decision
            warning = "⚠️ AI flagged as potentially dangerous" if is_safe == False else None
            result = EvaluationResult(
                should_execute=False,
                requires_approval=True,
                warning_message=warning,
                decision_reason="user_approval_required"
            )
            # Log with warning level if AI flagged as unsafe
            if is_safe == False:
                logger.warning(
                    f"AI SAFETY FLAG FALSE: command='{command}', "
                    f"is_safe={is_safe}, decision={result.decision_reason}, "
                    f"requires_approval={result.requires_approval}, "
                    f"directory='{current_directory}'"
                )
            else:
                logger.info(
                    f"Command evaluation: command='{command}', "
                    f"is_safe={is_safe}, decision={result.decision_reason}, "
                    f"requires_approval={result.requires_approval}, "
                    f"directory='{current_directory}'"
                )
            return result
    
    def handle_approval_dialog(
        self,
        command: str,
        warning_message: Optional[str],
        current_directory: str
    ) -> bool:
        """Show approval dialog and return user decision.
        
        This method integrates with the ApprovalDialog component to display
        an interactive approval dialog to the user. The dialog shows the command,
        current directory, and any warning messages (e.g., denylist warnings or
        AI safety warnings).
        
        Args:
            command: The command to approve
            warning_message: Optional warning to display (e.g., denylist or AI warning)
            current_directory: Current working directory for context
            
        Returns:
            True if user approved the command, False if denied
            
        Examples:
            >>> manager = TrustManager(TrustConfig())
            >>> approved = manager.handle_approval_dialog(
            ...     command="rm -rf node_modules",
            ...     warning_message="⚠️ CRITICAL: This command is in DENYLIST!",
            ...     current_directory="/home/user/project"
            ... )
            >>> # Returns True if user presses 'A', False if user presses 'D'
        """
        return self._approval_dialog.show(
            command=command,
            warning_message=warning_message,
            current_directory=current_directory
        )
