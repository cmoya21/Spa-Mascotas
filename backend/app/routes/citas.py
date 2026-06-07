from datetime import datetime, timedelta, timezone

from flask import Blueprint, request
from marshmallow import ValidationError

from ..extensions import db
from ..models import Cita, Cliente, MascotaDueno, Notificacion, AuditLog, Groomer, Servicio, Mascota
from ..schemas.agenda_schema import CitaSchema
from ..services.citas_service import validar_cita_logica
from ..utils.duracion import calcular_duracion_simple
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.crear_notificacion import crear_notificacion
from ..utils.plantillas_notif import (
    mensaje_cita_confirmada,
    mensaje_listo_recoger,
    mensaje_recordatorio_24h,
    mensaje_recordatorio_2h,
    mensaje_solicitud_revision,
)
from ..utils.responses import error, success


citas_bp = Blueprint("citas_bp", __name__, url_prefix="/api")


@citas_bp.post("/citas")
@requiere_rol("Admin", "Recepcion")
def crear_cita():
    try:
        data = CitaSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    resultado = validar_cita_logica(
        groomer_id=data["groomer_id"],
        servicio_id=data["servicio_id"],
        mascota_id=data["mascota_id"],
        fecha_hora_inicio=data["fecha_hora_inicio"],
    )
    if not resultado["valido"]:
        return error(
            "No se puede crear la cita",
            status=422,
        )

    usuario, _rol = get_current_user()
    cita = Cita(
        mascota_id=data["mascota_id"],
        groomer_id=data["groomer_id"],
        servicio_id=data["servicio_id"],
        fecha_hora_inicio=datetime.fromisoformat(resultado["fecha_hora_inicio"]),
        fecha_hora_fin=datetime.fromisoformat(resultado["fecha_hora_fin"]),
        duracion_estimada=resultado["duracion_ajustada_min"],
        precio_estimado=resultado["precio_estimado"],
        notas=data.get("notas"),
        creado_por=usuario.id if usuario else None,
    )
    db.session.add(cita)
    db.session.flush()

    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    fecha = cita.fecha_hora_inicio.strftime("%d/%m/%Y") if cita.fecha_hora_inicio else ""
    hora = cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else ""

    noti = _build_notificacion(
        cita,
        "confirmacion",
        mensaje_cita_confirmada(
            mascota.nombre if mascota else "Tu mascota",
            servicio.nombre if servicio else "servicio",
            fecha,
            hora,
        ),
    )
    if noti:
        db.session.add(noti)

    try:
        datos_despues = {
            "id": cita.id,
            "mascota_id": cita.mascota_id,
            "groomer_id": cita.groomer_id,
            "servicio_id": cita.servicio_id,
            "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
            "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
            "duracion_estimada": cita.duracion_estimada,
            "precio_estimado": float(cita.precio_estimado) if cita.precio_estimado is not None else None,
            "estado": cita.estado,
        }
    except Exception:
        datos_despues = None

    audit = AuditLog(
        tabla="citas",
        operacion="INSERT",
        registro_id=cita.id,
        datos_despues=datos_despues,
        usuario_id=usuario.id if usuario else None,
    )
    db.session.add(audit)

    db.session.commit()
    return success({"id": cita.id}, status=201)


def _build_notificacion(cita, tipo_evento, mensaje, delay_minutes=0):
    relacion = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id).first()
    if not relacion:
        return None
    cliente = Cliente.query.filter_by(id=relacion.cliente_id).first()
    if not cliente:
        return None

    existing = Notificacion.query.filter_by(
        cita_id=cita.id,
        cliente_id=cliente.id,
        tipo_evento=tipo_evento,
    ).first()
    if existing:
        return None

    return crear_notificacion(
        cita_id=cita.id,
        cliente=cliente,
        tipo_evento=tipo_evento,
        mensaje=mensaje,
        delay_minutes=delay_minutes,
    )


def _resolve_cliente_actual():
    usuario, rol = get_current_user()
    if not usuario or rol != "Cliente":
        return None
    cliente = usuario.perfil_cliente or Cliente.query.filter_by(usuario_id=usuario.id).first()
    return cliente


def _franja_a_hora(franja):
    mapa = {
        "manana": "09:00",
        "tarde": "14:00",
        "cualquiera": "09:00",
    }
    return mapa.get((franja or "cualquiera").strip().lower(), "09:00")


def _fecha_hora_desde_franja(fecha_preferida, franja):
    hora = _franja_a_hora(franja)
    return datetime.fromisoformat(f"{fecha_preferida}T{hora}:00")


