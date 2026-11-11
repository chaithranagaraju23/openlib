"""Utility helpers for slugs, images, PDFs, URLs, and ISBN validation."""
import os
import re
import uuid
from urllib.parse import urlparse
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename


def slugify(text):
    """Convert text to clean URL slug."""
    if not text:
        return ''
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def is_valid_http_url(url):
    """Check whether string is a well-formed HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc) and '.' in parsed.netloc
    except Exception:
        return False


def normalize_isbn(isbn):
    """Normalize ISBN-10 / ISBN-13 string by stripping dashes/spaces."""
    if not isbn:
        return None
    cleaned = re.sub(r'[^0-9Xx]', '', str(isbn)).upper()
    if len(cleaned) in (10, 13):
        return cleaned
    return str(isbn).strip() or None


def save_cover_image(file_storage, output_folder, size=(420, 600)):
    """Validate, resize, and save an uploaded cover image using Pillow."""
    if not file_storage or not file_storage.filename:
        return None

    os.makedirs(output_folder, exist_ok=True)
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise ValueError('Unsupported image format.')

    filename = f'cover_{uuid.uuid4().hex[:12]}.jpg'
    output_path = os.path.join(output_folder, filename)

    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img)
    if img.mode in ('RGBA', 'P', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail(size, Image.Resampling.LANCZOS)
    img.save(output_path, 'JPEG', quality=88, optimize=True)
    return filename


def save_book_pdf(file_storage, books_folder):
    """Validate PDF signature and save securely into data/books."""
    if not file_storage or not file_storage.filename:
        return None, None

    os.makedirs(books_folder, exist_ok=True)
    original_name = secure_filename(file_storage.filename)
    if not original_name.lower().endswith('.pdf'):
        raise ValueError('Only PDF files are permitted.')

    header = file_storage.stream.read(5)
    file_storage.stream.seek(0)
    if header != b'%PDF-':
        raise ValueError('Invalid PDF file header.')

    unique_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
    dest = os.path.join(books_folder, unique_name)
    file_storage.save(dest)
    size_bytes = os.path.getsize(dest)
    return unique_name, format_file_size(size_bytes)


def format_file_size(num_bytes):
    """Format byte size into human readable form."""
    if not num_bytes:
        return ''
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num_bytes < 1024.0:
            return f'{num_bytes:.1f} {unit}' if unit != 'B' else f'{int(num_bytes)} B'
        num_bytes /= 1024.0
    return f'{num_bytes:.1f} TB'

