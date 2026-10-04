"""The honesty oracle does not consult the critic."""

import ast
from pathlib import Path


def _imported(module_file: str) -> set[str]:
    src = Path(module_file).read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_oracle_module_does_not_import_critic():
    import elegant.swizzle as swizzle
    names = _imported(swizzle.__file__)
    assert "critic" not in names
    assert "elegant.critic" not in names


def test_critic_module_does_not_import_oracle():
    import elegant.critic as critic
    names = _imported(critic.__file__)
    assert "swizzle" not in names
