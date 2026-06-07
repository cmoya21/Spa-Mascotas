from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, date, timezone
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, request, jsonify, abort
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy import or_, func

from ..extensions import db
from ..models import (
    AuditLog,
    Cita,
    DisponibilidadGroomer,
    ChecklistItemTemplate,
    Cliente,
    Encuesta,
    FichaChecklist,
    FichaGrooming,
    FotoFicha,
    Groomer,
    HistorialMascota,
    InsumoSalida,
    Mascota,
    MascotaDueno,
    Notificacion,
    Producto,
    Servicio,
)
from ..utils.decorators import get_current_user
from ..utils.responses import error, success
from ..utils.roles import require_role, solo_propio_groomer


groomers_bp = Blueprint("groomers_bp", __name__, url_prefix="/api/groomers")
fichas_bp = Blueprint("fichas_bp", __name__, url_prefix="/api/fichas")

_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_PHOTO_BYTES = 8 * 1024 * 1024
_MESES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
_DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_NOTIFICACION_ENVIADA_ESTADOS = {"enviado", "entregado", "leido", "leída", "procesado"}


def _current_groomer():
    usuario, rol = get_current_user()
    if rol != "Groomer" or not usuario or not usuario.perfil_groomer:
        return None, error("Acceso denegado", status=403)
    return usuario.perfil_groomer, None


def _parse_date(value):
    if not value:
        return date.today()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _parse_iso_date_or_422(value):
    if not value:
        return date.today()
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        abort(422, description="Formato de fecha inválido. Use YYYY-MM-DD")


def _fecha_label_es(fecha_value):
    return f"{_DIAS_ES[fecha_value.weekday()]} {fecha_value.day} {_MESES_ES[fecha_value.month - 1]}"


def _edad_anios(fecha_nacimiento):
    if not fecha_nacimiento:
        return None
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))


def _estado_ficha_detalle(cita_id):
    ficha = FichaGrooming.query.filter_by(cita_id=cita_id).first()
    if not ficha:
        return {
            "id": None,
            "estado": "sin_iniciar",
            "checklist_completo": False,
            "items_pendientes": 0,
            "items_total": 0,
        }, None

    items_total = db.session.query(func.count(FichaChecklist.id)).filter(FichaChecklist.ficha_id == ficha.id).scalar() or 0
    items_pendientes = (
        db.session.query(func.count(FichaChecklist.id))
        .filter(FichaChecklist.ficha_id == ficha.id, FichaChecklist.completado.is_(False))
        .scalar()
        or 0
    )
    estado = "cerrada" if ficha.fecha_cierre else "en_curso"
    return (
        {
            "id": ficha.id,
            "estado": estado,
            "checklist_completo": bool(ficha.checklist_completo),
            "items_pendientes": int(items_pendientes),
            "items_total": int(items_total),
        },
        ficha,
    )


def _notificacion_cliente_detalle(cita_id):
    notificaciones = (
        Notificacion.query.filter_by(cita_id=cita_id)
        .order_by(Notificacion.creado_en.desc(), Notificacion.id.desc())
        .all()
    )
    if not notificaciones:
        return None

    ultima = notificaciones[0]
    enviada = bool(ultima.fecha_envio or ultima.estado in _NOTIFICACION_ENVIADA_ESTADOS)
    return {
        "id": ultima.id,
        "estado": ultima.estado,
        "tipo_evento": ultima.tipo_evento,
        "fecha_envio": ultima.fecha_envio.isoformat() if ultima.fecha_envio else None,
        "destino": ultima.destino,
        "enviada": enviada,
    }


def _agenda_cita_payload(cita):
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    ficha_detalle, ficha = _estado_ficha_detalle(cita.id)
    notificacion_cliente = _notificacion_cliente_detalle(cita.id)

    return {
        "id": cita.id,
        "hora_inicio": cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else None,
        "hora_fin": cita.fecha_hora_fin.strftime("%H:%M") if cita.fecha_hora_fin else None,
        "estado": cita.estado,
        "duracion_estimada": cita.duracion_estimada,
        "notas": cita.notas,
        "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
        "estado_ficha": ficha_detalle["estado"],
        "mascota": {
            "id": mascota.id if mascota else None,
            "nombre": mascota.nombre if mascota else None,
            "raza": mascota.raza if mascota else None,
            "peso_kg": float(mascota.peso_kg) if mascota and mascota.peso_kg is not None else None,
            "temperamento": mascota.temperamento if mascota else None,
            "alergias_conocidas": mascota.alergias_conocidas if mascota else None,
            "restricciones_medicas": mascota.restricciones_medicas if mascota else None,
            "foto_url": mascota.foto_url if mascota else None,
            "tiene_alergias": bool(mascota and mascota.alergias_conocidas),
        },
        "servicio": {
            "id": servicio.id if servicio else None,
            "nombre": servicio.nombre if servicio else None,
            "duracion_base_minutos": servicio.duracion_base_minutos if servicio else None,
        },
        "ficha": ficha_detalle,
        "cliente_notificado": bool(notificacion_cliente and notificacion_cliente["enviada"]),
        "notificacion_cliente": notificacion_cliente,
    }


