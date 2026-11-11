"""Complete the 420+ verified catalogue, normalize languages, verify IA PDF filenames, and download sample open PDFs."""
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request

from app.services.curate_catalogue import (
    CATALOGUE_DIR,
    BOOKS_DIR,
    CATEGORY_SPECS,
    LANG_MAP,
    query_ia,
    query_openlibrary,
    query_wikisource,
    norm_key,
)

HEADERS = {'User-Agent': 'OpenLibDigitalLibrary/1.0 (https://openlib.org)'}

EXTRA_LANG_MAP = {
    **LANG_MAP,
    'chi': 'Chinese', 'zho': 'Chinese', 'chinese': 'Chinese',
    'urd': 'Urdu', 'urdu': 'Urdu',
    'mar': 'Marathi', 'marathi': 'Marathi',
    'ben': 'Bengali', 'bengali': 'Bengali',
    'tel': 'Telugu', 'telugu': 'Telugu',
    'kan': 'Kannada', 'kannada': 'Kannada',
    'rus': 'Russian', 'russian': 'Russian',
    'ara': 'Arabic', 'arabic': 'Arabic',
    'jpn': 'Japanese', 'japanese': 'Japanese',
    'gem': 'Germanic', 'mal': 'Malayalam', 'tgl': 'Tagalog', 'zul': 'Zulu',
}

FILL_QUERIES = {
    ('Children', 'Moral Stories'): [
        ('ia', 'collection:gutenberg AND (Aesop OR fables OR "Moral stories") AND mediatype:texts'),
        ('wikisource', "Aesop's Fables"),
        ('openlibrary', 'Aesop fables moral stories children'),
    ],
    ('Youth', 'Fiction and Novels'): [
        ('ia', 'collection:gutenberg AND (subject:"Science fiction" OR subject:"Young adult fiction" OR subject:"Bildungsroman") AND mediatype:texts'),
        ('openlibrary', 'young adult classic novels'),
    ],
    ('Youth', 'Biographies'): [
        ('ia', 'collection:gutenberg AND (subject:"Biography" OR title:"Autobiography" OR title:"Life of") AND mediatype:texts'),
        ('openlibrary', 'biography young readers scientists'),
    ],
    ('Adults', 'Literature and Novels'): [
        ('ia', 'collection:gutenberg AND subject:"Fiction" AND mediatype:texts'),
        ('ia', 'collection:gutenberg AND (language:Spanish OR language:French OR language:German) AND mediatype:texts'),
    ],
    ('Seniors', 'Classic Literature'): [
        ('ia', 'collection:gutenberg AND (creator:"Dickens" OR creator:"Austen" OR creator:"Tolstoy" OR creator:"Shakespeare") AND mediatype:texts'),
    ],
    ('Seniors', 'Poetry'): [
        ('wikisource', 'Gitanjali Tagore poems'),
        ('ia', 'collection:gutenberg AND subject:"Poetry" AND mediatype:texts'),
    ],
    ('Seniors', 'Short Stories'): [
        ('ia', 'collection:gutenberg AND subject:"Short stories" AND mediatype:texts'),
        ('wikisource', 'short stories Chekhov O. Henry'),
    ],
}


def find_verified_ia_pdf(identifier):
    """Fetch exact PDF filename and size from archive.org/metadata/<id>/files."""
    url = f'https://archive.org/metadata/{urllib.parse.quote(identifier)}/files'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='replace'))
        for f in data.get('result', []):
            name = f.get('name', '')
            fmt = f.get('format', '')
            if name.lower().endswith('.pdf') and 'encrypted' not in name.lower():
                size = int(f.get('size', 0) or 0)
                return f'https://archive.org/download/{identifier}/{urllib.parse.quote(name)}', size, name
    except Exception:
        pass
    return None, 0, None


