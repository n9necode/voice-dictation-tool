"""Microphone and speaker backends.

Windows uses the built-in speech runtime so the plugin has no audio
dependencies. Tests inject their own listener and speaker.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable

from kimi_voice.errors import ListenEnded, ListenError, SpeechError

SAPI_SPEAK = r"""
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$text = [Console]::In.ReadToEnd()
if (-not [string]::IsNullOrWhiteSpace($text)) { $synth.Speak($text) }
"""


def sapi_listen_script(timeout: float) -> str:
    seconds = float(timeout)
    if seconds <= 0 or seconds > 120:
        raise ListenError("Listen timeout must be between 0 and 120 seconds.")
    return f"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
$engine.SetInputToDefaultAudioDevice()
$engine.InitialSilenceTimeout = [TimeSpan]::FromSeconds({seconds:.1f})
$result = $engine.Recognize()
if ($null -ne $result) {{ Write-Output $result.Text }}
"""


def run_powershell(script: str, *, input_text: str | None, timeout: float) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            input=None if input_text is None else input_text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ListenError("The speech command timed out.") from exc
    except FileNotFoundError as exc:
        raise SpeechError("PowerShell is required for microphone and speaker on Windows.") from exc


class WindowsSapiSpeaker:
    def speak(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        completed = run_powershell(SAPI_SPEAK, input_text=cleaned, timeout=120)
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise SpeechError(detail or "Windows could not speak that text.")


class WindowsSapiListener:
    def listen(self, timeout: float = 12) -> str:
        completed = run_powershell(
            sapi_listen_script(timeout),
            input_text=None,
            timeout=timeout + 15,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise ListenError(detail or "Windows could not hear the microphone.")
        text = completed.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            raise ListenError(
                "No speech was recognized. Check the microphone, or run with --text."
            )
        return text


class LineListener:
    """Reads utterances from an iterator. Used by --text and by tests."""

    def __init__(self, lines: Iterable[str]):
        self._lines = iter(lines)

    def listen(self, timeout: float = 12) -> str:
        del timeout
        try:
            return next(self._lines)
        except StopIteration as exc:
            raise ListenEnded("No more typed input.") from exc


class PromptListener:
    def __init__(self, input_fn=input, output=None):
        self.input_fn = input_fn
        self.output = output or sys.stdout

    def listen(self, timeout: float = 12) -> str:
        del timeout
        self.output.write("Listening...\n")
        self.output.flush()
        try:
            return self.input_fn("You: ")
        except EOFError as exc:
            raise ListenEnded("Input closed.") from exc


class PrintingSpeaker:
    """Writes each spoken sentence. Interactive text mode uses this."""

    def __init__(self, output=None):
        self.output = output or sys.stdout
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.spoken.append(cleaned)
        self.output.write(f"Kimi: {cleaned}\n")
        self.output.flush()


class ListSpeaker:
    def __init__(self):
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self.spoken.append(cleaned)


class TeeSpeaker:
    def __init__(self, inner, output=None):
        self.inner = inner
        self.output = output or sys.stdout

    def speak(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.output.write(f"Kimi: {cleaned}\n")
        self.output.flush()
        self.inner.speak(cleaned)


def default_listener():
    if sys.platform == "win32":
        return WindowsSapiListener()
    raise ListenError(
        "This system has no built-in microphone backend. Run with --text, "
        "or pass lines into the converse tool."
    )


def default_speaker():
    if sys.platform == "win32":
        return WindowsSapiSpeaker()
    raise SpeechError(
        "This system has no built-in speaker backend. Run with --text."
    )
