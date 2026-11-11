"""Tests for reading progress API, page bookmarks API, exchange approval, and donation publishing."""
from app.models.book import Book
from app.models.review import ReadingProgress, ReaderBookmark
from app.models.transaction import Donation, ExchangeListing, ExchangeRequest


def _login(client, ident, password):
    return client.post('/auth/login', data={'email_or_username': ident, 'password': password}, follow_redirects=True)


def test_reader_progress_and_bookmarks_api(client, app):
    _login(client, 'reader_test', 'ReaderTest@123')

    r = client.post('/api/reading-progress', json={
        'book_id': 1,
        'current_page': 5,
        'total_pages': 20,
    })
    assert r.status_code == 200
    data = r.get_json()
    assert data['percentage'] == 25.0

    r_bm = client.post('/api/reader-bookmarks', json={
        'book_id': 1,
        'page_number': 5,
        'label': 'Page 5',
        'note': 'Favorite fable',
        'action': 'save',
    })
    assert r_bm.status_code == 200
    assert r_bm.get_json()['status'] == 'saved'

    r_list = client.get('/api/reader-bookmarks/1')
    assert r_list.status_code == 200
    assert len(r_list.get_json()) == 1

    with app.app_context():
        prog = ReadingProgress.query.filter_by(book_id=1).first()
        assert prog.current_page == 5
        assert ReaderBookmark.query.filter_by(book_id=1, page_number=5).count() == 1


def test_admin_donation_acceptance_publishes_book(client, app):
    _login(client, 'reader_test', 'ReaderTest@123')
    client.post('/donate', data={
        'donor_name': 'Test Reader',
        'donor_email': 'reader@test.org',
        'donation_type': 'digital',
        'book_title': 'Community Folklore Anthology',
        'book_author': 'Community Collective',
        'book_description': 'Shared public domain regional folklore collection.',
        'age_group_name': 'Children',
        'book_category': 'Folktales',
        'book_language': 'English',
        'licence': 'CC BY 4.0',
        'source_url': 'https://archive.org/details/communityfolklore',
        'file_url': 'https://archive.org/details/communityfolklore',
        'book_condition': 'Digital',
        'copyright_confirmation': 'y',
    })
    with app.app_context():
        donation = Donation.query.filter_by(book_title='Community Folklore Anthology').first()
        did = donation.id

    client.get('/auth/logout')
    _login(client, 'admin_test', 'AdminTest@123')
    res = client.post(f'/admin/donations/{did}/accept', data={'admin_notes': 'Verified CC BY 4.0'}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        donation = Donation.query.get(did)
        assert donation.status == 'accepted'
        assert donation.published_book_id is not None
        assert Book.query.filter_by(title='Community Folklore Anthology').first() is not None


def test_exchange_accept_and_complete(client, app):
    _login(client, 'owner_test', 'OwnerTest@123')
    client.post('/exchange', data={
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'age_group_name': 'Youth',
        'condition': 'Good',
        'language': 'English',
        'location': 'Hyderabad',
        'delivery_method': 'Local Meetup',
    })
    with app.app_context():
        listing = ExchangeListing.query.filter_by(title='Clean Code').first()
        lid = listing.id

    client.get('/auth/logout')
    _login(client, 'reader_test', 'ReaderTest@123')
    client.post(f'/books/exchange/{lid}/request', data={
        'offered_book_title': 'Refactoring',
        'offered_book_author': 'Martin Fowler',
        'offered_book_condition': 'Good',
        'message': 'Let us swap near Jubilee Hills!',
    })
    with app.app_context():
        req_obj = ExchangeRequest.query.filter_by(listing_id=lid).first()
        rid = req_obj.id

    client.get('/auth/logout')
    _login(client, 'owner_test', 'OwnerTest@123')
    client.post(f'/user/exchange-request/{rid}/accept', data={'response': 'Sounds good!'})
    client.post(f'/user/exchange-request/{rid}/complete')

    with app.app_context():
        req_obj = ExchangeRequest.query.get(rid)
        listing = ExchangeListing.query.get(lid)
        assert req_obj.status == 'completed'
        assert listing.status == 'exchanged'

