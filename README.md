# OpenLib – Digital Public Library & Book Exchange Platform

> **"One Platform. Four Generations. Unlimited Knowledge."**

OpenLib is a full-stack Python Flask web application designed to make verified public-domain, open-access, and community-shared books freely discoverable across four generations: **Children (5–12)**, **Youth (13–24)**, **Adults (25–59)**, and **Senior Citizens (60+)**.

---

## Key Features

- **Four Generation-Based Libraries**: Tailored browsing experiences across 40 curated categories (10 per generation) with live database counts.
- **420+ Verified Books Catalogue**: Sourced exclusively from legitimate repositories (Project Gutenberg, Internet Archive, Open Library, Wikisource) with full copyright, licence, ISBN/year, and original source URL verification.
- **Integrated Online Reader (PDF.js + Built-in Text Reader)**:
  - Native PDF.js canvas rendering for local authorized open-licensed PDFs and whitelisted CORS-safe open PDFs
  - Previous/Next page, Jump to Page, Zoom In/Out/Fit Width, Fullscreen, Night Mode, Adjustable Font Size
  - Persistent Reading Progress and Page Bookmarks
  - Built-in Web Speech API Text-to-Speech (especially helpful for Seniors and accessibility)
- **Advanced Search & Filtering**: Search across title, author, ISBN, keywords, and description with live suggestions, multi-facet filters, sorting, and pagination.
- **Borrowing, Book Exchange & Donation Systems**:
  - 14-day member borrowing with renewals and returns
  - Peer-to-peer Community Book Exchange Hub for listing and swapping physical copies
  - Digital & Physical Book Donation workflow with librarian review
- **Administrator Dashboard**: Full CRUD for books (with Pillow cover optimization & PDF validation), JSON/CSV catalogue import with duplicate detection & metadata/URL validation, catalogue reports, donation moderation, user role management, and contact inbox.
- **Accessibility First**: Global Large Text, High Contrast, Night Mode, and Text-to-Speech support.

---

## Tech Stack

- **Backend**: Python 3.13, Flask, Flask-Login, Flask-WTF, Flask-SQLAlchemy, Flask-Migrate, Werkzeug, Pillow
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons, PDF.js (v3.11.174 bundled locally)
- **Database**: SQLite (development/testing) with SQLAlchemy ORM ready for PostgreSQL on Render

---

## Quick Start

1. **Create & activate virtual environment**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment (optional)**
   Copy `.env.example` to `.env` and adjust `SECRET_KEY`, `DATABASE_URL`, and `ADMIN_PASSWORD`.
4. **Run the application**
   ```bash
   python run.py
   ```
   Open `http://127.0.0.1:5000` in your browser.

---

## Default Accounts (Seeded Automatically in Development)

- **Administrator**: `admin@openlib.org` (or username `admin`) / `AdminSecure@2024`
- **Member Reader**: `reader@openlib.org` (or username `reader`) / `ReaderPass@2024`

*(Change default passwords via `.env` before deploying to production.)*

---

## Deployment on Render

This repository includes `Procfile` and `render.yaml`. Set `SECRET_KEY`, `DATABASE_URL` (PostgreSQL), `FLASK_ENV=production`, and `ADMIN_PASSWORD` in Render environment variables. Start command:
```bash
gunicorn run:app
```

