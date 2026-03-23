"""Repository scanning stubs for future enhancements."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models import RepoSummary


class RepoScanner:
    """Gather lightweight repo metadata for routing context."""

    def scan(self, repo_path: Optional[str]) -> RepoSummary | None:
        if not repo_path:
            return None
        path = Path(repo_path).expanduser()
        notes = []
        if not path.exists():
            notes.append("Path does not exist; repo insights unavailable yet")
            return RepoSummary(root_path=str(path), notes=notes)
        return RepoSummary(
            root_path=str(path),
            notes=["Repo scanning disabled in MVP; metadata collection stub."],
        )
