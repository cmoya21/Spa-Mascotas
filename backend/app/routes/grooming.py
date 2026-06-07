from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import (
    Cita,
    Cliente,
    Groomer,
    Mascota,
    MascotaDueno,
    Servicio,
    ChecklistItemTemplate,
    FichaGrooming,
    FichaChecklist,
    FotoFicha,
    Notificacion,
    Producto,
    Usuario,
)
from ..schemas.grooming_schema import (
    ChecklistUpdateSchema,
    CierreFichaSchema,
    FichaCreateSchema,
    InsumosFichaSchema,
    FotoSchema,
)
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.crear_notificacion import crear_notificacion
from ..utils.plantillas_notif import mensaje_listo_recoger
from ..utils.responses import error, success


grooming_bp = Blueprint("grooming_bp", __name__, url_prefix="/api/grooming")


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


def _ficha_payload(ficha):
    return {
        "id": ficha.id,
        "cita_id": ficha.cita_id,
        "groomer_id": ficha.groomer_id,
        "checklist_completo": ficha.checklist_completo,
        "fecha_cierre": ficha.fecha_cierre.isoformat() if ficha.fecha_cierre else None,
        "insumos_consumidos": ficha.insumos_consumidos or [],
    }


def _checklist_payload(item, template):
    return {
        "id": item.id,
        "item_id": item.item_id,
        "nombre": template.nombre if template else "",
        "requiere_obs": template.requiere_obs if template else False,
        "completado": item.completado,
        "observacion": item.observacion,
    }


def _build_notification(cita):
    cliente = None
    if cita and cita.mascota_id:
        relation = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id).first()
        if relation:
            cliente = Cliente.query.filter_by(id=relation.cliente_id).first()
    if not cliente:
        return None

    existing = Notificacion.query.filter_by(
        cita_id=cita.id,
        cliente_id=cliente.id,
        tipo_evento="listo_recoger",
    ).first()
    if existing:
        return None

    mascota = Mascota.query.filter_by(id=cita.mascota_id).first() if cita else None
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first() if cita else None
    return crear_notificacion(
        cita_id=cita.id,
        cliente=cliente,
        tipo_evento="listo_recoger",
        mensaje=mensaje_listo_recoger(
            mascota.nombre if mascota else "Tu mascota",
            servicio.nombre if servicio else "grooming",
        ),
    )


def _get_groomer_id(usuario):
    if not usuario or not usuario.rol or usuario.rol.nombre != "Groomer":
        return None
    if not usuario.perfil_groomer:
        return None
    return usuario.perfil_groomer.id


def _enforce_groomer_scope(resource_groomer_id):
    usuario, rol = get_current_user()
    if rol != "Groomer":
        return None
    groomer_id = _get_groomer_id(usuario)
    if not groomer_id or resource_groomer_id != groomer_id:
        return error("Acceso denegado", status=403)
    return None


def _build_citas_payload(citas):
    mascota_ids = [cita.mascota_id for cita in citas]
    servicio_ids = [cita.servicio_id for cita in citas]
    mascotas = Mascota.query.filter(Mascota.id.in_(mascota_ids)).all() if mascota_ids else []
    servicios = Servicio.query.filter(Servicio.id.in_(servicio_ids)).all() if servicio_ids else []
    mascotas_map = {item.id: item.nombre for item in mascotas}
    servicios_map = {item.id: item.nombre for item in servicios}

    return [
        {
            "id": cita.id,
            "mascota_id": cita.mascota_id,
            "mascota_nombre": mascotas_map.get(cita.mascota_id),
            "servicio_id": cita.servicio_id,
            "servicio_nombre": servicios_map.get(cita.servicio_id),
            "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat(),
            "estado": cita.estado,
        }
        for cita in citas
    ]


@grooming_bp.get("/checklist-template")
@requiere_rol("Admin", "Recepcion", "Groomer")
def checklist_template():
    servicio_id = request.args.get("servicio_id", type=int)
    if not servicio_id:
        return error("servicio_id requerido", status=400)
    items = (
        ChecklistItemTemplate.query.filter_by(servicio_id=servicio_id, activo=True)
        .order_by(ChecklistItemTemplate.orden.asc())
        .all()
    )
    payload = [
        {
            "id": item.id,
            "nombre": item.nombre,
            "requiere_obs": item.requiere_obs,
        }
        for item in items
    ]
    return success({"items": payload})


