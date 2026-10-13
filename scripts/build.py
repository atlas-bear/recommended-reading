#!/usr/bin/env python3
"""Build README.md, the list pages in docs/, and the exports from data/library.yml.

data/library.yml is the single source for the reading list. This script
validates it, then writes:

  README.md                      the whole list as one page for GitHub
  docs/index.md                  start page for the website
  docs/<section>.md              one page per section
  exports/reading-list.bib       BibTeX
  exports/reading-list.json      CSL JSON (imports straight into Zotero)
  exports/reading-list.csv       flat table

Run it after editing the YAML:

    python scripts/build.py          # rewrite everything
    python scripts/build.py --check  # exit 1 if any generated file is out of date

Nothing here depends on today's date, so running it twice gives identical output.
"""
import csv
import datetime as dt
import io
import json
import pathlib
import re
import sys
import unicodedata

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "library.yml"
DOCS = ROOT / "docs"
EXPORTS = ROOT / "exports"
README = ROOT / "README.md"

SECTIONS = [
    ("financial-crime", "Financial crime and illicit networks"),
    ("economics-politics", "Global economics and politics"),
    ("geopolitics", "Geopolitics and strategy"),
    ("osint", "OSINT and digital investigation"),
    ("reports", "Reports and papers"),
    ("wider-reading", "Wider reading"),
]
SECTION_TITLE = dict(SECTIONS)
TYPES = ("book", "report", "article", "document")
ACCESS = ("print", "open", "self-published", "out-of-print")
ACCESS_LABEL = {"open": "Open access.", "self-published": "Self-published.", "out-of-print": "Out of print or hard to find."}
CSL_TYPE = {"book": "book", "report": "report", "article": "article-journal", "document": "document"}
STRING_FIELDS_NO_DASH = ("publisher", "place", "journal", "audience", "why", "url", "archived", "access", "section")
GENERATED_NOTE = ("*This page is generated from [`data/library.yml`](https://github.com/atlas-bear/recommended-reading/blob/main/data/library.yml). "
                  "To propose a change, use the [issue form](https://github.com/atlas-bear/recommended-reading/issues/new/choose) "
                  "or open a pull request against that file.*")
HEADER = "<!-- GENERATED FILE. Do not edit by hand. Edit data/library.yml and run: python scripts/build.py -->\n\n"
CSV_COLUMNS = ["id", "type", "section", "title", "subtitle", "authors", "year", "publisher", "edition", "isbn13", "doi", "url", "access", "audience", "added", "last_checked"]


class BuildError(Exception):
    pass


# ---------- loading and validation ----------

