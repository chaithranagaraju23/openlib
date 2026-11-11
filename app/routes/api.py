"""JSON API routes for search suggestions, reader progress, bookmarks, and accessibility toggles."""
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user

from app import db
from app.models.book import AgeGroup, Category, Book
from app.models.review import ReaderBookmark, ReadingProgress

api_bp = Blueprint('api', __name__)


@api_bp.route('/search/suggestions')
def search_suggestions():
    """Return fast autocomplete suggestions for titles and authors."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])

    like_q = f'%{q}%'
    matches = (
        Book.query.filter(
            Book.is_active == True,
            Book.is_verified == True,
            db.or_(Book.title.ilike(like_q), Book.author.ilike(like_q), Book.isbn.ilike(like_q)),
        )
        .order_by(Book.view_count.desc())
        .limit(8)
        .all()
    )

    return jsonify([
        {
            'id': b.id,
            'title': b.title,
            'author': b.author,
            'age_group': b.age_group.display_name if b.age_group else '',
            'url': f'/books/{b.id}',
        }
        for b in matches
    ])


@api_bp.route('/categories')
def categories():
    """Return categories filtered optionally by age group slug."""
    ag_slug = request.args.get('age_group', '').strip()
    query = Category.query.filter_by(is_active=True)
    if ag_slug:
        ag = AgeGroup.query.filter_by(slug=ag_slug).first()
        if ag:
            query = query.filter_by(age_group_id=ag.id)
    cats = query.order_by(Category.name).all()
    return jsonify([
        {'id': c.id, 'name': c.name, 'slug': c.slug, 'count': c.get_book_count()}
        for c in cats
    ])


@api_bp.route('/books')
def list_books():
    """Paginated JSON book catalogue endpoint."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    pagination = (
        Book.query.filter_by(is_active=True, is_verified=True)
        .order_by(Book.id.asc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify({
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'books': [b.to_dict() for b in pagination.items],
    })


@api_bp.route('/reading-progress', methods=['POST'])
@login_required
def save_reading_progress():
    """Save current page and reading progress percentage for the reader."""
    data = request.get_json(silent=True) or {}
    book_id = data.get('book_id')
    current_page = max(1, int(data.get('current_page', 1)))
    total_pages = max(1, int(data.get('total_pages', 1)))

    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    pct = round(min(100.0, (current_page / total_pages) * 100.0), 1)
    prog = ReadingProgress.query.filter_by(user_id=current_user.id, book_id=book.id).first()
    if not prog:
        prog = ReadingProgress(user_id=current_user.id, book_id=book.id)
        db.session.add(prog)

    prog.current_page = current_page
    prog.total_pages = total_pages
    prog.percentage = pct
    prog.last_read = datetime.utcnow()
    prog.is_completed = current_page >= total_pages
    db.session.commit()

    return jsonify({
        'status': 'saved',
        'current_page': prog.current_page,
        'total_pages': prog.total_pages,
        'percentage': prog.percentage,
        'is_completed': prog.is_completed,
    })


@api_bp.route('/reader-bookmarks/<int:book_id>', methods=['GET'])
@login_required
def get_reader_bookmarks(book_id):
    """List saved page bookmarks for a specific book."""
    items = (
        ReaderBookmark.query.filter_by(user_id=current_user.id, book_id=book_id)
        .order_by(ReaderBookmark.page_number.asc())
        .all()
    )
    return jsonify([
        {
            'id': item.id,
            'page_number': item.page_number,
            'label': item.label or f'Page {item.page_number}',
            'note': item.note or '',
        }
        for item in items
    ])


@api_bp.route('/reader-bookmarks', methods=['POST'])
@login_required
def toggle_reader_bookmark():
    """Add, update, or remove a page bookmark inside the reader."""
    data = request.get_json(silent=True) or {}
    book_id = data.get('book_id')
    page_number = max(1, int(data.get('page_number', 1)))
    action = data.get('action', 'toggle')
    label = (data.get('label') or f'Page {page_number}').strip()[:150]
    note = (data.get('note') or '').strip()

    existing = ReaderBookmark.query.filter_by(
        user_id=current_user.id, book_id=book_id, page_number=page_number
    ).first()

    if action == 'delete' or (action == 'toggle' and existing):
        if existing:
            db.session.delete(existing)
            db.session.commit()
        return jsonify({'status': 'removed', 'page_number': page_number})

    if not existing:
        existing = ReaderBookmark(
            user_id=current_user.id,
            book_id=book_id,
            page_number=page_number,
            label=label,
            note=note,
        )
        db.session.add(existing)
    else:
        existing.label = label
        existing.note = note

    db.session.commit()
    return jsonify({
        'status': 'saved',
        'id': existing.id,
        'page_number': existing.page_number,
        'label': existing.label,
        'note': existing.note,
    })


@api_bp.route('/accessibility', methods=['POST'])
def update_accessibility():
    """Persist accessibility preferences in session and user profile."""
    data = request.get_json(silent=True) or {}
    for key in ('large_text', 'high_contrast', 'night_mode', 'text_to_speech'):
        if key in data:
            val = bool(data[key])
            session[f'a11y_{key}'] = val
            if current_user.is_authenticated:
                setattr(current_user, key, val)

    if current_user.is_authenticated:
        db.session.commit()

    return jsonify({
        'large_text': session.get('a11y_large_text', current_user.large_text if current_user.is_authenticated else False),
        'high_contrast': session.get('a11y_high_contrast', current_user.high_contrast if current_user.is_authenticated else False),
        'night_mode': session.get('a11y_night_mode', current_user.night_mode if current_user.is_authenticated else False),
        'text_to_speech': session.get('a11y_text_to_speech', current_user.text_to_speech if current_user.is_authenticated else False),
    })