def _aware_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _cita_payload_solicitud(cita):
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    groomer = Groomer.query.filter_by(id=cita.groomer_id).first() if cita.groomer_id else None
    return {
        "cita_id": cita.id,
        "estado": cita.estado,
        "mensaje": "Tu solicitud fue enviada. Recibirás confirmación en breve.",
        "fecha": cita.fecha_hora_inicio.date().isoformat() if cita.fecha_hora_inicio else None,
        "hora": cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else None,
        "servicio": servicio.nombre if servicio else None,
        "duracion_estimada": cita.duracion_estimada,
        "groomer": f"{groomer.nombre} {groomer.apellido or ''}".strip() if groomer else "Por asignar",
    }


def _buscar_groomer_disponible(fecha_preferida, duracion_min, groomer_id=None):
    from .agenda import _slots_disponibles_logic

    candidatos = []
    if groomer_id:
        groomer = Groomer.query.filter_by(id=groomer_id, estado_activo=True).first()
        if groomer:
            candidatos = [groomer]
    else:
        candidatos = (
            Groomer.query.filter_by(estado_activo=True)
            .order_by(Groomer.nombre.asc(), Groomer.apellido.asc())
            .all()
        )

    if not candidatos:
        return None

    for groomer in candidatos:
        slots = _slots_disponibles_logic(groomer.id, fecha_preferida, duracion_min).get("slots", [])
        if any(slot.get("disponible") for slot in slots):
            return groomer
    return candidatos[0] if candidatos else None


def _crear_solicitud_cita_cliente(data):
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    try:
        mascota_id = int(data.get("mascota_id"))
        servicio_id = int(data.get("servicio_id"))
    except (TypeError, ValueError):
        return error("mascota_id y servicio_id son requeridos", status=400)

    mascota_rel = MascotaDueno.query.filter_by(mascota_id=mascota_id, cliente_id=cliente.id).first()
    if not mascota_rel:
        return error("Mascota no encontrada", status=404)

    servicio = Servicio.query.filter_by(id=servicio_id, activo=True).first()
    if not servicio:
        return error("Servicio no encontrado", status=404)

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return error("Mascota no encontrada", status=404)

    fecha_preferida = data.get("fecha_preferida")
    franja = (data.get("franja") or "cualquiera").strip().lower()
    if franja not in {"manana", "tarde", "cualquiera"}:
        return error("franja invalida", status=422)
    if not fecha_preferida:
        return error("fecha_preferida requerido", status=400)

    try:
        fecha_dt = datetime.strptime(str(fecha_preferida), "%Y-%m-%d").date()
    except ValueError:
        return error("fecha_preferida invalida", status=422)
    if fecha_dt < datetime.now(timezone.utc).date():
        return error("No puedes agendar en el pasado", status=422)

    duracion_estimada = calcular_duracion_simple(
        servicio.duracion_base_minutos,
        float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        mascota.temperamento,
        servicio.factor_tamano_raza,
    )
    fecha_hora_inicio = _fecha_hora_desde_franja(fecha_preferida, franja)

    groomer_id = data.get("groomer_id")
    groomer = None
    if groomer_id not in (None, "", 0, "0"):
        try:
            groomer_id = int(groomer_id)
        except (TypeError, ValueError):
            return error("groomer_id invalido", status=422)
        groomer = Groomer.query.filter_by(id=groomer_id, estado_activo=True).first()
        if not groomer:
            return error("El groomer seleccionado no esta activo", status=422)
    else:
        groomer = _buscar_groomer_disponible(fecha_preferida, duracion_estimada)
        groomer_id = groomer.id if groomer else None

    resultado = validar_cita_logica(
        groomer_id=groomer_id or (groomer.id if groomer else None),
        servicio_id=servicio_id,
        mascota_id=mascota_id,
        fecha_hora_inicio=fecha_hora_inicio.isoformat(),
    ) if groomer_id else {"valido": True, "errores": [], "duracion_ajustada_min": duracion_estimada, "fecha_hora_inicio": fecha_hora_inicio.isoformat(), "fecha_hora_fin": (fecha_hora_inicio + timedelta(minutes=duracion_estimada)).isoformat(), "precio_estimado": float(servicio.precio_base or 0)}

    if groomer_id and not resultado["valido"]:
        return error(
            "No se puede crear la solicitud",
            status=422,
            details={
                "errores": resultado["errores"],
                "duracion_ajustada_min": resultado["duracion_ajustada_min"],
            },
        )

    usuario, _rol = get_current_user()
    cita = Cita(
        mascota_id=mascota_id,
        groomer_id=groomer_id,
        servicio_id=servicio_id,
        fecha_hora_inicio=datetime.fromisoformat(resultado["fecha_hora_inicio"]),
        fecha_hora_fin=datetime.fromisoformat(resultado["fecha_hora_fin"]),
        duracion_estimada=resultado["duracion_ajustada_min"],
        precio_estimado=resultado["precio_estimado"],
        notas=data.get("notas") or data.get("motivo"),
        estado="agendada",
        creado_por=usuario.id if usuario else None,
    )
    db.session.add(cita)
    db.session.flush()

    notificacion = _build_notificacion(
        cita,
        "solicitud_revision",
        mensaje_solicitud_revision(
            mascota.nombre if mascota else "tu mascota",
            servicio.nombre if servicio else "servicio",
            cita.fecha_hora_inicio.strftime("%d/%m/%Y") if cita.fecha_hora_inicio else "",
            cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else "",
        ),
    )
    if notificacion:
        db.session.add(notificacion)

    db.session.commit()
    return success(_cita_payload_solicitud(cita), status=201)


