"""Output management module for handling large command outputs."""

from shello_cli.tools.output.types import (
    OutputType,
    TruncationStrategy,
    LineImportance,
    TruncationResult,
    CompressionStats,
    CacheEntry,
)
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.type_detector import TypeDetector
from shello_cli.tools.output.compressor import ProgressBarCompressor
from shello_cli.tools.output.truncator import Truncator
from shello_cli.tools.output.semantic import LineClassifier
from shello_cli.tools.output.manager import OutputManager

__all__ = [
    "OutputType",
    "TruncationStrategy",
    "LineImportance",
    "TruncationResult",
    "CompressionStats",
    "CacheEntry",
    "OutputCache",
    "TypeDetector",
    "ProgressBarCompressor",
    "Truncator",
    "LineClassifier",
    "OutputManager",
]
