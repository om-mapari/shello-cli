"""Tests for system_info utilities."""
import os
import platform
from unittest.mock import patch
import pytest

from shello_cli.utils.system_info import detect_shell, get_shell_info


class TestShellDetection:
    """Test suite for shell detection."""
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'PSExecutionPolicyPreference': 'Unrestricted',
        'PSModulePath': 'C:\\Program Files\\PowerShell\\Modules'
    }, clear=True)
    def test_detect_powershell(self, mock_system):
        """Test PowerShell detection on Windows."""
        mock_system.return_value = 'Windows'
        
        shell, executable = detect_shell()
        
        assert shell == 'powershell'
        assert 'powershell' in executable.lower() or 'pwsh' in executable.lower()
        assert 'cmd.exe' not in executable  # Should NOT return cmd.exe
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'BASH_VERSION': '5.0.0',
        'BASH': '/usr/bin/bash'
    }, clear=True)
    def test_detect_bash_on_windows(self, mock_system):
        """Test Bash detection on Windows (Git Bash)."""
        mock_system.return_value = 'Windows'
        
        shell, executable = detect_shell()
        
        assert shell == 'bash'
        assert 'bash' in executable.lower()
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'COMSPEC': 'C:\\Windows\\system32\\cmd.exe'
    }, clear=True)
    def test_detect_cmd(self, mock_system):
        """Test cmd.exe detection on Windows."""
        mock_system.return_value = 'Windows'
        
        shell, executable = detect_shell()
        
        assert shell == 'cmd'
        assert 'cmd.exe' in executable
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'SHELL': '/bin/bash'
    }, clear=True)
    def test_detect_bash_on_unix(self, mock_system):
        """Test Bash detection on Unix-like systems."""
        mock_system.return_value = 'Linux'
        
        shell, executable = detect_shell()
        
        assert shell == 'bash'
        assert executable == '/bin/bash'
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'SHELL': '/bin/zsh'
    }, clear=True)
    def test_detect_zsh_on_unix(self, mock_system):
        """Test zsh detection on Unix-like systems."""
        mock_system.return_value = 'Darwin'
        
        shell, executable = detect_shell()
        
        assert shell == 'zsh'
        assert executable == '/bin/zsh'
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'PSExecutionPolicyPreference': 'Unrestricted'
    }, clear=True)
    def test_get_shell_info_powershell(self, mock_system):
        """Test get_shell_info returns correct structure for PowerShell."""
        mock_system.return_value = 'Windows'
        
        info = get_shell_info()
        
        assert info['os_name'] == 'Windows'
        assert info['shell'] == 'powershell'
        assert 'shell_executable' in info
        assert 'cwd' in info
        assert 'cmd.exe' not in info['shell_executable']
    
    @patch('platform.system')
    @patch.dict(os.environ, {
        'BASH': '/usr/bin/bash',
        'BASH_VERSION': '5.0'
    }, clear=True)
    def test_get_shell_info_bash(self, mock_system):
        """Test get_shell_info returns correct structure for Bash."""
        mock_system.return_value = 'Windows'
        
        info = get_shell_info()
        
        assert info['os_name'] == 'Windows'
        assert info['shell'] == 'bash'
        assert 'bash' in info['shell_executable'].lower()
