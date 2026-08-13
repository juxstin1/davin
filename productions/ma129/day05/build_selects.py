"""Build 'MA129 D5 selects v1' from day05/selects.json with beat markers."""

from __future__ import annotations

import json
from pathlib import Path

from davin.client import DavinClient, timeline_fps

WORK = Path(r"C:\Users\juxxs\Desktop\davin\ma129\day05")
SRC = Path(
    r"C:\Users\juxxs\Downloads\MA129-Music Therapy-20260723T214044Z-1-001"
    r"\MA129-Music Therapy"
)
PROJECT = "DASH-MA129"
TIMELINE = "MA129 D5 selects v2"

BEAT_COLORS = {
    "1.2 The Story Enters": "Yellow",
    "2.1 Arrival": "Green",
    "2.2 First Gift": "Red",
    "2.3 Story Deepens": "Purple",
    "2.4 Decision to Scale": "Fuchsia",
    "INT Trish": "Sky",
    "INT Gail": "Rose",
}


def main():
    data = json.loads((WORK / "selects.json").read_text(encoding="utf-8"))
    selects = data["selects"]
    ranges = [(s["start"], s["end"]) for s in selects]

    client = DavinClient.connect()
    client.ensure_project(PROJECT)
    timeline, fps = client.papercut(SRC / data["source"], ranges, TIMELINE)
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
