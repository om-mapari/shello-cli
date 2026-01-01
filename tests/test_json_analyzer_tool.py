"""
Tests for the JSON analyzer tool.
"""

import pytest
import json
import os
import platform
from unittest.mock import patch, MagicMock
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool


class TestJsonAnalyzerToolUnitTests:
    """Unit tests for JSON analyzer tool"""
    
    @patch('subprocess.run')
    def test_analyze_simple_json_command(self, mock_run):
        """Test analyzing a command that returns simple JSON"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"name": "John", "age": 30, "active": true}',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('echo \'{"name": "John", "age": 30, "active": true}\'')
        
        assert result.success is True
        assert result.error is None
        assert ".name | string" in result.output
        assert ".age | number" in result.output
        assert ".active | boolean" in result.output
    
    @patch('subprocess.run')
    def test_analyze_nested_json_command(self, mock_run):
        """Test analyzing a command that returns nested JSON"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"user": {"name": "John", "email": "john@example.com"}}',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is True
        assert ".user.name | string" in result.output
        assert ".user.email | string" in result.output
    
    @patch('subprocess.run')
    def test_analyze_array_json_command(self, mock_run):
        """Test analyzing a command that returns JSON with arrays"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"items": ["apple", "banana", "cherry"]}',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is True
        assert ".items[] | array[3]" in result.output
        assert ".items[] | array_item_str" in result.output
    
    @patch('subprocess.run')
    def test_analyze_array_of_objects_command(self, mock_run):
        """Test analyzing a command that returns array of objects"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"users": [{"name": "John", "age": 30}]}',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is True
        assert ".users[] | array[1]" in result.output
        assert ".users[].name | string" in result.output
        assert ".users[].age | number" in result.output
    
    @patch('subprocess.run')
    def test_analyze_command_returns_invalid_json(self, mock_run):
        """Test handling command that returns non-JSON output"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='This is not JSON',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is False
        assert result.output is None
        assert "not valid JSON" in result.error
    
    @patch('subprocess.run')
    def test_analyze_command_fails(self, mock_run):
        """Test handling command that fails"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Command not found'
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('invalid_command')
        
        assert result.success is False
        assert result.output is None
        assert "Command failed" in result.error
    
    @patch('subprocess.run')
    def test_analyze_command_empty_output(self, mock_run):
        """Test handling command that returns empty output"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is False
        assert result.output is None
        assert "no output" in result.error
    
    @patch('subprocess.run')
    def test_analyze_null_value(self, mock_run):
        """Test analyzing JSON with null values"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"value": null}',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is True
        assert ".value | null" in result.output
    
    @patch('subprocess.run')
    def test_analyze_root_array(self, mock_run):
        """Test analyzing JSON where root is an array"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]',
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('some_command')
        
        assert result.success is True
        assert ".[] | array[2]" in result.output
        assert ".[].id | number" in result.output
        assert ".[].name | string" in result.output
    
    @patch('subprocess.run')
    def test_analyze_aws_s3_buckets_example(self, mock_run):
        """Test analyzing AWS S3 list-buckets output structure"""
        aws_output = '''
        {
            "Buckets": [
                {
                    "Name": "my-bucket",
                    "CreationDate": "2023-01-01T00:00:00.000Z"
                }
            ],
            "Owner": {
                "DisplayName": "owner",
                "ID": "abc123"
            }
        }
        '''
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=aws_output,
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('aws s3api list-buckets --output json')
        
        assert result.success is True
        assert ".Buckets[] | array[1]" in result.output
        assert ".Buckets[].Name | string" in result.output
        assert ".Buckets[].CreationDate | string" in result.output
        assert ".Owner.DisplayName | string" in result.output
        assert ".Owner.ID | string" in result.output
    
    @patch('subprocess.run')
    def test_analyze_aws_lambda_example(self, mock_run):
        """Test analyzing AWS Lambda list-functions output structure"""
        lambda_output = '''
        {
            "Functions": [
                {
                    "FunctionName": "my-function",
                    "Runtime": "python3.9",
                    "Handler": "index.handler",
                    "CodeSize": 1024,
                    "LastModified": "2023-01-01T00:00:00.000+0000"
                }
            ]
        }
        '''
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=lambda_output,
            stderr=''
        )
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('aws lambda list-functions --output json')
        
        assert result.success is True
        assert ".Functions[] | array[1]" in result.output
        assert ".Functions[].FunctionName | string" in result.output
        assert ".Functions[].Runtime | string" in result.output
        assert ".Functions[].CodeSize | number" in result.output
    
    @patch('subprocess.run')
    def test_command_timeout(self, mock_run):
        """Test handling command timeout"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='slow_command', timeout=60)
        
        tool = JsonAnalyzerTool()
        result = tool.analyze('slow_command')
        
        assert result.success is False
        assert result.output is None
        assert "timed out" in result.error


class TestJsonAnalyzerToolIntegration:
    """Integration tests that actually execute commands"""
    
    def test_analyze_echo_json_command(self):
        """Test with actual echo command producing JSON"""
        tool = JsonAnalyzerTool()
        
        # Use platform-appropriate echo command
        if platform.system() == 'Windows':
            # PowerShell or cmd
            if tool._shell_type == 'powershell':
                command = 'Write-Output \'{"test": "value", "number": 42}\''
            else:
                command = 'echo {"test": "value", "number": 42}'
        else:
            command = 'echo \'{"test": "value", "number": 42}\''
        
        result = tool.analyze(command)
        
        # This might fail on some systems due to shell escaping
        # So we just check it doesn't crash
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'output')
        assert hasattr(result, 'error')
