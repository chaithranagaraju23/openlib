"""User dashboard, profile, accessibility settings, reading list, exchanges, and donations."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models.transaction import BorrowRecord, ExchangeListing, ExchangeRequest, Donation
from app.models.review import Bookmark, ReadingProgress, Review
from app.forms.auth_forms import ProfileUpdateForm, PasswordChangeForm

user_bp = Blueprint('user', __name__)


@user_bp.route('/dashboard')
@login_required
def dashboard():
    """Member personal library dashboard."""
    active_borrows = (
        BorrowRecord.query.filter_by(user_id=current_user.id, status='borrowed')
        .order_by(BorrowRecord.due_date.asc())
        .all()
    )
    borrow_history = (
        BorrowRecord.query.filter(
            BorrowRecord.user_id == current_user.id,
            BorrowRecord.status != 'borrowed',
        )
        .order_by(BorrowRecord.borrowed_at.desc())
        .limit(10)
        .all()
    )
    bookmarks = (
        Bookmark.query.filter_by(user_id=current_user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    progress_list = (
        ReadingProgress.query.filter_by(user_id=current_user.id)
        .order_by(ReadingProgress.last_read.desc())
        .limit(8)
        .all()
    )
    donations = (
        Donation.query.filter_by(donor_id=current_user.id)
        .order_by(Donation.created_at.desc())
        .all()
    )
    incoming_exchanges = (
        ExchangeRequest.query.filter_by(owner_id=current_user.id, status='pending')
        .order_by(ExchangeRequest.created_at.desc())
        .all()
    )
    outgoing_exchanges = (
        ExchangeRequest.query.filter_by(requester_id=current_user.id)
        .order_by(ExchangeRequest.created_at.desc())
        .limit(5)
        .all()
    )
    reviews_count = Review.query.filter_by(user_id=current_user.id).count()

    return render_template(
        'user/dashboard.html',
        active_borrows=active_borrows,
        borrow_history=borrow_history,
        bookmarks=bookmarks,
        progress_list=progress_list,
        donations=donations,
        incoming_exchanges=incoming_exchanges,
        outgoing_exchanges=outgoing_exchanges,
        reviews_count=reviews_count,
    )


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Edit profile and accessibility preferences."""
    form = ProfileUpdateForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.bio = form.bio.data.strip() if form.bio.data else ''
        current_user.preferred_language = form.preferred_language.data
        current_user.preferred_age_group = form.preferred_age_group.data
        current_user.large_text = form.large_text.data
        current_user.high_contrast = form.high_contrast.data
        current_user.text_to_speech = form.text_to_speech.data
        current_user.night_mode = form.night_mode.data
        db.session.commit()
        flash('Profile and accessibility preferences updated!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html', form=form)


@user_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Your current password is incorrect.', 'danger')
            return render_template('user/change_password.html', form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Your password has been updated securely.', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/change_password.html', form=form)


@user_bp.route('/reading-list')
@login_required
def reading_list():
    """Saved bookmarks and reading progress."""
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.created_at.desc()).all()
    progress_list = ReadingProgress.query.filter_by(user_id=current_user.id).order_by(ReadingProgress.last_read.desc()).all()
    return render_template('user/reading_list.html', bookmarks=bookmarks, progress_list=progress_list)


@user_bp.route('/exchanges')
@login_required
def exchanges():
    """Manage user's exchange listings and incoming/outgoing requests."""
    my_listings = ExchangeListing.query.filter_by(user_id=current_user.id).order_by(ExchangeListing.created_at.desc()).all()
    incoming = ExchangeRequest.query.filter_by(owner_id=current_user.id).order_by(ExchangeRequest.created_at.desc()).all()
    outgoing = ExchangeRequest.query.filter_by(requester_id=current_user.id).order_by(ExchangeRequest.created_at.desc()).all()
    return render_template('user/exchanges.html', my_listings=my_listings, incoming=incoming, outgoing=outgoing)


@user_bp.route('/exchange-request/<int:req_id>/<action>', methods=['POST'])
@login_required
def handle_exchange_request(req_id, action):
    """Accept, reject, complete, or cancel an exchange request."""
    req_obj = ExchangeRequest.query.get_or_404(req_id)

    if action in ('accept', 'reject', 'complete'):
        if req_obj.owner_id != current_user.id:
            flash('Only the book owner can perform this action.', 'danger')
            return redirect(url_for('user.exchanges'))
        if action == 'accept':
            req_obj.status = 'accepted'
            req_obj.owner_response = request.form.get('response', '').strip() or 'Accepted! Let us coordinate delivery.'
            if req_obj.listing:
                req_obj.listing.status = 'reserved'
            flash('Exchange request accepted!', 'success')
        elif action == 'reject':
            req_obj.status = 'rejected'
            req_obj.owner_response = request.form.get('response', '').strip() or 'Declined at this time.'
            flash('Exchange request declined.', 'info')
        elif action == 'complete':
            req_obj.status = 'completed'
            if req_obj.listing:
                req_obj.listing.status = 'exchanged'
            flash('Book exchange marked as completed!', 'success')
    elif action == 'cancel':
        if req_obj.requester_id != current_user.id:
            flash('Only the requester can cancel this proposal.', 'danger')
            return redirect(url_for('user.exchanges'))
        req_obj.status = 'cancelled'
        flash('Exchange proposal cancelled.', 'info')
    else:
        flash('Unknown exchange action.', 'warning')
        return redirect(url_for('user.exchanges'))

    db.session.commit()
    return redirect(url_for('user.exchanges'))


@user_bp.route('/exchange-listing/<int:listing_id>/toggle', methods=['POST'])
@login_required
def toggle_listing(listing_id):
    """Pause or re-activate own exchange listing."""
    listing = ExchangeListing.query.get_or_404(listing_id)
    if listing.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('user.exchanges'))
    listing.status = 'inactive' if listing.status == 'available' else 'available'
    db.session.commit()
    flash(f'Listing status updated to {listing.status}.', 'info')
    return redirect(url_for('user.exchanges'))


@user_bp.route('/donations')
@login_required
def donations():
    """View personal book donations."""
    user_donations = Donation.query.filter_by(donor_id=current_user.id).order_by(Donation.created_at.desc()).all()
    return render_template('user/donations.html', donations=user_donations)

