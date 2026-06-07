from ..extensions import db


class Notificacion(db.Model):
    __tablename__ = "notificaciones"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cita_id = db.Column(db.Integer, db.ForeignKey("citas.id"))
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    tipo_canal = db.Column(db.String(20), nullable=False)
    tipo_evento = db.Column(db.String(30), nullable=False)
    destino = db.Column(db.String(255), nullable=False)
    mensaje = db.Column(db.Text)
    fecha_programacion = db.Column(db.DateTime, nullable=False)
    fecha_envio = db.Column(db.DateTime)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    reintentos = db.Column(db.SmallInteger, nullable=False, default=0)
    ultimo_intento = db.Column(db.DateTime)
    error_mensaje = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
