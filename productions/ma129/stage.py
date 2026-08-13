"""Stage DASH-DAY06-MA129 in Resolve: reels imported, timelines built,
source-clip boundaries marked, transcript converted to davin captions JSON."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from davin.client import DavinClient

SRC = Path(r"C:\Users\juxxs\Downloads\drive-download-20260723T211350Z-1-001")
WORK = Path(r"C:\Users\juxxs\Desktop\davin\ma129")
PROJECT = "DASH-DAY06-MA129"

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


def add_boundary_markers(client, timeline_name: str, rows: list[dict]):
    at = 0.0
    added = 0
    for row in rows:
        name = row["filename"]
        short = name.split("-CAM ")[-1]  # e.g. "A-01"
        color = "Cyan" if short.startswith("B") else "Blue"
        if client.add_marker(at, color, short, name, timeline_name=timeline_name):
            added += 1
        at += float(row["duration_seconds"])
    return added


def main():
    captions, sections = parse_transcript(SRC / "CLIP_REEL_transcript.txt")
    clip_rows = read_manifest(SRC / "CLIP_REEL_manifest.tsv")
    broll_rows = read_manifest(SRC / "BROLL_REEL_manifest.tsv")

    # cross-check: manifest cumulative starts must match transcript reel_starts
    at, drift = 0.0, 0.0
    for row, sec in zip(clip_rows, sections):
        assert row["filename"] == sec["name"], (row["filename"], sec["name"])
        drift = max(drift, abs(at - sec["start"]))
        at += float(row["duration_seconds"])
    print(f"boundary cross-check: {len(sections)} sections, max drift {drift * 1000:.1f}ms")

    out = WORK / "MA129_CLIP_REEL.captions.json"
    out.write_text(
        json.dumps({"captions": captions}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{len(captions)} captions -> {out}")

    client = DavinClient.connect()
    client.ensure_project(PROJECT)
    [clip_reel] = client.import_media([SRC / "MA129_CLIP_REEL.mp4"], bin_path="reels")
    [broll_reel] = client.import_media([SRC / "MA129_BROLL_REEL.mp4"], bin_path="reels")
    print(f"imported: {clip_reel.GetName()}, {broll_reel.GetName()}")

    fps = float(clip_reel.GetClipProperty("FPS"))
    existing = {
        client.project.GetTimelineByIndex(i).GetName()
        for i in range(1, client.project.GetTimelineCount() + 1)
    }
    for tl_name, item, rows in (
        ("MA129 clip reel", clip_reel, clip_rows),
        ("MA129 broll reel", broll_reel, broll_rows),
    ):
        if tl_name in existing:
            print(f"timeline exists, skipping: {tl_name}")
            continue
        timeline = client.create_timeline(tl_name, [item], fps=fps)
        added = add_boundary_markers(client, timeline.GetName(), rows)
        print(f"timeline: {timeline.GetName()} @ {fps:g} fps, {added}/{len(rows)} markers")

    client.get_timeline("MA129 clip reel")
    client.save()
    print("saved.")


if __name__ == "__main__":
    main()
