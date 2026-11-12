"""Email notification helpers powered by Flask-Mail."""
import threading
from flask import current_app
from flask_mail import Message

from app import mail


def _clean_header(value):
    """Strip CR/LF characters from values used in email headers."""
    return ' '.join(str(value or '').splitlines()).strip()


def is_mail_configured(config):
    """Return True when SMTP server and sender credentials are set."""
    return bool(
        (config.get('MAIL_SERVER') or '').strip()
        and (config.get('MAIL_USERNAME') or '').strip()
        and config.get('MAIL_PASSWORD')
    )


def get_contact_recipient(config):
    """Resolve the destination email address for contact inquiries."""
    explicit = (config.get('CONTACT_RECIPIENT_EMAIL') or '').strip()
    if explicit:
        return explicit

    admin_email = (config.get('ADMIN_EMAIL') or '').strip()
    if admin_email and admin_email.lower() != 'admin@openlib.org':
        return admin_email

    return (config.get('MAIL_USERNAME') or '').strip() or admin_email or None


def _send_async_email(app, msg):
    """Send an email inside an application context without blocking the request."""
    with app.app_context():
        try:
            mail.send(msg)
            app.logger.info('Contact notification email sent to %s', msg.recipients)
        except Exception as exc:
            app.logger.warning('Failed to send contact notification email: %s', exc)


def send_contact_notification(contact_msg):
    """Email the library team when a visitor submits the Contact form.

    Returns True when delivery is dispatched (or recorded in test mode),
    and False when mail credentials are not configured or sending fails.
    """
    cfg = current_app.config
    if not is_mail_configured(cfg):
        current_app.logger.info(
            'Contact message #%s saved to DB; email skipped (MAIL_USERNAME/MAIL_PASSWORD not set).',
            getattr(contact_msg, 'id', None),
        )
        return False

    recipient = get_contact_recipient(cfg)
    if not recipient:
        return False

    sender = (
        (cfg.get('MAIL_DEFAULT_SENDER') or '').strip()
        or (cfg.get('MAIL_USERNAME') or '').strip()
    )
    clean_subject = _clean_header(contact_msg.subject)
    clean_name = _clean_header(contact_msg.name)
    clean_email = _clean_header(contact_msg.email)

    body_lines = [
        'New contact inquiry received on OpenLib.',
        '',
        f'From: {clean_name} <{clean_email}>',
        f'Subject: {clean_subject}',
        '',
        'Message:',
        contact_msg.message or '',
        '',
        '---',
        'You can reply directly to this email or review it in OpenLib Admin -> Messages (/admin/messages).',
    ]

    email_msg = Message(
        subject=f'[OpenLib Contact] {clean_subject}',
        sender=sender,
        recipients=[recipient],
        reply_to=clean_email or None,
        body='\n'.join(body_lines),
    )

    # Send synchronously during tests or when suppression is enabled so test outboxes capture it immediately.
    if current_app.testing or cfg.get('MAIL_SUPPRESS_SEND'):
        try:
            mail.send(email_msg)
            return True
        except Exception as exc:
            current_app.logger.warning('Failed to send contact notification email: %s', exc)
            return False

    app = current_app._get_current_object()
    thread = threading.Thread(target=_send_async_email, args=(app, email_msg), daemon=True)
    thread.start()
    return True

