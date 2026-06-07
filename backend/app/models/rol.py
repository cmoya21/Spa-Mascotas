from sqlalchemy.dialects.postgresql import JSONB

from ..extensions import db


class Rol(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    permisos = db.Column(JSONB, nullable=False, server_default=db.text("'{}'::jsonb"))
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    usuarios = db.relationship("Usuario", back_populates="rol")
