"""Catalogue Management Service: JSON/CSV import, validation, deduplication, and reporting."""
import csv
import io
import json
import os
import re
from datetime import datetime
from urllib.request import Request, urlopen

from app import db
from app.models.book import AgeGroup, Category, Book
from app.utils.helpers import is_valid_http_url, normalize_isbn, slugify


REQUIRED_BOOK_FIELDS = ('title', 'author', 'age_group', 'category', 'language', 'source_url', 'licence')

CATEGORY_TARGETS = {
    'children': {
        'Moral Stories': 15,
        'Fairy Tales': 10,
        'Panchatantra Stories': 10,
        'Adventure Stories': 10,
        'Science for Kids': 10,
        'Picture Books': 10,
        'Educational Books': 10,
        'General Knowledge': 10,
        'Bedtime Stories': 10,
        'Folktales': 10,
    },
    'youth': {
        'Programming and Computer Science': 15,
        'Science and Mathematics': 10,
        'Competitive Exam Preparation': 10,
        'Self-Improvement': 10,
        'Entrepreneurship': 10,
        'Career Guidance': 10,
        'Fiction and Novels': 10,
        'Technology': 10,
        'Psychology': 10,
        'Biographies': 10,
    },
    'adults': {
        'Business and Entrepreneurship': 15,
        'Personal Finance': 10,
        'Literature and Novels': 10,
        'History and Culture': 10,
        'Science and Technology': 10,
        'Psychology': 10,
        'Health and Wellness': 10,
        'Personal Development': 10,
        'Parenting': 10,
        'Biographies': 10,
    },
    'seniors': {
        'Spirituality and Philosophy': 15,
        'History and Culture': 10,
        'Classic Literature': 10,
        'Biographies': 10,
        'Health and Wellness': 10,
        'Devotional Literature': 10,
        'Poetry': 10,
        'Short Stories': 10,
        'Gardening and Hobbies': 10,
        'Large-Print Books': 10,
    },
}


def _normalize_text(val):
    if not val:
        return ''
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', str(val).lower())).strip()


def _parse_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if val is None or val == '':
        return default
    return str(val).strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def _parse_int(val, default=None):
    if val is None or val == '':
        return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def validate_book_metadata(record, verify_urls=True):
    """Validate a single book metadata dict. Returns (is_valid, errors_list)."""
    errors = []

    for field in REQUIRED_BOOK_FIELDS:
        if not str(record.get(field) or '').strip():
            errors.append(f"Missing required field: '{field}'")

    title = str(record.get('title') or '').strip()
    if title and len(title) > 300:
        errors.append('Title exceeds 300 characters.')

    if verify_urls:
        source_url = str(record.get('source_url') or '').strip()
        if source_url and not is_valid_http_url(source_url):
            errors.append(f"Invalid source_url: '{source_url}'")

        reading_url = str(record.get('reading_url') or '').strip()
        if reading_url and not reading_url.startswith('/') and not is_valid_http_url(reading_url):
            errors.append(f"Invalid reading_url: '{reading_url}'")

        download_url = str(record.get('download_url') or '').strip()
        if download_url and not download_url.startswith('/') and not is_valid_http_url(download_url):
            errors.append(f"Invalid download_url: '{download_url}'")

        licence_url = str(record.get('licence_url') or '').strip()
        if licence_url and not is_valid_http_url(licence_url):
            errors.append(f"Invalid licence_url: '{licence_url}'")

    pub_year = _parse_int(record.get('publication_year'))
    if record.get('publication_year') not in (None, '') and pub_year is None:
        errors.append('publication_year must be an integer.')
    elif pub_year is not None and (pub_year < 500 or pub_year > datetime.utcnow().year + 1):
        errors.append(f'publication_year {pub_year} is out of valid range.')

    min_age = _parse_int(record.get('min_age'), 0)
    max_age = _parse_int(record.get('max_age'), 99)
    if min_age < 0 or max_age > 120 or min_age > max_age:
        errors.append(f'Invalid recommended age range ({min_age}-{max_age}).')

    return len(errors) == 0, errors


