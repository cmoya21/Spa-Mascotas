from datetime import datetime, timezone
import os

import pyotp
import qrcode
from urllib.parse import urlencode

from flask import Blueprint, request, current_app, redirect
from sqlalchemy import func
from werkzeug.security import check_password_hash as werkzeug_check

def check_password_hash(pwhash, password):
    # Soportar bcrypt ($2b$ o $2a$) Y werkzeug (pbkdf2:)
    if pwhash.startswith('$2b$') or pwhash.startswith('$2a$'):
        import bcrypt
        return bcrypt.checkpw(
            password.encode('utf-8'),
            pwhash.encode('utf-8')
        )
    return werkzeug_check(pwhash, password)
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from ..extensions import db, oauth, limiter
from ..models import Usuario, Rol, UserSession, Cliente, TokenBlocklist
from ..utils.roles import require_role
from ..schemas.auth_schema import (
    Activar2FASchema,
    ForgotPasswordSchema,
    LoginSchema,
    RegisterSchema,
    ResetPasswordSchema,
    Verificar2FASchema,
)
from ..services import auth_service
from ..utils.responses import error, success


auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")


def _coerce_user_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _usuario_auth_payload(usuario):
    payload = usuario.to_dict()
    payload.update(
        {
            "id": usuario.id,
            "email": usuario.email,
            "rol": usuario.rol.nombre if usuario.rol else None,
            "nombre": payload.get("nombre") or payload.get("nombre_completo"),
            "two_factor_enabled": bool(usuario.two_factor_enabled),
        }
    )
    return payload


def _issue_tokens(usuario):
    claims = {"rol": usuario.rol.nombre if usuario.rol else None}
    access_token = create_access_token(identity=str(usuario.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(usuario.id), additional_claims=claims)
    return access_token, refresh_token


def _block_jti_from_token(token):
    try:
        claims = decode_token(token)
    except Exception:
        return False
    jti = claims.get("jti")
    if not jti:
        return False
    if TokenBlocklist.query.filter_by(jti=jti).first():
        return True
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    return True


def _login_2fa_response(usuario, codigo):
    if not auth_service.verificar_2fa(usuario, codigo):
        auth_service.log_audit(usuario.id, usuario.email, False, "2fa_invalido")
        return error("Código inválido", status=401)

    usuario.ultimo_acceso = datetime.now(timezone.utc)
    db.session.commit()
    auth_service.log_audit(usuario.id, usuario.email, True)

    access_token, refresh_token = _issue_tokens(usuario)
    return success(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "usuario": _usuario_auth_payload(usuario),
        }
    )


@auth_bp.post("/login")
@limiter.limit("30 per minute")
def login():
    data = LoginSchema().load(request.get_json() or {})
    email = data["email"].strip().lower()

    if auth_service.is_blocked(email):
        return error(
            "Cuenta bloqueada temporalmente. Intenta en 15 minutos.",
            status=429,
            details={"retry_after_seconds": auth_service.get_block_remaining_seconds(email)},
        )

    usuario = auth_service.get_usuario_by_email(email)
    if not usuario:
        auth_service.log_audit(None, email, False, "login_fail")
        return error("Credenciales inválidas", status=401)

    if not usuario.estado_activo:
        auth_service.log_audit(usuario.id, email, False, "login_fail")
        return error("Cuenta desactivada", status=403)

    if not check_password_hash(usuario.password_hash, data["password"]):
        auth_service.log_audit(usuario.id, email, False, "login_fail")
        return error("Credenciales inválidas", status=401)

    if usuario.tiene_2fa():
        temp_token = auth_service.generate_temp_token(usuario)
        return success({"requires_2fa": True, "requiere_2fa": True, "temp_token": temp_token})

    usuario.ultimo_acceso = datetime.now(timezone.utc)
    db.session.commit()
    auth_service.log_audit(usuario.id, email, True, "login_ok")

    access_token, refresh_token = _issue_tokens(usuario)
    auth_service.create_session(usuario, access_token, refresh_token)
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "usuario": _usuario_auth_payload(usuario),
    }
    return success(payload)


