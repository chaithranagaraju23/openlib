"""User model for OpenLib."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    """User model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128))
    avatar = db.Column(db.String(256), default='default_avatar.svg')
    bio = db.Column(db.Text)
    preferred_language = db.Column(db.String(20), default='English')
    preferred_age_group = db.Column(db.String(20), default='adults')

    # Roles
    role = db.Column(db.String(20), default='user')  # user, admin, moderator

    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_confirmed = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Accessibility
    large_text = db.Column(db.Boolean, default=False)
    high_contrast = db.Column(db.Boolean, default=False)
    text_to_speech = db.Column(db.Boolean, default=False)
    night_mode = db.Column(db.Boolean, default=False)

    # Relationships
    borrow_records = db.relationship('BorrowRecord', back_populates='user', lazy='dynamic')
    exchange_listings = db.relationship('ExchangeListing', back_populates='owner', lazy='dynamic')
    exchange_requests_sent = db.relationship('ExchangeRequest',
                                              foreign_keys='ExchangeRequest.requester_id',
                                              back_populates='requester', lazy='dynamic')
    exchange_requests_received = db.relationship('ExchangeRequest',
                                                  foreign_keys='ExchangeRequest.owner_id',
                                                  back_populates='owner', lazy='dynamic')
    donations = db.relationship('Donation', back_populates='donor', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='user', lazy='dynamic')
    bookmarks = db.relationship('Bookmark', back_populates='user', lazy='dynamic')
    reader_bookmarks = db.relationship('ReaderBookmark', back_populates='user', lazy='dynamic')
    reading_progress = db.relationship('ReadingProgress', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_moderator(self):
        return self.role in ('admin', 'moderator')

    def get_borrowed_books_count(self):
        return self.borrow_records.filter_by(status='borrowed').count()

    def get_reading_list(self):
        return [b.book for b in self.bookmarks.all()]

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
