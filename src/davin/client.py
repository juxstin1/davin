"""High-level wrapper over the Resolve scripting API."""

from __future__ import annotations

import time
from pathlib import Path

from davin.bootstrap import ResolveConnectionError, get_resolve

PAGES = ("media", "cut", "edit", "fusion", "color", "fairlight", "deliver")

# davin name -> Resolve clip property key (for `organize --by`)
ORGANIZE_PROPS = {
    "resolution": "Resolution",
    "fps": "FPS",
    "type": "Type",
    "format": "Format",
    "date": "Date Created",
}


class DavinError(RuntimeError):
    pass


def timeline_fps(timeline) -> float:
    """Actual timeline rate. GetSetting lies for timelines without custom
    settings (reports the project default), so prefer the timeline's own
    media pool item."""
    try:
        item = timeline.GetMediaPoolItem()
        if item:
            fps = float(item.GetClipProperty("FPS") or 0)
            if fps:
                return fps
    except Exception:
        pass
    return float(timeline.GetSetting("timelineFrameRate"))


class DavinClient:
    def __init__(self, resolve):
        self.resolve = resolve
        self.pm = resolve.GetProjectManager()

    @classmethod
    def connect(cls) -> "DavinClient":
        return cls(get_resolve())

    # -- projects ------------------------------------------------------

    @property
    def project(self):
        proj = self.pm.GetCurrentProject()
        if proj is None:
            raise DavinError("No project open in Resolve.")
        return proj

    @property
    def media_pool(self):
        return self.project.GetMediaPool()

    def list_projects(self) -> list[str]:
        return sorted(self.pm.GetProjectListInCurrentFolder())

    def open_project(self, name: str):
        proj = self.pm.LoadProject(name)
        if proj is None:
            raise DavinError(f"Project not found: {name}")
        return proj

    def create_project(self, name: str):
        proj = self.pm.CreateProject(name)
        if proj is None:
            raise DavinError(f"Could not create project {name!r} (name taken?)")
        return proj

    def ensure_project(self, name: str):
        if name in self.pm.GetProjectListInCurrentFolder():
            return self.open_project(name)
        return self.create_project(name)

    # -- media ---------------------------------------------------------

    def _goto_root(self):
        """Guard: pool operations land at root, not whatever bin is current."""
        root = self.media_pool.GetRootFolder()
        self.media_pool.SetCurrentFolder(root)
        return root

    def import_media(self, paths: list[str | Path], bin_path: str | None = None) -> list:
        """Import files into the media pool; resolves items already in the pool."""
        abs_paths = [str(Path(p).resolve()) for p in paths]
        for p in abs_paths:
            if not Path(p).exists():
                raise DavinError(f"File not found: {p}")
        if bin_path:
            self.media_pool.SetCurrentFolder(self.ensure_bin(bin_path))
        else:
            self._goto_root()
        imported = self.media_pool.ImportMedia(abs_paths) or []
        if len(imported) == len(abs_paths):
            return imported
        # Some (or all) were already in the pool - match them by file path.
        by_path = {}
        for clip in self._walk_clips(self.media_pool.GetRootFolder()):
            by_path[str(clip.GetClipProperty("File Path"))] = clip
        items = []
        for p in abs_paths:
            clip = by_path.get(p)
            if clip is None:
                raise DavinError(f"Import failed for {p}")
            items.append(clip)
        return items

    def _walk_clips(self, folder):
        yield from folder.GetClipList() or []
        for sub in folder.GetSubFolderList() or []:
            yield from self._walk_clips(sub)

    def find_clip(self, ref: str):
        """Find a media pool clip by name, file name, or file path."""
        ref_path = str(Path(ref).resolve()) if Path(ref).exists() else None
        matches = []
        for clip in self._walk_clips(self.media_pool.GetRootFolder()):
            path = str(clip.GetClipProperty("File Path"))
            if ref_path and path == ref_path:
                return clip
            if ref in (clip.GetName(), Path(path).name):
                matches.append(clip)
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise DavinError(f"No media pool clip matches {ref!r}")
        raise DavinError(f"{len(matches)} clips match {ref!r}; use a full path")

    # -- bins ------------------------------------------------------------

    def ensure_bin(self, path: str):
        """Get or create a bin by slash-separated path, e.g. 'b-roll/day1'."""
        folder = self.media_pool.GetRootFolder()
        for part in [p for p in path.replace("\\", "/").split("/") if p]:
            existing = {f.GetName(): f for f in folder.GetSubFolderList() or []}
            folder = existing.get(part) or self.media_pool.AddSubFolder(folder, part)
            if folder is None:
                raise DavinError(f"Could not create bin {part!r} in {path!r}")
        return folder

    def move_clips(self, refs: list[str], bin_path: str) -> int:
        clips = [self.find_clip(r) for r in refs]
        target = self.ensure_bin(bin_path)
        if not self.media_pool.MoveClips(clips, target):
            raise DavinError("MoveClips failed")
        return len(clips)

    def organize_by(self, prop: str) -> dict[str, int]:
        """Move loose root clips into bins named after a clip property value."""
        key = ORGANIZE_PROPS.get(prop)
        if key is None:
            raise DavinError(f"Unknown property {prop!r}; one of {list(ORGANIZE_PROPS)}")
        root = self.media_pool.GetRootFolder()
        groups: dict[str, list] = {}
        for clip in root.GetClipList() or []:
            if str(clip.GetClipProperty("Type")) == "Timeline":
                continue  # keep timelines where they are
            value = str(clip.GetClipProperty(key)).strip() or "unknown"
            groups.setdefault(value, []).append(clip)
        moved = {}
        for value, clips in sorted(groups.items()):
            bin_name = value.replace(":", ".").replace("/", "-")
            if not self.media_pool.MoveClips(clips, self.ensure_bin(bin_name)):
                raise DavinError(f"MoveClips failed for bin {bin_name!r}")
            moved[bin_name] = len(clips)
        return moved

    # -- transcription (Resolve's built-in AI) ----------------------------

    def transcribe(self, ref: str, speakers: bool | None = None) -> str:
        """Run Resolve's audio transcription on a media pool clip."""
        clip = self.find_clip(ref)
        ok = (
            clip.TranscribeAudio()
            if speakers is None
            else clip.TranscribeAudio(speakers)
        )
        if not ok:
            raise DavinError(
                f"TranscribeAudio failed for {clip.GetName()!r} "
                "(no audio, or language model not installed?)"
            )
        return clip.GetName()

    def auto_caption(
        self,
        timeline=None,
        language: str | None = None,
        chars_per_line: int | None = None,
        preset: str | None = None,
    ) -> int:
        """Timeline.CreateSubtitlesFromAudio; returns caption count."""
        timeline = timeline or self.project.GetCurrentTimeline()
        if timeline is None:
            raise DavinError("No current timeline")
        r = self.resolve
        settings = {}
        if language:
            settings[r.SUBTITLE_LANGUAGE] = getattr(
                r, f"AUTO_CAPTION_{language.upper()}", None
            )
            if settings[r.SUBTITLE_LANGUAGE] is None:
                raise DavinError(f"Unknown caption language {language!r}")
        if chars_per_line:
            settings[r.SUBTITLE_CHARS_PER_LINE] = chars_per_line
        if preset:
            settings[r.SUBTITLE_CAPTION_PRESET] = getattr(
                r, f"AUTO_CAPTION_{preset.upper()}", None
            )
            if settings[r.SUBTITLE_CAPTION_PRESET] is None:
                raise DavinError(f"Unknown caption preset {preset!r}")
        ok = (
            timeline.CreateSubtitlesFromAudio(settings)
            if settings
            else timeline.CreateSubtitlesFromAudio()
        )
        if not ok:
            raise DavinError(
                "CreateSubtitlesFromAudio failed (Studio + language model required)"
            )
        return len(self.read_subtitles(timeline))

    def read_subtitles(self, timeline=None) -> list[dict]:
        """Read subtitle items as [{start, end, text}] in seconds."""
        timeline = timeline or self.project.GetCurrentTimeline()
        if timeline is None:
            raise DavinError("No current timeline")
        fps = timeline_fps(timeline)
        t0 = timeline.GetStartFrame()
        captions = []
        for idx in range(1, timeline.GetTrackCount("subtitle") + 1):
            for item in timeline.GetItemListInTrack("subtitle", idx) or []:
                captions.append(
                    {
                        "start": round((item.GetStart() - t0) / fps, 3),
                        "end": round((item.GetEnd() - t0) / fps, 3),
                        "text": item.GetName(),
                    }
                )
        captions.sort(key=lambda c: c["start"])
        return captions

    def extract_transcript(
        self,
        source: str | Path,
        language: str | None = None,
        keep_timeline: bool = False,
    ) -> list[dict]:
        """Transcript with timings for a media file, via a scratch caption timeline."""
        [item] = self.import_media([source])
        fps = float(item.GetClipProperty("FPS") or 0) or None
        timeline = self.create_timeline(
            f"transcript {Path(str(source)).stem}", [item], fps=fps
        )
        try:
            self.auto_caption(timeline, language=language)
            return self.read_subtitles(timeline)
        finally:
            if not keep_timeline:
                self.media_pool.DeleteTimelines([timeline])

    # -- timeline editing --------------------------------------------------

    def get_timeline(self, name: str | None = None):
        proj = self.project
        if name is None:
            timeline = proj.GetCurrentTimeline()
            if timeline is None:
                raise DavinError("No current timeline")
            return timeline
        for idx in range(1, proj.GetTimelineCount() + 1):
            timeline = proj.GetTimelineByIndex(idx)
            if timeline.GetName() == name:
                proj.SetCurrentTimeline(timeline)
                return timeline
        raise DavinError(f"Timeline not found: {name}")

    def detect_scene_cuts(self, timeline_name: str | None = None) -> bool:
        return self.get_timeline(timeline_name).DetectSceneCuts()

    def add_marker(
        self,
        seconds: float,
        color: str = "Blue",
        name: str = "",
        note: str = "",
        duration_s: float = 0.0,
        timeline_name: str | None = None,
    ) -> bool:
        timeline = self.get_timeline(timeline_name)
        fps = timeline_fps(timeline)
        return timeline.AddMarker(
            round(seconds * fps), color, name, note, max(1, round(duration_s * fps))
        )

    def list_markers(self, timeline_name: str | None = None) -> dict:
        return self.get_timeline(timeline_name).GetMarkers() or {}

    # -- timelines -----------------------------------------------------

    def create_timeline(
        self, name: str, clips: list | None = None, fps: float | None = None
    ):
        self._goto_root()
        fps_str = f"{fps:g}" if fps is not None else None
        if fps_str:
            # Timeline-level SetSetting rejects fractional rates (29.97 etc.),
            # so set the project default first and let the timeline inherit it.
            self.project.SetSetting("timelineFrameRate", fps_str)
        timeline = None
        for suffix in [""] + [f" {n}" for n in range(2, 100)]:
            timeline = self.media_pool.CreateEmptyTimeline(name + suffix)
            if timeline is not None:
                break
        if timeline is None:
            raise DavinError(f"Could not create timeline {name!r}")
        if fps_str:
            # Integer rates can additionally be pinned per-timeline (while empty).
            if timeline.SetSetting("useCustomSettings", "1"):
                timeline.SetSetting("timelineFrameRate", fps_str)
            actual = float(timeline.GetSetting("timelineFrameRate") or 0)
            if abs(actual - fps) > 0.01:
                self.media_pool.DeleteTimelines([timeline])
                raise DavinError(
                    f"Timeline rate is {actual:g}, wanted {fps:g} - "
                    "project frame rate may be locked"
                )
        if clips:
            if not self.media_pool.AppendToTimeline(clips):
                raise DavinError("AppendToTimeline failed")
        return timeline

    def papercut(
        self,
        source: str | Path,
        ranges: list[tuple[float, float]],
        name: str | None = None,
        fps: float | None = None,
    ):
        """Build a timeline from kept ranges (seconds) of a single source clip."""
        [item] = self.import_media([source])
        if fps is None:
            fps = float(item.GetClipProperty("FPS"))
            if not fps:
                raise DavinError("Could not read clip FPS; pass fps explicitly.")
        clip_infos = []
        for start_s, end_s in ranges:
            start_f = max(0, round(start_s * fps))
            # Resolve treats endFrame as exclusive, matching half-open ranges.
            end_f = max(start_f + 1, round(end_s * fps))
            clip_infos.append(
                {"mediaPoolItem": item, "startFrame": start_f, "endFrame": end_f}
            )
        tl_name = name or f"{Path(source).stem} papercut"
        timeline = self.create_timeline(tl_name, clip_infos, fps=fps)
        return timeline, fps

    # -- render --------------------------------------------------------

    def render_presets(self) -> list[str]:
        return self.project.GetRenderPresetList()

    def render(
        self,
        target_dir: str | Path,
        custom_name: str | None = None,
        preset: str | None = None,
        fmt: str | None = None,
        codec: str | None = None,
        wait: bool = True,
        on_progress=None,
        timeline_name: str | None = None,
    ):
        if timeline_name:
            self.get_timeline(timeline_name)  # render targets the current timeline
        proj = self.project
        if preset is not None and not proj.LoadRenderPreset(preset):
            raise DavinError(
                f"Unknown render preset {preset!r}. Available: {self.render_presets()}"
            )
        if fmt is not None:
            if not proj.SetCurrentRenderFormatAndCodec(fmt, codec or ""):
                raise DavinError(f"Format/codec not accepted: {fmt}/{codec}")
        target_dir = Path(target_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        settings = {"TargetDir": str(target_dir), "SelectAllFrames": True}
        if custom_name:
            settings["CustomName"] = custom_name
        if not proj.SetRenderSettings(settings):
            raise DavinError("SetRenderSettings rejected")
        job = proj.AddRenderJob()
        if not job:
            raise DavinError("AddRenderJob failed (is a timeline open?)")
        if not proj.StartRendering(job):
            raise DavinError("StartRendering failed")
        if not wait:
            return {"JobId": job, "JobStatus": "Started"}
        while proj.IsRenderingInProgress():
            if on_progress is not None:
                status = proj.GetRenderJobStatus(job)
                on_progress(status.get("CompletionPercentage") or 0)
            time.sleep(2)
        status = proj.GetRenderJobStatus(job)
        status["JobId"] = job
        return status

    # -- export / stills -----------------------------------------------

    EXPORT_TYPES = {
        "otio": "EXPORT_OTIO",
        "edl": "EXPORT_EDL",
        "fcpxml": "EXPORT_FCPXML_1_10",
        "csv": "EXPORT_TEXT_CSV",
        "drt": "EXPORT_DRT",
        "aaf": "EXPORT_AAF",
    }

    def export_timeline(
        self, path: str | Path, kind: str | None = None, timeline_name: str | None = None
    ) -> Path:
        path = Path(path).resolve()
        kind = kind or path.suffix.lstrip(".").lower().replace("xml", "fcpxml")
        if kind not in self.EXPORT_TYPES:
            raise DavinError(f"Unknown export type {kind!r}; one of {list(self.EXPORT_TYPES)}")
        timeline = self.get_timeline(timeline_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        r = self.resolve
        subtype = r.EXPORT_AAF_NEW if kind == "aaf" else r.EXPORT_NONE
        if not timeline.Export(str(path), getattr(r, self.EXPORT_TYPES[kind]), subtype):
            raise DavinError(f"Export failed: {path}")
        return path

    def import_timeline(
        self,
        path: str | Path,
        name: str | None = None,
        media_dir: str | Path | None = None,
    ):
        """Conform a timeline file (OTIO/AAF/EDL/XML/FCPXML/DRT) into the project."""
        path = Path(path).resolve()
        if not path.exists():
            raise DavinError(f"File not found: {path}")
        self._goto_root()
        options = {}
        if name:
            options["timelineName"] = name
        if media_dir:
            options["sourceClipsPath"] = str(Path(media_dir).resolve())
        timeline = self.media_pool.ImportTimelineFromFile(str(path), options)
        if timeline is None:
            raise DavinError(f"ImportTimelineFromFile failed for {path}")
        return timeline

    def quick_export_presets(self) -> list[str]:
        return self.project.GetQuickExportRenderPresets() or []

    def quick_export(
        self,
        preset: str,
        target_dir: str | Path,
        name: str | None = None,
        timeline_name: str | None = None,
    ):
        if timeline_name:
            self.get_timeline(timeline_name)
        target = Path(target_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)
        params = {"TargetDir": str(target)}
        if name:
            params["CustomName"] = name
        status = self.project.RenderWithQuickExport(preset, params)
        if not isinstance(status, dict):
            raise DavinError(f"Quick export failed: {status}")
        return status

    def seek(
        self,
        seconds: float | None = None,
        timecode: str | None = None,
        timeline_name: str | None = None,
    ) -> str:
        timeline = self.get_timeline(timeline_name)
        if timecode is None:
            fps = timeline_fps(timeline)
            frame = round(seconds * fps) + timeline.GetStartFrame()
            fpsi = max(1, round(fps))
            secs, ff = divmod(frame, fpsi)
            timecode = f"{secs // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}:{ff:02d}"
        if not timeline.SetCurrentTimecode(timecode):
            raise DavinError(f"Could not seek to {timecode}")
        return timeline.GetCurrentTimecode()

    def export_still(
        self,
        path: str | Path,
        at_seconds: float | None = None,
        timeline_name: str | None = None,
    ) -> Path:
        self.get_timeline(timeline_name)  # pin the target before touching playhead
        self.resolve.OpenPage("edit")  # still export fails on the deliver page
        if at_seconds is not None:
            self.seek(at_seconds)
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.project.ExportCurrentFrameAsStill(str(path)):
            raise DavinError(f"ExportCurrentFrameAsStill failed: {path}")
        return path

    def contact_sheet(
        self,
        out_dir: str | Path,
        middle: bool = True,
        fmt: str = "png",
        timeline_name: str | None = None,
    ) -> list[str]:
        """Grab a still from every clip of a timeline; returns file paths."""
        timeline = self.get_timeline(timeline_name)
        stills = timeline.GrabAllStills(2 if middle else 1)
        if not stills:
            raise DavinError("GrabAllStills returned nothing")
        out = Path(out_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        existing = set(out.iterdir())
        album = self.project.GetGallery().GetCurrentStillAlbum()
        ok = album.ExportStills(stills, str(out), timeline.GetName(), fmt)
        album.DeleteStills(stills)  # keep the gallery clean
        if not ok:
            raise DavinError("ExportStills failed")
        return sorted(str(p) for p in set(out.iterdir()) - existing)

    # -- clip + track control --------------------------------------------

    def tag_clip(
        self,
        ref: str,
        color: str | None = None,
        flag: str | None = None,
        clear: bool = False,
    ):
        clip = self.find_clip(ref)
        if clear:
            clip.ClearClipColor()
            clip.ClearFlags("All")
        if color and not clip.SetClipColor(color):
            raise DavinError(f"SetClipColor rejected {color!r}")
        if flag and not clip.AddFlag(flag):
            raise DavinError(f"AddFlag rejected {flag!r}")
        return clip.GetName()

    def set_voice_isolation(
        self,
        track: int = 1,
        amount: int = 50,
        enabled: bool = True,
        timeline_name: str | None = None,
    ):
        timeline = self.get_timeline(timeline_name)
        state = {"isEnabled": enabled, "amount": amount}
        if not timeline.SetVoiceIsolationState(track, state):
            raise DavinError("SetVoiceIsolationState failed (Studio/AI required)")
        return timeline.GetVoiceIsolationState(track)

    def _video_item(self, index: int, track: int = 1, timeline_name: str | None = None):
        items = self.get_timeline(timeline_name).GetItemListInTrack("video", track) or []
        if not 1 <= index <= len(items):
            raise DavinError(f"Clip index {index} out of range (track has {len(items)})")
        return items[index - 1]

    def stabilize(
        self, index: int, track: int = 1, timeline_name: str | None = None
    ) -> bool:
        return self._video_item(index, track, timeline_name).Stabilize()

    def duplicate_timeline(
        self, new_name: str | None = None, timeline_name: str | None = None
    ):
        timeline = self.get_timeline(timeline_name)
        dup = (
            timeline.DuplicateTimeline(new_name)
            if new_name
            else timeline.DuplicateTimeline()
        )
        if dup is None:
            raise DavinError("DuplicateTimeline failed")
        return dup

    def insert_title(
        self,
        text: str | None = None,
        title_name: str = "Text+",
        at_seconds: float | None = None,
        timeline_name: str | None = None,
    ) -> tuple[str, bool]:
        """Insert a title at the playhead; best-effort set its text via Fusion."""
        timeline = self.get_timeline(timeline_name)
        if at_seconds is not None:
            self.seek(at_seconds)
        self.resolve.OpenPage("edit")  # title insertion needs the edit page
        item = timeline.InsertFusionTitleIntoTimeline(title_name)
        if item is None:
            item = timeline.InsertTitleIntoTimeline(title_name)
        if item is None:
            raise DavinError(f"Could not insert title {title_name!r}")
        text_set = False
        if text:
            try:
                comp = item.GetFusionCompByIndex(1)
                for tool in (comp.GetToolList(False, "TextPlus") or {}).values():
                    tool.SetInput("StyledText", text)
                    text_set = True
                    break
            except Exception:
                pass
        return item.GetName(), text_set

    def save(self) -> bool:
        return self.pm.SaveProject()

    # -- misc ----------------------------------------------------------

    def open_page(self, page: str):
        if page not in PAGES:
            raise DavinError(f"Unknown page {page!r}; one of {PAGES}")
        self.resolve.OpenPage(page)

    def status(self) -> dict:
        info = {
            "product": self.resolve.GetProductName(),
            "version": self.resolve.GetVersionString(),
            "project": None,
            "timeline": None,
            "timelines": 0,
        }
        proj = self.pm.GetCurrentProject()
        if proj is not None:
            info["project"] = proj.GetName()
            info["timelines"] = proj.GetTimelineCount()
            timeline = proj.GetCurrentTimeline()
            if timeline is not None:
                info["timeline"] = timeline.GetName()
        return info


__all__ = ["DavinClient", "DavinError", "ResolveConnectionError", "PAGES"]
