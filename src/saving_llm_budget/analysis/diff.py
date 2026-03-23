"""Git diff analysis placeholder."""

from __future__ import annotations

from typing import Optional

from ..models import DiffSummary


class GitDiffAnalyzer:
    """Summaries git diffs without actually shelling out in the MVP."""

    def analyze(self, repo_path: Optional[str]) -> DiffSummary | None:
        if not repo_path:
            return None
        return DiffSummary(notes=["Diff analysis reserved for future releases."])
