"""Keep test imports anchored to this repository.

This lets developers run pytest either from project-repo/ or from the parent
hackathon workspace, which also contains a separate backend package.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
repo_root_text = str(REPO_ROOT)

if sys.path[0] != repo_root_text:
    sys.path.insert(0, repo_root_text)
