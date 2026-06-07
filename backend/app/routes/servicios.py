from flask import Blueprint, abort, request
from sqlalchemy import text

from ..extensions import db
from ..models import Producto, Servicio
from ..models.grooming import ChecklistItemTemplate
from ..utils.decorators import requiere_rol
from ..utils.duracion import calcular_duracion, desglose_duracion, DEFAULT_FACTOR_TAMANO
from ..utils.responses import success


servicios_bp = Blueprint("servicios_bp", __name__, url_prefix="/api/servicios")


def _parse_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text_value = str(value).strip().lower()
    if text_value in {"1", "true", "t", "yes", "si", "on"}:
        return True
    if text_value in {"0", "false", "f", "no", "off"}:
        return False
    return None


def _abort_json(status_code, message, **extra):
    payload = {"success": False, "message": message}
    payload.update(extra)
    abort(status_code, description=payload)


def _service_exists(service_id):
    servicio = Servicio.query.filter_by(id=service_id).first()
    if not servicio:
        _abort_json(404, "Servicio no encontrado")
    return servicio


def _service_payload(servicio):
    checklist = (
        ChecklistItemTemplate.query.filter_by(servicio_id=servicio.id, activo=True)
        .order_by(ChecklistItemTemplate.orden.asc(), ChecklistItemTemplate.id.asc())
        .all()
    )
    return {
        "id": servicio.id,
        "nombre": servicio.nombre,
        "descripcion": servicio.descripcion,
        "precio_base": float(servicio.precio_base),
        "duracion_base_minutos": servicio.duracion_base_minutos,
        "permite_doble_booking": bool(servicio.permite_doble_booking),
        "requiere_bloqueo_consecutivo": bool(servicio.requiere_bloqueo_consecutivo),
        "factor_tamano_raza": servicio.factor_tamano_raza or DEFAULT_FACTOR_TAMANO,
        "consumo_insumos": servicio.consumo_insumos or [],
        "activo": bool(servicio.activo),
        "sucursal_id": servicio.sucursal_id,
        "creado_en": servicio.creado_en.isoformat() if servicio.creado_en else None,
        "actualizado_en": servicio.actualizado_en.isoformat() if servicio.actualizado_en else None,
        "checklist_items": [
            {
                "id": item.id,
                "nombre": item.nombre,
                "requiere_obs": bool(item.requiere_obs),
                "orden": item.orden,
            }
            for item in checklist
        ],
    }


def _validate_factor_tamano(data):
    factor = data.get("factor_tamano_raza") or DEFAULT_FACTOR_TAMANO.copy()
    if not isinstance(factor, dict):
        _abort_json(422, "factor_tamano_raza debe ser un objeto JSON")
    missing = [key for key in ("pequeno", "mediano", "grande", "gigante") if key not in factor]
    if missing:
        _abort_json(422, "factor_tamano_raza debe incluir pequeno, mediano, grande y gigante")
    normalized = {}
    for key in ("pequeno", "mediano", "grande", "gigante"):
        try:
            normalized[key] = float(factor[key])
        except (TypeError, ValueError):
            _abort_json(422, f"factor_tamano_raza.{key} debe ser numérico")
    return normalized


def _validate_consumo_insumos(consumo_insumos):
    if not consumo_insumos:
        return []
    if not isinstance(consumo_insumos, list):
        _abort_json(422, "consumo_insumos debe ser una lista JSON")

    normalized = []
    for index, item in enumerate(consumo_insumos):
        if not isinstance(item, dict):
            _abort_json(422, f"consumo_insumos[{index}] debe ser un objeto JSON")
        try:
            producto_id = int(item.get("producto_id"))
            cantidad = float(item.get("cantidad"))
        except (TypeError, ValueError):
            _abort_json(422, f"consumo_insumos[{index}] tiene datos invalidos")
        producto = Producto.query.filter_by(id=producto_id).first()
        if not producto:
            _abort_json(422, f"Producto ID {producto_id} no encontrado en inventario")
        normalized.append({"producto_id": producto_id, "cantidad": cantidad})
    return normalized


