from datetime import datetime, timedelta

from flask import current_app

from ..models import BloqueoCalendario, Cita, DisponibilidadGroomer, Groomer, Mascota, Servicio
from ..utils.duracion import calcular_duracion

ESTADOS_ACTIVOS = ["agendada", "confirmada", "en_progreso"]


def _parse_datetime(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def _day_bounds(fecha):
    inicio = datetime.combine(fecha, datetime.min.time())
    fin = inicio + timedelta(days=1)
    return inicio, fin


def _parse_descanso(intervalo_descanso):
    if not isinstance(intervalo_descanso, dict):
        return None
    inicio = intervalo_descanso.get("inicio")
    fin = intervalo_descanso.get("fin")
    if not inicio or not fin:
        return None
    return inicio, fin


def _time_to_datetime(fecha, hora_str):
    if hasattr(hora_str, "hour") and hasattr(hora_str, "minute"):
        hora = hora_str
    else:
        valor = str(hora_str)
        partes = valor.split(":")
        hora = datetime.strptime(":".join(partes[:2]), "%H:%M").time()
    return datetime.combine(fecha, hora)


def validar_cita_logica(groomer_id, servicio_id, mascota_id, fecha_hora_inicio, cita_id_excluir=None):
    errores = []

    groomer = Groomer.query.filter_by(id=groomer_id).first()
    if not groomer:
        return {
            "valido": False,
            "errores": ["Groomer no encontrado"],
            "duracion_ajustada_min": None,
        }

    servicio = Servicio.query.filter_by(id=servicio_id).first()
    if not servicio:
        return {
            "valido": False,
            "errores": ["Servicio no encontrado"],
            "duracion_ajustada_min": None,
        }

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return {
            "valido": False,
            "errores": ["Mascota no encontrada"],
            "duracion_ajustada_min": None,
        }

    inicio = _parse_datetime(fecha_hora_inicio)
    duracion_ajustada = calcular_duracion(
        servicio.duracion_base_minutos,
        float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        mascota.temperamento,
        servicio.factor_tamano_raza,
    )
    fin = inicio + timedelta(minutes=duracion_ajustada)
    dia_semana = int(inicio.strftime("%w"))
    dia_inicio, dia_fin = _day_bounds(inicio.date())

    horario = DisponibilidadGroomer.query.filter_by(
        groomer_id=groomer.id,
        dia_semana=dia_semana,
        activo=True,
    ).first()
    if not horario:
        errores.append("El groomer no trabaja ese día de la semana")
    else:
        jornada_inicio = _time_to_datetime(inicio.date(), horario.hora_inicio)
        jornada_fin = _time_to_datetime(inicio.date(), horario.hora_fin)

        if inicio < jornada_inicio:
            errores.append("El horario está fuera de la jornada laboral del groomer")
        if fin > jornada_fin:
            errores.append(
                f"El servicio de {duracion_ajustada} min no cabe antes del fin de jornada ({horario.hora_fin.strftime('%H:%M')})"
            )

        descanso = _parse_descanso(horario.intervalo_descanso)
        if descanso:
            descanso_inicio = _time_to_datetime(inicio.date(), descanso[0])
            descanso_fin = _time_to_datetime(inicio.date(), descanso[1])
            if _overlaps(inicio, fin, descanso_inicio, descanso_fin):
                errores.append("El horario se solapa con el intervalo de descanso del groomer")

    bloqueos = BloqueoCalendario.query.filter(
        (BloqueoCalendario.groomer_id == groomer.id) | (BloqueoCalendario.groomer_id.is_(None)),
        BloqueoCalendario.fecha_inicio < fin,
        BloqueoCalendario.fecha_fin > inicio,
    ).all()
    if bloqueos:
        errores.append("El groomer tiene un bloqueo en ese horario")

    citas_solapadas = (
        Cita.query.filter(
            Cita.groomer_id == groomer.id,
            Cita.estado.notin_(["cancelada", "no_asistio"]),
            Cita.fecha_hora_inicio < fin,
            Cita.fecha_hora_fin > inicio,
        )
        .order_by(Cita.fecha_hora_inicio.asc())
        .all()
    )
    if cita_id_excluir is not None:
        citas_solapadas = [item for item in citas_solapadas if item.id != cita_id_excluir]
    capacidad_simultanea = groomer.capacidad_simultanea or 1
    if len(citas_solapadas) >= capacidad_simultanea:
        if citas_solapadas:
            primera = citas_solapadas[0]
            errores.append(
                f"Solapamiento con cita existente de {primera.fecha_hora_inicio.strftime('%H:%M')} a {primera.fecha_hora_fin.strftime('%H:%M')}"
            )
        else:
            errores.append("El groomer alcanzó su capacidad simultánea")

    citas_del_dia = Cita.query.filter(
        Cita.groomer_id == groomer.id,
        Cita.estado.notin_(["cancelada", "no_asistio"]),
        Cita.fecha_hora_inicio >= dia_inicio,
        Cita.fecha_hora_inicio < dia_fin,
    ).count()
    capacidad_diaria = groomer.capacidad_diaria or capacidad_simultanea or 1
    if citas_del_dia >= capacidad_diaria:
        errores.append(
            f"El groomer alcanzó su capacidad máxima ({capacidad_diaria} servicios) para ese día"
        )

    total_citas_dia = Cita.query.filter(
        Cita.estado.notin_(["cancelada", "no_asistio"]),
        Cita.fecha_hora_inicio >= dia_inicio,
        Cita.fecha_hora_inicio < dia_fin,
    ).count()
    max_global = current_app.config.get("MAX_SERVICIOS_DIA_GLOBAL")
    if max_global and total_citas_dia >= max_global:
        errores.append("La capacidad diaria global fue alcanzada")

    return {
        "valido": not errores,
        "errores": errores,
        "duracion_ajustada_min": duracion_ajustada,
        "fecha_hora_inicio": inicio.isoformat(),
        "fecha_hora_fin": fin.isoformat(),
        "precio_estimado": float(servicio.precio_base or 0),
        "groomer_id": groomer.id,
        "servicio_id": servicio.id,
        "mascota_id": mascota.id,
    }


def validar_cita(data):
    resultado = validar_cita_logica(
        groomer_id=data["groomer_id"],
        servicio_id=data["servicio_id"],
        mascota_id=data["mascota_id"],
        fecha_hora_inicio=data["fecha_hora_inicio"],
    )
    return resultado["valido"], resultado, 200 if resultado["valido"] else 409
