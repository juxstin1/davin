"""davin CLI - drive DaVinci Resolve from the terminal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from davin import workspace
from davin.bootstrap import ResolveConnectionError
from davin.client import ORGANIZE_PROPS, PAGES, DavinClient, DavinError
from davin.ranges import captions_to_ranges, load_captions, load_ranges, save_ranges


def _client(args) -> DavinClient:
    client = DavinClient.connect()
    if getattr(args, "project", None):
        client.ensure_project(args.project)
    return client


def cmd_status(args):
    print(json.dumps(_client(args).status(), indent=2))


def cmd_inspect(args):
    snap = workspace.snapshot(_client(args), verbose=args.verbose)
    if args.json or args.verbose:
        print(json.dumps(snap, indent=2))
    else:
        print(workspace.render_text(snap))


def cmd_projects(args):
    for name in _client(args).list_projects():
        print(name)


def cmd_project(args):
    client = DavinClient.connect()
    if args.action == "open":
        client.open_project(args.name)
    else:
        client.create_project(args.name)
    print(f"{args.action}: {args.name}")


def cmd_import(args):
    items = _client(args).import_media(args.files, bin_path=args.bin)
    for item in items:
        print(f"imported: {item.GetName()}")


def cmd_conform(args):
    timeline = _client(args).import_timeline(args.path, args.name, args.media)
    print(f"conformed: {timeline.GetName()}")


def cmd_cutplan(args):
    captions = load_captions(args.captions)
    ranges, dropped = captions_to_ranges(
        captions,
        drop=set(args.drop or []),
        drop_matching=args.drop_matching,
        join_gap=args.join_gap,
        pad=args.pad,
    )
    for cap in dropped:
        print(f"drop {cap['index']:>3}  {cap['start']:7.2f}-{cap['end']:7.2f}  {cap['text']}")
    if not ranges:
        print("cutplan: nothing kept", file=sys.stderr)
        sys.exit(1)
    kept_s = sum(e - s for s, e in ranges)
    save_ranges(ranges, args.out)
    print(
        f"kept {len(captions) - len(dropped)}/{len(captions)} captions -> "
        f"{len(ranges)} range(s), {kept_s:.2f}s -> {args.out}"
    )


def cmd_timeline(args):
    client = _client(args)
    clips = client.import_media(args.clips) if args.clips else None
    timeline = client.create_timeline(args.name, clips)
    print(f"timeline: {timeline.GetName()}")


def cmd_papercut(args):
    client = _client(args)
    ranges = load_ranges(args.ranges)
    timeline, fps = client.papercut(args.source, ranges, args.name, args.fps)
    kept = sum(e - s for s, e in ranges)
    print(
        f"timeline: {timeline.GetName()}  ({len(ranges)} cuts, "
        f"{kept:.2f}s kept @ {fps:g} fps)"
    )


def cmd_transcribe(args):
    client = _client(args)
    name = client.transcribe(args.clip, speakers=args.speakers or None)
    print(f"transcribed: {name}")


def cmd_transcript(args):
    client = _client(args)
    captions = client.extract_transcript(
        args.source, language=args.lang, keep_timeline=args.keep_timeline
    )
    payload = json.dumps({"captions": captions}, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"{len(captions)} captions -> {args.out}")
    else:
        print(payload)


def cmd_subtitles(args):
    client = _client(args)
    timeline = client.get_timeline(args.timeline)
    count = client.auto_caption(
        timeline,
        language=args.lang,
        chars_per_line=args.chars,
        preset=args.preset,
    )
    print(f"subtitles: {count} captions on {timeline.GetName()}")


def cmd_scenecut(args):
    client = _client(args)
    ok = client.detect_scene_cuts(args.timeline)
    print("scene cuts: done" if ok else "scene cuts: nothing detected / failed")


def cmd_bin(args):
    folder = _client(args).ensure_bin(args.path)
    print(f"bin: {folder.GetName()}")


def cmd_move(args):
    count = _client(args).move_clips(args.clips, args.bin)
    print(f"moved {count} clip(s) -> {args.bin}")


def cmd_organize(args):
    moved = _client(args).organize_by(args.by)
    for bin_name, count in moved.items():
        print(f"{bin_name}: {count} clip(s)")
    if not moved:
        print("nothing to organize (no loose clips at root)")


def cmd_markers(args):
    client = _client(args)
    if args.add is not None:
        ok = client.add_marker(
            args.add,
            args.color,
            args.name or "",
            args.note or "",
            timeline_name=args.timeline,
        )
        if not ok:
            raise DavinError("AddMarker failed (frame out of range or occupied?)")
        print(f"marker @ {args.add}s ({args.color})")
    else:
        markers = client.list_markers(timeline_name=args.timeline)
        from davin.client import timeline_fps

        fps = timeline_fps(client.get_timeline(args.timeline))
        for frame in sorted(markers):
            m = markers[frame]
            print(f"{frame / fps:8.2f}s  {m['color']:<8} {m['name']} {m['note']}")
        if not markers:
            print("no markers")


def cmd_export(args):
    path = _client(args).export_timeline(args.path, args.type, args.timeline)
    print(f"exported: {path}")


def cmd_quickexport(args):
    client = _client(args)
    if not args.preset:
        for preset in client.quick_export_presets():
            print(preset)
        return
    status = client.quick_export(
        args.preset, args.out, args.name, timeline_name=args.timeline
    )
    print(json.dumps(status, indent=2))


def cmd_seek(args):
    ref = args.position
    if ":" in ref:
        tc = _client(args).seek(timecode=ref, timeline_name=args.timeline)
    else:
        tc = _client(args).seek(seconds=float(ref), timeline_name=args.timeline)
    print(f"playhead: {tc}")


def cmd_still(args):
    path = _client(args).export_still(
        args.path, at_seconds=args.at, timeline_name=args.timeline
    )
    print(f"still: {path}")


def cmd_stills(args):
    paths = _client(args).contact_sheet(
        args.out, middle=not args.first, timeline_name=args.timeline
    )
    print(f"{len(paths)} stills -> {args.out}")


def cmd_tag(args):
    name = _client(args).tag_clip(args.clip, args.color, args.flag, args.clear)
    print(f"tagged: {name}")


def cmd_voiceiso(args):
    state = _client(args).set_voice_isolation(
        track=args.track,
        amount=args.amount,
        enabled=not args.off,
        timeline_name=args.timeline,
    )
    print(f"voice isolation: {state}")


def cmd_stabilize(args):
    ok = _client(args).stabilize(
        args.clip, track=args.track, timeline_name=args.timeline
    )
    print("stabilized" if ok else "stabilize failed")


def cmd_dup(args):
    timeline = _client(args).duplicate_timeline(args.name, args.timeline)
    print(f"duplicated: {timeline.GetName()}")


def cmd_title(args):
    name, text_set = _client(args).insert_title(
        args.text, title_name=args.style, at_seconds=args.at, timeline_name=args.timeline
    )
    note = "" if text_set or not args.text else " (text not set - edit in Fusion)"
    print(f"title: {name}{note}")


def cmd_save(args):
    ok = _client(args).save()
    print("saved" if ok else "save failed")


def cmd_presets(args):
    for preset in _client(args).render_presets():
        print(preset)


def cmd_render(args):
    client = _client(args)
    status = client.render(
        args.out,
        custom_name=args.name,
        preset=args.preset,
        fmt=args.format,
        codec=args.codec,
        wait=not args.no_wait,
        on_progress=lambda pct: print(f"\r  rendering {pct}%", end="", flush=True),
        timeline_name=args.timeline,
    )
    print()
    print(json.dumps(status, indent=2))
    if status.get("JobStatus") not in ("Complete", "Started"):
        sys.exit(1)


def cmd_page(args):
    _client(args).open_page(args.name)
    print(f"page: {args.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="davin", description="Drive DaVinci Resolve Studio from the terminal."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        p.add_argument("--project", help="open-or-create this project first")
        return p

    add("status", cmd_status, "connection + current project/timeline")

    p = add("inspect", cmd_inspect, "snapshot the workspace (bins, clips, timelines)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--verbose", action="store_true", help="all clip properties (JSON)")

    add("projects", cmd_projects, "list projects in the current folder")

    p = add("project", cmd_project, "open or create a project")
    p.add_argument("action", choices=["open", "create"])
    p.add_argument("name")

    p = add("import", cmd_import, "import media files into the pool")
    p.add_argument("files", nargs="+")
    p.add_argument("--bin", help="import into this bin (default: root)")

    p = add("conform", cmd_conform, "import a timeline file (otio/aaf/edl/xml/drt)")
    p.add_argument("path", help="timeline file")
    p.add_argument("--name", help="timeline name")
    p.add_argument("--media", help="folder to search for source clips")

    p = add("cutplan", cmd_cutplan, "captions JSON -> kept-ranges JSON")
    p.add_argument("captions", help="output of `davin transcript`")
    p.add_argument("--out", required=True, help="kept-ranges JSON to write")
    p.add_argument("--drop", type=int, nargs="+", metavar="N", help="1-based caption indices")
    p.add_argument("--drop-matching", metavar="REGEX", help="drop captions matching this")
    p.add_argument("--join-gap", type=float, default=0.5, help="merge gaps <= seconds")
    p.add_argument("--pad", type=float, default=0.0, help="widen ranges by seconds")

    p = add("timeline", cmd_timeline, "create a timeline, optionally from clips")
    p.add_argument("name")
    p.add_argument("--clips", nargs="+", help="media files to append in order")

    p = add("papercut", cmd_papercut, "cut a timeline from a kept-ranges JSON")
    p.add_argument("source", help="source video file")
    p.add_argument("ranges", help="JSON: [[s,e],...] or [{start,end},...] seconds")
    p.add_argument("--name", help="timeline name")
    p.add_argument("--fps", type=float, help="override source fps")

    p = add("transcribe", cmd_transcribe, "run Resolve AI transcription on a clip")
    p.add_argument("clip", help="clip name or file path")
    p.add_argument("--speakers", action="store_true", help="use speaker detection")

    p = add("transcript", cmd_transcript, "extract transcript JSON for a media file")
    p.add_argument("source", help="media file")
    p.add_argument("--out", help="write JSON here instead of stdout")
    p.add_argument("--lang", help="caption language, e.g. english")
    p.add_argument("--keep-timeline", action="store_true")

    p = add("subtitles", cmd_subtitles, "auto-caption a timeline (built-in AI)")
    p.add_argument("--timeline", help="timeline name (default: current)")
    p.add_argument("--lang", help="e.g. english, german, japanese")
    p.add_argument("--chars", type=int, help="max chars per line")
    p.add_argument("--preset", help="subtitle_default | teletext | netflix")

    p = add("scenecut", cmd_scenecut, "detect + apply scene cuts on a timeline")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("bin", cmd_bin, "create a media pool bin (slash path ok)")
    p.add_argument("path", help="e.g. b-roll/day1")

    p = add("move", cmd_move, "move clips into a bin")
    p.add_argument("clips", nargs="+", help="clip names or paths")
    p.add_argument("--bin", required=True, help="target bin path")

    p = add("organize", cmd_organize, "bin loose root clips by a property")
    p.add_argument("--by", required=True, choices=sorted(ORGANIZE_PROPS))

    p = add("markers", cmd_markers, "list or add timeline markers")
    p.add_argument("--add", type=float, metavar="SECONDS")
    p.add_argument("--color", default="Blue")
    p.add_argument("--name")
    p.add_argument("--note")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("export", cmd_export, "export timeline (otio/edl/fcpxml/csv/drt/aaf)")
    p.add_argument("path", help="output file; type inferred from extension")
    p.add_argument("--type", choices=sorted(DavinClient.EXPORT_TYPES))
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("quickexport", cmd_quickexport, "render via Quick Export preset")
    p.add_argument("preset", nargs="?", help="omit to list presets")
    p.add_argument("--out", default="out", help="output directory")
    p.add_argument("--name", help="output file name")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("seek", cmd_seek, "move the playhead (seconds or timecode)")
    p.add_argument("position", help="e.g. 12.5 or 01:00:03:12")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("still", cmd_still, "export current/at frame as an image")
    p.add_argument("path", help="output image (png/jpg/...)")
    p.add_argument("--at", type=float, metavar="SECONDS")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("stills", cmd_stills, "contact sheet: one still per timeline clip")
    p.add_argument("out", help="output directory")
    p.add_argument("--first", action="store_true", help="first frame, not middle")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("tag", cmd_tag, "set clip color / flag in the media pool")
    p.add_argument("clip", help="clip name or path")
    p.add_argument("--color", help="e.g. Orange, Teal, Violet")
    p.add_argument("--flag", help="e.g. Red, Green, Blue")
    p.add_argument("--clear", action="store_true", help="clear color+flags first")

    p = add("voiceiso", cmd_voiceiso, "AI voice isolation on an audio track")
    p.add_argument("--track", type=int, default=1)
    p.add_argument("--amount", type=int, default=50, help="0-100")
    p.add_argument("--off", action="store_true")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("stabilize", cmd_stabilize, "stabilize a clip on the timeline")
    p.add_argument("clip", type=int, help="clip index on the track (1-based)")
    p.add_argument("--track", type=int, default=1)
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("dup", cmd_dup, "duplicate a timeline (version before risky edits)")
    p.add_argument("--name", help="name for the copy")
    p.add_argument("--timeline", help="timeline to copy (default: current)")

    p = add("title", cmd_title, "insert a title at the playhead")
    p.add_argument("text", nargs="?", help="title text (Text+ only)")
    p.add_argument("--style", default="Text+", help="title generator name")
    p.add_argument("--at", type=float, metavar="SECONDS")
    p.add_argument("--timeline", help="timeline name (default: current)")

    add("save", cmd_save, "save the current project")

    add("presets", cmd_presets, "list render presets")

    p = add("render", cmd_render, "render a timeline")
    p.add_argument("out", help="output directory")
    p.add_argument("--name", help="output file name (without extension)")
    p.add_argument("--preset", help="render preset, e.g. 'H.264 Master'")
    p.add_argument("--format", help="container, e.g. mp4/mov")
    p.add_argument("--codec", help="codec, e.g. H264")
    p.add_argument("--no-wait", action="store_true", help="queue and return")
    p.add_argument("--timeline", help="timeline name (default: current)")

    p = add("page", cmd_page, "switch UI page")
    p.add_argument("name", choices=list(PAGES))

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except (ResolveConnectionError, DavinError, ValueError) as exc:
        print(f"davin: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
