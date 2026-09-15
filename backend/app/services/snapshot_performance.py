"""Slide 5: Performance & Core Web Vitals from PageSpeed (lab + CrUX field)."""

from __future__ import annotations

from typing import Any, Optional


def _tone_score(score: Optional[int]) -> str:
    if score is None:
        return "neutral"
    if score >= 90:
        return "pass"
    if score >= 50:
        return "warn"
    return "fail"


def _human(status: str) -> str:
    return {
        "pass": "Good",
        "warning": "Needs Improvement",
        "fail": "Poor",
        "na": "n/a",
    }.get(status or "na", "n/a")


def _tone(status: str) -> str:
    if status == "pass":
        return "pass"
    if status in ("warn", "warning"):
        return "warn"
    if status == "fail":
        return "fail"
    return "neutral"


def _cell(device: dict, key: str, kind: str = "field") -> dict[str, str]:
    if kind == "field":
        field = (device or {}).get("field") or {}
        metric = field.get(key) or {}
        display = metric.get("display") or "n/a"
        status = metric.get("status") or "na"
        label = metric.get("label") or _human(status)
        if display in ("n/a", "N/A", None):
            return {"text": "n/a", "tone": "neutral"}
        metric_bit = " INP" if key == "inp" else ""
        return {"text": f"{display}{metric_bit} — {label}", "tone": _tone(status)}
    display = (device or {}).get(key) or "n/a"
    status = (device or {}).get(f"{key}_status") or "na"
    if key == "tbt":
        extra = " TBT (lab proxy)"
        if display in ("n/a", "N/A", None):
            return {"text": "n/a", "tone": "neutral"}
        return {
            "text": f"{display}{extra}",
            "tone": _tone(status),
        }
    if display in ("n/a", "N/A", None):
        return {"text": "n/a", "tone": "neutral"}
    return {"text": f"{display} — {_human(status)}", "tone": _tone(status)}


def _cwv_verdict(mobile: dict, desktop: dict) -> tuple[str, str, str]:
    """Prefer Chrome field data; fall back to lab."""
    sources = []
    for block in (mobile, desktop):
        field = (block or {}).get("field") or {}
        if field:
            sources.append(field)
    statuses = []
    for field in sources:
        for key in ("lcp", "inp", "cls"):
            statuses.append((key, (field.get(key) or {}).get("status") or "na"))
    if not statuses:
        for block in (mobile, desktop):
            for key in ("lcp", "inp", "cls"):
                statuses.append((key, (block or {}).get(f"{key}_status") or "na"))
        source_note = "lab assessment"
    else:
        source_note = "field assessment"
    fails = [k for k, s in statuses if s == "fail"]
    warns = [k for k, s in statuses if s == "warning"]
    valid = [s for _k, s in statuses if s != "na"]
    if fails:
        return "FAILED", "fail", source_note
    if warns:
        return "MIXED", "warn", source_note
    if valid and all(s == "pass" for s in valid):
        return "PASSED", "pass", source_note
    return "n/a", "neutral", source_note


def _worst_metric(mobile: dict, desktop: dict) -> Optional[str]:
    order = ("cls", "lcp", "inp")
    field_m = (mobile or {}).get("field") or {}
    field_d = (desktop or {}).get("field") or {}
    for key in order:
        m = (field_m.get(key) or {}).get("status")
        d = (field_d.get(key) or {}).get("status")
        if m == "fail" or d == "fail":
            return key.upper()
    for key in order:
        if (mobile or {}).get(f"{key}_status") == "fail" or (desktop or {}).get(f"{key}_status") == "fail":
            return key.upper()
    return None