def _validate_servicio_payload(data):
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        _abort_json(422, "nombre es requerido")

    try:
        precio_base = float(data.get("precio_base"))
    except (TypeError, ValueError):
        _abort_json(422, "precio_base debe ser numérico")
    if precio_base < 0:
        _abort_json(422, "precio_base no puede ser negativo")

    try:
        duracion_base_minutos = int(data.get("duracion_base_minutos"))
    except (TypeError, ValueError):
        _abort_json(422, "duracion_base_minutos debe ser entero")
    if duracion_base_minutos < 15:
        _abort_json(422, "La duración mínima es 15 minutos")
    if duracion_base_minutos % 15 != 0:
        _abort_json(422, "La duración debe ser múltiplo de 15 minutos")

    factor_tamano_raza = _validate_factor_tamano(data)
    consumo_insumos = _validate_consumo_insumos(data.get("consumo_insumos"))

    checklist_items = data.get("checklist_items") or []
    if not isinstance(checklist_items, list):
        _abort_json(422, "checklist_items debe ser una lista JSON")

    normalized_checklist = []
    for index, item in enumerate(checklist_items):
        if not isinstance(item, dict):
            _abort_json(422, f"checklist_items[{index}] debe ser un objeto JSON")
        item_nombre = (item.get("nombre") or "").strip()
        if not item_nombre:
            _abort_json(422, f"checklist_items[{index}].nombre es requerido")
        try:
            orden = int(item.get("orden", index + 1))
        except (TypeError, ValueError):
            _abort_json(422, f"checklist_items[{index}].orden debe ser entero")
        normalized_checklist.append(
            {
                "nombre": item_nombre,
                "requiere_obs": bool(item.get("requiere_obs", False)),
                "orden": orden,
                "activo": bool(item.get("activo", True)),
            }
        )

    return {
        "nombre": nombre,
        "descripcion": data.get("descripcion"),
        "precio_base": precio_base,
        "duracion_base_minutos": duracion_base_minutos,
        "permite_doble_booking": bool(data.get("permite_doble_booking", False)),
        "requiere_bloqueo_consecutivo": bool(data.get("requiere_bloqueo_consecutivo", False)),
        "factor_tamano_raza": factor_tamano_raza,
        "consumo_insumos": consumo_insumos,
        "activo": bool(data.get("activo", True)),
        "sucursal_id": data.get("sucursal_id"),
        "checklist_items": normalized_checklist,
    }


def _upsert_checklist_items(servicio_id, checklist_items):
    ChecklistItemTemplate.query.filter_by(servicio_id=servicio_id).delete()
    for item in checklist_items:
        db.session.add(
            ChecklistItemTemplate(
                servicio_id=servicio_id,
                nombre=item["nombre"],
                requiere_obs=item["requiere_obs"],
                orden=item["orden"],
                activo=item.get("activo", True),
            )
        )


@servicios_bp.get("")
def listar_servicios():
    activo = _parse_bool(request.args.get("activo"))
    query = Servicio.query
    if activo is not None:
        query = query.filter_by(activo=activo)
    servicios = query.order_by(Servicio.duracion_base_minutos.asc(), Servicio.nombre.asc()).all()
    return success({"servicios": [_service_payload(item) for item in servicios]})


@servicios_bp.get("/<int:servicio_id>")
def obtener_servicio(servicio_id):
    servicio = _service_exists(servicio_id)
    return success({"servicio": _service_payload(servicio)})


@servicios_bp.post("")
@requiere_rol("Admin")
def crear_servicio():
    data = request.get_json() or {}
    normalized = _validate_servicio_payload(data)

    servicio = Servicio(
        nombre=normalized["nombre"],
        descripcion=normalized["descripcion"],
        precio_base=normalized["precio_base"],
        duracion_base_minutos=normalized["duracion_base_minutos"],
        permite_doble_booking=normalized["permite_doble_booking"],
        requiere_bloqueo_consecutivo=normalized["requiere_bloqueo_consecutivo"],
        factor_tamano_raza=normalized["factor_tamano_raza"],
        consumo_insumos=normalized["consumo_insumos"],
        activo=normalized["activo"],
        sucursal_id=normalized["sucursal_id"],
    )
    db.session.add(servicio)
    db.session.flush()
    _upsert_checklist_items(servicio.id, normalized["checklist_items"])
    db.session.commit()
    return success({"servicio": _service_payload(servicio)}, status=201)


