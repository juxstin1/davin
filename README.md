# davin

Drive **DaVinci Resolve Studio** from the terminal via its scripting API — projects,
media, timelines, renders, and *papercut*: turn a kept-ranges JSON (the avenger
`KeptRange[]` edit model) into a real Resolve timeline.

## Requirements

- DaVinci Resolve **Studio** (free edition blocks external scripting), **running**
- Preferences → System → General → **External scripting using: Local**
- Python 3.10+ (64-bit), `uv`

No env vars needed — davin loads `DaVinciResolveScript.py` from Resolve's install
location directly.

## Setup

```powershell
cd davin
uv sync
uv run davin status
```

## Commands

```powershell
davin status                          # connection + current project/timeline
davin inspect [--json] [--verbose]    # workspace snapshot: bins, clips, timelines
davin projects                        # list projects
davin project create MyProject
davin import a.mp4 b.mp4 --project MyProject
davin timeline "Rough Cut" --clips a.mp4 b.mp4
davin papercut talk.mp4 kept.json --name "Talk papercut"
davin cutplan talk.captions.json --drop-matching "um|uh" --out kept.json
davin conform cut.otio --name "v2" --media D:\footage   # timeline file -> timeline
davin presets                         # render presets
davin render .\out --preset "H.264 Master" --name final
davin page deliver                    # switch UI page
```

Every command takes `--project NAME` to open-or-create that project first.

### Built-in AI features (Studio)

```powershell
davin transcript talk.mp4 --out talk.captions.json   # transcript JSON with timings
davin transcribe talk.mp4 --speakers  # clip transcription (text-based editing in UI)
davin subtitles --lang english        # auto-caption the current timeline
davin scenecut                        # split clips at detected scene changes
```

`transcript` works around the API having no transcript getter: it drops the clip on
a scratch timeline, runs `CreateSubtitlesFromAudio`, reads the subtitle items back
(`text`, `start`, `end` in seconds), then deletes the timeline (`--keep-timeline`
to keep it).

### Control pack

```powershell
davin export cut.otio                 # timeline -> otio/edl/fcpxml/csv/drt/aaf
davin quickexport                     # list Quick Export presets (YouTube, TikTok...)
davin quickexport YouTube --out .\out --name final
davin seek 12.5                       # move playhead (seconds or timecode)
davin still frame.png --at 3.0        # export a frame as an image
davin stills .\thumbs                 # contact sheet: one still per timeline clip
davin dup --name "cut v2"             # duplicate timeline before risky edits
davin title "MY CUT" --at 0.5         # insert Text+ title, text set via Fusion
davin voiceiso --amount 60            # AI voice isolation on an audio track
davin stabilize 1                     # stabilize clip 1 on video track 1
davin tag speech.mp4 --color Orange --flag Green
davin save                            # save the project
```

### Organize

```powershell
davin bin b-roll/day1                 # create bins (slash path)
davin move speech.mp4 --bin b-roll    # move clips by name or path
davin organize --by resolution        # bin loose root clips (fps/type/format/date)
davin markers --add 5.0 --color Red --name "cut here"
davin markers                         # list timeline markers
```

## Papercut ranges format

Seconds, half-open `[start, end)`. Any of:

```json
[[1.25, 3.5], [7.0, 9.2]]
[{"start": 1.25, "end": 3.5}]
{"ranges": [{"startSeconds": 1.25, "endSeconds": 3.5}]}
```

Ranges → source frames at the clip's native fps (`--fps` to override), appended
in order to a new timeline via `MediaPool.AppendToTimeline`.

## Text-based editing, no hands

```powershell
davin transcript talk.mp4 --out talk.captions.json
davin cutplan talk.captions.json --drop 3 4 --drop-matching "boring" --out kept.json
davin papercut talk.mp4 kept.json --name "auto edit"
davin render .\out --format mp4 --codec H264 --name final
```

`cutplan` is the seam: whoever chooses (model, regex, human) drops captions;
survivors merge into ranges (`--join-gap`, `--pad`).

## MCP server

22 tools over stdio: perception (`inspect`, `transcript`, `stills`), versioning
(`duplicate_timeline`, `save_project`), safe writes (`papercut`, `conform`),
plus organize/render.

```powershell
uv sync --extra mcp
uv run python scripts\mcp_smoke.py   # verify
```

`.mcp.json`:

```json
{
  "mcpServers": {
    "davin": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\Users\\juxxs\\Desktop\\davin\\davin", "davin-mcp"]
    }
  }
}
```

## Library use

```python
from davin import DavinClient

client = DavinClient.connect()
client.ensure_project("MyProject")
timeline, fps = client.papercut("talk.mp4", [(1.25, 3.5), (7.0, 9.2)])
client.render("out", custom_name="final", preset="H.264 Master")
```

Place exact source ranges over an existing cut without bringing their audio:

```python
timeline = client.get_timeline("Rough Cut")
[broll] = client.import_media(["broll.mp4"])
client.add_video_overlays(
    timeline,
    [
        {
            "mediaPoolItem": broll,
            "start_s": 12.5,
            "end_s": 16.0,
            "record_s": 42.0,
        }
    ],
)
```

Source ranges use each clip's native frame rate. Program positions are relative
to timeline start and use the timeline's frame rate; the method creates V2 when
needed and submits video only.
