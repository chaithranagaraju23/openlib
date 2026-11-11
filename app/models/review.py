"""Review, Bookmark, and Reading Progress models for OpenLib."""
from datetime import datetime
from app import db


class Review(db.Model):
    """Book review model."""
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='reviews')
    book = db.relationship('Book', back_populates='reviews')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_review'),
    )

    def __repr__(self):
        return f'<Review book={self.book_id} user={self.user_id} rating={self.rating}>'


class Bookmark(db.Model):
    """User bookmarks / reading list."""
    __tablename__ = 'bookmarks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', back_populates='bookmarks')
    book = db.relationship('Book', back_populates='bookmarks')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_bookmark'),
    )

    def __repr__(self):
        return f'<Bookmark user={self.user_id} book={self.book_id}>'


class ReaderBookmark(db.Model):
    """Per-page bookmarks saved inside the online reader."""
    __tablename__ = 'reader_bookmarks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(150))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='reader_bookmarks')
    book = db.relationship('Book', back_populates='reader_bookmarks')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', 'page_number', name='unique_user_book_page_bookmark'),
    )

    def __repr__(self):
        return f'<ReaderBookmark user={self.user_id} book={self.book_id} page={self.page_number}>'


class ReadingProgress(db.Model):
    """Track reading progress."""
    __tablename__ = 'reading_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    current_page = db.Column(db.Integer, default=1)
    total_pages = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    last_read = db.Column(db.DateTime, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship('User', back_populates='reading_progress')
    book = db.relationship('Book', back_populates='reading_progress')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_progress'),
    )

    def __repr__(self):
        return f'<ReadingProgress user={self.user_id} book={self.book_id} page={self.current_page}>'