@auth_bp.get("/debug-bloqueo")
def debug_bloqueo():
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return error("Email requerido", status=400)
    stats = auth_service.get_failed_login_stats(email)
    db_name = db.session.execute(func.current_database()).scalar()
    return success({
        "email": email,
        "fallos_ultimos_15_min": stats["total"],
        "ultimo_fallo": stats["ultimo_fallo"],
        "fallos_totales": stats["total_all"],
        "bloqueado": stats["total"] >= 5,
        "database": db_name,
    })


@auth_bp.post("/login-2fa")
@auth_bp.post("/verificar-2fa")
def login_2fa():
    data = request.get_json() or {}
    temp_token = data.get("temp_token")
    codigo = data.get("code") or data.get("codigo_totp")
    if not temp_token or not codigo:
        return error("Datos inválidos", status=422)

    try:
        claims = decode_token(temp_token)
    except Exception:
        return error("Token inválido", status=401)

    if claims.get("tipo") != "pre_2fa":
        return error("Token inválido", status=401)

    usuario_id = _coerce_user_id(claims.get("sub"))
    if usuario_id is None:
        return error("Token inválido", status=401)

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario:
        return error("Credenciales inválidas", status=401)

    return _login_2fa_response(usuario, codigo)


@auth_bp.post("/register")
def register():
    data = RegisterSchema().load(request.get_json() or {})

    if Usuario.query.filter_by(email=data["email"].strip().lower()).first():
        return error("El correo ya está en uso", status=400)

    if Rol.query.filter_by(nombre="Cliente").first() is None:
        return error("Configuración incompleta", status=500)

    if not auth_service.validar_password_segura(data["password"]):
        return error("Contraseña insegura", status=400)

    if auth_service.is_blocked(data["email"]):
        return error("Demasiados intentos fallidos", status=429)

    payload = auth_service.registrar_cliente(data)
    return success(payload, status=201)


@auth_bp.post("/forgot-password")
def forgot_password():
    data = ForgotPasswordSchema().load(request.get_json() or {})
    email = data["email"].strip().lower()
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return success({"message": "Si el correo existe, enviaremos un enlace."})

    token = auth_service.generate_reset_token(usuario)
    auth_service.send_reset_email(usuario, token)
    auth_service.log_security_event(str(usuario.id), usuario.rol.nombre if usuario.rol else None, "password_reset_requested")
    return success({"message": "Si el correo existe, enviaremos un enlace."})


@auth_bp.post("/reset-password")
def reset_password():
    data = ResetPasswordSchema().load(request.get_json() or {})
    if not auth_service.validar_password_segura(data["password"]):
        return error("Contraseña insegura", status=400)
    try:
        claims = auth_service.verify_reset_token(data["token"], max_age=900)
    except Exception:
        return error("Token inválido o expirado", status=400)

    usuario = Usuario.query.filter_by(id=claims.get("user_id")).first()
    if not usuario:
        return error("Usuario no encontrado", status=404)

    usuario.set_password(data["password"])
    db.session.commit()
    auth_service.log_security_event(str(usuario.id), usuario.rol.nombre if usuario.rol else None, "password_reset")
    return success({"message": "Contraseña actualizada correctamente"})


@auth_bp.get("/activar-cuenta")
def activar_cuenta():
    token = request.args.get("token")
    if not token:
        return error("Token inválido", status=400)
    try:
        claims = auth_service.verify_activation_token(token, max_age=900)
    except Exception:
        return error("Token inválido o expirado", status=400)

    usuario_id = _coerce_user_id(claims.get("user_id"))
    if usuario_id is None:
        return error("Token inválido", status=400)

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario:
        return error("Usuario no encontrado", status=404)

    usuario.estado_activo = True
    db.session.commit()
    auth_service.log_security_event(str(usuario.id), usuario.rol.nombre if usuario.rol else None, "email_activado")

    return success({"message": "Cuenta activada correctamente"})


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    usuario_id = _coerce_user_id(get_jwt_identity())
    if usuario_id is None:
        return error("Token inválido", status=401)

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario:
        return error("Token inválido", status=401)

    access_token = create_access_token(
        identity=str(usuario.id),
        additional_claims={"rol": usuario.rol.nombre if usuario.rol else None},
    )
    return success({"access_token": access_token})


@auth_bp.route("/logout", methods=["POST", "DELETE"])
@jwt_required()
def logout():
    jwt_data = get_jwt()
    access_jti = jwt_data.get("jti")
    if access_jti:
        _block_jti_from_token(request.headers.get("Authorization", "").replace("Bearer ", "").strip())

    refresh_token = (request.get_json(silent=True) or {}).get("refresh_token")
    if refresh_token:
        _block_jti_from_token(refresh_token)

    return success({"message": "Sesión cerrada correctamente"})


