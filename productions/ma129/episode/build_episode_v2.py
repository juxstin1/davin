"""Build episode assembly v2: v1 base cut + video-only b-roll/reaction
overlays on V2, placed relative to labeled base segments.

overlays.json: {"overlays":[{"source":"d5broll|d6broll|d5clip|d6clip",
"srcStart":s,"srcEnd":s,"at_label":"<base segment label>","occurrence":1,
"offset":<sec into that segment>,"note":"..."}]}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from davin.client import DavinClient, timeline_fps

EP = Path(r"C:\Users\juxxs\Desktop\davin\ma129\episode")
PROJECT = "DASH-MA129"
D5 = r"C:\Users\juxxs\Downloads\MA129-Music Therapy-20260723T214044Z-1-001\MA129-Music Therapy"
D6 = r"C:\Users\juxxs\Downloads\drive-download-20260723T211350Z-1-001"
SOURCES = {
    "d5clip": rf"{D5}\MA129-Music Therapy_CLIP_REEL.mp4",
    "d5broll": rf"{D5}\MA129-Music Therapy_BROLL_REEL.mp4",
    "d6clip": rf"{D6}\MA129_CLIP_REEL.mp4",
    "d6broll": rf"{D6}\MA129_BROLL_REEL.mp4",
}
DAY_SOURCE = {5: "d5clip", 6: "d6clip"}


def main(timeline_name: str = "MA129 episode assembly v2"):
    cutlist = json.loads((EP / "cutlist.json").read_text(encoding="utf-8"))
    overlays = json.loads((EP / "overlays.json").read_text(encoding="utf-8"))["overlays"]

    client = DavinClient.connect()
    client.ensure_project(PROJECT)
    items = {key: client.find_clip(path) for key, path in SOURCES.items()}
    fps = float(items["d6clip"].GetClipProperty("FPS"))

    # base cut (V1) + timeline-offset map per (label, occurrence)
    flat, clip_infos, seg_at = [], [], {}
    cursor = 0.0
    for section in cutlist["sections"]:
        for seg in section["segments"]:
            start_f = max(0, round(seg["start"] * fps))
            end_f = max(start_f + 1, round(seg["end"] * fps))
            clip_infos.append(
                {"mediaPoolItem": items[DAY_SOURCE[seg["day"]]],
                 "startFrame": start_f, "endFrame": end_f}
            )
            flat.append((section, seg, cursor))
            n = sum(1 for k in seg_at if k[0] == seg["label"]) + 1
            seg_at[(seg["label"], n)] = (cursor, seg["end"] - seg["start"])
            cursor += (end_f - start_f) / fps

    timeline = client.create_timeline(timeline_name, clip_infos, fps=fps)
    name = timeline.GetName()
    fps = timeline_fps(timeline)
    t0 = timeline.GetStartFrame()

    placed = timeline.GetItemListInTrack("video", 1) or []
    for item, (section, seg, _) in zip(placed, flat):
        note = f"D{seg['day']} {seg['label']}: {seg.get('note', '')}"[:180]
        timeline.AddMarker(item.GetStart() - t0, section.get("color", "Blue"),
                           seg["label"], note, 1)

    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")

    total_len = cursor
    ok, skipped = 0, []
    for ov in overlays:
        key = (ov["at_label"], ov.get("occurrence", 1))
        if key not in seg_at:
            skipped.append(f"{ov['at_label']}: no such base segment")
            continue
        seg_start, _ = seg_at[key]
        at = seg_start + ov.get("offset", 0.0)
        length = ov["srcEnd"] - ov["srcStart"]
        if at + length > total_len:
            length = max(1.0, total_len - at - 0.1)
        res = client.media_pool.AppendToTimeline([
            {"mediaPoolItem": items[ov["source"]],
             "startFrame": round(ov["srcStart"] * fps),
             "endFrame": round((ov["srcStart"] + length) * fps),
             "mediaType": 1, "trackIndex": 2,
             "recordFrame": t0 + round(at * fps)}
        ])
        if res:
            timeline.AddMarker(round(at * fps), "Cream",
                               f"OV {ov['source']}", ov.get("note", "")[:180], 1)
            ok += 1
        else:
            skipped.append(f"{ov['at_label']}+{ov.get('offset', 0)}: append failed")

    print(f"timeline: {name} @ {fps:g} fps")
    print(f"base {len(clip_infos)} cuts ({total_len / 60:.1f} min), overlays {ok}/{len(overlays)}")
    for s in skipped:
        print(f"  skipped: {s}")
    client.save()
    print("saved.")


if __name__ == "__main__":
    main(*sys.argv[1:])
