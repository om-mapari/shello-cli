"""
Integration tests for Smart Output Management.

These tests verify the complete output management pipeline including:
- Install command flow with FIRST_LAST strategy
- Semantic truncation with error detection
- JSON analyzer integration
- Progress bar compression

Feature: output-management
"""

import json
import pytest
from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.get_cached_output_tool import GetCachedOutputTool
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from shello_cli.tools.output.types import TruncationStrategy


@pytest.mark.integration
class TestInstallCommandFlow:
    """
    Integration test for install command flow.
    
    Requirements: 13.1, 14.1, 15.1
    """
    
    def test_install_command_with_first_last_strategy(self):
        """
        Test install command flow:
        - Execute npm install (simulated)
        - Verify FIRST_LAST strategy
        - Verify cache_id in summary
        - Retrieve last 50 lines via get_cached_output
        
        Validates: Requirements 13.1, 14.1, 15.1
        """
        # Create shared cache
        cache = OutputCache()
        
        # Create OutputManager with cache
        manager = OutputManager(cache=cache)
        
        # Simulate npm install output (large enough to trigger truncation)
        install_output = self._generate_install_output(lines=300)
        command = "npm install"
        
        # Process output
        result = manager.process_output(install_output, command)
        
        # Verify FIRST_LAST strategy was used
        assert result.strategy == TruncationStrategy.FIRST_LAST, \
            "Install commands should use FIRST_LAST strategy"
        
        # Verify output was truncated
        assert result.was_truncated, \
            "Large install output should be truncated"
        
        # Verify cache_id is present
        assert result.cache_id is not None, \
            "Truncated output must have cache_id"
        assert result.cache_id.startswith("cmd_"), \
            "Cache ID should have correct format"
        
        # Verify cache_id in summary
        assert result.cache_id in result.summary, \
            "Summary must contain cache_id"
        
        # Verify summary mentions FIRST_LAST strategy
        assert "FIRST_LAST" in result.summary or "first" in result.summary.lower(), \
            "Summary should mention FIRST_LAST strategy"
        
        # Verify summary suggests get_cached_output
        assert "get_cached_output" in result.summary, \
            "Summary should suggest get_cached_output"
        
        # Create GetCachedOutputTool with same cache
        get_tool = GetCachedOutputTool(cache=cache)
        
        # Retrieve last 50 lines
        retrieval_result = get_tool.execute(cache_id=result.cache_id, lines="-50")
        
        # Verify retrieval succeeded
        assert retrieval_result.success, \
            f"Retrieval should succeed: {retrieval_result.error}"
        
        # Verify we got output
        assert retrieval_result.output, \
            "Should retrieve output from cache"
        
        # Verify we got approximately 50 lines (or less if output is smaller)
        retrieved_lines = retrieval_result.output.strip().split('\n')
        assert len(retrieved_lines) <= 50, \
            "Should retrieve at most 50 lines"
        
        # Verify the retrieved lines are from the end
        original_lines = install_output.strip().split('\n')
        last_50_original = original_lines[-50:]
        
        # Check that retrieved lines match the last lines of original
        for i, line in enumerate(retrieved_lines):
            expected_line = last_50_original[i] if i < len(last_50_original) else ""
            assert line == expected_line, \
                f"Retrieved line {i} should match original"
        
        print(f"\n✓ Install command flow test passed")
        print(f"✓ Strategy: {result.strategy.value}")
        print(f"✓ Cache ID: {result.cache_id}")
        print(f"✓ Retrieved {len(retrieved_lines)} lines from cache")
    
    def _generate_install_output(self, lines: int) -> str:
        """Generate simulated npm install output.
        
        Args:
            lines: Number of lines to generate
            
        Returns:
            Simulated install output
        """
        output_lines = [
            "npm WARN deprecated package@1.0.0: This package is deprecated",
            "npm WARN deprecated another-package@2.0.0: Use new-package instead",
            "",
            "added 150 packages, and audited 151 packages in 5s",
            "",
            "10 packages are looking for funding",
            "  run `npm fund` for details",
            "",
        ]
        
        # Add package installation lines with longer text to exceed 8K chars
        for i in range(lines - len(output_lines) - 5):
            # Make each line longer to ensure we exceed the 8000 char limit
            output_lines.append(
                f"added package-{i}@1.0.{i % 10} from registry with dependencies "
                f"and peer dependencies resolved successfully"
            )
        
        # Add final summary
        output_lines.extend([
            "",
            "found 0 vulnerabilities",
            "",
            "Done in 5.23s"
        ])
        
        return '\n'.join(output_lines)


