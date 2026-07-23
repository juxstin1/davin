"""Workspace introspection: snapshot the project so agents/humans can see it."""

from __future__ import annotations

CLIP_KEYS = (
    "Type",
    "FPS",
    "Duration",
    "Resolution",
    "Format",
    "Audio Ch",
    "File Path",
)

PROJECT_SETTINGS = (
    "timelineFrameRate",
    "timelineResolutionWidth",
    "timelineResolutionHeight",
)


def _clip_info(clip, verbose: bool) -> dict:
    props = clip.GetClipProperty() or {}
    if verbose:
        info = {"name": clip.GetName(), **props}
    else:
        info = {"name": clip.GetName()}
        info.update({k: props[k] for k in CLIP_KEYS if props.get(k)})
    color = clip.GetClipColor()
    if color:
        info["color"] = color
    flags = clip.GetFlagList()
    if flags:
        info["flags"] = flags
    return info


def _folder_tree(folder, verbose: bool) -> dict:
    return {
        "name": folder.GetName(),
        "clips": [_clip_info(c, verbose) for c in folder.GetClipList() or []],
        "bins": [_folder_tree(f, verbose) for f in folder.GetSubFolderList() or []],
    }


def _timeline_info(timeline, is_current: bool) -> dict:
    from davin.client import timeline_fps

    tracks = {
        kind: timeline.GetTrackCount(kind) for kind in ("video", "audio", "subtitle")
    }
    items = sum(
        len(timeline.GetItemListInTrack("video", i) or [])
        for i in range(1, tracks["video"] + 1)
    )
    return {
        "name": timeline.GetName(),
        "fps": timeline_fps(timeline),
        "tracks": tracks,
        "videoItems": items,
        "markers": len(timeline.GetMarkers() or {}),
        "current": is_current,
    }


def snapshot(client, verbose: bool = False) -> dict:
    proj = client.project
    current = proj.GetCurrentTimeline()
    current_name = current.GetName() if current else None
    return {
        "project": proj.GetName(),
        "settings": {k: proj.GetSetting(k) for k in PROJECT_SETTINGS},
        "mediaPool": _folder_tree(client.media_pool.GetRootFolder(), verbose),
        "timelines": [
            _timeline_info(t, t.GetName() == current_name)
            for t in (
                proj.GetTimelineByIndex(i)
                for i in range(1, proj.GetTimelineCount() + 1)
            )
        ],
    }


def render_text(snap: dict) -> str:
    """Compact human-readable view of a snapshot."""
    s = snap["settings"]
    lines = [
        f"project: {snap['project']}  "
        f"({s['timelineResolutionWidth']}x{s['timelineResolutionHeight']} "
        f"@ {s['timelineFrameRate']} fps)"
    ]

    def walk(folder, depth):
        indent = "  " * depth
        lines.append(f"{indent}[{folder['name']}]")
        for clip in folder["clips"]:
            desc = "  ".join(
                str(clip[k]) for k in ("Type", "Resolution", "FPS", "Duration")
                if clip.get(k)
            )
            extras = "".join(
                f" #{clip[k]}" for k in ("color",) if clip.get(k)
            )
            lines.append(f"{indent}  {clip['name']}  {desc}{extras}".rstrip())
        for sub in folder["bins"]:
            walk(sub, depth + 1)

    walk(snap["mediaPool"], 0)
    if snap["timelines"]:
        lines.append("timelines:")
        for t in snap["timelines"]:
            cur = " *" if t["current"] else ""
            tr = t["tracks"]
            lines.append(
                f"  {t['name']}{cur}  {t['videoItems']} clips, "
                f"{tr['video']}v/{tr['audio']}a/{tr['subtitle']}s tracks, "
                f"{t['markers']} markers @ {t['fps']} fps"
            )
    return "\n".join(lines)
