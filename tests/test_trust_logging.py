"""Tests for TrustManager logging functionality."""

import logging
import pytest
from shello_cli.trust.trust_manager import TrustManager, TrustConfig


class TestTrustManagerLogging:
    """Test that TrustManager logs command evaluations correctly."""
    
    def test_logging_for_allowlist_match(self, caplog):
        """Test that allowlist matches are logged at INFO level."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=["ls", "pwd"],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.INFO, logger="shello.trust"):
            result = manager.evaluate("ls", current_directory="/home/user")
        
        assert result.decision_reason == "allowlist_match"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "command='ls'" in caplog.records[0].message
        assert "decision=allowlist_match" in caplog.records[0].message
        assert "requires_approval=False" in caplog.records[0].message
    
    def test_logging_for_denylist_match(self, caplog):
        """Test that denylist matches are logged at WARNING level."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=[],
            denylist=["rm -rf /"]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.WARNING, logger="shello.trust"):
            result = manager.evaluate("rm -rf /", current_directory="/home/user")
        
        assert result.decision_reason == "denylist_match"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "DENYLIST MATCH" in caplog.records[0].message
        assert "command='rm -rf /'" in caplog.records[0].message
        assert "decision=denylist_match" in caplog.records[0].message
    
    def test_logging_for_ai_safety_flag_false(self, caplog):
        """Test that AI safety flag false is logged at WARNING level."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="ai_driven",
            allowlist=["ls"],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.WARNING, logger="shello.trust"):
            result = manager.evaluate("ls", is_safe=False, current_directory="/home/user")
        
        assert result.decision_reason == "ai_override_allowlist"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "AI SAFETY FLAG FALSE" in caplog.records[0].message
        assert "command='ls'" in caplog.records[0].message
        assert "is_safe=False" in caplog.records[0].message
    
    def test_logging_for_ai_safety_flag_false_user_driven(self, caplog):
        """Test that AI safety flag false is logged in user_driven mode."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=[],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.WARNING, logger="shello.trust"):
            result = manager.evaluate("dangerous_command", is_safe=False, current_directory="/home/user")
        
        assert result.decision_reason == "user_approval_required"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "AI SAFETY FLAG FALSE" in caplog.records[0].message
        assert "command='dangerous_command'" in caplog.records[0].message
        assert "is_safe=False" in caplog.records[0].message
    
    def test_logging_for_yolo_mode(self, caplog):
        """Test that YOLO mode is logged at INFO level."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=True,
            approval_mode="user_driven",
            allowlist=[],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.INFO, logger="shello.trust"):
            result = manager.evaluate("any_command", current_directory="/home/user")
        
        assert result.decision_reason == "yolo_mode"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "command='any_command'" in caplog.records[0].message
        assert "decision=yolo_mode" in caplog.records[0].message
    
    def test_logging_for_trust_disabled(self, caplog):
        """Test that trust system disabled is logged at INFO level."""
        config = TrustConfig(
            enabled=False,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=[],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.INFO, logger="shello.trust"):
            result = manager.evaluate("any_command", current_directory="/home/user")
        
        assert result.decision_reason == "trust_system_disabled"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "command='any_command'" in caplog.records[0].message
        assert "decision=trust_system_disabled" in caplog.records[0].message
    
    def test_logging_includes_directory(self, caplog):
        """Test that logging includes the current directory."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=["ls"],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.INFO, logger="shello.trust"):
            result = manager.evaluate("ls", current_directory="/home/user/project")
        
        assert result.decision_reason == "allowlist_match"
        assert len(caplog.records) == 1
        assert "directory='/home/user/project'" in caplog.records[0].message
    
    def test_logging_for_ai_approved(self, caplog):
        """Test that AI approved commands are logged at INFO level."""
        config = TrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="ai_driven",
            allowlist=[],
            denylist=[]
        )
        manager = TrustManager(config)
        
        with caplog.at_level(logging.INFO, logger="shello.trust"):
            result = manager.evaluate("some_command", is_safe=True, current_directory="/home/user")
        
        assert result.decision_reason == "ai_approved"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "command='some_command'" in caplog.records[0].message
        assert "is_safe=True" in caplog.records[0].message
        assert "decision=ai_approved" in caplog.records[0].message
