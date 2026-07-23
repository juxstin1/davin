"""Stage the Day 5 drop (Act 1/2) into the unified DASH-MA129 project."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from davin.client import DavinClient

SRC = Path(
    r"C:\Users\juxxs\Downloads\MA129-Music Therapy-20260723T214044Z-1-001"
    r"\MA129-Music Therapy"
)
WORK = Path(r"C:\Users\juxxs\Desktop\davin\ma129\day05")
CLIP_REEL = SRC / "MA129-Music Therapy_CLIP_REEL.mp4"
BROLL_REEL = SRC / "MA129-Music Therapy_BROLL_REEL.mp4"
OLD_PROJECT, PROJECT = "DASH-DAY06-MA129", "DASH-MA129"

CAPTION_RE = re.compile(
    r"\[(\d+):(\d+):(\d+)\.(\d+) --> (\d+):(\d+):(\d+)\.(\d+)\]\s*(.*)"
)


def tc_to_s(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_transcript(path: Path):
    captions, sections = [], []
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DASH-"):
            current = line.strip()
        elif line.startswith("reel_start:") and current:
            h, m, s = line.split(":", 1)[1].strip().split(":")
            sections.append(
                {"name": current, "start": tc_to_s(h, m, s.split(".")[0], s.split(".")[1])}
            )
            current = None
        else:
            match = CAPTION_RE.match(line.strip())
            if match and match.group(9).strip():
                g = match.groups()
                captions.append(
                    {
                        "start": round(tc_to_s(*g[0:4]), 3),
                        "end": round(tc_to_s(*g[4:8]), 3),
                        "text": g[8].strip(),
                    }
                )
    return captions, sections


def read_manifest(path: Path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def add_boundary_markers(client, timeline_name, rows):
    at, added = 0.0, 0
    for row in rows:
        short = row["filename"].split("-CAM ")[-1]
        color = "Cyan" if short.startswith("B") else "Blue"
        if client.add_marker(at, color, short, row["filename"], timeline_name=timeline_name):
            added += 1
        at += float(row["duration_seconds"])
    return added


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    captions, sections = parse_transcript(SRC / "CLIP_REEL_transcript.txt")
    clip_rows = read_manifest(SRC / "CLIP_REEL_manifest.tsv")
    broll_rows = read_manifest(SRC / "BROLL_REEL_manifest.tsv")

    at, drift = 0.0, 0.0
    for row, sec in zip(clip_rows, sections):
        assert row["filename"] == sec["name"], (row["filename"], sec["name"])
        drift = max(drift, abs(at - sec["start"]))
        at += float(row["duration_seconds"])
    print(f"boundary cross-check: {len(sections)} sections, max drift {drift * 1000:.1f}ms")

    out = WORK / "D5_CLIP_REEL.captions.json"
    out.write_text(
        json.dumps({"captions": captions}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{len(captions)} captions -> {out}")

    client = DavinClient.connect()
    # unify: one story, one project
    if OLD_PROJECT in client.pm.GetProjectListInCurrentFolder():
        client.open_project(OLD_PROJECT)
        if client.project.SetName(PROJECT):
            print(f"project renamed: {OLD_PROJECT} -> {PROJECT}")
    client.ensure_project(PROJECT)

    [clip_reel] = client.import_media([CLIP_REEL], bin_path="day05")
    [broll_reel] = client.import_media([BROLL_REEL], bin_path="day05")
    print(f"imported: {clip_reel.GetName()}, {broll_reel.GetName()}")

    fps = float(clip_reel.GetClipProperty("FPS"))
    existing = {
        client.project.GetTimelineByIndex(i).GetName()
        for i in range(1, client.project.GetTimelineCount() + 1)
    }
    for tl_name, item, rows in (
        ("MA129 D5 clip reel", clip_reel, clip_rows),
        ("MA129 D5 broll reel", broll_reel, broll_rows),
    ):
        if tl_name in existing:
            print(f"timeline exists, skipping: {tl_name}")
            continue
        timeline = client.create_timeline(tl_name, [item], fps=fps)
        added = add_boundary_markers(client, timeline.GetName(), rows)
        print(f"timeline: {timeline.GetName()} @ {fps:g} fps, {added}/{len(rows)} markers")

    client.get_timeline("MA129 D5 clip reel")
    client.save()
    print("saved.")


if __name__ == "__main__":
    main()
