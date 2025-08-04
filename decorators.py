from functools import wraps
from flask_login import current_user
from flask import abort

def admin_required(f):
    """Permette accesso solo agli admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """Permette accesso a admin e user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role not in ('admin', 'user'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def guest_required(f):
    """Permette accesso a admin e guest."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role not in ('admin', 'guest'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def ceo_required(f):
    """Permette accesso solo ai CEO."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role != 'ceo':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def roles_required(roles):
    """Permette accesso solo ai ruoli specificati."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(current_user, 'role') or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator 