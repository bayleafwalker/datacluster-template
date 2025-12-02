"""
Data Connectors

Standard interfaces for reading/writing data from various sources.
"""

from . import kafka
from . import s3
from . import jdbc
from . import files

__all__ = ["kafka", "s3", "jdbc", "files"]
