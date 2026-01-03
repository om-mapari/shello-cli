"""
Property-based tests for TypeDetector.

Feature: output-management
Tests output type detection from commands and content.
"""

import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.tools.output.type_detector import TypeDetector
from shello_cli.tools.output.types import OutputType


class TestTypeDetectorProperties:
    """Property-based tests for TypeDetector."""
    
    @given(
        command=st.text(min_size=0, max_size=200),
        output=st.text(min_size=0, max_size=1000)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_type_detection_consistency(self, command, output):
        """
        Feature: output-management, Property 6: Type Detection Consistency
        
        For any command and output, type detection SHALL be deterministic 
        (same input → same type).
        
        Validates: Requirements 18.1-18.6
        """
        detector = TypeDetector()
        
        # Detect type twice with same inputs
        type1 = detector.detect(command, output)
        type2 = detector.detect(command, output)
        
        # Should always return the same type
        assert type1 == type2, \
            f"Type detection not consistent: got {type1} then {type2} for command='{command[:50]}...'"
        
        # Should always return a valid OutputType
        assert isinstance(type1, OutputType), \
            f"Expected OutputType, got {type(type1)}"
        
        # Should never return None (defaults to DEFAULT)
        assert type1 is not None, \
            "Type detection should never return None"


class TestTypeDetectorCommandPatterns:
    """Tests for command-based type detection."""
    
    def test_detect_list_commands(self):
        """Test detection of list commands."""
        detector = TypeDetector()
        
        # Test various list commands
        assert detector.detect("ls -la", "") == OutputType.LIST
        assert detector.detect("dir /s", "") == OutputType.LIST
        assert detector.detect("docker ps -a", "") == OutputType.LIST
        assert detector.detect("docker images", "") == OutputType.LIST
        assert detector.detect("aws lambda list-functions", "") == OutputType.LIST
        assert detector.detect("kubectl get pods", "") == OutputType.LIST
        assert detector.detect("Get-ChildItem", "") == OutputType.LIST
    
    def test_detect_search_commands(self):
        """Test detection of search commands."""
        detector = TypeDetector()
        
        assert detector.detect("grep pattern file.txt", "") == OutputType.SEARCH
        assert detector.detect("find . -name '*.py'", "") == OutputType.SEARCH
        assert detector.detect("rg pattern", "") == OutputType.SEARCH
        assert detector.detect("ag pattern", "") == OutputType.SEARCH
        assert detector.detect("Select-String pattern", "") == OutputType.SEARCH
        assert detector.detect("findstr pattern", "") == OutputType.SEARCH
    
    def test_detect_log_commands(self):
        """Test detection of log commands."""
        detector = TypeDetector()
        
        assert detector.detect("tail -f app.log", "") == OutputType.LOG
        assert detector.detect("head -n 100 error.log", "") == OutputType.LOG
        assert detector.detect("cat /var/log/syslog.log", "") == OutputType.LOG
        assert detector.detect("docker logs container_id", "") == OutputType.LOG
        assert detector.detect("journalctl -u service", "") == OutputType.LOG
        assert detector.detect("Get-EventLog", "") == OutputType.LOG
        assert detector.detect("Get-Content app.log", "") == OutputType.LOG
    
    def test_detect_install_commands(self):
        """Test detection of install commands."""
        detector = TypeDetector()
        
        assert detector.detect("npm install express", "") == OutputType.INSTALL
        assert detector.detect("npm i lodash", "") == OutputType.INSTALL
        assert detector.detect("npm ci", "") == OutputType.INSTALL
        assert detector.detect("yarn install", "") == OutputType.INSTALL
        assert detector.detect("yarn add react", "") == OutputType.INSTALL
        assert detector.detect("pip install requests", "") == OutputType.INSTALL
        assert detector.detect("pip3 install numpy", "") == OutputType.INSTALL
        assert detector.detect("cargo install ripgrep", "") == OutputType.INSTALL
        assert detector.detect("gem install rails", "") == OutputType.INSTALL
        assert detector.detect("apt install nginx", "") == OutputType.INSTALL
        assert detector.detect("apt-get install curl", "") == OutputType.INSTALL
        assert detector.detect("brew install wget", "") == OutputType.INSTALL
        assert detector.detect("choco install git", "") == OutputType.INSTALL
    
    def test_detect_build_commands(self):
        """Test detection of build commands."""
        detector = TypeDetector()
        
        assert detector.detect("npm run build", "") == OutputType.BUILD
        assert detector.detect("yarn build", "") == OutputType.BUILD
        assert detector.detect("cargo build --release", "") == OutputType.BUILD
        assert detector.detect("go build main.go", "") == OutputType.BUILD
        assert detector.detect("mvn compile", "") == OutputType.BUILD
        assert detector.detect("mvn package", "") == OutputType.BUILD
        assert detector.detect("gradle build", "") == OutputType.BUILD
        assert detector.detect("docker build -t myapp .", "") == OutputType.BUILD
        assert detector.detect("make", "") == OutputType.BUILD
    
    def test_detect_test_commands(self):
        """Test detection of test commands."""
        detector = TypeDetector()
        
        assert detector.detect("pytest", "") == OutputType.TEST
        assert detector.detect("python -m pytest tests/", "") == OutputType.TEST
        assert detector.detect("npm test", "") == OutputType.TEST
        assert detector.detect("npm run test", "") == OutputType.TEST
        assert detector.detect("yarn test", "") == OutputType.TEST
        assert detector.detect("jest", "") == OutputType.TEST
        assert detector.detect("vitest run", "") == OutputType.TEST
        assert detector.detect("cargo test", "") == OutputType.TEST
        assert detector.detect("go test ./...", "") == OutputType.TEST
        assert detector.detect("mvn test", "") == OutputType.TEST


class TestTypeDetectorContentPatterns:
    """Tests for content-based type detection."""
    
    def test_detect_json_content(self):
        """Test detection of JSON content."""
        detector = TypeDetector()
        
        # JSON array
        json_array = '[\n  {"id": 1, "name": "test"}\n]'
        assert detector.detect("some command", json_array) == OutputType.JSON
        
        # JSON object
        json_object = '{\n  "status": "ok",\n  "data": []\n}'
        assert detector.detect("some command", json_object) == OutputType.JSON
        
        # JSON with leading whitespace
        json_whitespace = '  \n  [\n    {"key": "value"}\n  ]'
        assert detector.detect("some command", json_whitespace) == OutputType.JSON
    
    def test_detect_test_content(self):
        """Test detection of test output content."""
        detector = TypeDetector()
        
        # Test results with passed/failed
        test_output1 = "10 passed, 2 failed, 1 skipped"
        assert detector.detect("some command", test_output1) == OutputType.TEST
        
        # Test results with status indicators
        test_output2 = "PASSED: test_foo\nFAILED: test_bar\nERROR: test_baz"
        assert detector.detect("some command", test_output2) == OutputType.TEST
        
        # Test results with symbols
        test_output3 = "✓ test_foo\n✗ test_bar\n✔ test_baz"
        assert detector.detect("some command", test_output3) == OutputType.TEST
        
        # Test results with count
        test_output4 = "Tests: 15 passed, 3 failed"
        assert detector.detect("some command", test_output4) == OutputType.TEST
    
    def test_detect_build_content(self):
        """Test detection of build output content."""
        detector = TypeDetector()
        
        # Build success
        build_output1 = "Build succeeded in 5.2s"
        assert detector.detect("some command", build_output1) == OutputType.BUILD
        
        # Build completed
        build_output2 = "Build completed with warnings"
        assert detector.detect("some command", build_output2) == OutputType.BUILD
        
        # Compilation success
        build_output3 = "Compiled successfully in 1234ms"
        assert detector.detect("some command", build_output3) == OutputType.BUILD
        
        # Maven/Gradle style
        build_output4 = "BUILD SUCCESS"
        assert detector.detect("some command", build_output4) == OutputType.BUILD
        
        build_output5 = "BUILD FAILURE"
        assert detector.detect("some command", build_output5) == OutputType.BUILD
        
        # Webpack
        build_output6 = "webpack 5.88.0 compiled successfully"
        assert detector.detect("some command", build_output6) == OutputType.BUILD


class TestTypeDetectorPrecedence:
    """Tests for content detection taking precedence over command detection."""
    
    def test_content_overrides_command(self):
        """Test that content detection takes precedence."""
        detector = TypeDetector()
        
        # Command suggests LIST, but content is JSON
        json_content = '{"items": [1, 2, 3]}'
        result = detector.detect("ls -la", json_content)
        assert result == OutputType.JSON, \
            "Content detection (JSON) should override command detection (LIST)"
        
        # Command suggests SEARCH, but content is TEST results
        test_content = "15 passed, 2 failed"
        result = detector.detect("grep pattern file.txt", test_content)
        assert result == OutputType.TEST, \
            "Content detection (TEST) should override command detection (SEARCH)"
        
        # Command suggests LOG, but content is BUILD output
        build_content = "Build succeeded in 3.5s"
        result = detector.detect("tail -f build.log", build_content)
        assert result == OutputType.BUILD, \
            "Content detection (BUILD) should override command detection (LOG)"
    
    def test_command_used_when_no_content_match(self):
        """Test that command detection is used when content doesn't match."""
        detector = TypeDetector()
        
        # Plain text output, command is LIST
        plain_output = "file1.txt\nfile2.txt\nfile3.txt"
        result = detector.detect("ls -la", plain_output)
        assert result == OutputType.LIST, \
            "Command detection should be used when content doesn't match patterns"
    
    def test_default_when_nothing_matches(self):
        """Test that DEFAULT is returned when nothing matches."""
        detector = TypeDetector()
        
        # Unknown command and plain output
        result = detector.detect("unknown_command", "some plain text output")
        assert result == OutputType.DEFAULT, \
            "Should return DEFAULT when neither command nor content matches"


class TestTypeDetectorEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_command_and_output(self):
        """Test with empty command and output."""
        detector = TypeDetector()
        
        result = detector.detect("", "")
        assert result == OutputType.DEFAULT
    
    def test_empty_command(self):
        """Test with empty command but valid output."""
        detector = TypeDetector()
        
        # JSON content with empty command
        result = detector.detect("", '{"key": "value"}')
        assert result == OutputType.JSON
    
    def test_empty_output(self):
        """Test with valid command but empty output."""
        detector = TypeDetector()
        
        # List command with empty output
        result = detector.detect("ls -la", "")
        assert result == OutputType.LIST
    
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        detector = TypeDetector()
        
        # Uppercase commands
        assert detector.detect("NPM INSTALL express", "") == OutputType.INSTALL
        assert detector.detect("PYTEST", "") == OutputType.TEST
        assert detector.detect("GREP pattern", "") == OutputType.SEARCH
        
        # Mixed case content
        assert detector.detect("", "BUILD SUCCEEDED") == OutputType.BUILD
        assert detector.detect("", "10 PASSED, 2 FAILED") == OutputType.TEST
    
    def test_multiline_content(self):
        """Test detection with multiline content."""
        detector = TypeDetector()
        
        # Multiline JSON
        json_multiline = """
        {
            "status": "ok",
            "data": [
                {"id": 1},
                {"id": 2}
            ]
        }
        """
        assert detector.detect("", json_multiline) == OutputType.JSON
        
        # Multiline test output
        test_multiline = """
        Running tests...
        ✓ test_foo
        ✗ test_bar
        15 passed, 2 failed
        """
        assert detector.detect("", test_multiline) == OutputType.TEST


class TestTypeDetectorMethods:
    """Tests for individual detection methods."""
    
    def test_detect_from_command_returns_none_for_unknown(self):
        """Test that detect_from_command returns None for unknown commands."""
        detector = TypeDetector()
        
        result = detector.detect_from_command("unknown_command")
        assert result is None
    
    def test_detect_from_command_returns_none_for_empty(self):
        """Test that detect_from_command returns None for empty command."""
        detector = TypeDetector()
        
        result = detector.detect_from_command("")
        assert result is None
    
    def test_detect_from_content_returns_none_for_unknown(self):
        """Test that detect_from_content returns None for unknown content."""
        detector = TypeDetector()
        
        result = detector.detect_from_content("plain text output")
        assert result is None
    
    def test_detect_from_content_returns_none_for_empty(self):
        """Test that detect_from_content returns None for empty content."""
        detector = TypeDetector()
        
        result = detector.detect_from_content("")
        assert result is None
