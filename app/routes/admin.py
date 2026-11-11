"""Administrator dashboard, book management, catalogue import/validation/reports, donations, users."""
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
)
from flask_login import current_user

from app import db
from app.models.user import User
from app.models.book import AgeGroup, Category, Book
from app.models.transaction import BorrowRecord, ExchangeListing, ExchangeRequest, Donation, ContactMessage
from app.forms.book_forms import BookForm, CatalogueImportForm
from app.utils.decorators import admin_required
from app.utils.helpers import save_cover_image, save_book_pdf, normalize_isbn, slugify
from app.services.catalogue_manager import (
    import_json_data,
    import_csv_data,
    export_catalogue_json,
    export_catalogue_csv,
    generate_catalogue_report,
    check_live_url,
)

admin_bp = Blueprint('admin', __name__)


def _populate_book_form_choices(form):
    form.age_group_id.choices = [
        (ag.id, ag.display_name) for ag in AgeGroup.query.order_by(AgeGroup.sort_order).all()
    ]
    form.category_id.choices = [
        (c.id, f'{c.age_group.name if c.age_group else "General"} — {c.name}')
        for c in Category.query.join(AgeGroup, isouter=True)
        .order_by(AgeGroup.sort_order, Category.name).all()
    ]


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin overview dashboard with real DB counts and target tracking."""
    report = generate_catalogue_report()
    stats = {
        'total_books': report['total_verified'],
        'total_users': User.query.count(),
        'active_borrows': BorrowRecord.query.filter_by(status='borrowed').count(),
        'pending_donations': Donation.query.filter_by(status='pending').count(),
        'active_exchanges': ExchangeListing.query.filter_by(status='available').count(),
        'pending_exchange_reqs': ExchangeRequest.query.filter_by(status='pending').count(),
        'unread_messages': ContactMessage.query.filter_by(is_read=False).count(),
    }
    recent_donations = Donation.query.order_by(Donation.created_at.desc()).limit(5).all()
    recent_books = Book.query.order_by(Book.date_added.desc()).limit(5).all()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        report=report,
        recent_donations=recent_donations,
        recent_books=recent_books,
    )


@admin_bp.route('/books')
@admin_required
def books():
    """Admin book list and management."""
    q = request.args.get('q', '').strip()
    age_group_slug = request.args.get('age_group', '').strip()
    status_filter = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Book.query
    if q:
        like_q = f'%{q}%'
        query = query.filter(
            db.or_(Book.title.ilike(like_q), Book.author.ilike(like_q), Book.isbn.ilike(like_q), Book.book_code.ilike(like_q))
        )
    if age_group_slug:
        ag = AgeGroup.query.filter_by(slug=age_group_slug).first()
        if ag:
            query = query.filter(Book.age_group_id == ag.id)
    if status_filter == 'unverified':
        query = query.filter(db.or_(Book.is_verified == False, Book.licence_verified == False))
    elif status_filter == 'inactive':
        query = query.filter(Book.is_active == False)
    elif status_filter == 'featured':
        query = query.filter(Book.is_featured == True)

    per_page = current_app.config.get('ADMIN_BOOKS_PER_PAGE', 20)
    pagination = query.order_by(Book.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    age_groups = AgeGroup.query.order_by(AgeGroup.sort_order).all()

    return render_template(
        'admin/books.html',
        books=pagination.items,
        pagination=pagination,
        age_groups=age_groups,
        q=q,
        age_group_slug=age_group_slug,
        status_filter=status_filter,
    )


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    """Add a new verified book."""
    form = BookForm()
    _populate_book_form_choices(form)

    if form.validate_on_submit():
        cover_filename = 'default_cover.svg'
        if form.cover_file.data:
            try:
                cover_filename = save_cover_image(form.cover_file.data, current_app.config['COVERS_FOLDER']) or 'default_cover.svg'
            except ValueError as exc:
                flash(f'Cover error: {exc}', 'danger')
                return render_template('admin/book_form.html', form=form, mode='add')

        local_pdf = None
        file_size = None
        if form.pdf_file.data:
            try:
                local_pdf, file_size = save_book_pdf(form.pdf_file.data, current_app.config['BOOKS_FOLDER'])
            except ValueError as exc:
                flash(f'PDF error: {exc}', 'danger')
                return render_template('admin/book_form.html', form=form, mode='add')

        book = Book(
            title=form.title.data.strip(),
            author=form.author.data.strip(),
            description=form.description.data.strip(),
            cover_image=cover_filename,
            age_group_id=form.age_group_id.data,
            category_id=form.category_id.data,
            min_age=form.min_age.data or 0,
            max_age=form.max_age.data or 99,
            language=form.language.data.strip(),
            publisher=form.publisher.data.strip() if form.publisher.data else None,
            publication_year=form.publication_year.data,
            isbn=normalize_isbn(form.isbn.data),
            pages=form.pages.data,
            file_format=form.file_format.data,
            file_size=file_size,
            local_file_path=local_pdf,
            reading_url=form.reading_url.data.strip() if form.reading_url.data else form.source_url.data.strip(),
            download_url=form.download_url.data.strip() if form.download_url.data else None,
            source_url=form.source_url.data.strip(),
            source_repository=form.source_repository.data,
            copyright_status=form.copyright_status.data,
            licence=form.licence.data.strip(),
            licence_url=form.licence_url.data.strip() if form.licence_url.data else None,
            tags=form.tags.data.strip() if form.tags.data else '',
            is_readable_online=form.is_readable_online.data,
            is_downloadable=form.is_downloadable.data,
            redistribution_permitted=form.redistribution_permitted.data,
            is_borrowable=form.is_borrowable.data,
            is_exchangeable=form.is_exchangeable.data,
            is_featured=form.is_featured.data,
            is_verified=form.is_verified.data,
            licence_verified=form.licence_verified.data,
            licence_verified_at=datetime.utcnow() if form.licence_verified.data else None,
            is_active=form.is_active.data,
            verification_notes=form.verification_notes.data.strip() if form.verification_notes.data else None,
        )
        db.session.add(book)
        db.session.flush()
        book.book_code = f'OL-{book.id:05d}'
        db.session.commit()
        flash(f'Book "{book.title}" ({book.book_code}) added successfully!', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', form=form, mode='add')


@admin_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    """Edit an existing book."""
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    _populate_book_form_choices(form)

    if form.validate_on_submit():
        if form.cover_file.data:
            try:
                saved_cover = save_cover_image(form.cover_file.data, current_app.config['COVERS_FOLDER'])
                if saved_cover:
                    book.cover_image = saved_cover
            except ValueError as exc:
                flash(f'Cover error: {exc}', 'danger')
                return render_template('admin/book_form.html', form=form, mode='edit', book=book)

        if form.pdf_file.data:
            try:
                local_pdf, file_size = save_book_pdf(form.pdf_file.data, current_app.config['BOOKS_FOLDER'])
                if local_pdf:
                    book.local_file_path = local_pdf
                    book.file_size = file_size
            except ValueError as exc:
                flash(f'PDF error: {exc}', 'danger')
                return render_template('admin/book_form.html', form=form, mode='edit', book=book)

        book.title = form.title.data.strip()
        book.author = form.author.data.strip()
        book.description = form.description.data.strip()
        book.age_group_id = form.age_group_id.data
        book.category_id = form.category_id.data
        book.min_age = form.min_age.data or 0
        book.max_age = form.max_age.data or 99
        book.language = form.language.data.strip()
        book.publisher = form.publisher.data.strip() if form.publisher.data else None
        book.publication_year = form.publication_year.data
        book.isbn = normalize_isbn(form.isbn.data)
        book.pages = form.pages.data
        book.file_format = form.file_format.data
        book.reading_url = form.reading_url.data.strip() if form.reading_url.data else form.source_url.data.strip()
        book.download_url = form.download_url.data.strip() if form.download_url.data else None
        book.source_url = form.source_url.data.strip()
        book.source_repository = form.source_repository.data
        book.copyright_status = form.copyright_status.data
        book.licence = form.licence.data.strip()
        book.licence_url = form.licence_url.data.strip() if form.licence_url.data else None
        book.tags = form.tags.data.strip() if form.tags.data else ''
        book.is_readable_online = form.is_readable_online.data
        book.is_downloadable = form.is_downloadable.data
        book.redistribution_permitted = form.redistribution_permitted.data
        book.is_borrowable = form.is_borrowable.data
        book.is_exchangeable = form.is_exchangeable.data
        book.is_featured = form.is_featured.data
        book.is_verified = form.is_verified.data
        book.licence_verified = form.licence_verified.data
        if form.licence_verified.data and not book.licence_verified_at:
            book.licence_verified_at = datetime.utcnow()
        book.is_active = form.is_active.data
        book.verification_notes = form.verification_notes.data.strip() if form.verification_notes.data else None

        db.session.commit()
        flash(f'Book "{book.title}" updated!', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', form=form, mode='edit', book=book)


@admin_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@admin_required
def delete_book(book_id):
    """Deactivate or remove a book."""
    book = Book.query.get_or_404(book_id)
    title = book.title
    BorrowRecord.query.filter_by(book_id=book.id).delete()
    db.session.delete(book)
    db.session.commit()
    flash(f'Removed "{title}" from the catalogue.', 'info')
    return redirect(url_for('admin.books'))


@admin_bp.route('/books/<int:book_id>/verify-url', methods=['POST'])
@admin_required
def verify_book_url(book_id):
    """Run live HTTP verification on a book's source_url."""
    book = Book.query.get_or_404(book_id)
    ok, msg = check_live_url(book.source_url)
    if ok:
        book.is_verified = True
        book.licence_verified = True
        book.licence_verified_at = datetime.utcnow()
        book.verification_notes = f'Live source check passed ({msg}) on {datetime.utcnow().strftime("%Y-%m-%d")}.'
        flash(f'Source URL verified for "{book.title}" ({msg}).', 'success')
    else:
        book.verification_notes = f'Live source check returned: {msg}'
        flash(f'Could not reach source URL for "{book.title}": {msg}', 'warning')
    db.session.commit()
    return redirect(url_for('admin.books'))


