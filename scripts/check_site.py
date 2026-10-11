#!/usr/bin/env python3
"""Check static links, accessibility basics, and promoted/negative publication state."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.duplicates: list[str] = []
        self.downloads: list[str] = []
        self.h1 = 0
        self.lang = None

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        a = dict(attributes)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if a.get("id"):
            if a["id"] in self.ids:
                self.duplicates.append(a["id"])
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if key in a and a[key]:
                self.links.append(a[key])
        if tag == "a" and "download" in a and a.get("href"):
            self.downloads.append(a["href"])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check() -> dict:
    problems: list[str] = []
    card = json.loads((DOCS / "data/run_card.json").read_text())
    source_card = json.loads((ROOT / "evidence/run_card.json").read_text())
    if card != source_card:
        problems.append("site run card differs from measured evidence")

    promoted = card.get("verdict") == "promote" and bool(card.get("download_allowed"))
    rasters = sorted([p for p in DOCS.rglob("*") if p.suffix.lower() in (".tif", ".tiff")])
    if promoted:
        sub_name = card.get("submission_name", "")
        z_tif = DOCS / "submissions" / f"{sub_name}-zeros.tif"
        n_tif = DOCS / "submissions" / f"{sub_name}-nan.tif"
        if not z_tif.is_file() or _sha256(z_tif) != card.get("raster_zeros_sha256"):
            problems.append("missing or mismatched primary -zeros.tif in docs/submissions/")
        if not n_tif.is_file() or _sha256(n_tif) != card.get("raster_nan_sha256"):
            problems.append("missing or mismatched companion -nan.tif in docs/submissions/")
    else:
        if rasters:
            problems.append("negative site contains TIFF files")

    pages: dict[Path, Parser] = {}
    approved_tiff_links = 0
    for path in sorted(DOCS.glob("*.html")):
        p = Parser()
        html_text = path.read_text()
        p.feed(html_text)
        pages[path.resolve()] = p
        if p.lang != "en" or p.h1 != 1:
            problems.append(f"{path}: language or heading hierarchy")
        if p.duplicates:
            problems.append(f"{path}: duplicate IDs {p.duplicates}")
        if promoted:
            if "CLEARED FOR DOWNLOAD &amp; SUBMISSION" not in html_text and "CLEARED FOR DOWNLOAD & SUBMISSION" not in html_text:
                problems.append(f"{path}: missing prominent CLEARED FOR DOWNLOAD & SUBMISSION banner")
            approved_tiff_links += sum(1 for d in p.downloads if d.endswith(".tif") or d.endswith(".zip"))
        else:
            if "NOT CLEARED FOR SUBMISSION" not in html_text:
                problems.append(f"{path}: missing prominent negative verdict")

    for path, p in pages.items():
        for link in p.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme not in ("https",):
                    problems.append(f"{path}: unexpected URL scheme {link}")
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not target.is_relative_to(DOCS.resolve()):
                problems.append(f"{path}: link escapes deployed site {link}")
            elif not target.exists():
                problems.append(f"{path}: missing {link}")
            elif parsed.fragment and target in pages and parsed.fragment not in pages[target].ids:
                problems.append(f"{path}: missing fragment {link}")
    if len(pages) != 4:
        problems.append("expected four main pages")

    return dict(
        ok=not problems,
        checked_pages=len(pages),
        problems=problems,
        approved_tiff_links=approved_tiff_links,
        production_tiffs=len(rasters),
    )


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
