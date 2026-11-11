"""Routes package."""
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

__all__ = [
    'main_bp',
    'auth_bp',
    'books_bp',
    'children_bp',
    'youth_bp',
    'adults_bp',
    'seniors_bp',
    'user_bp',
    'admin_bp',
    'api_bp',
]