@admin_bp.route('/catalogue', methods=['GET', 'POST'])
@admin_required
def catalogue():
    """Catalogue Import (JSON/CSV), Validation, Verification, and Reports."""
    form = CatalogueImportForm()
    import_result = None

    if form.validate_on_submit():
        uploaded = form.file.data
        filename = (uploaded.filename or '').lower()
        raw_text = uploaded.read().decode('utf-8-sig', errors='replace')
        try:
            if filename.endswith('.json'):
                import_result = import_json_data(
                    raw_text,
                    update_duplicates=form.update_duplicates.data,
                    verify_urls=form.verify_urls.data,
                )
            elif filename.endswith('.csv'):
                import_result = import_csv_data(
                    raw_text,
                    update_duplicates=form.update_duplicates.data,
                    verify_urls=form.verify_urls.data,
                )
            else:
                flash('Unsupported file type.', 'danger')
        except Exception as exc:
            flash(f'Import failed: {exc}', 'danger')

        if import_result:
            flash(
                f"Processed {import_result['total_processed']} rows: "
                f"{import_result['imported']} imported, {import_result['updated']} updated, "
                f"{import_result['skipped_duplicates']} duplicates skipped, "
                f"{len(import_result['errors'])} errors.",
                'success' if not import_result['errors'] else 'warning',
            )

    report = generate_catalogue_report()
    return render_template('admin/catalogue.html', form=form, report=report, import_result=import_result)