@pytest.mark.integration
class TestSemanticTruncationWithErrors:
    """
    Integration test for semantic truncation with error detection.
    
    Requirements: 16.5, 16.6
    """
    
    def test_semantic_truncation_preserves_critical_lines(self):
        """
        Test semantic truncation with errors:
        - Execute command with errors in middle
        - Verify CRITICAL lines in output
        - Verify semantic stats in summary
        
        Validates: Requirements 16.5, 16.6
        """
        # Create OutputManager
        manager = OutputManager()
        
        # Generate output with errors in the middle (large enough to exceed 15K chars)
        output = self._generate_output_with_errors(
            before_lines=200,
            error_lines=5,
            after_lines=200
        )
        
        command = "pytest tests/"
        
        # Process output
        result = manager.process_output(output, command)
        
        # Verify output was truncated
        assert result.was_truncated, \
            "Large output should be truncated"
        
        # Verify semantic stats are present
        assert result.semantic_stats is not None, \
            "Semantic truncation should provide stats"
        
        # Verify critical lines were detected
        critical_count = result.semantic_stats.get('critical', 0)
        assert critical_count > 0, \
            "Should detect critical lines (errors)"
        
        # Verify critical lines are in the output
        # Check for error keywords
        output_lower = result.output.lower()
        assert 'error' in output_lower or 'fail' in output_lower, \
            "Critical error lines should be preserved in output"
        
        # Verify summary mentions semantic truncation
        assert "Semantic:" in result.summary or "semantic" in result.summary.lower(), \
            "Summary should mention semantic truncation"
        
        # Verify summary shows critical count
        assert "critical" in result.summary.lower(), \
            "Summary should show critical line count"
        
        # Verify the actual critical count is in the summary
        assert str(critical_count) in result.summary, \
            f"Summary should show critical count: {critical_count}"
        
        print(f"\n✓ Semantic truncation test passed")
        print(f"✓ Critical lines detected: {critical_count}")
        print(f"✓ Semantic stats: {result.semantic_stats}")
    
    def _generate_output_with_errors(
        self,
        before_lines: int,
        error_lines: int,
        after_lines: int
    ) -> str:
        """Generate output with errors in the middle.
        
        Args:
            before_lines: Number of normal lines before errors
            error_lines: Number of error lines
            after_lines: Number of normal lines after errors
            
        Returns:
            Output with errors in the middle
        """
        lines = []
        
        # Normal output before errors (make lines longer)
        for i in range(before_lines):
            lines.append(f"test_case_{i} ............................ PASSED [test_module_{i}.py::test_function_{i}]")
        
        # Error lines in the middle
        for i in range(error_lines):
            lines.append(f"ERROR: test_error_{i} failed with exception in module test_errors.py")
            lines.append(f"  File 'test.py', line {i+10}, in test_error_{i}")
            lines.append(f"  AssertionError: Expected value not found - this is a critical error that must be visible")
        
        # Normal output after errors (make lines longer)
        for i in range(after_lines):
            lines.append(f"test_case_{i+before_lines} .............. PASSED [test_module_{i+before_lines}.py::test_function_{i+before_lines}]")
        
        return '\n'.join(lines)


