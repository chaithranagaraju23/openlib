"""Children's Library routes (Recommended ages 5-12)."""
from flask import Blueprint
from app.routes._generation import render_generation_library

children_bp = Blueprint('children', __name__)


@children_bp.route('/')
def index():
    return render_generation_library('children', 'children/index.html')


@children_bp.route('/category/<slug>')
def category(slug):
    return render_generation_library('children', 'children/index.html', category_slug=slug)

