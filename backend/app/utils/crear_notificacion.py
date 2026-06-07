from datetime import datetime, timedelta, timezone

from ..extensions import db
from ..models.notificacion import Notificacion


def crear_notificacion(cita_id=None, cliente=None, tipo_evento=None, mensaje=None, delay_minutes=0):
    """Helper para insertar notificación."""
    if not cliente or not tipo_evento or not mensaje:
        return None

    canal = cliente.canal_notificacion or "whatsapp"
    if canal == "whatsapp" or canal == "sms":
        destino = cliente.telefono
    else:
        destino = getattr(getattr(cliente, "usuario", None), "email", None)
        if not destino:
            destino = getattr(cliente, "email", None)

    if not destino:
        return None

    fecha = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

    notif = Notificacion(
        cita_id=cita_id,
        cliente_id=cliente.id,
        tipo_canal=canal,
        tipo_evento=tipo_evento,
        destino=destino,
        mensaje=mensaje,
        fecha_programacion=fecha,
        estado="pendiente",
    )
    db.session.add(notif)
    return notif
