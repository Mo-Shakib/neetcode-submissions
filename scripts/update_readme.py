#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
INDEX_PATH = ROOT / "index.html"

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


def latest_by_problem(submissions: list[Submission]) -> list[Submission]:
    latest_map: dict[str, Submission] = {}
    for sub in submissions:
        existing = latest_map.get(sub.problem_slug)
        if existing is None:
            latest_map[sub.problem_slug] = sub
            continue

        if (sub.timestamp, sub.submission_index, sub.rel_path) > (
            existing.timestamp,
            existing.submission_index,
            existing.rel_path,
        ):
            latest_map[sub.problem_slug] = sub

    return sorted(
        latest_map.values(),
        key=lambda s: (s.timestamp, s.submission_index, s.rel_path),
        reverse=True,
    )


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


def build_progress_block(submissions: list[Submission], now_utc: str) -> str:
    problems = {s.problem_slug for s in submissions}
    topics = {s.topic for s in submissions}

    lines = [
        f"- Problems solved: **{len(problems)}**",
        f"- Total submissions: **{len(submissions)}**",
        f"- Topics covered: **{len(topics)}**",
        f"- Last refreshed (UTC): **{now_utc}**",
    ]
    return "\n".join(lines)


def build_recent_block(items: list[Submission], limit: int = 10) -> str:
    if not items:
        return "- No submissions found yet."

    lines: list[str] = []
    for sub in items[:limit]:
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


