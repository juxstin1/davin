# MA129 "Music Therapy" — Editor Handoff

Everything in this package is **traceable**: every cut in every timeline maps
to a JSON cutlist entry, which maps to a transcript timecode you can read in
plain text. Nothing was eyeballed; if you want to know why a cut exists, the
answer is written down.

## The package

**Resolve project `DASH-MA129`** (Studio 21, 29.97 NTSC throughout):

| Timeline | What it is |
| --- | --- |
| `MA129 D5 clip reel` / `MA129 D5 broll reel` | Day 5 dailies (2h02m / 11m), one boundary marker per source clip (Blue = CAM A, Cyan = CAM B, note = full clip name) |
| `MA129 clip reel` / `MA129 broll reel` | Day 6 dailies (2h26m / 9m32s), same marker scheme |
| `MA129 D5 selects v2` | Day 5 selects, 27 cuts / 19.1 min, beat-colored markers |
| `MA129 selects v3` | Day 6 selects, 34 cuts / 21.6 min, beat-colored markers |
| `MA129 episode assembly v1` | The radio cut: 13:52, 44 cuts (cold open 0:34 → Act 1/2 5:29 → Act 3 6:27 → close 1:22), marker per cut with source + rationale (Lemon/Green/Red/Purple by section) |
| `MA129 episode assembly v2` | v1 + picture pass: 20 video-only b-roll/reaction overlays on V2 (Cream markers), placed from the visual b-roll log (`broll_log\d{5,6}_log.json` — every b-roll clip described from stills). Screener: `out\MA129_assembly_v2.mp4` |
| `MA129 episode assembly v3` | **Current: 26 overlays (every intra-scene jump-cut seam now bridged), voice isolation 35% on A1, 419 auto-captions on the subtitle track** (QC before delivery; render with SubtitleFormat SeparateFile for SRT). Screener: `out\MA129_assembly_v3.mp4`. Not done by design: B-cam angle flips (needs waveform A/B alignment — transcript offsets risk lip drift), music bed (no library provided), J/L audio restructure (post sync-verdict). |

**On disk (`Desktop\davin\ma129\`):**
- `selects.json` / `day05\selects.json` — the source of truth for selects (label, start, end, cam, alternates, quote)
- `episode\cutlist.json` + `episode\{bookends,act12,act3}.json` — the assembly's edit decisions with rationale
- `*.captions.json` — full transcripts, reel-relative seconds
- `SELECTS.md` / `day05\SELECTS.md` — human-readable spines, alternates maps, rights tables
- `out\MA129_assembly_v1.mp4` — screener render
- `out\MA129_assembly_v1.otio` / `.edl` — portable versions of the assembly

## Conventions

- **Marker colors** on selects/assembly: Yellow = build-up, Green = arrival,
  Red = gift/reveal, Purple = story/sit-down, Fuchsia = decision-to-scale,
  Sky = INT Trish, Rose = INT Gail. On dailies reels: Blue/Cyan = clip
  boundaries (jump between markers to navigate the day).
- **A↔B twins**: every scene has second-angle CAM B coverage. Twin maps are in
  the SELECTS docs; exact B-cam offsets are the Cyan markers on the dailies
  timelines. B-cam occasionally has the clean read of a line garbled on A
  (both known cases are already in the selects, labeled `-bcam`).
- Timelines are **append-only**: rebuilds get a new version suffix; old ones
  stay for diffing. Delete at your own discretion.

## Known issues / open items

1. **Audio sync**: possible per-segment A/V offset baked into the concat
   reels (metadata is clean; suspicion is per-splice audio priming). Raw
   discriminating snippets are in `davin\out\sync-check-*.mp4` — play outside
   Resolve. If confirmed, fix is upstream in the Mac concat or an audio slip
   on affected segments.
2. **No shop footage** — Act 1 beats 1.1/1.4 (Neville working, building the
   arrangement) exist in neither drop. The assembly opens without them.
3. **Rights**: cleared-by-default only This Little Light of Mine + Michael
   Row the Boat Ashore (traditional). Flagged: Bring Me Sunshine (1966),
   Eight Days a Week (Beatles), Peaceful Easy Feeling fragment. Floor audio
   on D6 says "we can't use this song" before Bring Me Sunshine.
4. **EP note applied**: all nominating language and show-self-reference cut
   from selects v3 / D5 v2 and the assembly. Two borderline survivors
   (`meant-to-be`, `gail-blownaway`) — no banned words, but they carry the
   premise; kill them if the EP means the framing, not just the word.
5. **Cold open** is a first pass; EP already noted it needs work. Alternate
   cold-open candidates are listed in `episode\bookends.json` notes.
6. **Media is 540p proxies.** For online, relink to camera originals
   (Resolve: Relink Media / davin `RelinkClips` can be scripted when drives
   are available). All cuts are frame-math on the reels, so a re-conform of
   the same reels at full res drops in losslessly.

## How to work with davin (the fast loop)

You never have to hand-edit a timeline to try a note:

1. Say the note in plain language ("lose the 11:11 story", "tighten the
   pinning scene", "swap the cold open for the thesis line") — or edit the
   JSON yourself: drop/nudge entries in `episode\cutlist.json` or a
   `selects.json`.
2. Rebuild: `uv run python ..\ma129\episode\build_episode.py "MA129 episode
   assembly v2"` (or the day builders for selects). Seconds, not hours.
3. Screen: `uv run davin render out --format mp4 --codec H264 --timeline
   "<name>" --name <file>` or `davin quickexport YouTube`.

Other things to ask for, because they're one command away: transcript search
("find where anyone says X" — it's grep on the captions JSON), a contact
sheet of any timeline (`davin stills`), stills at a timecode (`davin still
--at`), auto-captions on any cut (`davin subtitles`), OTIO/EDL/AAF export
(`davin export`), scene-cut detection, marker sweeps. The full transcripts
have already been read end to end; ask "is there a moment where…" and the
answer comes with timecodes.
