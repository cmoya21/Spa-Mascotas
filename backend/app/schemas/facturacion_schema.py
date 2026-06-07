from marshmallow import Schema, fields, validate


class FacturaSchema(Schema):
    cita_id = fields.Integer(required=False, allow_none=True)
    cliente_id = fields.Integer(required=True)
    subtotal = fields.Float(required=True)
    impuesto = fields.Float(required=False, allow_none=True)
    descuento = fields.Float(required=False, allow_none=True)
    metodo_pago = fields.String(required=False, allow_none=True)
    notas = fields.String(required=False, allow_none=True)


class PagoSchema(Schema):
    factura_id = fields.Integer(required=True)
    monto = fields.Float(required=True)
    metodo_pago = fields.String(required=True, validate=validate.OneOf(["efectivo", "qr", "transferencia"]))
    referencia_transaccion = fields.String(required=False, allow_none=True)
