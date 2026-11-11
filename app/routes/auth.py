"""Authentication routes: login, register, logout."""
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User
from app.forms.auth_forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)


def _is_safe_redirect(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return (not test_url.scheme and not test_url.netloc) or (
        test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Sign in existing member."""
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        ident = form.email_or_username.data.strip()
        user = User.query.filter(
            db.or_(
                db.func.lower(User.email) == ident.lower(),
                db.func.lower(User.username) == ident.lower(),
            )
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account is currently deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            user.ping()
            db.session.commit()
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')

            next_page = request.args.get('next')
            if _is_safe_redirect(next_page):
                return redirect(next_page)
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))

        flash('Invalid email/username or password. Please try again.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Create a free OpenLib reader account."""
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            preferred_age_group=form.preferred_age_group.data,
            preferred_language=form.preferred_language.data,
            role='user',
            is_active=True,
            is_verified=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Welcome to OpenLib! Your free digital library account is ready.', 'success')
        return redirect(url_for('user.dashboard'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Sign out current user."""
    logout_user()
    flash('You have been signed out cleanly.', 'info')
    return redirect(url_for('main.index'))

