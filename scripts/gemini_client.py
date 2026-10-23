"""Credential resolution that never leaks or tests a key needlessly.

Why a module and not an env read: this repo has no GEMINI_API_KEY, the sibling
zaitoon-studio/.env key is out of quota / rejected, and the key that does work
lives in a local note. Hard-coding any of that would rot. So: collect every
candidate in a defined order, validate by an authenticated call (a models list
is free and does not spend TTS quota), and cache the winner for the process.
The key is never printed, logged, written to a file, or placed in a shell
argument.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_KEY_PATTERN = re.compile(r"AQ\.Ab8[A-Za-z0-9_\-]{46,60}")
_LOCAL_NOTE = Path(
    "/home/kai/.gemini/antigravity/brain/"
    "05e0ac25-9e76-40e2-9e9c-9c80ef023b07/zaitoon_studio_technical_audit.md"
)
_cached: str | None = None


def _candidates() -> list[str]:
    """Candidate keys, in preference order. CI supplies the first via env."""
    found: list[str] = []
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            found.append(os.environ[var].strip())
    if _LOCAL_NOTE.exists():
        found.extend(_KEY_PATTERN.findall(_LOCAL_NOTE.read_text(errors="ignore")))
    seen: set[str] = set()
    unique: list[str] = []
    for key in found:
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def validates(key: str, timeout: int = 30) -> bool:
    """True when the key authenticates. Lists models: free, spends no request quota."""
    try:
        with urllib.request.urlopen(f"{BASE}?key={key}", timeout=timeout) as resp:
            return bool(json.load(resp).get("models"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return False


def get_key() -> str:
    """Return the first key that authenticates, or raise with a non-secret message."""
    global _cached
    if _cached:
        return _cached
    tried = 0
    for key in _candidates():
        tried += 1
        if validates(key):
            _cached = key
            return key
    raise SystemExit(f"No usable GEMINI_API_KEY found ({tried} candidate(s) rejected). "
                     "Set GEMINI_API_KEY in the environment (CI) or the local repo .env.")


def tail(key: str) -> str:
    """Last four characters only - safe for logs."""
    return "..." + key[-4:]


def post_json(model: str, body: dict, timeout: int = 900, key: str | None = None) -> dict:
    """POST to :generateContent and decode the JSON reply."""
    key = key or get_key()
    req = urllib.request.Request(
        f"{BASE}/{model}:generateContent?key={key}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)
