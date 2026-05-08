# Anki Census

Anki Census is an Anki Desktop add-on that provides a local user analytics dashboard and, during semester census windows, sends privacy-conscious aggregated data to a public API.

The project has two layers:

1. **My Anki**: a local dashboard with collection metrics, recent activity, FSRS usage, media stats, add-on insights, and (when available) community comparisons.
2. **Anki Census**: a semester census that tracks aggregate Anki usage and add-on adoption patterns across the global community.

Author: **Danyel Barboza - Anki Community**

---

## Overview

The **My Anki** screen summarizes local usage, including:

- approximate card, note, deck, tag, and note-type counts
- recent review activity
- retention over recent windows
- study-day consistency
- FSRS adoption
- answer-button distribution (`Again`, `Hard`, `Good`, `Easy`)
- media footprint and composition
- installed add-ons
- wrapped-style profile generated from aggregate signals
- community comparisons when enough public responses exist

---

## Project Structure

```text
addon/      Anki Desktop add-on
worker/     Cloudflare Worker API + Cloudflare D1 database
scripts/    Add-on packaging scripts
privacy.md  Privacy policy
```

Data dictionary file:

```text
dicionario-dados-anki-census.ods
```

---

## Version Requirement

- Anki Desktop **24.06+**
- Windows, macOS, Linux

---

## Collection Windows

The census runs twice a year:

```text
06/01 to 06/10
12/10 to 12/20
```

Survey ID examples:

```text
anki-census-2026-1
anki-census-2026-2
```

During active windows, one submission is sent per local user/profile if participation is not paused.

---

## Data Sent

The add-on sends aggregate technical signals, such as:

- Anki version and OS
- add-on list (technical metadata)
- collection size buckets
- FSRS and scheduling buckets
- review activity buckets
- optional profile fields
- aggregate fingerprint for deduplication support

Most numeric values are bucketed.

---

## Data Not Sent

Anki Census does **not** send:

- card content
- note content
- deck/tag/field/note-type names
- media files or media file names
- email
- real name
- AnkiWeb login
- local collection file paths

See [privacy.md](privacy.md).

---

## Backend

The backend uses:

- Cloudflare Worker
- Cloudflare D1
- HTTP endpoints
- payload validation
- separate tables for production and debug submissions

Public endpoints:

```text
GET  /config
POST /submit
POST /debug-submit
GET  /results
GET  /results.html
```

---

## Deploy Backend

```bash
cd worker
npm install
npx wrangler login
npm run db:create
npm run db:init
npm run deploy
```

Keep the current D1 database name unchanged for compatibility:

```toml
database_name = "censo-anki-brasil-db"
```

---

## Configure API URL

In add-on UI:

```text
Tools -> Anki Census -> Settings -> API URL
```

Or at build time:

```bash
python scripts/build_addon.py --api-url "https://anki-census-api.YOURSUBDOMAIN.workers.dev"
```

---

## Embedding Client

Anki Census includes a reusable embedded client module for other add-ons:

- folder: `addon/anki_census/censo_client`
- docs: `docs/EMBEDDING_CENSO_CLIENT.md`

### Add-ons Embedding Anki Census Client

The following add-ons currently ship with the embedded `censo_client` module:

1. Dynamic Deadline New Cards (`anki-dynamic-deadline`)

These add-ons reuse shared global runtime/config state so end users do not need manual setup.

---

## New Repository

Official repository:

- [https://github.com/danyelbarboza/anki-census](https://github.com/danyelbarboza/anki-census)

This project started as Censo Anki Brasil and is now evolving as Anki Census with backward-compatible migration behavior.