@grooming_bp.get("/citas")
@requiere_rol("Admin", "Recepcion", "Groomer", "Cliente")
def listar_citas():
    usuario, rol = get_current_user()
    query = Cita.query
    estado = request.args.get("estado")
    if estado:
        query = query.filter_by(estado=estado)
    if rol == "Groomer":
        groomer_id = _get_groomer_id(usuario)
        if not groomer_id:
            return error("Acceso denegado", status=403)
        query = query.filter_by(groomer_id=groomer_id)
    elif rol == "Cliente":
        # limitar al cliente: obtener mascotas del cliente y filtrar
        if not usuario or not usuario.perfil_cliente:
            return error("Cliente no encontrado", status=404)
        cliente_id = usuario.perfil_cliente.id
        mascota_ids = [rel.mascota_id for rel in MascotaDueno.query.filter_by(cliente_id=cliente_id).all()]
        if mascota_ids:
            query = query.filter(Cita.mascota_id.in_(mascota_ids))
        else:
            return success({"citas": []})

    citas = query.order_by(Cita.fecha_hora_inicio.desc()).limit(200).all()
    return success({"citas": _build_citas_payload(citas)})


@grooming_bp.get("/fichas")
@requiere_rol("Admin", "Recepcion", "Groomer")
def listar_fichas():
    usuario, rol = get_current_user()
    query = FichaGrooming.query
    if rol == "Groomer":
        groomer_id = _get_groomer_id(usuario)
        if not groomer_id:
            return error("Acceso denegado", status=403)
        query = query.filter_by(groomer_id=groomer_id)
    fichas = query.order_by(FichaGrooming.creado_en.desc()).limit(200).all()
    return success({"fichas": [_ficha_payload(ficha) for ficha in fichas]})


@grooming_bp.post("/fichas")
@requiere_rol("Admin", "Recepcion", "Groomer")
def crear_ficha():
    try:
        data = FichaCreateSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    cita = Cita.query.filter_by(id=data["cita_id"]).first()
    if not cita:
        return error("Cita no encontrada", status=404)

    scope_error = _enforce_groomer_scope(cita.groomer_id)
    if scope_error:
        return scope_error

    if FichaGrooming.query.filter_by(cita_id=cita.id).first():
        return error("La ficha ya existe", status=409)

    ficha = FichaGrooming(
        cita_id=cita.id,
        groomer_id=data.get("groomer_id") or cita.groomer_id,
    )
    db.session.add(ficha)
    db.session.flush()

    templates = ChecklistItemTemplate.query.filter_by(servicio_id=data["servicio_id"], activo=True).all()
    for template in templates:
        db.session.add(
            FichaChecklist(
                ficha_id=ficha.id,
                item_id=template.id,
                completado=False,
            )
        )

    db.session.commit()
    return success({"ficha": _ficha_payload(ficha)}, status=201)


@grooming_bp.get("/fichas/<int:ficha_id>")
@requiere_rol("Admin", "Recepcion", "Groomer")
def obtener_ficha(ficha_id):
    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return error("Ficha no encontrada", status=404)

    scope_error = _enforce_groomer_scope(ficha.groomer_id)
    if scope_error:
        return scope_error

    items = FichaChecklist.query.filter_by(ficha_id=ficha.id).all()
    template_map = {
        item.id: item
        for item in ChecklistItemTemplate.query.filter(
            ChecklistItemTemplate.id.in_([i.item_id for i in items])
        ).all()
    }

    payload = _ficha_payload(ficha)
    payload["checklist"] = [_checklist_payload(item, template_map.get(item.item_id)) for item in items]
    return success({"ficha": payload})


@grooming_bp.post("/fichas/<int:ficha_id>/checklist")
@requiere_rol("Admin", "Recepcion", "Groomer")
def actualizar_checklist(ficha_id):
    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return error("Ficha no encontrada", status=404)

    scope_error = _enforce_groomer_scope(ficha.groomer_id)
    if scope_error:
        return scope_error

    try:
        data = ChecklistUpdateSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    items = {item.id: item for item in FichaChecklist.query.filter_by(ficha_id=ficha.id).all()}
    for item in data["items"]:
        item_id = item.get("id")
        if not item_id or item_id not in items:
            continue
        registro = items[item_id]
        registro.completado = bool(item.get("completado"))
        registro.observacion = item.get("observacion")
        registro.completado_en = datetime.now(timezone.utc) if registro.completado else None

    db.session.commit()
    return success({"message": "Checklist actualizado"})


