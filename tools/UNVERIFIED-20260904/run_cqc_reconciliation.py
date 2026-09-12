#!/usr/bin/env python3
"""Run a complete CQC reconciliation cycle: prepare -> shards -> finalize.

Why this exists
---------------
`incremental_update.py` implements reconciliation as four separate operator
commands (`prepare`, `shard`, `finalize`, `abort`). Only the `finalize` phase
writes `counts_reconciled = TRUE` and `reconciled_at`, and only a run with
those columns set can act as the CQC source-freshness watermark that
`api/services/cqc_freshness.py` reads. `commercialReadiness.checkoutReady`
in `/api/v1/health` is false until that watermark exists and is inside its
192-hour SLA, and the pricing page renders "Paid checkout unavailable"
whenever it is false.

In production, batches `c6e7d7fa` (2026-08-11, run 5244) and `56a11f0f`
(2026-08-12, run 5312) each finished with every shard `completed`,
57,025/57,025 and 57,060/57,060 locations checked and zero failures — and
were then closed by `abort` because nobody ran `finalize`. Both are recorded
as `failed` and neither produced a watermark. Paid checkout has therefore been
switched off by successful data collection that was never booked as finished.

This orchestrator removes the manual step that keeps being missed: it drives
every phase in one command, retries a transient shard, and only aborts a batch
it can prove is incomplete. Run it on a schedule.

Usage:
    python3 tools/run_cqc_reconciliation.py --shard-count 8
    python3 tools/run_cqc_reconciliation.py --shard-count 8 --dry-run
    python3 tools/run_cqc_reconciliation.py --finalize-batch <uuid> --shard-count 8
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "incremental_update.py"


def run_phase(phase: str, *extra: str, echo: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(CLI), "--phase", phase, *extra]
    if echo:
        print(f"\n$ {' '.join(cmd[1:])}", flush=True)
    return subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)


def report(result: subprocess.CompletedProcess) -> None:
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-count", type=int, default=8,
                        help="Number of shards to split the snapshot across.")
    parser.add_argument("--concurrency", type=int, default=4,
                        help="Shards to run at once. Each holds its own advisory lock.")
    parser.add_argument("--shard-retries", type=int, default=2,
                        help="Retries per shard before the batch is treated as incomplete.")
    parser.add_argument("--manifest-dir", default=None,
                        help="Where to write the snapshot manifest (default: a temp dir).")
    parser.add_argument("--resume-batch",
                        help="Continue an already-prepared batch: run its outstanding "
                             "shards, then finalize. Needs the original manifest.")
    parser.add_argument("--finalize-batch",
                        help="Skip prepare/shard and finalize an existing batch id.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Prepare and shard without finalizing; leaves the batch open.")
    parser.add_argument("--abort-on-failure", action="store_true",
                        help="Abort the batch if a shard cannot be completed. Off by default so "
                             "an incomplete batch stays resumable instead of being written off.")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL") and not (REPO_ROOT / ".env").exists():
        print("ERROR: DATABASE_URL is not set and there is no .env to read it from.",
              file=sys.stderr)
        return 2

    if args.finalize_batch:
        batch_id = args.finalize_batch
        print(f"Finalizing existing batch {batch_id}")
    else:
        if args.resume_batch:
            # Reuse an open batch and its manifest. Shards are checkpointed, so
            # completed ones are skipped and a part-done one continues from its
            # own offset -- no work is repeated and no duplicate batch is opened.
            batch_id = args.resume_batch
            manifest_dir = Path(args.manifest_dir) if args.manifest_dir else REPO_ROOT / "outreach" / "recon"
            manifest_path = manifest_dir / f"{batch_id}.json"
            if not manifest_path.exists():
                print(f"ERROR: manifest {manifest_path} not found; a resume needs the "
                      f"original manifest.", file=sys.stderr)
                return 2
            print(f"Resuming batch {batch_id} from {manifest_path}")
        else:
            batch_id = str(uuid.uuid4())
            manifest_dir = Path(args.manifest_dir) if args.manifest_dir else Path(
                tempfile.mkdtemp(prefix="cqc-reconciliation-"))
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifest_dir / f"{batch_id}.json"

        prepare = None if args.resume_batch else run_phase("prepare", "--batch-id", batch_id,
                            "--shard-count", str(args.shard_count),
                            "--snapshot-manifest", str(manifest_path))
        if prepare is not None:
            report(prepare)
        if prepare is not None and prepare.returncode != 0:
            print(f"\nPrepare failed; no batch was opened. Nothing to clean up.", file=sys.stderr)
            return prepare.returncode

        # Each shard takes its own per-shard advisory lock
        # (cqc-reconciliation:<batch>:<index>), so shards are safe to run
        # concurrently -- and must be, or a full pass takes ~16 hours instead
        # of ~3 and can never fit a daily schedule.
        import concurrent.futures

        def run_one(shard_index: int) -> tuple[int, bool]:
            for attempt in range(1, args.shard_retries + 2):
                shard = run_phase("shard", "--batch-id", batch_id,
                                  "--shard-count", str(args.shard_count),
                                  "--shard-index", str(shard_index),
                                  "--snapshot-manifest", str(manifest_path),
                                  echo=False)
                if shard.returncode == 0:
                    print(f"shard {shard_index}: complete", flush=True)
                    return shard_index, True
                print(f"shard {shard_index}: attempt {attempt} failed "
                      f"(exit {shard.returncode}) {(shard.stderr or '').strip()[-200:]}",
                      flush=True)
            return shard_index, False

        incomplete: list[int] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for shard_index, ok in pool.map(run_one, range(args.shard_count)):
                if not ok:
                    incomplete.append(shard_index)
        incomplete.sort()

        if incomplete:
            print(f"\nShards still incomplete after retries: {incomplete}", file=sys.stderr)
            if args.abort_on_failure:
                report(run_phase("abort", "--batch-id", batch_id,
                                 "--shard-count", str(args.shard_count)))
                print("Batch aborted. No watermark was written.", file=sys.stderr)
            else:
                print(f"Batch {batch_id} left open and resumable. Re-run the missing shards, "
                      f"then:\n  python3 tools/run_cqc_reconciliation.py "
                      f"--finalize-batch {batch_id} --shard-count {args.shard_count}",
                      file=sys.stderr)
            return 1

        if args.dry_run:
            print(f"\n--dry-run: every shard completed but finalize was skipped. "
                  f"Batch {batch_id} is open and will NOT unlock checkout until finalized.")
            return 0

    finalize = run_phase("finalize", "--batch-id", batch_id,
                         "--shard-count", str(args.shard_count))
    report(finalize)
    if finalize.returncode != 0:
        print("\nFinalize failed. The batch is still open — do NOT abort it; every shard's "
              "work is intact and finalize can be retried.", file=sys.stderr)
        return finalize.returncode

    print(f"\nReconciliation complete. Batch {batch_id} is finalized, so pipeline_runs now "
          f"carries counts_reconciled=TRUE and reconciled_at.")
    print("Verify the commercial gate opened:")
    print("  curl -s https://www.caregist.co.uk/api/v1/health "
          "| python3 -c \"import sys,json;d=json.load(sys.stdin);"
          "print(d['commercialReadiness'], d['source']['freshnessStatus'])\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
