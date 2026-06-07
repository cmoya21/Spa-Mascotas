from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1))


class RegisterSchema(Schema):
    nombres = fields.String(required=True, validate=validate.Length(min=2))
    apellidos = fields.String(required=True, validate=validate.Length(min=2))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))
    telefono = fields.String(required=False, allow_none=True)
    ci = fields.String(required=True, validate=validate.Length(min=5))
    direccion = fields.String(required=True, validate=validate.Length(min=4))


class Verificar2FASchema(Schema):
    temp_token = fields.String(required=True)
    codigo_totp = fields.String(required=True, validate=validate.Length(equal=6))


class RefreshSchema(Schema):
    refresh_token = fields.String(required=False, allow_none=True)


class Activar2FASchema(Schema):
    secreto = fields.String(required=True)
    codigo_verificacion = fields.String(required=True, validate=validate.Length(equal=6))


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.String(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))


class CrearEmpleadoSchema(Schema):
    nombres = fields.String(required=True, validate=validate.Length(min=2))
    apellidos = fields.String(required=True, validate=validate.Length(min=2))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))
    telefono = fields.String(required=False, allow_none=True)
    rol = fields.String(required=True, validate=validate.OneOf(["Recepcion", "Groomer"]))
    especialidad = fields.String(required=False, allow_none=True)
    turno = fields.String(required=False, allow_none=True)