@citas_bp.patch("/citas/<int:cita_id>/estado")
@requiere_rol("Admin", "Recepcion", "Groomer")
def actualizar_estado_cita(cita_id):
    data = request.get_json() or {}
    nuevo_estado = data.get("estado")
    if not nuevo_estado:
        return error("estado requerido", status=400)

    estados_validos = {
        "pendiente",
        "agendada",
        "confirmada",
        "en_progreso",
        "completada",
        "rechazada",
        "cancelada",
        "no_asistio",
    }
    if nuevo_estado not in estados_validos:
        return error("estado invalido", status=400)

    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)

    usuario, rol = get_current_user()
    if rol == "Groomer":
        if not usuario or not usuario.perfil_groomer or cita.groomer_id != usuario.perfil_groomer.id:
            return error("Acceso denegado", status=403)

    # solicitudes de cliente: solo recepcion/admin pueden aprobar o rechazar
    if cita.estado == "pendiente" and nuevo_estado in {"agendada", "rechazada"}:
        if rol not in {"Admin", "Recepcion"}:
            return error("Solo recepcion puede aprobar o rechazar solicitudes", status=403)

    cita.estado = nuevo_estado

    if nuevo_estado == "confirmada":
        mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
        servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
        fecha = cita.fecha_hora_inicio.strftime("%d/%m/%Y") if cita.fecha_hora_inicio else ""
        hora = cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else ""
        notificacion = _build_notificacion(
            cita,
            "confirmacion",
            mensaje_cita_confirmada(
                mascota.nombre if mascota else "Tu mascota",
                servicio.nombre if servicio else "servicio",
                fecha,
                hora,
            ),
        )
        if notificacion:
            db.session.add(notificacion)

        ahora = datetime.now(timezone.utc)
        horas_hasta_cita = ((cita.fecha_hora_inicio - ahora).total_seconds() / 3600) if cita.fecha_hora_inicio else 0
        if horas_hasta_cita > 24:
            noti24 = _build_notificacion(
                cita,
                "recordatorio_24h",
                mensaje_recordatorio_24h(
                    mascota.nombre if mascota else "Tu mascota",
                    servicio.nombre if servicio else "servicio",
                    hora,
                ),
                delay_minutes=(horas_hasta_cita - 24) * 60,
            )
            if noti24:
                db.session.add(noti24)

        if horas_hasta_cita > 2:
            noti2 = _build_notificacion(
                cita,
                "recordatorio_2h",
                mensaje_recordatorio_2h(
                    mascota.nombre if mascota else "Tu mascota",
                    servicio.nombre if servicio else "servicio",
                    hora,
                ),
                delay_minutes=(horas_hasta_cita - 2) * 60,
            )
            if noti2:
                db.session.add(noti2)

    if nuevo_estado == "completada":
        mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
        servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
        notificacion = _build_notificacion(
            cita,
            "listo_recoger",
            mensaje_listo_recoger(
                mascota.nombre if mascota else "Tu mascota",
                servicio.nombre if servicio else "servicio",
            ),
        )
        if notificacion:
            db.session.add(notificacion)

    db.session.commit()
    return success({"id": cita.id, "estado": cita.estado})


