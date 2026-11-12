"""Main public routes: homepage, about, contact, donate, community exchange."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.models.book import AgeGroup, Category, Book
from app.models.user import User
from app.models.transaction import Donation, ExchangeListing, ContactMessage, BorrowRecord
from app.forms.book_forms import ContactForm, DonationForm, ExchangeListingForm
from app.services.email_service import send_contact_notification
from app.utils.helpers import save_book_pdf

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """OpenLib homepage."""
    active_verified = (Book.is_active == True) & (Book.is_verified == True)

    age_groups = AgeGroup.query.order_by(AgeGroup.sort_order).all()
    age_group_cards = [
        {
            'group': ag,
            'book_count': ag.get_book_count(),
            'category_count': ag.categories.filter_by(is_active=True).count(),
        }
        for ag in age_groups
    ]

    featured_books = (
        Book.query.filter(active_verified, Book.is_featured == True)
        .order_by(Book.date_added.desc())
        .limit(8)
        .all()
    )
    if len(featured_books) < 8:
        existing_ids = [b.id for b in featured_books]
        extra = (
            Book.query.filter(active_verified, ~Book.id.in_(existing_ids) if existing_ids else True)
            .order_by(Book.view_count.desc(), Book.id.asc())
            .limit(8 - len(featured_books))
            .all()
        )
        featured_books.extend(extra)

    recent_books = (
        Book.query.filter(active_verified)
        .order_by(Book.date_added.desc(), Book.id.desc())
        .limit(8)
        .all()
    )

    popular_books = (
        Book.query.filter(active_verified)
        .order_by((Book.view_count + Book.borrow_count * 2).desc(), Book.average_rating.desc(), Book.id.asc())
        .limit(8)
        .all()
    )

    # Top categories with actual counts
    category_counts = (
        db.session.query(Category, AgeGroup, func.count(Book.id).label('book_count'))
        .join(AgeGroup, Category.age_group_id == AgeGroup.id)
        .outerjoin(Book, (Book.category_id == Category.id) & active_verified)
        .filter(Category.is_active == True)
        .group_by(Category.id, AgeGroup.id)
        .order_by(AgeGroup.sort_order, Category.sort_order)
        .all()
    )

    language_counts = (
        db.session.query(Book.language, func.count(Book.id).label('cnt'))
        .filter(active_verified, Book.language != None)
        .group_by(Book.language)
        .order_by(func.count(Book.id).desc())
        .all()
    )

    stats = {
        'total_books': Book.query.filter(active_verified).count(),
        'total_categories': Category.query.filter_by(is_active=True).count(),
        'total_languages': len(language_counts),
        'total_members': User.query.filter_by(is_active=True).count(),
        'total_donations': Donation.query.count(),
        'active_exchanges': ExchangeListing.query.filter_by(status='available').count(),
        'total_borrows': BorrowRecord.query.count(),
    }

    recent_exchanges = (
        ExchangeListing.query.filter_by(status='available')
        .order_by(ExchangeListing.created_at.desc())
        .limit(4)
        .all()
    )

    return render_template(
        'index.html',
        age_group_cards=age_group_cards,
        featured_books=featured_books,
        recent_books=recent_books,
        popular_books=popular_books,
        category_counts=category_counts,
        language_counts=language_counts,
        stats=stats,
        recent_exchanges=recent_exchanges,
    )


@main_bp.route('/about')
def about():
    """About OpenLib mission, licensing standards, and real statistics."""
    active_verified = (Book.is_active == True) & (Book.is_verified == True)
    repo_counts = (
        db.session.query(Book.source_repository, func.count(Book.id))
        .filter(active_verified)
        .group_by(Book.source_repository)
        .order_by(func.count(Book.id).desc())
        .all()
    )
    stats = {
        'total_books': Book.query.filter(active_verified).count(),
        'total_categories': Category.query.filter_by(is_active=True).count(),
        'total_languages': db.session.query(func.count(func.distinct(Book.language))).filter(active_verified).scalar() or 0,
        'total_donations': Donation.query.filter_by(status='accepted').count(),
        'age_groups': AgeGroup.query.order_by(AgeGroup.sort_order).all(),
        'repo_counts': repo_counts,
    }
    return render_template('about.html', stats=stats)


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact OpenLib team."""
    form = ContactForm()
    if current_user.is_authenticated and request.method == 'GET':
        form.name.data = current_user.full_name or current_user.username
        form.email.data = current_user.email

    if form.validate_on_submit():
        msg = ContactMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip(),
            subject=form.subject.data.strip(),
            message=form.message.data.strip(),
        )
        db.session.add(msg)
        db.session.commit()
        send_contact_notification(msg)
        flash('Thank you for contacting OpenLib! Your message has been received by our team.', 'success')
        return redirect(url_for('main.contact'))

    return render_template('contact.html', form=form)


