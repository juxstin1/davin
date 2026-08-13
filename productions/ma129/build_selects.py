"""Build the 'MA129 selects v1' timeline from selects.json, with one
beat-labeled marker per select."""

from __future__ import annotations

import json
from pathlib import Path

from davin.client import DavinClient, timeline_fps

WORK = Path(r"C:\Users\juxxs\Desktop\davin\ma129")
SRC = Path(r"C:\Users\juxxs\Downloads\drive-download-20260723T211350Z-1-001")
PROJECT = "DASH-DAY06-MA129"
TIMELINE = "MA129 selects v3"

BEAT_COLORS = {
    "3.1 Before The Concert": "Yellow",
    "3.2 Performers Gather": "Green",
    "3.3 Reveal": "Red",
    "3.4 Closing Moment": "Purple",
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
    name = timeline.GetName()
    print(f"timeline: {name} @ {fps:g} fps, {len(ranges)} selects")

    # one marker per select at its in-point, colored by beat
    fps = timeline_fps(timeline)
    t0 = timeline.GetStartFrame()
    items = timeline.GetItemListInTrack("video", 1) or []
    if len(items) != len(selects):
        print(f"WARNING: {len(items)} timeline items vs {len(selects)} selects")
    marked = 0
    for item, sel in zip(items, selects):
        frame = item.GetStart() - t0
        color = BEAT_COLORS.get(sel["beat"], "Blue")
        if timeline.AddMarker(frame, color, sel["label"], sel["quote"][:180], 1):
            marked += 1
    total = sum(e - s for s, e in ranges)
    print(f"{marked}/{len(selects)} beat markers, {total / 60:.1f} min selected")
    client.save()
    print("saved.")


if __name__ == "__main__":
    main()
