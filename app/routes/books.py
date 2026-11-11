"""Book search, details, online PDF.js reader, borrowing, bookmarks, reviews, and exchange requests."""
import os
import re
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    current_app, send_from_directory, Response, abort, stream_with_context
)
from flask_login import login_required, current_user

from app import db
from app.models.book import AgeGroup, Category, Book
from app.models.transaction import BorrowRecord, ExchangeListing, ExchangeRequest
from app.models.review import Review, Bookmark, ReaderBookmark, ReadingProgress
from app.forms.book_forms import ReviewForm, ExchangeRequestForm

books_bp = Blueprint('books', __name__)

ALLOWED_PDF_HOSTS = (
    'archive.org',
    'www.gutenberg.org',
    'gutenberg.org',
    'upload.wikimedia.org',
    'openstax.org',
    'assets.openstax.org',
)


def _is_whitelisted_pdf_host(url):
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or '').lower()
        return any(host == allowed or host.endswith('.' + allowed) for allowed in ALLOWED_PDF_HOSTS)
    except Exception:
        return False


def _is_direct_pdf_url(url):
    if not url:
        return False
    path = urlparse(url).path.lower()
    return path.endswith('.pdf')


@books_bp.route('/')
@books_bp.route('/search')
def search():
    """Advanced database-backed search and filtering across the catalogue."""
    active_verified = (Book.is_active == True) & (Book.is_verified == True)

    q = request.args.get('q', '').strip()
    age_group_slug = request.args.get('age_group', '').strip()
    category_slug = request.args.get('category', '').strip()
    language = request.args.get('language', '').strip()
    author_filter = request.args.get('author', '').strip()
    file_format = request.args.get('file_format', '').strip()
    year_from = request.args.get('year_from', type=int)
    year_to = request.args.get('year_to', type=int)
    online_only = request.args.get('online_only') == '1'
    downloadable_only = request.args.get('downloadable_only') == '1'
    sort_by = request.args.get('sort', 'popular').strip()
    page = request.args.get('page', 1, type=int)

    query = Book.query.filter(active_verified)

    if q:
        like_q = f'%{q}%'
        query = query.filter(
            db.or_(
                Book.title.ilike(like_q),
                Book.author.ilike(like_q),
                Book.isbn.ilike(like_q),
                Book.tags.ilike(like_q),
                Book.description.ilike(like_q),
                Book.book_code.ilike(like_q),
            )
        )

    selected_age_group = None
    if age_group_slug:
        selected_age_group = AgeGroup.query.filter_by(slug=age_group_slug).first()
        if selected_age_group:
            query = query.filter(Book.age_group_id == selected_age_group.id)

    if category_slug:
        cat = Category.query.filter(
            db.or_(Category.slug == category_slug, Category.name == category_slug)
        ).first()
        if cat:
            query = query.filter(Book.category_id == cat.id)

    if language:
        query = query.filter(Book.language == language)

    if author_filter:
        query = query.filter(Book.author.ilike(f'%{author_filter}%'))

    if file_format:
        query = query.filter(Book.file_format.ilike(f'%{file_format}%'))

    if year_from is not None:
        query = query.filter(Book.publication_year >= year_from)

    if year_to is not None:
        query = query.filter(Book.publication_year <= year_to)

    if online_only:
        query = query.filter(Book.is_readable_online == True)

    if downloadable_only:
        query = query.filter(Book.is_downloadable == True)

    if sort_by == 'alphabetical':
        query = query.order_by(Book.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Book.title.desc())
    elif sort_by == 'recent':
        query = query.order_by(Book.date_added.desc(), Book.id.desc())
    elif sort_by == 'rating':
        query = query.order_by(Book.average_rating.desc(), Book.review_count.desc(), Book.title.asc())
    else:
        query = query.order_by((Book.view_count + Book.borrow_count * 2).desc(), Book.is_featured.desc(), Book.id.asc())

    per_page = current_app.config.get('BOOKS_PER_PAGE', 12)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    age_groups = AgeGroup.query.order_by(AgeGroup.sort_order).all()
    cat_query = Category.query.filter_by(is_active=True)
    if selected_age_group:
        cat_query = cat_query.filter_by(age_group_id=selected_age_group.id)
    filter_categories = cat_query.order_by(Category.name).all()

    languages = [
        r[0] for r in db.session.query(Book.language)
        .filter(active_verified, Book.language != None)
        .distinct().order_by(Book.language).all()
    ]
    formats = [
        r[0] for r in db.session.query(Book.file_format)
        .filter(active_verified, Book.file_format != None)
        .distinct().order_by(Book.file_format).all()
    ]

    pagination_params = {
        'q': q or None,
        'age_group': age_group_slug or None,
        'category': category_slug or None,
        'language': language or None,
        'author': author_filter or None,
        'file_format': file_format or None,
        'year_from': year_from,
        'year_to': year_to,
        'online_only': '1' if online_only else None,
        'downloadable_only': '1' if downloadable_only else None,
        'sort': sort_by if sort_by != 'popular' else None,
    }

    return render_template(
        'search.html',
        books=pagination.items,
        pagination=pagination,
        age_groups=age_groups,
        filter_categories=filter_categories,
        languages=languages,
        formats=formats,
        pagination_params=pagination_params,
        filters={
            'q': q,
            'age_group': age_group_slug,
            'category': category_slug,
            'language': language,
            'author': author_filter,
            'file_format': file_format,
            'year_from': year_from,
            'year_to': year_to,
            'online_only': online_only,
            'downloadable_only': downloadable_only,
            'sort': sort_by,
        },
    )


