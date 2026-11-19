"""Stage one story-day folder of a DASH review drop into Resolve.

    uv run python productions/stage_drop.py "<drop>/Day 07/MA129" \
        --project DASH-MA129 --label "MA129 D7" --work productions/ma129/day07

Idempotent and safe to rerun when missing reels arrive: checks run on whatever
is present, existing timelines are skipped, absent reels are reported.

Checks (no video needed for the first): manifest cumulative durations vs the
transcript's per-clip reel_start headers (expect 0ms drift); sum of manifest
rows vs ffprobe reel duration; per-stream video/audio duration + start_time.
Per-segment A/V offsets baked into concat reels do NOT show in stream
metadata, so for the clip reel it also cuts two raw re-encoded snippets
(near start, mid-reel) for a human to play outside Resolve.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

CAPTION_RE = re.compile(
    r"\[(\d+):(\d+):(\d+)\.(\d+) --> (\d+):(\d+):(\d+)\.(\d+)\]\s*(.*)"
)


def tc_to_s(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_transcript(path: Path):
    captions, sections, current = [], [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DASH-"):
            current = line.strip()
        elif line.startswith("reel_start:") and current:
            h, m, s = line.split(":", 1)[1].strip().split(":")
            sec, ms = s.split(".")
            sections.append({"name": current, "start": tc_to_s(h, m, sec, ms)})
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


def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def ffprobe_streams(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,duration,start_time", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def check_reel(reel: Path, rows: list[dict], kind: str) -> float:
    info = ffprobe_streams(reel)
    dur = float(info["format"]["duration"])
    manifest = sum(float(r["duration_seconds"]) for r in rows)
    print(f"[{kind}] reel {dur:.3f}s vs manifest sum {manifest:.3f}s "
          f"(diff {(dur - manifest) * 1000:+.0f}ms)")
    for st in info.get("streams", []):
        print(f"[{kind}]   {st.get('codec_type'):5s} duration {st.get('duration')} "
              f"start_time {st.get('start_time')}")
    return dur


def sync_snippets(reel: Path, dur: float, out_dir: Path, label: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = label.lower().replace(" ", "-")
    for tag, at in (("start", 5.0), ("mid", dur / 2)):
        dst = out_dir / f"sync-check-{slug}-{tag}.mp4"
        if dst.exists():
            continue
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(reel), "-t", "12",
             "-c:v", "libx264", "-c:a", "aac", str(dst)],
            check=True,
        )
        print(f"sync snippet ({tag} @ {at:.1f}s) -> {dst}")


def find_reel(folder: Path, kind: str) -> Path | None:
    hits = sorted(folder.glob(f"*{kind}_REEL.mp4"))
    return hits[0] if hits else None


def boundary_markers(client, timeline_name: str, rows: list[dict]) -> int:
    at, added = 0.0, 0
    for row in rows:
        short = row["filename"].split("-CAM ")[-1]  # "A-01"
        color = "Cyan" if short.startswith("B") else "Blue"
        if client.add_marker(at, color, short, row["filename"], timeline_name=timeline_name):
            added += 1
        at += float(row["duration_seconds"])
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="story-day folder (has *_manifest.tsv)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--label", required=True, help='timeline prefix, e.g. "MA129 D7"')
    ap.add_argument("--work", type=Path, required=True, help="output dir for captions/notes")
    ap.add_argument("--bin", default=None, help="media pool bin (default: label day)")
    ap.add_argument("--no-resolve", action="store_true", help="checks + captions only")
    args = ap.parse_args()

    folder, work = args.folder, args.work
    work.mkdir(parents=True, exist_ok=True)
    clip_rows = read_manifest(folder / "CLIP_REEL_manifest.tsv")
    broll_rows = read_manifest(folder / "BROLL_REEL_manifest.tsv")
    clip_reel, broll_reel = find_reel(folder, "CLIP"), find_reel(folder, "BROLL")

    if clip_rows:
        captions, sections = parse_transcript(folder / "CLIP_REEL_transcript.txt")
        assert len(sections) == len(clip_rows), (len(sections), len(clip_rows))
        at, drift = 0.0, 0.0
        for row, sec in zip(clip_rows, sections):
            assert row["filename"] == sec["name"], (row["filename"], sec["name"])
            drift = max(drift, abs(at - sec["start"]))
            at += float(row["duration_seconds"])
        print(f"boundary cross-check: {len(sections)} sections, max drift {drift * 1000:.1f}ms")
        if drift > 0.001:
            raise SystemExit("manifest/transcript drift - investigate before cutting")
        slug = args.label.replace(" ", "_")
        out = work / f"{slug}_CLIP_REEL.captions.json"
        out.write_text(json.dumps({"captions": captions}, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        print(f"{len(captions)} captions -> {out}")

    reels = []
    for kind, reel, rows in (("CLIP", clip_reel, clip_rows), ("BROLL", broll_reel, broll_rows)):
        if not rows:
            continue
        if reel is None:
            print(f"[{kind}] MISSING reel video in {folder} ({len(rows)} manifest rows)")
            continue
        dur = check_reel(reel, rows, kind)
        if kind == "CLIP":
            sync_snippets(reel, dur, work / "out", args.label)
        reels.append((kind, reel, rows))

    if args.no_resolve or not reels:
        return

    from davin.client import DavinClient

    client = DavinClient.connect()
    client.ensure_project(args.project)
    bin_path = args.bin or args.label.split()[-1].lower()  # "MA129 D7" -> "d7"
    existing = {
        client.project.GetTimelineByIndex(i).GetName()
        for i in range(1, client.project.GetTimelineCount() + 1)
    }
    first = None
    for kind, reel, rows in reels:
        tl_name = f"{args.label} {kind.lower()} reel"
        first = first or tl_name
        if tl_name in existing:
            print(f"timeline exists, skipping: {tl_name}")
            continue
        [item] = client.import_media([reel], bin_path=bin_path)
        fps = float(item.GetClipProperty("FPS"))
        timeline = client.create_timeline(tl_name, [item], fps=fps)
        added = boundary_markers(client, timeline.GetName(), rows)
        print(f"timeline: {timeline.GetName()} @ {fps:g} fps, {added}/{len(rows)} markers")
    client.get_timeline(first)
    client.save()
    print("saved.")


if __name__ == "__main__":
    main()
