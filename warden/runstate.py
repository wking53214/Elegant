"""Things a run must keep outside the target: a lock and a journal.

THE LOCK   Two runs on one target would interleave their edits and test runs.
           A lock file in the temp directory, named by a hash of the target's
           path, is held for the whole run.
THE JOURNAL  The keep test makes code raise on purpose and puts it back
           afterward. If the process is killed in between, the trap stays in
           the user's source. Before any trap is written, the original bytes of
           every file are saved here, outside the target. The next run restores
           them first.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional


INTERRUPTED_NOTE = "A previous run was interrupted during the keep test; its trap code was removed."
BUSY_NOTE = "another Warden run is using this target"


def _key(target: Path) -> str:
    return hashlib.sha256(str(Path(target).resolve()).encode("utf-8")).hexdigest()[:20]


def lock_path(target: Path) -> Path:
    return Path(tempfile.gettempdir()) / f"warden-lock-{_key(target)}"


def journal_path(target: Path) -> Path:
    return Path(tempfile.gettempdir()) / f"warden-journal-{_key(target)}.json"


class TargetLock:
    """An exclusive, non-blocking lock on one target for the length of a run."""

    def __init__(self, target: Path) -> None:
        self.path = lock_path(target)
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None


def write_journal(target: Path, originals: Dict[str, bytes]) -> None:
    """Record every file and its original bytes. Written before any trap is."""
    payload = {"target": str(Path(target).resolve()),
               "files": {rel: base64.b64encode(data).decode("ascii") for rel, data in originals.items()}}
    path = journal_path(target)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def clear_journal(target: Path) -> None:
    journal_path(target).unlink(missing_ok=True)


def recover(target: Path) -> Optional[str]:
    """If an earlier run left a journal for this target, put its files back. Returns a note, or None."""
    path = journal_path(target)
    if not path.exists():
        return None
    root = Path(target).resolve()
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("target") != str(root):
            return None
        files = {rel: base64.b64decode(blob) for rel, blob in payload["files"].items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    for rel, data in files.items():
        dest = (root / rel)
        if Path(rel).is_absolute() or not dest.resolve().is_relative_to(root):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    clear_journal(target)
    return INTERRUPTED_NOTE