@grooming_bp.post("/fichas/<int:ficha_id>/fotos")
@requiere_rol("Admin", "Recepcion", "Groomer")
def agregar_foto(ficha_id):
    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return error("Ficha no encontrada", status=404)

    scope_error = _enforce_groomer_scope(ficha.groomer_id)
    if scope_error:
        return scope_error

    try:
        data = FotoSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    foto = FotoFicha(
        ficha_id=ficha.id,
        url=data["url"],
        tipo=data["tipo"],
        descripcion=data.get("descripcion"),
    )
    db.session.add(foto)
    db.session.commit()
    return success({"message": "Foto registrada"}, status=201)


@grooming_bp.patch("/fichas/<int:ficha_id>/insumos")
@requiere_rol("Admin", "Recepcion", "Groomer")
def registrar_insumos_ficha(ficha_id):
    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return error("Ficha no encontrada", status=404)

    scope_error = _enforce_groomer_scope(ficha.groomer_id)
    if scope_error:
        return scope_error

    if ficha.fecha_cierre:
        return error("La ficha ya fue cerrada", status=409)

    try:
        data = InsumosFichaSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    insumos = []
    for item in data["insumos"]:
        producto_id = item.get("producto_id")
        cantidad = item.get("cantidad")
        if not producto_id or cantidad is None:
            return error("Insumo invalido", status=400)
        if cantidad <= 0:
            return error("Cantidad invalida", status=400)

        producto = Producto.query.filter_by(id=producto_id).first()
        if not producto:
            return error("Producto no encontrado", status=404)
        if producto.stock <= 0:
            return error(f"Stock insuficiente para {producto.nombre}", status=422)

        insumos.append({"producto_id": int(producto_id), "cantidad": float(cantidad)})

    ficha.insumos_consumidos = insumos
    db.session.commit()
    return success({"ficha": _ficha_payload(ficha)})


def _cerrar_ficha_impl(ficha_id):
    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return error("Ficha no encontrada", status=404)

    scope_error = _enforce_groomer_scope(ficha.groomer_id)
    if scope_error:
        return scope_error

    if ficha.fecha_cierre:
        return error("La ficha ya fue cerrada", status=409)

    try:
        data = CierreFichaSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    pendientes = FichaChecklist.query.filter_by(ficha_id=ficha.id, completado=False).count()
    if pendientes > 0:
        return error("Checklist incompleto", status=422, details={"pendientes": pendientes})

    fotos_antes = FotoFicha.query.filter_by(ficha_id=ficha.id, tipo="antes").count()
    fotos_despues = FotoFicha.query.filter_by(ficha_id=ficha.id, tipo="despues").count()
    if fotos_antes == 0 or fotos_despues == 0:
        return error("Faltan fotos antes/despues", status=422)

    ficha.estado_final = data.get("estado_final")
    ficha.observaciones_final = data.get("observaciones_final")
    ficha.notas_internas = data.get("notas_internas")
    if data.get("insumos_consumidos") is not None:
        ficha.insumos_consumidos = data.get("insumos_consumidos")
    ficha.consumido_inventario = True
    ficha.fecha_cierre = datetime.now(timezone.utc)
    ficha.checklist_completo = True

    if ficha.insumos_consumidos:
        for insumo in ficha.insumos_consumidos:
            producto_id = insumo.get("producto_id")
            cantidad = insumo.get("cantidad")
            if not producto_id or cantidad is None:
                return error("Insumo invalido", status=400)
            producto = Producto.query.filter_by(id=producto_id).first()
            if not producto:
                return error("Producto no encontrado", status=404)
            if producto.stock - float(cantidad) < 0:
                return error(f"Stock insuficiente para {producto.nombre}", status=422)

    cita = Cita.query.filter_by(id=ficha.cita_id).first()
    if cita:
        cita.estado = "completada"

    notificacion = _build_notification(cita) if cita else None
    if notificacion:
        db.session.add(notificacion)

    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        message = str(exc.orig) if getattr(exc, "orig", None) else "Error al cerrar la ficha"
        return error(message, status=422)

    return success({"message": "Ficha cerrada"})


@grooming_bp.patch("/fichas/<int:ficha_id>/cerrar")
@requiere_rol("Admin", "Recepcion", "Groomer")
def cerrar_ficha(ficha_id):
    return _cerrar_ficha_impl(ficha_id)


@grooming_bp.post("/fichas/<int:ficha_id>/cierre")
@requiere_rol("Admin", "Recepcion", "Groomer")
def cerrar_ficha_legacy(ficha_id):
    return _cerrar_ficha_impl(ficha_id)
