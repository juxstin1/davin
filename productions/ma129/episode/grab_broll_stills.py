"""Export 2 stills per b-roll source clip (30% / 70%) for visual logging."""

from __future__ import annotations

import csv
from pathlib import Path

from davin.client import DavinClient

OUT = Path(r"C:\Users\juxxs\Desktop\davin\ma129\broll_log\stills")
DAYS = {
    5: (
        Path(r"C:\Users\juxxs\Downloads\MA129-Music Therapy-20260723T214044Z-1-001"
             r"\MA129-Music Therapy\BROLL_REEL_manifest.tsv"),
        "MA129 D5 broll reel",
    ),
    6: (
        Path(r"C:\Users\juxxs\Downloads\drive-download-20260723T211350Z-1-001"
             r"\BROLL_REEL_manifest.tsv"),
        "MA129 broll reel",
    ),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    client = DavinClient.connect()
    client.ensure_project("DASH-MA129")
    count = 0
    for day, (manifest, timeline_name) in DAYS.items():
        client.get_timeline(timeline_name)
        at = 0.0
        with manifest.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        for row in rows:
            dur = float(row["duration_seconds"])
            short = row["filename"].split("-CAM ")[-1].replace(" ", "")
            for pct in (0.3, 0.7):
                path = OUT / f"d{day}_{short}_{int(pct * 100)}.png"
                try:
                    client.export_still(path, at_seconds=at + dur * pct)
                    count += 1
                except Exception as exc:
                    print(f"skip {path.name}: {exc}")
            at += dur
        print(f"day {day}: {len(rows)} clips done")
    print(f"{count} stills -> {OUT}")


if __name__ == "__main__":
    main()
