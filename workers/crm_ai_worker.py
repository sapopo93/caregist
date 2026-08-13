#!/usr/bin/env python3
"""Long-lived local worker for private transcription and advisory AI jobs."""

from __future__ import annotations

import argparse
import asyncio
import signal

from api.services.crm_ai import record_worker_heartbeat, process_ai_jobs


async def run(*, once: bool, poll_seconds: float) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for event in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(event, stop.set)

    await record_worker_heartbeat("starting")
    while not stop.is_set():
        job = asyncio.create_task(process_ai_jobs(limit=1))
        while not job.done():
            await record_worker_heartbeat("processing")
            try:
                await asyncio.wait_for(asyncio.shield(job), timeout=30)
            except TimeoutError:
                continue
        result = await job
        await record_worker_heartbeat(
            "error" if result["failed"] else "idle",
            metadata=result,
        )
        if once:
            return
        try:
            await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
        except TimeoutError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one queued job.")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.poll_seconds < 1 or args.poll_seconds > 300:
        parser.error("--poll-seconds must be between 1 and 300")
    asyncio.run(run(once=args.once, poll_seconds=args.poll_seconds))


if __name__ == "__main__":
    main()
