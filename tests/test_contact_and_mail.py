"""Tests for Contact form storage, Admin inbox, and Flask-Mail notifications."""
from app import mail
from app.models.transaction import ContactMessage
from app.services.email_service import get_contact_recipient


def _login(client, ident, password):
    return client.post(
        '/auth/login',
        data={'email_or_username': ident, 'password': password},
        follow_redirects=True,
    )


def test_contact_saves_to_db_and_admin_inbox_without_smtp(client, app):
    with mail.record_messages() as outbox:
        resp = client.post('/contact', data={
            'name': 'Asha Reader',
            'email': 'asha@example.org',
            'subject': 'Question about Kannada books',
            'message': 'Could you add more bilingual children stories for early readers?',
        }, follow_redirects=True)

    assert resp.status_code == 200
    assert b'Your message has been received' in resp.data
    assert len(outbox) == 0

    with app.app_context():
        msg = ContactMessage.query.filter_by(email='asha@example.org').first()
        assert msg is not None
        assert msg.is_read is False
        msg_id = msg.id

    _login(client, 'admin_test', 'AdminTest@123')
    inbox = client.get('/admin/messages')
    assert inbox.status_code == 200
    assert b'Question about Kannada books' in inbox.data
    assert b'asha@example.org' in inbox.data

    mark = client.post(f'/admin/messages/{msg_id}/read', follow_redirects=True)
    assert mark.status_code == 200
    with app.app_context():
        assert ContactMessage.query.get(msg_id).is_read is True


def test_contact_sends_email_when_mail_configured(client, app):
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_USERNAME'] = 'librarian.inbox@example.com'
    app.config['MAIL_PASSWORD'] = 'app-password-placeholder'
    app.config['MAIL_DEFAULT_SENDER'] = 'librarian.inbox@example.com'
    app.config['ADMIN_EMAIL'] = 'admin@openlib.org'

    with mail.record_messages() as outbox:
        resp = client.post('/contact', data={
            'name': 'Rohan Student',
            'email': 'rohan@example.org',
            'subject': 'Python PDF help',
            'message': 'Thank you for hosting Think Python for engineering students.',
        }, follow_redirects=True)

    assert resp.status_code == 200
    assert len(outbox) == 1
    sent = outbox[0]
    assert sent.recipients == ['librarian.inbox@example.com']
    assert sent.reply_to == 'rohan@example.org'
    assert sent.subject == '[OpenLib Contact] Python PDF help'
    assert 'Thank you for hosting Think Python' in sent.body


def test_contact_prefers_explicit_recipient_and_survives_smtp_error(client, app, monkeypatch):
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_USERNAME'] = 'sender@example.com'
    app.config['MAIL_PASSWORD'] = 'app-password-placeholder'
    app.config['CONTACT_RECIPIENT_EMAIL'] = 'desk@example.com'

    assert get_contact_recipient(app.config) == 'desk@example.com'

    def _boom(_msg):
        raise RuntimeError('SMTP unavailable')

    monkeypatch.setattr(mail, 'send', _boom)

    resp = client.post('/contact', data={
        'name': 'Meera Senior',
        'email': 'meera@example.org',
        'subject': 'Large print books',
        'message': 'I enjoy reading the classic poetry section with larger text.',
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b'Your message has been received' in resp.data
    with app.app_context():
        assert ContactMessage.query.filter_by(email='meera@example.org').count() == 1