@pytest.mark.integration
class TestJSONAnalyzerIntegration:
    """
    Integration test for JSON analyzer integration.
    
    Requirements: 5.1, 5.2
    """
    
    def test_json_analyzer_for_large_json(self):
        """
        Test JSON analyzer integration:
        - Execute command returning large JSON
        - Verify json_analyzer_tool used
        - Verify jq paths returned
        - Verify cache_id for raw JSON retrieval
        
        Validates: Requirements 5.1, 5.2
        """
        # Create cache and analyzer
        cache = OutputCache()
        analyzer = JsonAnalyzerTool()
        
        # Create OutputManager with both
        manager = OutputManager(cache=cache, json_analyzer=analyzer)
        
        # Generate large JSON (exceeds 20K chars)
        large_json = self._generate_large_json(items=400)
        
        # Verify it exceeds the limit
        assert len(large_json) > 20000, \
            "Test JSON should exceed 20K chars"
        
        command = "aws lambda list-functions"
        
        # Process output
        result = manager.process_output(large_json, command)
        
        # Verify output was truncated
        assert result.was_truncated, \
            "Large JSON should be truncated"
        
        # Verify json_analyzer was used
        assert result.used_json_analyzer, \
            "Should use json_analyzer for large JSON"
        
        # Verify jq paths are in output
        assert "jq path" in result.output or ".items" in result.output, \
            "Output should contain jq paths"
        
        # Verify cache_id is present
        assert result.cache_id is not None, \
            "Should have cache_id for raw JSON retrieval"
        
        # Verify summary mentions json_analyzer
        assert "json_analyzer" in result.summary.lower(), \
            "Summary should mention json_analyzer usage"
        
        # Verify summary suggests get_cached_output for raw JSON
        assert "get_cached_output" in result.summary, \
            "Summary should suggest get_cached_output"
        
        # Create GetCachedOutputTool
        get_tool = GetCachedOutputTool(cache=cache)
        
        # Retrieve raw JSON from cache
        retrieval_result = get_tool.execute(cache_id=result.cache_id, lines="+50")
        
        # Verify retrieval succeeded
        assert retrieval_result.success, \
            f"Should retrieve raw JSON from cache: {retrieval_result.error}"
        
        # Verify we got JSON content
        assert retrieval_result.output, \
            "Should retrieve raw JSON"
        
        # Verify it's valid JSON (at least the first 50 lines)
        retrieved_text = retrieval_result.output.strip()
        assert retrieved_text.startswith('{') or retrieved_text.startswith('['), \
            "Retrieved content should be JSON"
        
        print(f"\n✓ JSON analyzer integration test passed")
        print(f"✓ JSON size: {len(large_json):,} chars")
        print(f"✓ Used json_analyzer: {result.used_json_analyzer}")
        print(f"✓ Cache ID: {result.cache_id}")
    
    def _generate_large_json(self, items: int) -> str:
        """Generate large JSON output.
        
        Args:
            items: Number of items to generate
            
        Returns:
            JSON string
        """
        data = {
            "Functions": [
                {
                    "FunctionName": f"lambda-function-{i}",
                    "FunctionArn": f"arn:aws:lambda:us-east-1:123456789012:function:lambda-function-{i}",
                    "Runtime": "python3.9",
                    "Role": f"arn:aws:iam::123456789012:role/lambda-role-{i}",
                    "Handler": "index.handler",
                    "CodeSize": 1024 * (i % 100 + 1),
                    "Description": f"Lambda function number {i} with some description text",
                    "Timeout": 30,
                    "MemorySize": 128,
                    "LastModified": f"2024-01-{(i % 28) + 1:02d}T12:00:00.000+0000",
                    "Environment": {
                        "Variables": {
                            "ENV": "production",
                            "LOG_LEVEL": "INFO",
                            "REGION": "us-east-1"
                        }
                    }
                }
                for i in range(items)
            ]
        }
        
        return json.dumps(data, indent=2)


