"""Tests for admin authorization, JSON/CSV catalogue import, duplicate detection, and reporting."""
import io
import json
from app.models.book import Book
from app.services.catalogue_manager import import_json_data, import_csv_data, generate_catalogue_report


def test_admin_access_protection(client):
    # Unauthenticated redirected
    res = client.get('/admin/')
    assert res.status_code == 302

    # Normal user gets 403 Forbidden
    client.post('/auth/login', data={'email_or_username': 'reader_test', 'password': 'ReaderTest@123'})
    res = client.get('/admin/')
    assert res.status_code == 403


def test_catalogue_import_deduplication_and_validation(app):
    with app.app_context():
        payload = json.dumps([
            {
                'title': "Aesop's Fables",
                'author': 'Aesop',
                'age_group': 'Children',
                'category': 'Moral Stories',
                'language': 'English',
                'source_url': 'https://www.gutenberg.org/ebooks/21',
                'licence': 'Public Domain',
            },
            {
                'title': 'Alice in Wonderland',
                'author': 'Lewis Carroll',
                'age_group': 'Children',
                'category': 'Fairy Tales',
                'language': 'English',
                'source_url': 'https://www.gutenberg.org/ebooks/11',
                'licence': 'Public Domain',
            },
            {
                'title': 'Bad Record Missing URL',
                'author': 'No One',
                'age_group': 'Children',
                'category': 'Fairy Tales',
                'language': 'English',
                'source_url': 'not-a-valid-url',
                'licence': 'Public Domain',
            }
        ])
        report = import_json_data(payload, update_duplicates=False, verify_urls=True)
        assert report['imported'] == 1
        assert report['skipped_duplicates'] == 1
        assert len(report['errors']) == 1

        csv_text = (
            "title,author,age_group,category,language,source_url,licence\n"
            "The Jungle Book,Rudyard Kipling,Children,Adventure Stories,English,https://www.gutenberg.org/ebooks/236,Public Domain\n"
        )
        csv_report = import_csv_data(csv_text)
        assert csv_report['imported'] == 1
        assert Book.query.filter_by(title='The Jungle Book').first() is not None

        audit = generate_catalogue_report()
        assert audit['total_verified'] == 4
        assert audit['invalid_url_count'] == 0

