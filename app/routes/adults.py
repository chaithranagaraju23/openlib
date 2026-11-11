"""Adult Library routes (Recommended ages 25-59)."""
from flask import Blueprint
from app.routes._generation import render_generation_library

adults_bp = Blueprint('adults', __name__)


@adults_bp.route('/')
def index():
    return render_generation_library('adults', 'adults/index.html')


@adults_bp.route('/category/<slug>')
def category(slug):
    return render_generation_library('adults', 'adults/index.html', category_slug=slug)

