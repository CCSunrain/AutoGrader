"""Local file storage for uploaded reports (workspace-isolated).

Storage key format: `{workspace_id}/{file_id}{ext}`. The physical file lives
under `settings.upload_dir`. This is a dev-friendly local store; a future
adapter can swap in object storage (S3/COS) without changing callers.
"""
from pathlib import Path

from app.core.config import settings


def _root() -> Path:
    return Path(settings.upload_dir)


def save_upload(*, workspace_id: str, file_id: str, ext: str, content: bytes) -> str:
    """Write file bytes and return its storage key."""
    key = f"{workspace_id}/{file_id}{ext}"
    path = _root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return key


def read_upload(file_key: str) -> bytes:
    """Read file bytes by storage key; raises FileNotFoundError if missing."""
    path = _root() / file_key
    if not path.exists():
        raise FileNotFoundError(f"file not found: {file_key}")
    return path.read_bytes()


def exists(file_key: str) -> bool:
    return (_root() / file_key).exists()


def resolve_path(file_key: str) -> Path:
    return _root() / file_key
