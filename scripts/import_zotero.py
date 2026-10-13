#!/usr/bin/env python3
"""Turn a CSL JSON export from Zotero into draft entries for data/library.yml.

Collect titles in Zotero, export the collection as CSL JSON (File > Export
Library or right-click a collection > Export, format "CSL JSON"), then:

    python scripts/import_zotero.py export.json            # print draft YAML blocks
    python scripts/import_zotero.py export.json --lookup   # also fill the Open Library work key by ISBN (network)

Paste the blocks into data/library.yml, pick the section, write the "why" and
"audience" lines, and run scripts/build.py. The script never edits the YAML
itself. Titles already in the list (same ISBN or DOI) are skipped.
"""
import json
import pathlib
import re
import sys
import time
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "library.yml"
TYPES = {"book": "book", "report": "report", "article-journal": "article", "paper-conference": "article"}
UA = "atlas-bear-recommended-reading/2.0 (https://github.com/atlas-bear/recommended-reading; mailto:support@ab-labs.io)"


def q(s):
    return json.dumps(str(s), ensure_ascii=False)


def person(p):
    if "literal" in p:
        return f'      - {{literal: {q(p["literal"])}}}'
    return f'      - {{family: {q(p.get("family", ""))}, given: {q(p.get("given", ""))}}}'


def work_key(isbn):
    req = urllib.request.Request(f"https://openlibrary.org/isbn/{isbn}.json", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        works = d.get("works", [])
        return works[0]["key"].split("/")[-1] if works else None
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    items = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    lookup = "--lookup" in sys.argv
    with DATA.open(encoding="utf-8") as fh:
        existing = yaml.safe_load(fh)["items"]
    known_isbn = {str(e["isbn13"]).replace("-", "") for e in existing if e.get("isbn13")}
    known_doi = {e["doi"].lower() for e in existing if e.get("doi")}
    known_title = {((str(e["title"]) + (": " + str(e["subtitle"]) if e.get("subtitle") else "")).casefold(), e.get("year")) for e in existing}
    blocks = []
    for it in items:
        isbn = (it.get("ISBN") or "").split()[0].replace("-", "") if it.get("ISBN") else None
        doi = it.get("DOI")
        title, _, subtitle = (it.get("title") or "Untitled").partition(": ")
        year = (it.get("issued") or {}).get("date-parts", [[None]])[0][0]
        if (isbn and isbn in known_isbn) or (doi and doi.lower() in known_doi) or ((it.get("title") or "").casefold(), year) in known_title:
            continue
        authors = it.get("author") or [{"literal": it.get("publisher") or "Unknown"}]
        first = authors[0].get("family") or authors[0].get("literal", "x").split()[0]
        ident = re.sub(r"[^a-z0-9]", "", f"{first}{year or ''}".lower()) or "newitem"
        typ = TYPES.get(it.get("type"), "document")
        lines = [f"  - id: {ident}", f"    type: {typ}", f"    title: {q(title)}"]
        if subtitle:
            lines.append(f"    subtitle: {q(subtitle)}")
        lines.append("    authors:")
        lines += [person(p) for p in authors]
        for role, key in (("editor", "editors"), ("translator", "translators")):
            if it.get(role):
                lines.append(f"    {key}:")
                lines += [person(p) for p in it[role]]
        if it.get("edition") and str(it["edition"]).strip("stndrh ").isdigit():
            lines.append(f"    edition: {int(str(it['edition']).strip('stndrh '))}")
        if it.get("publisher"):
            lines.append(f"    publisher: {q(it['publisher'])}")
        if it.get("publisher-place"):
            lines.append(f"    place: {q(it['publisher-place'])}")
        lines.append(f"    year: {year or 'FILL'}")
        if typ == "article" and it.get("container-title"):
            lines.append(f"    journal: {q(it['container-title'])}")
            for k, ck in (("volume", "volume"), ("issue", "issue"), ("page", "page_range")):
                if it.get(k):
                    lines.append(f"    {ck}: {q(it[k])}")
        if isbn:
            lines.append(f'    isbn13: "{isbn}"')
            if lookup:
                wk = work_key(isbn)
                time.sleep(1)
                if wk:
                    lines.append(f"    openlibrary: {wk}")
        if doi:
            lines.append(f'    doi: "{doi}"')
        if it.get("URL"):
            lines.append(f"    url: {it['URL']}")
        if it.get("number-of-pages"):
            lines.append(f"    pages: {it['number-of-pages']}")
        lines.append("    access: " + ("open" if it.get("URL") and not isbn else "print"))
        lines.append("    section: financial-crime   # choose: financial-crime | economics-politics | geopolitics | osint | reports | wider-reading")
        lines.append("    audience: FILL")
        lines.append("    why: >")
        lines.append("      " + (" ".join(str(it.get("abstract", "")).split()) or "FILL: two or three plain sentences."))
        today = time.strftime("%Y-%m-%d")
        lines.append(f"    added: {today}")
        lines.append(f"    last_checked: {today}")
        blocks.append("\n".join(lines))
    if not blocks:
        print("# nothing new: every item is already in data/library.yml", file=sys.stderr)
        return 0
    print("# Draft entries from Zotero. Paste under items: in data/library.yml, fill FILL, pick the section, then run scripts/build.py\n")
    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
