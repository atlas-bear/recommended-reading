#!/usr/bin/env python3
"""Check the identifiers in data/library.yml against the registries.

For every ISBN-13, ask Open Library which work the edition belongs to and
compare it with the stored work key. For every DOI, ask Crossref (then
DataCite, which holds arXiv DOIs) whether it resolves. The script only reads;
it never rewrites the YAML.

    python scripts/verify.py                    # print a report
    python scripts/verify.py --report out.md    # also write it as Markdown

Exit codes: 0 all good; 1 a mismatch or a missing record (worth an issue);
2 the registries could not be reached (try again later, no issue).
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "library.yml"
UA = "atlas-bear-recommended-reading/2.0 (https://github.com/atlas-bear/recommended-reading; mailto:support@atlasbear.co)"
PAUSE = 1.0


class Unreachable(Exception):
    pass


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, None
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise Unreachable(f"{url}: HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise Unreachable(f"{url}: {e}")
    raise Unreachable(url)


def check_isbn(isbn, stored_work):
    status, ed = get_json(f"https://openlibrary.org/isbn/{isbn}.json")
    if status == 404 or ed is None:
        return f"ISBN {isbn}: not in Open Library"
    works = [w["key"].split("/")[-1] for w in ed.get("works", [])]
    if not stored_work:
        return None
    if stored_work in works:
        return None
    # the stored work may have been merged into another record
    time.sleep(PAUSE)
    status, work = get_json(f"https://openlibrary.org/works/{stored_work}.json")
    if work and work.get("type", {}).get("key") == "/type/redirect":
        target = work.get("location", "").split("/")[-1]
        if target in works:
            return None
    return f"ISBN {isbn}: Open Library work {works} does not match stored {stored_work}"


def check_doi(doi):
    status, d = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/") + "?mailto=support@atlasbear.co")
    if d and d.get("message", {}).get("DOI", "").lower() == doi.lower():
        return None
    time.sleep(PAUSE)
    status, d = get_json("https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="/"))
    if d and d.get("data", {}).get("id", "").lower() == doi.lower():
        return None
    return f"DOI {doi}: not found in Crossref or DataCite"


def main():
    with DATA.open(encoding="utf-8") as fh:
        items = yaml.safe_load(fh)["items"]
    problems, checked = [], 0
    try:
        for it in items:
            if it.get("isbn13"):
                checked += 1
                msg = check_isbn(str(it["isbn13"]).replace("-", ""), it.get("openlibrary"))
                if msg:
                    problems.append(f"{it['id']}: {msg}")
                time.sleep(PAUSE)
            if it.get("doi"):
                checked += 1
                msg = check_doi(it["doi"])
                if msg:
                    problems.append(f"{it['id']}: {msg}")
                time.sleep(PAUSE)
    except Unreachable as e:
        report(f"Could not reach a registry, so the check did not finish: {e}", [], checked)
        return 2
    report("Identifier check", problems, checked)
    return 1 if problems else 0


def report(title, problems, checked):
    lines = [f"## {title}", "", f"{checked} identifiers checked against Open Library, Crossref and DataCite."]
    if problems:
        lines += ["", "Problems:", ""] + [f"- {p}" for p in problems]
    else:
        lines += ["", "No problems found."]
    text = "\n".join(lines) + "\n"
    print(text)
    if "--report" in sys.argv:
        pathlib.Path(sys.argv[sys.argv.index("--report") + 1]).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