@auth_bp.get("/me")
@jwt_required()
def me():
    usuario_id = _coerce_user_id(get_jwt_identity())
    if usuario_id is None:
        return error("Token inválido", status=401)

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario:
        return error("Usuario no encontrado", status=404)

    return success(_usuario_auth_payload(usuario))


@auth_bp.get("/perfil")
@jwt_required()
def perfil():
    return me()


@auth_bp.post("/setup-2fa")
@require_role("Admin", "Recepcion")
@jwt_required()
def setup_2fa():
    usuario_id = _coerce_user_id(get_jwt_identity())
    usuario = Usuario.query.filter_by(id=usuario_id).first() if usuario_id is not None else None
    if not usuario:
        return error("Usuario no encontrado", status=404)

    if not usuario.rol or usuario.rol.nombre not in {"Admin", "Recepcion"}:
        return error("Acceso denegado", status=403)

    if usuario.two_factor_enabled:
        return error("2FA ya está activado", status=409)

    secreto = pyotp.random_base32()
    usuario.two_factor_secret = secreto
    db.session.commit()
    qr_uri = pyotp.TOTP(secreto).provisioning_uri(name=usuario.email, issuer_name="Spa Mascotas")
    return success({"secret": secreto, "qr_uri": qr_uri, "mensaje": "Escanea el QR en tu app autenticadora"})


@auth_bp.post("/verify-2fa")
@require_role("Admin", "Recepcion")
@jwt_required()
def verify_2fa():
    data = request.get_json() or {}
    codigo = str(data.get("code") or "").strip()
    if len(codigo) != 6:
        return error("Código inválido", status=401)

    usuario_id = _coerce_user_id(get_jwt_identity())
    usuario = Usuario.query.filter_by(id=usuario_id).first() if usuario_id is not None else None
    if not usuario:
        return error("Usuario no encontrado", status=404)

    if not usuario.rol or usuario.rol.nombre not in {"Admin", "Recepcion"}:
        return error("Acceso denegado", status=403)

    if not usuario.two_factor_secret:
        return error("2FA no configurado", status=409)

    totp = pyotp.TOTP(usuario.two_factor_secret)
    if not totp.verify(codigo, valid_window=1):
        return error("Código inválido", status=401)

    usuario.two_factor_enabled = True
    db.session.commit()
    return success({"mensaje": "2FA activado correctamente"})


@auth_bp.post("/activar-2fa")
@jwt_required()
def activar_2fa():
    return verify_2fa()


@auth_bp.get("/configurar-2fa")
@jwt_required()
def configurar_2fa():
    return setup_2fa()


@auth_bp.get("/google/start")
def google_start():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        return error("OAuth no configurado", status=501)

    oauth.register(
        name="google",
        client_id=current_app.config["GOOGLE_CLIENT_ID"],
        client_secret=current_app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    redirect_uri = current_app.config.get("GOOGLE_OAUTH_REDIRECT")
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.get("/google/callback")
def google_callback():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        return error("OAuth no configurado", status=501)

    oauth.register(
        name="google",
        client_id=current_app.config["GOOGLE_CLIENT_ID"],
        client_secret=current_app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo:
        return error("OAuth inválido", status=400)

    email = userinfo.get("email")
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        rol_cliente = Rol.query.filter_by(nombre="Cliente").first()
        usuario = Usuario(email=email, rol_id=rol_cliente.id, estado_activo=True)
        usuario.set_password(os.urandom(12).hex())
        db.session.add(usuario)
        db.session.commit()

        cliente = Cliente(
            usuario_id=usuario.id,
            nombre=userinfo.get("given_name") or "Cliente",
            apellido=userinfo.get("family_name"),
            telefono=None,
            direccion="",
            canal_notificacion="email",
        )
        db.session.add(cliente)
        db.session.commit()

    access_token, refresh_token = auth_service.generate_tokens(usuario)
    query = urlencode(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "rol": usuario.rol.nombre if usuario.rol else "",
            "email": usuario.email,
        }
    )
    callback_url = f"{current_app.config['FRONTEND_URL']}/oauth/google?{query}"
    return redirect(callback_url)