@admin_bp.route('/catalogue/export/json')
@admin_required
def export_json():
    """Download entire verified catalogue as JSON."""
    payload = export_catalogue_json()
    return Response(
        payload,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename="openlib_catalogue.json"'},
    )


@admin_bp.route('/catalogue/export/csv')
@admin_required
def export_csv():
    """Download entire verified catalogue as CSV."""
    payload = export_catalogue_csv()
    return Response(
        payload,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename="openlib_catalogue.csv"'},
    )


@admin_bp.route('/donations')
@admin_required
def donations():
    """Review and approve/reject book donations."""
    status_filter = request.args.get('status', '').strip()
    query = Donation.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_donations = query.order_by(Donation.created_at.desc()).all()
    return render_template('admin/donations.html', donations=all_donations, status_filter=status_filter)


@admin_bp.route('/donations/<int:donation_id>/<action>', methods=['POST'])
@admin_required
def handle_donation(donation_id, action):
    """Approve (and optionally publish to catalogue) or reject a donation."""
    donation = Donation.query.get_or_404(donation_id)
    notes = request.form.get('admin_notes', '').strip()

    if action == 'accept':
        donation.status = 'accepted'
        donation.admin_notes = notes or 'Verified and accepted into OpenLib.'

        if not donation.published_book_id and donation.source_url:
            ag_name = (donation.age_group_name or 'Adults').lower()
            ag = AgeGroup.query.filter(
                db.or_(AgeGroup.slug == ag_name, db.func.lower(AgeGroup.name) == ag_name)
            ).first() or AgeGroup.query.first()
            cat_name = donation.book_category or 'General'
            cat_slug = f"{ag.slug}-{slugify(cat_name)}" if ag else slugify(cat_name)
            cat = Category.query.filter_by(slug=cat_slug).first()
            if not cat and ag:
                cat = Category.query.filter_by(age_group_id=ag.id).first()

            new_book = Book(
                title=donation.book_title,
                author=donation.book_author,
                description=donation.book_description or f'{donation.book_title} donated by {donation.donor_name}.',
                age_group_id=ag.id if ag else None,
                category_id=cat.id if cat else None,
                min_age=ag.min_age if ag else 0,
                max_age=ag.max_age if ag else 99,
                language=donation.book_language or 'English',
                publication_year=donation.publication_year,
                publisher=donation.publisher,
                isbn=normalize_isbn(donation.isbn),
                file_format='PDF' if donation.local_file_path else 'Online/Digital',
                local_file_path=donation.local_file_path,
                reading_url=donation.file_url or donation.source_url,
                source_url=donation.source_url,
                source_repository='Community Donation',
                copyright_status='Open Access (Creative Commons)' if 'cc' in (donation.licence or '').lower() else 'Public Domain',
                licence=donation.licence or 'Public Domain',
                is_readable_online=bool(donation.is_digital),
                is_downloadable=bool(donation.local_file_path),
                redistribution_permitted=bool(donation.local_file_path),
                is_verified=True,
                licence_verified=True,
                licence_verified_at=datetime.utcnow(),
                is_active=True,
            )
            db.session.add(new_book)
            db.session.flush()
            new_book.book_code = f'OL-{new_book.id:05d}'
            donation.published_book_id = new_book.id

        flash(f'Donation "{donation.book_title}" accepted!', 'success')
    elif action == 'reject':
        donation.status = 'rejected'
        donation.admin_notes = notes or 'Unable to verify copyright/licence permissions.'
        flash(f'Donation "{donation.book_title}" marked rejected.', 'info')

    db.session.commit()
    return redirect(url_for('admin.donations'))


@admin_bp.route('/users')
@admin_required
def users():
    """Manage registered members."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own admin account.', 'warning')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {user.username} is now {"active" if user.is_active else "inactive"}.', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'user')
    if new_role in ('user', 'moderator', 'admin'):
        if user.id == current_user.id and new_role != 'admin':
            flash('You cannot demote your own active admin account.', 'warning')
        else:
            user.role = new_role
            db.session.commit()
            flash(f'Updated {user.username} role to {new_role}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/transactions')
@admin_required
def transactions():
    """Manage borrowing records and community exchange requests."""
    borrows = BorrowRecord.query.order_by(BorrowRecord.borrowed_at.desc()).limit(100).all()
    exchanges = ExchangeRequest.query.order_by(ExchangeRequest.created_at.desc()).limit(100).all()
    return render_template('admin/transactions.html', borrows=borrows, exchanges=exchanges)


@admin_bp.route('/messages')
@admin_required
def messages():
    """View contact form inquiries."""
    all_msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=all_msgs)


@admin_bp.route('/messages/<int:msg_id>/read', methods=['POST'])
@admin_required
def mark_message_read(msg_id):
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('admin.messages'))

