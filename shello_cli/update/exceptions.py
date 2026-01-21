"""Custom exceptions for the update module."""


class UpdateError(Exception):
    """Base exception for update-related errors.
    
    Raised when an error occurs during the update process that prevents
    the update from completing successfully.
    """
    pass


class DownloadError(UpdateError):
    """Exception raised when downloading a binary fails.
    
    This can occur due to network issues, invalid URLs, or server errors.
    """
    pass


class UnsupportedPlatformError(UpdateError):
    """Exception raised when the current platform is not supported.
    
    Raised when attempting to update on an operating system that doesn't
    have pre-built binaries available in GitHub releases.
    """
    pass
