"""
Delta Lake Manager

ACID transactions, time travel, and UPSERT operations for Delta tables.
"""

from .manager import DeltaManager

__all__ = ["DeltaManager"]