@pytest.mark.integration
class TestProgressBarCompression:
    """
    Integration test for progress bar compression.
    
    Requirements: 17.1, 17.5
    """
    
    def test_progress_bar_compression_in_install(self):
        """
        Test progress bar compression:
        - Execute npm install with progress
        - Verify compression occurred
        - Verify compression stats in summary
        
        Validates: Requirements 17.1, 17.5
        """
        # Create OutputManager
        manager = OutputManager()
        
        # Generate output with progress bars
        output = self._generate_output_with_progress(
            packages=50,
            progress_updates=20
        )
        
        command = "npm install"
        
        # Process output
        result = manager.process_output(output, command)
        
        # Verify compression stats are present
        assert result.compression_stats is not None, \
            "Should have compression stats"
        
        # Verify compression occurred (lines were saved)
        lines_saved = result.compression_stats.lines_saved
        assert lines_saved > 0, \
            "Progress bars should be compressed (lines saved > 0)"
        
        # Verify summary mentions compression
        assert "compressed" in result.summary.lower(), \
            "Summary should mention compression"
        
        # Verify summary shows lines saved
        assert "saved" in result.summary.lower(), \
            "Summary should mention lines saved"
        
        # Verify the actual count is in the summary
        assert str(lines_saved) in result.summary, \
            f"Summary should show lines saved: {lines_saved}"
        
        # Verify progress bars are not all in the output
        # (should only have final state)
        progress_count = result.output.count("Progress:")
        assert progress_count < 20, \
            "Should compress progress bars (not all updates in output)"
        
        print(f"\n✓ Progress bar compression test passed")
        print(f"✓ Lines saved: {lines_saved}")
        print(f"✓ Compression stats: {result.compression_stats}")
    
    def _generate_output_with_progress(
        self,
        packages: int,
        progress_updates: int
    ) -> str:
        """Generate output with progress bars.
        
        Args:
            packages: Number of packages to install
            progress_updates: Number of progress updates
            
        Returns:
            Output with progress bars
        """
        lines = []
        
        lines.append("npm install")
        lines.append("")
        
        # Add progress updates
        for i in range(progress_updates):
            percentage = int((i + 1) / progress_updates * 100)
            lines.append(f"Progress: {percentage}% [{i+1}/{progress_updates}]")
        
        lines.append("")
        
        # Add package installations
        for i in range(packages):
            lines.append(f"added package-{i}@1.0.0")
        
        lines.append("")
        lines.append(f"added {packages} packages in 3.5s")
        lines.append("")
        lines.append("found 0 vulnerabilities")
        
        return '\n'.join(lines)


@pytest.mark.integration
class TestEndToEndFlow:
    """
    End-to-end integration test combining all features.
    """
    
    def test_complete_output_management_pipeline(self):
        """
        Test complete pipeline:
        - Large output with progress bars
        - Errors in the middle (semantic)
        - Truncation with FIRST_LAST
        - Caching and retrieval
        """
        # Create shared cache
        cache = OutputCache()
        
        # Create OutputManager
        manager = OutputManager(cache=cache)
        
        # Generate complex output
        output = self._generate_complex_output()
        command = "npm run build"
        
        # Process output
        result = manager.process_output(output, command)
        
        # Verify all features worked
        assert result.was_truncated, "Should be truncated"
        assert result.cache_id is not None, "Should have cache_id"
        assert result.compression_stats is not None, "Should have compression"
        assert result.semantic_stats is not None, "Should have semantic stats"
        assert result.strategy == TruncationStrategy.FIRST_LAST, "Should use FIRST_LAST"
        
        # Verify summary is complete
        assert "OUTPUT SUMMARY" in result.summary or "📊" in result.summary
        assert result.cache_id in result.summary
        assert "get_cached_output" in result.summary
        assert "compressed" in result.summary.lower()
        assert "Semantic:" in result.summary or "semantic" in result.summary.lower()
        
        # Test retrieval
        get_tool = GetCachedOutputTool(cache=cache)
        retrieval = get_tool.execute(cache_id=result.cache_id, lines="-50")
        
        assert retrieval.success, "Should retrieve from cache"
        assert retrieval.output, "Should have output"
        
        print(f"\n✓ End-to-end pipeline test passed")
        print(f"✓ All features working together")
    
    def _generate_complex_output(self) -> str:
        """Generate complex output with all features."""
        lines = []
        
        # Start
        lines.append("npm run build")
        lines.append("")
        
        # Progress bars
        for i in range(20):
            lines.append(f"Building... {i*5}%")
        
        lines.append("")
        
        # Normal output (make it longer to exceed 8K chars for build commands)
        for i in range(150):
            lines.append(f"Compiling module-{i}.js with dependencies and webpack loaders")
        
        # Errors in the middle
        lines.append("ERROR: Failed to compile module-75.js - this is a critical error")
        lines.append("  SyntaxError: Unexpected token in module source code")
        lines.append("  at line 42 in module-75.js")
        
        # More normal output
        for i in range(150, 300):
            lines.append(f"Compiling module-{i}.js with dependencies and webpack loaders")
        
        # Final summary
        lines.append("")
        lines.append("Build completed with 1 error")
        lines.append("Time: 5.23s")
        
        return '\n'.join(lines)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
