"""OpenLib Flask Application Factory."""
import os
from datetime import datetime
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_migrate import Migrate

from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
migrate = Migrate()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    app = Flask(__name__)
    cfg = config.get(config_name, config['default'])
    app.config.from_object(cfg)
    cfg.init_app(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Ensure required directories exist
    _ensure_directories(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.books import books_bp
    from app.routes.children import children_bp
    from app.routes.youth import youth_bp
    from app.routes.adults import adults_bp
    from app.routes.seniors import seniors_bp
    from app.routes.user import user_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(books_bp, url_prefix='/books')
    app.register_blueprint(children_bp, url_prefix='/children')
    app.register_blueprint(youth_bp, url_prefix='/youth')
    app.register_blueprint(adults_bp, url_prefix='/adults')
    app.register_blueprint(seniors_bp, url_prefix='/seniors')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register error handlers
    _register_error_handlers(app)

    # Register template filters and context processors
    _register_template_helpers(app)

    # Create tables and seed data
    with app.app_context():
        db.create_all()
        if app.config.get('AUTO_SEED', True):
            _seed_initial_data(app)

    return app


def _ensure_directories(app):
    """Ensure required directories exist."""
    dirs = [
        app.config.get('COVERS_FOLDER', ''),
        app.config.get('BOOKS_FOLDER', ''),
        app.config.get('CATALOGUE_FOLDER', ''),
        os.path.join(app.root_path, '..', 'instance'),
    ]
    for d in dirs:
        if d:
            os.makedirs(d, exist_ok=True)


def _register_error_handlers(app):
    """Register HTTP error handlers."""

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500


def _register_template_helpers(app):
    """Register template filters and context processors."""

    @app.template_filter('truncate_words')
    def truncate_words(s, num=20):
        if not s:
            return ''
        words = str(s).split()
        if len(words) > num:
            return ' '.join(words[:num]) + '...'
        return str(s)

    @app.template_filter('format_date')
    def format_date(dt):
        if dt:
            return dt.strftime('%B %d, %Y')
        return ''

    @app.context_processor
    def inject_globals():
        from app.models.book import Category, AgeGroup, Book
        try:
            age_groups = AgeGroup.query.order_by(AgeGroup.sort_order).all()
            total_books = Book.query.filter_by(is_active=True, is_verified=True).count()
            languages = [
                row[0] for row in db.session.query(Book.language)
                .filter(Book.is_active == True, Book.is_verified == True, Book.language != None)
                .distinct().order_by(Book.language).all()
            ]
        except Exception:
            age_groups = []
            total_books = 0
            languages = []

        return {
            'app_name': app.config.get('APP_NAME', 'OpenLib'),
            'app_tagline': app.config.get('APP_TAGLINE', ''),
            'age_groups': age_groups,
            'total_books': total_books,
            'available_languages': languages,
            'current_year': datetime.now().year,
        }


def _seed_initial_data(app):
    """Seed initial data into the database."""
    from app.services.seeder import seed_all
    seed_all(app)
