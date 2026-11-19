# MA129 Music Therapy — Day 7 Selects (Act 1: Discovery in the Shop)

**Status: selects written, timeline NOT built.** The 2026-11-19 Drive drop
contained only the B-roll reels; `MA129_CLIP_REEL.mp4` is missing. Once it's in
`Downloads\Making Arrangements\Day 07\MA129\`:

```
uv run python productions/stage_drop.py "<drop>/Day 07/MA129" --project DASH-MA129 --label "MA129 D7" --work productions/ma129/day07
uv run python productions/ma129/day07/build_selects.py      # -> "MA129 D7 selects v1"
```

14 selects, 8.7 min from 52.1 min of dailies (17%; CAM B is twin coverage, so
it's ~33% of the unique 26 min). Marker colors: Lavender 1.1 / Yellow 1.2 /
Mint 1.4. Timecodes + quotes are in `selects.json`, and every in-point sits on a
caption start (no backward pads). Validated: no range crosses a source-clip
boundary and no crew speech falls inside a range.

**This fills the known gap.** EDITOR_HANDOFF item 2 ("No shop footage, Act 1
beats 1.1/1.4 exist in neither drop") is answered by this day. The v3 assembly
opens without the shop, and these selects are the material for Act 1.

## Scope vs the beat sheet / DCP

| Beat | Day 7 coverage |
| --- | --- |
| 1.1 Shop Work | Yes. Neville with the orchids (A-01) plus B-roll of him pulling carnations. The DCP's "David notices the pieces could be shared by a group" was **not shot**. |
| 1.2 The Story Enters | Yes, in 5 takes. David takes Gail's call and brings Neville over. |
| 1.3 The Need Becomes Clear | **Not shot here.** The director cut it on the floor ("we don't really need too much more info than that", A-01 @92.4). The mom/dementia need lives on D5 (`gail-lightsup`, `music-medicine`) and D6 (`trish-mom`). |
| 1.4 First Gesture | Yes, and it's the best material of the day. Neville builds the carnation treble clef and explains it to David (A-07), then leaves with the piece (A-09 + B-roll departure). |

No interviews on this day. No performed music, so nothing needs rights
clearance. Listen for a shop radio under A-07 before locking.

## The spine

- **1.1 `orchids` (A-01 12.8):** "Look at you, beautiful thing... all you want
  to do is bloom... all beautiful families, all from different places, but
  they're all shining individually and together." B-01 has the clean ASR of
  the same take; the A-cam transcript drops half the lines.
- **1.2 the call:** `call-smashing` (A-02 316.3). David hangs up with Gail: "we
  gotta come up with something pretty smashing." This is the only on-camera
  "Gail". Then `trish-named` (A-01 take 2 @120.4) is **the only take that names
  Trish and Gail's ask together**: "they want to celebrate the person that
  started the group, named Trish. And so Gail just called and asked if we could
  do something special for her." It covers the Must-Have "Gail's ask and the
  reason Trish is being recognized."
- **1.2 Neville takes it on:** `ukulele-punch` (A-04 485.3, the circled take,
  shot after the floor correction): "a ukulele is a simple, diminutive little
  instrument that can pack a lot of punch and a lot of color and a lot of
  power, and carnations do the same thing... I'm gonna surprise them all."
  Outros: `share-love-bcam` (B-03 2271.1). This has the thesis-ish line "we get
  to share love through the beauty of flowers and music"; ASR garbles it on A,
  and a boom reset was called right after this take, so use B-cam. Then
  `dance-outro` (A-04 787.8, the last take, director: "That felt good").
- **1.4 the build (A-07, one continuous take):** `popcorn-string` ("remember
  stringing popcorn for Christmas?") → `try-one` ("I am many things; a florist
  is not one") → `bad-relationship` ("carnations will hang on like a bad
  relationship... get over it, they're beautiful... they play with everyone")
  → `treble-clef` (the comedy peak: "What's that squiggly thing?" / "That's
  exactly where I was going with that... I'm so smart with these words now...
  too lazy and a little proud") → `dance-curl` ("so they'll dance... Gail's
  gonna flip when she sees this") → `not-just-a-carnation` ("This is not just a
  carnation. This is a dance... moving with the vibrations of the music").
- **1.4 exit:** `finished-piece` (A-09 1426.4: "Look at you. You're absolutely
  beautiful... here's some tea for you") → `found-something` (A-09 1442.7:
  "Honey, I found something else that's gotta go with this... on the way over
  to the event... You can have my tea... Bye, doll"). The 1434–1442 gap between
  them holds an uncertain aside ("How'd it go that time, Charlie" / "Sorry, I'm
  just"). Listen before closing it. Cut to B-roll `B-10` / `A-10` (door → SUV).

## Continuity across days (new)

- **`found-something` → D5 `surprise` (1284.8):** "It's not a new ukulele, but
  it's still played." The thing Neville runs off to get is the ukulele. This is
  the cleanest setup→payoff in the episode. Keep both.
- **`treble-clef` → D6 A-01 59.92–76.4 (B twin 4263.3):** at the brooch reveal,
  Neville says "These spirals remind you of the treble clef... I wasn't sure
  what the clef is." It's a callback to the shop joke. **Used in assembly v4**,
  via the circled take's version inside `trish-reveal` (D6 343.08: "It
  almost reminds me of a treble clef. / And it kind of brings a what? / A
  treble clef. / That's exactly what I was gonna think").
- **`orchids` → `dance-outro` ("see you later, orchids") → A-08/A-09 tea:**
  small runners that make the shop feel lived-in. David's tea pays off in
  `found-something` ("You can have my tea").

## Floor notes worth knowing

- A-02's take was **stopped for wrong facts**. David said "pastels / Hawaiian";
  Neville: "it's not pastels at all... it ain't the Hawaiian thing, it's
  carnations" (A-02 380–395). A-03 is the director confirming "lose the Hawaiian
  element". Never use A-02 past 344.8, and use A-01 take 2 only up to 147.8
  (it says "Hawaii" at 170).
- A-04 take 3 (754.9) was stopped because Neville said Gail is "from
  Newfoundland". She isn't; David corrects him on camera. Don't use.

## Alternates (A↔B twins)

B-01≈A-01 (+1569.1s), B-02≈A-02 (+1527.0), B-03≈A-03+A-04 (+1575.6 / +1607.7;
B-03 rolled through), B-06≈A-06, B-07≈A-07 (+1541.0), B-08≈A-08 (+1545.8),
B-09≈A-09 (+1552.7), B-11≈A-11 (+1559.0). A-05, A-06 and A-11 (and their B
twins) are **picture-only inserts** with no dialogue: "keep it tight, no
moving" (A-05) suggests hand close-ups of the build. They're the first thing to
check for 1.4 cutaways once the reel lands.

## B-roll (logged from stills: `broll_log\d7_log.json`)

- Shop B-roll, overcast: B-04/B-05 Neville pulling carnations and stems
  (cutaways for 1.1/1.4); A-10/B-10 departure, door no. 2086 → SUV (Act 1 out).
- **Establishing Shots group (Day 7, its own folder):** "My Mother's Bloomers"
  signboard (B-17/18), wide corner with flags (B-03/B-04 = the DCP's "wide shop
  establisher"), comic signs ("Don't Pee On Me" B-08, "Dog urine kills plants"
  B-16), a Neville poster in the window (B-21). ⚠ These are **sunny** and the
  shop day is **overcast**. Use them for an episode-open establisher, not
  intercut with the departure.
