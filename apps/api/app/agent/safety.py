"""Agent safety layer — deny destructive commands."""
from __future__ import annotations

import re
from typing import Tuple

# Substring patterns that are always blocked.
_DENYLIST_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf\s+/?($|\s)", "rm -rf / — refuses to wipe root filesystem"),
    (r"rm\s+-rf\s+~", "rm -rf ~ — refuses to wipe home directory"),
    (r"mkfs\.", "mkfs — refuses to format filesystem"),
    (r"dd\s+if=.*\s+of=/dev/", "dd to block device — refuses raw disk write"),
    (r":\(\)\{\s*:\s*\|\s*:\s*&\s*\};\s*:", "fork bomb detected"),
    (r"\bshutdown\b", "shutdown is denied without explicit override"),
    (r"\bpoweroff\b", "poweroff is denied without explicit override"),
    (r"\breboot\b", "reboot is denied without explicit override"),
    (r"halt\b", "halt is denied without explicit override"),
    (r">\s*/dev/sda", "writing directly to /dev/sda"),
    (r"chmod\s+-R\s+777\s+/", "chmod -R 777 / — refuses world-writable root"),
]

_COMPILED = [(re.compile(p, re.MULTILINE), reason) for p, reason in _DENYLIST_PATTERNS]


def check_command(command: str) -> Tuple[bool, str]:
    """Return (allowed, reason). allowed=False means the command must be refused."""
    for pattern, reason in _COMPILED:
        if pattern.search(command):
            return False, reason
    return True, ""


def is_destructive(command: str) -> bool:
    """Lighter heuristic — flags commands that *should* require approval even if not outright denied."""
    destructive_markers = [
        r"\brm\s+-rf\b", r"\bdrop\s+table\b", r"\btruncate\b", r"\bdrop\s+database\b",
        r"\bkill\s+-9\b", r"\biptables\s+-F\b", r"systemctl\s+(stop|disable)",
    ]
    for m in destructive_markers:
        if re.search(m, command, re.IGNORECASE):
            return True
    return False
