"""Merge + validate the subagent cutlists into episode\\cutlist.json.

Checks every segment: label exists in that day's selects, range lies within
the select, sane duration, and no banned EP words in the captions under it.
Fails loudly; writes cutlist.json only if fully clean.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MA = Path(r"C:\Users\juxxs\Desktop\davin\ma129")
EP = MA / "episode"
BANNED = re.compile(r"nominat|this production", re.IGNORECASE)

SELECTS = {
    5: MA / "day05" / "selects.json",
    6: MA / "selects.json",
}
CAPTIONS = {
    5: MA / "day05" / "D5_CLIP_REEL.captions.json",
    6: MA / "MA129_CLIP_REEL.captions.json",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    selects = {
        day: {s["label"]: (s["start"], s["end"]) for s in load(p)["selects"]}
        for day, p in SELECTS.items()
    }
    captions = {day: load(p)["captions"] for day, p in CAPTIONS.items()}

    bookends = load(EP / "bookends.json")
    sections = [
        {"name": "cold_open", "color": "Lemon", "segments": bookends["cold_open"]},
        {"name": "act12", "color": "Green", "segments": load(EP / "act12.json")["segments"]},
        {"name": "act3", "color": "Red", "segments": load(EP / "act3.json")["segments"]},
        {"name": "closing", "color": "Purple", "segments": bookends["closing"]},
    ]

    problems = []
    for section in sections:
        for seg in section["segments"]:
            day, label = seg["day"], seg["label"]
            where = f"{section['name']}/{label}"
            sel = selects.get(day, {}).get(label)
            if sel is None:
                problems.append(f"{where}: no select named {label!r} on day {day}")
                continue
            s, e = float(seg["start"]), float(seg["end"])
            if not (sel[0] - 0.01 <= s < e <= sel[1] + 0.01):
                problems.append(
                    f"{where}: range {s}-{e} outside select {sel[0]}-{sel[1]}"
                )
            if e - s < 1.0:
                problems.append(f"{where}: too short ({e - s:.2f}s)")
            text = " ".join(
                c["text"] for c in captions[day] if c["start"] < e and c["end"] > s
            )
            hit = BANNED.search(text)
            if hit:
                problems.append(f"{where}: banned word {hit.group(0)!r} in captions")

    total = sum(
        s["end"] - s["start"] for sec in sections for s in sec["segments"]
    )
    for sec in sections:
        t = sum(s["end"] - s["start"] for s in sec["segments"])
        print(f"{sec['name']:<10} {len(sec['segments']):>2} cuts  {t / 60:5.1f} min")
    print(f"{'TOTAL':<10} {sum(len(s['segments']) for s in sections):>2} cuts  {total / 60:5.1f} min")

    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    (EP / "cutlist.json").write_text(
        json.dumps({"sections": sections}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("\nclean -> cutlist.json")


if __name__ == "__main__":
    main()
