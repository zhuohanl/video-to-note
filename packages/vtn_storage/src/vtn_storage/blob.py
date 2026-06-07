from __future__ import annotations

from pathlib import Path
from typing import Protocol


class BlobStore(Protocol):
    def put(self, key: str, data: bytes) -> str: ...

    def get(self, key: str) -> bytes: ...

    def url_for(self, key: str) -> str: ...

    def delete_prefix(self, prefix: str) -> int: ...


class LocalBlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return self.url_for(key)

    def get(self, key: str) -> bytes:
        return self._path_for(key).read_bytes()

    def url_for(self, key: str) -> str:
        return f"local://{key}"

    def delete_prefix(self, prefix: str) -> int:
        base = self._path_for(prefix)
        if base.is_file():
            base.unlink()
            return 1
        if not base.exists():
            return 0

        files = [path for path in base.rglob("*") if path.is_file()]
        for path in files:
            path.unlink()
        for path in sorted(base.rglob("*"), reverse=True):
            if path.is_dir():
                path.rmdir()
        base.rmdir()
        return len(files)

    def _path_for(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        root = self.root.resolve()
        if root != candidate and root not in candidate.parents:
            msg = f"blob key escapes root: {key}"
            raise ValueError(msg)
        return candidate
