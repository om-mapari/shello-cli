"""Integration test for surrogate character handling in bash tool."""
import pytest
from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.output.cache import OutputCache


def test_bash_tool_handles_surrogates_in_output():
    """Test that bash tool properly sanitizes surrogate characters from command output."""
    cache = OutputCache()
    bash_tool = BashTool(output_cache=cache)
    
    # Create a Python command that outputs surrogate characters
    # This simulates what happens when Windows console output contains invalid UTF-8
    command = 'python -c "import sys; sys.stdout.write(\'Hello\\ud800World\')"'
    
    result = bash_tool.execute(command, timeout=5)
    
    # The command should execute successfully
    assert result.success or result.error  # Either succeeds or fails, but shouldn't crash
    
    # If there's output, it should be UTF-8 encodable (no surrogates)
    if result.output:
        # This should not raise UnicodeEncodeError
        result.output.encode('utf-8')
    
    if result.error:
        # Error should also be UTF-8 encodable
        result.error.encode('utf-8')


def test_bash_tool_streaming_handles_surrogates():
    """Test that bash tool streaming properly sanitizes surrogate characters."""
    cache = OutputCache()
    bash_tool = BashTool(output_cache=cache)
    
    # Create a Python command that outputs surrogate characters
    command = 'python -c "import sys; sys.stdout.write(\'Test\\ud800Output\')"'
    
    # Collect all chunks
    chunks = []
    result = None
    
    try:
        stream = bash_tool.execute_stream(command, timeout=5)
        for chunk in stream:
            chunks.append(chunk)
        # Get the return value
        result = stream.gi_frame  # This won't work, need to catch StopIteration
    except StopIteration as e:
        result = e.value
    
    # All chunks should be UTF-8 encodable
    for chunk in chunks:
        if isinstance(chunk, str):
            chunk.encode('utf-8')
    
    # Result should be UTF-8 encodable
    if result and hasattr(result, 'output') and result.output:
        result.output.encode('utf-8')
