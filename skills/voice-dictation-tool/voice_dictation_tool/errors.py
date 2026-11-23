"""Failures the voice plugin reports to the caller."""


class KimiVoiceError(Exception):
    """Base error for config, speech, and API failures."""


class ConfigError(KimiVoiceError):
    """The plugin is missing a setting it needs to run."""


class KimiAPIError(KimiVoiceError):
    """The Moonshot API rejected the request or could not be reached."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        detail = body.strip().replace("\n", " ")
        if len(detail) > 500:
            detail = detail[:500] + "..."
        super().__init__(f"Kimi API returned {status}: {detail}")


class ListenError(KimiVoiceError):
    """The microphone produced no usable transcript."""


class SpeechError(KimiVoiceError):
    """The speaker could not play the reply."""


class ListenEnded(KimiVoiceError):
    """The listener closed, for example the user pressed Ctrl-D."""
