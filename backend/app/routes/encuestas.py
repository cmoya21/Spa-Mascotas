from datetime import datetime, timezone

from flask import Blueprint, request

from ..extensions import db
from ..models import Cita, Cliente, Encuesta, MascotaDueno
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.responses import error, success


encuestas_bp = Blueprint("encuestas_bp", __name__, url_prefix="/api/encuestas")


def _cliente_id_from_cita(cita):
    relacion = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id).first()
    if not relacion:
        return None
    return relacion.cliente_id


@encuestas_bp.post("/<int:cita_id>")
@requiere_rol("Cliente")
def responder_encuesta(cita_id):
    data = request.get_json() or {}
    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)

    usuario, _rol = get_current_user()
    if not usuario or not usuario.perfil_cliente:
        return error("Cliente no encontrado", status=404)

    cliente_id = _cliente_id_from_cita(cita)
    if cliente_id != usuario.perfil_cliente.id:
        return error("Acceso denegado", status=403)

    encuesta = Encuesta.query.filter_by(cita_id=cita.id).first()
    if not encuesta:
        encuesta = Encuesta(
            cita_id=cita.id,
            cliente_id=cliente_id,
            creado_en=datetime.now(timezone.utc),
        )
        db.session.add(encuesta)

    encuesta.calificacion = data.get("calificacion")
    encuesta.nps = data.get("nps")
    encuesta.comentario = data.get("comentario")
    encuesta.respondida = True
    encuesta.respondida_en = datetime.now(timezone.utc)

    db.session.commit()
    return success({"message": "Encuesta registrada"})


@encuestas_bp.get("")
@requiere_rol("Admin", "Recepcion")
def listar_encuestas():
    items = Encuesta.query.order_by(Encuesta.creado_en.desc()).limit(200).all()
    payload = [
        {
            "id": item.id,
            "cita_id": item.cita_id,
            "cliente_id": item.cliente_id,
            "calificacion": item.calificacion,
            "nps": item.nps,
            "comentario": item.comentario,
            "respondida": item.respondida,
        }
        for item in items
    ]
    return success({"encuestas": payload})
