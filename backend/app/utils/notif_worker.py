import logging
from datetime import datetime, timezone

from flask import current_app

from ..extensions import db
from ..models import Notificacion, Producto, Usuario, Rol
from .crear_notificacion import crear_notificacion
from .plantillas_notif import mensaje_bajo_stock

logger = logging.getLogger(__name__)

MAX_REINTENTOS = 3


def procesar_notificaciones():
    """Llamada por APScheduler cada 60s."""
    app = current_app._get_current_object()
    with app.app_context():
        return _procesar_interno(app)


def _procesar_interno(app):
    from ..extensions import db
    from ..models.notificacion import Notificacion

    try:
        notifs = Notificacion.query.filter(
            Notificacion.estado == 'pendiente',
            Notificacion.fecha_programacion <= datetime.now(timezone.utc),
            Notificacion.reintentos < 3
        ).limit(50).all()

        for notif in notifs:
            try:
                exito = _enviar_notificacion(notif)
                if exito:
                    notif.estado = 'enviado'
                    notif.fecha_envio = datetime.now(timezone.utc)
                else:
                    _marcar_fallo(notif, 'Envío retornó False')
            except Exception as e:
                _marcar_fallo(notif, str(e))
                logger.error(f"Error notif {notif.id}: {e}")

        db.session.commit()
        return len(notifs)

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"Error en _procesar_interno: {e}")
        return 0


def notificar_bajo_stock(producto, admins):
    if not producto or not admins:
        return 0

    enviados = 0
    mensaje = mensaje_bajo_stock(producto.nombre, producto.stock, producto.stock_minimo)
    for admin in admins:
        destino = getattr(admin, "email", None)
        if not destino:
            continue

        existing = Notificacion.query.filter(
            Notificacion.tipo_evento == "bajo_stock",
            Notificacion.destino == destino,
            Notificacion.mensaje == mensaje,
            Notificacion.creado_en >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        ).first()
        if existing:
            continue

        notif = Notificacion(
            cita_id=None,
            cliente_id=None,
            tipo_canal="email",
            tipo_evento="bajo_stock",
            destino=destino,
            mensaje=mensaje,
            fecha_programacion=datetime.now(timezone.utc),
            estado="pendiente",
        )
        db.session.add(notif)
        enviados += 1

    return enviados


def _enviar_notificacion(notif):
    if notif.tipo_canal == "whatsapp":
        return _enviar_whatsapp(notif.destino, notif.mensaje)
    if notif.tipo_canal == "email":
        return _enviar_email(notif.destino, _asunto_por_evento(notif.tipo_evento), notif.mensaje)
    if notif.tipo_canal == "sms":
        return _enviar_sms(notif.destino, notif.mensaje)
    return False


def _marcar_fallo(notif, error_msg):
    notif.reintentos = int(notif.reintentos or 0) + 1
    notif.ultimo_intento = datetime.now(timezone.utc)
    notif.error_mensaje = error_msg[:500]
    if notif.reintentos >= MAX_REINTENTOS:
        notif.estado = "fallido"


def _asunto_por_evento(tipo_evento):
    asuntos = {
        "confirmacion": "Tu cita ha sido confirmada",
        "recordatorio_24h": "Recordatorio: tu cita es mañana",
        "recordatorio_2h": "Tu cita es en 2 horas",
        "listo_recoger": "¡Tu mascota está lista!",
        "encuesta": "¿Cómo fue tu experiencia?",
        "bajo_stock": "Alerta de inventario",
        "pago_registrado": "Pago confirmado",
        "solicitud_revision": "Solicitud recibida",
    }
    return asuntos.get(tipo_evento, "Notificación del Spa")


def _enviar_whatsapp(telefono, mensaje):
    logger.info("[WHATSAPP-STUB] → %s: %s...", telefono, mensaje[:60])
    return True


def _enviar_email(destino, asunto, mensaje):
    logger.info("[EMAIL-STUB] → %s: %s", destino, asunto)
    return True


def _enviar_sms(telefono, mensaje):
    logger.info("[SMS-STUB] → %s: %s...", telefono, mensaje[:40])
    return True
