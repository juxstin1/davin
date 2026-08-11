"""Smoke tests pinning the knowledge this project paid for:

- endFrame-exclusive papercut math (render duration == kept duration)
- transcript extraction via the subtitle-track readback
- timeline_fps() surviving the conform round trip (GetSetting lies at 24)
"""

from __future__ import annotations

from davin.client import timeline_fps
from davin.ranges import captions_to_ranges

from conftest import ffprobe_duration


def test_transcript_cutplan_papercut_render(client, speech_clip, tmp_path):
    captions = client.extract_transcript(speech_clip)
    assert len(captions) >= 4
    text = " ".join(c["text"].lower() for c in captions)
    assert "boring" in text

    ranges, dropped = captions_to_ranges(captions, drop_matching="boring|cut out")
    assert dropped, "the chooser regex must drop at least one caption"
    assert ranges

    timeline, fps = client.papercut(speech_clip, ranges, "smoke papercut")
    try:
        status = client.render(
            str(tmp_path),
            custom_name="smoke",
            fmt="mp4",
            codec="H264",
            timeline_name=timeline.GetName(),
        )
        assert status["JobStatus"] == "Complete"
        rendered = next(tmp_path.glob("smoke*.mp4"))
        kept = sum(e - s for s, e in ranges)
        # endFrame-exclusive: rendered duration matches kept duration to
        # within a frame per cut plus container slack.
        slack = len(ranges) / fps + 0.15
        assert abs(ffprobe_duration(rendered) - kept) < slack
    finally:
        client.media_pool.DeleteTimelines([timeline])


def test_conform_roundtrip_preserves_fps(client, speech_clip, tmp_path):
    timeline, fps = client.papercut(speech_clip, [(1.0, 3.0)], "smoke roundtrip")
    conformed = None
    try:
        otio = tmp_path / "roundtrip.otio"
        client.export_timeline(otio, timeline_name=timeline.GetName())
        assert otio.exists()
        conformed = client.import_timeline(otio, name="smoke conformed")
        # GetSetting("timelineFrameRate") reports the project default (24)
        # for non-custom timelines; timeline_fps must see the real rate.
        assert timeline_fps(conformed) == fps
    finally:
        doomed = [t for t in (timeline, conformed) if t is not None]
        client.media_pool.DeleteTimelines(doomed)


def test_video_overlay_uses_absolute_record_frame_without_adding_audio(
    client, speech_clip
):
    [item] = client.import_media([speech_clip])
    source_fps = float(item.GetClipProperty("FPS"))
    timeline_rate = 24
    timeline = client.create_timeline(
        "smoke overlay",
        [
            {
                "mediaPoolItem": item,
                "startFrame": 0,
                "endFrame": round(6 * source_fps),
            }
        ],
        fps=timeline_rate,
    )
    try:
        audio_before = [
            (clip.GetName(), clip.GetStart(), clip.GetEnd())
            for track in range(1, timeline.GetTrackCount("audio") + 1)
            for clip in timeline.GetItemListInTrack("audio", track) or []
        ]
        count = client.add_video_overlays(
            timeline,
            [
                {
                    "mediaPoolItem": item,
                    "start_s": 10.0,
                    "end_s": 12.0,
                    "record_s": 2.0,
                }
            ],
        )
        assert count == 1
        assert timeline.GetTrackCount("video") == 2
        [overlay] = timeline.GetItemListInTrack("video", 2)
        assert overlay.GetStart() == timeline.GetStartFrame() + round(2 * timeline_rate)
        assert overlay.GetDuration() == round(2 * timeline_rate)
        audio_after = [
            (clip.GetName(), clip.GetStart(), clip.GetEnd())
            for track in range(1, timeline.GetTrackCount("audio") + 1)
            for clip in timeline.GetItemListInTrack("audio", track) or []
        ]
        assert audio_after == audio_before
    finally:
        client.media_pool.DeleteTimelines([timeline])