@citas_bp.patch("/citas/<int:cita_id>/reprogramar")
@requiere_rol("Admin", "Recepcion")
def reprogramar_cita(cita_id):
    data = request.get_json() or {}
    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)

    groomer_id = data.get("groomer_id", cita.groomer_id)
    fecha_hora_inicio = data.get("fecha_hora_inicio") or data.get("nueva_fecha_hora_inicio")
    if not fecha_hora_inicio:
        return error("fecha_hora_inicio requerida", status=400)

    resultado = validar_cita_logica(
        groomer_id=groomer_id,
        servicio_id=cita.servicio_id,
        mascota_id=cita.mascota_id,
        fecha_hora_inicio=fecha_hora_inicio,
        cita_id_excluir=cita.id,
    )
    if not resultado["valido"]:
        return error(
            "No se puede reprogramar la cita",
            status=409,
            details={
                "errores": resultado["errores"],
                "duracion_ajustada_min": resultado["duracion_ajustada_min"],
            },
        )

    usuario, _rol = get_current_user()

    # datos antes para audit
    datos_antes = {
        "id": cita.id,
        "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
        "groomer_id": cita.groomer_id,
        "duracion_estimada": cita.duracion_estimada,
    }

    # cancelar notificaciones previas de esta cita
    Notificacion.query.filter_by(cita_id=cita.id, estado="pendiente").update({"estado": "cancelado"})

    # marcar reprogramacion
    try:
        cita.reprogramada_desde = cita.id
    except Exception:
        pass
    cita.reprogramada_en = datetime.now(timezone.utc)
    cita.reprogramada_por = usuario.id if usuario else None

    cita.groomer_id = groomer_id
    cita.fecha_hora_inicio = datetime.fromisoformat(resultado["fecha_hora_inicio"])
    cita.fecha_hora_fin = datetime.fromisoformat(resultado["fecha_hora_fin"])
    cita.duracion_estimada = resultado["duracion_ajustada_min"]

    # crear nuevas notificaciones
    nuevo_inicio = datetime.fromisoformat(resultado["fecha_hora_inicio"])
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    hora = nuevo_inicio.strftime("%H:%M")
    horas_hasta_cita = (_aware_datetime(nuevo_inicio) - datetime.now(timezone.utc)).total_seconds() / 3600
    if horas_hasta_cita > 24:
        noti24 = _build_notificacion(
            cita,
            "recordatorio_24h",
            mensaje_recordatorio_24h(
                mascota.nombre if mascota else "Tu mascota",
                servicio.nombre if servicio else "servicio",
                hora,
            ),
            delay_minutes=(horas_hasta_cita - 24) * 60,
        )
        if noti24:
            db.session.add(noti24)
    if horas_hasta_cita > 2:
        noti2 = _build_notificacion(
            cita,
            "recordatorio_2h",
            mensaje_recordatorio_2h(
                mascota.nombre if mascota else "Tu mascota",
                servicio.nombre if servicio else "servicio",
                hora,
            ),
            delay_minutes=(horas_hasta_cita - 2) * 60,
        )
        if noti2:
            db.session.add(noti2)

    # audit
    datos_despues = {
        "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
        "groomer_id": cita.groomer_id,
        "duracion_estimada": cita.duracion_estimada,
    }
    audit = AuditLog(
        tabla="citas",
        operacion="UPDATE",
        registro_id=cita.id,
        datos_antes=datos_antes,
        datos_despues=datos_despues,
        usuario_id=usuario.id if usuario else None,
    )
    db.session.add(audit)

    db.session.commit()
    return success({"id": cita.id, "estado": cita.estado})



@citas_bp.patch("/citas/<int:cita_id>/confirmar")
@requiere_rol("Admin", "Recepcion")
def confirmar_cita(cita_id):
    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)
    if cita.estado != "agendada":
        return error("Solo se pueden confirmar citas agendadas", status=422)
    usuario, _rol = get_current_user()
    cita.estado = "confirmada"

    # cancelar notificaciones previas pendientes
    Notificacion.query.filter_by(cita_id=cita.id, estado="pendiente").update({"estado": "cancelado"})

    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    fecha = cita.fecha_hora_inicio.strftime("%d/%m/%Y") if cita.fecha_hora_inicio else ""
    hora = cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else ""

    notificacion = _build_notificacion(
        cita,
        "confirmacion",
        mensaje_cita_confirmada(
            mascota.nombre if mascota else "Tu mascota",
            servicio.nombre if servicio else "servicio",
            fecha,
            hora,
        ),
    )
    if notificacion:
        db.session.add(notificacion)

    inicio_cita = _aware_datetime(cita.fecha_hora_inicio)
    horas_hasta_cita = ((inicio_cita - datetime.now(timezone.utc)).total_seconds() / 3600) if inicio_cita else 0
    if horas_hasta_cita > 24:
        noti24 = _build_notificacion(
            cita,
            "recordatorio_24h",
            mensaje_recordatorio_24h(
                mascota.nombre if mascota else "Tu mascota",
                servicio.nombre if servicio else "servicio",
                hora,
            ),
            delay_minutes=(horas_hasta_cita - 24) * 60,
        )
        if noti24:
            db.session.add(noti24)
    if horas_hasta_cita > 2:
        noti2 = _build_notificacion(
            cita,
            "recordatorio_2h",
            mensaje_recordatorio_2h(
                mascota.nombre if mascota else "Tu mascota",
                servicio.nombre if servicio else "servicio",
                hora,
            ),
            delay_minutes=(horas_hasta_cita - 2) * 60,
        )
        if noti2:
            db.session.add(noti2)

    db.session.commit()
    return success({"id": cita.id, "estado": cita.estado})


