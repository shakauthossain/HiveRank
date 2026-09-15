"""Run the pptxgenjs deck builder. Node is required; Python only shells out."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

DECK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "deck-builder")
)
SCRIPT = os.path.join(DECK_DIR, "build-deck.js")


def _node_bin() -> str:
    found = shutil.which("node")
    if found:
        return found
    nvm_root = os.path.join(os.path.expanduser("~"), ".nvm", "versions", "node")
    if os.path.isdir(nvm_root):
        versions = sorted(os.listdir(nvm_root), reverse=True)
        for version in versions:
            candidate = os.path.join(nvm_root, version, "bin", "node")
            if os.path.isfile(candidate):
                return candidate
    raise RuntimeError(
        "Node.js is required to build the PPTX deck (pptxgenjs). Install Node 20+ on the backend host."
    )


def build_pptx(payload: dict[str, Any], output_path: str) -> None:
    node = _node_bin()
    if not os.path.isfile(SCRIPT):
        raise RuntimeError(f"Deck builder script missing at {SCRIPT}")
    pptx_mod = os.path.join(DECK_DIR, "node_modules", "pptxgenjs")
    if not os.path.isdir(pptx_mod):
        raise RuntimeError(
            "pptxgenjs is not installed. Run npm install inside backend/deck-builder."
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    tmp_json = f"{output_path}.json"
    with open(tmp_json, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)

    try:
        result = subprocess.run(
            [node, SCRIPT, tmp_json, output_path],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=DECK_DIR,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(err or "pptxgenjs deck build failed")
        if not os.path.isfile(output_path):
            raise RuntimeError("Deck builder finished but did not write a PPTX file")
    finally:
        if os.path.isfile(tmp_json):
            os.remove(tmp_json)
