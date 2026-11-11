"""Shared helper for the four generation-based library blueprints."""
from flask import render_template, request, abort
from sqlalchemy import func

from app import db
from app.models.book import AgeGroup, Category, Book


def render_generation_library(age_group_slug, template_name, category_slug=None):
    """Render a generation library landing or filtered category page with real DB counts."""
    age_group = AgeGroup.query.filter_by(slug=age_group_slug).first_or_404()

    active_verified = (Book.is_active == True) & (Book.is_verified == True)

    categories_with_counts = (
        db.session.query(Category, func.count(Book.id).label('book_count'))
        .outerjoin(Book, (Book.category_id == Category.id) & active_verified)
        .filter(Category.age_group_id == age_group.id, Category.is_active == True)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.name)
        .all()
    )

    selected_category = None
    if category_slug:
        selected_category = Category.query.filter_by(
            slug=category_slug, age_group_id=age_group.id, is_active=True
        ).first()
        if not selected_category:
            abort(404)

    q = request.args.get('q', '').strip()
    language = request.args.get('language', '').strip()
    sort_by = request.args.get('sort', 'popular').strip()
    page = request.args.get('page', 1, type=int)

    query = Book.query.filter(active_verified, Book.age_group_id == age_group.id)

    if selected_category:
        query = query.filter(Book.category_id == selected_category.id)
    if q:
        like_q = f'%{q}%'
        query = query.filter(
            db.or_(
                Book.title.ilike(like_q),
                Book.author.ilike(like_q),
                Book.description.ilike(like_q),
                Book.tags.ilike(like_q),
            )
        )
    if language:
        query = query.filter(Book.language == language)

    if sort_by == 'alphabetical':
        query = query.order_by(Book.title.asc())
    elif sort_by == 'recent':
        query = query.order_by(Book.date_added.desc(), Book.id.desc())
    elif sort_by == 'rating':
        query = query.order_by(Book.average_rating.desc(), Book.review_count.desc(), Book.title.asc())
    else:
        query = query.order_by(Book.is_featured.desc(), Book.view_count.desc(), Book.id.asc())

    pagination = query.paginate(page=page, per_page=12, error_out=False)

    languages = [
        row[0] for row in db.session.query(Book.language)
        .filter(active_verified, Book.age_group_id == age_group.id, Book.language != None)
        .distinct().order_by(Book.language).all()
    ]

    total_in_section = age_group.get_book_count()

    return render_template(
        template_name,
        age_group=age_group,
        categories_with_counts=categories_with_counts,
        selected_category=selected_category,
        books=pagination.items,
        pagination=pagination,
        total_in_section=total_in_section,
        languages=languages,
        q=q,
        selected_language=language,
        sort_by=sort_by,
    )

