"""Looking at documentation rather than building it: ``py-doc stats``, ``py-doc check`` and ``py-doc diff``."""

from .diff import SectionChange, diff_markdown, sections
from .stats import FileStats, file_stats

__all__ = ["FileStats", "SectionChange", "diff_markdown", "file_stats", "sections"]
