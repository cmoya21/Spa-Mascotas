from ..extensions import db


class Promocion(db.Model):
    __tablename__ = "promociones"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_inicio = db.Column(db.Date)
    fecha_fin = db.Column(db.Date)
    activa = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

