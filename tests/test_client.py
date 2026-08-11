from __future__ import annotations

import pytest

from davin.client import DavinClient, DavinError


class FakeMediaItem:
    def __init__(self, fps: float):
        self.fps = fps

    def GetClipProperty(self, name: str):
        return str(self.fps) if name == "FPS" else ""


class FakeTimeline:
    def __init__(self, fps: float = 30, start_frame: int = 100):
        self.fps = fps
        self.start_frame = start_frame
        self.video_tracks = 1
        self.add_track_calls = 0
        self.deleted_items = []
        self.deleted_tracks = []

    def GetMediaPoolItem(self):
        return FakeMediaItem(self.fps)

    def GetSetting(self, name: str):
        return str(self.fps) if name == "timelineFrameRate" else ""

    def GetStartFrame(self):
        return self.start_frame

    def GetTrackCount(self, track_type: str):
        return self.video_tracks if track_type == "video" else 0

    def AddTrack(self, track_type: str):
        assert track_type == "video"
        self.video_tracks += 1
        self.add_track_calls += 1
        return True

    def DeleteClips(self, items, ripple: bool):
        assert ripple is False
        self.deleted_items.extend(items)
        return True

    def DeleteTrack(self, track_type: str, track_index: int):
        assert track_type == "video"
        assert track_index == self.video_tracks
        self.video_tracks -= 1
        self.deleted_tracks.append(track_index)
        return True


class FakeMediaPool:
    def __init__(self, append_count: int | None = None):
        self.appended = []
        self.append_count = append_count

    def AppendToTimeline(self, clip_infos):
        self.appended.append(clip_infos)
        count = len(clip_infos) if self.append_count is None else self.append_count
        return [object() for _ in range(count)]


class FakeProject:
    def __init__(self, *, set_current_ok: bool = True, append_count: int | None = None):
        self.media_pool = FakeMediaPool(append_count=append_count)
        self.set_current_ok = set_current_ok
        self.set_current_calls = 0
        self.current_timeline = object()

    def GetMediaPool(self):
        return self.media_pool

    def GetCurrentTimeline(self):
        return self.current_timeline

    def SetCurrentTimeline(self, timeline):
        self.set_current_calls += 1
        if self.set_current_ok:
            self.current_timeline = timeline
            return True
        return False


class FakeProjectManager:
    def __init__(self, project):
        self.project = project

    def GetCurrentProject(self):
        return self.project


class FakeResolve:
    def __init__(self, project):
        self.project_manager = FakeProjectManager(project)

    def GetProjectManager(self):
        return self.project_manager


def make_client(*, set_current_ok: bool = True, append_count: int | None = None):
    project = FakeProject(
        set_current_ok=set_current_ok,
        append_count=append_count,
    )
    return DavinClient(FakeResolve(project)), project


def test_video_overlays_use_source_fps_for_trim_and_timeline_fps_for_record():
    client, project = make_client()
    timeline = FakeTimeline(fps=30, start_frame=100)
    source = FakeMediaItem(fps=24)

    count = client.add_video_overlays(
        timeline,
        [
            {
                "mediaPoolItem": source,
                "start_s": 1.0,
                "end_s": 3.0,
                "record_s": 2.0,
            }
        ],
    )

    assert count == 1
    [[clip_info]] = project.media_pool.appended
    assert clip_info == {
        "mediaPoolItem": source,
        "startFrame": 24,
        "endFrame": 72,
        "recordFrame": 160,
        "trackIndex": 2,
        "mediaType": 1,
    }


@pytest.mark.parametrize(
    "start_s,end_s,record_s",
    [(-1, 1, 0), (1, 1, 0), (2, 1, 0), (0, 1, -1)],
)
def test_video_overlays_reject_invalid_times_before_mutating_timeline(
    start_s, end_s, record_s
):
    client, project = make_client()
    timeline = FakeTimeline()

    with pytest.raises(DavinError):
        client.add_video_overlays(
            timeline,
            [
                {
                    "mediaPoolItem": FakeMediaItem(24),
                    "start_s": start_s,
                    "end_s": end_s,
                    "record_s": record_s,
                }
            ],
        )

    assert project.set_current_calls == 0
    assert timeline.add_track_calls == 0
    assert project.media_pool.appended == []


def test_video_overlays_stop_when_destination_timeline_cannot_be_selected():
    client, project = make_client(set_current_ok=False)
    timeline = FakeTimeline()

    with pytest.raises(DavinError, match="destination timeline"):
        client.add_video_overlays(
            timeline,
            [
                {
                    "mediaPoolItem": FakeMediaItem(24),
                    "start_s": 0,
                    "end_s": 1,
                    "record_s": 0,
                }
            ],
        )

    assert timeline.add_track_calls == 0
    assert project.media_pool.appended == []


def test_video_overlays_roll_back_partial_append_and_created_track():
    client, project = make_client(append_count=1)
    previous_timeline = project.current_timeline
    timeline = FakeTimeline()
    source = FakeMediaItem(24)

    with pytest.raises(DavinError, match="appended 1 of 2"):
        client.add_video_overlays(
            timeline,
            [
                {
                    "mediaPoolItem": source,
                    "start_s": 0,
                    "end_s": 1,
                    "record_s": 0,
                },
                {
                    "mediaPoolItem": source,
                    "start_s": 1,
                    "end_s": 2,
                    "record_s": 1,
                },
            ],
        )

    assert len(timeline.deleted_items) == 1
    assert timeline.deleted_tracks == [2]
    assert timeline.video_tracks == 1
    assert project.current_timeline is previous_timeline
