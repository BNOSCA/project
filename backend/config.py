"""Environment-only runtime settings; no keys or user data in Git."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    mode: str
    cors_origins: tuple[str, ...]
    db_path: Path
    data_dir: Path
    llm_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("BACKEND_MODE", "mock").lower()
        if mode not in {"mock", "live"}:
            raise ValueError("BACKEND_MODE must be mock or live")
        origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip())
        db_path = Path(os.getenv("APP_DB_PATH", str(ROOT / "runtime" / "demo.sqlite3"))).expanduser()
        data_dir = Path(os.getenv("APP_DATA_DIR", str(ROOT / "data" / "catalog" / "combined"))).expanduser()
        return cls(mode, origins, db_path, data_dir, float(os.getenv("LLM_TIMEOUT_SECONDS", "8")))
