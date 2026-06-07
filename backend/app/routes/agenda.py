import math
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, request

from ..extensions import db
from ..models import Groomer, Cliente, Mascota, MascotaDueno
from ..models.agenda import BloqueoCalendario, Cita, DisponibilidadGroomer, Servicio
from ..schemas.agenda_schema import (
    BloqueoSchema,
    CitaSchema,
    DisponibilidadSchema,
    ServicioSchema,
    SlotsSchema,
)
from ..services.citas_service import validar_cita_logica
from ..utils.duracion import calcular_duracion, calcular_duracion_simple
from ..utils.decorators import requiere_rol, get_current_user
from ..utils.responses import error, success


agenda_bp = Blueprint("agenda_bp", __name__, url_prefix="/api/agenda")
_SPA_HORARIO_CACHE = None


def _parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


def _parse_datetime(value):
    return datetime.fromisoformat(value)


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalize_text(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    replacements = {
        ord("\u00e1"): "a",
        ord("\u00e9"): "e",
        ord("\u00ed"): "i",
        ord("\u00f3"): "o",
        ord("\u00fa"): "u",
        ord("\u00fc"): "u",
        ord("\u00f1"): "n",
    }
    return text.translate(replacements)


def _duration_with_adjustments(base_minutes, tamano=None, temperamento=None, extra_minutos=None):
    factor = 1.0
    tamano_map = {
        "pequeno": 1.0,
        "pequena": 1.0,
        "mediano": 1.10,
        "mediana": 1.10,
        "grande": 1.15,
        "gigante": 1.30,
        "compleja": 1.30,
        "raza_compleja": 1.30,
    }
    normalized_size = _normalize_text(tamano)
    if normalized_size:
        normalized_size = normalized_size.replace(" ", "_")
        factor = tamano_map.get(normalized_size, factor)

    extra = 0
    normalized_temper = _normalize_text(temperamento)
    if normalized_temper in {"nervioso", "ansioso"}:
        extra += 10
    if normalized_temper in {"agresivo"}:
        extra += 15
    if extra_minutos:
        extra += extra_minutos

    return int(math.ceil((base_minutes * factor + extra) / 15.0) * 15)


def _overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def _daily_range(fecha):
    start = datetime.combine(fecha, datetime.min.time())
    end = datetime.combine(fecha, datetime.max.time())
    return start, end


def _time_on_date(fecha, hora_value):
    if isinstance(hora_value, datetime):
        return hora_value
    return datetime.combine(fecha, hora_value)


def _normalize_datetime(dt):
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_descanso(intervalo_descanso):
    if not isinstance(intervalo_descanso, dict):
        return None
    inicio = intervalo_descanso.get("inicio")
    fin = intervalo_descanso.get("fin")
    if not inicio or not fin:
        return None
    return inicio, fin


def _split_jornada(fecha, horario):
    jornada_inicio = _time_on_date(fecha, horario.hora_inicio)
    jornada_fin = _time_on_date(fecha, horario.hora_fin)
    descanso = _parse_descanso(horario.intervalo_descanso)
    if not descanso:
        return [(jornada_inicio, jornada_fin)]

    descanso_inicio = datetime.combine(fecha, _parse_time(descanso[0]))
    descanso_fin = datetime.combine(fecha, _parse_time(descanso[1]))
    intervals = []
    if jornada_inicio < descanso_inicio:
        intervals.append((jornada_inicio, descanso_inicio))
    if descanso_fin < jornada_fin:
        intervals.append((descanso_fin, jornada_fin))
    return intervals or [(jornada_inicio, jornada_fin)]


def _serialize_cita_agenda(cita):
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    relacion = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id, es_principal=True).first()
    cliente = relacion.cliente if relacion else None
    if not cliente and relacion:
        cliente = Cliente.query.filter_by(id=relacion.cliente_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    return {
        "id": cita.id,
        "hora_inicio": cita.fecha_hora_inicio.strftime("%H:%M"),
        "hora_fin": cita.fecha_hora_fin.strftime("%H:%M"),
        "estado": cita.estado,
        "mascota": mascota.nombre if mascota else None,
        "servicio": servicio.nombre if servicio else None,
        "cliente": f"{cliente.nombre} {cliente.apellido or ''}".strip() if cliente else None,
    }


def _serialize_bloqueo_agenda(bloqueo):
    return {
        "hora_inicio": bloqueo.fecha_inicio.strftime("%H:%M"),
        "hora_fin": bloqueo.fecha_fin.strftime("%H:%M"),
        "tipo": bloqueo.tipo_bloqueo,
    }


def _groomer_snapshot(groomer, fecha):
    day_start, day_end = _daily_range(fecha)
    citas = Cita.query.filter(
        Cita.groomer_id == groomer.id,
        Cita.estado.notin_(["cancelada", "no_asistio"]),
        Cita.fecha_hora_inicio >= day_start,
        Cita.fecha_hora_inicio < day_end,
    ).order_by(Cita.fecha_hora_inicio.asc()).all()
    bloqueos = BloqueoCalendario.query.filter(
        (BloqueoCalendario.groomer_id == groomer.id) | (BloqueoCalendario.groomer_id.is_(None)),
        BloqueoCalendario.fecha_inicio < day_end,
        BloqueoCalendario.fecha_fin > day_start,
    ).order_by(BloqueoCalendario.fecha_inicio.asc()).all()
    capacidad_max = groomer.capacidad_diaria or groomer.capacidad_simultanea or 1
    citas_usadas = len(citas)
    return {
        "citas_usadas": citas_usadas,
        "capacidad_restante": max(capacidad_max - citas_usadas, 0),
        "citas": [_serialize_cita_agenda(item) for item in citas],
        "bloqueos": [_serialize_bloqueo_agenda(item) for item in bloqueos],
    }


def _slots_disponibles_logic(groomer_id, fecha_texto, duracion_min):
    fecha = _parse_date(fecha_texto)
    groomer = Groomer.query.filter_by(id=groomer_id).first()
    if not groomer:
        return {
            "groomer_id": groomer_id,
            "fecha": fecha.isoformat(),
            "duracion_solicitada_min": duracion_min,
            "capacidad_diaria": {"max": 0, "usada": 0, "restante": 0},
            "jornada": None,
            "slots": [],
            "motivo": "Groomer no encontrado",
        }

    dia_semana = int(fecha.strftime("%w"))
    horario = DisponibilidadGroomer.query.filter_by(
        groomer_id=groomer.id,
        dia_semana=dia_semana,
        activo=True,
    ).first()
    if not horario:
        return {
            "groomer_id": groomer.id,
            "groomer_nombre": f"{groomer.nombre} {groomer.apellido or ''}".strip(),
            "fecha": fecha.isoformat(),
            "duracion_solicitada_min": duracion_min,
            "capacidad_diaria": {"max": groomer.capacidad_diaria or groomer.capacidad_simultanea or 1, "usada": 0, "restante": groomer.capacidad_diaria or groomer.capacidad_simultanea or 1},
            "jornada": None,
            "slots": [],
            "motivo": "Groomer no trabaja ese día",
        }

    jornada_inicio = _time_on_date(fecha, horario.hora_inicio)
    jornada_fin = _time_on_date(fecha, horario.hora_fin)
    intervalos = _split_jornada(fecha, horario)
    dia_start, dia_end = _daily_range(fecha)

    bloqueos = BloqueoCalendario.query.filter(
        (BloqueoCalendario.groomer_id == groomer.id) | (BloqueoCalendario.groomer_id.is_(None)),
        BloqueoCalendario.fecha_inicio < dia_end,
        BloqueoCalendario.fecha_fin > dia_start,
    ).all()

    citas = Cita.query.filter(
        Cita.groomer_id == groomer.id,
        Cita.estado.notin_(["cancelada", "no_asistio"]),
        Cita.fecha_hora_inicio >= dia_start,
        Cita.fecha_hora_inicio < dia_end,
    ).order_by(Cita.fecha_hora_inicio.asc()).all()

    capacidad_max = groomer.capacidad_diaria or groomer.capacidad_simultanea or 1
    capacidad_restante = capacidad_max - len(citas)

    def _normalize(dt):
        if isinstance(dt, datetime) and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    slots = []
    for inicio_intervalo, fin_intervalo in intervalos:
        cursor = _normalize(inicio_intervalo)
        fin_intervalo = _normalize(fin_intervalo)
        while cursor < fin_intervalo:
            slot_fin = _normalize(cursor + timedelta(minutes=duracion_min))
            bloqueado = any(
                _normalize(bloqueo.fecha_inicio) < slot_fin and _normalize(bloqueo.fecha_fin) > cursor
                for bloqueo in bloqueos
            )
            ocupado = any(
                _normalize(cita.fecha_hora_inicio) < slot_fin and _normalize(cita.fecha_hora_fin) > cursor
                for cita in citas
            )
            espacio_libre = slot_fin <= fin_intervalo
            sin_capacidad = capacidad_restante <= 0
            disponible = not bloqueado and not ocupado and espacio_libre and not sin_capacidad
            motivo = None
            if not disponible:
                if bloqueado:
                    motivo = "Bloqueado"
                elif ocupado:
                    motivo = "Ocupado"
                elif not espacio_libre:
                    motivo = "Sin espacio para duración solicitada"
                elif sin_capacidad:
                    motivo = "Capacidad máxima alcanzada"
            slots.append(
                {
                    "hora_inicio": cursor.strftime("%H:%M"),
                    "hora_fin": slot_fin.strftime("%H:%M"),
                    "disponible": disponible,
                    "motivo": motivo,
                }
            )
            cursor += timedelta(minutes=30)

    return {
        "groomer_id": groomer.id,
        "groomer_nombre": f"{groomer.nombre} {groomer.apellido or ''}".strip(),
        "fecha": fecha.isoformat(),
        "duracion_solicitada_min": duracion_min,
        "capacidad_diaria": {
            "max": capacidad_max,
            "usada": len(citas),
            "restante": max(capacidad_restante, 0),
        },
        "jornada": {
            "inicio": jornada_inicio.strftime("%H:%M"),
            "fin": jornada_fin.strftime("%H:%M"),
        },
        "slots": slots,
    }


def _fechas_disponibles_logic(servicio_id, mascota_id, groomer_id=None, dias=30):
    servicio = Servicio.query.filter_by(id=servicio_id, activo=True).first()
    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not servicio:
        return None, error("Servicio no encontrado", status=404)
    if not mascota:
        return None, error("Mascota no encontrada", status=404)

    duracion_ajustada = calcular_duracion_simple(
        servicio.duracion_base_minutos,
        float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        mascota.temperamento,
        servicio.factor_tamano_raza,
    )

    if groomer_id:
        groomers = [Groomer.query.filter_by(id=groomer_id, estado_activo=True).first()]
    else:
        groomers = Groomer.query.filter_by(estado_activo=True).order_by(Groomer.nombre.asc(), Groomer.apellido.asc()).all()

    groomers = [item for item in groomers if item]
    if not groomers:
        return {"fechas_disponibles": [], "duracion_ajustada": duracion_ajustada}, None

    fechas_disponibles = []
    hoy = datetime.now(timezone.utc).date()
    for offset in range(dias):
        fecha = hoy + timedelta(days=offset)
        disponible = False
        for groomer in groomers:
            slots = _slots_disponibles_logic(groomer.id, fecha.isoformat(), duracion_ajustada).get("slots", [])
            if any(slot.get("disponible") for slot in slots):
                disponible = True
                break
        if disponible:
            fechas_disponibles.append(fecha.isoformat())

    return {"fechas_disponibles": fechas_disponibles, "duracion_ajustada": duracion_ajustada}, None


def _default_spa_schedule():
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


def _serialize_disponibilidad(item):
    return {
        "id": item.id,
        "dia_semana": item.dia_semana,
        "hora_inicio": item.hora_inicio.strftime("%H:%M"),
        "hora_fin": item.hora_fin.strftime("%H:%M"),
        "buffer_minutos": item.buffer_minutos,
        "activo": item.activo,
        "intervalo_descanso": item.intervalo_descanso,
    }


def _serialize_bloqueo(item):
    return {
        "id": item.id,
        "groomer_id": item.groomer_id,
        "fecha_inicio": item.fecha_inicio.isoformat(),
        "fecha_fin": item.fecha_fin.isoformat(),
        "tipo_bloqueo": item.tipo_bloqueo,
        "descripcion": item.descripcion,
    }


def _serialize_servicio(item):
    return {
        "id": item.id,
        "nombre": item.nombre,
        "descripcion": item.descripcion,
        "precio_base": float(item.precio_base),
        "duracion_base_minutos": item.duracion_base_minutos,
        "permite_doble_booking": item.permite_doble_booking,
        "requiere_bloqueo_consecutivo": item.requiere_bloqueo_consecutivo,
        "factor_tamano_raza": item.factor_tamano_raza or {},
        "consumo_insumos": item.consumo_insumos or [],
        "activo": item.activo,
    }


@agenda_bp.get("/servicios")
@requiere_rol("Admin", "Recepcion", "Groomer", "Cliente")
def list_servicios():
    servicios = Servicio.query.filter_by(activo=True).order_by(Servicio.nombre.asc()).all()
    return success({"servicios": [_serialize_servicio(item) for item in servicios]})


@agenda_bp.post("/servicios")
@requiere_rol("Admin")
def create_servicio():
    data = ServicioSchema().load(request.get_json() or {})
    servicio = Servicio(
        nombre=data["nombre"],
        descripcion=data.get("descripcion"),
        precio_base=data["precio_base"],
        duracion_base_minutos=data["duracion_base_minutos"],
        activo=data.get("activo", True),
    )
    db.session.add(servicio)
    db.session.commit()
    return success({"id": servicio.id}, status=201)


@agenda_bp.patch("/servicios/<int:servicio_id>")
@requiere_rol("Admin")
def update_servicio(servicio_id):
    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        return error("Servicio no encontrado", status=404)
    data = request.get_json() or {}
    for field in ("nombre", "descripcion", "precio_base", "duracion_base_minutos", "permite_doble_booking", "requiere_bloqueo_consecutivo", "factor_tamano_raza", "consumo_insumos"):
        if field in data:
            setattr(servicio, field, data[field])
    db.session.commit()
    return success({"servicio": _serialize_servicio(servicio)})


@agenda_bp.patch("/servicios/<int:servicio_id>/estado")
@requiere_rol("Admin")
def update_servicio_estado(servicio_id):
    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        return error("Servicio no encontrado", status=404)
    data = request.get_json() or {}
    servicio.activo = bool(data.get("activo", True))
    db.session.commit()
    return success({"servicio": _serialize_servicio(servicio)})


@agenda_bp.get("/horario-spa")
@requiere_rol("Admin", "Recepcion")
def get_horario_spa():
    global _SPA_HORARIO_CACHE
    if _SPA_HORARIO_CACHE is None:
        _SPA_HORARIO_CACHE = _default_spa_schedule()
    return success({"dias": _SPA_HORARIO_CACHE})


@agenda_bp.put("/horario-spa")
@requiere_rol("Admin")
def update_horario_spa():
    global _SPA_HORARIO_CACHE
    data = request.get_json() or {}
    dias = data.get("dias") or []
    normalized = []
    for index in range(7):
        source = next((item for item in dias if int(item.get("dia_semana", -1)) == index), None)
        normalized.append(
            {
                "dia_semana": index,
                "hora_inicio": (source or {}).get("hora_inicio", "09:00"),
                "hora_fin": (source or {}).get("hora_fin", "18:00"),
                "activo": bool((source or {}).get("activo", True)),
                "buffer_minutos": int((source or {}).get("buffer_minutos", 15) or 15),
                "intervalo_descanso": (source or {}).get("intervalo_descanso") or {"inicio": "13:00", "fin": "14:00"},
            }
        )
    _SPA_HORARIO_CACHE = normalized
    return success({"dias": _SPA_HORARIO_CACHE})


@agenda_bp.get("/disponibilidad-groomers")
@requiere_rol("Admin", "Recepcion")
def get_disponibilidad_groomers():
    groomers = Groomer.query.order_by(Groomer.nombre.asc(), Groomer.apellido.asc()).all()
    payload = []
    for groomer in groomers:
        items = DisponibilidadGroomer.query.filter_by(groomer_id=groomer.id, activo=True).all()
        payload.append(
            {
                "id": groomer.id,
                "nombre": groomer.nombre,
                "apellido": groomer.apellido,
                "disponibilidad": [_serialize_disponibilidad(item) for item in items],
            }
        )
    return success({"groomers": payload})


@agenda_bp.put("/disponibilidad-groomers/<int:groomer_id>")
@requiere_rol("Admin", "Recepcion")
def update_disponibilidad_groomer(groomer_id):
    data = request.get_json() or {}
    dias = data.get("dias") or []
    DisponibilidadGroomer.query.filter_by(groomer_id=groomer_id).delete()
    for item in dias:
        if item is None:
            continue
        hora_inicio = _parse_time(item.get("hora_inicio", "09:00"))
        hora_fin = _parse_time(item.get("hora_fin", "18:00"))
        db.session.add(
            DisponibilidadGroomer(
                groomer_id=groomer_id,
                dia_semana=int(item.get("dia_semana", 0)),
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                buffer_minutos=int(item.get("buffer_minutos", 15) or 15),
                activo=bool(item.get("activo", True)),
                intervalo_descanso=item.get("intervalo_descanso"),
            )
        )
    db.session.commit()
    return success({"message": "Disponibilidad actualizada"})


@agenda_bp.get("/horarios")
@requiere_rol("Admin", "Recepcion")
def list_horarios():
    groomer_id = request.args.get("groomer_id", type=int)
    if not groomer_id:
        return error("groomer_id requerido", status=400)
    horarios = DisponibilidadGroomer.query.filter_by(groomer_id=groomer_id, activo=True).all()
    payload = [
        {
            "id": item.id,
            "dia_semana": item.dia_semana,
            "hora_inicio": item.hora_inicio.strftime("%H:%M"),
            "hora_fin": item.hora_fin.strftime("%H:%M"),
            "buffer_minutos": item.buffer_minutos,
        }
        for item in horarios
    ]
    return success({"horarios": payload})


@agenda_bp.post("/horarios")
@requiere_rol("Admin", "Recepcion")
def upsert_horario():
    data = DisponibilidadSchema().load(request.get_json() or {})
    horario = DisponibilidadGroomer.query.filter_by(
        groomer_id=data["groomer_id"],
        dia_semana=data["dia_semana"],
    ).first()

    if not horario:
        horario = DisponibilidadGroomer(
            groomer_id=data["groomer_id"],
            dia_semana=data["dia_semana"],
        )
        db.session.add(horario)

    horario.hora_inicio = _parse_time(data["hora_inicio"])
    horario.hora_fin = _parse_time(data["hora_fin"])
    horario.buffer_minutos = data.get("buffer_minutos") or 15
    horario.activo = True
    db.session.commit()
    return success({"message": "Horario actualizado"})


@agenda_bp.post("/bloqueos")
@requiere_rol("Admin", "Recepcion")
def create_bloqueo():
    data = BloqueoSchema().load(request.get_json() or {})
    bloqueo = BloqueoCalendario(
        groomer_id=data.get("groomer_id"),
        fecha_inicio=_parse_datetime(data["fecha_inicio"]),
        fecha_fin=_parse_datetime(data["fecha_fin"]),
        tipo_bloqueo=data["tipo_bloqueo"],
        descripcion=data.get("descripcion"),
    )
    db.session.add(bloqueo)
    db.session.commit()
    return success({"id": bloqueo.id}, status=201)


@agenda_bp.get("/bloqueos")
@requiere_rol("Admin", "Recepcion")
def list_bloqueos():
    query = BloqueoCalendario.query.order_by(BloqueoCalendario.fecha_inicio.desc())
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    if fecha_inicio and fecha_fin:
        inicio = _parse_datetime(f"{fecha_inicio}T00:00:00")
        fin = _parse_datetime(f"{fecha_fin}T23:59:59")
        query = query.filter(BloqueoCalendario.fecha_inicio <= fin, BloqueoCalendario.fecha_fin >= inicio)
    bloqueos = query.all()
    return success({"bloqueos": [_serialize_bloqueo(item) for item in bloqueos]})


@agenda_bp.delete("/bloqueos/<int:bloqueo_id>")
@requiere_rol("Admin", "Recepcion")
def delete_bloqueo(bloqueo_id):
    bloqueo = BloqueoCalendario.query.filter_by(id=bloqueo_id).first()
    if not bloqueo:
        return error("Bloqueo no encontrado", status=404)
    db.session.delete(bloqueo)
    db.session.commit()
    return success({"message": "Bloqueo eliminado"})


@agenda_bp.get("/slots-disponibles")
def slots_disponibles():
    groomer_id = request.args.get("groomer_id", type=int)
    fecha = request.args.get("fecha")
    duracion_min = request.args.get("duracion_min", type=int)

    if not groomer_id or not fecha or not duracion_min:
        return error("groomer_id, fecha y duracion_min son requeridos", status=400)

    payload = _slots_disponibles_logic(groomer_id, fecha, duracion_min)
    return success(payload)


@agenda_bp.get("/fechas-disponibles")
def fechas_disponibles():
    servicio_id = request.args.get("servicio_id", type=int)
    mascota_id = request.args.get("mascota_id", type=int)
    groomer_id = request.args.get("groomer_id", type=int)
    if not servicio_id or not mascota_id:
        return error("servicio_id y mascota_id son requeridos", status=400)

    payload, err = _fechas_disponibles_logic(servicio_id, mascota_id, groomer_id=groomer_id)
    if err:
        return err
    return success(payload)


def _week_dates(fecha_base):
    lunes = fecha_base - timedelta(days=fecha_base.weekday())
    return [lunes + timedelta(days=index) for index in range(7)]


def _calendar_payload(groomer, fechas):
    dias = {}
    for fecha in fechas:
        dias[fecha.isoformat()] = _groomer_snapshot(groomer, fecha)
    return {
        "groomer_id": groomer.id,
        "groomer_nombre": f"{groomer.nombre} {groomer.apellido or ''}".strip(),
        "capacidad_simultanea": groomer.capacidad_simultanea or 1,
        "dias": dias,
    }


@agenda_bp.get("/semana")
@requiere_rol("Admin", "Recepcion")
def get_semana():
    fecha_param = request.args.get("fecha")
    fecha_base = _parse_date(fecha_param) if fecha_param else datetime.today().date()
    fechas = _week_dates(fecha_base)
    groomers = Groomer.query.filter_by(estado_activo=True).order_by(Groomer.nombre.asc(), Groomer.apellido.asc()).all()
    payload = [_calendar_payload(groomer, fechas) for groomer in groomers]
    return success(payload)


@agenda_bp.get("/dia")
@requiere_rol("Admin", "Recepcion", "Groomer")
def get_dia():
    fecha_param = request.args.get("fecha")
    if not fecha_param:
        return error("fecha requerida", status=400)

    fecha_base = _parse_date(fecha_param)
    groomer_id = request.args.get("groomer_id", type=int)
    try:
        usuario, rol = get_current_user()
    except RuntimeError:
        usuario, rol = None, None
    if rol == "Groomer":
        groomer_id = usuario.perfil_groomer.id if usuario and usuario.perfil_groomer else None
        if request.args.get("groomer_id", type=int) and request.args.get("groomer_id", type=int) != groomer_id:
            return error("Acceso denegado", status=403)

    groomers = Groomer.query.filter_by(estado_activo=True)
    if groomer_id:
        groomers = groomers.filter_by(id=groomer_id)
    groomers = groomers.order_by(Groomer.nombre.asc(), Groomer.apellido.asc()).all()
    payload = [_calendar_payload(groomer, [fecha_base]) for groomer in groomers]
    return success(payload)


@agenda_bp.post("/slots")
@requiere_rol("Admin", "Recepcion", "Cliente")
def get_slots():
    data = SlotsSchema().load(request.get_json() or {})
    servicio = Servicio.query.filter_by(id=data["servicio_id"]).first()
    if not servicio:
        return error("Servicio no encontrado", status=404)

    duracion = data.get("duracion_min") or _duration_with_adjustments(
        servicio.duracion_base_minutos,
        tamano=data.get("tamano"),
        temperamento=data.get("temperamento"),
        extra_minutos=data.get("extra_minutos"),
    )
    payload = _slots_disponibles_logic(data["groomer_id"], data["fecha"], duracion)
    return success(payload)


@agenda_bp.post("/validar-cita")
def validar_cita_endpoint():
    data = request.get_json() or {}
    resultado = validar_cita_logica(
        groomer_id=data.get("groomer_id"),
        servicio_id=data.get("servicio_id"),
        mascota_id=data.get("mascota_id"),
        fecha_hora_inicio=data.get("fecha_hora_inicio"),
    )
    if not resultado["valido"]:
        return resultado, 409
    return success(resultado)


@agenda_bp.post("/citas")
@requiere_rol("Admin", "Recepcion", "Cliente")
def create_cita():
    data = CitaSchema().load(request.get_json() or {})
    resultado = validar_cita_logica(
        groomer_id=data["groomer_id"],
        servicio_id=data["servicio_id"],
        mascota_id=data["mascota_id"],
        fecha_hora_inicio=data["fecha_hora_inicio"],
    )
    if not resultado["valido"]:
        return error(
            "No se puede crear la cita",
            status=409,
            details={
                "errores": resultado["errores"],
                "duracion_ajustada_min": resultado["duracion_ajustada_min"],
            },
        )

    inicio = _parse_datetime(resultado["fecha_hora_inicio"])
    fin = _parse_datetime(resultado["fecha_hora_fin"])

    cita = Cita(
        mascota_id=data["mascota_id"],
        groomer_id=data["groomer_id"],
        servicio_id=data["servicio_id"],
        fecha_hora_inicio=inicio,
        fecha_hora_fin=fin,
        duracion_estimada=resultado["duracion_ajustada_min"],
        precio_estimado=resultado["precio_estimado"],
        notas=data.get("notas"),
    )
    # If a Cliente requests the cita via frontend, mark it as pendiente for review
    usuario, rol = get_current_user()
    if rol == "Cliente":
        cita.estado = "pendiente"
        if usuario:
            cita.creado_por = usuario.id
    db.session.add(cita)
    db.session.commit()
    return success({"id": cita.id}, status=201)
