"""Access control decorators."""
from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def admin_required(f):
    """Require authenticated admin role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def moderator_required(f):
    """Require authenticated admin or moderator role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_moderator():
            abort(403)
        return f(*args, **kwargs)
    return decorated

