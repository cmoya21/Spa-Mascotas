from marshmallow import Schema, fields, validate


class FichaCreateSchema(Schema):
    cita_id = fields.Integer(required=True)
    servicio_id = fields.Integer(required=True)
    groomer_id = fields.Integer(required=False, allow_none=True)


class ChecklistUpdateSchema(Schema):
    items = fields.List(
        fields.Dict(),
        required=True,
        validate=validate.Length(min=1),
    )


class FotoSchema(Schema):
    url = fields.String(required=True)
    tipo = fields.String(required=True, validate=validate.OneOf(["antes", "despues"]))
    descripcion = fields.String(required=False, allow_none=True)


class CierreFichaSchema(Schema):
    estado_final = fields.String(required=False, allow_none=True)
    observaciones_final = fields.String(required=False, allow_none=True)
    notas_internas = fields.String(required=False, allow_none=True)
    insumos_consumidos = fields.List(fields.Dict(), required=False, allow_none=True)
    consumido_inventario = fields.Boolean(required=False)


class InsumosFichaSchema(Schema):
    insumos = fields.List(
        fields.Dict(),
        required=True,
        validate=validate.Length(min=1),
    )
