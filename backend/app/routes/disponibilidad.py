from datetime import datetime

from flask import Blueprint, request
from marshmallow import ValidationError
from sqlalchemy import or_

from ..extensions import db
from ..models import Groomer
from ..models.agenda import BloqueoCalendario, Cita, DisponibilidadGroomer
from ..routes import agenda as agenda_routes
from ..schemas.agenda_schema import BloqueoSchema
from ..utils.decorators import get_current_user
from ..utils.responses import error, success
from ..utils.roles import require_role


disponibilidad_bp = Blueprint("disponibilidad_bp", __name__)


def _parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


def _parse_datetime(value):
    return datetime.fromisoformat(value)


def _default_general_schedule():
    return [
        {
            "dia_semana": index,
            "hora_inicio": "09:00",
            "hora_fin": "18:00",
            "activo": True,
            "buffer_minutos": 15,
            "intervalo_descanso": {"inicio": "13:00", "fin": "14:00"},
        }
        for index in range(7)
    ]


def _normalize_day(item, index=None, default_active=True):
    dia_semana = index if index is not None else int(item.get("dia_semana", 0))
    hora_inicio = item.get("hora_inicio", "09:00")
    hora_fin = item.get("hora_fin", "18:00")
    buffer_minutos = int(item.get("buffer_minutos", 15) or 15)
    intervalo_descanso = item.get("intervalo_descanso") or {"inicio": "13:00", "fin": "14:00"}
    activo = bool(item.get("activo", default_active))

    if activo and hora_inicio >= hora_fin:
        raise ValueError("horas_invalidas")

    return {
        "dia_semana": dia_semana,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "buffer_minutos": buffer_minutos,
        "intervalo_descanso": intervalo_descanso,
        "activo": activo,
    }


def _serialize_groomer_schedule(item):
    return {
        "id": item.id,
        "dia_semana": item.dia_semana,
        "hora_inicio": item.hora_inicio.strftime("%H:%M"),
        "hora_fin": item.hora_fin.strftime("%H:%M"),
        "buffer_minutos": item.buffer_minutos,
        "activo": item.activo,
        "intervalo_descanso": item.intervalo_descanso,
    }


def _serialize_block(item):
    return {
        "id": item.id,
        "groomer_id": item.groomer_id,
        "fecha_inicio": item.fecha_inicio.isoformat(),
        "fecha_fin": item.fecha_fin.isoformat(),
        "tipo_bloqueo": item.tipo_bloqueo,
        "descripcion": item.descripcion,
        "creado_por": item.creado_por,
    }


def _validate_date_range(fecha_inicio, fecha_fin):
    if fecha_fin <= fecha_inicio:
        raise ValueError("horas_invalidas")


def _find_block_conflicts(groomer_id, inicio, fin):
    bloqueos_query = BloqueoCalendario.query.filter(
        BloqueoCalendario.fecha_inicio < fin,
        BloqueoCalendario.fecha_fin > inicio,
    )
    if groomer_id is not None:
        bloqueos_query = bloqueos_query.filter(
            or_(BloqueoCalendario.groomer_id.is_(None), BloqueoCalendario.groomer_id == groomer_id)
        )
    bloqueos = bloqueos_query.order_by(BloqueoCalendario.fecha_inicio.asc()).all()

    citas_query = Cita.query.filter(
        Cita.fecha_hora_inicio < fin,
        Cita.fecha_hora_fin > inicio,
        Cita.estado.in_(["agendada", "confirmada", "en_progreso"]),
    )
    if groomer_id is not None:
        citas_query = citas_query.filter(Cita.groomer_id == groomer_id)
    citas = citas_query.order_by(Cita.fecha_hora_inicio.asc()).all()

    return bloqueos, citas


@disponibilidad_bp.get("/api/disponibilidad/horario-general")
@require_role("Admin", "Recepcion")
def get_horario_general():
    if agenda_routes._SPA_HORARIO_CACHE is None:
        agenda_routes._SPA_HORARIO_CACHE = _default_general_schedule()
    return success({"dias": agenda_routes._SPA_HORARIO_CACHE})


@disponibilidad_bp.put("/api/disponibilidad/horario-general")
@require_role("Admin", "Recepcion")
def update_horario_general():
    data = request.get_json() or {}
    dias = data.get("dias") or []
    normalized = []

    try:
        for index in range(7):
            source = next((item for item in dias if int(item.get("dia_semana", -1)) == index), None) or {}
            normalized.append(_normalize_day(source, index=index, default_active=True))
    except (TypeError, ValueError):
        return error("Los horarios del spa tienen horas invalidas", status=400)

    agenda_routes._SPA_HORARIO_CACHE = normalized
    return success({"dias": agenda_routes._SPA_HORARIO_CACHE})


