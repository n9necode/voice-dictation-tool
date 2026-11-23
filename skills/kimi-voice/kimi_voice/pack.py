"""Zip the plugin so it can be installed or downloaded as a skill."""

from __future__ import annotations

import zipfile
from pathlib import Path

INCLUDE = (
    "kimi.plugin.json",
    "marketplace.json",
    "README.md",
    "pyproject.toml",
    ".env.example",
    "commands",
    "skills",
)

SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "dist", "tests"}
SKIP_SUFFIXES = {".pyc", ".wav"}


def plugin_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "kimi.plugin.json").is_file():
            return parent
    raise FileNotFoundError("kimi.plugin.json was not found above the package.")


def pack_plugin(root: Path | None = None, dest: Path | None = None) -> Path:
    source = root or plugin_root()
    output = dest or (source / "dist" / "kimi-voice.zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in INCLUDE:
            path = source / name
            if not path.exists():
                continue
            if path.is_file():
                archive.write(path, name)
                continue
            for file in path.rglob("*"):
                if not file.is_file():
                    continue
                if any(part in SKIP_DIRS for part in file.parts):
                    continue
                if file.suffix in SKIP_SUFFIXES:
                    continue
                archive.write(file, file.relative_to(source).as_posix())
    return output
