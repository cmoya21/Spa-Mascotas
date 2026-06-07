from ..extensions import db


class Mascota(db.Model):
    __tablename__ = "mascotas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    especie = db.Column(db.String(50), nullable=False)
    raza = db.Column(db.String(100))
    tamano = db.Column(db.String(30))
    fecha_nacimiento = db.Column(db.Date)
    peso_kg = db.Column(db.Numeric(5, 2))
    temperamento = db.Column(db.String(50))
    alergias_conocidas = db.Column(db.Text)
    restricciones_medicas = db.Column(db.Text)
    foto_url = db.Column(db.Text)
    carnet_vacunas_url = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    duenos = db.relationship(
        "MascotaDueno",
        back_populates="mascota",
        cascade="all, delete-orphan",
    )


class MascotaDueno(db.Model):
    __tablename__ = "mascota_dueno"

    mascota_id = db.Column(db.Integer, db.ForeignKey("mascotas.id"), primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), primary_key=True)
    es_principal = db.Column(db.Boolean, nullable=False, default=False)
    desde = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    mascota = db.relationship("Mascota", back_populates="duenos")
    cliente = db.relationship("Cliente")


class VacunaMascota(db.Model):
    __tablename__ = "vacunas_mascota"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mascota_id = db.Column(db.Integer, db.ForeignKey("mascotas.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    nombre_vacuna = db.Column(db.String(150), nullable=False)
    aplicada_en = db.Column(db.Date, nullable=False)
    proxima_aplicacion = db.Column(db.Date)
    lote = db.Column(db.String(80))
    observaciones = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    mascota = db.relationship("Mascota")
    cliente = db.relationship("Cliente")
