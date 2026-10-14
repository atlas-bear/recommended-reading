# Changelog

All notable changes to this list are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/) loosely: a major version for a rebuild or a change to the data format, a minor version for each twice-yearly sweep, a patch for fixes between sweeps.

## [Unreleased]

### Changed

- The search box in the navigation bar now searches the whole Library: this site, the guide, the tools list, the reading list and the Library page, with results grouped by site and this site first. It uses the shared theme's search (v1.1.0) and an index the Library page publishes.
- Link previews: every page now carries Open Graph and Twitter card metadata with a description and a preview image in the AB//LABS style, and the favicon is the AB//LABS mark.
- The website moved to <https://library.ab-labs.io/recommended-reading/>. The old atlas-bear.github.io address redirects there, so existing links keep working.
- Ownership wording, contacts and names now reflect AB//LABS, which began as Atlas|Bear Labs and spun off from Atlas|Bear; the connection is explained in About. Copyright lines read AB//LABS (formerly Atlas|Bear Labs); contact is `support@ab-labs.io`.
- The website is now built with Quarto instead of MkDocs Material: the same generated pages, plus a Browse page (a filterable card grid of every title) and a References page rendered by Quarto's citation processor from the CSL JSON export. MkDocs was pinned to a version line that has stopped receiving updates.

## [2.0.0] - 2026-10-13

A rebuild. The list moved from prose bullets to a single data file with full citations, and gained a website, downloads for reference managers, and monthly checks of every identifier.

### Added

- `data/library.yml` as the single source, with authors in published order, publisher, year, edition, ISBN-13, DOI, Open Library work key, access status, section, "why read it" and "who it is for" for every title.
- A "Reports and papers" section: C4ADS's Oil and Water, the RUSI Maritime Sanctions Taskforce report on insurance and flag states, Europol's EU-SOCTA 2025, the Global Organized Crime Index 2025, the Berkeley Protocol on Digital Open Source Investigations, the UN AIS Handbook, Ogundoyin and colleagues on custom GPT security, Hütten on open AIS data in the Baltic, and the Allianz Safety and Shipping Review 2026.
- A "Start here" pick for each section.
- Chicago author-date citations generated for every entry, with the ISBN-13 or DOI, and titles linked to Open Library or the DOI rather than to a shop.
- Downloads: BibTeX, CSL JSON (for Zotero) and CSV, generated from the data file.
- A website at atlas-bear.github.io/recommended-reading built with MkDocs Material.
- Continuous checks: generated files match the data, the site builds, Markdown lints, links are checked on every pull request and monthly, and ISBNs and DOIs are checked against Open Library, Crossref and DataCite monthly.
- Written inclusion criteria, an issue form, a pull request template, a CITATION.cff and an MIT licence file (the README claimed one but the file was missing).

### Changed

- Corrected the Kaussler entry: the title and subtitle were swapped (it is *Rhetoric and Governance under Trump: Proclamations from the Bullshit Pulpit*) and the co-authors Lars J. Kristiansen and Jeffrey Delbert were missing.
- Bazzell's *OSINT Techniques* now cites the 11th edition (2024) and is marked as a rolling "latest edition" title.
- McFate's *The New Rules of War* cites the 2020 paperback, whose subtitle is *How America Can Win Against Russia, China, and Other Threats*.
- Hopkirk's *The Great Game* cites the John Murray edition, whose subtitle is *On Secret Service in High Asia*.
- Kapuściński's *The Shadow of the Sun* credits the translator, Klara Glowczewska.
- *Somalia: Economy without State* is marked hard to find.
- Sections reorganised: Financial crime and illicit networks; Global economics and politics; Geopolitics and strategy; OSINT and digital investigation; Reports and papers; Wider reading (for titles that are context rather than core).
- Descriptions rewritten in plain language.

## [1.1] - 2026-10-12

### Changed

- Ecosystem links: linked the osint-tools website, replaced the private mara link with mara-roadmap, removed the retired supply-chain-management-tools repository, and dated the community guidelines.

## [1.0] - 2025-07-15

### Added

- Related resources, the Atlas Bear ecosystem table and community guidelines.
- Descriptions for every title.

## [0.1] - 2024-07-15

### Added

- First public version of the list.
