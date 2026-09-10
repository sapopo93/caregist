#!/usr/bin/env python3
"""Ingest READY AI OS GitHub repair issues into Hermes Kanban.

Designed for Hermes script-only cron (``--no-agent``): polling and routing cost
zero model tokens.  The script is deliberately deterministic and fail-closed.
It never implements repairs, changes production, or chooses business values.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

DEFAULT_REPOS = ("sapopo93/caregist", "sapopo93/regintel-v2")
DISPATCH_MARKER = "AI_OS_DISPATCH"
KANBAN_MARKER = "AI_OS_KANBAN_TASK"
ORIGIN_PR_RE = re.compile(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)")


@dataclass(frozen=True)
class RepairIssue:
    repo: str
    number: int
    title: str
    body: str
    url: str
    origin_pr: int | None


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, text=True, capture_output=True)


def require_cli(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"required CLI not found: {name}")


def gh_json(args: list[str]) -> Any:
    proc = run(["gh", *args])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh returned non-JSON output for {' '.join(args)}: {exc}") from exc


def is_ready(body: str) -> bool:
    return all(
        token in body
        for token in (
            DISPATCH_MARKER,
            "worker_profile: coder",
            "status: READY",
            "human_input_required: false",
        )
    ) and KANBAN_MARKER not in body


def issue_origin_pr(repo: str, body: str) -> int | None:
    match = ORIGIN_PR_RE.search(body)
    if not match:
        return None
    if match.group(1).lower() != repo.lower():
        return None
    return int(match.group(2))


def load_ready_issues(repo: str) -> list[RepairIssue]:
    rows = gh_json(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--label",
            "ai-os-repair",
            "--limit",
            "100",
            "--json",
            "number,title,body,url,comments",
        ]
    )
    issues: list[RepairIssue] = []
    for row in rows:
        body = row.get("body") or ""
        if not is_ready(body) or any(
            KANBAN_MARKER in (comment.get("body") or "")
            for comment in row.get("comments", [])
        ):
            continue
        issues.append(
            RepairIssue(
                repo=repo,
                number=int(row["number"]),
                title=str(row["title"]),
                body=body,
                url=str(row["url"]),
                origin_pr=issue_origin_pr(repo, body),
            )
        )
    return issues


def pr_context(repo: str, pr_number: int) -> dict[str, Any]:
    return gh_json(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "number,url,headRefName,headRefOid,baseRefName,state",
        ]
    )


def kanban_id(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("id", "task_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.startswith("t_"):
                return value
        for value in payload.values():
            try:
                return kanban_id(value)
            except ValueError:
                pass
    if isinstance(payload, list):
        for value in payload:
            try:
                return kanban_id(value)
            except ValueError:
                pass
    raise ValueError("Hermes Kanban JSON did not contain a task id")


def build_task_body(repo: str, issues: list[RepairIssue], pr: dict[str, Any] | None) -> str:
    issue_lines = "\n".join(f"- #{i.number}: {i.title} — {i.url}" for i in issues)
    if pr:
        target = (
            f"Parent PR: {pr['url']}\n"
            f"Target feature branch: {pr['headRefName']}\n"
            f"Observed head SHA at dispatch: {pr['headRefOid']}\n"
            f"Base branch: {pr['baseRefName']}"
        )
    else:
        target = "No parent PR was proven. Create a repair branch; never push directly to main."

    return f"""AI OS CODE REPAIR BATCH

Repository: {repo}
{target}

GitHub repair issues:
{issue_lines}