@books_bp.route('/<int:book_id>')
def details(book_id):
    """Book details page displaying full verified metadata, licence, and reader actions."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    book.increment_view()
    db.session.commit()

    is_bookmarked = False
    active_borrow = None
    reading_progress = None
    user_review = None

    if current_user.is_authenticated:
        is_bookmarked = Bookmark.query.filter_by(user_id=current_user.id, book_id=book.id).first() is not None
        active_borrow = BorrowRecord.query.filter_by(
            user_id=current_user.id, book_id=book.id, status='borrowed'
        ).first()
        reading_progress = ReadingProgress.query.filter_by(user_id=current_user.id, book_id=book.id).first()
        user_review = Review.query.filter_by(user_id=current_user.id, book_id=book.id).first()

    reviews = (
        Review.query.filter_by(book_id=book.id, is_approved=True)
        .order_by(Review.created_at.desc())
        .all()
    )

    related_books = (
        Book.query.filter(
            Book.is_active == True,
            Book.is_verified == True,
            Book.id != book.id,
            db.or_(Book.category_id == book.category_id, Book.age_group_id == book.age_group_id),
        )
        .order_by(Book.category_id == book.category_id, Book.view_count.desc())
        .limit(4)
        .all()
    )

    review_form = ReviewForm()
    if user_review:
        review_form.rating.data = user_review.rating
        review_form.title.data = user_review.title
        review_form.content.data = user_review.content

    return render_template(
        'book_details.html',
        book=book,
        is_bookmarked=is_bookmarked,
        active_borrow=active_borrow,
        reading_progress=reading_progress,
        reviews=reviews,
        user_review=user_review,
        review_form=review_form,
        related_books=related_books,
    )


@books_bp.route('/<int:book_id>/read')
def read(book_id):
    """Integrated PDF.js / accessible online reader."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    if not book.is_readable_online and not book.has_local_pdf():
        flash('This title is available via its official external borrowing page.', 'info')
        return redirect(url_for('books.details', book_id=book.id))

    pdf_source_url = None
    reader_mode = 'external'

    if book.has_local_pdf():
        pdf_source_url = url_for('books.serve_local_pdf', book_id=book.id)
        reader_mode = 'pdfjs'
    elif (
        _is_direct_pdf_url(book.reading_url)
        and _is_whitelisted_pdf_host(book.reading_url)
        and (book.redistribution_permitted or book.copyright_status in ('Public Domain', 'Open Access (Creative Commons)'))
    ):
        pdf_source_url = url_for('books.stream_remote_pdf', book_id=book.id)
        reader_mode = 'pdfjs'
    elif (
        _is_direct_pdf_url(book.download_url)
        and _is_whitelisted_pdf_host(book.download_url)
        and (book.redistribution_permitted or book.copyright_status in ('Public Domain', 'Open Access (Creative Commons)'))
    ):
        pdf_source_url = url_for('books.stream_remote_pdf', book_id=book.id, use_download=1)
        reader_mode = 'pdfjs'
    elif book.gutenberg_id or 'gutenberg.org' in (book.source_url or '') or 'wikisource.org' in (book.source_url or ''):
        reader_mode = 'text_or_external'

    progress = None
    page_bookmarks = []
    if current_user.is_authenticated:
        progress = ReadingProgress.query.filter_by(user_id=current_user.id, book_id=book.id).first()
        page_bookmarks = (
            ReaderBookmark.query.filter_by(user_id=current_user.id, book_id=book.id)
            .order_by(ReaderBookmark.page_number.asc())
            .all()
        )

    return render_template(
        'reader.html',
        book=book,
        reader_mode=reader_mode,
        pdf_source_url=pdf_source_url,
        progress=progress,
        page_bookmarks=page_bookmarks,
    )


