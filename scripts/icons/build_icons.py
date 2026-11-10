"""Builds the word-picture assets from the hand-made maps (scripts/icons/map_*.txt: "<headword> <emoji>").

  * app/seed/word_icons.json   {headword: "<codepoint id>"}   read by the lecture slides
  * <frontend>/public/illus/<id>.svg   one small vector picture per id (Noto Emoji, Apache-2.0)

The pictures come from the @svgmoji/noto sprite sheet (npm); pass its all.svg and the frontend folder.
    python scripts/icons/build_icons.py <all.svg> <frontend>/public/illus
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent


def cp(e: str) -> str:
    return "-".join(f"{ord(c):04X}" for c in e)


def main(sprite: str, out_dir: str) -> None:
    sp = Path(sprite).read_text(encoding="utf8")
    starts = {m.group(1).upper(): m.start() for m in re.finditer(r'<svg\b[^>]*?\bid="([0-9A-Fa-f-]+)"[^>]*>', sp)}
    mapping: dict[str, str] = {}
    for f in sorted(glob.glob(str(HERE / "map_*.txt"))):
        for line in Path(f).read_text(encoding="utf8").splitlines():
            if not line.strip():
                continue
            word, emoji = line.rsplit(" ", 1)
            c = cp(emoji)
            hit = next((x for x in (c, c.replace("-FE0F", ""), c + "-FE0F") if x in starts), None)
            if hit is None:
                raise SystemExit(f"no picture for {word} {emoji} ({c})")
            mapping[word] = hit
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.svg"):
        old.unlink()
    for ident in sorted(set(mapping.values())):
        s = starts[ident]
        e = sp.index("</svg>", s) + len("</svg>")
        svg = sp[s:e]
        svg = re.sub(r'\s+id="[^"]*"', "", svg, count=1)
        svg = re.sub(r'\sxml:space="preserve"|\sstyle="enable-background:[^"]*"|\sx="0px"|\sy="0px"', "", svg)
        if "xlink:" in svg and "xmlns:xlink" not in svg:
            svg = svg.replace("<svg ", '<svg xmlns:xlink="http://www.w3.org/1999/xlink" ', 1)
        (out / f"{ident}.svg").write_text(svg, encoding="utf8")
    dest = HERE.parent.parent / "app" / "seed" / "word_icons.json"
    dest.write_text(json.dumps(dict(sorted(mapping.items())), ensure_ascii=False, indent=0) + "\n", encoding="utf8")
    sizes = [p.stat().st_size for p in out.glob("*.svg")]
    print(f"{len(mapping)} words, {len(sizes)} pictures, {sum(sizes)//1024} KB total, max {max(sizes)//1024} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
