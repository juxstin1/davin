"""Render cutlist.json + overlays.json as a readable paper cut (PAPERCUT.md):
episode timecode, source, and the transcript under every cut, with overlays
inline. Review the assembly without media.

    python productions/ma129/episode/paper_cut.py "MA129 episode assembly v4"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EP = Path(__file__).resolve().parent
MA = EP.parent
CAPTIONS = {
    5: MA / "day05" / "D5_CLIP_REEL.captions.json",
    6: MA / "MA129_CLIP_REEL.captions.json",
    7: MA / "day07" / "MA129_D7_CLIP_REEL.captions.json",
}
FPS = 30000 / 1001


def tc(sec: float) -> str:
    return f"{int(sec // 60):02d}:{sec % 60:04.1f}"


def main(title: str = "MA129 episode assembly v4"):
    cutlist = json.loads((EP / "cutlist.json").read_text(encoding="utf-8"))
    overlays = json.loads((EP / "overlays.json").read_text(encoding="utf-8"))["overlays"]
    caps = {d: json.loads(p.read_text(encoding="utf-8"))["captions"] for d, p in CAPTIONS.items()}

    by_seg = {}
    for ov in overlays:
        by_seg.setdefault((ov["at_label"], ov.get("occurrence", 1)), []).append(ov)

    out, cursor, count = [], 0.0, {}
    total = sum(round(s["end"] * FPS) - round(s["start"] * FPS)
                for sec in cutlist["sections"] for s in sec["segments"]) / FPS
    out.append(f"# {title} — paper cut\n")
    out.append(f"Runtime **{tc(total)}**, {sum(len(s['segments']) for s in cutlist['sections'])} cuts, "
               f"{len(overlays)} V2 overlays. Generated from `episode/cutlist.json` + `overlays.json` "
               "(regenerate after any edit). Text is raw ASR, so expect misheard words.\n")
    for sec in cutlist["sections"]:
        sec_len = sum(round(s["end"] * FPS) - round(s["start"] * FPS) for s in sec["segments"]) / FPS
        out.append(f"\n## {sec['name']} ({tc(sec_len)}, starts {tc(cursor)})\n")
        for seg in sec["segments"]:
            n = count[seg["label"]] = count.get(seg["label"], 0) + 1
            length = (round(seg["end"] * FPS) - round(seg["start"] * FPS)) / FPS
            src = seg.get("source", f"D{seg['day']} clip")
            out.append(f"**{tc(cursor)}** `{seg['label']}` · {src} {seg['start']:.2f}–{seg['end']:.2f} ({length:.1f}s)")
            if seg.get("source", "").endswith("broll"):
                out.append("> *(nat sound, no dialogue)*")
            else:
                text = " ".join(c["text"] for c in caps[seg["day"]]
                                if c["start"] < seg["end"] and c["end"] > seg["start"])
                out.append(f"> {text}")
            for ov in by_seg.get((seg["label"], n), []):
                out.append(f"  - ▣ V2 @ {tc(cursor + ov.get('offset', 0))} "
                           f"({ov['srcEnd'] - ov['srcStart']:.1f}s {ov['source']}): {ov.get('note', '')}")
            out.append("")
            cursor += length
    (EP / "PAPERCUT.md").write_text("\n".join(out), encoding="utf-8")
    print(f"{tc(total)} -> {EP / 'PAPERCUT.md'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
