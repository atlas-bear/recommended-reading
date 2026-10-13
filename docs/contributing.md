---
title: "Contributing"
description: "How to propose a title and the format every entry follows."
---

Know a book, report or paper that belongs here? Please tell us. The easiest route is the [issue form](https://github.com/atlas-bear/recommended-reading/issues/new/choose), which needs no YAML. If you prefer a pull request, add a block to `data/library.yml` in the format below. We reply to every proposal, whether or not we add the title.

## What earns a place

A title goes on the list when:

1. It helps someone work on illicit trade, or on the economics, politics, places and methods around it. The "Wider reading" section exists for the second kind.
2. Someone at AB//LABS has read it. We do not list on reputation.
3. It can be obtained: in print, through a library or publisher subscription, or free online. Out-of-print titles stay only when there is no replacement, and are marked.
4. It has a full citation: authors in published order, publisher, year, and an ISBN-13 for the edition we recommend, or a DOI or stable address for papers and reports.
5. It adds something the list does not already have. Two books on the same subject need a reason.

Authors and publishers are welcome to propose their own work if they say so. We treat those proposals exactly like any other and read the work before deciding.

## The entry format

Every title is one block in `data/library.yml`. The fields are explained in the comment at the top of that file. A book looks like this:

```yaml
  - id: shelley2020
    type: book
    title: Dark Commerce
    subtitle: How a New Illicit Economy Is Threatening Our Future
    authors:
      - {family: Shelley, given: Louise I.}
    original_year: 2018
    publisher: Princeton University Press
    place: Princeton
    year: 2020
    isbn13: "9780691209760"
    doi: "10.1515/9780691184296"
    openlibrary: OL20186908W
    access: print
    section: financial-crime
    audience: anyone who needs the big picture of illicit trade in one book
    why: >
      Two or three plain sentences on what the book does and why it matters for this work.
    added: 2025-07-12
    last_checked: 2026-10-13
```

A few rules keep the list consistent:

- **Cite the edition you recommend.** The ISBN-13 is the one printed in that edition; the year is that edition's year, with `original_year` for the first publication if it differs. For method books that are rewritten often, set `rolling: true` and we will cite whatever edition is current.
- **Organisations are authors too.** Write `{literal: "Europol"}` for a corporate author.
- **Reports and papers** need a DOI where one exists, otherwise the publisher's stable address, and `access: open` if anyone can read them for free.
- **The "why" is plain.** Two or three sentences in ordinary words about what the reader gets, tied to illicit trade work. No marketing language and no em dashes. **The "audience"** is one short line.
- **No retailer links.** Titles link to Open Library or to the DOI. We do not use affiliate links, prices or ratings.

## Generated files

`README.md`, the list pages in `docs/`, and the files in `exports/` are built from `data/library.yml` by `scripts/build.py`. Please do not edit them directly; the check on every pull request will fail if they differ from the YAML. If you can run Python, run the script and commit everything it changes. If not, tick "Allow edits by maintainers" and we will regenerate on your branch.

```bash
pip install pyyaml
python scripts/build.py          # rebuild README, docs and exports
python scripts/build.py --check  # what CI runs
python scripts/verify.py         # check ISBNs and DOIs against the registries (network)
```

If you keep candidates in Zotero, export them as CSL JSON and run `python scripts/import_zotero.py export.json` to get draft YAML blocks with the citation details filled in; you add the section, the "why" and the "audience" lines.

The build checks every ISBN's check digit, the shape of every DOI, duplicate identifiers and the required fields. Once a month a workflow checks each ISBN against Open Library and each DOI against Crossref or DataCite, and opens an issue if something no longer resolves.

## Reviews and releases

We sweep the whole list twice a year with our other lists, in spring before the [Summer School on Illicit Trade](https://www.rug.nl/education/summer-winter-schools/illicit-trade) and again in autumn: editions, availability and whether each title still earns its place. Each sweep ends with a release and a [CHANGELOG](https://github.com/atlas-bear/recommended-reading/blob/main/CHANGELOG.md) entry. Please keep to our [community guidelines](https://github.com/atlas-bear/recommended-reading/blob/main/COMMUNITY_GUIDELINES.md) in issues and pull requests.
