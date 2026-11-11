"""Book models for OpenLib."""
from datetime import datetime
import os
from app import db


class AgeGroup(db.Model):
    """Age group model for the four library sections."""
    __tablename__ = 'age_groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    icon = db.Column(db.String(50))
    color_class = db.Column(db.String(50))
    bg_color = db.Column(db.String(20))
    sort_order = db.Column(db.Integer, default=0)

    # Relationships
    books = db.relationship('Book', back_populates='age_group', lazy='dynamic')
    categories = db.relationship('Category', back_populates='age_group', lazy='dynamic')

    def get_book_count(self):
        return self.books.filter_by(is_active=True, is_verified=True).count()

    def __repr__(self):
        return f'<AgeGroup {self.name}>'


class Category(db.Model):
    """Book category model."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='bi-folder')
    age_group_id = db.Column(db.Integer, db.ForeignKey('age_groups.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    age_group = db.relationship('AgeGroup', back_populates='categories')
    books = db.relationship('Book', back_populates='category', lazy='dynamic')

    def get_book_count(self):
        return self.books.filter_by(is_active=True, is_verified=True).count()

    def __repr__(self):
        return f'<Category {self.name}>'


class Book(db.Model):
    """Book model storing verified catalogue metadata and licensing details."""
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    book_code = db.Column(db.String(32), unique=True, index=True)

    # Basic info
    title = db.Column(db.String(300), nullable=False, index=True)
    author = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(500), default='default_cover.svg')

    # Classification
    age_group_id = db.Column(db.Integer, db.ForeignKey('age_groups.id'), index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)
    min_age = db.Column(db.Integer, default=0)
    max_age = db.Column(db.Integer, default=99)
    language = db.Column(db.String(50), default='English', index=True)
    language_code = db.Column(db.String(10), default='en')

    # Publication details
    publisher = db.Column(db.String(200))
    publication_year = db.Column(db.Integer, index=True)
    isbn = db.Column(db.String(32), index=True)
    pages = db.Column(db.Integer)
    edition = db.Column(db.String(50))

    # File information
    file_format = db.Column(db.String(30), default='HTML/PDF', index=True)
    file_size = db.Column(db.String(30))
    local_file_path = db.Column(db.String(500))  # Relative path inside data/books/ if hosted locally

    # Access URLs & Provenance
    reading_url = db.Column(db.String(1000))        # Official online reading / borrowing page or PDF URL
    download_url = db.Column(db.String(1000))       # Authorized download URL if permitted
    source_url = db.Column(db.String(1000))         # Original verifiable source page URL
    source_repository = db.Column(db.String(100))   # e.g., Project Gutenberg, Internet Archive, DOAB, Wikisource, StoryWeaver, OpenStax
    gutenberg_id = db.Column(db.String(32))

    # Permissions
    is_readable_online = db.Column(db.Boolean, default=True)
    is_downloadable = db.Column(db.Boolean, default=False)
    redistribution_permitted = db.Column(db.Boolean, default=False)
    is_borrowable = db.Column(db.Boolean, default=True)
    is_exchangeable = db.Column(db.Boolean, default=False)

    # Copyright & Licensing
    copyright_status = db.Column(db.String(100), default='Public Domain')
    licence = db.Column(db.String(200), default='Public Domain')
    licence_url = db.Column(db.String(500))
    licence_verified = db.Column(db.Boolean, default=True)
    licence_verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    verification_notes = db.Column(db.Text)

    # Stats
    view_count = db.Column(db.Integer, default=0)
    borrow_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=True)

    # Timestamps
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Tags (comma-separated)
    tags = db.Column(db.Text, default='')

    # Relationships
    age_group = db.relationship('AgeGroup', back_populates='books')
    category = db.relationship('Category', back_populates='books')
    borrow_records = db.relationship('BorrowRecord', back_populates='book', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='book', lazy='dynamic')
    bookmarks = db.relationship('Bookmark', back_populates='book', lazy='dynamic')
    reader_bookmarks = db.relationship('ReaderBookmark', back_populates='book', lazy='dynamic')
    reading_progress = db.relationship('ReadingProgress', back_populates='book', lazy='dynamic')

    def get_display_id(self):
        return self.book_code or f'OL-{self.id:05d}'

    def has_local_pdf(self):
        if not self.local_file_path:
            return False
        from flask import current_app
        full_path = os.path.join(current_app.config['BOOKS_FOLDER'], self.local_file_path)
        return os.path.isfile(full_path)

    def increment_view(self):
        self.view_count = (self.view_count or 0) + 1
        db.session.add(self)

    def update_rating(self):
        from app.models.review import Review
        reviews = Review.query.filter_by(book_id=self.id, is_approved=True).all()
        if reviews:
            self.average_rating = round(sum(r.rating for r in reviews) / len(reviews), 2)
            self.review_count = len(reviews)
        else:
            self.average_rating = 0.0
            self.review_count = 0
        db.session.add(self)

    def get_tags_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    def get_cover_url(self):
        from flask import url_for, current_app
        if self.cover_image and self.cover_image != 'default_cover.svg':
            if self.cover_image.startswith('http://') or self.cover_image.startswith('https://'):
                return self.cover_image
            cover_path = os.path.join(current_app.config.get('COVERS_FOLDER', ''), self.cover_image)
            if os.path.isfile(cover_path):
                return url_for('static', filename=f'covers/{self.cover_image}')
        return url_for('static', filename='images/default_cover.svg')

    def to_dict(self):
        return {
            'id': self.id,
            'book_code': self.get_display_id(),
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'age_group': self.age_group.name if self.age_group else None,
            'min_age': self.min_age,
            'max_age': self.max_age,
            'category': self.category.name if self.category else None,
            'language': self.language,
            'publication_year': self.publication_year,
            'publisher': self.publisher,
            'isbn': self.isbn,
            'file_format': self.file_format,
            'reading_url': self.reading_url,
            'local_file_path': self.local_file_path,
            'source_url': self.source_url,
            'source_repository': self.source_repository,
            'is_readable_online': self.is_readable_online,
            'is_downloadable': self.is_downloadable,
            'redistribution_permitted': self.redistribution_permitted,
            'copyright_status': self.copyright_status,
            'licence': self.licence,
            'licence_url': self.licence_url,
            'licence_verified': self.licence_verified,
            'date_added': self.date_added.isoformat() if self.date_added else None,
        }

    def __repr__(self):
        return f'<Book {self.title}>'
