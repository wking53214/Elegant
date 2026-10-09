"""Reading and writing files without changing what the author wrote.

Python's text mode quietly turns CRLF into LF when it reads, and writes LF
back. A file that came in with Windows line endings would leave with
different ones. These helpers keep the line-ending style of a file that
already exists, and refuse a file that is not valid UTF-8 instead of
crashing on it or guessing.
"""

from __future__ import annotations

from pathlib import Path


class Undecodable(ValueError):
    """A file is not valid UTF-8, so Warden will not edit it."""


def _is_crlf(raw: bytes) -> bool:
    """True when every line ending in the file is CRLF (and there is at least one)."""
    return b"\r\n" in raw and raw.count(b"\r\n") == raw.count(b"\n") and b"\r" not in raw.replace(b"\r\n", b"")


def decode(raw: bytes, label: str = "file") -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Undecodable(f"{label} is not valid UTF-8, so it will not be edited") from exc


def read_text(path: Path, label: str = "") -> str:
    """The file's text, with a pure CRLF file shown with LF so edits can match it."""
    raw = Path(path).read_bytes()
    text = decode(raw, label or str(path))
    return text.replace("\r\n", "\n") if _is_crlf(raw) else text


def is_decodable(path: Path) -> bool:
    try:
        decode(Path(path).read_bytes())
    except (Undecodable, OSError):
        return False
    return True


def encode_like(path: Path, text: str) -> bytes:
    """`text` as bytes, in CRLF if the file already there uses CRLF throughout."""
    path = Path(path)
    if path.is_file() and _is_crlf(path.read_bytes()):
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    return text.encode("utf-8")


def write_text(path: Path, text: str) -> None:
    """Write `text`, keeping the line endings of the file it replaces."""
    path = Path(path)
    data = encode_like(path, text)
    path.write_bytes(data)
