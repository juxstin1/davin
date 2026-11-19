"""Build 'MA129 episode assembly v4': cutlist.json base cut (V1/A1) + video-only
overlays on V2 + section/overlay markers, then voice isolation 35% on A1 and
auto-captions (the v3 recipe). v4 = v3 + Act 1 shop (Day 7) + the D6
treble-clef callback.

    uv run python productions/ma129/episode/validate_cutlist.py
    uv run python productions/ma129/episode/build_episode_v4.py --check            # preflight only
    uv run python productions/ma129/episode/build_episode_v4.py                    # full v4
    uv run python productions/ma129/episode/build_episode_v4.py --act1-pending     # everything but Day 7

Reels resolve from the Nov-2026 drop, then `Making Arrangements (rebuilt
reels)` (productions/rebuild_reel.py), then the July paths. Each must match
its manifest duration (+/-0.1s); the cut times are frame math on these reels.

Stand-ins used only while the real D5 clip reel is unavailable (Drive has no
D5 A-01 proxy):
  * D5 time >= A-01's end -> the reel rebuilt from A-02 on, at t - 913.246s.
  * D5 cuts inside A-01  -> the v1 base-cut render (no overlays / no voice
    iso), at frames verified against the v1 EDL (v1_render_map.json).
--act1-pending drops the Day 7 sections/overlays and leaves a marker.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

EP = Path(__file__).resolve().parent
PROJECT = "DASH-MA129"
DROP = Path(r"C:\Users\juxxs\Downloads\Making Arrangements")
REBUILT = Path(r"C:\Users\juxxs\Downloads\Making Arrangements (rebuilt reels)")
JULY_D5 = Path(r"C:\Users\juxxs\Downloads\MA129-Music Therapy-20260723T214044Z-1-001\MA129-Music Therapy")
JULY_D6 = Path(r"C:\Users\juxxs\Downloads\drive-download-20260723T211350Z-1-001")
D5_FOLDER = DROP / "Day 05" / "MA129-Music Therapy"
A01_END = 913.246  # D5 A-01 duration (manifest row 1)

# key -> (drop folder, reel kind, July fallback file)
SOURCES = {
    "d5clip": (D5_FOLDER, "CLIP", JULY_D5 / "MA129-Music Therapy_CLIP_REEL.mp4"),
    "d5broll": (D5_FOLDER, "BROLL", JULY_D5 / "MA129-Music Therapy_BROLL_REEL.mp4"),
    "d6clip": (DROP / "Day 06" / "MA129", "CLIP", JULY_D6 / "MA129_CLIP_REEL.mp4"),
    "d6broll": (DROP / "Day 06" / "MA129", "BROLL", JULY_D6 / "MA129_BROLL_REEL.mp4"),
    "d7clip": (DROP / "Day 07" / "MA129", "CLIP", None),
    "d7broll": (DROP / "Day 07" / "MA129", "BROLL", None),
    "estbroll": (DROP / "Day 07" / "Establishing Shots", "BROLL", None),
}
DAY_SOURCE = {5: "d5clip", 6: "d6clip", 7: "d7clip"}


def manifest_rows(folder: Path, kind: str) -> list[dict]:
    path = folder / f"{kind}_REEL_manifest.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def probe_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def check_len(path: Path, want: float | None) -> str | None:
    if want is None:
        return None
    got = probe_seconds(path)
    return None if abs(got - want) <= 0.1 else f"{path.name} is {got:.3f}s, manifest says {want:.3f}s"


def find_reel(key: str) -> tuple[Path | None, str | None]:
    folder, kind, fallback = SOURCES[key]
    rebuilt = REBUILT / folder.relative_to(DROP)
    hits = [h for d in (folder, rebuilt) if d.exists() for h in sorted(d.glob(f"*{kind}_REEL.mp4"))]
    path = hits[0] if hits else (fallback if fallback and fallback.exists() else None)
    if path is None:
        return None, None
    rows = manifest_rows(folder, kind)
    return path, check_len(path, sum(float(r["duration_seconds"]) for r in rows) if rows else None)


def d5_standins() -> tuple[dict, list[str]]:
    """Paths for the d5rest + v1render stand-ins, or problems."""
    found, problems = {}, []
    rest = REBUILT / "Day 05" / "MA129-Music Therapy" / "MA129-Music Therapy_CLIP_REEL_from-A-02.mp4"
    if rest.exists():
        rows = manifest_rows(D5_FOLDER, "CLIP")[1:]
        err = check_len(rest, sum(float(r["duration_seconds"]) for r in rows))
        (problems.append(f"d5rest: {err}") if err else found.__setitem__("d5rest", rest))
    else:
        problems.append(f"d5rest: MISSING {rest}")
    vmap = json.loads((EP / "v1_render_map.json").read_text(encoding="utf-8"))
    render = Path(vmap["render"])
    if render.exists() and all(s["edl_match"] for s in vmap["segments"]):
        found["v1render"] = render
    else:
        problems.append(f"v1render: MISSING or unverified {render}")
    return found, problems


def main():
    check_only = "--check" in sys.argv
    act1_pending = "--act1-pending" in sys.argv
    timeline_name = "MA129 episode assembly v4" + (" - act1 pending" if act1_pending else "")
    cutlist = json.loads((EP / "cutlist.json").read_text(encoding="utf-8"))
    overlays = json.loads((EP / "overlays.json").read_text(encoding="utf-8"))["overlays"]
    v1map = {(s["label"], s["start"], s["end"]): (s["render_in_f"], s["render_out_f"])
             for s in json.loads((EP / "v1_render_map.json").read_text(encoding="utf-8"))["segments"]}

    sections = cutlist["sections"]
    if act1_pending:
        act1_labels = {s["label"] for sec in sections if sec["name"] == "act1" for s in sec["segments"]}
        sections = [sec for sec in sections if sec["name"] != "act1"]
        overlays = [ov for ov in overlays if ov["at_label"] not in act1_labels]
    segs = [(sec, seg) for sec in sections for seg in sec["segments"]]
    needed = {seg.get("source") or DAY_SOURCE[seg["day"]] for _, seg in segs} | {ov["source"] for ov in overlays}

    paths, problems = {}, []
    for key in sorted(needed):
        path, err = find_reel(key)
        if path and not err:
            paths[key] = path
        elif key == "d5clip":
            extra, probs = d5_standins()
            paths.update(extra)
            problems += probs
            if not probs:
                print("  note: real D5 clip reel unavailable - using d5rest + v1render stand-ins")
        else:
            problems.append(f"{key}: {err or 'MISSING reel in ' + str(SOURCES[key][0])}")
    for key, path in sorted(paths.items()):
        print(f"  ok  {key:<9} {path}")
    if problems:
        print(f"\n{len(problems)} source problem(s) - not building:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(2)

    def place(key: str, start: float, end: float, fps: float, label: str | None = None):
        """-> (source key, start frame, end frame), routing D5 through stand-ins."""
        if key == "d5clip" and "d5clip" not in paths:
            if end <= A01_END + 1e-6:
                rng = v1map.get((label, start, end))
                if rng is None:
                    raise SystemExit(f"D5 A-01 range {label} {start}-{end} not in v1_render_map.json")
                return "v1render", rng[0], rng[1]
            if start < A01_END:
                raise SystemExit(f"D5 range {start}-{end} straddles the A-01 boundary")
            start, end, key = start - A01_END, end - A01_END, "d5rest"
        a = max(0, round(start * fps))
        return key, a, max(a + 1, round(end * fps))

    if check_only:
        fps = 30000 / 1001
        for _, seg in segs:  # dry-run every placement
            place(seg.get("source") or DAY_SOURCE[seg["day"]], seg["start"], seg["end"], fps, seg["label"])
        for ov in overlays:
            place(ov["source"], ov["srcStart"], ov["srcEnd"], fps)
        print(f"\npreflight clean: {timeline_name}, {len(segs)} cuts, {len(overlays)} overlays.")
        return

    from davin.client import DavinClient, timeline_fps

    client = DavinClient.connect()
    client.ensure_project(PROJECT)
    items = {key: client.import_media([p], bin_path="reels v4")[0] for key, p in paths.items()}
    fps = float(items["d6clip"].GetClipProperty("FPS"))

    clip_infos, flat, seg_at, cursor = [], [], {}, 0.0
    for section, seg in segs:
        src, a, b = place(seg.get("source") or DAY_SOURCE[seg["day"]], seg["start"], seg["end"], fps, seg["label"])
        clip_infos.append({"mediaPoolItem": items[src], "startFrame": a, "endFrame": b})
        n = sum(1 for k in seg_at if k[0] == seg["label"]) + 1
        seg_at[(seg["label"], n)] = cursor
        flat.append((section, seg, src))
        cursor += (b - a) / fps

    timeline = client.create_timeline(timeline_name, clip_infos, fps=fps)
    name = timeline.GetName()
    fps = timeline_fps(timeline)
    t0 = timeline.GetStartFrame()

    placed = timeline.GetItemListInTrack("video", 1) or []
    if len(placed) != len(flat):
        print(f"WARNING: {len(placed)} base items vs {len(flat)} segments")
    for item, (section, seg, src) in zip(placed, flat):
        tag = " [v1-render stand-in]" if src == "v1render" else ""
        note = f"D{seg['day']} {seg['label']}{tag}: {seg.get('note', '')}"[:180]
        timeline.AddMarker(item.GetStart() - t0, section.get("color", "Blue"), seg["label"], note, 1)
    if act1_pending:
        cold = sum(s["end"] - s["start"] for s in cutlist["sections"][0]["segments"])
        timeline.AddMarker(round(cold * fps), "Mint", "ACT 1 SHOP GOES HERE",
                           "Day 7 shop act (episode/act1.json, 4:10, 12 cuts) - its clip footage is not delivered yet", 1)

    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")
    ok, skipped = 0, []
    for ov in overlays:
        key = (ov["at_label"], ov.get("occurrence", 1))
        if key not in seg_at:
            skipped.append(f"{ov['at_label']}: no such base segment")
            continue
        at = seg_at[key] + ov.get("offset", 0.0)
        length = min(ov["srcEnd"] - ov["srcStart"], max(1.0, cursor - at - 0.1))
        src, a, b = place(ov["source"], ov["srcStart"], ov["srcStart"] + length, fps)
        res = client.media_pool.AppendToTimeline([{
            "mediaPoolItem": items[src], "startFrame": a, "endFrame": b,
            "mediaType": 1, "trackIndex": 2, "recordFrame": t0 + round(at * fps),
        }])
        if res:
            timeline.AddMarker(round(at * fps), "Cream", f"OV {ov['source']}", ov.get("note", "")[:180], 1)
            ok += 1
        else:
            skipped.append(f"{ov['at_label']}+{ov.get('offset', 0)}: append failed")

    print(f"timeline: {name} @ {fps:g} fps")
    print(f"base {len(clip_infos)} cuts ({int(cursor // 60)}:{cursor % 60:04.1f}), overlays {ok}/{len(overlays)}")
    for s in skipped:
        print(f"  skipped: {s}")
    try:
        print("voice isolation:", client.set_voice_isolation(1, 35, timeline_name=name))
    except Exception as exc:  # noqa: BLE001 - finish the build, report the gap
        print(f"voice isolation FAILED: {exc}")
    try:
        print(f"captions: {client.auto_caption(client.get_timeline(name))}")
    except Exception as exc:  # noqa: BLE001
        print(f"auto-captions FAILED: {exc}")
    client.save()
    print("saved.")


if __name__ == "__main__":
    main()
