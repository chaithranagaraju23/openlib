"""Transaction models for OpenLib - Borrowing, Exchange, Donation, Contact."""
from datetime import datetime, timedelta
from app import db


class BorrowRecord(db.Model):
    """Borrow record model."""
    __tablename__ = 'borrow_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    status = db.Column(db.String(20), default='borrowed')  # borrowed, returned, overdue, cancelled
    borrowed_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    returned_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    renewal_count = db.Column(db.Integer, default=0)

    # Relationships
    user = db.relationship('User', back_populates='borrow_records')
    book = db.relationship('Book', back_populates='borrow_records')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.due_date:
            self.due_date = datetime.utcnow() + timedelta(days=14)

    def is_overdue(self):
        return self.status == 'borrowed' and datetime.utcnow() > self.due_date

    def days_remaining(self):
        if self.status == 'borrowed' and self.due_date:
            delta = self.due_date - datetime.utcnow()
            return max(0, delta.days)
        return 0

    def renew(self):
        if self.renewal_count < 2 and self.status == 'borrowed':
            self.due_date = self.due_date + timedelta(days=14)
            self.renewal_count += 1
            return True
        return False

    def __repr__(self):
        return f'<BorrowRecord user={self.user_id} book={self.book_id}>'


class ExchangeListing(db.Model):
    """Community book exchange listing posted by a member."""
    __tablename__ = 'exchange_listings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)

    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(32))
    language = db.Column(db.String(50), default='English')
    age_group_name = db.Column(db.String(50), default='Adult')
    category_name = db.Column(db.String(100))
    condition = db.Column(db.String(50), default='Good')  # New, Like New, Good, Fair
    location = db.Column(db.String(120))
    delivery_method = db.Column(db.String(50), default='Local Meetup or Mail')
    looking_for = db.Column(db.String(300))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='available')  # available, reserved, exchanged, inactive

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = db.relationship('User', back_populates='exchange_listings')
    book = db.relationship('Book')
    requests = db.relationship('ExchangeRequest', back_populates='listing', lazy='dynamic')

    def __repr__(self):
        return f'<ExchangeListing {self.title} by user={self.user_id}>'


class ExchangeRequest(db.Model):
    """Book exchange request model."""
    __tablename__ = 'exchange_requests'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('exchange_listings.id'), nullable=True)
    offered_book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)
    requested_book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)

    offered_book_title = db.Column(db.String(300))
    offered_book_author = db.Column(db.String(200))
    offered_book_condition = db.Column(db.String(50), default='Good')

    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, completed, cancelled
    message = db.Column(db.Text)
    owner_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], back_populates='exchange_requests_sent')
    owner = db.relationship('User', foreign_keys=[owner_id], back_populates='exchange_requests_received')
    listing = db.relationship('ExchangeListing', back_populates='requests')
    offered_book = db.relationship('Book', foreign_keys=[offered_book_id])
    requested_book = db.relationship('Book', foreign_keys=[requested_book_id])

    def __repr__(self):
        return f'<ExchangeRequest {self.id}>'


class Donation(db.Model):
    """Book donation model."""
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    donor_name = db.Column(db.String(128))
    donor_email = db.Column(db.String(128))

    # Book info
    book_title = db.Column(db.String(300), nullable=False)
    book_author = db.Column(db.String(200), nullable=False)
    book_description = db.Column(db.Text)
    book_condition = db.Column(db.String(50))
    book_language = db.Column(db.String(50), default='English')
    book_category = db.Column(db.String(100))
    age_group_name = db.Column(db.String(50), default='Adult')
    isbn = db.Column(db.String(32))
    publication_year = db.Column(db.Integer)
    publisher = db.Column(db.String(200))
    file_format = db.Column(db.String(30), default='PDF')

    # Digital donation
    is_digital = db.Column(db.Boolean, default=True)
    file_url = db.Column(db.String(500))
    local_file_path = db.Column(db.String(500))
    source_url = db.Column(db.String(500))
    licence = db.Column(db.String(200), default='Public Domain')
    copyright_confirmation = db.Column(db.Boolean, default=False)

    # Physical donation
    is_physical = db.Column(db.Boolean, default=False)
    shipping_address = db.Column(db.Text)

    # Status
    status = db.Column(db.String(20), default='pending')  # pending, reviewing, accepted, rejected
    admin_notes = db.Column(db.Text)
    published_book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    donor = db.relationship('User', back_populates='donations')
    published_book = db.relationship('Book', foreign_keys=[published_book_id])

    def __repr__(self):
        return f'<Donation {self.book_title}>'


class ContactMessage(db.Model):
    """Contact form messages."""
    __tablename__ = 'contact_messages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContactMessage from={self.email}>'
