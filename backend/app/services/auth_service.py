from datetime import datetime, timedelta, timezone
import html
import logging
from logging.handlers import RotatingFileHandler
import os
import smtplib
from email.mime.text import MIMEText

import pyotp
from flask import request, current_app
from sqlalchemy import func, select, text
from flask_jwt_extended import create_access_token, create_refresh_token
from itsdangerous import URLSafeTimedSerializer

from ..extensions import db
from ..models import Usuario, Rol, Cliente, AuditLog, UserSession, TokenBlocklist


def _get_logger():
    logger = logging.getLogger("security_log")
    if logger.handlers:
        return logger
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "security.log"), maxBytes=500000, backupCount=3
    )
    formatter = logging.Formatter(
        "%(asctime)s | user=%(user)s | rol=%(rol)s | ip=%(ip)s | ua=%(ua)s | action=%(action)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def log_security_event(user_id, rol, action):
    logger = _get_logger()
    logger.info(
        "event",
        extra={
            "user": user_id or "-",
            "rol": rol or "-",
            "ip": request.remote_addr or "-",
            "ua": request.headers.get("User-Agent", "-")[:120],
            "action": action,
        },
    )


def log_audit(usuario_id, email_intent, exitoso, motivo_fallo=None):
    rol = None
    if usuario_id:
        usuario = Usuario.query.filter_by(id=usuario_id).first()
        rol = usuario.rol.nombre if usuario and usuario.rol else None

    registro = AuditLog(
        tabla="usuarios",
        operacion="UPDATE",
        registro_id=usuario_id,
        datos_despues={
            "action": "login_ok" if exitoso else "login_fail",
            "email": email_intent,
            "motivo": motivo_fallo,
        },
        usuario_id=usuario_id,
        ip_address=request.remote_addr,
    )
    db.session.add(registro)
    db.session.commit()

    action = "login_ok" if exitoso else f"login_fail:{motivo_fallo}"
    log_security_event(str(usuario_id) if usuario_id else "-", rol, action)


def _failed_login_query(email, within_minutes=15):
    limite = None
    if within_minutes is not None:
        limite = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)

    dialect_name = db.engine.dialect.name if db.engine and db.engine.dialect else ""
    if dialect_name == "sqlite":
        action = func.json_extract(AuditLog.datos_despues, "$.action")
        email_field = func.json_extract(AuditLog.datos_despues, "$.email")
    else:
        action = func.jsonb_extract_path_text(AuditLog.datos_despues, "action")
        email_field = func.jsonb_extract_path_text(AuditLog.datos_despues, "email")

    query = (
        AuditLog.query.filter(AuditLog.tabla == "usuarios")
        .filter(AuditLog.operacion == "UPDATE")
        .filter(action == "login_fail")
        .filter(email_field == email)
    )
    if limite is not None:
        query = query.filter(AuditLog.creado_en >= limite)
    return query


def is_blocked(email):
    fallos = _failed_login_query(email).count()
    return fallos >= 5


def get_failed_login_stats(email):
    query_15 = _failed_login_query(email, within_minutes=15)
    total = query_15.count()
    ultimo = query_15.order_by(AuditLog.creado_en.desc()).first()
    total_all = _failed_login_query(email, within_minutes=None).count()
    return {
        "total": total,
        "ultimo_fallo": ultimo.creado_en.isoformat() if ultimo else None,
        "total_all": total_all,
    }


def get_block_remaining_seconds(email, window_minutes=15):
    query_15 = _failed_login_query(email, within_minutes=window_minutes)
    ultimo = query_15.order_by(AuditLog.creado_en.desc()).first()
    if not ultimo:
        return 0

    ahora = datetime.now(timezone.utc)
    creado_en = ultimo.creado_en
    if creado_en is not None and creado_en.tzinfo is None:
        creado_en = creado_en.replace(tzinfo=timezone.utc)
    elapsed = (ahora - creado_en).total_seconds() if creado_en else 0
    remaining = int(window_minutes * 60 - elapsed)
    return max(0, remaining)


def generate_tokens(usuario, extra_claims=None):
    claims = {"rol": usuario.rol.nombre if usuario.rol else None}
    if extra_claims:
        claims.update(extra_claims)
    access_token = create_access_token(identity=str(usuario.id), additional_claims=claims)
    refresh_token = create_refresh_token(
        identity=str(usuario.id),
        additional_claims={"rol": usuario.rol.nombre if usuario.rol else None},
    )
    return access_token, refresh_token


def create_session(usuario, access_token, refresh_token):
    expires = datetime.now(timezone.utc) + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    refresh_expires = datetime.now(timezone.utc) + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]

    session = UserSession(
        usuario_id=usuario.id,
        token_jwt=access_token,
        refresh_token=refresh_token,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        fecha_expiracion=expires,
        refresh_expira=refresh_expires,
    )
    db.session.add(session)
    db.session.commit()


