from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..extensions import db
from ..models import Cliente, Mascota, MascotaDueno, Usuario
from ..schemas.mascota_schema import MascotaSchema
from ..utils.decorators import requiere_rol
from ..utils.responses import error, success


mascotas_bp = Blueprint("mascotas_bp", __name__, url_prefix="/api/mascotas")


def _coerce_user_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_usuario():
    usuario_id = _coerce_user_id(get_jwt_identity())
    if usuario_id is None:
        return None
    return Usuario.query.filter_by(id=usuario_id).first()


def _mascota_payload(mascota):
    return {
        "id": mascota.id,
        "nombre": mascota.nombre,
        "especie": mascota.especie,
        "raza": mascota.raza,
        "tamano": mascota.tamano,
        "fecha_nacimiento": mascota.fecha_nacimiento.isoformat() if mascota.fecha_nacimiento else None,
        "peso_kg": float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        "temperamento": mascota.temperamento,
        "alergias_conocidas": mascota.alergias_conocidas,
        "restricciones_medicas": mascota.restricciones_medicas,
        "foto_url": mascota.foto_url,
        "observaciones": mascota.observaciones,
    }


def _normalize_value(value):
    if value is None:
        return None
    return str(value).strip().lower()


def _normalize_temperamento(value):
    mapping = {
        "tranquilo": "tranquilo",
        "nervioso": "ansioso",
        "agresivo": "agresivo",
        "inquieto": "otro",
        "ansioso": "ansioso",
        "jugueton": "jugueton",
        "otro": "otro",
    }
    normalized = _normalize_value(value)
    return mapping.get(normalized, normalized)


def _resolve_or_create_cliente(usuario):
    if not usuario:
        return None
    cliente = Cliente.query.filter_by(usuario_id=usuario.id).first()
    if cliente:
        return cliente

    if not usuario.email:
        return None

    nombre_base = usuario.email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    nombre_base = nombre_base.title() or "Cliente"
    cliente = Cliente(
        usuario_id=usuario.id,
        nombre=nombre_base,
        apellido=None,
        telefono=None,
        direccion="",
        canal_notificacion="email",
    )
    db.session.add(cliente)
    db.session.flush()
    db.session.commit()
    return cliente


@mascotas_bp.get("")
@requiere_rol("Admin", "Recepcion", "Cliente")
def listar_mascotas():
    usuario = _resolve_usuario()
    if not usuario or not usuario.rol:
        return error("Acceso denegado", status=403)

    cliente_id = request.args.get("cliente_id", type=int)

    if usuario.rol.nombre == "Cliente":
        cliente = _resolve_or_create_cliente(usuario)
        if not cliente:
            return error("Cliente no encontrado", status=404)
        cliente_id = cliente.id

    if not cliente_id:
        mascotas = Mascota.query.order_by(Mascota.creado_en.desc()).all()
        return success({"mascotas": [_mascota_payload(m) for m in mascotas]})

    mascotas = (
        Mascota.query.join(MascotaDueno, MascotaDueno.mascota_id == Mascota.id)
        .filter(MascotaDueno.cliente_id == cliente_id)
        .order_by(Mascota.creado_en.desc())
        .all()
    )
    return success({"mascotas": [_mascota_payload(m) for m in mascotas]})


@mascotas_bp.post("")
@requiere_rol("Admin", "Recepcion", "Cliente")
def crear_mascota():
    try:
        data = MascotaSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    usuario = _resolve_usuario()
    if not usuario or not usuario.rol:
        return error("Acceso denegado", status=403)

    cliente_id = data.get("cliente_id")
    if usuario.rol.nombre == "Cliente":
        cliente = _resolve_or_create_cliente(usuario)
        if not cliente:
            return error("Cliente no encontrado", status=404)
        cliente_id = cliente.id

    if not cliente_id:
        return error("cliente_id requerido", status=400)

    cliente = Cliente.query.filter_by(id=cliente_id).first()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    mascota = Mascota(
        nombre=data["nombre"],
        especie=data["especie"],
        raza=data.get("raza"),
        tamano=_normalize_value(data.get("tamano")),
        fecha_nacimiento=data.get("fecha_nacimiento"),
        peso_kg=data.get("peso_kg"),
        temperamento=_normalize_temperamento(data.get("temperamento")),
        alergias_conocidas=data.get("alergias_conocidas"),
        restricciones_medicas=data.get("restricciones_medicas"),
        foto_url=data.get("foto_url"),
        observaciones=data.get("observaciones"),
    )
    db.session.add(mascota)
    db.session.flush()

    MascotaDueno.query.filter_by(cliente_id=cliente_id, es_principal=True).update(
        {"es_principal": False}
    )
    es_principal = True
    relacion = MascotaDueno(
        mascota_id=mascota.id,
        cliente_id=cliente_id,
        es_principal=es_principal,
    )
    db.session.add(relacion)
    db.session.commit()

    return success({"mascota": _mascota_payload(mascota)}, status=201)


@mascotas_bp.patch("/<int:mascota_id>")
@requiere_rol("Admin", "Recepcion", "Cliente")
def actualizar_mascota(mascota_id):
    try:
        data = MascotaSchema().load(request.get_json() or {}, partial=True)
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return error("Mascota no encontrada", status=404)

    usuario = _resolve_usuario()
    if usuario and usuario.rol and usuario.rol.nombre == "Cliente":
        if not usuario.perfil_cliente:
            return error("Acceso denegado", status=403)
        relation = MascotaDueno.query.filter_by(
            mascota_id=mascota_id,
            cliente_id=usuario.perfil_cliente.id,
        ).first()
        if not relation:
            return error("Acceso denegado", status=403)

    for key, value in data.items():
        if hasattr(mascota, key):
            if key == "temperamento":
                setattr(mascota, key, _normalize_temperamento(value))
            elif key == "tamano":
                setattr(mascota, key, _normalize_value(value))
            else:
                setattr(mascota, key, value)

    db.session.commit()
    return success({"mascota": _mascota_payload(mascota)})


@mascotas_bp.delete("/<int:mascota_id>")
@requiere_rol("Admin", "Recepcion", "Cliente")
def eliminar_mascota(mascota_id):
    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return error("Mascota no encontrada", status=404)

    usuario = _resolve_usuario()
    if usuario and usuario.rol and usuario.rol.nombre == "Cliente":
        if not usuario.perfil_cliente:
            return error("Acceso denegado", status=403)
        relation = MascotaDueno.query.filter_by(
            mascota_id=mascota_id,
            cliente_id=usuario.perfil_cliente.id,
        ).first()
        if not relation:
            return error("Acceso denegado", status=403)

    db.session.delete(mascota)
    db.session.commit()
    return success({"message": "Mascota eliminada"})


@mascotas_bp.post("/<int:mascota_id>/duenos")
@requiere_rol("Admin", "Recepcion")
def asociar_dueno(mascota_id):
    data = request.get_json() or {}
    cliente_id = data.get("cliente_id")
    if not cliente_id:
        return error("cliente_id requerido", status=400)

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return error("Mascota no encontrada", status=404)

    cliente = Cliente.query.filter_by(id=cliente_id).first()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    existing = MascotaDueno.query.filter_by(mascota_id=mascota_id, cliente_id=cliente_id).first()
    if existing:
        return error("El cliente ya esta asociado", status=409)

    relacion = MascotaDueno(
        mascota_id=mascota_id,
        cliente_id=cliente_id,
        es_principal=False,
    )
    db.session.add(relacion)
    db.session.commit()
    return success({"message": "Dueno asociado"}, status=201)
