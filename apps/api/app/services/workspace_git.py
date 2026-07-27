"""Git operations in the workspace root (sandboxed)."""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path
from typing import Any

from app.services.workspace_fs import workspace_root

GIT_TIMEOUT = 45
DIFF_MAX_LINES = 500


def _run_git(args: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    root = cwd or workspace_root()
    if not (root / ".git").exists():
        return {"ok": False, "error": "not a git repository", "code": 128}

    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "git command timed out", "code": -1}
    except FileNotFoundError:
        return {"ok": False, "error": "git not installed", "code": -1}

    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "code": proc.returncode,
    }


def _parse_status(stdout: str) -> dict[str, Any]:
    staged: list[dict[str, str]] = []
    unstaged: list[dict[str, str]] = []
    untracked: list[str] = []

    for line in stdout.splitlines():
        if not line or line.startswith("## "):
            continue
        if line.startswith("??"):
            untracked.append(line[3:].strip())
            continue
        index, worktree = line[0], line[1] if len(line) > 1 else " "
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if index != " " and index != "?":
            staged.append({"status": index, "path": path})
        if worktree != " " and worktree != "?":
            unstaged.append({"status": worktree, "path": path})

    return {"staged": staged, "unstaged": unstaged, "untracked": untracked}


def _parse_diff_hunks(diff_text: str) -> list[dict[str, Any]]:
    """Parse unified diff into structured hunks for the UI."""
    hunks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current:
                hunks.append(current)
            current = {"header": line, "lines": []}
        elif line.startswith("+++") or line.startswith("---"):
            if current is not None:
                current["lines"].append({"type": "meta", "text": line})
        elif line.startswith("@@"):
            if current is not None:
                current["lines"].append({"type": "hunk", "text": line})
        elif current is not None:
            if line.startswith("+"):
                current["lines"].append({"type": "add", "text": line[1:]})
            elif line.startswith("-"):
                current["lines"].append({"type": "del", "text": line[1:]})
            else:
                current["lines"].append({"type": "ctx", "text": line[1:] if line.startswith(" ") else line})

    if current:
        hunks.append(current)
    return hunks[:20]


async def git_status() -> dict[str, Any]:
    branch = await asyncio.to_thread(_run_git, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = await asyncio.to_thread(_run_git, ["status", "--porcelain", "-b"])
    if not status["ok"]:
        return status

    branch_name = "unknown"
    for line in status["stdout"].splitlines():
        if line.startswith("## "):
            branch_name = line[3:].split("...")[0].strip()
            break

    parsed = _parse_status("\n".join(l for l in status["stdout"].splitlines() if not l.startswith("##")))
    return {
        "ok": True,
        "branch": branch_name if branch["ok"] else branch_name,
        "clean": not (parsed["staged"] or parsed["unstaged"] or parsed["untracked"]),
        **parsed,
    }


async def git_diff(path: str = "", staged: bool = False) -> dict[str, Any]:
    args = ["diff", "--no-color"]
    if staged:
        args.append("--cached")
    if path:
        args.extend(["--", path])

    result = await asyncio.to_thread(_run_git, args)
    if not result["ok"] and not result["stdout"]:
        return result

    diff_text = result["stdout"]
    lines = diff_text.splitlines()
    if len(lines) > DIFF_MAX_LINES:
        diff_text = "\n".join(lines[:DIFF_MAX_LINES]) + f"\n... ({len(lines) - DIFF_MAX_LINES} more lines)"

    return {
        "ok": True,
        "path": path or None,
        "staged": staged,
        "raw": diff_text,
        "hunks": _parse_diff_hunks(result["stdout"]),
        "has_changes": bool(result["stdout"].strip()),
    }


async def git_branches() -> dict[str, Any]:
    result = await asyncio.to_thread(_run_git, ["branch", "-a", "--no-color"])
    if not result["ok"]:
        return result
    branches = []
    current = None
    for line in result["stdout"].splitlines():
        name = line.strip().lstrip("* ").strip()
        if line.startswith("*"):
            current = name
        branches.append(name)
    return {"ok": True, "current": current, "branches": branches}


async def git_log(limit: int = 15) -> dict[str, Any]:
    limit = max(1, min(int(limit), 50))
    result = await asyncio.to_thread(
        _run_git,
        ["log", f"-{limit}", "--oneline", "--no-decorate"],
    )
    if not result["ok"]:
        return result
    commits = []
    for line in result["stdout"].splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "message": parts[1]})
    return {"ok": True, "commits": commits}


async def git_add(paths: list[str]) -> dict[str, Any]:
    if not paths:
        return await asyncio.to_thread(_run_git, ["add", "-A"])
    return await asyncio.to_thread(_run_git, ["add", "--", *paths])


async def git_commit(message: str) -> dict[str, Any]:
    if not message.strip():
        return {"ok": False, "error": "commit message required"}
    if len(message) > 500:
        return {"ok": False, "error": "commit message too long"}
    return await asyncio.to_thread(_run_git, ["commit", "-m", message])


async def git_checkout(branch: str) -> dict[str, Any]:
    if not re.match(r"^[a-zA-Z0-9._/-]+$", branch):
        return {"ok": False, "error": "invalid branch name"}
    return await asyncio.to_thread(_run_git, ["checkout", branch])


def text_diff(old_text: str, new_text: str) -> list[dict[str, str]]:
    """Simple line diff for editor save preview."""
    import difflib

    lines: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2, text in difflib.SequenceMatcher(
        None, old_text.splitlines(), new_text.splitlines()
    ).get_opcodes():
        chunk_old = old_text.splitlines()[i1:i2]
        chunk_new = new_text.splitlines()[j1:j2]
        if tag == "equal":
            for t in chunk_old:
                lines.append({"type": "ctx", "text": t})
        elif tag == "delete":
            for t in chunk_old:
                lines.append({"type": "del", "text": t})
        elif tag == "insert":
            for t in chunk_new:
                lines.append({"type": "add", "text": t})
        elif tag == "replace":
            for t in chunk_old:
                lines.append({"type": "del", "text": t})
            for t in chunk_new:
                lines.append({"type": "add", "text": t})
    return lines[:DIFF_MAX_LINES]