def build_index_html(submissions: list[Submission], items: list[Submission], now_utc: str) -> str:
    problems_count = len({s.problem_slug for s in submissions})
    topics_count = len({s.topic for s in submissions})
    submissions_count = len(submissions)

    if items:
        list_items = []
        for sub in items[:12]:
            title = escape(to_title(sub.problem_slug))
            problem_url = f"https://neetcode.io/problems/{sub.problem_slug}/"
            local_link = "./" + quote(sub.rel_path, safe="/-_.~")
            list_items.append(
                (
                    "<li class=\"solution-item\">"
                    f"<a class=\"problem-link\" href=\"{problem_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{title}</a>"
                    f"<a class=\"code-link\" href=\"{local_link}\">View Solution</a>"
                    "</li>"
                )
            )
        recent_html = "\n".join(list_items)
    else:
        recent_html = "<li class=\"solution-item empty\">No submissions found yet.</li>"

    person_schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "MD SHAKIB MOLLA",
        "alternateName": ["Shakib", "Mo-shakib", "Mo-Shakib"],
        "url": "https://github.com/mo-shakib",
        "sameAs": [
            "https://github.com/mo-shakib",
            "https://linkedin.com/in/mo-shakib",
        ],
        "jobTitle": "Software Engineer",
    }

    schema_json = json.dumps(person_schema, ensure_ascii=True)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NeetCode Journey | MD SHAKIB MOLLA</title>
  <meta name="description" content="NeetCode practice tracker by MD SHAKIB MOLLA (Shakib / Mo-shakib) with progress, recent solutions, and direct problem links." />
  <meta name="keywords" content="MD SHAKIB MOLLA, Shakib, Mo-shakib, NeetCode, coding interview, DSA, LeetCode style, GitHub Pages" />
  <meta name="author" content="MD SHAKIB MOLLA" />
  <meta name="robots" content="index,follow" />
  <link rel="canonical" href="https://mo-shakib.github.io/neetcode-submissions/" />

  <meta property="og:type" content="website" />
  <meta property="og:title" content="NeetCode Journey | MD SHAKIB MOLLA" />
  <meta property="og:description" content="Live NeetCode progress and recent solution links by MD SHAKIB MOLLA." />
  <meta property="og:url" content="https://mo-shakib.github.io/neetcode-submissions/" />
  <meta property="og:site_name" content="NeetCode Journey - Mo-Shakib" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="NeetCode Journey | MD SHAKIB MOLLA" />
  <meta name="twitter:description" content="Track NeetCode progress, recent solutions, and direct problem links." />

  <script type="application/ld+json">{schema_json}</script>

  <style>
    :root {{
      --lc-bg: #121212;
      --lc-surface: #1e1e1e;
      --lc-surface-2: #262626;
      --lc-border: #3a3a3a;
      --lc-text: #f5f5f5;
      --lc-muted: #b8b8b8;
      --lc-accent: #ffa116;
      --lc-accent-soft: rgba(255, 161, 22, 0.14);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
      color: var(--lc-text);
      background:
        radial-gradient(circle at top right, rgba(255, 161, 22, 0.12), transparent 35%),
        radial-gradient(circle at 20% 80%, rgba(255, 161, 22, 0.08), transparent 40%),
        var(--lc-bg);
      min-height: 100vh;
      line-height: 1.6;
    }}

    .container {{
      max-width: 980px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }}

    .hero {{
      border: 1px solid var(--lc-border);
      background: linear-gradient(145deg, rgba(255, 161, 22, 0.14), rgba(30, 30, 30, 0.95));
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 18px;
    }}

    .hero h1 {{
      margin: 0 0 8px;
      font-size: clamp(1.65rem, 4vw, 2.3rem);
      letter-spacing: 0.02em;
    }}

    .hero p {{
      margin: 0;
      color: var(--lc-muted);
    }}

    .links {{
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .pill {{
      display: inline-block;
      text-decoration: none;
      color: var(--lc-text);
      border: 1px solid var(--lc-border);
      background: var(--lc-surface);
      border-radius: 999px;
      padding: 7px 12px;
      font-size: 0.92rem;
    }}

    .pill:hover {{
      border-color: var(--lc-accent);
      box-shadow: 0 0 0 3px var(--lc-accent-soft);
    }}

    .grid {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(12, minmax(0, 1fr));
    }}

    .card {{
      border: 1px solid var(--lc-border);
      background: var(--lc-surface);
      border-radius: 14px;
      padding: 18px;
    }}

    .card h2 {{
      margin: 0 0 12px;
      font-size: 1.15rem;
      color: var(--lc-accent);
    }}

    .structure {{
      grid-column: span 5;
    }}

    .progress {{
      grid-column: span 7;
    }}

    .recent {{
      grid-column: span 12;
      background: var(--lc-surface-2);
    }}

    pre {{
      margin: 0;
      white-space: pre-wrap;
      font-size: 0.95rem;
      color: var(--lc-muted);
    }}

    .stats {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}

    .stat {{
      border: 1px solid var(--lc-border);
      border-radius: 10px;
      padding: 10px;
      background: #191919;
    }}

    .stat-label {{
      display: block;
      color: var(--lc-muted);
      font-size: 0.86rem;
    }}

    .stat-value {{
      font-size: 1.2rem;
      font-weight: 700;
    }}

    .solutions {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}

    .solution-item {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border: 1px solid var(--lc-border);
      border-radius: 10px;
      padding: 10px 12px;
      background: #1a1a1a;
    }}

    .solution-item.empty {{
      color: var(--lc-muted);
      justify-content: center;
    }}

    .problem-link {{
      color: var(--lc-text);
      text-decoration: none;
      font-weight: 600;
    }}

    .problem-link:hover {{
      color: var(--lc-accent);
    }}

    .code-link {{
      color: var(--lc-accent);
      text-decoration: none;
      white-space: nowrap;
      font-size: 0.9rem;
    }}

    .code-link:hover {{
      text-decoration: underline;
    }}

    footer {{
      margin-top: 20px;
      color: var(--lc-muted);
      font-size: 0.9rem;
      text-align: center;
    }}

    footer a {{
      color: var(--lc-accent);
      text-decoration: none;
    }}

    @media (max-width: 860px) {{
      .structure,
      .progress {{
        grid-column: span 12;
      }}
    }}

    @media (max-width: 640px) {{
      .container {{
        padding: 16px 12px 30px;
      }}

      .hero {{
        padding: 16px;
      }}

      .stats {{
        grid-template-columns: 1fr;
      }}

      .solution-item {{
        align-items: flex-start;
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <main class="container">
    <section class="hero">
      <h1>NeetCode Journey</h1>
      <p>MD SHAKIB MOLLA (aka Shakib / Mo-shakib)</p>
      <p>Personal NeetCode tracker with live progress and recent submissions.</p>
      <div class="links">
        <a class="pill" href="https://github.com/mo-shakib" target="_blank" rel="noopener noreferrer">GitHub</a>
        <a class="pill" href="https://linkedin.com/in/mo-shakib" target="_blank" rel="noopener noreferrer">LinkedIn</a>
        <a class="pill" href="https://github.com/mo-shakib/neetcode-submissions" target="_blank" rel="noopener noreferrer">Repository</a>
      </div>
    </section>

    <section class="grid">
      <article class="card structure">
        <h2>Repository Structure</h2>
        <pre>&lt;topic-folder&gt;/
  &lt;problem-slug&gt;/
    submission-0.&lt;ext&gt;
    submission-1.&lt;ext&gt;</pre>
      </article>

      <article class="card progress">
        <h2>Progress</h2>
        <ul class="stats">
          <li class="stat">
            <span class="stat-label">Problems Solved</span>
            <span class="stat-value">{problems_count}</span>
          </li>
          <li class="stat">
            <span class="stat-label">Total Submissions</span>
            <span class="stat-value">{submissions_count}</span>
          </li>
          <li class="stat">
            <span class="stat-label">Topics Covered</span>
            <span class="stat-value">{topics_count}</span>
          </li>
          <li class="stat">
            <span class="stat-label">Last Refreshed (UTC)</span>
            <span class="stat-value">{escape(now_utc)}</span>
          </li>
        </ul>
      </article>

      <article class="card recent">
        <h2>Recent Solutions</h2>
        <ul class="solutions">
{recent_html}
        </ul>
      </article>
    </section>

    <footer>
      Automatically synced from <a href="https://neetcode.io" target="_blank" rel="noopener noreferrer">NeetCode</a>.
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    submissions = collect_submissions()
    latest_items = latest_by_problem(submissions)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    progress_block = build_progress_block(submissions, now_utc)
    recent_block = build_recent_block(latest_items)

    updated = replace_section(readme, PROGRESS_HEADING, progress_block)
    updated = replace_section(updated, RECENT_HEADING, recent_block)

    index_html = build_index_html(submissions, latest_items, now_utc)

    if updated != readme:
        README_PATH.write_text(updated, encoding="utf-8")
    if not INDEX_PATH.exists() or INDEX_PATH.read_text(encoding="utf-8") != index_html:
        INDEX_PATH.write_text(index_html, encoding="utf-8")

    # Helpful summary in CI logs
    problems = len({s.problem_slug for s in submissions})
    print(
        "Updated README/index with "
        f"{problems} problems and {len(submissions)} submissions."
    )


if __name__ == "__main__":
    main()
