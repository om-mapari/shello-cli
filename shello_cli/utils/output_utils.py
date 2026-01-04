"""
Output utility functions for Shello CLI.

This module provides utility functions for processing command output,
including stripping PowerShell column padding.
"""


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
