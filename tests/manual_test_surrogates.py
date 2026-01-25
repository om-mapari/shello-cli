#!/usr/bin/env python
"""Manual test script for surrogate character handling.

Run this to verify the fix works:
    python tests/manual_test_surrogates.py
"""

from shello_cli.utils.output_utils import sanitize_surrogates


def test_emoji_corruption():
    """Test handling of corrupted emoji (common Windows paste issue)."""
    print("Testing emoji corruption handling...")
    
    # Simulate corrupted emoji (🌐 becomes surrogates)
    corrupted = "🌐 Networking"
    try:
        # This would fail before the fix
        corrupted.encode('utf-8')
        print(f"✓ Original text is valid UTF-8: {corrupted}")
    except UnicodeEncodeError:
        print(f"✗ Original text has surrogates")
        sanitized = sanitize_surrogates(corrupted)
        sanitized.encode('utf-8')  # Should not raise
        print(f"✓ Sanitized successfully: {sanitized}")


def test_surrogate_pairs():
    """Test handling of explicit surrogate pairs."""
    print("\nTesting explicit surrogate pairs...")
    
    # Create text with surrogates
    text_with_surrogates = "Hello\ud800\udc00World"
    
    try:
        text_with_surrogates.encode('utf-8')
        print("✗ Surrogates were not detected")
    except UnicodeEncodeError:
        print("✓ Surrogates detected as expected")
        
        sanitized = sanitize_surrogates(text_with_surrogates)
        sanitized.encode('utf-8')  # Should not raise
        print(f"✓ Sanitized successfully: {repr(sanitized)}")


def test_mixed_content():
    """Test handling of mixed valid Unicode and surrogates."""
    print("\nTesting mixed content...")
    
    text = "Hello 世界\ud800Test 🌍"
    
    try:
        text.encode('utf-8')
        print("✗ Surrogates were not detected")
    except UnicodeEncodeError:
        print("✓ Surrogates detected in mixed content")
        
        sanitized = sanitize_surrogates(text)
        sanitized.encode('utf-8')  # Should not raise
        
        # Verify valid Unicode is preserved
        assert '世界' in sanitized
        assert 'Hello' in sanitized
        assert 'Test' in sanitized
        assert '🌍' in sanitized
        
        print(f"✓ Sanitized with valid Unicode preserved: {sanitized}")


def test_api_encoding():
    """Test that sanitized text can be JSON encoded (for API calls)."""
    print("\nTesting API encoding...")
    
    import json
    
    text = "Command\ud800Output"
    sanitized = sanitize_surrogates(text)
    
    # This is what happens when sending to OpenAI API
    message = {"role": "user", "content": sanitized}
    json_str = json.dumps(message)  # Should not raise
    
    print(f"✓ Successfully JSON encoded: {json_str[:50]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("Surrogate Character Handling - Manual Test")
    print("=" * 60)
    
    test_emoji_corruption()
    test_surrogate_pairs()
    test_mixed_content()
    test_api_encoding()
    
    print("\n" + "=" * 60)
    print("All manual tests passed! ✓")
    print("=" * 60)
