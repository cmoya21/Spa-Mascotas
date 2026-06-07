from marshmallow import Schema, fields, validate, pre_load


class MascotaSchema(Schema):
    id = fields.Integer(dump_only=True)
    nombre = fields.String(required=True, validate=validate.Length(min=2))
    especie = fields.String(
        required=True,
        validate=validate.OneOf(["perro", "gato"]),
    )
    raza = fields.String(required=False, allow_none=True)
    tamano = fields.String(required=False, allow_none=True)
    fecha_nacimiento = fields.Date(required=False, allow_none=True)
    peso_kg = fields.Float(required=False, allow_none=True)
    temperamento = fields.String(required=False, allow_none=True)
    alergias_conocidas = fields.String(required=False, allow_none=True)
    restricciones_medicas = fields.String(required=False, allow_none=True)
    foto_url = fields.String(required=False, allow_none=True)
    carnet_vacunas_url = fields.String(required=False, allow_none=True)
    observaciones = fields.String(required=False, allow_none=True)
    cliente_id = fields.Integer(required=False, allow_none=True)

    @pre_load
    def _normalizar_especie(self, data, **kwargs):
        if isinstance(data, dict) and data.get("especie") is not None:
            data = dict(data)
            data["especie"] = str(data["especie"]).strip().lower()
        return data