@citas_bp.post("/solicitudes-cita")
@requiere_rol("Cliente")
def crear_solicitud_cita_cliente():
    return _crear_solicitud_cita_cliente(request.get_json() or {})


@citas_bp.patch("/citas/<int:cita_id>/cancelar")
@requiere_rol("Admin", "Recepcion")
def cancelar_cita(cita_id):
    data = request.get_json() or {}
    motivo = data.get("motivo_cancelacion")
    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)
    if cita.estado in {"completada", "cancelada"}:
        return error("No se puede cancelar una cita completada o ya cancelada", status=422)
    usuario, _rol = get_current_user()

    datos_antes = {
        "estado": cita.estado,
        "motivo_cancelacion": cita.motivo_cancelacion,
    }

    cita.estado = "cancelada"
    cita.motivo_cancelacion = motivo

    # cancelar notificaciones pendientes
    Notificacion.query.filter_by(cita_id=cita.id, estado="pendiente").update({"estado": "cancelado"})

    audit = AuditLog(
        tabla="citas",
        operacion="UPDATE",
        registro_id=cita.id,
        datos_antes=datos_antes,
        datos_despues={"estado": cita.estado, "motivo_cancelacion": motivo},
        usuario_id=usuario.id if usuario else None,
    )
    db.session.add(audit)
    db.session.commit()
    return success({"id": cita.id, "estado": cita.estado})


@citas_bp.get("/citas")
@requiere_rol("Admin", "Recepcion")
def listar_citas():
    fecha = request.args.get("fecha")
    groomer_id = request.args.get("groomer_id", type=int)
    estado = request.args.get("estado")

    query = Cita.query
    if fecha:
        inicio = datetime.fromisoformat(f"{fecha}T00:00:00")
        fin = datetime.fromisoformat(f"{fecha}T23:59:59")
        query = query.filter(Cita.fecha_hora_inicio >= inicio, Cita.fecha_hora_inicio <= fin)
    if groomer_id:
        query = query.filter(Cita.groomer_id == groomer_id)
    if estado:
        query = query.filter(Cita.estado == estado)

    citas = query.order_by(Cita.fecha_hora_inicio.asc()).all()
    resultado = []
    for c in citas:
        mascota = MascotaDueno.query.filter_by(mascota_id=c.mascota_id).first()
        cliente = None
        if mascota:
            cliente = Cliente.query.filter_by(id=mascota.cliente_id).first()
        servicio = None
        # join servicio and groomer lazily to avoid circular import
        from ..models import Servicio, Groomer, Mascota

        servicio = Servicio.query.filter_by(id=c.servicio_id).first()
        groomer = Groomer.query.filter_by(id=c.groomer_id).first()
        mascota_obj = Mascota.query.filter_by(id=c.mascota_id).first()
        resultado.append(
            {
                "id": c.id,
                "fecha_hora_inicio": c.fecha_hora_inicio.isoformat() if c.fecha_hora_inicio else None,
                "fecha_hora_fin": c.fecha_hora_fin.isoformat() if c.fecha_hora_fin else None,
                "estado": c.estado,
                "mascota": {"id": mascota_obj.id, "nombre": mascota_obj.nombre} if mascota_obj else None,
                "cliente": {"id": cliente.id, "nombre": f"{cliente.nombre} {cliente.apellido or ''}"} if cliente else None,
                "servicio": {"id": servicio.id, "nombre": servicio.nombre} if servicio else None,
                "groomer": {"id": groomer.id, "nombre": f"{groomer.nombre} {groomer.apellido or ''}"} if groomer else None,
            }
        )
    return success({"citas": resultado})
