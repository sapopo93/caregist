"""Local dual-channel faster-whisper transcription for the CRM worker."""

from __future__ import annotations

import asyncio
import json
import multiprocessing
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.config import settings


class TranscriptionError(RuntimeError):
    """Raised when audio cannot be safely transcribed and labelled."""


@dataclass(frozen=True)
class SpeakerSegment:
    start: float
    end: float
    speaker: str
    text: str


async def _run_media_command(*command: str, timeout_seconds: int = 60) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise TranscriptionError("Local audio processing timed out.") from exc
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()[:500]
        raise TranscriptionError(f"Local audio processing failed: {detail or 'unknown error'}")
    return stdout


async def _split_dual_channel(source: Path, agent_path: Path, contact_path: Path) -> None:
    probe = await _run_media_command(
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=channels",
        "-of",
        "json",
        str(source),
    )
    try:
        streams = json.loads(probe).get("streams", [])
        channels = int(streams[0]["channels"])
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TranscriptionError("Recording does not contain a readable audio stream.") from exc
    if channels != 2:
        raise TranscriptionError("Recording is not dual-channel; speaker identity cannot be inferred.")

    # Twilio <Dial> dual recordings place the parent browser call in channel 1
    # and the child PSTN call in channel 2. CareGist's parent is always the
    # authenticated agent and the child is always the selected contact.
    await _run_media_command(
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(source),
        "-filter_complex",
        "[0:a]channelsplit=channel_layout=stereo[agent][contact]",
        "-map",
        "[agent]",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(agent_path),
        "-map",
        "[contact]",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(contact_path),
    )


@lru_cache(maxsize=1)
def _whisper_model() -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise TranscriptionError(
            "faster-whisper is not installed; install requirements-worker.txt."
        ) from exc
    return WhisperModel(
        settings.crm_transcription_model,
        device=settings.crm_transcription_device,
        compute_type=settings.crm_transcription_compute_type,
        cpu_threads=settings.crm_transcription_cpu_threads,
        num_workers=1,
    )


def _transcribe_track(path: Path, speaker: str) -> list[SpeakerSegment]:
    segments, _info = _whisper_model().transcribe(
        str(path),
        language="en",
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
    )
    result: list[SpeakerSegment] = []
    for segment in segments:
        text = str(segment.text).strip()
        if text:
            result.append(
                SpeakerSegment(
                    start=max(0.0, float(segment.start)),
                    end=max(0.0, float(segment.end)),
                    speaker=speaker,
                    text=text,
                )
            )
    return result


def _transcribe_tracks_process(agent: str, contact: str, queue: Any) -> None:
    """Run inference in a disposable process so timeout termination is real."""
    try:
        queue.put(
            {
                "segments": [
                    *[segment.__dict__ for segment in _transcribe_track(Path(agent), "Agent")],
                    *[segment.__dict__ for segment in _transcribe_track(Path(contact), "Contact")],
                ]
            }
        )
    except BaseException as exc:  # child must return a serialisable failure
        queue.put({"error": f"{type(exc).__name__}: {exc}"[:500]})


async def _transcribe_tracks(agent: Path, contact: Path) -> list[SpeakerSegment]:
    context = multiprocessing.get_context("spawn")
    queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_transcribe_tracks_process,
        args=(str(agent), str(contact), queue),
        daemon=True,
    )
    process.start()
    try:
        # Drain while the child is alive. Joining first can deadlock when a
        # long transcript fills the multiprocessing queue's feeder pipe.
        payload = await asyncio.wait_for(
            asyncio.to_thread(queue.get),
            timeout=settings.crm_transcription_timeout_seconds,
        )
        await asyncio.to_thread(process.join, 10)
    except TimeoutError as exc:
        process.terminate()
        await asyncio.to_thread(process.join, 10)
        if process.is_alive():
            process.kill()
            await asyncio.to_thread(process.join)
        raise TranscriptionError("Local faster-whisper transcription timed out.") from exc
    finally:
        if process.is_alive():
            process.terminate()
            await asyncio.to_thread(process.join)
    if process.exitcode != 0:
        raise TranscriptionError("Local faster-whisper worker exited without a transcript.")
    queue.close()
    if payload.get("error"):
        raise TranscriptionError(f"Local faster-whisper transcription failed: {payload['error']}")
    return [SpeakerSegment(**item) for item in payload["segments"]]


async def transcribe_dual_channel(content: bytes) -> str:
    """Transcribe stereo audio locally and merge tracks by timestamp."""
    if not content:
        raise TranscriptionError("Recording is empty.")
    with tempfile.TemporaryDirectory(prefix="caregist-crm-audio-") as directory:
        root = Path(directory)
        source = root / "recording.mp3"
        agent = root / "agent.wav"
        contact = root / "contact.wav"
        source.write_bytes(content)
        await _split_dual_channel(source, agent, contact)
        segments = await _transcribe_tracks(agent, contact)

    segments = sorted(
        segments,
        key=lambda item: (item.start, 0 if item.speaker == "Agent" else 1, item.end),
    )
    if not segments:
        raise TranscriptionError("Local transcription returned an empty transcript.")
    return "\n".join(
        f"[{segment.start:07.2f}] {segment.speaker}: {segment.text}" for segment in segments
    )