def _citas_personales_en_rango(groomer_id, inicio, fin):
    return (
        Cita.query.filter(
            Cita.groomer_id == groomer_id,
            Cita.fecha_hora_inicio >= inicio,
            Cita.fecha_hora_inicio < fin,
            Cita.estado.notin_(["cancelada", "no_asistio"]),
        )
        .order_by(Cita.fecha_hora_inicio.asc())
        .all()
    )


def _parse_week_range(semana=None, fecha=None):
    if semana:
        try:
            anio, week_raw = semana.split("-W", 1)
            return datetime.fromisocalendar(int(anio), int(week_raw), 1).date()
        except Exception:
            pass
    fecha_value = _parse_date(fecha)
    return fecha_value - timedelta(days=fecha_value.weekday())


def _mascota_payload(mascota):
    return {
        "id": mascota.id,
        "nombre": mascota.nombre,
        "raza": mascota.raza,
        "tamano": mascota.tamano,
        "fecha_nacimiento": mascota.fecha_nacimiento.isoformat() if mascota.fecha_nacimiento else None,
        "edad_anios": _edad_anios(mascota.fecha_nacimiento),
        "peso_kg": float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        "temperamento": mascota.temperamento,
        "alergias_conocidas": mascota.alergias_conocidas,
        "restricciones_medicas": mascota.restricciones_medicas,
        "foto_url": mascota.foto_url,
        "observaciones": mascota.observaciones,
    }


def _servicio_payload(servicio):
    return {
        "id": servicio.id,
        "nombre": servicio.nombre,
        "duracion_base_minutos": servicio.duracion_base_minutos,
    }


def _estado_ficha_for_cita(cita):
    ficha = FichaGrooming.query.filter_by(cita_id=cita.id).first()
    if not ficha:
        return "sin_iniciar", None
    if ficha.fecha_cierre:
        return "cerrada", ficha
    return "en_curso", ficha


def _cita_payload(cita):
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    estado_ficha, ficha = _estado_ficha_for_cita(cita)
    return {
        "id": cita.id,
        "mascota_id": cita.mascota_id,
        "groomer_id": cita.groomer_id,
        "servicio_id": cita.servicio_id,
        "fecha": cita.fecha_hora_inicio.date().isoformat() if cita.fecha_hora_inicio else None,
        "hora_inicio": cita.fecha_hora_inicio.strftime("%H:%M") if cita.fecha_hora_inicio else None,
        "hora_fin": cita.fecha_hora_fin.strftime("%H:%M") if cita.fecha_hora_fin else None,
        "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
        "estado": cita.estado,
        "estado_ficha": estado_ficha,
        "ficha_id": ficha.id if ficha else None,
        "mascota": _mascota_payload(mascota) if mascota else None,
        "servicio": _servicio_payload(servicio) if servicio else None,
    }


def _ficha_basic_payload(ficha):
    return {
        "id": ficha.id,
        "cita_id": ficha.cita_id,
        "groomer_id": ficha.groomer_id,
        "checklist_completo": ficha.checklist_completo,
        "fecha_cierre": ficha.fecha_cierre.isoformat() if ficha.fecha_cierre else None,
        "estado_inicial": ficha.estado_inicial,
        "temperatura_ingreso": float(ficha.temperatura_ingreso) if ficha.temperatura_ingreso is not None else None,
        "peso_momento_servicio": float(ficha.peso_momento_servicio) if ficha.peso_momento_servicio is not None else None,
        "raza_tamano_momento": ficha.raza_tamano_momento,
        "estado_final": ficha.estado_final,
        "observaciones_final": ficha.observaciones_final,
        "notas_internas": ficha.notas_internas,
        "consumido_inventario": ficha.consumido_inventario,
        "insumos_consumidos": ficha.insumos_consumidos or [],
    }


