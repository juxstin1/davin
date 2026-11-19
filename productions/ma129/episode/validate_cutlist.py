"""Merge + validate the section cutlists into episode\\cutlist.json.

Checks every segment: label exists in that day's selects, range lies within
the select, sane duration, and no banned EP words in the captions under it.
B-roll base segments ("source": "<x>broll") skip the select/caption checks.
Also checks every overlay addresses an existing (label, occurrence).
Fails loudly; writes cutlist.json only if fully clean.

v4 adds Act 1 (Day 7 shop). v3's inputs are git 78ad9ca.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MA = Path(__file__).resolve().parents[1]
EP = MA / "episode"
BANNED = re.compile(r"nominat|this production", re.IGNORECASE)

SELECTS = {
    5: MA / "day05" / "selects.json",
    6: MA / "selects.json",
    7: MA / "day07" / "selects.json",
}
CAPTIONS = {
    5: MA / "day05" / "D5_CLIP_REEL.captions.json",
    6: MA / "MA129_CLIP_REEL.captions.json",
    7: MA / "day07" / "MA129_D7_CLIP_REEL.captions.json",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sections():
    bookends = load(EP / "bookends.json")
    return [
        {"name": "cold_open", "color": "Lemon", "segments": bookends["cold_open"]},
        {"name": "act1", "color": "Mint", "segments": load(EP / "act1.json")["segments"]},
        {"name": "act12", "color": "Green", "segments": load(EP / "act12.json")["segments"]},
        {"name": "act3", "color": "Red", "segments": load(EP / "act3.json")["segments"]},
        {"name": "closing", "color": "Purple", "segments": bookends["closing"]},
    ]


def main():
    selects = {}
    for day, p in SELECTS.items():
        for s in load(p)["selects"]:
            selects.setdefault(day, {}).setdefault(s["label"], []).append((s["start"], s["end"]))
    captions = {day: load(p)["captions"] for day, p in CAPTIONS.items()}
    secs = sections()

    problems, seen = [], {}
    for section in secs:
        for seg in section["segments"]:
            day, label = seg["day"], seg["label"]
            where = f"{section['name']}/{label}"
            seen[label] = seen.get(label, 0) + 1
            s, e = float(seg["start"]), float(seg["end"])
            if e - s < 1.0:
                problems.append(f"{where}: too short ({e - s:.2f}s)")
            if seg.get("source", "").endswith("broll"):
                if e - s > 20:
                    problems.append(f"{where}: b-roll base segment over 20s")
                continue
            ranges = selects.get(day, {}).get(label)
            if not ranges:
                problems.append(f"{where}: no select named {label!r} on day {day}")
                continue
            if not any(a - 0.01 <= s < e <= b + 0.01 for a, b in ranges):
                problems.append(f"{where}: range {s}-{e} outside select(s) {ranges}")
            text = " ".join(
                c["text"] for c in captions[day] if c["start"] < e and c["end"] > s
            )
            hit = BANNED.search(text)
            if hit:
                problems.append(f"{where}: banned word {hit.group(0)!r} in captions")

    for ov in load(EP / "overlays.json")["overlays"]:
        if ov.get("occurrence", 1) > seen.get(ov["at_label"], 0):
            problems.append(f"overlay {ov['source']}@{ov['at_label']}#{ov.get('occurrence', 1)}: no such base segment")

    total = sum(s["end"] - s["start"] for sec in secs for s in sec["segments"])
    for sec in secs:
        t = sum(s["end"] - s["start"] for s in sec["segments"])
        print(f"{sec['name']:<10} {len(sec['segments']):>2} cuts  {int(t // 60)}:{t % 60:04.1f}")
    print(f"{'TOTAL':<10} {sum(len(s['segments']) for s in secs):>2} cuts  {int(total // 60)}:{total % 60:04.1f}")

    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    (EP / "cutlist.json").write_text(
        json.dumps({"sections": secs}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\nclean -> cutlist.json")


if __name__ == "__main__":
    main()
