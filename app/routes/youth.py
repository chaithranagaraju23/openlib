"""Youth Library routes (Recommended ages 13-24)."""
from flask import Blueprint
from app.routes._generation import render_generation_library

youth_bp = Blueprint('youth', __name__)


@youth_bp.route('/')
def index():
    return render_generation_library('youth', 'youth/index.html')


@youth_bp.route('/category/<slug>')
def category(slug):
    return render_generation_library('youth', 'youth/index.html', category_slug=slug)

