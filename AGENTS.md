# AGENTS.md – OpenLib Engineering & Architecture Guidelines

## Overview
**OpenLib** is a full-stack Flask web application for a free digital public library and community book exchange platform serving four generations (`Children`, `Youth`, `Adults`, `Seniors`).

## Architecture Rules
- **Modular Structure**: Keep Flask models in `app/models/`, routes/blueprints in `app/routes/`, forms in `app/forms/`, business/catalogue services in `app/services/`, and shared helpers/decorators in `app/utils/`.
- **Database Portability**: Write all queries with SQLAlchemy ORM (`app/models/`) so SQLite (dev/testing) and PostgreSQL (production on Render) behave identically.
- **No Fabricated Catalogue Data**: Every book added via `data/catalogue/`, Admin UI, or donations must originate from legitimate open repositories (Project Gutenberg, Internet Archive, Open Library, Wikisource, StoryWeaver, DOAB, OpenStax) with verified `source_url`, `copyright_status`, and `licence` metadata.
- **Download & Redistribution Respect**: Never enable `is_downloadable` or `redistribution_permitted` unless the book's licence explicitly permits it. Otherwise link to the official reading or Controlled Digital Lending page.
- **Counts Integrity**: Always display exact live counts from SQLAlchemy queries; never hardcode book totals.

## Common Commands
- Run dev server: `.venv\Scripts\python.exe run.py`
- Run test suite: `.venv\Scripts\python.exe -m pytest`
- Curate/verify catalogue: `.venv\Scripts\python.exe app/services/curate_catalogue.py`

