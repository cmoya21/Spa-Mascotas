from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..models import Usuario
from .responses import error


def _coerce_user_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_current_user():
    usuario_id = _coerce_user_id(get_jwt_identity())
    if usuario_id is None:
        return None, None

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario or not usuario.rol:
        return usuario, None

    return usuario, usuario.rol.nombre


def requiere_rol(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            usuario_id = _coerce_user_id(get_jwt().get("sub"))
            if usuario_id is None:
                return error("Token inválido", status=401)

            usuario = Usuario.query.filter_by(id=usuario_id).first()
            if not usuario or not usuario.rol or usuario.rol.nombre not in roles:
                return error("Acceso denegado", status=403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