def _checklist_items_payload(ficha):
    templates = {
        item.id: item
        for item in ChecklistItemTemplate.query.filter(
            ChecklistItemTemplate.id.in_([item.item_id for item in ficha.checklist_items])
        ).all()
    }
    items = []
    for item in ficha.checklist_items:
        template = templates.get(item.item_id)
        items.append(
            {
                "id": item.id,
                "item_id": item.item_id,
                "orden": template.orden if template else 0,
                "nombre": template.nombre if template else "",
                "requiere_obs": template.requiere_obs if template else False,
                "completado": item.completado,
                "observacion": item.observacion,
                "completado_en": item.completado_en.isoformat() if item.completado_en else None,
            }
        )
    return items


def _fotos_payload(ficha):
    before = []
    after = []
    for foto in ficha.fotos:
        payload = {
            "id": foto.id,
            "url": foto.url,
            "tipo": foto.tipo,
            "descripcion": foto.descripcion,
            "creado_en": foto.creado_en.isoformat() if foto.creado_en else None,
        }
        if foto.tipo == "antes":
            before.append(payload)
        else:
            after.append(payload)
    return {"antes": before, "despues": after, "conteo": {"antes": len(before), "despues": len(after)}}


def _insumos_payload(ficha):
    if not ficha.insumos_consumidos:
        return []
    product_ids = [item.get("producto_id") for item in ficha.insumos_consumidos if item.get("producto_id")]
    productos = {item.id: item for item in Producto.query.filter(Producto.id.in_(product_ids)).all()} if product_ids else {}
    payload = []
    for item in ficha.insumos_consumidos:
        producto = productos.get(item.get("producto_id"))
        payload.append(
            {
                "producto_id": item.get("producto_id"),
                "producto_nombre": producto.nombre if producto else None,
                "sku": producto.sku if producto else None,
                "unidad_medida": getattr(producto, "unidad_medida", None) if producto else None,
                "cantidad": float(item.get("cantidad") or 0),
                "devuelto": float(item.get("devuelto") or 0) if item.get("devuelto") is not None else None,
                "desperdicio": float(item.get("desperdicio") or 0) if item.get("desperdicio") is not None else None,
            }
        )
    return payload


def _estado_cierre_payload(ficha):
    items_total = FichaChecklist.query.filter_by(ficha_id=ficha.id).count()
    items_pendientes = (
        FichaChecklist.query.join(ChecklistItemTemplate)
        .filter(FichaChecklist.ficha_id == ficha.id, FichaChecklist.completado.is_(False))
        .count()
    )
    fotos_antes = FotoFicha.query.filter_by(ficha_id=ficha.id, tipo="antes").count()
    fotos_despues = FotoFicha.query.filter_by(ficha_id=ficha.id, tipo="despues").count()
    razones_bloqueo = []
    if items_pendientes:
        razones_bloqueo.append(f"Checklist incompleto: {items_pendientes} ítems pendientes")
    if fotos_antes == 0:
        razones_bloqueo.append("Falta foto del estado inicial")
    if fotos_despues == 0:
        razones_bloqueo.append("Falta foto del resultado final")
    return {
        "puede_cerrar": bool(ficha.fecha_cierre is None and items_pendientes == 0 and fotos_antes > 0 and fotos_despues > 0),
        "checklist": {
            "completo": bool(ficha.checklist_completo),
            "pendientes": int(items_pendientes),
            "total": int(items_total),
        },
        "fotos": {
            "antes": int(fotos_antes),
            "despues": int(fotos_despues),
            "ok": bool(fotos_antes > 0 and fotos_despues > 0),
        },
        "razones_bloqueo": razones_bloqueo,
    }


def _ficha_detalle_payload(ficha):
    cita = Cita.query.filter_by(id=ficha.cita_id).first()
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first() if cita else None
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first() if cita else None
    payload = _ficha_basic_payload(ficha)
    payload.update(
        {
            "cita": _cita_payload(cita) if cita else None,
            "mascota": _mascota_payload(mascota) if mascota else None,
            "servicio": _servicio_payload(servicio) if servicio else None,
            "checklist": _checklist_items_payload(ficha),
            "fotos": _fotos_payload(ficha),
            "insumos_detalle": _insumos_payload(ficha),
            "alerta_alergias": bool(mascota and mascota.alergias_conocidas),
            "alerta_restricciones": bool(mascota and mascota.restricciones_medicas),
        }
    )
    return payload


def _current_user_id():
    try:
        return int(get_jwt_identity())
    except (TypeError, ValueError):
        return None


def _registro_historial(mascota_id, tipo, descripcion, groomer_id=None):
    item = HistorialMascota(
        mascota_id=mascota_id,
        tipo=tipo,
        descripcion=descripcion,
    )
    db.session.add(item)
    return item


