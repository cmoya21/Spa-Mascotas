from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..extensions import db
from ..models import Usuario, Rol, Groomer, Cliente
from ..schemas.auth_schema import CrearEmpleadoSchema
from ..services import auth_service
from ..utils.decorators import requiere_rol
from ..utils.responses import error, success


admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")


def _coerce_user_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _usuario_payload(usuario):
    data = usuario.to_dict()
    data["estado_activo"] = usuario.estado_activo
    data["ultimo_acceso"] = usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None
    return data


def _cliente_payload(cliente):
    return {
        "id": str(cliente.id),
        "usuario_id": str(cliente.usuario_id),
        "email": cliente.usuario.email if cliente.usuario else None,
        "nombre": cliente.nombre,
        "apellido": cliente.apellido,
        "telefono": cliente.telefono,
        "direccion": cliente.direccion,
        "estado_activo": cliente.usuario.estado_activo if cliente.usuario else None,
    }


@admin_bp.post("/empleados")
@requiere_rol("Admin")
def crear_empleado():
    try:
        data = CrearEmpleadoSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos inválidos", status=400, details=exc.messages)
    email = data["email"].strip().lower()

    if Usuario.query.filter_by(email=email).first():
        return error("El correo ya está registrado", status=400)

    if not auth_service.validar_password_segura(data["password"]):
        return error("Contraseña insegura", status=400)

    rol = Rol.query.filter_by(nombre=data["rol"]).first()
    if not rol:
        return error("Rol inválido", status=400)

    usuario = Usuario(
        email=email,
        rol_id=rol.id,
        estado_activo=True,
        ultimo_acceso=None,
    )
    usuario.set_password(data["password"])
    db.session.add(usuario)
    db.session.flush()

    if data["rol"] == "Groomer":
        if not data.get("especialidad") or not data.get("turno"):
            return error("Especialidad y turno son obligatorios para groomers", status=400)

        groomer = Groomer(
            usuario_id=usuario.id,
            nombre=auth_service.sanitize_text(data["nombres"]),
            apellido=auth_service.sanitize_text(data["apellidos"]),
            telefono=auth_service.sanitize_text(data.get("telefono")),
            especialidad=auth_service.sanitize_text(data["especialidad"]),
            horario_trabajo={"turno": auth_service.sanitize_text(data["turno"])},
            capacidad_simultanea=1,
            estado_activo=True,
        )
        db.session.add(groomer)

    usuario.actualizado_en = datetime.now(timezone.utc)
    db.session.commit()

    admin_id = _coerce_user_id(get_jwt_identity())
    auth_service.log_security_event(str(admin_id) if admin_id else "-", "Admin", "crear_empleado")

    return success({
        "message": "Empleado creado correctamente",
        "usuario": usuario.to_dict(),
    }, status=201)


@admin_bp.get("/usuarios")
@requiere_rol("Admin")
def listar_usuarios():
    rol = request.args.get("rol")
    query = Usuario.query
    if rol:
        rol_obj = Rol.query.filter_by(nombre=rol).first()
        if rol_obj:
            query = query.filter_by(rol_id=rol_obj.id)
    usuarios = query.order_by(Usuario.creado_en.desc()).all()
    return success({"usuarios": [_usuario_payload(user) for user in usuarios]})


@admin_bp.get("/clientes")
@requiere_rol("Admin", "Recepcion")
def listar_clientes():
    clientes = Cliente.query.order_by(Cliente.creado_en.desc()).all()
    return success({"clientes": [_cliente_payload(cliente) for cliente in clientes]})


@admin_bp.get("/groomers")
@requiere_rol("Admin", "Recepcion", "Cliente")
def listar_groomers():
    groomers = Groomer.query.order_by(Groomer.nombre.asc(), Groomer.apellido.asc()).all()
    payload = [
        {
            "id": g.id,
            "nombre": g.nombre,
            "apellido": g.apellido,
            "telefono": g.telefono,
            "especialidad": g.especialidad,
        }
        for g in groomers
    ]
    return success({"groomers": payload})


@admin_bp.patch("/usuarios/<int:usuario_id>/estado")
@requiere_rol("Admin")
def actualizar_estado(usuario_id):
    data = request.get_json() or {}
    activo = data.get("activo")
    if activo is None:
        return error("Campo 'activo' requerido", status=400)

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario:
        return error("Usuario no encontrado", status=404)

    usuario.estado_activo = bool(activo)
    usuario.actualizado_en = datetime.now(timezone.utc)
    db.session.commit()

    admin_id = _coerce_user_id(get_jwt_identity())
    accion = "activar_usuario" if usuario.estado_activo else "desactivar_usuario"
    auth_service.log_security_event(str(admin_id) if admin_id else "-", "Admin", accion)

    return success({"usuario": _usuario_payload(usuario)})
