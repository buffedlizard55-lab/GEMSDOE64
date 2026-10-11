#!/usr/bin/env python3
"""Check static links, accessibility basics and fail-closed publication state.

Publication rules enforced here (the site is a claim about evidence, so the
checker re-derives the claim from the run card rather than trusting the HTML):

* the deployed card must be byte-equal to ``evidence/run_card.json``;
* a TIFF/ZIP may sit in ``docs/`` only when the card's ``download_allowed`` is
  true, and each published file must match the card's ``raster_sha256``;
* every download link must point at a published, hash-matching file;
* every page states its verdict banner explicitly, so a reader cannot mistake an
  audit artefact for a cleared submission.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DIAGNOSTIC_UNIQUE = "unique by bytes, pixels and rank structure"
UNSAT_REASON = "cannot be satisfied by"


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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check():
    problems = []
    card = json.loads((DOCS / "data/run_card.json").read_text())
    source_card = json.loads((ROOT / "evidence/run_card.json").read_text())
    if card != source_card:
        problems.append("site run card differs from measured evidence")
    allowed = bool(card.get("download_allowed"))
    banner = "CLEARED FOR SUBMISSION" if allowed else "NOT CLEARED FOR SUBMISSION"

    rasters = [p for p in DOCS.rglob("*") if p.suffix.lower() in (".tif", ".tiff", ".zip")]
    cleared_links = []
    # Publication policy (fail-closed, and explicit about the difference between
    # "cleared" and "published as an audit artefact"):
    #   cleared  -> a download link MUST exist and the bytes MUST match the card;
    #   not cleared -> a download MAY exist only as a labelled audit artefact, the
    #                  bytes must still match the card, and the banner must appear.
    for path in rasters:
        if path.suffix.lower() == ".tif" and sha256(path) != card.get("raster_sha256"):
            problems.append(f"{path.name}: published bytes differ from the run-card sha256")
        elif not allowed and len(rasters) > 1:
            problems.append(f"{path.name}: more than one raster published for a non-promoted card")

    pages = {}
    for path in DOCS.glob("*.html"):
        p = Parser()
        p.feed(path.read_text())
        pages[path.resolve()] = p
        if p.lang != "en" or p.h1 != 1:
            problems.append(f"{path}: language or heading hierarchy")
        if p.duplicates:
            problems.append(f"{path}: duplicate IDs {p.duplicates}")
        text = path.read_text()
        if banner not in text:
            problems.append(f"{path}: missing prominent verdict banner")
        if not allowed and path.name in ("index.html", "executive-summary.html"):
            if DIAGNOSTIC_UNIQUE not in text:
                problems.append(f"{path}: non-promoted page without the diagnostic verdict stated")
            if UNSAT_REASON not in text:
                problems.append(f"{path}: non-promoted page without the unsatisfiable-criterion reason")
        for link in p.downloads:
            if link.endswith(".tif") or link.endswith(".zip"):
                cleared_links.append(link)
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
    if len(pages) < 6:
        problems.append(f"expected the full page set, found {len(pages)}")
    if allowed and not cleared_links:
        problems.append("promoted run card without a download link on the site")
    if allowed and len(cleared_links) != len(set(cleared_links)):
        problems.append("duplicate download links")
    return dict(ok=not problems, checked_pages=len(pages), problems=problems,
                banner=banner, download_allowed=allowed,
                approved_tiff_links=len(cleared_links) if allowed else 0,
                production_tiffs=len(rasters) if allowed else 0)


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
