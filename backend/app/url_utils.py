"""URL helpers for audits: validation and resolving canonical URLs from API results."""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """Ensures the URL has a protocol (http/https). Defaults to https."""
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith(("http://", "https://")):
        return u
    return f"https://{u}"


def extract_domain(url: str) -> str:
    """Hostname without leading www, for DataForSEO Labs/Backlinks targets."""
    parsed = urlparse(normalize_url(url))
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_valid_public_audit_url(url: str) -> tuple[bool, str]:
    """
    Reject values that cannot be real public websites (e.g. spreadsheet row ids
    like '552' normalized to https://552).
    """
    if not url or not url.startswith(("http://", "https://")):
        return False, "Enter a full website URL (e.g. https://example.com)."

    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False, "Missing hostname. Use a domain like example.com."

        if host in ("localhost", "127.0.0.1") or host.endswith(".localhost"):
            return True, ""

        # Bare numeric "hostnames" (row ids, internal codes)
        if re.fullmatch(r"\d+", host):
            return (
                False,
                f"'{host}' is not a website. Use the real domain (e.g. https://client.com), "
                "not row numbers or IDs.",
            )

        # Expect a registered-style name (contains a dot: example.com)
        if "." not in host:
            return (
                False,
                f"'{host}' does not look like a public domain. Include the full hostname "
                "(e.g. agencyname.com).",
            )

        return True, ""
    except Exception:
        return False, "Invalid URL format."


def _final_from_speed_block(block: Any) -> Optional[str]:
    if not isinstance(block, dict):
        return None
    fu = block.get("final_url")
    return fu if isinstance(fu, str) and fu.strip() else None


def resolved_url_for_storage(requested: str, speed_data: dict) -> str:
    """Prefer Lighthouse final URL when PageSpeed returned a real run."""
    if not speed_data:
        return requested
    mob = speed_data.get("mobile") or {}
    dsk = speed_data.get("desktop") or {}
    return (
        _final_from_speed_block(mob)
        or _final_from_speed_block(dsk)
        or requested
    )


def resolved_url_for_list(audit_url: str, full_results: Any) -> str:
    """Best URL to show in history lists (uses stored PageSpeed finalUrl when present)."""
    if not isinstance(full_results, dict):
        return audit_url
    spd = full_results.get("speed")
    if isinstance(spd, dict):
        for key in ("mobile", "desktop"):
            fu = _final_from_speed_block(spd.get(key))
            if fu:
                return fu
    return audit_url


def format_speed_score_for_storage(speed_data: dict) -> str:
    """Human-readable speed summary for DB (matches bulk style when both strategies exist)."""
    if not speed_data:
        return "N/A"
    mob = speed_data.get("mobile") if isinstance(speed_data.get("mobile"), dict) else {}
    dsk = speed_data.get("desktop") if isinstance(speed_data.get("desktop"), dict) else {}
    if not mob and not dsk:
        return str(speed_data.get("perf_score", "N/A"))
    m = mob.get("perf_score", "N/A") if mob else "N/A"
    d = dsk.get("perf_score", "N/A") if dsk else "N/A"
    return f"M:{m} D:{d}"