def _cliente_from_cita(cita):
    relation = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id).first()
    if not relation:
        return None
    return Cliente.query.filter_by(id=relation.cliente_id).first()


def _checklist_templates_for_service(servicio_id):
    return (
        ChecklistItemTemplate.query.filter_by(servicio_id=servicio_id, activo=True)
        .order_by(ChecklistItemTemplate.orden.asc(), ChecklistItemTemplate.id.asc())
        .all()
    )


def _ficha_or_404(ficha_id):
    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return None, error("Ficha no encontrada", status=404)
    solo_propio_groomer(ficha)
    return ficha, None


def _cita_or_404(cita_id):
    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return None, error("Cita no encontrada", status=404)
    solo_propio_groomer(cita)
    return cita, None


def _upload_root():
    return Path(current_app.config.get("UPLOAD_FOLDER") or Path(current_app.root_path) / "uploads")


def _save_photo_file(ficha_id, tipo, archivo):
    filename = secure_name = archivo.filename or "foto"
    ext = Path(secure_name).suffix.lower()
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        return None, error("Solo se permiten imágenes JPG, PNG o WEBP", status=422)

    if request.content_length and request.content_length > _MAX_PHOTO_BYTES:
        return None, error("La imagen supera el tamaño máximo permitido de 8MB", status=422)

    root = _upload_root() / "fichas" / str(ficha_id)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    nombre_archivo = f"{tipo}_{timestamp}{ext}"
    absolute_path = root / nombre_archivo
    archivo.save(absolute_path)
    relative_url = f"/uploads/fichas/{ficha_id}/{nombre_archivo}"
    return {"absolute_path": absolute_path, "relative_url": relative_url}, None


def _remove_photo_file(url_value):
    if not url_value:
        return
    relative = str(url_value).lstrip("/")
    path = Path(current_app.root_path) / relative
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _apply_inventory_for_ficha(ficha):
    if not ficha.insumos_consumidos:
        return None

    for item in ficha.insumos_consumidos:
        producto_id = item.get("producto_id")
        cantidad = float(item.get("cantidad") or 0)
        if not producto_id or cantidad <= 0:
            return error("Insumo invalido", status=422)
        producto = Producto.query.filter_by(id=producto_id).first()
        if not producto:
            return error(f"Producto ID {producto_id} no encontrado", status=422)
        if float(producto.stock) - cantidad < 0:
            return error("Stock insuficiente para uno o más insumos. Ajusta los insumos registrados y vuelve a intentar.", status=422)

    if db.engine.dialect.name == "sqlite":
        for item in ficha.insumos_consumidos:
            producto = Producto.query.filter_by(id=item.get("producto_id")).first()
            cantidad = float(item.get("cantidad") or 0)
            producto.stock = float(producto.stock or 0) - cantidad
    return None


@groomers_bp.get("/me/agenda")
@require_role("Groomer")
def agenda_personal():
    groomer, error_response = _current_groomer()
    if error_response:
        return error_response

    fecha = _parse_iso_date_or_422(request.args.get("fecha"))
    inicio = datetime.combine(fecha, datetime.min.time())
    fin = inicio + timedelta(days=1)
    citas = _citas_personales_en_rango(groomer.id, inicio, fin)
    return jsonify([_agenda_cita_payload(cita) for cita in citas])


@groomers_bp.get("/me/agenda/semana")
@require_role("Groomer")
def agenda_personal_semana():
    groomer, error_response = _current_groomer()
    if error_response:
        return error_response

    fecha = _parse_iso_date_or_422(request.args.get("fecha"))
    inicio = fecha - timedelta(days=fecha.weekday())
    fin = inicio + timedelta(days=7)
    citas = _citas_personales_en_rango(
        groomer.id,
        datetime.combine(inicio, datetime.min.time()),
        datetime.combine(fin, datetime.min.time()),
    )

    disponibilidad_activa = {
        item.dia_semana
        for item in DisponibilidadGroomer.query.filter_by(groomer_id=groomer.id, activo=True).all()
    }
    dias = {}
    for offset in range(7):
        dia = inicio + timedelta(days=offset)
        dias[dia.isoformat()] = {
            "fecha_label": _fecha_label_es(dia),
            "trabaja": dia.weekday() in disponibilidad_activa,
            "capacidad": groomer.capacidad_diaria,
            "citas": [],
        }

    total = 0
    completadas = 0
    en_curso = 0
    pendientes = 0
    for cita in citas:
        payload = _agenda_cita_payload(cita)
        cita_fecha = cita.fecha_hora_inicio.date().isoformat()
        dias.setdefault(
            cita_fecha,
            {
                "fecha_label": _fecha_label_es(cita.fecha_hora_inicio.date()),
                "trabaja": cita.fecha_hora_inicio.weekday() in disponibilidad_activa,
                "capacidad": groomer.capacidad_diaria,
                "citas": [],
            },
        )["citas"].append(payload)
        total += 1
        estado_ficha = payload["ficha"]["estado"]
        if estado_ficha == "cerrada":
            completadas += 1
        elif estado_ficha == "en_curso":
            en_curso += 1
        else:
            pendientes += 1

    return jsonify(
        {
            "semana_inicio": inicio.isoformat(),
            "semana_fin": (inicio + timedelta(days=6)).isoformat(),
            "dias": dias,
            "resumen": {
                "total_citas": total,
                "completadas": completadas,
                "en_curso": en_curso,
                "pendientes": pendientes,
            },
        }
    )


