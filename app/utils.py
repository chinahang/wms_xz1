import functools

from flask import abort
from flask_login import current_user


def admin_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if current_user.role != 'admin':
            abort(403)
        return view(**kwargs)
    return wrapped

