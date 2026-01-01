"""
Property-based tests for OutputManager.

Feature: output-management
Tests output type detection, truncation, and configuration.
"""

import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.tools.output_manager import (
    TypeDetector,
    OutputType,
    OutputManagementConfig,
    TruncationResult,
    DEFAULT_LIMITS,
    Truncator,
    OutputManager
)


class TestTypeDetectorProperties:
    """Property-based tests for TypeDetector."""
    
    @given(
        list_cmd=st.sampled_from([
            'ls -la',
            'dir',
            'docker ps',
            'kubectl get pods',
            'Get-ChildItem',
            'aws s3 list-buckets',
            'aws lambda list-functions'
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_list_command_detection(self, list_cmd):
        """
        Feature: output-management, Property 4: Output Type Detection (LIST)
        
        For any command containing list keywords (ls, dir, docker ps), 
        the TypeDetector SHALL classify it as LIST type.
        
        Validates: Requirements 8.2, 8.3
        """
        detector = TypeDetector()
        output_type = detector.detect_from_command(list_cmd)
        
        assert output_type == OutputType.LIST, \
            f"Command '{list_cmd}' should be detected as LIST type"
    
    @given(
        search_cmd=st.sampled_from([
            'grep pattern file.txt',
            'find . -name "*.py"',
            'search term',
            'Select-String pattern',
            'findstr pattern file.txt'
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_search_command_detection(self, search_cmd):
        """
        Feature: output-management, Property 4: Output Type Detection (SEARCH)
        
        For any command containing search keywords (grep, find, search), 
        the TypeDetector SHALL classify it as SEARCH type.
        
        Validates: Requirements 8.4
        """
        detector = TypeDetector()
        output_type = detector.detect_from_command(search_cmd)
        
        assert output_type == OutputType.SEARCH, \
            f"Command '{search_cmd}' should be detected as SEARCH type"
    
    @given(
        log_cmd=st.sampled_from([
            'tail -f /var/log/syslog',
            'cat error.log',
            'journalctl -u nginx',
            'Get-Content app.log'
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_log_command_detection(self, log_cmd):
        """
        Feature: output-management, Property 4: Output Type Detection (LOG)
        
        For any command containing log keywords (tail, cat.*log, journalctl), 
        the TypeDetector SHALL classify it as LOG type.
        
        Validates: Requirements 8.5
        """
        detector = TypeDetector()
        output_type = detector.detect_from_command(log_cmd)
        
        assert output_type == OutputType.LOG, \
            f"Command '{log_cmd}' should be detected as LOG type"
    
    @given(
        json_output=st.sampled_from([
            '{"key": "value"}',
            '[{"id": 1}, {"id": 2}]',
            '  {"nested": {"data": "test"}}',
            '\n\n[1, 2, 3]'
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_json_content_detection(self, json_output):
        """
        Feature: output-management, Property 4: Output Type Detection (JSON)
        
        For any output starting with valid JSON syntax ({ or [), 
        the TypeDetector SHALL classify it as JSON type.
        
        Validates: Requirements 8.2
        """
        detector = TypeDetector()
        output_type = detector.detect_from_content(json_output)
        
        assert output_type == OutputType.JSON, \
            f"Output starting with JSON syntax should be detected as JSON type"
    
    @given(
        command=st.sampled_from(['ls', 'grep test', 'tail log.txt']),
        json_output=st.sampled_from(['{"result": "data"}', '[1, 2, 3]'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_json_content_takes_precedence(self, command, json_output):
        """
        Feature: output-management, Property 4: Output Type Detection (Precedence)
        
        For any command with JSON output, content-based detection SHALL take 
        precedence over command-based detection.
        
        Validates: Requirements 8.2
        """
        detector = TypeDetector()
        output_type = detector.detect(command, json_output)
        
        assert output_type == OutputType.JSON, \
            f"JSON content should take precedence over command type for '{command}'"
    
    @given(
        unknown_cmd=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
            min_size=5,
            max_size=20
        ).filter(lambda x: not any(kw in x.lower() for kw in [
            'ls', 'dir', 'docker', 'kubectl', 'get', 'childitem',
            'grep', 'find', 'search', 'findstr', 'select', 'string',
            'tail', 'cat', 'log', 'journalctl', 'content', 'aws', 'list'
        ]))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_unknown_command_defaults(self, unknown_cmd):
        """
        Feature: output-management, Property 4: Output Type Detection (DEFAULT)
        
        For any command without recognized keywords and non-JSON output, 
        the TypeDetector SHALL classify it as DEFAULT type.
        
        Validates: Requirements 8.1
        """
        detector = TypeDetector()
        output_type = detector.detect(unknown_cmd, "some regular output")
        
        assert output_type == OutputType.DEFAULT, \
            f"Unknown command '{unknown_cmd}' should default to DEFAULT type"


class TestOutputManagementConfigUnitTests:
    """Unit tests for OutputManagementConfig."""
    
    def test_default_config_values(self):
        """Test that default config has expected values."""
        config = OutputManagementConfig()
        
        assert config.enabled is True
        assert config.show_warnings is True
        assert config.limits == DEFAULT_LIMITS
        assert config.safety_limit == 1000
    
    def test_custom_config_values(self):
        """Test that custom config values are preserved."""
        custom_limits = {
            "list": 25,
            "search": 50,
            "log": 100,
            "json": 250,
            "default": 50
        }
        config = OutputManagementConfig(
            enabled=False,
            show_warnings=False,
            limits=custom_limits,
            safety_limit=500
        )
        
        assert config.enabled is False
        assert config.show_warnings is False
        assert config.limits == custom_limits
        assert config.safety_limit == 500


class TestTypeDetectorUnitTests:
    """Unit tests for specific TypeDetector scenarios."""
    
    def test_case_insensitive_detection(self):
        """Test that command detection is case-insensitive."""
        detector = TypeDetector()
        
        assert detector.detect_from_command('LS -la') == OutputType.LIST
        assert detector.detect_from_command('GREP pattern') == OutputType.SEARCH
        assert detector.detect_from_command('TAIL log.txt') == OutputType.LOG
    
    def test_json_with_whitespace(self):
        """Test JSON detection with leading/trailing whitespace."""
        detector = TypeDetector()
        
        assert detector.detect_from_content('   {"key": "value"}') == OutputType.JSON
        assert detector.detect_from_content('\n\n[1, 2, 3]\n') == OutputType.JSON
    
    def test_non_json_content(self):
        """Test that non-JSON content returns None."""
        detector = TypeDetector()
        
        assert detector.detect_from_content('regular text output') is None
        assert detector.detect_from_content('some data here') is None
    
    def test_docker_ps_detection(self):
        """Test docker ps command detection."""
        detector = TypeDetector()
        
        assert detector.detect_from_command('docker ps -a') == OutputType.LIST
        assert detector.detect_from_command('docker ps --all') == OutputType.LIST
    
    def test_aws_list_detection(self):
        """Test AWS list commands detection."""
        detector = TypeDetector()
        
        assert detector.detect_from_command('aws s3 list-buckets') == OutputType.LIST
        assert detector.detect_from_command('aws lambda list-functions') == OutputType.LIST
        assert detector.detect_from_command('aws ec2 list-instances') == OutputType.LIST
    
    def test_powershell_commands(self):
        """Test PowerShell command detection."""
        detector = TypeDetector()
        
        assert detector.detect_from_command('Get-ChildItem') == OutputType.LIST
        assert detector.detect_from_command('Select-String pattern') == OutputType.SEARCH
        assert detector.detect_from_command('Get-Content app.log') == OutputType.LOG


class TestTruncatorProperties:
    """Property-based tests for Truncator."""
    
    @given(
        num_lines=st.integers(min_value=101, max_value=1000),
        limit=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_basic_truncation_correctness(self, num_lines, limit):
        """
        Feature: output-management, Property 1: Basic Truncation Correctness
        
        For any command output with N lines where N > limit, the Output_Manager 
        SHALL return exactly `limit` lines, preserve the first `limit` lines 
        unchanged, and append a warning containing both the total count (N) 
        and shown count (limit).
        
        Validates: Requirements 1.1, 1.2, 1.3, 12.1, 12.2
        """
        # Generate output with num_lines
        lines = [f"line {i}" for i in range(num_lines)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, limit, OutputType.DEFAULT)
        
        # Check that truncation occurred
        assert result.was_truncated is True, \
            f"Output with {num_lines} lines should be truncated with limit {limit}"
        
        # Check that exactly limit lines are returned
        result_lines = result.output.split('\n')
        assert len(result_lines) == limit, \
            f"Truncated output should have exactly {limit} lines, got {len(result_lines)}"
        
        # Check that first limit lines are preserved unchanged
        for i in range(limit):
            assert result_lines[i] == lines[i], \
                f"Line {i} should be preserved unchanged"
        
        # Check metadata
        assert result.total_lines == num_lines, \
            f"Total lines should be {num_lines}, got {result.total_lines}"
        assert result.shown_lines == limit, \
            f"Shown lines should be {limit}, got {result.shown_lines}"
        
        # Check that warning exists and contains counts
        assert result.warning is not None, "Warning should exist for truncated output"
        assert str(num_lines) in result.warning, \
            f"Warning should contain total count {num_lines}"
        assert str(limit) in result.warning, \
            f"Warning should contain shown count {limit}"
        
        # Check percentage calculation
        expected_percentage = int((limit / num_lines) * 100)
        assert str(expected_percentage) in result.warning, \
            f"Warning should contain percentage {expected_percentage}%"
    
    @given(
        num_lines=st.integers(min_value=1, max_value=100),
        limit=st.integers(min_value=100, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_non_truncation_preservation(self, num_lines, limit):
        """
        Feature: output-management, Property 2: Non-Truncation Preservation
        
        For any command output with N lines where N <= limit, the Output_Manager 
        SHALL return the complete output unchanged with no warning appended.
        
        Validates: Requirements 1.4
        """
        # Generate output with num_lines (always <= limit)
        lines = [f"line {i}" for i in range(num_lines)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, limit, OutputType.DEFAULT)
        
        # Check that no truncation occurred
        assert result.was_truncated is False, \
            f"Output with {num_lines} lines should not be truncated with limit {limit}"
        
        # Check that output is unchanged
        assert result.output == output, \
            "Output should be unchanged when under limit"
        
        # Check metadata
        assert result.total_lines == num_lines, \
            f"Total lines should be {num_lines}, got {result.total_lines}"
        assert result.shown_lines == num_lines, \
            f"Shown lines should be {num_lines}, got {result.shown_lines}"
        
        # Check that no warning exists
        assert result.warning is None, \
            "Warning should not exist for non-truncated output"
    
    @given(
        num_items=st.integers(min_value=10, max_value=100),
        limit=st.integers(min_value=5, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_json_truncation_integrity(self, num_items, limit):
        """
        Feature: output-management, Property 5: JSON Truncation Integrity
        
        For any JSON array output that is truncated, the resulting output 
        SHALL be valid JSON (parseable without errors) by truncating at 
        complete object boundaries.
        
        Validates: Requirements 5.4, 5.5
        """
        import json
        
        # Generate a JSON array with num_items objects
        items = [{"id": i, "name": f"item_{i}", "value": i * 10} for i in range(num_items)]
        json_output = json.dumps(items, indent=2)
        
        # Only test when truncation will occur
        output_lines = len(json_output.split('\n'))
        if output_lines <= limit:
            # Skip this test case - no truncation will occur
            return
        
        truncator = Truncator()
        result = truncator.truncate_json(json_output, limit)
        
        # Check that truncation occurred
        assert result.was_truncated is True, \
            f"JSON with {output_lines} lines should be truncated with limit {limit}"
        
        # Check that the truncated output is valid JSON
        try:
            truncated_data = json.loads(result.output)
        except json.JSONDecodeError as e:
            pytest.fail(f"Truncated JSON should be valid, but got error: {e}")
        
        # Check that it's still an array
        assert isinstance(truncated_data, list), \
            "Truncated JSON array should still be an array"
        
        # Check that we have fewer items than original
        assert len(truncated_data) < len(items), \
            "Truncated array should have fewer items than original"
        
        # Check that items are preserved in order
        for i, item in enumerate(truncated_data):
            assert item == items[i], \
                f"Item {i} should be preserved unchanged in truncated output"


class TestTruncatorUnitTests:
    """Unit tests for specific Truncator scenarios."""
    
    def test_empty_output(self):
        """Test that empty output is handled correctly."""
        truncator = Truncator()
        result = truncator.truncate("", 100, OutputType.DEFAULT)
        
        assert result.was_truncated is False
        assert result.output == ""
        assert result.total_lines == 1  # Empty string splits to one empty line
        assert result.warning is None
    
    def test_single_line_output(self):
        """Test that single line output is not truncated."""
        truncator = Truncator()
        result = truncator.truncate("single line", 100, OutputType.DEFAULT)
        
        assert result.was_truncated is False
        assert result.output == "single line"
        assert result.total_lines == 1
        assert result.warning is None
    
    def test_exactly_at_limit(self):
        """Test output exactly at the limit."""
        lines = [f"line {i}" for i in range(100)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, 100, OutputType.DEFAULT)
        
        assert result.was_truncated is False
        assert result.output == output
        assert result.total_lines == 100
        assert result.warning is None
    
    def test_one_over_limit(self):
        """Test output one line over the limit."""
        lines = [f"line {i}" for i in range(101)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, 100, OutputType.DEFAULT)
        
        assert result.was_truncated is True
        assert result.shown_lines == 100
        assert result.total_lines == 101
        assert result.warning is not None
    
    def test_warning_format_contains_emoji(self):
        """Test that warning contains visual indicator."""
        lines = [f"line {i}" for i in range(200)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, 100, OutputType.DEFAULT)
        
        assert "⚠️" in result.warning or "⚠" in result.warning
    
    def test_warning_format_contains_counts(self):
        """Test that warning contains total and shown counts."""
        lines = [f"line {i}" for i in range(200)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, 100, OutputType.DEFAULT)
        
        assert "200" in result.warning
        assert "100" in result.warning
    
    def test_warning_format_contains_percentage(self):
        """Test that warning contains percentage."""
        lines = [f"line {i}" for i in range(200)]
        output = '\n'.join(lines)
        
        truncator = Truncator()
        result = truncator.truncate(output, 100, OutputType.DEFAULT)
        
        # 100/200 = 50%
        assert "50%" in result.warning
    
    def test_json_truncation_with_analyzer(self):
        """Test JSON truncation with analyzer integration."""
        from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
        import json
        
        # Create a large JSON array
        items = [{"id": i, "name": f"item_{i}"} for i in range(100)]
        json_output = json.dumps(items, indent=2)
        
        analyzer = JsonAnalyzerTool()
        truncator = Truncator(json_analyzer=analyzer)
        result = truncator.truncate_json(json_output, 50)
        
        assert result.was_truncated is True
        # Verify the output is still valid JSON
        truncated_data = json.loads(result.output)
        assert isinstance(truncated_data, list)
        assert len(truncated_data) < len(items)
    
    def test_json_truncation_fallback_on_invalid_json(self):
        """Test that invalid JSON falls back to line-based truncation."""
        invalid_json = "{\n" + "\n".join([f"  line {i}" for i in range(100)])
        
        truncator = Truncator()
        result = truncator.truncate_json(invalid_json, 50)
        
        assert result.was_truncated is True
        assert result.shown_lines == 50
        # Should still return a result even though JSON is invalid
    
    def test_json_single_object_truncation(self):
        """Test JSON truncation with a single large object."""
        import json
        
        large_obj = {f"key_{i}": f"value_{i}" for i in range(100)}
        json_output = json.dumps(large_obj, indent=2)
        
        truncator = Truncator()
        result = truncator.truncate_json(json_output, 50)
        
        assert result.was_truncated is True
        # For single objects, falls back to line-based truncation


class TestOutputManagerProperties:
    """Property-based tests for OutputManager."""
    
    @given(
        output_type=st.sampled_from([
            (OutputType.LIST, ['ls -la', 'dir', 'docker ps'], 50),
            (OutputType.SEARCH, ['grep pattern', 'find . -name'], 100),
            (OutputType.LOG, ['tail -f log.txt', 'cat error.log'], 200),
            (OutputType.JSON, ['aws lambda list-functions --output json'], 500),
            (OutputType.DEFAULT, ['echo hello', 'unknown command'], 100)
        ]),
        num_lines=st.integers(min_value=150, max_value=600)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_type_specific_limit_application(self, output_type, num_lines):
        """
        Feature: output-management, Property 3: Type-Specific Limit Application
        
        For any command and output pair, the Output_Manager SHALL apply the 
        correct limit based on detected type: 50 for list commands, 100 for 
        search commands, 200 for log commands, 500 for JSON output, and 100 
        for unknown types.
        
        Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6
        """
        expected_type, commands, expected_limit = output_type
        command = commands[0]  # Use first command from the list
        
        # Generate output with num_lines
        if expected_type == OutputType.JSON:
            # Generate JSON output
            import json
            items = [{"id": i, "value": f"item_{i}"} for i in range(num_lines // 3)]
            output = json.dumps(items, indent=2)
        else:
            # Generate regular text output
            lines = [f"line {i}" for i in range(num_lines)]
            output = '\n'.join(lines)
        
        # Create OutputManager with default config
        manager = OutputManager()
        result = manager.process_output(output, command, override_limit=False)
        
        # Verify the correct limit was applied based on type
        if result.was_truncated:
            # For JSON, the actual shown lines might be less than limit due to object boundaries
            if expected_type == OutputType.JSON:
                assert result.shown_lines <= expected_limit, \
                    f"JSON output should be truncated to at most {expected_limit} lines"
            else:
                assert result.shown_lines == expected_limit, \
                    f"{expected_type.value} output should be truncated to exactly {expected_limit} lines"
        
        # Verify the output type was detected correctly
        assert result.output_type == expected_type, \
            f"Command '{command}' should be detected as {expected_type.value} type"
    
    @given(
        num_lines=st.integers(min_value=1001, max_value=2000),
        safety_limit=st.integers(min_value=500, max_value=1000)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_safety_limit_enforcement(self, num_lines, safety_limit):
        """
        Feature: output-management, Property 7: Safety Limit Enforcement
        
        For any output processed with override_limit=True, the Output_Manager 
        SHALL still apply the safety limit of 1000 lines and include a file 
        export suggestion in the warning when the safety limit is reached.
        
        Validates: Requirements 11.4, 11.5
        """
        # Generate output with num_lines (always > safety_limit)
        lines = [f"line {i}" for i in range(num_lines)]
        output = '\n'.join(lines)
        
        # Create OutputManager with custom safety limit
        config = OutputManagementConfig(safety_limit=safety_limit)
        manager = OutputManager(config=config)
        
        # Process with override_limit=True
        result = manager.process_output(output, "echo test", override_limit=True)
        
        # Verify truncation occurred
        assert result.was_truncated is True, \
            f"Output with {num_lines} lines should be truncated with safety limit {safety_limit}"
        
        # Verify safety limit was applied
        assert result.shown_lines == safety_limit, \
            f"Override mode should apply safety limit of {safety_limit} lines, got {result.shown_lines}"
        
        # Verify file export suggestion is included
        assert result.warning is not None, \
            "Warning should exist when safety limit is reached"
        assert "file" in result.warning.lower() or "export" in result.warning.lower(), \
            "Warning should include file export suggestion when safety limit is reached"
    
    @given(
        total_lines=st.integers(min_value=101, max_value=1000),
        shown_lines=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_8_truncation_percentage_accuracy(self, total_lines, shown_lines):
        """
        Feature: output-management, Property 8: Truncation Percentage Accuracy
        
        For any truncated output, the warning SHALL display the percentage of 
        output shown, calculated as (shown_lines / total_lines * 100), rounded 
        to the nearest integer.
        
        Validates: Requirements 12.3
        """
        # Generate output with total_lines
        lines = [f"line {i}" for i in range(total_lines)]
        output = '\n'.join(lines)
        
        # Create OutputManager
        manager = OutputManager()
        
        # Use a truncator directly to control the exact truncation
        truncator = Truncator()
        result = truncator.truncate(output, shown_lines, OutputType.DEFAULT)
        
        # Verify truncation occurred
        assert result.was_truncated is True, \
            f"Output with {total_lines} lines should be truncated with limit {shown_lines}"
        
        # Calculate expected percentage
        expected_percentage = int((shown_lines / total_lines) * 100)
        
        # Verify warning contains the correct percentage
        assert result.warning is not None, \
            "Warning should exist for truncated output"
        assert f"{expected_percentage}%" in result.warning, \
            f"Warning should contain percentage {expected_percentage}%, got: {result.warning}"


class TestOutputManagerUnitTests:
    """Unit tests for OutputManager."""
    
    def test_output_manager_initialization_with_config(self):
        """Test OutputManager initialization with custom config."""
        custom_config = OutputManagementConfig(
            enabled=True,
            show_warnings=True,
            limits={"list": 25, "search": 50, "log": 100, "json": 250, "default": 50},
            safety_limit=500
        )
        
        manager = OutputManager(config=custom_config)
        
        assert manager.is_enabled() is True
        assert manager.get_limit_for_type(OutputType.LIST) == 25
        assert manager.get_limit_for_type(OutputType.SEARCH) == 50
        assert manager.get_limit_for_type(OutputType.LOG) == 100
        assert manager.get_limit_for_type(OutputType.JSON) == 250
        assert manager.get_limit_for_type(OutputType.DEFAULT) == 50
    
    def test_output_manager_initialization_from_settings(self):
        """Test OutputManager initialization from SettingsManager."""
        manager = OutputManager.from_settings()
        
        # Should use default limits from SettingsManager
        assert manager.is_enabled() is True
        assert manager.get_limit_for_type(OutputType.LIST) == 50
        assert manager.get_limit_for_type(OutputType.SEARCH) == 100
    
    def test_output_manager_disabled(self):
        """Test OutputManager when disabled."""
        config = OutputManagementConfig(enabled=False)
        manager = OutputManager(config=config)
        
        # Generate large output
        lines = [f"line {i}" for i in range(200)]
        output = '\n'.join(lines)
        
        result = manager.process_output(output, "ls -la", override_limit=False)
        
        # Should not truncate when disabled
        assert result.was_truncated is False
        assert result.output == output
        assert result.total_lines == 200
        assert result.shown_lines == 200
    
    def test_output_manager_list_command(self):
        """Test OutputManager with list command."""
        manager = OutputManager()
        
        # Generate 100 lines of output
        lines = [f"file_{i}.txt" for i in range(100)]
        output = '\n'.join(lines)
        
        result = manager.process_output(output, "ls -la", override_limit=False)
        
        # Should truncate to 50 lines (LIST limit)
        assert result.was_truncated is True
        assert result.shown_lines == 50
        assert result.output_type == OutputType.LIST
    
    def test_output_manager_search_command(self):
        """Test OutputManager with search command."""
        manager = OutputManager()
        
        # Generate 150 lines of output
        lines = [f"match {i}" for i in range(150)]
        output = '\n'.join(lines)
        
        result = manager.process_output(output, "grep pattern file.txt", override_limit=False)
        
        # Should truncate to 100 lines (SEARCH limit)
        assert result.was_truncated is True
        assert result.shown_lines == 100
        assert result.output_type == OutputType.SEARCH
    
    def test_output_manager_log_command(self):
        """Test OutputManager with log command."""
        manager = OutputManager()
        
        # Generate 300 lines of output (avoid starting with [ to prevent JSON detection)
        lines = [f"INFO: log entry {i}" for i in range(300)]
        output = '\n'.join(lines)
        
        result = manager.process_output(output, "tail -f /var/log/syslog", override_limit=False)
        
        # Should truncate to 200 lines (LOG limit)
        assert result.was_truncated is True
        assert result.shown_lines == 200
        assert result.output_type == OutputType.LOG
    
    def test_output_manager_json_output(self):
        """Test OutputManager with JSON output."""
        import json
        
        manager = OutputManager()
        
        # Generate large JSON array
        items = [{"id": i, "name": f"item_{i}"} for i in range(200)]
        output = json.dumps(items, indent=2)
        
        result = manager.process_output(output, "aws lambda list-functions", override_limit=False)
        
        # Should truncate to 500 lines (JSON limit)
        assert result.was_truncated is True
        assert result.output_type == OutputType.JSON
        # JSON truncation preserves object boundaries, so might be less than 500
        assert result.shown_lines <= 500
    
    def test_output_manager_detect_output_type(self):
        """Test output type detection."""
        manager = OutputManager()
        
        assert manager.detect_output_type("ls -la", "file1\nfile2") == OutputType.LIST
        assert manager.detect_output_type("grep test", "match1\nmatch2") == OutputType.SEARCH
        assert manager.detect_output_type("tail log.txt", "log line") == OutputType.LOG
        assert manager.detect_output_type("echo test", '{"key": "value"}') == OutputType.JSON
        assert manager.detect_output_type("unknown", "output") == OutputType.DEFAULT


class TestStreamingTruncationProperties:
    """Property-based tests for streaming truncation."""
    
    @given(
        num_lines=st.integers(min_value=1, max_value=500),
        limit=st.integers(min_value=50, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_streaming_truncation_consistency(self, num_lines, limit):
        """
        Feature: output-management, Property 6: Streaming Truncation Consistency
        
        For any streaming command output, the Output_Manager SHALL count lines 
        in real-time, stop yielding after reaching the limit, yield a truncation 
        warning as the final chunk when truncated, and include truncation metadata 
        in the final TruncationResult.
        
        Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
        """
        # Generate streaming output
        def generate_stream():
            for i in range(num_lines):
                yield f"line {i}\n"
        
        # Create OutputManager with custom limit
        config = OutputManagementConfig(
            limits={
                "list": limit,
                "search": limit,
                "log": limit,
                "json": limit,
                "default": limit
            }
        )
        manager = OutputManager(config=config)
        
        # Process the stream
        stream_gen = manager.process_stream(generate_stream(), "echo test", override_limit=False)
        
        # Collect all yielded chunks
        yielded_chunks = []
        result = None
        try:
            while True:
                chunk = next(stream_gen)
                yielded_chunks.append(chunk)
        except StopIteration as e:
            result = e.value
        
        # Verify result exists
        assert result is not None, "process_stream should return TruncationResult"
        
        # Reconstruct the yielded output
        yielded_output = ''.join(yielded_chunks)
        
        # Count lines in yielded output
        yielded_lines = yielded_output.count('\n')
        
        if num_lines > limit:
            # Truncation should have occurred
            assert result.was_truncated is True, \
                f"Stream with {num_lines} lines should be truncated with limit {limit}"
            
            # Should have stopped yielding after limit
            # Note: The warning is also yielded, so we need to check the actual content
            assert result.shown_lines == limit, \
                f"Should show exactly {limit} lines, got {result.shown_lines}"
            
            # Truncation warning should be yielded as final chunk
            assert result.warning is not None, \
                "Warning should exist for truncated stream"
            
            # The warning should be in the yielded output
            assert result.warning in yielded_output, \
                "Truncation warning should be yielded as final chunk"
            
            # Verify metadata
            assert result.total_lines == num_lines, \
                f"Total lines should be {num_lines}, got {result.total_lines}"
            
            # Verify warning contains counts
            assert str(num_lines) in result.warning, \
                f"Warning should contain total count {num_lines}"
            assert str(limit) in result.warning, \
                f"Warning should contain shown count {limit}"
        else:
            # No truncation should have occurred
            assert result.was_truncated is False, \
                f"Stream with {num_lines} lines should not be truncated with limit {limit}"
            
            # All lines should be yielded
            assert result.shown_lines == num_lines, \
                f"Should show all {num_lines} lines"
            
            # No warning should be yielded
            assert result.warning is None, \
                "Warning should not exist for non-truncated stream"
            
            # Verify metadata
            assert result.total_lines == num_lines, \
                f"Total lines should be {num_lines}, got {result.total_lines}"










