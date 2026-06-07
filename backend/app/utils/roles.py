from flask import abort
from flask_jwt_extended import get_jwt_identity

from ..models import Groomer

from .decorators import get_current_user, requiere_rol


def require_role(*roles):
    return requiere_rol(*roles)


def solo_propio_groomer(cita_o_ficha):
    try:
        usuario_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        abort(403, description="Solo puedes acceder a tus propias citas")

    groomer = Groomer.query.filter_by(usuario_id=usuario_id).first()
    if not groomer or getattr(cita_o_ficha, "groomer_id", None) != groomer.id:
        abort(403, description="Solo puedes acceder a tus propias citas")
    return groomer