def generate_temp_token(usuario):
    return create_access_token(
        identity=str(usuario.id),
        additional_claims={"tipo": "pre_2fa"},
        expires_delta=timedelta(minutes=5),
    )


def get_usuario_by_email(email):
    return Usuario.query.filter_by(email=email.strip().lower()).first()


def validar_password_segura(password):
    if len(password) < 8:
        return False
    tiene_mayus = any(ch.isupper() for ch in password)
    tiene_minus = any(ch.islower() for ch in password)
    tiene_num = any(ch.isdigit() for ch in password)
    tiene_simbolo = any(ch in "!@#$%^&*()_+-=[]{};:,.?/" for ch in password)
    return tiene_mayus and tiene_minus and tiene_num and tiene_simbolo


def sanitize_text(value):
    if value is None:
        return None
    return html.escape(str(value).strip())


def generate_activation_token(usuario):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"user_id": str(usuario.id), "email": usuario.email}, salt="email-activation")


def verify_activation_token(token, max_age=900):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.loads(token, salt="email-activation", max_age=max_age)


def generate_reset_token(usuario):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"user_id": str(usuario.id), "email": usuario.email}, salt="password-reset")


def verify_reset_token(token, max_age=900):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.loads(token, salt="password-reset", max_age=max_age)


def send_activation_email(usuario, token):
    cfg = current_app.config
    if not cfg["SMTP_HOST"]:
        return False
    link = f"{cfg['FRONTEND_URL']}/activar?token={token}"
    msg = MIMEText(
        f"Hola, activa tu cuenta de Pet Spa aquí: {link}\n\nEste enlace expira en 15 minutos.",
        "plain",
        "utf-8",
    )
    msg["Subject"] = "Activa tu cuenta de Pet Spa"
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = usuario.email

    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"]) as server:
        if cfg["SMTP_USE_TLS"]:
            server.starttls()
        if cfg["SMTP_USER"]:
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)
    return True


def send_reset_email(usuario, token):
    cfg = current_app.config
    if not cfg["SMTP_HOST"]:
        return False
    link = f"{cfg['FRONTEND_URL']}/reset-password?token={token}"
    msg = MIMEText(
        f"Hola, restablece tu contraseña aquí: {link}\n\nEste enlace expira en 15 minutos.",
        "plain",
        "utf-8",
    )
    msg["Subject"] = "Restablecer contraseña - Pet Spa"
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = usuario.email

    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"]) as server:
        if cfg["SMTP_USE_TLS"]:
            server.starttls()
        if cfg["SMTP_USER"]:
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)
    return True


def registrar_cliente(data):
    rol_cliente = Rol.query.filter_by(nombre="Cliente").first()
    usuario = Usuario(
        email=data["email"].strip().lower(),
        rol_id=rol_cliente.id,
        estado_activo=False,
    )
    usuario.set_password(data["password"])

    cliente = Cliente(
        usuario=usuario,
        nombre=sanitize_text(data["nombres"]),
        apellido=sanitize_text(data["apellidos"]),
        telefono=sanitize_text(data.get("telefono")),
        direccion=sanitize_text(
            f"CI: {data.get('ci')} | Dir: {data.get('direccion')}"
        ),
        canal_notificacion="email",
    )

    db.session.add(usuario)
    db.session.add(cliente)
    db.session.commit()

    token = generate_activation_token(usuario)
    email_enviado = False
    try:
        email_enviado = send_activation_email(usuario, token)
    except Exception:
        email_enviado = False
    log_security_event(str(usuario.id), usuario.rol.nombre if usuario.rol else None, "register")

    if email_enviado:
        message = "Cuenta creada. Revisa tu correo para activar la cuenta."
    else:
        message = "Cuenta creada, pero no se pudo enviar el correo de activación."

    return {
        "message": message,
        "requiere_activacion": True,
    }


def verificar_2fa(usuario, codigo):
    totp = pyotp.TOTP(usuario.two_factor_secret)
    return totp.verify(codigo, valid_window=1)


def revoke_session(access_token=None, refresh_token=None):
    query = UserSession.query
    if access_token:
        query = query.filter_by(token_jwt=access_token)
    if refresh_token:
        query = query.filter_by(refresh_token=refresh_token)
    rows = query.all()
    for row in rows:
        db.session.delete(row)
    if rows:
        db.session.commit()


def block_jti(jti):
    if not jti:
        return False
    if TokenBlocklist.query.filter_by(jti=jti).first():
        return False
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    return True


def is_jti_blocked(jti):
    return TokenBlocklist.query.filter_by(jti=jti).first() is not None


def cleanup_blocklist(days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    TokenBlocklist.query.filter(TokenBlocklist.creado_en < cutoff).delete(synchronize_session=False)
    db.session.commit()


