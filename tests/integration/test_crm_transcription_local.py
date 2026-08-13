"""Executable local-media checks for the private CRM transcription worker."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from api.services.crm_transcription import TranscriptionError, transcribe_dual_channel


def _run(*command: str) -> None:
    subprocess.run(command, check=True, capture_output=True)


@pytest.mark.asyncio
async def test_empty_and_malformed_audio_fail_closed():
    with pytest.raises(TranscriptionError, match="empty"):
        await transcribe_dual_channel(b"")
    with pytest.raises(TranscriptionError, match="audio processing failed"):
        await transcribe_dual_channel(b"not an audio file")


@pytest.mark.asyncio
async def test_mono_audio_is_rejected_before_inference(tmp_path):
    mono = tmp_path / "mono.mp3"
    _run(
        "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=0.2", "-ac", "1", str(mono),
    )
    with pytest.raises(TranscriptionError, match="not dual-channel"):
        await transcribe_dual_channel(mono.read_bytes())


@pytest.mark.skipif(
    os.environ.get("CAREGIST_RUN_WHISPER_INTEGRATION") != "1" or shutil.which("say") is None,
    reason="Set CAREGIST_RUN_WHISPER_INTEGRATION=1 on macOS to run the model-backed test.",
)
@pytest.mark.asyncio
async def test_real_small_en_transcription_preserves_channel_labels(tmp_path):
    agent = tmp_path / "agent.aiff"
    contact = tmp_path / "contact.aiff"
    stereo = tmp_path / "stereo.mp3"
    _run("say", "-o", str(agent), "Hello, this is the agent speaking.")
    _run("say", "-o", str(contact), "Please call me again tomorrow morning.")
    _run(
        "ffmpeg", "-nostdin", "-v", "error", "-i", str(agent), "-i", str(contact),
        "-filter_complex", "[0:a][1:a]amerge=inputs=2[a]", "-map", "[a]", "-ac", "2",
        "-c:a", "libmp3lame", str(stereo),
    )

    transcript = await transcribe_dual_channel(stereo.read_bytes())

    assert "Agent:" in transcript
    assert "Contact:" in transcript
    assert "agent" in transcript.lower()
    assert "tomorrow" in transcript.lower()
