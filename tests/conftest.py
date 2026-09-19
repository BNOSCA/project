from __future__ import annotations

import os
import sys
from pathlib import Path


# Unit/integration tests must be deterministic and must not call the live LLM.
# Defining these as empty before backend.config is imported also prevents
# load_dotenv(..., override=False) from restoring local .env API keys.
os.environ["GROQ_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""


REPO_ROOT = Path(__file__).resolve().parents[1]
repo_root_text = str(REPO_ROOT)

if sys.path[0] != repo_root_text:
    sys.path.insert(0, repo_root_text)