def load():
    with DATA.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    items = data.get("items") or []
    errors = []
    seen_ids, seen_isbn, seen_doi, start = set(), set(), set(), {}
    tomorrow = dt.date.today() + dt.timedelta(days=1)
    for i, it in enumerate(items):
        where = f"items[{i}] ({it.get('id', '?')})"
        for k in ("id", "type", "title", "authors", "year", "section", "why", "added", "last_checked"):
            if it.get(k) in (None, "", []):
                errors.append(f"{where}: missing {k}")
        if not re.match(r"^[a-z0-9]+$", str(it.get("id", ""))):
            errors.append(f"{where}: id must match ^[a-z0-9]+$")
        if it.get("id") in seen_ids:
            errors.append(f"{where}: duplicate id")
        seen_ids.add(it.get("id"))
        if it.get("type") not in TYPES:
            errors.append(f"{where}: type must be one of {TYPES}")
        if it.get("section") not in SECTION_TITLE:
            errors.append(f"{where}: unknown section {it.get('section')!r}")
        for role in ("authors", "editors", "translators"):
            for p in it.get(role) or []:
                keys = set(p.keys()) if isinstance(p, dict) else set()
                if keys not in ({"family", "given"}, {"literal"}):
                    errors.append(f"{where}: {role} entries must be {{family, given}} or {{literal}}")
        year = it.get("year")
        if not isinstance(year, int):
            errors.append(f"{where}: year must be an integer")
        if it.get("original_year") is not None and not isinstance(it["original_year"], int):
            errors.append(f"{where}: original_year must be an integer")
        ed = it.get("edition")
        if ed is not None and (not isinstance(ed, int) or ed < 2):
            errors.append(f"{where}: edition must be an integer of 2 or more, or null")
        isbn = it.get("isbn13")
        if isbn is not None:
            digits = str(isbn).replace("-", "")
            if not re.match(r"^97[89]\d{10}$", digits) or not isbn_ok(digits):
                errors.append(f"{where}: isbn13 {isbn!r} is not a valid ISBN-13")
            if digits in seen_isbn:
                errors.append(f"{where}: duplicate ISBN")
            seen_isbn.add(digits)
        elif it.get("type") == "book" and not it.get("rolling") and not it.get("url"):
            errors.append(f"{where}: a book needs isbn13 unless rolling or url is set")
        doi = it.get("doi")
        if doi is not None:
            if not re.match(r"^10\.\d{4,9}/\S+$", str(doi)):
                errors.append(f"{where}: doi {doi!r} is not a bare DOI")
            if doi.lower() in seen_doi:
                errors.append(f"{where}: duplicate DOI")
            seen_doi.add(doi.lower())
        if it.get("openlibrary") is not None and not re.match(r"^OL\d+W$", str(it["openlibrary"])):
            errors.append(f"{where}: openlibrary must look like OL123W")
        if it.get("type") == "article" and not it.get("journal"):
            errors.append(f"{where}: an article needs journal")
        if it.get("type") in ("report", "document") and not (it.get("doi") or it.get("url")):
            errors.append(f"{where}: a report or document needs a doi or a url")
        if it.get("type") == "report" and not it.get("publisher"):
            errors.append(f"{where}: a report needs publisher (the issuing body)")
        if it.get("access", "print") not in ACCESS:
            errors.append(f"{where}: access must be one of {ACCESS}")
        for k in ("added", "last_checked", "accessed"):
            v = it.get(k)
            if v is None:
                continue
            d = v if isinstance(v, dt.date) else None
            if d is None:
                try:
                    d = dt.date.fromisoformat(str(v))
                except ValueError:
                    errors.append(f"{where}: {k} must be an ISO date")
                    continue
            if d > tomorrow:
                errors.append(f"{where}: {k} is in the future")
            it[k] = d.isoformat()
        for k in STRING_FIELDS_NO_DASH:
            if isinstance(it.get(k), str) and "—" in it[k]:
                errors.append(f"{where}: em dash in {k}")
        if it.get("start_here"):
            if it["section"] in start:
                errors.append(f"{where}: more than one start_here in section {it['section']}")
            start[it["section"]] = it["id"]
        it["why"] = " ".join(str(it.get("why", "")).split())
        if it.get("audience"):
            it["audience"] = " ".join(str(it["audience"]).split())
    if errors:
        raise BuildError("\n".join(errors))
    return items


def isbn_ok(digits):
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == int(digits[12])


# ---------- names and citations ----------

def person(p, inverted=False):
    if "literal" in p:
        return p["literal"]
    return f"{p['family']}, {p['given']}" if inverted else f"{p['given']} {p['family']}"


def name_list(people, inverted_first=True):
    """Chicago: first name inverted, the rest natural; 'and' before the last."""
    names = [person(p, inverted=(i == 0 and inverted_first)) for i, p in enumerate(people)]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def sort_key(it):
    first = it["authors"][0]
    s = first.get("literal") or first.get("family", "")
    s = re.sub(r"^(the|a|an)\s+", "", s, flags=re.I)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return (0 if it.get("start_here") else 1, s.casefold(), it["year"], it["title"].casefold())


def full_title(it):
    return it["title"] + (f": {it['subtitle']}" if it.get("subtitle") else "")