@servicios_bp.put("/<int:servicio_id>")
@requiere_rol("Admin")
def actualizar_servicio(servicio_id):
    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        _abort_json(404, "Servicio no encontrado")

    data = request.get_json() or {}
    normalized = _validate_servicio_payload(data)

    servicio.nombre = normalized["nombre"]
    servicio.descripcion = normalized["descripcion"]
    servicio.precio_base = normalized["precio_base"]
    servicio.duracion_base_minutos = normalized["duracion_base_minutos"]
    servicio.permite_doble_booking = normalized["permite_doble_booking"]
    servicio.requiere_bloqueo_consecutivo = normalized["requiere_bloqueo_consecutivo"]
    servicio.factor_tamano_raza = normalized["factor_tamano_raza"]
    servicio.consumo_insumos = normalized["consumo_insumos"]
    servicio.activo = normalized["activo"]
    servicio.sucursal_id = normalized["sucursal_id"]

    if "checklist_items" in data:
        _upsert_checklist_items(servicio.id, normalized["checklist_items"])

    db.session.commit()
    return success({"servicio": _service_payload(servicio)})


@servicios_bp.patch("/<int:servicio_id>/estado")
@requiere_rol("Admin")
def actualizar_estado_servicio(servicio_id):
    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        _abort_json(404, "Servicio no encontrado")

    data = request.get_json() or {}
    activo = bool(data.get("activo", True))
    forzar = _parse_bool(request.args.get("forzar")) or bool(data.get("forzar", False))

    if not activo:
        count_query = db.session.execute(
            text(
                """
                SELECT COUNT(*) AS total
                FROM citas
                WHERE servicio_id = :servicio_id
                  AND estado NOT IN ('cancelada', 'no_asistio', 'completada')
                  AND fecha_hora_inicio > NOW()
                """
            ),
            {"servicio_id": servicio_id},
        ).scalar_one()
        if count_query and not forzar:
            _abort_json(
                409,
                "El servicio tiene citas futuras pendientes",
                citas_afectadas=int(count_query),
                mensaje="¿Deseas desactivarlo de todas formas?",
            )

    servicio.activo = activo
    db.session.commit()
    estado_msg = "Servicio desactivado" if not activo else "Servicio reactivado"
    return success({"id": servicio.id, "activo": servicio.activo, "mensaje": estado_msg})


@servicios_bp.get("/<int:servicio_id>/checklist-template")
def checklist_template(servicio_id):
    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        _abort_json(404, "Servicio no encontrado")
    items = (
        ChecklistItemTemplate.query.filter_by(servicio_id=servicio_id, activo=True)
        .order_by(ChecklistItemTemplate.orden.asc(), ChecklistItemTemplate.id.asc())
        .all()
    )
    return success(
        {
            "servicio_id": servicio_id,
            "items": [
                {
                    "id": item.id,
                    "nombre": item.nombre,
                    "requiere_obs": bool(item.requiere_obs),
                    "orden": item.orden,
                }
                for item in items
            ],
        }
    )


@servicios_bp.get("/<int:servicio_id>/duracion-estimada")
def duracion_estimada(servicio_id):
    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        _abort_json(404, "Servicio no encontrado")

    mascota_id = request.args.get("mascota_id", type=int)
    hora_inicio = request.args.get("hora_inicio") or "13:00"

    if not mascota_id:
        return success(
            {
                "duracion_base": servicio.duracion_base_minutos,
                "duracion_total": servicio.duracion_base_minutos,
                "factor_tamano": 1.0,
                "categoria_tamano": None,
                "extra_temperamento": 0,
                "temperamento": None,
            }
        )

    from ..models import Mascota

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        _abort_json(404, f"Mascota ID {mascota_id} no encontrada")

    detalle = desglose_duracion(
        servicio.duracion_base_minutos,
        float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        mascota.temperamento,
        servicio.factor_tamano_raza or DEFAULT_FACTOR_TAMANO,
        hora_inicio=hora_inicio,
    )
    return success(detalle)
