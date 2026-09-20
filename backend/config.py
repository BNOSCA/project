"""Environment-only runtime settings; no keys or user data in Git."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - only used in a minimal local venv
    def load_dotenv(path: Path, override: bool = False) -> None:
        if not path.exists():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()) and (override or key.strip() not in os.environ):
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    mode: str
    cors_origins: tuple[str, ...]
    db_path: Path
    data_dir: Path
    llm_timeout_seconds: float
    admin_uids: tuple[str, ...] = ()
    storage_backend: str = "sqlite"

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("BACKEND_MODE", "mock").lower()
        if mode not in {"mock", "live"}:
            raise ValueError("BACKEND_MODE must be mock or live")
        origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip())
        db_path = Path(os.getenv("APP_DB_PATH", str(ROOT / "runtime" / "demo.sqlite3"))).expanduser()
        data_dir = Path(os.getenv("APP_DATA_DIR", str(ROOT / "data" / "catalog" / "combined"))).expanduser()
        admin_uids = tuple(uid.strip() for uid in os.getenv("ADMIN_UIDS", "").split(",") if uid.strip())
        storage = os.getenv("STORAGE_BACKEND", "sqlite").lower()
        if storage not in {"sqlite", "firestore"}:
            raise ValueError("STORAGE_BACKEND must be sqlite or firestore")
        return cls(mode, origins, db_path, data_dir, float(os.getenv("LLM_TIMEOUT_SECONDS", "8")), admin_uids, storage)
