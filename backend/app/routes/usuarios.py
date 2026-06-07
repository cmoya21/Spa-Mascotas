from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import Cliente, Groomer, Rol, Usuario
from ..utils.roles import require_role
from ..utils.responses import error, success


usuarios_bp = Blueprint("usuarios_bp", __name__, url_prefix="/api")


def _coerce_user_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _serialize_usuario(usuario):
    data = usuario.to_dict()
    data["estado_activo"] = usuario.estado_activo
    data["ultimo_acceso"] = usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None
    return data


def _crear_perfil_usuario(usuario, rol_nombre, nombre=None):
    if rol_nombre == "Groomer":
        db.session.add(
            Groomer(
                usuario_id=usuario.id,
                nombre=nombre or "Groomer",
                apellido=None,
                capacidad_simultanea=1,
                estado_activo=True,
            )
        )
    elif rol_nombre == "Cliente":
        db.session.add(
            Cliente(
                usuario_id=usuario.id,
                nombre=nombre or "Cliente",
                apellido=None,
                canal_notificacion="email",
            )
        )


@usuarios_bp.get("/usuarios")
@require_role("Admin")
def listar_usuarios():
    usuarios = (
        Usuario.query.join(Rol)
        .order_by(Usuario.creado_en.desc())
        .all()
    )
    payload = []
    for usuario in usuarios:
        item = _serialize_usuario(usuario)
        item["rol"] = usuario.rol.nombre if usuario.rol else None
        payload.append(item)
    return success({"usuarios": payload})


@usuarios_bp.post("/usuarios")
@require_role("Admin")
def crear_usuario():
    data = request.get_json() or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    rol_nombre = str(data.get("rol_nombre") or "").strip()
    nombre = str(data.get("nombre") or "").strip() or None

    if not email:
        return error("email requerido", status=422)
    if Usuario.query.filter_by(email=email).first():
        return error("El correo ya está en uso", status=422)
    if rol_nombre not in {"Admin", "Recepcion", "Groomer", "Cliente"}:
        return error("rol_nombre invalido", status=422)
    if len(password) < 8:
        return error("password demasiado corta", status=422)

    rol = Rol.query.filter_by(nombre=rol_nombre).first()
    if not rol:
        return error("Rol no encontrado", status=404)

    usuario = Usuario(email=email, rol_id=rol.id, estado_activo=True)
    usuario.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
    db.session.add(usuario)
    db.session.flush()
    _crear_perfil_usuario(usuario, rol_nombre, nombre)
    db.session.commit()

    return success({"usuario": _serialize_usuario(usuario)}, status=201)


@usuarios_bp.patch("/usuarios/<int:usuario_id>/estado")
@require_role("Admin")
def actualizar_estado(usuario_id):
    actor_id = _coerce_user_id(get_jwt_identity())
    if actor_id == usuario_id:
        return error("No puedes desactivarte a ti mismo", status=422)

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return error("Usuario no encontrado", status=404)

    data = request.get_json(silent=True) or {}
    if "activo" in data and data["activo"] is not None:
        usuario.estado_activo = bool(data["activo"])
    else:
        usuario.estado_activo = not bool(usuario.estado_activo)
    usuario.actualizado_en = datetime.now(timezone.utc)
    db.session.commit()
    return success({"usuario": _serialize_usuario(usuario)})


@usuarios_bp.patch("/usuarios/<int:usuario_id>/password")
@require_role("Admin")
def cambiar_password(usuario_id):
    data = request.get_json() or {}
    nueva_password = str(data.get("nueva_password") or "")
    if len(nueva_password) < 8:
        return error("nueva_password demasiado corta", status=422)

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return error("Usuario no encontrado", status=404)

    usuario.password_hash = generate_password_hash(nueva_password, method="pbkdf2:sha256", salt_length=16)
    usuario.actualizado_en = datetime.now(timezone.utc)
    db.session.commit()
    return success({"usuario": _serialize_usuario(usuario)})


@usuarios_bp.get("/roles")
@require_role("Admin")
def listar_roles():
    roles = Rol.query.order_by(Rol.nombre.asc()).all()
    return success({"roles": [{"id": rol.id, "nombre": rol.nombre} for rol in roles]})


@usuarios_bp.put("/roles")
@require_role("Admin")
def actualizar_roles():
    data = request.get_json() or {}
    roles = data.get("roles") or []
    resultado = []
    for item in roles:
        rol_id = item.get("id")
        nombre = str(item.get("nombre") or "").strip()
        if not rol_id or not nombre:
            continue
        rol = db.session.get(Rol, int(rol_id))
        if not rol:
            continue
        rol.nombre = nombre
        resultado.append({"id": rol.id, "nombre": rol.nombre})
    db.session.commit()
    return success({"roles": resultado})