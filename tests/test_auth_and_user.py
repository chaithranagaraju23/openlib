"""Tests for authentication, user dashboard, borrowing, donations, and exchanges."""
from app.models.user import User
from app.models.transaction import BorrowRecord, Donation, ExchangeListing, ExchangeRequest


def _login(client, ident, password):
    return client.post('/auth/login', data={'email_or_username': ident, 'password': password}, follow_redirects=True)


def test_register_login_logout(client):
    res = client.post('/auth/register', data={
        'full_name': 'New Reader',
        'username': 'newreader99',
        'email': 'newreader99@test.org',
        'preferred_age_group': 'adults',
        'preferred_language': 'English',
        'password': 'StrongPassword123',
        'confirm_password': 'StrongPassword123',
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'New Reader' in res.data

    res = client.get('/auth/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b'signed out' in res.data


def test_borrow_return_bookmark_and_review(client, app):
    _login(client, 'reader_test', 'ReaderTest@123')

    res = client.post('/books/1/borrow', follow_redirects=True)
    assert b'Successfully borrowed' in res.data

    res = client.post('/books/1/bookmark', follow_redirects=True)
    assert b'Saved to your reading list' in res.data

    res = client.post('/books/1/review', data={
        'rating': 5,
        'title': 'Timeless classic',
        'content': 'Every child and parent should read this edition together.',
    }, follow_redirects=True)
    assert b'Timeless classic' in res.data

    res = client.post('/books/1/return', follow_redirects=True)
    assert b'Returned' in res.data

    with app.app_context():
        rec = BorrowRecord.query.filter_by(book_id=1).first()
        assert rec.status == 'returned'


def test_donation_and_exchange_workflow(client, app):
    # Submit donation as reader
    _login(client, 'reader_test', 'ReaderTest@123')
    res = client.post('/donate', data={
        'donor_name': 'Test Reader',
        'donor_email': 'reader@test.org',
        'donation_type': 'digital',
        'book_title': 'Open Science Guide',
        'book_author': 'Jane Scientist',
        'book_description': 'An open educational handbook for young students.',
        'age_group_name': 'Youth',
        'book_category': 'Science and Mathematics',
        'book_language': 'English',
        'licence': 'CC BY 4.0',
        'source_url': 'https://archive.org/details/openscienceguide',
        'file_url': 'https://archive.org/details/openscienceguide',
        'book_condition': 'Digital',
        'copyright_confirmation': 'y',
    }, follow_redirects=True)
    assert b'generous donation' in res.data

    with app.app_context():
        assert Donation.query.filter_by(book_title='Open Science Guide').count() == 1

    # Owner publishes exchange listing
    client.get('/auth/logout')
    _login(client, 'owner_test', 'OwnerTest@123')
    res = client.post('/exchange', data={
        'title': 'Introduction to Algorithms',
        'author': 'Cormen et al.',
        'age_group_name': 'Youth',
        'condition': 'Good',
        'language': 'English',
        'location': 'Chennai',
        'delivery_method': 'Local Meetup',
        'looking_for': 'Python or discrete math books',
    }, follow_redirects=True)
    assert b'listed for community exchange' in res.data

    with app.app_context():
        listing = ExchangeListing.query.filter_by(title='Introduction to Algorithms').first()
        assert listing is not None
        listing_id = listing.id

    # Reader proposes swap
    client.get('/auth/logout')
    _login(client, 'reader_test', 'ReaderTest@123')
    res = client.post(f'/books/exchange/{listing_id}/request', data={
        'offered_book_title': 'Think Python',
        'offered_book_author': 'Allen Downey',
        'offered_book_condition': 'Like New',
        'message': 'Happy to swap in Chennai this weekend!',
    }, follow_redirects=True)
    assert b'Exchange proposal sent' in res.data

    with app.app_context():
        req_obj = ExchangeRequest.query.filter_by(listing_id=listing_id).first()
        assert req_obj is not None
        assert req_obj.status == 'pending'

