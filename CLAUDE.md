# davin — DaVinci Resolve automation

Python package + CLI that drives DaVinci Resolve Studio through its scripting
API. Resolve must be **running** (takes ~30–60s after launch before it accepts
connections; `davin status` exits 2 until then).

**Python 3.12, pinned in `.python-version`.** Resolve 21's `fusionscript.dll`
hard-crashes (access violation, exit 139 / -1073741819, no traceback) under
3.13. A segfault from `davin status` means a 3.13 venv, not Resolve being down.
Fix: `rm -rf .venv && uv run davin status`.

Footage drops: `productions/stage_drop.py <story-day folder> --project ...
--label ... --work ...` stages any DASH story-day folder (cross-checks, captions
JSON, reels + boundary markers). It's idempotent: rerun it when missing reels
arrive. The Drive packages often lack the CLIP reels, but the per-clip 540p
proxies (`Shoot-Day Transcripts/<NN Day>/<NN Day>/<story>/`) rebuild them
**bit-identically** (verified by MD5 against a shipped reel) via
`productions/rebuild_reel.py`, into `Downloads\Making Arrangements (rebuilt
reels)\`. It refuses to build if any proxy is missing or off its manifest
duration.

## Drive it

- `uv run davin --help` — full command list. Every command accepts
  `--project NAME` (open-or-create first).
- `uv run davin inspect --json` — workspace state (bins, clips, timelines) for
  programmatic use.
- Multi-step logic: write a script against `from davin import DavinClient`
  instead of chaining many CLI calls.
- Write commands accept `--timeline NAME` — always pass it; "current timeline"
  is a mutable global a human can change by clicking in Resolve.
- `davin dup --timeline X` before destructive edits; `davin save` when done.
- The MCP adapter (`davin-mcp`, `uv sync --extra mcp`) is for no-shell callers
  only. With a shell, the CLI is the API. Keep logic in `client.py`; CLI and
  MCP stay thin adapters over it.

## Test

`uv run pytest` — needs Resolve running + ffmpeg. Generates its own TTS speech
fixture (`tests/fixtures/`), uses the project `davin-test`, cleans up its
timelines. Run it after touching frame math, transcript readback, or conform.

## API knowledge already paid for (do not re-lose)

- `AppendToTimeline` `endFrame` is **exclusive** — half-open second ranges map
  1:1 to frames. Pinned by `test_transcript_cutplan_papercut_render`.
- New timelines inherit the project default fps (24) regardless of source.
  Timeline-level `SetSetting("timelineFrameRate", ...)` **rejects fractional
  rates** (29.97 in any spelling) while accepting integers — set the *project*
  `timelineFrameRate` before creating the timeline and let it inherit;
  `create_timeline(fps=...)` does this and verifies loudly.
- `GetSetting("timelineFrameRate")` reports the project default for timelines
  without custom settings (a conformed 30fps timeline reads 24). Use
  `client.timeline_fps()` for any frame math. Pinned by
  `test_conform_roundtrip_preserves_fps`.
- Timelines and imports land in the **current media pool folder** — all
  creation paths guard with `_goto_root()`.
- No transcript getter exists in the API. `extract_transcript` reads captions
  back off a scratch timeline's subtitle track (`GetName`/`GetStart`/`GetEnd`).
- Title insertion silently fails unless the **edit page** is open; `Text+`
  needs `InsertFusionTitleIntoTimeline` (plain `InsertTitleIntoTimeline` is for
  Edit-page titles like `Text`).
- Transcription/captions/scene-cut need Studio; extended language models and
  IntelliSearch need Extras Download Manager installs.
- Full API reference:
  `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\README.txt`

## Layout

`src/davin/`: `bootstrap.py` (attach + liveness check), `client.py` (**single
source of truth**), `workspace.py` (inspect), `ranges.py` (kept-ranges +
captions→ranges seam), `cli.py`, `mcp_server.py` (thin adapters).
