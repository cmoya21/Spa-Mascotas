from sqlalchemy.dialects.postgresql import INET, JSONB

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, bcrypt


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    two_factor_secret = db.Column(db.String(255))
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    ultimo_acceso = db.Column(db.DateTime)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    estado_activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

    rol = db.relationship("Rol", back_populates="usuarios")
    perfil_groomer = db.relationship("Groomer", uselist=False, back_populates="usuario")
    perfil_cliente = db.relationship("Cliente", uselist=False, back_populates="usuario")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        nombre_completo = None
        if self.perfil_groomer:
            nombre_completo = f"{self.perfil_groomer.nombre} {self.perfil_groomer.apellido or ''}".strip()
        if self.perfil_cliente:
            nombre_completo = f"{self.perfil_cliente.nombre} {self.perfil_cliente.apellido or ''}".strip()

        nivel_map = {
            "Admin": "full",
            "Recepcion": "medio",
            "Groomer": "restringido",
            "Cliente": "externo",
        }

        return {
            "id": self.id,
            "email": self.email,
            "rol": self.rol.nombre if self.rol else None,
            "nivel_acceso": nivel_map.get(self.rol.nombre) if self.rol else None,
            "nombre_completo": nombre_completo,
            "nombre": nombre_completo,
            "two_factor_enabled": bool(self.two_factor_enabled),
        }

    def tiene_2fa(self):
        return bool(self.two_factor_secret) and self.two_factor_enabled


class Groomer(db.Model):
    __tablename__ = "groomers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    telefono = db.Column(db.String(30))
    especialidad = db.Column(db.String(100))
    capacidad_simultanea = db.Column(db.Integer, nullable=False, default=1)
    capacidad_diaria = db.Column(db.Integer, nullable=False, default=8)
    horario_trabajo = db.Column(JSONB)
    sucursal_id = db.Column(db.Integer)
    estado_activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    usuario = db.relationship("Usuario", back_populates="perfil_groomer")


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    telefono = db.Column(db.String(30))
    direccion = db.Column(db.Text)
    canal_notificacion = db.Column(db.String(20))
    horario_preferido = db.Column(db.String(50))
    sucursal_id = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    usuario = db.relationship("Usuario", back_populates="perfil_cliente")


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tabla = db.Column(db.String(100), nullable=False)
    operacion = db.Column(db.String(10), nullable=False)
    registro_id = db.Column(db.BigInteger)
    datos_antes = db.Column(JSONB)
    datos_despues = db.Column(JSONB)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    ip_address = db.Column(INET)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(255), nullable=False, unique=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    token_jwt = db.Column(db.Text, nullable=False, unique=True)
    refresh_token = db.Column(db.Text, nullable=False, unique=True)
    ip_address = db.Column(INET)
    user_agent = db.Column(db.Text)
    fecha_expiracion = db.Column(db.DateTime, nullable=False)
    refresh_expira = db.Column(db.DateTime, nullable=False)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