def isbn_digits(it):
    return str(it["isbn13"]).replace("-", "") if it.get("isbn13") else None


def link_target(it):
    if it.get("doi"):
        return f"https://doi.org/{it['doi']}"
    if it.get("type") == "book" and it.get("isbn13"):
        return f"https://openlibrary.org/isbn/{isbn_digits(it)}"
    return it.get("url") or ""


def citation(it):
    """Chicago 18th author-date reference, as one line."""
    names = name_list(it["authors"])
    parts = [names if names.endswith(".") else names + "."]
    year = f"({it['original_year']}) {it['year']}" if it.get("original_year") else str(it["year"])
    parts.append(year + ".")
    title = full_title(it)
    if it["type"] == "article":
        parts.append(f"“{title}.”")
        j = f"*{it['journal']}*"
        if it.get("volume"):
            j += f" {it['volume']}"
            if it.get("issue"):
                j += f" ({it['issue']})"
        if it.get("page_range"):
            j += f": {it['page_range']}"
        parts.append(j + ".")
    else:
        parts.append(f"*{title}*.")
    if it.get("edition"):
        parts.append(f"{ordinal(it['edition'])} ed.")
    if it.get("editors"):
        parts.append("Edited by " + name_list(it["editors"], inverted_first=False) + ".")
    if it.get("translators"):
        parts.append("Translated by " + name_list(it["translators"], inverted_first=False) + ".")
    if it["type"] == "report" and it.get("number"):
        parts.append(f"Report {it['number']}.")
    if it["type"] != "article" and it.get("publisher"):
        parts.append(f"{it['publisher']}.")
    if it.get("isbn13"):
        parts.append(f"ISBN {it['isbn13']}.")
    if it.get("doi"):
        parts.append(f"<https://doi.org/{it['doi']}>.")
    elif it.get("url"):
        parts.append(f"<{it['url']}>.")
    if it.get("access", "print") != "print":
        parts.append(ACCESS_LABEL[it["access"]])
    if it.get("rolling"):
        parts.append("Latest edition recommended; we review it each year.")
    return " ".join(parts)


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def entry_md(it):
    title = full_title(it)
    target = link_target(it)
    head = f"**[{title}]({target})**" if target else f"**{title}**"
    tail = f"**Why read it:** {it['why']}"
    if it.get("audience"):
        tail += f" **Who it is for:** {it['audience']}."
    return f"- <a id=\"{it['id']}\"></a>{head}<br>\n  {citation(it)}<br>\n  {tail}"


# ---------- pages ----------

def section_body(items, key):
    rows = sorted((it for it in items if it["section"] == key), key=sort_key)
    if not rows:
        return "", None
    body = "\n".join(entry_md(it) for it in rows)
    latest = max(it["last_checked"] for it in rows)
    return body, latest


def front_matter(title, description=None):
    fm = f"---\ntitle: \"{title}\"\n"
    if description:
        fm += f"description: \"{description}\"\n"
    return fm + "---\n\n"


def section_page(items, key, title, intro):
    body, latest = section_body(items, key)
    return (front_matter(title) + HEADER
            + f"{intro}\n\n{GENERATED_NOTE}\n\n{body}\n\n*Last checked {latest}.*\n")


SECTION_INTROS = {
    "financial-crime": "How dirty money moves, who moves it and why the system lets them. Start with the one marked first; it is the shortest route into the subject.",
    "economics-politics": "The wider economy that illicit trade lives inside: offshore finance, informal markets and states that work differently from the textbook.",
    "geopolitics": "The strategic background for the places and conflicts that keep turning up in our work.",
    "osint": "Method books for finding and checking information in the open. Method moves fast, so we cite the latest edition and review these every year.",
    "reports": "Reports and papers we hand to people when a book is too slow. Each has a DOI or a stable address, and most are free to read.",
    "wider-reading": "Books that are not about illicit trade but that we keep recommending anyway, because of what they teach about places, people or power.",
}


