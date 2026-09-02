"""Server-side authorization helpers.

`pagePermission` in the frontend only hides pages; every API that changes data
must also be guarded here. UserType: 1 Administrator, 2 Supervisor, 3 Staff,
4 Guest (statictext.UserTypes).

    @bp.route("/save", methods=["POST"])
    @require_types(ADMIN, SUPERVISOR)
    def save(): ...

require_types implies login: anonymous callers get 401, logged-in users of a
type outside the list get 403 - both as the usual JSON result envelope.
"""

from functools import wraps

from flask import jsonify
from flask_login import current_user

from util import statictext

ADMIN = 1
SUPERVISOR = 2
STAFF = 3
GUEST = 4

# Convenience groups used across the routes.
ADMINS = (ADMIN,)
MANAGERS = (ADMIN, SUPERVISOR)
EDITORS = (ADMIN, SUPERVISOR, STAFF)


def deny(code):
    """JSON refusal in the usual result envelope (401 not logged in, 403 no permission)."""
    return (
        jsonify(
            {
                "Result": False,
                "Title": statictext.Messages["Title"],
                "Message": (
                    statictext.Messages["NoPermission"]
                    if code == 403
                    else statictext.ResponseCode[code]
                ),
                "Code": code,
            }
        ),
        code,
    )


def require_types(*types):
    """Allow only authenticated users whose UserType is in `types`."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return deny(401)
            if current_user.UserType not in types:
                return deny(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def is_scoped_user():
    """Staff / Guest only see their teams' stations (managers see everything)."""
    return current_user.is_authenticated and current_user.UserType in (STAFF, GUEST)