def build_performance_slide(payload: dict) -> dict[str, Any]:
    tech = payload.get("technical") or {}
    mobile = tech.get("mobile") or tech
    desktop = tech.get("desktop") or {}
    mobile_score = mobile.get("perf_score")
    desktop_score = desktop.get("perf_score")
    tbt = mobile.get("tbt") or "n/a"
    tbt_status = mobile.get("tbt_status") or "na"
    verdict, verdict_tone, source_note = _cwv_verdict(mobile, desktop)
    worst = _worst_metric(mobile, desktop)
    causes = list(mobile.get("causes") or [])
    for extra in desktop.get("causes") or []:
        if extra not in causes:
            causes.append(extra)

    cards = [
        {
            "value": "—" if mobile_score is None else f"{mobile_score} / 100",
            "label": "Mobile Performance",
            "subtext": "Lighthouse, PSI",
            "tone": _tone_score(mobile_score),
        },
        {
            "value": "—" if desktop_score is None else f"{desktop_score} / 100",
            "label": "Desktop Performance",
            "subtext": "Lighthouse, PSI",
            "tone": _tone_score(desktop_score),
        },
        {
            "value": tbt if tbt not in (None, "N/A") else "—",
            "label": "Lab TBT",
            "subtext": "PageSpeed lab",
            "tone": _tone(tbt_status),
        },
        {
            "value": verdict,
            "label": "Core Web Vitals",
            "subtext": source_note,
            "tone": verdict_tone,
        },
    ]

    rows = [
        {
            "metric": "LCP — Largest Contentful Paint",
            "mobile": _cell(mobile, "lcp", "field"),
            "desktop": _cell(desktop, "lcp", "field"),
            "lab": _cell(mobile, "lcp", "lab"),
        },
        {
            "metric": "INP / TBT — Responsiveness",
            "mobile": _cell(mobile, "inp", "field"),
            "desktop": _cell(desktop, "inp", "field"),
            "lab": _cell(mobile, "tbt", "lab"),
        },
        {
            "metric": "CLS — Cumulative Layout Shift",
            "mobile": _cell(mobile, "cls", "field"),
            "desktop": _cell(desktop, "cls", "field"),
            "lab": _cell(mobile, "cls", "lab"),
        },
    ]

    if worst == "CLS":
        cls_vals = []
        for block in (mobile, desktop):
            field = (block or {}).get("field") or {}
            raw = (field.get("cls") or {}).get("display")
            if raw and raw not in ("n/a", "N/A"):
                cls_vals.append(raw)
        if mobile.get("cls") not in (None, "N/A"):
            cls_vals.append(str(mobile.get("cls")))
        shown = ", ".join(cls_vals[:3]) if cls_vals else "the current value"
        cause_bit = (
            f" Root causes: {', '.join(causes)}."
            if causes
            else " Check unsized images, lazy-loaded LCP media, and late font/animation shifts."
        )
        takeaway = (
            f"CLS — not LCP — is the metric failing Core Web Vitals, confirmed on "
            f"PageSpeed field (CrUX) and lab ({shown}; 0.25 is the “poor” threshold)."
            f"{cause_bit} LCP is already passing or close — don’t spend budget chasing it."
            if (mobile.get("lcp_status") in ("pass", "warning") or ((mobile.get("field") or {}).get("lcp") or {}).get("status") in ("pass", "warning"))
            else (
                f"CLS is failing Core Web Vitals on PageSpeed field/lab ({shown})."
                f"{cause_bit}"
            )
        )
    elif worst == "LCP":
        takeaway = (
            f"Largest Contentful Paint is the Core Web Vital to fix first "
            f"({mobile.get('lcp') or 'see table'} on mobile lab). "
            f"{'Root causes: ' + ', '.join(causes) + '.' if causes else 'Compress the hero, preload the LCP image, and cut server wait.'}"
        )
    elif worst == "INP":
        takeaway = (
            f"Interaction to Next Paint is the Core Web Vital to fix first. "
            f"Lab Total Blocking Time is {tbt}. Cut main-thread JavaScript."
        )
    elif verdict == "PASSED":
        takeaway = "Core Web Vitals pass on the available PageSpeed field/lab data. Keep watching CLS when new templates ship."
    else:
        takeaway = "PageSpeed did not return a full Core Web Vitals set. Re-run after the origin has CrUX field data."

    return {
        "title": "Performance & Core Web Vitals",
        "cards": cards,
        "rows": rows,
        "takeaway": takeaway,
        "lab_header": "Lab (PageSpeed · mobile)",
    }
