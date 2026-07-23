"""davin MCP server - DaVinci Resolve as agent tools.

Perception (inspect, transcript, stills), memory (dup, save), and safe
writes (papercut, conform) over a running Resolve Studio instance.
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit("davin-mcp requires the mcp extra: uv sync --extra mcp") from exc

from davin import workspace
from davin.client import DavinClient
from davin.ranges import captions_to_ranges

mcp = FastMCP("davin")


def _client() -> DavinClient:
    return DavinClient.connect()


# -- perception ----------------------------------------------------------


@mcp.tool()
def status() -> dict:
    """Resolve connection info plus current project and timeline."""
    return _client().status()


@mcp.tool()
def inspect(verbose: bool = False) -> dict:
    """Snapshot the workspace: bins, clips with properties, timelines with tracks."""
    return workspace.snapshot(_client(), verbose=verbose)


@mcp.tool()
def transcript(source: str, language: str | None = None) -> list[dict]:
    """Transcribe a media file with Resolve's AI. Returns [{start, end, text}]
    in seconds (uses a scratch timeline that is deleted afterwards)."""
    return _client().extract_transcript(source, language=language)


@mcp.tool()
def stills(out_dir: str, timeline: str | None = None) -> list[str]:
    """Export one still image per clip of a timeline (its visual contact
    sheet). Returns the image file paths - read them to see the edit."""
    return _client().contact_sheet(out_dir, timeline_name=timeline)


@mcp.tool()
def still(path: str, at_seconds: float | None = None, timeline: str | None = None) -> str:
    """Export the frame at the playhead (or at_seconds) of a timeline."""
    return str(_client().export_still(path, at_seconds=at_seconds, timeline_name=timeline))


@mcp.tool()
def list_markers(timeline: str | None = None) -> dict:
    """Markers on a timeline as {frame: {color, name, note, ...}}."""
    return _client().list_markers(timeline_name=timeline)


# -- projects / versioning -------------------------------------------------


@mcp.tool()
def open_project(name: str) -> str:
    """Open a project by name, creating it if it does not exist."""
    client = _client()
    client.ensure_project(name)
    return name


@mcp.tool()
def duplicate_timeline(new_name: str | None = None, timeline: str | None = None) -> str:
    """Duplicate a timeline (do this before risky edits). Returns the copy's name."""
    return _client().duplicate_timeline(new_name, timeline).GetName()


@mcp.tool()
def save_project() -> bool:
    """Save the current project."""
    return _client().save()


# -- edit ------------------------------------------------------------------


@mcp.tool()
def build_ranges(
    captions: list[dict],
    drop_indices: list[int] | None = None,
    drop_matching: str | None = None,
    join_gap: float = 0.5,
    pad: float = 0.0,
) -> dict:
    """Turn captions [{start, end, text}] into kept ranges by dropping captions
    (1-based indices and/or a regex). Merges survivors closer than join_gap
    seconds. Returns {ranges: [[start, end]...], dropped: [...]}."""
    ranges, dropped = captions_to_ranges(
        captions,
        drop=set(drop_indices or []),
        drop_matching=drop_matching,
        join_gap=join_gap,
        pad=pad,
    )
    return {"ranges": [list(r) for r in ranges], "dropped": dropped}


@mcp.tool()
def papercut(
    source: str, ranges: list[list[float]], name: str | None = None
) -> str:
    """Build a timeline that keeps only the given [start, end) second ranges
    of a source media file. Returns the timeline name."""
    timeline, _ = _client().papercut(source, [(r[0], r[1]) for r in ranges], name)
    return timeline.GetName()


@mcp.tool()
def conform(path: str, name: str | None = None, media_dir: str | None = None) -> str:
    """Import a timeline file (OTIO/AAF/EDL/FCPXML/DRT) as a new timeline -
    the atomic write primitive. media_dir helps relink source clips."""
    return _client().import_timeline(path, name, media_dir).GetName()


@mcp.tool()
def export_timeline(path: str, kind: str | None = None, timeline: str | None = None) -> str:
    """Export a timeline to otio/edl/fcpxml/csv/drt/aaf (kind inferred from
    the file extension if omitted)."""
    return str(_client().export_timeline(path, kind, timeline))


@mcp.tool()
def subtitles(timeline: str | None = None, language: str | None = None) -> int:
    """Auto-caption a timeline with Resolve's AI. Returns the caption count."""
    client = _client()
    return client.auto_caption(client.get_timeline(timeline), language=language)


@mcp.tool()
def scenecut(timeline: str | None = None) -> bool:
    """Detect scene changes on a timeline and split its clips at each cut."""
    return _client().detect_scene_cuts(timeline)


@mcp.tool()
def add_marker(
    seconds: float,
    color: str = "Blue",
    name: str = "",
    note: str = "",
    timeline: str | None = None,
) -> bool:
    """Add a marker to a timeline at the given second."""
    return _client().add_marker(seconds, color, name, note, timeline_name=timeline)


# -- organize ----------------------------------------------------------------


@mcp.tool()
def import_media(files: list[str], bin_path: str | None = None) -> list[str]:
    """Import media files into the pool (optionally into a bin). Returns clip names."""
    return [i.GetName() for i in _client().import_media(files, bin_path=bin_path)]


@mcp.tool()
def organize(by: str) -> dict:
    """Move loose root clips into bins by property: resolution|fps|type|format|date."""
    return _client().organize_by(by)


@mcp.tool()
def move_clips(clips: list[str], bin_path: str) -> int:
    """Move clips (by name or path) into a bin; bins are created as needed."""
    return _client().move_clips(clips, bin_path)


@mcp.tool()
def tag_clip(clip: str, color: str | None = None, flag: str | None = None) -> str:
    """Set a media pool clip's color and/or add a flag."""
    return _client().tag_clip(clip, color, flag)


# -- deliver -------------------------------------------------------------------


@mcp.tool()
def render(
    out_dir: str,
    name: str | None = None,
    preset: str | None = None,
    format: str | None = None,
    codec: str | None = None,
    timeline: str | None = None,
) -> dict:
    """Render a timeline (blocks until done - renders take a while).
    Returns job status."""
    return _client().render(
        out_dir,
        custom_name=name,
        preset=preset,
        fmt=format,
        codec=codec,
        timeline_name=timeline,
    )


@mcp.tool()
def quick_export(
    preset: str, out_dir: str, name: str | None = None, timeline: str | None = None
) -> dict:
    """One-call render with a Quick Export preset (H.264 Master, YouTube,
    TikTok, ProRes 422 HQ, ...)."""
    return _client().quick_export(preset, out_dir, name, timeline_name=timeline)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
