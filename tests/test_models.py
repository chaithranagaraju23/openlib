"""Tests for OpenLib models, password hashing, borrowing, and ratings."""
from app import db
from app.models.user import User
from app.models.book import Book
from app.models.transaction import BorrowRecord
from app.models.review import Review


def test_user_password_hashing(app):
    with app.app_context():
        u = User(username='hashcheck', email='hash@test.org')
        u.set_password('SecretPass123!')
        assert u.password_hash != 'SecretPass123!'
        assert u.check_password('SecretPass123!') is True
        assert u.check_password('WrongPass') is False


def test_borrow_renewal_limit(app):
    with app.app_context():
        user = User.query.filter_by(username='reader_test').first()
        book = Book.query.first()
        rec = BorrowRecord(user_id=user.id, book_id=book.id)
        db.session.add(rec)
        db.session.commit()

        assert rec.renew() is True
        assert rec.renew() is True
        assert rec.renew() is False
        assert rec.renewal_count == 2


def test_book_rating_aggregation(app):
    with app.app_context():
        user1 = User.query.filter_by(username='reader_test').first()
        user2 = User.query.filter_by(username='owner_test').first()
        book = Book.query.first()
        db.session.add_all([
            Review(user_id=user1.id, book_id=book.id, rating=5, title='Great', content='Wonderful fables!', is_approved=True),
            Review(user_id=user2.id, book_id=book.id, rating=3, title='Good', content='Helpful collection.', is_approved=True),
        ])
        db.session.flush()
        book.update_rating()
        db.session.commit()

        assert book.review_count == 2
        assert book.average_rating == 4.0