def index_body(items):
    picks = [it for it in sorted(items, key=sort_key) if it.get("start_here")]
    lines = []
    for key, title in SECTIONS:
        rows = [it for it in picks if it["section"] == key]
        if rows:
            it = rows[0]
            lines.append(f"- **{title}**: [{full_title(it)}]({key}.md#{it['id']}), {name_list(it['authors'])} ({it['year']}).")
    picks_md = "\n".join(lines)
    counts = {key: sum(1 for it in items if it["section"] == key) for key, _ in SECTIONS}
    toc = "\n".join(f"- [{title}]({key}.md) ({counts[key]})" for key, title in SECTIONS if counts[key])
    return f"""![Titles](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fatlas-bear%2Frecommended-reading%2Fmain%2Fexports%2Freading-list.json&query=%24.length&label=titles&color=blue)
![Check list](https://github.com/atlas-bear/recommended-reading/actions/workflows/check.yml/badge.svg)
![Check links](https://github.com/atlas-bear/recommended-reading/actions/workflows/links.yml/badge.svg)
![Verify identifiers](https://github.com/atlas-bear/recommended-reading/actions/workflows/verify.yml/badge.svg)
![License](https://img.shields.io/github/license/atlas-bear/recommended-reading)

> Part of the [Library](https://atlas-bear.github.io/), by AB//LABS. Read this list as a website at [atlas-bear.github.io/recommended-reading](https://atlas-bear.github.io/recommended-reading/), or take it into your reference manager: [BibTeX](https://github.com/atlas-bear/recommended-reading/blob/main/exports/reading-list.bib), [CSL JSON](https://github.com/atlas-bear/recommended-reading/blob/main/exports/reading-list.json) (imports straight into Zotero) or [CSV](https://github.com/atlas-bear/recommended-reading/blob/main/exports/reading-list.csv).

**Related resources:**

- [Maritime and Supply Chain OSINT Tools](https://github.com/atlas-bear/osint-tools): the tools and data sources we use, also as a [website](https://atlas-bear.github.io/osint-tools/).
- [AI-Enhanced OSINT](https://github.com/atlas-bear/osint-ai-guide): our guide to using AI in intelligence work, also as a [website](https://atlas-bear.github.io/osint-ai-guide/).
- [Atlas|Bear Academy](https://www.atlasbear.academy): professional development programmes from Atlas|Bear, the company we spun off from.

---

These are the books, reports and papers we recommend to people who work on illicit trade: analysts, investigators, journalists, students at the Summer School on Illicit Trade, and colleagues who ask us where to start. Every entry carries a full citation, an ISBN or DOI, and a few sentences on why it is worth your time and who it suits.

The list is short on purpose and it is not exhaustive. If a title you rely on is missing, please [propose it](contributing.md). We reply to every proposal.

## Start here

One pick per section if you only have time for one.

{picks_md}

## Sections

{toc}

## How to read an entry

Each entry gives the title (linked to the edition we recommend on Open Library, or to the DOI), a citation in Chicago author-date style with the ISBN-13 or DOI, then **Why read it** and **Who it is for**. A note at the end marks titles that are open access, self-published, or out of print and hard to find. Where we cite a reissue or translation, the first year in brackets is the original.

## How this list is maintained

The list lives in one data file, `data/library.yml`. A script builds this page, the website and the downloads from it, and checks every ISBN against Open Library and every DOI against Crossref or DataCite once a month. We sweep the whole list twice a year with our other lists, re-check editions, and record changes in the [CHANGELOG](https://github.com/atlas-bear/recommended-reading/blob/main/CHANGELOG.md). Each sweep ends with a GitHub release.
"""


def index_page(items):
    return (front_matter("Recommended Reading",
                         "Books, reports and papers for intelligence professionals working on illicit trade, with full citations.")
            + HEADER + index_body(items))


