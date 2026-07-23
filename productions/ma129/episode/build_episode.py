"""Assemble the MA129 episode from the merged cutlist (multi-source papercut).

Reads episode\cutlist.json: {"sections":[{"name","color","segments":[
{"day":5|6,"label","start","end","note"}]}]} and builds one timeline that
interleaves the Day 5 and Day 6 clip reels, with a marker per segment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from davin.client import DavinClient, timeline_fps

EP = Path(r"C:\Users\juxxs\Desktop\davin\ma129\episode")
PROJECT = "DASH-MA129"
REEL_BY_DAY = {
    5: r"C:\Users\juxxs\Downloads\MA129-Music Therapy-20260723T214044Z-1-001"
       r"\MA129-Music Therapy\MA129-Music Therapy_CLIP_REEL.mp4",
    6: r"C:\Users\juxxs\Downloads\drive-download-20260723T211350Z-1-001"
       r"\MA129_CLIP_REEL.mp4",
}


def main(timeline_name: str = "MA129 episode assembly v1"):
    data = json.loads((EP / "cutlist.json").read_text(encoding="utf-8"))
    client = DavinClient.connect()
    client.ensure_project(PROJECT)

    items = {day: client.find_clip(name) for day, name in REEL_BY_DAY.items()}
    fps = float(items[6].GetClipProperty("FPS"))

    flat = []  # (section, color, segment)
    clip_infos = []
    for section in data["sections"]:
        for seg in section["segments"]:
            start_f = max(0, round(seg["start"] * fps))
            end_f = max(start_f + 1, round(seg["end"] * fps))
            clip_infos.append(
                {
                    "mediaPoolItem": items[seg["day"]],
                    "startFrame": start_f,
                    "endFrame": end_f,
                }
            )
            flat.append((section["name"], section.get("color", "Blue"), seg))

    timeline = client.create_timeline(timeline_name, clip_infos, fps=fps)
    name = timeline.GetName()

    fps = timeline_fps(timeline)
    t0 = timeline.GetStartFrame()
    placed = timeline.GetItemListInTrack("video", 1) or []
    if len(placed) != len(flat):
        print(f"WARNING: {len(placed)} items vs {len(flat)} segments")
    marked = 0
    for item, (section, color, seg) in zip(placed, flat):
        note = f"D{seg['day']} {seg['label']}: {seg.get('note', '')}"[:180]
        if timeline.AddMarker(item.GetStart() - t0, color, seg["label"], note, 1):
            marked += 1

    total = sum(s["end"] - s["start"] for sec in data["sections"] for s in sec["segments"])
    print(f"timeline: {name} @ {fps:g} fps")
    print(f"{len(clip_infos)} cuts, {marked} markers, {total / 60:.1f} min")
    for section in data["sections"]:
        sec_total = sum(s["end"] - s["start"] for s in section["segments"])
        print(f"  {section['name']:<12} {len(section['segments']):>2} cuts  {sec_total / 60:.1f} min")
    client.save()
    print("saved.")
    return name


if __name__ == "__main__":
    main(*sys.argv[1:])