EXECUTION CONTRACT
1. Read every linked issue and its evidence before editing.
2. Work only on the repair scope. Do not change business pricing decisions, live Stripe, production secrets, customer data, permissions, or destructive infrastructure.
3. Preserve or strengthen all fail-closed CI/security gates. Never silence, waive, lower severity, or skip a gate merely to make CI green.
4. In the scratch workspace, authenticate with existing host CLI credentials and clone/fetch {repo}. If a parent feature branch is listed, check out that branch and update it; never push to main.
5. Implement the smallest correct repairs. Run focused tests first, then the repository-required validation relevant to changed files.
6. Commit and push repair changes only to the non-production feature branch associated with the parent PR when one is proven.
7. Post implementation evidence to each linked GitHub issue: changed files, commit SHA, tests, remaining risks, and whether CI is pending/green/red.
8. A code commit is not overall completion. GitHub CI and the independent Grok reviewer must evaluate the new exact head SHA.
9. If any required action crosses a founder approval boundary, stop that part and use kanban_block with the exact decision required. Do not ask the founder to restate the task.
10. The Kanban card represents engineering implementation only. Complete it only after the repair changes and evidence are pushed; the parent AI OS task remains fail-closed until external CI + Grok review pass.
"""


def create_kanban_task(repo: str, issues: list[RepairIssue], pr: dict[str, Any] | None) -> str:
    issue_key = "-".join(str(i.number) for i in sorted(issues, key=lambda x: x.number))
    if pr:
        scope_key = f"pr-{pr['number']}"
        title = f"Repair {repo} PR #{pr['number']} blockers ({', '.join('#'+str(i.number) for i in issues)})"
    else:
        scope_key = f"issues-{issue_key}"
        title = f"Repair {repo} issues {', '.join('#'+str(i.number) for i in issues)}"
    idempotency_key = f"ai-os:github:{repo}:{scope_key}:{issue_key}"
    body = build_task_body(repo, issues, pr)
    command = [
        "hermes",
        "kanban",
        "create",
        title,
        "--body",
        body,
        "--assignee",
        "coder",
        "--workspace",
        "scratch",
        "--idempotency-key",
        idempotency_key,
        "--max-runtime",
        "2h",
        "--max-retries",
        "2",
        "--json",
    ]
    proc = run(command)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Hermes Kanban returned non-JSON output: {exc}") from exc
    return kanban_id(payload)


def stamp_issue(issue: RepairIssue, task_id: str) -> None:
    stamp = f"""<!-- ai-os-kanban-task -->
{KANBAN_MARKER}
task_id: {task_id}
orchestrator: hermes:ai-company-governed
worker_profile: coder
status: QUEUED
human_authored: false
END_AI_OS_KANBAN_TASK"""
    run(
        [
            "gh",
            "issue",
            "comment",
            str(issue.number),
            "--repo",
            issue.repo,
            "--body",
            stamp,
        ]
    )


def ingest(repos: tuple[str, ...], *, dry_run: bool) -> int:
    require_cli("gh")
    require_cli("hermes")
    grouped: dict[tuple[str, int | None], list[RepairIssue]] = defaultdict(list)
    for repo in repos:
        for issue in load_ready_issues(repo):
            grouped[(repo, issue.origin_pr)].append(issue)

    if not grouped:
        return 0

    created: list[str] = []
    for (repo, origin_pr), issues in sorted(grouped.items()):
        issues.sort(key=lambda issue: issue.number)
        pr = pr_context(repo, origin_pr) if origin_pr is not None else None
        if pr and pr.get("state") != "OPEN":
            raise RuntimeError(f"refusing to dispatch repairs for non-open PR {repo}#{origin_pr}")
        if dry_run:
            created.append(
                f"DRY_RUN {repo} pr={origin_pr} issues={','.join(str(i.number) for i in issues)}"
            )
            continue
        task_id = create_kanban_task(repo, issues, pr)
        for issue in issues:
            stamp_issue(issue, task_id)
        created.append(
            f"QUEUED {task_id} -> coder for {repo} "
            f"issues {','.join('#'+str(i.number) for i in issues)}"
        )

    print("\n".join(created))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", action="append", dest="repos")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repos = tuple(args.repos) if args.repos else DEFAULT_REPOS
    try:
        return ingest(repos, dry_run=args.dry_run)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"AI_OS_INGEST_FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
