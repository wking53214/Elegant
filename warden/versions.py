"""Which versions took part in a run, for the `versions` field of `warden tagteam`'s JSON.

Every answer is read from files and never by running anything: a commit comes from `.git`, a
version string from `pyproject.toml` or from the installed package's metadata. A value that
cannot be found is `None`, never a guess. This only reports; nothing here decides anything.
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
import re
import tomllib
from pathlib import Path
from typing import Optional

_SHA = re.compile(r"^[0-9a-f]{40}$")


def git_commit(path: Path) -> Optional[str]:
    """The commit a checkout is on (read from .git, walking up from `path`), or None."""
    try:
        here = Path(path).resolve()
        for folder in (here, *here.parents):
            dot = folder / ".git"
            if dot.is_file():  # a worktree or submodule: ".git" is a file naming the real folder
                text = dot.read_text(encoding="utf-8").strip()
                if not text.startswith("gitdir:"):
                    return None
                gitdir = (folder / text[len("gitdir:"):].strip()).resolve()
            elif dot.is_dir():
                gitdir = dot
            else:
                continue
            head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
            if _SHA.match(head):
                return head
            if not head.startswith("ref:"):
                return None
            ref = head[4:].strip()
            common = gitdir
            if (gitdir / "commondir").is_file():
                common = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
            for base in (gitdir, common):
                loose = base / ref
                if loose.is_file():
                    sha = loose.read_text(encoding="utf-8").strip()
                    return sha if _SHA.match(sha) else None
            packed = common / "packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    parts = line.split()
                    if len(parts) == 2 and parts[1] == ref and _SHA.match(parts[0]):
                        return parts[0]
            return None
    except (OSError, ValueError):
        return None
    return None


def project_version(root: Path) -> Optional[str]:
    """The `version` in a checkout's pyproject.toml, or None."""
    try:
        data = tomllib.loads((Path(root) / "pyproject.toml").read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version")
        return version if isinstance(version, str) else None
    except (OSError, ValueError):
        return None


def instrument(root: Optional[Path]) -> Optional[dict]:
    """An instrument checkout (Ghost Tools, SWIZZLE, ASSAY): where it is, its commit and version."""
    if root is None:
        return None
    root = Path(root).expanduser().resolve()
    return {"path": str(root), "commit": git_commit(root), "version": project_version(root)}


def _installed(module_name: str, module_file: Optional[str]) -> dict:
    """Commit and version of the code a seat's module really came from."""
    out: dict = {"version": None, "commit": None}
    top = module_name.partition(".")[0]
    try:
        dists = metadata.packages_distributions().get(top) or []
        if dists:
            dist = metadata.distribution(dists[0])
            out["version"] = dist.version
            direct = dist.read_text("direct_url.json")
            if direct:
                info = json.loads(direct).get("vcs_info") or {}
                if _SHA.match(str(info.get("commit_id", ""))):
                    out["commit"] = info["commit_id"]
    except Exception:  # noqa: BLE001 - a report that cannot be read is None, never a crash
        pass
    if out["commit"] is None and module_file:
        out["commit"] = git_commit(Path(module_file).parent)
    return out


def seat(spec: Optional[str], filled) -> Optional[dict]:
    """A seat named MODULE:FACTORY and the object built from it."""
    if not spec or filled is None:
        return None
    module_name = spec.partition(":")[0]
    try:
        module_file = getattr(importlib.import_module(module_name), "__file__", None)
    except Exception:  # noqa: BLE001
        module_file = None
    declared = getattr(filled, "requires_contract", None)
    return {"spec": spec, "requires_contract": declared if isinstance(declared, str) else None,
            **_installed(module_name, module_file)}


def report(*, warden_module, contract: str, version: str, ghost_root, swizzle_root, assay_root,
           seats: dict) -> dict:
    """The `versions` object: Warden, each instrument root given, and each seat that was loaded."""
    me = _installed("warden", getattr(warden_module, "__file__", None))
    return {
        "warden": {"version": version, "contract": contract, "commit": me["commit"]},
        "ghost_tools": instrument(ghost_root),
        "swizzle": instrument(swizzle_root),
        "assay": instrument(assay_root),
        "seats": seats,
    }
