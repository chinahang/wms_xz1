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


class FakePagination:
    """替代 Flask-SQLAlchemy paginate，用于手动分页的场景"""
    def __init__(self, items, page, per_page, total, total_pages):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = total_pages
        self.has_prev = page > 1
        self.has_next = page < total_pages
        self.prev_num = page - 1
        self.next_num = page + 1

    def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
        last = 0
        for i in range(1, self.pages + 1):
            if i <= left_edge or i > self.pages - right_edge or \
               (i >= self.page - left_current and i <= self.page + right_current):
                if last + 1 != i:
                    yield None
                yield i
                last = i