def check_live_url(url, timeout=8):
    """Perform an HTTP HEAD/GET check on a source URL."""
    if not is_valid_http_url(url):
        return False, 'Invalid URL syntax'
    headers = {'User-Agent': 'OpenLibCatalogueVerifier/1.0'}
    for method in ('HEAD', 'GET'):
        try:
            req = Request(url, headers=headers, method=method)
            with urlopen(req, timeout=timeout) as resp:
                return 200 <= resp.status < 400, f'HTTP {resp.status}'
        except Exception as exc:
            last_err = str(exc)
    return False, last_err


def find_duplicate_book(record):
    """Detect duplicates by ISBN, source_url, gutenberg_id, or normalized (title, author)."""
    isbn = normalize_isbn(record.get('isbn'))
    if isbn:
        match = Book.query.filter_by(isbn=isbn).first()
        if match:
            return match, 'isbn'

    source_url = (record.get('source_url') or '').strip()
    if source_url:
        match = Book.query.filter_by(source_url=source_url).first()
        if match:
            return match, 'source_url'

    gutenberg_id = str(record.get('gutenberg_id') or '').strip()
    if gutenberg_id:
        match = Book.query.filter_by(gutenberg_id=gutenberg_id).first()
        if match:
            return match, 'gutenberg_id'

    norm_title = _normalize_text(record.get('title'))
    norm_author = _normalize_text(record.get('author'))
    if norm_title and norm_author:
        candidates = Book.query.filter(
            db.func.lower(Book.title) == str(record.get('title')).strip().lower()
        ).all()
        for c in candidates:
            if _normalize_text(c.author) == norm_author:
                return c, 'title_author'

    return None, None


def _resolve_age_group(age_group_val):
    if not age_group_val:
        return None
    val = str(age_group_val).strip().lower()
    mapping = {
        'children': 'children', "children's": 'children', 'child': 'children', 'kids': 'children',
        'youth': 'youth', 'teen': 'youth', 'young adult': 'youth',
        'adults': 'adults', 'adult': 'adults',
        'seniors': 'seniors', 'senior': 'seniors', 'senior citizens': 'seniors',
    }
    target_slug = mapping.get(val, slugify(val))
    return AgeGroup.query.filter(
        db.or_(AgeGroup.slug == target_slug, db.func.lower(AgeGroup.name) == val)
    ).first()


def _resolve_or_create_category(cat_name, age_group):
    name = str(cat_name).strip()
    slug = f"{age_group.slug}-{slugify(name)}" if age_group else slugify(name)
    category = Category.query.filter_by(slug=slug).first()
    if category:
        return category

    # Also match case-insensitively within the same age_group
    if age_group:
        category = Category.query.filter(
            Category.age_group_id == age_group.id,
            db.func.lower(Category.name) == name.lower()
        ).first()
        if category:
            return category

    category = Category(
        name=name,
        slug=slug,
        description=f'{name} collection for {age_group.display_name if age_group else "all readers"}.',
        icon='bi-book',
        age_group_id=age_group.id if age_group else None,
        is_active=True,
    )
    db.session.add(category)
    db.session.flush()
    return category