def include_page(path):
    """A hand-written docs page as a README section: front-matter title becomes an H2."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\ntitle: \"([^\"]+)\"\n(?:.*?\n)*?---\n", text, re.S)
    title = m.group(1) if m else path.stem.title()
    body = text[m.end():] if m else text
    body = re.sub(r"^(#{1,5}) ", lambda h: "#" + h.group(1) + " ", body, flags=re.M)   # one level down under the H2
    return f"## {title}\n\n{body.strip()}"


# ---------- README ----------

def readme(items):
    out = ["# Recommended Reading\n\n" + index_body(items).replace("(contributing.md)", "(#contributing)").strip()]
    # section links in the index point at pages; in the README they point at headings
    out[0] = re.sub(r"\]\(([a-z-]+)\.md#([^)]+)\)", r"](#\2)", out[0])
    out[0] = re.sub(r"\]\(([a-z-]+)\.md\)", lambda m: "](#" + slug(SECTION_TITLE[m.group(1)]) + ")", out[0])
    for key, title in SECTIONS:
        body, latest = section_body(items, key)
        if body:
            out.append(f"## {title}\n\n{SECTION_INTROS[key]}\n\n{body}\n\n*Last checked {latest}.*")
    out.append(include_page(DOCS / "contributing.md"))
    out.append(include_page(DOCS / "about.md"))
    text = "\n\n---\n\n".join(out) + "\n"
    text = text.replace("](https://github.com/atlas-bear/recommended-reading/blob/main/", "](")
    return text


def slug(heading):
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s", "-", s)


# ---------- exports ----------

def bib_escape(s):
    return re.sub(r"([&%$#_])", r"\\\1", str(s))


def bib_names(people):
    out = []
    for p in people:
        if "literal" in p:
            out.append("{" + bib_escape(p["literal"]) + "}")
        else:
            out.append(f"{bib_escape(p['family'])}, {bib_escape(p['given'])}")
    return " and ".join(out)


def bibtex(items):
    kinds = {"book": "book", "report": "techreport", "article": "article", "document": "misc"}
    entries = []
    for it in sorted(items, key=lambda x: x["id"]):
        f = []
        f.append(("author", bib_names(it["authors"])))
        if it.get("editors"):
            f.append(("editor", bib_names(it["editors"])))
        f.append(("title", "{" + bib_escape(full_title(it)) + "}"))
        f.append(("year", str(it["year"])))
        if it["type"] == "article":
            f.append(("journal", bib_escape(it["journal"])))
            for k in ("volume", "issue", "page_range"):
                if it.get(k):
                    f.append(({"page_range": "pages"}.get(k, k), bib_escape(str(it[k]).replace("-", "--") if k == "page_range" else it[k])))
        elif it["type"] == "report":
            f.append(("institution", bib_escape(it["publisher"])))
            f.append(("type", "Report"))
            if it.get("number"):
                f.append(("number", bib_escape(it["number"])))
        else:
            if it.get("publisher"):
                f.append(("publisher", bib_escape(it["publisher"])))
            if it.get("place"):
                f.append(("address", bib_escape(it["place"])))
        if it.get("edition"):
            f.append(("edition", str(it["edition"])))
        if it.get("isbn13"):
            f.append(("isbn", isbn_digits(it)))
        if it.get("doi"):
            f.append(("doi", it["doi"]))
        if it.get("url"):
            f.append(("url", it["url"]))
        if it["type"] == "document" and it.get("url"):
            f.append(("howpublished", "\\url{" + it["url"] + "}"))
        notes = []
        if it.get("translators"):
            notes.append("Translated by " + name_list(it["translators"], inverted_first=False))
        if it.get("original_year"):
            notes.append(f"First published {it['original_year']}")
        if notes:
            f.append(("note", bib_escape(". ".join(notes))))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f)
        entries.append(f"@{kinds[it['type']]}{{{it['id']},\n{body}\n}}")
    return "% Recommended Reading, by AB//LABS. Generated from data/library.yml; do not edit by hand.\n% UTF-8. Use biber or a UTF-8 aware BibTeX, or import into Zotero.\n\n" + "\n\n".join(entries) + "\n"


def csl_person(p):
    return {"literal": p["literal"]} if "literal" in p else {"family": p["family"], "given": p["given"]}


def csl_json(items):
    out = []
    for it in sorted(items, key=lambda x: x["id"]):
        d = {"id": it["id"], "type": CSL_TYPE[it["type"]], "title": full_title(it),
             "author": [csl_person(p) for p in it["authors"]], "issued": {"date-parts": [[it["year"]]]}}
        if it.get("editors"):
            d["editor"] = [csl_person(p) for p in it["editors"]]
        if it.get("translators"):
            d["translator"] = [csl_person(p) for p in it["translators"]]
        if it.get("original_year"):
            d["original-date"] = {"date-parts": [[it["original_year"]]]}
        if it.get("publisher"):
            d["publisher"] = it["publisher"]
        if it.get("place"):
            d["publisher-place"] = it["place"]
        if it.get("edition"):
            d["edition"] = str(it["edition"])
        if it.get("isbn13"):
            d["ISBN"] = isbn_digits(it)
        if it.get("doi"):
            d["DOI"] = it["doi"]
        if it.get("url"):
            d["URL"] = it["url"]
        if it.get("journal"):
            d["container-title"] = it["journal"]
        for k, ck in (("volume", "volume"), ("issue", "issue"), ("page_range", "page"), ("number", "number"), ("pages", "number-of-pages")):
            if it.get(k):
                d[ck] = str(it[k])
        if it.get("accessed"):
            y, m, day = (int(x) for x in it["accessed"].split("-"))
            d["accessed"] = {"date-parts": [[y, m, day]]}
        d["abstract"] = it["why"]
        out.append(d)
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def csv_text(items):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    for it in sorted(items, key=lambda x: x["id"]):
        row = []
        for k in CSV_COLUMNS:
            if k == "authors":
                row.append("; ".join(person(p) for p in it["authors"]))
            else:
                v = it.get(k)
                row.append("" if v is None else str(v))
        w.writerow(row)
    return buf.getvalue()


def listing_yaml(items):
    """Items for the Browse page: a Quarto listing rendered as a card grid."""
    rows = []
    for it in sorted(items, key=lambda x: (x["section"], sort_key(x))):
        rows.append({
            "title": full_title(it),
            "subtitle": f"{name_list(it['authors'])}, {it['year']}",
            "description": it["why"],
            "path": f"{it['section']}.html#{it['id']}",
            "categories": [SECTION_TITLE[it["section"]], it["type"].capitalize()],
        })
    return ("# GENERATED FILE. Do not edit by hand. Edit data/library.yml and run: python scripts/build.py\n"
            + yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=1000))


# ---------- main ----------

def outputs(items):
    files = {README: readme(items), DOCS / "index.md": index_page(items),
             EXPORTS / "reading-list.bib": bibtex(items), EXPORTS / "reading-list.json": csl_json(items),
             EXPORTS / "reading-list.csv": csv_text(items), DOCS / "listing.yml": listing_yaml(items)}
    for key, title in SECTIONS:
        if any(it["section"] == key for it in items):
            files[DOCS / f"{key}.md"] = section_page(items, key, title, SECTION_INTROS[key])
    return files


def main():
    try:
        items = load()
        files = outputs(items)
    except BuildError as err:
        print(f"build failed:\n{err}", file=sys.stderr)
        return 1
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, want in files.items()
                 if not p.exists() or p.open(encoding="utf-8", newline="").read() != want]
        if stale:
            print(f"out of date: {', '.join(stale)}. Run: python scripts/build.py", file=sys.stderr)
            return 1
        print(f"README, docs and exports match data/library.yml ({len(items)} titles)")
        return 0
    for p, want in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8", newline="") as fh:
            fh.write(want)
    print(f"wrote {len(files)} files ({len(items)} titles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
