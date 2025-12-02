"""
S3 Connectors (Hetzner Object Storage)

Readers and writers for S3-compatible storage with optimizations.
"""

from .reader import S3Reader
from .writer import S3Writer

__all__ = ["S3Reader", "S3Writer"]
