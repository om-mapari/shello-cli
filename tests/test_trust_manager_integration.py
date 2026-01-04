"""Integration tests for TrustManager with ApprovalDialog."""

import pytest
from unittest.mock import Mock, patch
from shello_cli.trust.trust_manager import TrustManager, TrustConfig, EvaluationResult


class TestTrustManagerApprovalDialog:
    """Test TrustManager.handle_approval_dialog method."""
    
    def test_handle_approval_dialog_approved(self):
        """Test that handle_approval_dialog returns True when user approves."""
        config = TrustConfig()
        manager = TrustManager(config)
        
        # Mock the approval dialog to return True (approved)
        with patch.object(manager._approval_dialog, 'show', return_value=True):
            result = manager.handle_approval_dialog(
                command="rm -rf node_modules",
                warning_message="⚠️ CRITICAL: This command is in DENYLIST!",
                current_directory="/home/user/project"
            )
            
            assert result is True
    
    def test_handle_approval_dialog_denied(self):
        """Test that handle_approval_dialog returns False when user denies."""
        config = TrustConfig()
        manager = TrustManager(config)
        
        # Mock the approval dialog to return False (denied)
        with patch.object(manager._approval_dialog, 'show', return_value=False):
            result = manager.handle_approval_dialog(
                command="rm -rf node_modules",
                warning_message="⚠️ CRITICAL: This command is in DENYLIST!",
                current_directory="/home/user/project"
            )
            
            assert result is False
    
    def test_handle_approval_dialog_passes_correct_arguments(self):
        """Test that handle_approval_dialog passes correct arguments to ApprovalDialog."""
        config = TrustConfig()
        manager = TrustManager(config)
        
        # Mock the approval dialog
        mock_show = Mock(return_value=True)
        manager._approval_dialog.show = mock_show
        
        # Call handle_approval_dialog
        command = "git push --force"
        warning = "⚠️ AI WARNING: This command may be dangerous!"
        directory = "/home/user/repo"
        
        manager.handle_approval_dialog(
            command=command,
            warning_message=warning,
            current_directory=directory
        )
        
        # Verify the correct arguments were passed
        mock_show.assert_called_once_with(
            command=command,
            warning_message=warning,
            current_directory=directory
        )
    
    def test_handle_approval_dialog_with_no_warning(self):
        """Test handle_approval_dialog with no warning message."""
        config = TrustConfig()
        manager = TrustManager(config)
        
        # Mock the approval dialog
        mock_show = Mock(return_value=True)
        manager._approval_dialog.show = mock_show
        
        # Call with no warning
        manager.handle_approval_dialog(
            command="npm install",
            warning_message=None,
            current_directory="/home/user/project"
        )
        
        # Verify None was passed for warning_message
        mock_show.assert_called_once_with(
            command="npm install",
            warning_message=None,
            current_directory="/home/user/project"
        )


class TestTrustManagerIntegration:
    """Test TrustManager evaluate method integration."""
    
    def test_evaluate_returns_requires_approval_for_denylist(self):
        """Test that evaluate returns requires_approval=True for denylist commands."""
        config = TrustConfig()
        manager = TrustManager(config)
        
        result = manager.evaluate(
            command="rm -rf /",
            current_directory="/home/user"
        )
        
        assert result.requires_approval is True
        assert result.should_execute is False
        assert "CRITICAL" in result.warning_message
        assert result.decision_reason == "denylist_match"
    
    def test_evaluate_returns_requires_approval_for_non_allowlist(self):
        """Test that evaluate returns requires_approval=True for non-allowlist commands."""
        config = TrustConfig(approval_mode="user_driven")
        manager = TrustManager(config)
        
        result = manager.evaluate(
            command="npm install dangerous-package",
            current_directory="/home/user"
        )
        
        assert result.requires_approval is True
        assert result.should_execute is False
        assert result.decision_reason == "user_approval_required"
    
    def test_evaluate_no_approval_for_allowlist(self):
        """Test that evaluate returns requires_approval=False for allowlist commands."""
        config = TrustConfig()
        manager = TrustManager(config)
        
        result = manager.evaluate(
            command="git status",
            current_directory="/home/user"
        )
        
        assert result.requires_approval is False
        assert result.should_execute is True
        assert result.decision_reason == "allowlist_match"
