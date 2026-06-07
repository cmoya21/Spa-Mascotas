from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Cliente, Notificacion
from ..services.notifications_worker import process_pending_notifications
from ..utils.decorators import get_current_user, requiere_rol


notificaciones_bp = Blueprint("notificaciones_bp", __name__, url_prefix="/api/notificaciones")


def _resolve_cliente_actual():
    usuario, rol = get_current_user()
    if not usuario or rol != "Cliente":
        return None
    return usuario.perfil_cliente or Cliente.query.filter_by(usuario_id=usuario.id).first()


def _payload_notificacion(item, cliente_nombre=None):
    return {
        "id": item.id,
        "cita_id": item.cita_id,
        "cliente_id": item.cliente_id,
        "cliente_nombre": cliente_nombre,
        "tipo_canal": item.tipo_canal,
        "tipo_evento": item.tipo_evento,
        "destino": item.destino,
        "mensaje": item.mensaje,
        "estado": item.estado,
        "fecha_programacion": item.fecha_programacion.isoformat() if item.fecha_programacion else None,
        "fecha_envio": item.fecha_envio.isoformat() if item.fecha_envio else None,
        "reintentos": int(item.reintentos or 0),
        "ultimo_intento": item.ultimo_intento.isoformat() if item.ultimo_intento else None,
        "error_mensaje": item.error_mensaje,
        "creado_en": item.creado_en.isoformat() if item.creado_en else None,
    }


@notificaciones_bp.get("")
@requiere_rol("Admin", "Recepcion")
def listar_notificaciones_legacy():
    return listar_notificaciones_admin()


@notificaciones_bp.get("/me")
@requiere_rol("Cliente")
def listar_notificaciones_cliente():
    cliente = _resolve_cliente_actual()
    if not cliente:
        return jsonify([])

    notificaciones = (
        Notificacion.query.filter_by(cliente_id=cliente.id)
        .order_by(Notificacion.creado_en.desc(), Notificacion.id.desc())
        .limit(20)
        .all()
    )
    return jsonify([_payload_notificacion(item) for item in notificaciones])


@notificaciones_bp.get("/admin")
@requiere_rol("Admin", "Recepcion")
def listar_notificaciones_admin():
    estado = request.args.get("estado")
    tipo = request.args.get("tipo")
    limit = request.args.get("limit", type=int) or 50

    query = Notificacion.query
    if estado:
        query = query.filter_by(estado=estado)
    if tipo:
        query = query.filter_by(tipo_evento=tipo)

    notificaciones = query.order_by(Notificacion.creado_en.desc(), Notificacion.id.desc()).limit(limit).all()
    payload = []
    for item in notificaciones:
        cliente = Cliente.query.filter_by(id=item.cliente_id).first() if item.cliente_id else None
        payload.append(
            _payload_notificacion(
                item,
                cliente_nombre=(f"{cliente.nombre} {cliente.apellido or ''}".strip() if cliente else None),
            )
        )
    return jsonify({"notificaciones": payload})


@notificaciones_bp.get("/stats")
@requiere_rol("Admin", "Recepcion")
def stats_notificaciones():
    hace_24 = datetime.now(timezone.utc) - timedelta(hours=24)
    notificaciones = Notificacion.query.filter(Notificacion.creado_en >= hace_24).all()

    pendientes = sum(1 for item in notificaciones if item.estado == "pendiente")
    enviadas = sum(1 for item in notificaciones if item.estado == "enviado")
    fallidas = sum(1 for item in notificaciones if item.estado == "fallido")
    listo_recoger_enviadas = sum(
        1 for item in notificaciones if item.tipo_evento == "listo_recoger" and item.estado == "enviado"
    )

    return jsonify(
        {
            "pendientes": pendientes,
            "enviadas": enviadas,
            "fallidas": fallidas,
            "listo_recoger_enviadas": listo_recoger_enviadas,
        }
    )


@notificaciones_bp.post("/reenviar/<int:notif_id>")
@requiere_rol("Admin")
def reenviar_notificacion(notif_id):
    notif = Notificacion.query.filter_by(id=notif_id).first()
    if not notif:
        return jsonify({"message": "Notificacion no encontrada"}), 404
    if notif.estado != "fallido":
        return jsonify({"message": "Solo se pueden reenviar notificaciones fallidas"}), 422

    notif.estado = "pendiente"
    notif.reintentos = 0
    notif.error_mensaje = None
    notif.ultimo_intento = None
    db.session.commit()
    return jsonify({"message": "Notificacion reprogramada", "id": notif.id})


@notificaciones_bp.post("/procesar")
@requiere_rol("Admin")
def procesar_notificaciones():
    total = process_pending_notifications()
    return jsonify({"procesadas": total})
