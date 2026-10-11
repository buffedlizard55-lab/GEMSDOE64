#!/usr/bin/env python3
"""Check static links, accessibility basics, and verified publication state."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from gems64.promotion import lane64_promotion_decision

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.duplicates, self.downloads = [], set(), [], []
        self.h1 = 0
        self.lang = None

    def handle_starttag(self, tag, attributes):
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
            if key in a:
                self.links.append(a[key])
        if tag == "a" and "download" in a:
            self.downloads.append(a.get("href"))


def check() -> dict:
    problems = []
    card = json.loads((DOCS / "data/run_card.json").read_text())
    source_card = json.loads((ROOT / "evidence/run_card.json").read_text())
    if card != source_card:
        problems.append("site run card differs from measured evidence")

    decision = lane64_promotion_decision(card)
    if decision["verdict"] != card.get("verdict") or decision["download_allowed"] != card.get("download_allowed"):
        problems.append(f"promotion policy mismatch: {decision}")

    promoted = card.get("verdict") == "promote" and card.get("download_allowed") is True
    allowed_downloads = {"data/run_card.json"}
    if promoted:
        for k, sha_k in [
            ("download_url_tif", "raster_sha256"),
            ("download_url_zip", "zip_sha256"),
            ("download_url_nan_tif", "nan_outside_raster_sha256"),
        ]:
            rel = card.get(k)
            if not rel:
                problems.append(f"missing {k} in promoted run_card")
                continue
            allowed_downloads.add(rel)
            f_path = DOCS / rel
            if not f_path.exists():
                problems.append(f"missing promoted download file {f_path}")
            elif sha256_file(f_path) != card.get(sha_k):
                problems.append(f"sha256 mismatch on {f_path}")
    else:
        rasters = [p for p in DOCS.rglob("*") if p.suffix.lower() in (".tif", ".tiff", ".zip")]
        if rasters:
            problems.append("negative site contains TIFF/ZIP files")

    pages = {}
    approved_tiff_links = 0
    for path in DOCS.glob("*.html"):
        p = Parser()
        text = path.read_text()
        p.feed(text)
        pages[path.resolve()] = p
        if p.lang != "en" or p.h1 != 1:
            problems.append(f"{path}: language or heading hierarchy")
        if p.duplicates:
            problems.append(f"{path}: duplicate IDs {p.duplicates}")
        for dl in p.downloads:
            if dl not in allowed_downloads:
                problems.append(f"{path}: unauthorized download link {dl}")
            if dl and dl.endswith(".tif"):
                approved_tiff_links += 1
        expected_banner = "CLEARED FOR SUBMISSION" if promoted else "NOT CLEARED FOR SUBMISSION"
        if expected_banner not in text:
            problems.append(f"{path}: missing prominent verdict banner ({expected_banner})")

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
    prod_tiffs = len(list((DOCS / "downloads").glob("*.tif"))) if (DOCS / "downloads").exists() else 0
    return dict(
        ok=not problems,
        checked_pages=len(pages),
        problems=problems,
        verdict=card.get("verdict"),
        approved_tiff_links=approved_tiff_links,
        production_tiffs=prod_tiffs,
    )


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
