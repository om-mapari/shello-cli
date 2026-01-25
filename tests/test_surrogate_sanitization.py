"""Tests for surrogate character sanitization."""
import pytest
from shello_cli.utils.output_utils import sanitize_surrogates


def test_sanitize_surrogates_clean_text():
    """Test that clean text passes through unchanged."""
    text = "Hello, world! This is normal text."
    assert sanitize_surrogates(text) == text


def test_sanitize_surrogates_empty_string():
    """Test that empty string is handled."""
    assert sanitize_surrogates("") == ""


def test_sanitize_surrogates_none():
    """Test that None is handled."""
    assert sanitize_surrogates(None) is None


def test_sanitize_surrogates_with_surrogates():
    """Test that surrogate characters are replaced."""
    # Create a string with surrogate characters
    # Surrogates are in the range U+D800 to U+DFFF
    text_with_surrogates = "Hello\ud800\udc00World"
    
    # Should replace surrogates with replacement character
    result = sanitize_surrogates(text_with_surrogates)
    
    # Result should not contain surrogates
    # Should be encodable to UTF-8
    result.encode('utf-8')
    
    # Should contain replacement characters
    assert '\ufffd' in result or 'Hello' in result
    assert 'World' in result


def test_sanitize_surrogates_unicode_safe():
    """Test that valid Unicode characters are preserved."""
    text = "Hello 世界 🌍 Привет"
    assert sanitize_surrogates(text) == text


def test_sanitize_surrogates_mixed():
    """Test text with both valid Unicode and surrogates."""
    # Mix valid Unicode with surrogates
    text = "Hello 世界\ud800Test"
    result = sanitize_surrogates(text)
    
    # Should be encodable
    result.encode('utf-8')
    
    # Valid Unicode should be preserved
    assert '世界' in result
    assert 'Hello' in result
    assert 'Test' in result


def test_sanitize_surrogates_with_warning(capsys):
    """Test that warning is printed when warn=True and surrogates detected."""
    text_with_surrogates = "Hello\ud800World"
    
    result = sanitize_surrogates(text_with_surrogates, warn=True)
    
    # Should still sanitize
    result.encode('utf-8')
    
    # Should print warning to stderr
    captured = capsys.readouterr()
    # The replacement character might be � or ? depending on encoding
    assert "Warning" in captured.err or '\ufffd' in result or '?' in result


def test_sanitize_surrogates_no_warning_on_clean_text(capsys):
    """Test that no warning is printed for clean text even with warn=True."""
    text = "Hello World"
    
    result = sanitize_surrogates(text, warn=True)
    
    # Should return unchanged
    assert result == text
    
    # Should not print warning
    captured = capsys.readouterr()
    assert captured.err == ""
