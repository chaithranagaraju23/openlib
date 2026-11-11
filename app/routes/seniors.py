"""Senior Citizens Library routes (Recommended ages 60+)."""
from flask import Blueprint
from app.routes._generation import render_generation_library

seniors_bp = Blueprint('seniors', __name__)


@seniors_bp.route('/')
def index():
    return render_generation_library('seniors', 'seniors/index.html')


@seniors_bp.route('/category/<slug>')
def category(slug):
    return render_generation_library('seniors', 'seniors/index.html', category_slug=slug)