@groomers_bp.get("/me/stats")
@require_role("Groomer")
def stats_personales():
    groomer, error_response = _current_groomer()
    if error_response:
        return error_response

    hoy = date.today()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    fin_hoy = inicio_hoy + timedelta(days=1)
    inicio_semana = inicio_hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=7)

    citas_hoy_list = _citas_personales_en_rango(groomer.id, inicio_hoy, fin_hoy)
    citas_hoy = len(citas_hoy_list)
    completadas_hoy = len([cita for cita in citas_hoy_list if cita.estado == "completada"])
    citas_semana = len(_citas_personales_en_rango(groomer.id, inicio_semana, fin_semana))
    promedio = (
        db.session.query(func.avg(Encuesta.calificacion))
        .join(Cita, Encuesta.cita_id == Cita.id)
        .filter(
            Cita.groomer_id == groomer.id,
            Encuesta.respondida.is_(True),
            Encuesta.calificacion.isnot(None),
        )
        .scalar()
    )

    return jsonify(
        {
            "citas_hoy": citas_hoy,
            "completadas_hoy": completadas_hoy,
            "citas_semana": citas_semana,
            "promedio_calificacion": round(float(promedio), 1) if promedio is not None else None,
        }
    )


@groomers_bp.get("/activos")
def groomers_activos():
    groomers = (
        Groomer.query.filter_by(estado_activo=True)
        .order_by(Groomer.nombre.asc(), Groomer.apellido.asc())
        .all()
    )
    payload = [
        {
            "id": item.id,
            "nombre": item.nombre,
            "especialidad": item.especialidad,
        }
        for item in groomers
    ]
    return success({"groomers": payload})


@fichas_bp.post("")
@require_role("Groomer")
def crear_ficha():
    groomer, error_response = _current_groomer()
    if error_response:
        return error_response

    data = request.get_json() or {}
    cita_id = data.get("cita_id")
    if not cita_id:
        return error("cita_id requerido", status=400)

    cita = Cita.query.filter_by(id=int(cita_id)).first()
    if not cita:
        return error("Cita no encontrada", status=404)
    if cita.groomer_id is None:
        cita.groomer_id = groomer.id
        db.session.flush()
    elif cita.groomer_id != groomer.id:
        return error("Esta cita pertenece a otro groomer.", status=403)

    if cita.estado not in {"agendada", "confirmada"}:
        return error("La cita no está en un estado válido para iniciar", status=422)
    if FichaGrooming.query.filter_by(cita_id=cita.id).first():
        return error("Ya existe una ficha para esta cita", status=409)

    ficha = FichaGrooming(
        cita_id=cita.id,
        groomer_id=groomer.id,
        estado_inicial=data.get("estado_inicial"),
        temperatura_ingreso=data.get("temperatura_ingreso"),
        peso_momento_servicio=data.get("peso_momento_servicio"),
        raza_tamano_momento=data.get("raza_tamano_momento"),
        notas_internas=data.get("notas_internas"),
        checklist_completo=False,
    )
    db.session.add(ficha)
    db.session.flush()

    cita.estado = "en_progreso"
    templates = _checklist_templates_for_service(cita.servicio_id)
    for template in templates:
        db.session.add(
            FichaChecklist(
                ficha_id=ficha.id,
                item_id=template.id,
                completado=False,
            )
        )
    _registro_historial(
        mascota_id=cita.mascota_id,
        tipo="servicio",
        descripcion=f"Servicio iniciado por {groomer.nombre}",
        groomer_id=groomer.id,
    )
    db.session.commit()
    return success({"ficha": _ficha_detalle_payload(ficha)}, status=201)


