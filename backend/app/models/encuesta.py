from ..extensions import db


class Encuesta(db.Model):
    __tablename__ = "encuestas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cita_id = db.Column(db.Integer, db.ForeignKey("citas.id"), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    calificacion = db.Column(db.SmallInteger)
    nps = db.Column(db.SmallInteger)
    comentario = db.Column(db.Text)
    respondida = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    respondida_en = db.Column(db.DateTime)
