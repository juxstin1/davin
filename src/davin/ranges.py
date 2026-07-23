"""Kept-range edit lists (seconds, half-open [start, end)) and the
captions -> ranges seam: whoever chooses (model, regex, human) drops
captions; the survivors merge into ranges."""

from __future__ import annotations

import json
import re
from pathlib import Path

_START_KEYS = ("start", "startSeconds", "start_s", "startSec")
_END_KEYS = ("end", "endSeconds", "end_s", "endSec")


def _pick(d: dict, keys: tuple[str, ...], path: str) -> float:
    for k in keys:
        if k in d:
            return float(d[k])
    raise ValueError(f"{path}: range object missing any of {keys}: {d}")


def load_ranges(path: str | Path) -> list[tuple[float, float]]:
    """Accepts [[s,e],...], [{start,end},...], or {"ranges":[...]}.

    start/end keys may also be startSeconds/endSeconds or start_s/end_s,
    matching the avenger KeptRange shapes. Values are seconds.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("ranges", data.get("keptRanges"))
        if data is None:
            raise ValueError(f"{path}: expected a list or a 'ranges' key")

    ranges: list[tuple[float, float]] = []
    for entry in data:
        if isinstance(entry, dict):
            start = _pick(entry, _START_KEYS, str(path))
            end = _pick(entry, _END_KEYS, str(path))
        else:
            start, end = float(entry[0]), float(entry[1])
        if end <= start:
            raise ValueError(f"{path}: empty or inverted range ({start}, {end})")
        ranges.append((start, end))
    if not ranges:
        raise ValueError(f"{path}: no ranges found")
    return ranges


def load_captions(path: str | Path) -> list[dict]:
    """Load [{start, end, text}] from `davin transcript` output or a bare list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    captions = data.get("captions") if isinstance(data, dict) else data
    if not isinstance(captions, list) or not captions:
        raise ValueError(f"{path}: no captions found")
    return captions


def captions_to_ranges(
    captions: list[dict],
    drop: set[int] | None = None,
    drop_matching: str | None = None,
    join_gap: float = 0.5,
    pad: float = 0.0,
) -> tuple[list[tuple[float, float]], list[dict]]:
    """Drop captions (1-based indices and/or regex), merge survivors into ranges.

    Adjacent kept captions closer than join_gap seconds become one range.
    pad widens each range on both sides without overlapping its neighbours.
    Returns (ranges, dropped_captions).
    """
    drop = drop or set()
    pattern = re.compile(drop_matching, re.IGNORECASE) if drop_matching else None
    kept, dropped = [], []
    for idx, cap in enumerate(captions, 1):
        if idx in drop or (pattern and pattern.search(cap["text"])):
            dropped.append({"index": idx, **cap})
        else:
            kept.append((float(cap["start"]), float(cap["end"])))
    merged: list[list[float]] = []
    for start, end in kept:
        if merged and start - merged[-1][1] <= join_gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    if pad > 0:
        for i, rng in enumerate(merged):
            rng[0] = max(0.0, rng[0] - pad, merged[i - 1][1] if i else 0.0)
            rng[1] = rng[1] + pad
            if i + 1 < len(merged):
                rng[1] = min(rng[1], merged[i + 1][0])
    return [tuple(r) for r in merged], dropped


def save_ranges(ranges: list[tuple[float, float]], path: str | Path) -> None:
    payload = {"ranges": [{"start": s, "end": e} for s, e in ranges]}
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