def run():
    json_path = os.path.join(CATALOGUE_DIR, 'openlib_verified_catalogue.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        books = json.load(f)['books']

    seen_keys = set()
    seen_urls = set()
    counts = {}

    for b in books:
        raw_lang = (b.get('language') or 'English').strip().lower()
        b['language'] = EXTRA_LANG_MAP.get(raw_lang, b.get('language', 'English').title())
        # Normalize default reading_url for IA items to official /details/ unless verified PDF is attached
        if b.get('source_repository') == 'Internet Archive' and b.get('source_url'):
            if b.get('reading_url', '').endswith('.pdf') and not b.get('local_file_path'):
                b['reading_url'] = b['source_url']
                b['download_url'] = None

        seen_keys.add(norm_key(b['title'], b['author']))
        seen_urls.add(b['source_url'])
        pair = (b['age_group'], b['category'])
        counts[pair] = counts.get(pair, 0) + 1

    # Fill remaining categories to exact target
    for age_name, age_slug, min_age, max_age, cat_name, target, _ in CATEGORY_SPECS:
        pair = (age_name, cat_name)
        have = counts.get(pair, 0)
        if have >= target:
            continue
        print(f'Filling {pair}: {have}/{target}...', flush=True)
        for src_type, q in FILL_QUERIES.get(pair, []):
            if have >= target:
                break
            if src_type == 'ia':
                cands = query_ia(q, limit=40)
            elif src_type == 'openlibrary':
                cands = query_openlibrary(q, limit=30)
            elif src_type == 'wikisource':
                cands = query_wikisource(q, limit=25)
            else:
                cands = []

            for c in cands:
                if have >= target:
                    break
                key = norm_key(c['title'], c['author'])
                if not key[0] or key in seen_keys or c['source_url'] in seen_urls:
                    continue
                if c.get('source_repository') == 'Internet Archive':
                    c['reading_url'] = c['source_url']
                    c['download_url'] = None
                raw_lang = (c.get('language') or 'English').strip().lower()
                c['language'] = EXTRA_LANG_MAP.get(raw_lang, c.get('language', 'English').title())
                c['age_group'] = age_name
                c['age_group_slug'] = age_slug
                c['category'] = cat_name
                c['min_age'] = min_age
                c['max_age'] = max_age
                c['is_featured'] = have == 0
                seen_keys.add(key)
                seen_urls.add(c['source_url'])
                books.append(c)
                have += 1
            time.sleep(0.15)
        counts[pair] = have
        print(f'Filled {pair}: {have}/{target}', flush=True)

    # Download up to 2 genuine small (<1.8 MB) open-licensed PDFs per age group into data/books/
    os.makedirs(BOOKS_DIR, exist_ok=True)
    downloaded_per_age = {'Children': 0, 'Youth': 0, 'Adults': 0, 'Seniors': 0}

    for b in books:
        ag = b['age_group']
        if downloaded_per_age.get(ag, 0) >= 2:
            continue
        if b.get('source_repository') != 'Internet Archive':
            continue
        if b.get('copyright_status') not in ('Public Domain', 'Open Access (Creative Commons)'):
            continue
        if 'PDF' not in (b.get('file_format') or ''):
            continue
        ident = b['source_url'].rstrip('/').split('/')[-1]
        pdf_url, size_bytes, orig_name = find_verified_ia_pdf(ident)
        if not pdf_url or size_bytes <= 10000 or size_bytes > 1_800_000:
            continue

        safe_fname = re.sub(r'[^a-zA-Z0-9._-]+', '_', f'{ag.lower()}_{ident}.pdf')[:80]
        dest_path = os.path.join(BOOKS_DIR, safe_fname)
        try:
            req = urllib.request.Request(pdf_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()
            if data[:5] == b'%PDF-':
                with open(dest_path, 'wb') as out:
                    out.write(data)
                b['local_file_path'] = safe_fname
                b['file_format'] = 'PDF'
                b['file_size'] = f'{round(len(data) / 1024)} KB'
                b['reading_url'] = pdf_url
                b['download_url'] = pdf_url
                b['is_downloadable'] = True
                b['redistribution_permitted'] = True
                b['is_featured'] = True
                downloaded_per_age[ag] += 1
                print(f'Downloaded verified PDF [{ag}]: {b["title"]} -> {safe_fname} ({b["file_size"]})', flush=True)
        except Exception as e:
            print(f'Skip PDF {ident}: {e}', flush=True)

    # Save JSON and CSV
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'total': len(books), 'books': books}, f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(CATALOGUE_DIR, 'openlib_verified_catalogue.csv')
    fieldnames = [
        'title', 'author', 'description', 'cover_image', 'age_group', 'min_age', 'max_age',
        'category', 'language', 'language_code', 'publisher', 'publication_year', 'isbn',
        'file_format', 'file_size', 'local_file_path', 'reading_url', 'download_url',
        'source_url', 'source_repository', 'gutenberg_id', 'is_readable_online',
        'is_downloadable', 'redistribution_permitted', 'is_borrowable', 'copyright_status',
        'licence', 'licence_url', 'licence_verified', 'is_featured', 'tags'
    ]
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for b in books:
            writer.writerow({k: b.get(k, '') for k in fieldnames})

    print(f'\nFINAL VERIFIED CATALOGUE COUNT: {len(books)}', flush=True)
    print('Local PDFs downloaded:', downloaded_per_age, flush=True)


if __name__ == '__main__':
    run()
