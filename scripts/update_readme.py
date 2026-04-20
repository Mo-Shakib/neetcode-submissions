#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"

PROGRESS_HEADING = "## Progress"
RECENT_HEADING = "## Recent Solutions"

SUBMISSION_FILE_RE = re.compile(r"^submission-(\d+)\.[^.]+$")


@dataclass
class Submission:
    rel_path: str
    topic: str
    problem_slug: str
    submission_index: int
    timestamp: int


def run_git_log() -> dict[str, int]:
    """
    Build a map of file path -> latest commit timestamp (epoch seconds) using git log.
    """
    cmd = ["git", "log", "--name-only", "--pretty=format:__TS__%ct"]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    timestamps: dict[str, int] = {}
    current_ts = 0

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__TS__"):
            try:
                current_ts = int(line.replace("__TS__", "", 1))
            except ValueError:
                current_ts = 0
            continue

        if line not in timestamps:
            timestamps[line] = current_ts

    return timestamps


def to_title(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def collect_submissions() -> list[Submission]:
    git_ts = run_git_log()
    submissions: list[Submission] = []

    for file_path in ROOT.rglob("submission-*.*"):
        if not file_path.is_file():
            continue

        match = SUBMISSION_FILE_RE.match(file_path.name)
        if not match:
            continue

        rel = file_path.relative_to(ROOT).as_posix()
        parts = file_path.relative_to(ROOT).parts

        # Expected shape: <topic>/<problem>/submission-N.ext
        if len(parts) < 3:
            continue

        topic = parts[-3]
        problem_slug = parts[-2]
        submission_index = int(match.group(1))

        timestamp = git_ts.get(rel)
        if timestamp is None:
            timestamp = int(file_path.stat().st_mtime)

        submissions.append(
            Submission(
                rel_path=rel,
                topic=topic,
                problem_slug=problem_slug,
                submission_index=submission_index,
                timestamp=timestamp,
            )
        )

    return submissions


def build_progress_block(submissions: list[Submission]) -> str:
    problems = {s.problem_slug for s in submissions}
    topics = {s.topic for s in submissions}
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"- Problems solved: **{len(problems)}**",
        f"- Total submissions: **{len(submissions)}**",
        f"- Topics covered: **{len(topics)}**",
        f"- Last refreshed (UTC): **{now_utc}**",
    ]
    return "\n".join(lines)


def build_recent_block(submissions: list[Submission], limit: int = 10) -> str:
    latest_by_problem: dict[str, Submission] = {}

    for sub in submissions:
        existing = latest_by_problem.get(sub.problem_slug)
        if existing is None:
            latest_by_problem[sub.problem_slug] = sub
            continue

        if (sub.timestamp, sub.submission_index, sub.rel_path) > (
            existing.timestamp,
            existing.submission_index,
            existing.rel_path,
        ):
            latest_by_problem[sub.problem_slug] = sub

    sorted_items = sorted(
        latest_by_problem.values(),
        key=lambda s: (s.timestamp, s.submission_index, s.rel_path),
        reverse=True,
    )

    if not sorted_items:
        return "- No submissions found yet."

    lines: list[str] = []
    for sub in sorted_items[:limit]:
        title = to_title(sub.problem_slug)
        problem_url = f"https://neetcode.io/problems/{sub.problem_slug}/"
        local_link = "./" + quote(sub.rel_path, safe="/-_.~")
        lines.append(
            f"- [{title}]({problem_url}) - [Solution]({local_link})"
        )

    return "\n".join(lines)


def replace_section(text: str, heading: str, new_body: str) -> str:
    pattern = re.compile(
        rf"({re.escape(heading)}\n)(.*?)(?=\n## |\n---\n|\Z)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise RuntimeError(f"Could not replace section: {heading}")
    return pattern.sub(rf"\1\n{new_body}\n", text, count=1)


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    submissions = collect_submissions()

    progress_block = build_progress_block(submissions)
    recent_block = build_recent_block(submissions)

    updated = replace_section(readme, PROGRESS_HEADING, progress_block)
    updated = replace_section(updated, RECENT_HEADING, recent_block)

    if updated != readme:
        README_PATH.write_text(updated, encoding="utf-8")

    # Helpful summary in CI logs
    problems = len({s.problem_slug for s in submissions})
    print(f"Updated README with {problems} problems and {len(submissions)} submissions.")


if __name__ == "__main__":
    main()