@disponibilidad_bp.get("/api/disponibilidad/groomers")
@require_role("Admin", "Recepcion")
def get_groomers():
    groomers = Groomer.query.order_by(Groomer.nombre.asc(), Groomer.apellido.asc()).all()
    payload = []
    for groomer in groomers:
        availability = DisponibilidadGroomer.query.filter_by(groomer_id=groomer.id).order_by(
            DisponibilidadGroomer.dia_semana.asc()
        ).all()
        payload.append(
            {
                "id": groomer.id,
                "nombre": groomer.nombre,
                "apellido": groomer.apellido,
                "estado_activo": groomer.estado_activo,
                "capacidad_diaria": groomer.capacidad_diaria,
                "capacidad_simultanea": groomer.capacidad_simultanea,
                "disponibilidad": [_serialize_groomer_schedule(item) for item in availability],
            }
        )
    return success({"groomers": payload})


@disponibilidad_bp.put("/api/disponibilidad/groomers/<int:groomer_id>")
@require_role("Admin", "Recepcion")
def update_groomer(groomer_id):
    groomer = Groomer.query.filter_by(id=groomer_id).first()
    if not groomer:
        return error("Groomer no encontrado", status=404)

    data = request.get_json() or {}
    dias = data.get("dias") or []

    try:
        normalized = []
        for index in range(7):
            source = next((item for item in dias if int(item.get("dia_semana", -1)) == index), None) or {}
            normalized.append(_normalize_day(source, index=index, default_active=True))
    except (TypeError, ValueError):
        return error("La disponibilidad del groomer tiene horas invalidas", status=400)

    DisponibilidadGroomer.query.filter_by(groomer_id=groomer_id).delete()
    for item in normalized:
        db.session.add(
            DisponibilidadGroomer(
                groomer_id=groomer_id,
                dia_semana=item["dia_semana"],
                hora_inicio=_parse_time(item["hora_inicio"]),
                hora_fin=_parse_time(item["hora_fin"]),
                buffer_minutos=item["buffer_minutos"],
                activo=item["activo"],
                intervalo_descanso=item["intervalo_descanso"],
            )
        )

    db.session.commit()
    return success({"message": "Disponibilidad actualizada", "groomer_id": groomer.id})


@disponibilidad_bp.get("/api/bloqueos")
@require_role("Admin", "Recepcion")
def list_bloqueos():
    query = BloqueoCalendario.query.order_by(BloqueoCalendario.fecha_inicio.desc())
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    if fecha_inicio and fecha_fin:
        inicio = _parse_datetime(f"{fecha_inicio}T00:00:00")
        fin = _parse_datetime(f"{fecha_fin}T23:59:59")
        query = query.filter(BloqueoCalendario.fecha_inicio <= fin, BloqueoCalendario.fecha_fin >= inicio)

    bloqueos = query.all()
    return success({"bloqueos": [_serialize_block(item) for item in bloqueos]})


@disponibilidad_bp.post("/api/bloqueos")
@require_role("Admin", "Recepcion")
def create_bloqueo():
    try:
        data = BloqueoSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos de bloqueo invalidos", status=400, details=exc.messages)

    try:
        inicio = _parse_datetime(data["fecha_inicio"])
        fin = _parse_datetime(data["fecha_fin"])
        _validate_date_range(inicio, fin)
    except ValueError:
        return error("Las fechas del bloqueo no son validas", status=400)

    groomer_id = data.get("groomer_id")
    forced = str(request.args.get("forzar", "")).lower() in {"1", "true", "yes", "si"}
    bloqueos_conflictivos, citas_conflictivas = _find_block_conflicts(groomer_id, inicio, fin)

    if (bloqueos_conflictivos or citas_conflictivas) and not forced:
        details = {
            "bloqueos_conflictivos": len(bloqueos_conflictivos),
            "citas_conflictivas": len(citas_conflictivas),
        }
        return error(
            "El bloqueo coincide con citas o bloqueos existentes",
            status=409,
            details=details,
        )

    usuario, _rol = get_current_user()
    bloqueo = BloqueoCalendario(
        groomer_id=groomer_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
        tipo_bloqueo=data["tipo_bloqueo"],
        descripcion=data.get("descripcion"),
        creado_por=usuario.id if usuario else None,
    )
    db.session.add(bloqueo)
    db.session.commit()

    return success({"id": bloqueo.id, "forzado": forced}, status=201)


@disponibilidad_bp.delete("/api/bloqueos/<int:bloqueo_id>")
@require_role("Admin", "Recepcion")
def delete_bloqueo(bloqueo_id):
    bloqueo = BloqueoCalendario.query.filter_by(id=bloqueo_id).first()
    if not bloqueo:
        return error("Bloqueo no encontrado", status=404)

    db.session.delete(bloqueo)
    db.session.commit()
    return success({"message": "Bloqueo eliminado"})