@books_bp.route('/<int:book_id>/pdf-file')
def serve_local_pdf(book_id):
    """Serve authorized local PDF file stored in data/books/."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    if not book.local_file_path:
        abort(404)
    books_folder = current_app.config['BOOKS_FOLDER']
    safe_rel = os.path.normpath(book.local_file_path)
    if safe_rel.startswith('..') or os.path.isabs(safe_rel):
        abort(403)
    full_path = os.path.join(books_folder, safe_rel)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(books_folder, safe_rel, mimetype='application/pdf')


@books_bp.route('/<int:book_id>/pdf-stream')
def stream_remote_pdf(book_id):
    """CORS-safe verified stream proxy for authorized open-licensed remote PDFs."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    if not (book.redistribution_permitted or book.copyright_status in ('Public Domain', 'Open Access (Creative Commons)')):
        abort(403)

    target_url = book.download_url if request.args.get('use_download') == '1' else book.reading_url
    if not (_is_direct_pdf_url(target_url) and _is_whitelisted_pdf_host(target_url)):
        abort(403)

    try:
        req = Request(target_url, headers={'User-Agent': 'OpenLibDigitalLibrary/1.0'})
        remote = urlopen(req, timeout=20)
        content_type = remote.headers.get('Content-Type', 'application/pdf')
        if 'pdf' not in content_type.lower() and 'octet-stream' not in content_type.lower():
            remote.close()
            abort(502)

        def generate():
            try:
                while True:
                    chunk = remote.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                remote.close()

        return Response(
            stream_with_context(generate()),
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="openlib_{book.id}.pdf"'},
        )
    except Exception:
        abort(502)


@books_bp.route('/<int:book_id>/text-preview')
def text_preview(book_id):
    """Fetch public-domain plain text chapters cleanly for Gutenberg/Wikisource works."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    if book.copyright_status not in ('Public Domain', 'Open Access (Creative Commons)'):
        return {'available': False, 'message': 'External reading required by licence.'}, 403

    text_url = None
    if book.gutenberg_id and re.match(r'^\d+$', str(book.gutenberg_id).strip()):
        gid = str(book.gutenberg_id).strip()
        text_url = f'https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt'
    elif book.reading_url and 'gutenberg.org' in book.reading_url and book.reading_url.endswith('.txt'):
        text_url = book.reading_url

    if not text_url:
        return {'available': False, 'message': 'No plain text stream available for this edition.'}, 404

    try:
        req = Request(text_url, headers={'User-Agent': 'OpenLibDigitalLibrary/1.0'})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read(300000).decode('utf-8', errors='replace')
        return {'available': True, 'text': raw, 'source_url': text_url}
    except Exception:
        return {'available': False, 'message': 'Could not fetch remote public-domain text right now.'}, 502


@books_bp.route('/<int:book_id>/download')
def download(book_id):
    """Download book ONLY if permitted by copyright/licence."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    if not book.is_downloadable:
        flash(
            f'Downloading is not permitted under this book\'s licence ({book.licence}). '
            'Please use the online reader or official source link.',
            'warning'
        )
        return redirect(url_for('books.details', book_id=book.id))

    book.download_count = (book.download_count or 0) + 1
    db.session.commit()

    if book.has_local_pdf():
        books_folder = current_app.config['BOOKS_FOLDER']
        return send_from_directory(
            books_folder,
            book.local_file_path,
            as_attachment=True,
            download_name=f'{book.get_display_id()}.pdf',
        )

    target = book.download_url or book.reading_url or book.source_url
    if target:
        return redirect(target)

    flash('Download link is unavailable.', 'warning')
    return redirect(url_for('books.details', book_id=book.id))


