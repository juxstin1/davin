"""Build 'MA129 D7 selects v1' from day07/selects.json with beat markers.

Needs MA129_CLIP_REEL.mp4 in selects.json's source_dir (missing from the
2026-11-19 drop - only the B-roll reels came through). Rerun after it lands:
    uv run python productions/ma129/day07/build_selects.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from davin.client import DavinClient, timeline_fps

HERE = Path(__file__).resolve().parent
PROJECT = "DASH-MA129"
TIMELINE = "MA129 D7 selects v1"

BEAT_COLORS = {
    "1.1 Shop Work": "Lavender",
    "1.2 The Story Enters": "Yellow",
    "1.4 First Gesture": "Mint",
}


def main():
    data = json.loads((HERE / "selects.json").read_text(encoding="utf-8"))
    selects = data["selects"]
    reel = Path(data["source_dir"]) / data["source"]
    if not reel.exists():
        sys.exit(f"clip reel not found: {reel}\n(download the rest of the Drive folder)")
    ranges = [(s["start"], s["end"]) for s in selects]

    client = DavinClient.connect()
    client.ensure_project(PROJECT)
    timeline, fps = client.papercut(reel, ranges, TIMELINE)
    print(f"timeline: {timeline.GetName()} @ {fps:g} fps, {len(ranges)} selects")

    fps = timeline_fps(timeline)
    t0 = timeline.GetStartFrame()
    items = timeline.GetItemListInTrack("video", 1) or []
    if len(items) != len(selects):
        print(f"WARNING: {len(items)} timeline items vs {len(selects)} selects")
    marked = 0
    for item, sel in zip(items, selects):
        color = BEAT_COLORS.get(sel["beat"], "Blue")
        if timeline.AddMarker(item.GetStart() - t0, color, sel["label"], sel["quote"][:180], 1):
            marked += 1
    total = sum(e - s for s, e in ranges)
    print(f"{marked}/{len(selects)} beat markers, {total / 60:.1f} min selected")
    client.save()
    print("saved.")


if __name__ == "__main__":
    main()
