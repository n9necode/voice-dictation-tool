"""Settings read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from voice_dictation_tool.errors import ConfigError

EFFORTS = ("low", "high", "max")
DEFAULT_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MODEL = "kimi-k3"


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.strip():
            continue
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _load_dotenv() -> dict[str, str]:
    candidates = [Path.cwd() / ".env"]
    candidates.extend(p / ".env" for p in Path(__file__).resolve().parents)
    for candidate in candidates:
        if candidate.is_file():
            return _parse_dotenv(candidate)
    return {}


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    reasoning_effort: str = "low"
    timeout: float = 60.0
    lang: str = ""

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        if env is None:
            source = {**_load_dotenv(), **os.environ}
        else:
            source = env
        effort = source.get("KIMI_REASONING_EFFORT", "low").strip() or "low"
        if effort not in EFFORTS:
            allowed = ", ".join(EFFORTS)
            raise ConfigError(
                f"KIMI_REASONING_EFFORT must be one of {allowed}, got {effort!r}."
            )
        try:
            timeout = float(source.get("KIMI_TIMEOUT", "60"))
        except ValueError as exc:
            raise ConfigError("KIMI_TIMEOUT must be a number of seconds.") from exc
        if timeout <= 0:
            raise ConfigError("KIMI_TIMEOUT must be greater than zero.")
        return cls(
            api_key=source.get("MOONSHOT_API_KEY", "").strip(),
            base_url=(source.get("MOONSHOT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            model=(source.get("KIMI_MODEL") or DEFAULT_MODEL).strip(),
            reasoning_effort=effort,
            timeout=timeout,
            lang=(source.get("KIMI_LANG") or "").strip(),
        )

    def require_api_key(self) -> None:
        if not self.api_key:
            raise ConfigError(
                "Set MOONSHOT_API_KEY to your Moonshot API key before talking to Kimi K3."
            )
