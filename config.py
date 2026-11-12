import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def _normalize_database_url(url):
    """Normalize Render/Heroku postgres:// URI for SQLAlchemy 2.x."""
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    WTF_CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
    AUTO_SEED = True

    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = (os.environ.get('MAIL_USERNAME') or '').strip() or None
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = (
        os.environ.get('MAIL_DEFAULT_SENDER')
        or MAIL_USERNAME
        or os.environ.get('ADMIN_EMAIL', 'noreply@openlib.org')
    )
    CONTACT_RECIPIENT_EMAIL = (os.environ.get('CONTACT_RECIPIENT_EMAIL') or '').strip() or None

    # Upload folders
    COVERS_FOLDER = os.path.join(basedir, 'app', 'static', 'covers')
    BOOKS_FOLDER = os.path.join(basedir, 'data', 'books')
    CATALOGUE_FOLDER = os.path.join(basedir, 'data', 'catalogue')

    # Pagination
    BOOKS_PER_PAGE = 12
    ADMIN_BOOKS_PER_PAGE = 20

    # Borrowing rules
    MAX_ACTIVE_BORROWS = 5
    LOAN_DURATION_DAYS = 14

    # Admin
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@openlib.org')
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'AdminSecure@2024')

    # App info
    APP_NAME = 'OpenLib'
    APP_TAGLINE = 'One Platform. Four Generations. Unlimited Knowledge.'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.environ.get('DATABASE_URL')) or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'openlib.db')


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    AUTO_SEED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.environ.get('DATABASE_URL')) or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'openlib.db')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