@books_bp.route('/<int:book_id>/borrow', methods=['POST'])
@login_required
def borrow(book_id):
    """Borrow a book (14-day loan, max 5 active borrows)."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    if not book.is_borrowable:
        flash('This item is reference-only and cannot be borrowed directly.', 'warning')
        return redirect(url_for('books.details', book_id=book.id))

    existing = BorrowRecord.query.filter_by(
        user_id=current_user.id, book_id=book.id, status='borrowed'
    ).first()
    if existing:
        flash('You already have this book on loan.', 'info')
        return redirect(url_for('books.details', book_id=book.id))

    max_borrows = current_app.config.get('MAX_ACTIVE_BORROWS', 5)
    active_count = BorrowRecord.query.filter_by(user_id=current_user.id, status='borrowed').count()
    if active_count >= max_borrows:
        flash(f'You have reached the maximum of {max_borrows} active borrowed books. Please return one first.', 'warning')
        return redirect(url_for('user.dashboard'))

    record = BorrowRecord(user_id=current_user.id, book_id=book.id, status='borrowed')
    book.borrow_count = (book.borrow_count or 0) + 1
    db.session.add(record)
    db.session.add(book)
    db.session.commit()

    flash(f'Successfully borrowed "{book.title}". Due back in 14 days.', 'success')
    return redirect(url_for('books.details', book_id=book.id))


@books_bp.route('/<int:book_id>/return', methods=['POST'])
@login_required
def return_book(book_id):
    """Return a borrowed book."""
    record = BorrowRecord.query.filter_by(
        user_id=current_user.id, book_id=book_id, status='borrowed'
    ).first_or_404()
    record.status = 'returned'
    record.returned_at = datetime.utcnow()
    db.session.commit()
    flash(f'Returned "{record.book.title}". Thank you!', 'success')
    next_url = request.form.get('next') or url_for('books.details', book_id=book_id)
    return redirect(next_url)


@books_bp.route('/<int:book_id>/renew', methods=['POST'])
@login_required
def renew_book(book_id):
    """Renew an active borrow."""
    record = BorrowRecord.query.filter_by(
        user_id=current_user.id, book_id=book_id, status='borrowed'
    ).first_or_404()
    if record.renew():
        db.session.commit()
        flash(f'Loan renewed! New due date: {record.due_date.strftime("%B %d, %Y")}.', 'success')
    else:
        flash('Maximum renewals (2) already reached for this loan.', 'warning')
    next_url = request.form.get('next') or url_for('user.dashboard')
    return redirect(next_url)


@books_bp.route('/<int:book_id>/bookmark', methods=['POST'])
@login_required
def toggle_bookmark(book_id):
    """Add or remove a book from the user's reading list."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    bm = Bookmark.query.filter_by(user_id=current_user.id, book_id=book.id).first()
    if bm:
        db.session.delete(bm)
        db.session.commit()
        flash('Removed from your reading list.', 'info')
    else:
        bm = Bookmark(user_id=current_user.id, book_id=book.id)
        db.session.add(bm)
        db.session.commit()
        flash('Saved to your reading list!', 'success')
    return redirect(url_for('books.details', book_id=book.id))


@books_bp.route('/<int:book_id>/review', methods=['POST'])
@login_required
def submit_review(book_id):
    """Submit or update a book review."""
    book = Book.query.filter_by(id=book_id, is_active=True).first_or_404()
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review.query.filter_by(user_id=current_user.id, book_id=book.id).first()
        if review:
            review.rating = form.rating.data
            review.title = form.title.data.strip()
            review.content = form.content.data.strip()
            flash('Your review has been updated!', 'success')
        else:
            review = Review(
                user_id=current_user.id,
                book_id=book.id,
                rating=form.rating.data,
                title=form.title.data.strip(),
                content=form.content.data.strip(),
                is_approved=True,
            )
            db.session.add(review)
            flash('Thank you for reviewing this book!', 'success')
        db.session.flush()
        book.update_rating()
        db.session.commit()
    else:
        for field_errors in form.errors.values():
            for err in field_errors:
                flash(err, 'danger')
    return redirect(url_for('books.details', book_id=book.id))


@books_bp.route('/exchange/<int:listing_id>/request', methods=['GET', 'POST'])
@login_required
def request_exchange(listing_id):
    """Send an exchange proposal for a community book exchange listing."""
    listing = ExchangeListing.query.get_or_404(listing_id)
    if listing.user_id == current_user.id:
        flash('You cannot request an exchange for your own listing.', 'warning')
        return redirect(url_for('main.exchange'))
    if listing.status != 'available':
        flash('This book listing is no longer available for exchange.', 'warning')
        return redirect(url_for('main.exchange'))

    form = ExchangeRequestForm()
    if form.validate_on_submit():
        req_obj = ExchangeRequest(
            requester_id=current_user.id,
            owner_id=listing.user_id,
            listing_id=listing.id,
            requested_book_id=listing.book_id,
            offered_book_title=form.offered_book_title.data.strip(),
            offered_book_author=form.offered_book_author.data.strip(),
            offered_book_condition=form.offered_book_condition.data,
            message=form.message.data.strip(),
            status='pending',
        )
        db.session.add(req_obj)
        db.session.commit()
        flash('Exchange proposal sent! You can track responses in your dashboard.', 'success')
        return redirect(url_for('user.exchanges'))

    return render_template('exchange_request.html', listing=listing, form=form)