@main_bp.route('/donate', methods=['GET', 'POST'])
def donate():
    """Public book donation portal (digital & physical)."""
    form = DonationForm()
    if current_user.is_authenticated and request.method == 'GET':
        form.donor_name.data = current_user.full_name or current_user.username
        form.donor_email.data = current_user.email

    if form.validate_on_submit():
        is_digital = form.donation_type.data == 'digital'
        local_pdf = None
        if is_digital and form.pdf_file.data:
            try:
                local_pdf, _ = save_book_pdf(form.pdf_file.data, current_app.config['BOOKS_FOLDER'])
            except ValueError as exc:
                flash(f'PDF upload error: {exc}', 'danger')
                return render_template('donate.html', form=form)

        donation = Donation(
            donor_id=current_user.id if current_user.is_authenticated else None,
            donor_name=form.donor_name.data.strip(),
            donor_email=form.donor_email.data.strip(),
            book_title=form.book_title.data.strip(),
            book_author=form.book_author.data.strip(),
            book_description=form.book_description.data.strip(),
            book_condition='Digital' if is_digital else form.book_condition.data,
            book_language=form.book_language.data.strip(),
            book_category=form.book_category.data.strip(),
            age_group_name=form.age_group_name.data,
            isbn=form.isbn.data.strip() if form.isbn.data else None,
            publication_year=form.publication_year.data,
            publisher=form.publisher.data.strip() if form.publisher.data else None,
            is_digital=is_digital,
            is_physical=not is_digital,
            file_url=form.file_url.data.strip() if form.file_url.data else None,
            local_file_path=local_pdf,
            source_url=form.source_url.data.strip() if form.source_url.data else None,
            licence=form.licence.data.strip(),
            copyright_confirmation=bool(form.copyright_confirmation.data),
            shipping_address=form.shipping_address.data.strip() if form.shipping_address.data else None,
            status='pending',
        )
        db.session.add(donation)
        db.session.commit()
        flash('Thank you for your generous donation! Our librarians will verify the licence and details shortly.', 'success')
        return redirect(url_for('main.donate'))

    recent_accepted = (
        Donation.query.filter_by(status='accepted')
        .order_by(Donation.created_at.desc())
        .limit(6)
        .all()
    )
    total_accepted = Donation.query.filter_by(status='accepted').count()
    return render_template(
        'donate.html',
        form=form,
        recent_accepted=recent_accepted,
        total_accepted=total_accepted,
    )


@main_bp.route('/exchange', methods=['GET', 'POST'])
def exchange():
    """Community book exchange marketplace."""
    listing_form = ExchangeListingForm()

    if listing_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please sign in to publish a book exchange listing.', 'warning')
            return redirect(url_for('auth.login', next=url_for('main.exchange')))

        listing = ExchangeListing(
            user_id=current_user.id,
            title=listing_form.title.data.strip(),
            author=listing_form.author.data.strip(),
            isbn=listing_form.isbn.data.strip() if listing_form.isbn.data else None,
            language=listing_form.language.data.strip(),
            age_group_name=listing_form.age_group_name.data,
            category_name=listing_form.category_name.data.strip() if listing_form.category_name.data else None,
            condition=listing_form.condition.data,
            location=listing_form.location.data.strip(),
            delivery_method=listing_form.delivery_method.data,
            looking_for=listing_form.looking_for.data.strip() if listing_form.looking_for.data else None,
            notes=listing_form.notes.data.strip() if listing_form.notes.data else None,
            status='available',
        )
        db.session.add(listing)
        db.session.commit()
        flash('Your book has been listed for community exchange!', 'success')
        return redirect(url_for('main.exchange'))

    q = request.args.get('q', '').strip()
    age_filter = request.args.get('age_group', '').strip()
    condition_filter = request.args.get('condition', '').strip()
    page = request.args.get('page', 1, type=int)

    query = ExchangeListing.query.filter_by(status='available')
    if q:
        like_q = f'%{q}%'
        query = query.filter(
            db.or_(
                ExchangeListing.title.ilike(like_q),
                ExchangeListing.author.ilike(like_q),
                ExchangeListing.location.ilike(like_q),
                ExchangeListing.looking_for.ilike(like_q),
            )
        )
    if age_filter:
        query = query.filter(ExchangeListing.age_group_name == age_filter)
    if condition_filter:
        query = query.filter(ExchangeListing.condition == condition_filter)

    pagination = query.order_by(ExchangeListing.created_at.desc()).paginate(page=page, per_page=12, error_out=False)

    return render_template(
        'exchange.html',
        listings=pagination.items,
        pagination=pagination,
        listing_form=listing_form,
        q=q,
        age_filter=age_filter,
        condition_filter=condition_filter,
    )