def _apply_record_to_book(book, record, age_group, category):
    book.title = str(record['title']).strip()[:300]
    book.author = str(record['author']).strip()[:200]
    book.description = str(record.get('description') or f"{book.title} by {book.author}.").strip()
    book.cover_image = str(record.get('cover_image') or 'default_cover.svg').strip()
    book.age_group_id = age_group.id
    book.category_id = category.id
    book.min_age = _parse_int(record.get('min_age'), age_group.min_age or 0)
    book.max_age = _parse_int(record.get('max_age'), age_group.max_age or 99)
    book.language = str(record.get('language') or 'English').strip()
    book.language_code = str(record.get('language_code') or book.language[:2].lower()).strip()
    book.publisher = str(record.get('publisher') or '').strip() or None
    book.publication_year = _parse_int(record.get('publication_year'))
    book.isbn = normalize_isbn(record.get('isbn'))
    book.pages = _parse_int(record.get('pages'))
    book.edition = str(record.get('edition') or '').strip() or None
    book.file_format = str(record.get('file_format') or 'PDF/HTML').strip()
    book.file_size = str(record.get('file_size') or '').strip() or None
    book.local_file_path = str(record.get('local_file_path') or '').strip() or None
    book.reading_url = str(record.get('reading_url') or record.get('source_url') or '').strip()
    book.download_url = str(record.get('download_url') or '').strip() or None
    book.source_url = str(record.get('source_url') or '').strip()
    book.source_repository = str(record.get('source_repository') or 'Verified Open Repository').strip()
    book.gutenberg_id = str(record.get('gutenberg_id') or '').strip() or None
    book.is_readable_online = _parse_bool(record.get('is_readable_online'), True)
    book.is_downloadable = _parse_bool(record.get('is_downloadable'), False)
    book.redistribution_permitted = _parse_bool(record.get('redistribution_permitted'), False)
    book.is_borrowable = _parse_bool(record.get('is_borrowable'), True)
    book.is_exchangeable = _parse_bool(record.get('is_exchangeable'), False)
    book.copyright_status = str(record.get('copyright_status') or 'Public Domain').strip()
    book.licence = str(record.get('licence') or 'Public Domain').strip()
    book.licence_url = str(record.get('licence_url') or '').strip() or None
    book.licence_verified = _parse_bool(record.get('licence_verified'), True)
    book.licence_verified_at = datetime.utcnow()
    book.verification_notes = str(record.get('verification_notes') or '').strip() or None
    book.is_featured = _parse_bool(record.get('is_featured'), False)
    book.is_verified = _parse_bool(record.get('is_verified'), True)
    book.is_active = _parse_bool(record.get('is_active'), True)
    book.tags = str(record.get('tags') or '').strip()


def import_from_records(records, update_duplicates=False, verify_urls=True):
    """Import a list of book dicts with validation and duplicate detection."""
    report = {
        'total_processed': 0,
        'imported': 0,
        'updated': 0,
        'skipped_duplicates': 0,
        'errors': [],
    }

    for idx, raw in enumerate(records, start=1):
        report['total_processed'] += 1
        record = {k.strip(): v for k, v in raw.items()} if isinstance(raw, dict) else {}

        is_valid, errs = validate_book_metadata(record, verify_urls=verify_urls)
        if not is_valid:
            report['errors'].append({'row': idx, 'title': record.get('title', 'Unknown'), 'errors': errs})
            continue

        age_group = _resolve_age_group(record.get('age_group'))
        if not age_group:
            report['errors'].append({
                'row': idx,
                'title': record.get('title', 'Unknown'),
                'errors': [f"Unknown age_group '{record.get('age_group')}'"]
            })
            continue

        existing, dup_reason = find_duplicate_book(record)
        if existing:
            if update_duplicates:
                category = _resolve_or_create_category(record.get('category'), age_group)
                _apply_record_to_book(existing, record, age_group, category)
                report['updated'] += 1
            else:
                report['skipped_duplicates'] += 1
            continue

        category = _resolve_or_create_category(record.get('category'), age_group)
        book = Book()
        _apply_record_to_book(book, record, age_group, category)
        db.session.add(book)
        db.session.flush()
        if not book.book_code:
            book.book_code = f'OL-{book.id:05d}'
        report['imported'] += 1

    db.session.commit()
    return report


def import_json_data(json_text, update_duplicates=False, verify_urls=True):
    """Parse JSON string/bytes and import books."""
    payload = json.loads(json_text)
    if isinstance(payload, dict) and 'books' in payload:
        records = payload['books']
    elif isinstance(payload, list):
        records = payload
    else:
        raise ValueError('JSON must be a list of book objects or an object with a "books" array.')
    return import_from_records(records, update_duplicates=update_duplicates, verify_urls=verify_urls)


def import_csv_data(csv_text, update_duplicates=False, verify_urls=True):
    """Parse CSV text and import books."""
    reader = csv.DictReader(io.StringIO(csv_text))
    records = [row for row in reader]
    return import_from_records(records, update_duplicates=update_duplicates, verify_urls=verify_urls)


def export_catalogue_json():
    """Export all active verified books as formatted JSON string."""
    books = Book.query.filter_by(is_active=True).order_by(Book.id).all()
    return json.dumps({'total': len(books), 'books': [b.to_dict() for b in books]}, indent=2, ensure_ascii=False)


