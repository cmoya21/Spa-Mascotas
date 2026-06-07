from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import synonym

from ..extensions import db


class ChecklistItemTemplate(db.Model):
    __tablename__ = "checklist_items_template"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    servicio_id = db.Column(db.Integer, db.ForeignKey("servicios.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    requiere_obs = db.Column(db.Boolean, nullable=False, default=False)
    orden = db.Column(db.SmallInteger, nullable=False, default=0)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class FichaGrooming(db.Model):
    __tablename__ = "fichas_grooming"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cita_id = db.Column(db.Integer, db.ForeignKey("citas.id"), nullable=False, unique=True)
    estado_inicial = db.Column(db.Text)
    temperatura_ingreso = db.Column(db.Numeric(4, 1))
    peso_momento_servicio = db.Column(db.Numeric(5, 2))
    raza_tamano_momento = db.Column(db.String(100))
    estado_final = db.Column(db.Text)
    observaciones_final = db.Column(db.Text)
    notas_internas = db.Column(db.Text)
    consumido_inventario = db.Column(db.Boolean, nullable=False, default=False)
    insumos_consumidos = db.Column(JSONB)
    fecha_cierre = db.Column(db.DateTime)
    checklist_completo = db.Column(db.Boolean, nullable=False, default=False)
    groomer_id = db.Column(db.Integer, db.ForeignKey("groomers.id"))
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    checklist_items = db.relationship(
        "FichaChecklist",
        back_populates="ficha",
        cascade="all, delete-orphan",
    )
    fotos = db.relationship(
        "FotoFicha",
        back_populates="ficha",
        cascade="all, delete-orphan",
    )


class FichaChecklist(db.Model):
    __tablename__ = "fichas_checklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ficha_id = db.Column(db.Integer, db.ForeignKey("fichas_grooming.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("checklist_items_template.id"), nullable=False)
    completado = db.Column(db.Boolean, nullable=False, default=False)
    observacion = db.Column(db.Text)
    completado_en = db.Column(db.DateTime)

    ficha = db.relationship("FichaGrooming", back_populates="checklist_items")


class FotoFicha(db.Model):
    __tablename__ = "fotos_ficha"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ficha_id = db.Column(db.Integer, db.ForeignKey("fichas_grooming.id"), nullable=False)
    url = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    descripcion = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    ficha = db.relationship("FichaGrooming", back_populates="fotos")


class HistorialMascota(db.Model):
    __tablename__ = "historial_mascota"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mascota_id = db.Column(db.Integer, db.ForeignKey("mascotas.id"), nullable=False)
    tipo_evento = db.Column(db.String(30), nullable=False)
    tipo = synonym("tipo_evento")
    descripcion = db.Column(db.Text, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    mascota = db.relationship("Mascota")
