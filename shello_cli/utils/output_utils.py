"""
Output utility functions for Shello CLI.

This module provides utility functions for processing command output,
including stripping PowerShell column padding.
"""


def sanitize_surrogates(text: str, warn: bool = False) -> str:
    """Remove or replace surrogate characters that can't be encoded in UTF-8.
    
    Windows console output can contain surrogate characters (U+D800 to U+DFFF)
    that are invalid in UTF-8. These cause encoding errors when sending to APIs
    or writing to files. This function replaces them with the Unicode replacement
    character (U+FFFD).
    
    Args:
        text: Text that may contain surrogate characters
        warn: If True, print a warning when surrogates are detected
        
    Returns:
        Text with surrogates replaced by the replacement character
    """
    if not text:
        return text
    
    # Use 'surrogatepass' error handler to detect surrogates, then replace them
    # This is more efficient than checking each character
    try:
        # Try to encode normally - if it works, no surrogates present
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # Surrogates present - replace them
        # Use 'replace' error handler to substitute with U+FFFD
        sanitized = text.encode('utf-8', errors='replace').decode('utf-8')
        
        if warn:
            # Count how many characters were replaced
            original_len = len(text)
            sanitized_len = len(sanitized)
            if original_len != sanitized_len or '�' in sanitized:
                import sys
                print(
                    "\n⚠️  Warning: Invalid characters detected and replaced with �",
                    file=sys.stderr
                )
                print(
                    "   This usually happens when emoji are corrupted by your terminal.",
                    file=sys.stderr
                )
                print(
                    "   Consider using Windows Terminal for better Unicode support.\n",
                    file=sys.stderr
                )
        
        return sanitized


def strip_line_padding(output: str) -> str:
    """Strip trailing whitespace from each line.
    
    Removes PowerShell column padding while preserving structure.
    PowerShell's Format-Table pads columns to fixed widths, which
    inflates character counts by 2-3x. This function removes that
    padding without affecting the visual structure.
    
    Args:
        output: Raw command output
        
    Returns:
        Output with trailing whitespace removed from each line
    """
    if not output:
        return output
    lines = output.split('\n')
    return '\n'.join(line.rstrip() for line in lines)