def export_catalogue_csv():
    """Export all active verified books as CSV string."""
    books = Book.query.filter_by(is_active=True).order_by(Book.id).all()
    output = io.StringIO()
    fieldnames = [
        'book_code', 'title', 'author', 'description', 'age_group', 'min_age', 'max_age',
        'category', 'language', 'publication_year', 'publisher', 'isbn', 'file_format',
        'reading_url', 'local_file_path', 'source_url', 'source_repository',
        'copyright_status', 'licence', 'licence_url', 'is_readable_online',
        'is_downloadable', 'redistribution_permitted', 'licence_verified', 'date_added'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for b in books:
        d = b.to_dict()
        writer.writerow({k: d.get(k, '') for k in fieldnames})
    return output.getvalue()


def generate_catalogue_report():
    """Generate a comprehensive, real-DB-backed catalogue audit report."""
    total_active = Book.query.filter_by(is_active=True).count()
    total_verified = Book.query.filter_by(is_active=True, is_verified=True).count()
    licence_verified_count = Book.query.filter_by(is_active=True, licence_verified=True).count()
    readable_online_count = Book.query.filter_by(is_active=True, is_readable_online=True).count()
    downloadable_count = Book.query.filter_by(is_active=True, is_downloadable=True).count()
    local_pdf_count = Book.query.filter(Book.is_active == True, Book.local_file_path != None, Book.local_file_path != '').count()
    missing_isbn_count = Book.query.filter(Book.is_active == True, db.or_(Book.isbn == None, Book.isbn == '')).count()
    invalid_url_books = []

    for b in Book.query.filter_by(is_active=True).all():
        if not is_valid_http_url(b.source_url or ''):
            invalid_url_books.append({'id': b.id, 'title': b.title, 'source_url': b.source_url})

    age_group_stats = []
    for ag in AgeGroup.query.order_by(AgeGroup.sort_order).all():
        count = ag.get_book_count()
        cat_rows = []
        targets = CATEGORY_TARGETS.get(ag.slug, {})
        for cat in ag.categories.order_by(Category.sort_order, Category.name).all():
            c_count = cat.get_book_count()
            target = targets.get(cat.name, 10)
            cat_rows.append({
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'count': c_count,
                'target': target,
                'meets_target': c_count >= target,
            })
        age_group_stats.append({
            'name': ag.name,
            'display_name': ag.display_name,
            'slug': ag.slug,
            'count': count,
            'target': 105,
            'meets_target': count >= 105,
            'categories': cat_rows,
        })

    by_language = db.session.query(Book.language, db.func.count(Book.id)).filter(
        Book.is_active == True, Book.is_verified == True
    ).group_by(Book.language).order_by(db.func.count(Book.id).desc()).all()

    by_repository = db.session.query(Book.source_repository, db.func.count(Book.id)).filter(
        Book.is_active == True, Book.is_verified == True
    ).group_by(Book.source_repository).order_by(db.func.count(Book.id).desc()).all()

    by_copyright = db.session.query(Book.copyright_status, db.func.count(Book.id)).filter(
        Book.is_active == True, Book.is_verified == True
    ).group_by(Book.copyright_status).order_by(db.func.count(Book.id).desc()).all()

    return {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'total_active': total_active,
        'total_verified': total_verified,
        'meets_400_target': total_verified >= 400,
        'licence_verified_count': licence_verified_count,
        'readable_online_count': readable_online_count,
        'downloadable_count': downloadable_count,
        'local_pdf_count': local_pdf_count,
        'missing_isbn_count': missing_isbn_count,
        'invalid_url_count': len(invalid_url_books),
        'invalid_url_books': invalid_url_books[:20],
        'age_groups': age_group_stats,
        'by_language': [{'language': lang or 'Unknown', 'count': cnt} for lang, cnt in by_language],
        'by_repository': [{'repository': repo or 'Unspecified', 'count': cnt} for repo, cnt in by_repository],
        'by_copyright': [{'status': st or 'Unspecified', 'count': cnt} for st, cnt in by_copyright],
    }

