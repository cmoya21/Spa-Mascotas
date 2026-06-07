from marshmallow import Schema, fields, validate


class InsumoSalidaSchema(Schema):
    ficha_id = fields.Integer(required=True)
    producto_id = fields.Integer(required=True)
    cantidad = fields.Float(required=True)
    estado = fields.String(
        required=True,
        validate=validate.OneOf(["entregado", "usado", "devuelto", "desperdiciado"])
    )


class InsumoUpdateSchema(Schema):
    estado = fields.String(
        required=True,
        validate=validate.OneOf(["entregado", "usado", "devuelto", "desperdiciado"])
    )
