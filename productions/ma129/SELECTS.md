# MA129 Music Group — Selects (Day 6)

**Current: `MA129 selects v3`** (21.6 min — v2 minus nomination language per
EP note: `trish-touched` now starts at "The beautiful pins from Neville",
past "Gail making the nomination / part of this production"; earlier versions
kept for diffing). 34 selects from 145.9 min of dailies. Timeline
in project `DASH-DAY06-MA129`, one beat-colored marker per select (Yellow 3.1 /
Green 3.2 / Red 3.3 / Purple 3.4 / Sky INT-Trish / Rose INT-Gail). Ordered as a
rough assembly, not reel order. Full timecodes + quotes in `selects.json`.

**Scope note:** Day 6 covers **Act 3 + interviews** only. Act 1 (shop) and
Act 2 (first gesture at the rehearsal — referenced repeatedly as "yesterday" /
"the other day") live on other shoot days.

## The spine

- **3.1 build-up (Gail, A-05):** "criers on our hands" → family/lasting-reminder
  → "they have no idea" → thesis: *"sometimes just a song or an act of kindness
  can change someone's life"* (clean pickup at 20:04).
- **3.2 Trish one-on-one (A-01, circled take @ 05:08):** "It's us" · "You
  actually made this? I've been practicing" · takes the brooch off for the big
  reveal. Plus the **B-04 clean line**: *"It's kind of coming home… this is like
  a celebration"* (garbled on A-cam).
- **3.3 group reveal (A-03 for scene, A-04 for speech):** floral-jewelry intro,
  the pinning comedy ("been a while since a man had his hand in my shirt" /
  "never in my wildest dreams"), the emotional peak ("my heart's just full —
  mine is too"), Neville's clean "Music is food for the soul" monologue from
  the A-04 pass, group hug, two buttons ("What a bunch of dolls", "I think they
  like them. There's that. Thank goodness").
- **3.4 concert + close (A-09/10/11/12):** venue intro → Trish's onstage origin
  (90 minutes → two hours → weekly) → This Little Light of Mine → **the mom
  story onstage** (Alzheimer's, toe tapping, "our dream") → "two chords →
  hundreds of songs" → thanks → Neville's goodbye ("it was so much more than a
  good job… the man spelling out the words, not always to the right song").
- **INT Trish (A-15):** "full circle" · "it feeds us" · "I hadn't heard my name
  in ten years, but she could still relate to the music" · "I am so lucky to
  have Gail in my life" (clean pickup) · closer thesis: *"what you think is
  something small is huge to somebody else."*
- **INT Gail (A-16):** soul sister · the 11:11 angel-hours story · unsung
  heroes · "people feel forgotten, we need to value our seniors" · button:
  *"there's nothing wrong with being mushy"* (clean pickup).

## Rights flags (performed on camera)

| Song | Status |
| --- | --- |
| This Little Light of Mine | traditional — safe (selected) |
| Michael, Row the Boat Ashore | traditional — safe (not selected) |
| Five Foot Two, Eyes of Blue | 1925 composition — likely safe (not selected) |
| Bring Me Sunshine (1966) | **flag** — floor audio literally says "we can't use this song" |
| Eight Days a Week (Beatles, closer) | **flag** — almost certainly unclearable (not selected) |
| Peaceful Easy Feeling fragment (B-31) | **flag** — Eagles (not selected) |

## Alternates

Every A-cam select has a CAM B twin for angle cuts (B-04≈A-01, B-08≈A-03,
B-09≈A-04, B-10≈A-05, B-29≈A-09, B-30≈A-10, B-39≈A-12, B-46≈A-15, B-47≈A-16 —
exact reel offsets in the boundary markers on `MA129 clip reel`). B-42 has
Five Foot Two pickups with **brooch close-ups** for inserts.

## Veto / adjust

Edit `selects.json` (drop an entry, nudge start/end), then:

```powershell
uv run python ..\ma129\build_selects.py   # rebuilds as "MA129 selects v1 2"
```
