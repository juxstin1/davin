"""Fixtures: a reproducible TTS speech clip + a client on a dedicated test project.

Requires a running DaVinci Resolve Studio and ffmpeg on PATH. The speech
fixture is generated on first run (Windows TTS + ffmpeg) so it works on any
machine without checking media into git.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SPEECH = FIXTURES / "speech.mp4"

SPEECH_TEXT = (
    "Hello, my name is davin, and I am editing this video by myself. "
    "This boring sentence should be cut out of the final edit. "
    "DaVinci Resolve transcribed everything you are hearing right now. "
    "The papercut keeps only the good parts."
)

TTS_PS = (
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$s.Rate = -1; "
    "$s.SetOutputToWaveFile('{wav}'); "
    "$s.Speak('{text}'); "
    "$s.Dispose()"
)


@pytest.fixture(scope="session")
def speech_clip() -> Path:
    if not SPEECH.exists():
        FIXTURES.mkdir(exist_ok=True)
        wav = FIXTURES / "speech.wav"
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                TTS_PS.format(wav=wav, text=SPEECH_TEXT),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "testsrc2=duration=30:size=1280x720:rate=30",
                "-i", str(wav),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", str(SPEECH),
            ],
            check=True,
        )
        wav.unlink(missing_ok=True)
    return SPEECH


@pytest.fixture(scope="session")
def client():
    from davin.client import DavinClient

    c = DavinClient.connect()
    c.ensure_project("davin-test")
    return c


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())
