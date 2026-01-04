"""Property-based tests for user input path utilities.

Feature: direct-command-execution
"""
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings
from shello_cli.ui.user_input import abbreviate_path, truncate_path


# Feature: direct-command-execution, Property 6: Home Directory Abbreviation
# Validates: Requirements 3.3
@settings(max_examples=100)
@given(
    suffix=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='/-_.'
        ),
        min_size=0,
        max_size=100
    )
)
def test_home_directory_abbreviation(suffix):
    """For any path that starts with the user's home directory,
    the path abbreviation function SHALL replace the home directory prefix with ~.
    """
    home_dir = str(Path.home())
    
    # Create a path that starts with home directory
    if suffix and not suffix.startswith('/'):
        suffix = '/' + suffix
    full_path = home_dir + suffix
    
    # Apply abbreviation
    abbreviated = abbreviate_path(full_path)
    
    # Verify the home directory is replaced with ~
    assert abbreviated.startswith('~'), \
        f"Path starting with home directory should be abbreviated with ~, got: {abbreviated}"
    
    # Verify the suffix is preserved
    assert abbreviated == '~' + suffix, \
        f"Expected '~{suffix}', got '{abbreviated}'"


# Test that non-home paths are unchanged
@settings(max_examples=100)
@given(
    path=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='/-_.'
        ),
        min_size=1,
        max_size=100
    ).filter(lambda p: not p.startswith(str(Path.home())))
)
def test_non_home_paths_unchanged(path):
    """Paths that don't start with home directory should remain unchanged."""
    # Ensure path doesn't accidentally start with home
    home_dir = str(Path.home())
    if path.startswith(home_dir):
        return  # Skip this example
    
    abbreviated = abbreviate_path(path)
    assert abbreviated == path, \
        f"Non-home path should be unchanged, expected '{path}', got '{abbreviated}'"



# Feature: direct-command-execution, Property 7: Long Path Truncation
# Validates: Requirements 3.4
@settings(max_examples=100)
@given(
    path=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='/-_.'
        ),
        min_size=41,  # Longer than max_length
        max_size=200
    ),
    max_length=st.integers(min_value=10, max_value=50)
)
def test_long_path_truncation(path, max_length):
    """For any path longer than the maximum display length,
    the truncation function SHALL return a path prefixed with "..."
    that fits within the limit while preserving the rightmost path components.
    """
    # Only test paths that are actually longer than max_length
    if len(path) <= max_length:
        return
    
    truncated = truncate_path(path, max_length)
    
    # Verify the truncated path fits within the limit
    assert len(truncated) <= max_length, \
        f"Truncated path should be <= {max_length} chars, got {len(truncated)}"
    
    # Verify it starts with "..."
    assert truncated.startswith("..."), \
        f"Truncated path should start with '...', got: {truncated}"
    
    # Verify the rightmost components are preserved
    expected_suffix = path[-(max_length - 3):]
    assert truncated == "..." + expected_suffix, \
        f"Expected '...{expected_suffix}', got '{truncated}'"


# Test that short paths are unchanged
@settings(max_examples=100)
@given(
    path=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='/-_.'
        ),
        min_size=0,
        max_size=40
    )
)
def test_short_paths_unchanged(path):
    """Paths shorter than or equal to max_length should remain unchanged."""
    max_length = 40
    
    truncated = truncate_path(path, max_length)
    
    assert truncated == path, \
        f"Short path should be unchanged, expected '{path}', got '{truncated}'"



# Feature: direct-command-execution, Property 5: Prompt Format with Directory
# Validates: Requirements 3.1, 3.2, 3.5
@settings(max_examples=100)
@given(
    username=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        ),
        min_size=1,
        max_size=20
    ),
    directory=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='/-_.'
        ),
        min_size=1,
        max_size=100
    )
)
def test_prompt_format_with_directory(username, directory):
    """For any username and directory path, the prompt renderer SHALL produce output
    matching the format 🌊 {username} [{path}]\n──└─⟩ where path reflects the current
    working directory.
    """
    from shello_cli.ui.user_input import build_prompt_parts
    
    # Build prompt parts
    prompt_parts = build_prompt_parts(username, directory)
    
    # Extract text from prompt parts
    prompt_text = ''.join(text for _, text in prompt_parts)
    
    # Verify format: 🌊 username [path]\n──└─⟩ 
    assert prompt_text.startswith('🌊 '), \
        f"Prompt should start with '🌊 ', got: {prompt_text[:5]}"
    
    assert username in prompt_text, \
        f"Prompt should contain username '{username}', got: {prompt_text}"
    
    # Check for path in brackets
    assert '[' in prompt_text and ']' in prompt_text, \
        f"Prompt should contain path in brackets, got: {prompt_text}"
    
    # Check for arrow on new line
    assert '\n──└─⟩ ' in prompt_text, \
        f"Prompt should contain '\\n──└─⟩ ', got: {prompt_text}"
    
    # Verify the general structure
    lines = prompt_text.split('\n')
    assert len(lines) == 2, \
        f"Prompt should have 2 lines, got {len(lines)}: {lines}"
    
    # First line should have icon, username, and path
    first_line = lines[0]
    assert '🌊' in first_line, f"First line should contain icon, got: {first_line}"
    assert username in first_line, f"First line should contain username, got: {first_line}"
    assert '[' in first_line and ']' in first_line, \
        f"First line should contain path in brackets, got: {first_line}"
    
    # Second line should be the arrow
    assert lines[1] == '──└─⟩ ', \
        f"Second line should be '──└─⟩ ', got: '{lines[1]}'"


# Test prompt without directory
@settings(max_examples=100)
@given(
    username=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        ),
        min_size=1,
        max_size=20
    )
)
def test_prompt_format_without_directory(username):
    """Prompt without directory should not include brackets."""
    from shello_cli.ui.user_input import build_prompt_parts
    
    # Build prompt parts without directory
    prompt_parts = build_prompt_parts(username, None)
    
    # Extract text from prompt parts
    prompt_text = ''.join(text for _, text in prompt_parts)
    
    # Verify format: 🌊 username\n──└─⟩ 
    assert prompt_text.startswith('🌊 '), \
        f"Prompt should start with '🌊 ', got: {prompt_text[:5]}"
    
    assert username in prompt_text, \
        f"Prompt should contain username '{username}', got: {prompt_text}"
    
    # Should NOT have brackets when no directory
    assert '[' not in prompt_text and ']' not in prompt_text, \
        f"Prompt without directory should not have brackets, got: {prompt_text}"
    
    # Check for arrow on new line
    assert '\n──└─⟩ ' in prompt_text, \
        f"Prompt should contain '\\n──└─⟩ ', got: {prompt_text}"
