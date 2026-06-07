from sqlalchemy.dialects.postgresql import JSONB

from ..extensions import db


class Servicio(db.Model):
    __tablename__ = "servicios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    precio_base = db.Column(db.Numeric(10, 2), nullable=False)
    duracion_base_minutos = db.Column(db.Integer, nullable=False)
    permite_doble_booking = db.Column(db.Boolean, nullable=False, default=False)
    requiere_bloqueo_consecutivo = db.Column(db.Boolean, nullable=False, default=False)
    factor_tamano_raza = db.Column(JSONB)
    consumo_insumos = db.Column(JSONB)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    sucursal_id = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class DisponibilidadGroomer(db.Model):
    __tablename__ = "disponibilidad_groomer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    groomer_id = db.Column(db.Integer, db.ForeignKey("groomers.id"), nullable=False)
    dia_semana = db.Column(db.SmallInteger, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    intervalo_descanso = db.Column(JSONB)
    buffer_minutos = db.Column(db.Integer, nullable=False, default=15)
    activo = db.Column(db.Boolean, nullable=False, default=True)


class BloqueoCalendario(db.Model):
    __tablename__ = "bloqueos_calendario"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    groomer_id = db.Column(db.Integer, db.ForeignKey("groomers.id"))
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)
    tipo_bloqueo = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.Text)
    creado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class Cita(db.Model):
    __tablename__ = "citas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mascota_id = db.Column(db.Integer, nullable=False)
    groomer_id = db.Column(db.Integer, db.ForeignKey("groomers.id"), nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey("servicios.id"), nullable=False)
    sucursal_id = db.Column(db.Integer)
    fecha_hora_inicio = db.Column(db.DateTime, nullable=False)
    fecha_hora_fin = db.Column(db.DateTime, nullable=False)
    duracion_estimada = db.Column(db.Integer, nullable=False)
    duracion_real = db.Column(db.Integer)
    estado = db.Column(db.String(20), nullable=False, default="agendada")
    precio_estimado = db.Column(db.Numeric(10, 2))
    creado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    notas = db.Column(db.Text)
    motivo_cancelacion = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
