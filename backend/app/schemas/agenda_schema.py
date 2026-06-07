from marshmallow import Schema, fields, validate


class ServicioSchema(Schema):
    nombre = fields.String(required=True, validate=validate.Length(min=2))
    descripcion = fields.String(required=False, allow_none=True)
    precio_base = fields.Float(required=True)
    duracion_base_minutos = fields.Integer(required=True)
    activo = fields.Boolean(required=False)


class DisponibilidadSchema(Schema):
    groomer_id = fields.Integer(required=True)
    dia_semana = fields.Integer(required=True, validate=validate.Range(min=0, max=6))
    hora_inicio = fields.String(required=True)
    hora_fin = fields.String(required=True)
    buffer_minutos = fields.Integer(required=False, validate=validate.Range(min=0, max=60))


class BloqueoSchema(Schema):
    groomer_id = fields.Integer(required=False, allow_none=True)
    fecha_inicio = fields.String(required=True)
    fecha_fin = fields.String(required=True)
    tipo_bloqueo = fields.String(required=True)
    descripcion = fields.String(required=False, allow_none=True)


class SlotsSchema(Schema):
    groomer_id = fields.Integer(required=True)
    servicio_id = fields.Integer(required=True)
    fecha = fields.String(required=True)
    tamano = fields.String(required=False, allow_none=True)
    temperamento = fields.String(required=False, allow_none=True)
    extra_minutos = fields.Integer(required=False, allow_none=True)


class CitaSchema(Schema):
    mascota_id = fields.Integer(required=True)
    groomer_id = fields.Integer(required=True)
    servicio_id = fields.Integer(required=True)
    fecha_hora_inicio = fields.String(required=True)
    fecha_hora_fin = fields.String(required=True)
    duracion_estimada = fields.Integer(required=True)
    precio_estimado = fields.Float(required=False, allow_none=True)
    notas = fields.String(required=False, allow_none=True)