@fichas_bp.get("/<int:ficha_id>")
@require_role("Groomer")
def obtener_ficha(ficha_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    return success({"ficha": _ficha_detalle_payload(ficha)})


@fichas_bp.get("/cita/<int:cita_id>")
@require_role("Groomer")
def obtener_ficha_por_cita(cita_id):
    groomer, error_response = _current_groomer()
    if error_response:
        return error_response

    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)
    if cita.groomer_id != groomer.id:
        return error("Acceso denegado", status=403)

    ficha = FichaGrooming.query.filter_by(cita_id=cita.id).first()
    if not ficha:
        return error("Ficha no encontrada", status=404)
    return success({"ficha": _ficha_detalle_payload(ficha)})


@fichas_bp.patch("/<int:ficha_id>")
@require_role("Groomer")
def actualizar_ficha_base(ficha_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    if ficha.fecha_cierre:
        return error("Ficha cerrada", status=409)

    data = request.get_json() or {}
    for field in ["estado_inicial", "raza_tamano_momento", "notas_internas"]:
        if field in data:
            setattr(ficha, field, data.get(field))
    if "temperatura_ingreso" in data:
        ficha.temperatura_ingreso = data.get("temperatura_ingreso") or None
    if "peso_momento_servicio" in data:
        ficha.peso_momento_servicio = data.get("peso_momento_servicio") or None

    db.session.commit()
    return success({"ficha": _ficha_detalle_payload(ficha)})


@fichas_bp.patch("/<int:ficha_id>/checklist/<int:item_id>")
@require_role("Groomer")
def actualizar_item_checklist(ficha_id, item_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    if ficha.fecha_cierre:
        return error("No puedes modificar una ficha cerrada", status=409)

    data = request.get_json() or {}
    item = FichaChecklist.query.filter_by(ficha_id=ficha.id, item_id=item_id).first()
    if not item:
        return error("Item de checklist no encontrado", status=404)

    template = ChecklistItemTemplate.query.filter_by(id=item_id).first()
    completado = bool(data.get("completado"))
    observacion = data.get("observacion")
    if completado and template and template.requiere_obs and not (observacion or "").strip():
        return error("Este ítem requiere observación para marcarse completo", status=422)

    item.completado = completado
    if observacion is not None:
        item.observacion = observacion
    item.completado_en = datetime.now(timezone.utc) if item.completado else None
    pendientes = FichaChecklist.query.filter_by(ficha_id=ficha.id, completado=False).count()
    ficha.checklist_completo = pendientes == 0
    db.session.commit()
    return success({"item_id": item.item_id, "completado": item.completado, "checklist_completo": ficha.checklist_completo, "items_pendientes": pendientes})


@fichas_bp.post("/<int:ficha_id>/fotos")
@require_role("Groomer")
def agregar_foto_ficha(ficha_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    if ficha.fecha_cierre:
        return error("No puedes modificar una ficha cerrada", status=409)

    archivo = request.files.get("archivo")
    if not archivo:
        return error("archivo requerido", status=400)
    tipo = (request.form.get("tipo") or "").strip().lower()
    if tipo not in {"antes", "despues"}:
        return error("Tipo de foto invalido", status=422)

    saved, file_error = _save_photo_file(ficha.id, tipo, archivo)
    if file_error:
        return file_error

    foto = FotoFicha(
        ficha_id=ficha.id,
        url=saved["relative_url"],
        tipo=tipo,
        descripcion=request.form.get("descripcion"),
    )
    db.session.add(foto)
    db.session.commit()
    return success({"foto_id": foto.id, "url": foto.url, "tipo": foto.tipo, "descripcion": foto.descripcion}, status=201)


@fichas_bp.get("/<int:ficha_id>/fotos")
@require_role("Groomer")
def listar_fotos_ficha(ficha_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    fotos = _fotos_payload(ficha)
    return success({"antes": fotos["antes"], "despues": fotos["despues"], "conteo": fotos["conteo"]})


@fichas_bp.delete("/<int:ficha_id>/fotos/<int:foto_id>")
@require_role("Groomer")
def eliminar_foto_ficha(ficha_id, foto_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    if ficha.fecha_cierre:
        return error("No puedes modificar una ficha cerrada", status=409)

    foto = FotoFicha.query.filter_by(id=foto_id, ficha_id=ficha.id).first()
    if not foto:
        return error("Foto no encontrada", status=404)
    _remove_photo_file(foto.url)
    db.session.delete(foto)
    db.session.commit()
    return success({"message": "Foto eliminada"})


@fichas_bp.patch("/<int:ficha_id>/insumos")
@require_role("Groomer")
def guardar_insumos_ficha(ficha_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error
    if ficha.fecha_cierre:
        return error("No puedes modificar una ficha cerrada", status=409)

    data = request.get_json() or {}
    insumos = data.get("insumos") or []
    if not insumos:
        return error("insumos requerido", status=400)

    sanitized = []
    groomer, _ = _current_groomer()
    user_id = _current_user_id()
    for item in insumos:
        producto_id = item.get("producto_id")
        cantidad = item.get("cantidad")
        devuelto = item.get("devuelto")
        desperdicio = item.get("desperdicio")
        if not producto_id or cantidad is None:
            return error("Insumo invalido", status=422)
        producto = Producto.query.filter_by(id=producto_id).first()
        if not producto:
            return error(f"Producto ID {producto_id} no encontrado", status=422)
        if float(cantidad) <= 0:
            return error("Cantidad invalida", status=422)
        if devuelto is not None and float(devuelto) < 0:
            return error("Devuelto invalido", status=422)
        if desperdicio is not None and float(desperdicio) < 0:
            return error("Desperdicio invalido", status=422)
        sanitized.append(
            {
                "producto_id": producto.id,
                "producto_nombre": producto.nombre,
                "cantidad": float(cantidad),
                "devuelto": float(devuelto) if devuelto is not None else None,
                "desperdicio": float(desperdicio) if desperdicio is not None else None,
            }
        )

    ficha.insumos_consumidos = sanitized
    InsumoSalida.query.filter_by(ficha_id=ficha.id).delete()
    for item in sanitized:
        db.session.add(
            InsumoSalida(
                ficha_id=ficha.id,
                producto_id=item["producto_id"],
                groomer_id=ficha.groomer_id,
                cantidad=item["cantidad"],
                estado="registrado",
            )
        )

    db.session.add(
        AuditLog(
            tabla="fichas_grooming",
            operacion="UPDATE",
            registro_id=ficha.id,
            datos_despues={
                "accion": "registro_insumos",
                "groomer_id": ficha.groomer_id,
                "groomer_nombre": groomer.nombre if groomer else None,
                "insumos": sanitized,
                "cita_id": ficha.cita_id,
            },
            usuario_id=user_id,
            groomer_id=ficha.groomer_id,
        )
    )
    db.session.commit()
    return success({"mensaje": "Insumos guardados", "cantidad": len(sanitized)})


@fichas_bp.get("/<int:ficha_id>/insumos-disponibles")
@require_role("Groomer")
def insumos_disponibles(ficha_id):
    ficha, scope_error = _ficha_or_404(ficha_id)
    if scope_error:
        return scope_error

    q = (request.args.get("q") or "").strip().lower()
    query = Producto.query.filter(Producto.activo.is_(True), Producto.stock > 0)
    if q:
        query = query.filter(or_(Producto.nombre.ilike(f"%{q}%"), Producto.sku.ilike(f"%{q}%")))
    productos = query.order_by(Producto.nombre.asc()).limit(20).all()
    payload = [
        {
            "id": producto.id,
            "nombre": producto.nombre,
            "sku": producto.sku,
            "stock": float(producto.stock or 0),
            "precio_base": float(producto.precio_base or 0),
            "unidad_medida": getattr(producto, "unidad_medida", None),
        }
        for producto in productos
    ]
    return success({"productos": payload})


@fichas_bp.get("/<int:ficha_id>/estado-cierre")
@require_role("Groomer")
def estado_cierre_ficha(ficha_id):
    usuario_id = get_jwt_identity()
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Acceso denegado", "mensaje": "Acceso denegado"}), 403

    groomer = Groomer.query.filter_by(usuario_id=usuario_id).first()
    if not groomer:
        return jsonify({"error": "Acceso denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return jsonify({"error": "Ficha no encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.groomer_id != groomer.id:
        return jsonify({"error": "Acceso denegado", "mensaje": "Acceso denegado"}), 403

    return jsonify(_estado_cierre_payload(ficha))


@fichas_bp.patch("/<int:ficha_id>/cerrar")
@require_role("Groomer")
def cerrar_ficha(ficha_id):
    usuario_id = get_jwt_identity()
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Acceso denegado", "mensaje": "Acceso denegado"}), 403

    groomer = Groomer.query.filter_by(usuario_id=usuario_id).first()
    if not groomer:
        return jsonify({"error": "Acceso denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return jsonify({"error": "Ficha no encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.groomer_id != groomer.id:
        return jsonify({"error": "Acceso denegado", "mensaje": "Acceso denegado"}), 403
    if ficha.fecha_cierre is not None:
        return jsonify({"error": "ficha_cerrada", "mensaje": "La ficha ya está cerrada"}), 409

    body = request.get_json() or {}
    if not body.get("estado_final"):
        return jsonify({"error": "estado_final_requerido", "mensaje": "estado_final requerido"}), 400

    items_pendientes = (
        FichaChecklist.query.join(ChecklistItemTemplate)
        .filter(FichaChecklist.ficha_id == ficha.id, FichaChecklist.completado.is_(False))
        .count()
    )
    if items_pendientes > 0:
        return jsonify(
            {
                "error": "checklist_incompleto",
                "mensaje": f"No se puede cerrar: {items_pendientes} ítem(s) pendientes",
                "items_pendientes": int(items_pendientes),
            }
        ), 422

    fotos_antes = FotoFicha.query.filter_by(ficha_id=ficha.id, tipo="antes").count()
    if fotos_antes == 0:
        return jsonify({"error": "sin_foto_antes", "mensaje": "Se requiere al menos 1 foto del estado inicial"}), 422

    fotos_despues = FotoFicha.query.filter_by(ficha_id=ficha.id, tipo="despues").count()
    if fotos_despues == 0:
        return jsonify({"error": "sin_foto_despues", "mensaje": "Se requiere al menos 1 foto del resultado final"}), 422

    inventory_error = _apply_inventory_for_ficha(ficha)
    if inventory_error:
        return inventory_error

    try:
        ficha.fecha_cierre = datetime.now(timezone.utc)
        ficha.estado_final = body.get("estado_final")
        ficha.observaciones_final = body.get("observaciones_final", "")
        ficha.consumido_inventario = True
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        message = str(exc).lower()
        if "stock" in message or "inventario" in message:
            return jsonify(
                {
                    "error": "stock_insuficiente",
                    "mensaje": "Stock insuficiente para uno o más insumos. Ajusta los insumos registrados y vuelve a intentar.",
                }
            ), 422
        raise

    cita = Cita.query.filter_by(id=ficha.cita_id).first()
    if not cita:
        db.session.rollback()
        return jsonify({"error": "cita_no_encontrada", "mensaje": "Cita no encontrada"}), 404
    cita.estado = "completada"
    cita.duracion_real = body.get("duracion_real")

    cliente = _cliente_from_cita(cita)
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    recomendaciones = (body.get("recomendaciones") or "").strip()

    if mascota:
        _registro_historial(
            mascota_id=mascota.id,
            tipo="servicio",
            descripcion=(
                f"Servicio {servicio.nombre if servicio else ''} finalizado. "
                f"Estado final: {body.get('estado_final')}. "
                f"Recomendaciones: {recomendaciones or 'Ninguna'}"
            ),
            groomer_id=groomer.id,
        )

    canal_notificacion = None
    if cliente:
        canal_notificacion = cliente.canal_notificacion or "email"
        destino = cliente.telefono if canal_notificacion in {"whatsapp", "sms"} else cliente.usuario.email
        db.session.add(
            Notificacion(
                cita_id=cita.id,
                cliente_id=cliente.id,
                tipo_canal=canal_notificacion,
                tipo_evento="listo_recoger",
                destino=destino,
                mensaje=(
                    f"¡{mascota.nombre if mascota else 'Tu mascota'} está lista para ser recogida! "
                    f"El servicio de {servicio.nombre if servicio else 'grooming'} finalizó exitosamente. "
                    f"¡Quedó hermosa/hermoso! 🐾"
                ),
                fecha_programacion=datetime.now(timezone.utc),
                estado="pendiente",
            )
        )

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        message = str(exc).lower()
        if "stock" in message or "inventario" in message:
            return jsonify(
                {
                    "error": "stock_insuficiente",
                    "mensaje": "Stock insuficiente para uno o más insumos. Ajusta los insumos registrados y vuelve a intentar.",
                }
            ), 422
        raise

    return jsonify(
        {
            "ok": True,
            "mensaje": "Servicio cerrado. El cliente será notificado.",
            "cita_id": cita.id,
            "ficha_id": ficha.id,
            "duracion_real": body.get("duracion_real"),
            "estado_final": body.get("estado_final"),
            "notificacion_programada": True,
            "canal_notificacion": canal_notificacion,
        }
    )
