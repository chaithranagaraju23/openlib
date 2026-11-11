"""Pytest / unittest test fixtures for OpenLib."""
import os
import pytest

from app import create_app, db
from app.models.user import User
from app.models.book import AgeGroup, Category, Book
from app.services.seeder import seed_age_groups_and_categories


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        seed_age_groups_and_categories()

        admin = User(username='admin_test', email='admin@test.org', full_name='Test Admin', role='admin', is_active=True)
        admin.set_password('AdminTest@123')
        user = User(username='reader_test', email='reader@test.org', full_name='Test Reader', role='user', is_active=True)
        user.set_password('ReaderTest@123')
        other = User(username='owner_test', email='owner@test.org', full_name='Book Owner', role='user', is_active=True)
        other.set_password('OwnerTest@123')
        db.session.add_all([admin, user, other])

        ag_child = AgeGroup.query.filter_by(slug='children').first()
        cat_moral = Category.query.filter_by(slug='children-moral-stories').first()
        ag_youth = AgeGroup.query.filter_by(slug='youth').first()
        cat_prog = Category.query.filter_by(slug='youth-programming-and-computer-science').first()

        b1 = Book(
            book_code='OL-00001',
            title="Aesop's Fables",
            author='Aesop',
            description='Classic moral fables for children.',
            age_group_id=ag_child.id,
            category_id=cat_moral.id,
            min_age=5,
            max_age=12,
            language='English',
            publication_year=1912,
            isbn='9780140446494',
            file_format='PDF/HTML',
            reading_url='https://www.gutenberg.org/ebooks/21',
            source_url='https://www.gutenberg.org/ebooks/21',
            source_repository='Project Gutenberg',
            gutenberg_id='21',
            is_readable_online=True,
            is_downloadable=True,
            redistribution_permitted=True,
            is_borrowable=True,
            copyright_status='Public Domain',
            licence='Public Domain',
            licence_verified=True,
            is_featured=True,
            is_verified=True,
            is_active=True,
        )
        b2 = Book(
            book_code='OL-00002',
            title='Think Python',
            author='Allen B. Downey',
            description='Introduction to Python programming.',
            age_group_id=ag_youth.id,
            category_id=cat_prog.id,
            min_age=13,
            max_age=24,
            language='English',
            publication_year=2015,
            isbn='9781491939369',
            file_format='PDF',
            reading_url='https://archive.org/details/thinkpython',
            source_url='https://archive.org/details/thinkpython',
            source_repository='Internet Archive',
            is_readable_online=True,
            is_downloadable=False,
            redistribution_permitted=False,
            is_borrowable=True,
            copyright_status='Open Access (Creative Commons)',
            licence='CC BY-NC-SA 3.0',
            licence_verified=True,
            is_featured=True,
            is_verified=True,
            is_active=True,
        )
        db.session.add_all([b1, b2])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()

