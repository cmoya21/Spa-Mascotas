from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, current_app, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import time
import os
from marshmallow import ValidationError

from ..extensions import db
from ..models import Cita, Cliente, Encuesta, Mascota, MascotaDueno, Notificacion, Servicio, VacunaMascota, AuditLog
from ..schemas.mascota_schema import MascotaSchema
from ..services.citas_service import validar_cita_logica
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.responses import error, success


clientes_bp = Blueprint("clientes_bp", __name__, url_prefix="/api/clientes")


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value)).date()


def _resolve_cliente_actual():
    usuario, rol = get_current_user()
    if not usuario or rol != "Cliente":
        return None
    cliente = usuario.perfil_cliente or Cliente.query.filter_by(usuario_id=usuario.id).first()
    return cliente


def _es_propietario(cliente_id, mascota_id):
    return (
        MascotaDueno.query.filter_by(cliente_id=cliente_id, mascota_id=mascota_id)
        .first()
        is not None
    )


def _normalizar_mascota_payload(data):
    if not isinstance(data, dict):
        return data

    payload = dict(data)
    mapeo_tamano = {
        "pequeño": "pequeno",
        "pequeno": "pequeno",
        "mediano": "mediano",
        "grande": "grande",
        "gigante": "gigante",
    }
    mapeo_temperamento = {
        "nervioso": "ansioso",
        "juguetón": "jugueton",
        "jugueton": "jugueton",
        "jugeton": "jugueton",
    }

    if payload.get("tamano") is not None:
        tamano = str(payload.get("tamano")).strip().lower()
        payload["tamano"] = mapeo_tamano.get(tamano, tamano)
    if payload.get("temperamento") is not None:
        temperamento = str(payload.get("temperamento")).strip().lower()
        payload["temperamento"] = mapeo_temperamento.get(temperamento, temperamento)
    return payload


def _mascota_resumen(mascota, es_principal=False):
    vacunas = (
        VacunaMascota.query.filter_by(mascota_id=mascota.id)
        .order_by(VacunaMascota.aplicada_en.desc(), VacunaMascota.id.desc())
        .limit(3)
        .all()
    )
    return {
        "id": mascota.id,
        "nombre": mascota.nombre,
        "especie": mascota.especie,
        "raza": mascota.raza,
        "tamano": mascota.tamano,
        "peso_kg": float(mascota.peso_kg) if mascota.peso_kg is not None else None,
        "temperamento": mascota.temperamento,
        "alergias_conocidas": mascota.alergias_conocidas,
        "restricciones_medicas": mascota.restricciones_medicas,
        "foto_url": mascota.foto_url,
        "observaciones": mascota.observaciones,
        "es_principal": es_principal,
        "vacunas": [
            {
                "id": vacuna.id,
                "nombre_vacuna": vacuna.nombre_vacuna,
                "aplicada_en": vacuna.aplicada_en.isoformat() if vacuna.aplicada_en else None,
                "proxima_aplicacion": vacuna.proxima_aplicacion.isoformat() if vacuna.proxima_aplicacion else None,
                "lote": vacuna.lote,
                "observaciones": vacuna.observaciones,
            }
            for vacuna in vacunas
        ],
    }


def _cita_resumen(cita):
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    groomer = getattr(cita, "groomer", None)
    if not groomer and cita.groomer_id:
        from ..models import Groomer

        groomer = Groomer.query.filter_by(id=cita.groomer_id).first()
    encuesta = Encuesta.query.filter_by(cita_id=cita.id).first()
    return {
        "id": cita.id,
        "mascota_id": cita.mascota_id,
        "mascota_nombre": mascota.nombre if mascota else None,
        "servicio_id": cita.servicio_id,
        "servicio_nombre": servicio.nombre if servicio else None,
        "groomer_nombre": f"{groomer.nombre} {groomer.apellido or ''}".strip() if groomer else None,
        "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
        "estado": cita.estado,
        "motivo_cancelacion": getattr(cita, "motivo_cancelacion", None),
        "duracion_estimada": cita.duracion_estimada,
        "precio_estimado": float(cita.precio_estimado) if cita.precio_estimado is not None else None,
        "tiene_encuesta": bool(encuesta and encuesta.respondida),
        "puede_cancelar": cita.estado not in {"cancelada", "completada", "no_asistio"}
        and cita.fecha_hora_inicio
        and cita.fecha_hora_inicio - datetime.now(timezone.utc) >= timedelta(hours=24),
    }


def _historial_eventos(cliente_id, mascota_id):
    eventos = []
    relaciones = MascotaDueno.query.filter_by(cliente_id=cliente_id, mascota_id=mascota_id).all()
    if not relaciones:
        return eventos

    citas = (
        Cita.query.join(MascotaDueno, MascotaDueno.mascota_id == Cita.mascota_id)
        .filter(MascotaDueno.cliente_id == cliente_id, Cita.mascota_id == mascota_id)
        .order_by(Cita.fecha_hora_inicio.desc())
        .all()
    )
    for cita in citas:
        servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
        eventos.append(
            {
                "tipo": "cita",
                "id": cita.id,
                "fecha": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
                "titulo": servicio.nombre if servicio else "Cita",
                "estado": cita.estado,
                "detalle": cita.motivo_cancelacion or cita.notas,
            }
        )

    vacunas = (
        VacunaMascota.query.filter_by(cliente_id=cliente_id, mascota_id=mascota_id)
        .order_by(VacunaMascota.aplicada_en.desc(), VacunaMascota.id.desc())
        .all()
    )
    for vacuna in vacunas:
        eventos.append(
            {
                "tipo": "vacuna",
                "id": vacuna.id,
                "fecha": vacuna.aplicada_en.isoformat() if vacuna.aplicada_en else None,
                "titulo": vacuna.nombre_vacuna,
                "estado": "registrada",
                "detalle": vacuna.observaciones,
            }
        )

    notificaciones = (
        Notificacion.query.filter_by(cliente_id=cliente_id)
        .order_by(Notificacion.creado_en.desc())
        .limit(100)
        .all()
    )
    for notificacion in notificaciones:
        if not notificacion.cita_id:
            continue
        cita = Cita.query.filter_by(id=notificacion.cita_id, mascota_id=mascota_id).first()
        if not cita:
            continue
        eventos.append(
            {
                "tipo": "notificacion",
                "id": notificacion.id,
                "fecha": notificacion.creado_en.isoformat() if notificacion.creado_en else None,
                "titulo": notificacion.tipo_evento,
                "estado": notificacion.estado,
                "detalle": notificacion.mensaje,
            }
        )

    eventos.sort(key=lambda item: item.get("fecha") or "", reverse=True)
    return eventos


@clientes_bp.get("/me/mascotas")
@requiere_rol("Cliente")
def listar_mis_mascotas():
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    relaciones = MascotaDueno.query.filter_by(cliente_id=cliente.id).all()
    mascotas = Mascota.query.filter(Mascota.id.in_([rel.mascota_id for rel in relaciones])).all()
    rel_map = {rel.mascota_id: rel.es_principal for rel in relaciones}
    payload = [_mascota_resumen(mascota, rel_map.get(mascota.id, False)) for mascota in mascotas]
    return success({"mascotas": payload, "total": len(payload)})


@clientes_bp.post("/me/mascotas")
@requiere_rol("Cliente")
def crear_mi_mascota():
    # Accept JSON or multipart/form-data with files
    errores = {}
    # collect fields from form or json
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        form = request.form.to_dict()
        files = request.files
    else:
        form = request.get_json() or {}
        files = {}

    # Basic validation using schema for non-file fields
    schema = MascotaSchema()
    try:
        mascota_data = schema.load(_normalizar_mascota_payload(form))
    except ValidationError as err:
        errores.update(err.messages)

    # file validations
    def _allowed_ext(filename, kinds):
        if not filename:
            return False
        ext = filename.rsplit('.', 1)[-1].lower()
        return ext in kinds

    foto = files.get('foto')
    carnet = files.get('carnet_vacunas') or files.get('carnet')

    # foto: images only
    if foto:
        if not _allowed_ext(foto.filename, ('jpg','jpeg','png','gif','webp')):
            errores.setdefault('foto', []).append('Formato de foto inválido')
        else:
            foto.stream.seek(0, os.SEEK_END)
            size = foto.stream.tell()
            foto.stream.seek(0)
            if size > 5 * 1024 * 1024:
                errores.setdefault('foto', []).append('Foto supera 5MB')

    # carnet: pdf or images, up to 10MB
    if carnet:
        if not _allowed_ext(carnet.filename, ('pdf','jpg','jpeg','png','gif','webp')):
            errores.setdefault('carnet_vacunas', []).append('Formato de carnet inválido')
        else:
            carnet.stream.seek(0, os.SEEK_END)
            size = carnet.stream.tell()
            carnet.stream.seek(0)
            if size > 10 * 1024 * 1024:
                errores.setdefault('carnet_vacunas', []).append('Carnet supera 10MB')

    if errores:
        return jsonify({"errores": errores}), 422

    # save files
    upload_root = current_app.config.get('UPLOAD_FOLDER') or (Path(current_app.root_path) / 'uploads')
    fotos_dir = Path(upload_root) / 'mascotas' / 'fotos'
    carnets_dir = Path(upload_root) / 'mascotas' / 'carnets'
    fotos_dir.mkdir(parents=True, exist_ok=True)
    carnets_dir.mkdir(parents=True, exist_ok=True)

    if foto:
        fname = f"foto_{int(time.time())}_{secure_filename(foto.filename)}"
        foto_path = fotos_dir / fname
        foto.save(str(foto_path))
        mascota_data['foto_url'] = f"/uploads/mascotas/fotos/{fname}"

    if carnet:
        fname = f"carnet_{int(time.time())}_{secure_filename(carnet.filename)}"
        carnet_path = carnets_dir / fname
        carnet.save(str(carnet_path))
        mascota_data['carnet_vacunas_url'] = f"/uploads/mascotas/carnets/{fname}"

    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    mascota = Mascota(**mascota_data)
    db.session.add(mascota)
    db.session.flush()

    md = MascotaDueno(mascota_id=mascota.id, cliente_id=cliente.id, es_principal=True)
    db.session.add(md)
    db.session.commit()

    schema = MascotaSchema()
    return jsonify(schema.dump(mascota)), 201

    try:
        data = MascotaSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    mascota = Mascota(
        nombre=data["nombre"],
        especie=data["especie"],
        raza=data.get("raza"),
        tamano=(data.get("tamano") or None),
        fecha_nacimiento=data.get("fecha_nacimiento"),
        peso_kg=data.get("peso_kg"),
        temperamento=data.get("temperamento"),
        alergias_conocidas=data.get("alergias_conocidas"),
        restricciones_medicas=data.get("restricciones_medicas"),
        foto_url=data.get("foto_url"),
        observaciones=data.get("observaciones"),
    )
    db.session.add(mascota)
    db.session.flush()

    MascotaDueno.query.filter_by(cliente_id=cliente.id).update({"es_principal": False})
    db.session.add(MascotaDueno(mascota_id=mascota.id, cliente_id=cliente.id, es_principal=True))
    db.session.commit()

    return success({"mascota": _mascota_resumen(mascota, True)}, status=201)


@clientes_bp.put("/me/mascotas/<int:mascota_id>")
@requiere_rol("Cliente")
def actualizar_mi_mascota(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)
    cliente = _resolve_cliente_actual()
    if not cliente or not _es_propietario(cliente.id, mascota_id):
        return error("Mascota no encontrada", status=404)

    # Accept JSON or multipart/form-data
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        form = request.form.to_dict()
        files = request.files
    else:
        form = request.get_json() or {}
        files = {}

    errores = {}
    schema = MascotaSchema(partial=True)
    try:
        mascota_data = schema.load(_normalizar_mascota_payload(form))
    except ValidationError as err:
        errores.update(err.messages)

    def _allowed_ext(filename, kinds):
        if not filename:
            return False
        ext = filename.rsplit('.', 1)[-1].lower()
        return ext in kinds

    foto = files.get('foto')
    carnet = files.get('carnet_vacunas') or files.get('carnet')

    # validate files
    if foto:
        if not _allowed_ext(foto.filename, ('jpg','jpeg','png','gif','webp')):
            errores.setdefault('foto', []).append('Formato de foto inválido')
        else:
            foto.stream.seek(0, os.SEEK_END)
            size = foto.stream.tell()
            foto.stream.seek(0)
            if size > 5 * 1024 * 1024:
                errores.setdefault('foto', []).append('Foto supera 5MB')

    if carnet:
        if not _allowed_ext(carnet.filename, ('pdf','jpg','jpeg','png','gif','webp')):
            errores.setdefault('carnet_vacunas', []).append('Formato de carnet inválido')
        else:
            carnet.stream.seek(0, os.SEEK_END)
            size = carnet.stream.tell()
            carnet.stream.seek(0)
            if size > 10 * 1024 * 1024:
                errores.setdefault('carnet_vacunas', []).append('Carnet supera 10MB')

    if errores:
        return jsonify({"errores": errores}), 422

    upload_root = current_app.config.get('UPLOAD_FOLDER') or (Path(current_app.root_path) / 'uploads')
    fotos_dir = Path(upload_root) / 'mascotas' / 'fotos'
    carnets_dir = Path(upload_root) / 'mascotas' / 'carnets'
    fotos_dir.mkdir(parents=True, exist_ok=True)
    carnets_dir.mkdir(parents=True, exist_ok=True)

    # replace files: delete previous when uploading new
    if foto:
        # delete old
        if mascota.foto_url and mascota.foto_url.startswith('/uploads/'):
            old_path = Path(current_app.root_path) / mascota.foto_url.lstrip('/')
            try:
                if old_path.exists():
                    old_path.unlink()
            except Exception:
                pass
        fname = f"foto_{int(time.time())}_{secure_filename(foto.filename)}"
        foto_path = fotos_dir / fname
        foto.save(str(foto_path))
        mascota_data['foto_url'] = f"/uploads/mascotas/fotos/{fname}"

    if carnet:
        if mascota.carnet_vacunas_url and mascota.carnet_vacunas_url.startswith('/uploads/'):
            old_path = Path(current_app.root_path) / mascota.carnet_vacunas_url.lstrip('/')
            try:
                if old_path.exists():
                    old_path.unlink()
            except Exception:
                pass
        fname = f"carnet_{int(time.time())}_{secure_filename(carnet.filename)}"
        carnet_path = carnets_dir / fname
        carnet.save(str(carnet_path))
        mascota_data['carnet_vacunas_url'] = f"/uploads/mascotas/carnets/{fname}"

    for k, v in mascota_data.items():
        setattr(mascota, k, v)

    db.session.commit()
    schema = MascotaSchema()
    return jsonify(schema.dump(mascota)), 200
    if not _es_propietario(cliente.id, mascota_id):
        return error("Acceso denegado", status=403)

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return error("Mascota no encontrada", status=404)

    try:
        data = MascotaSchema().load(request.get_json() or {}, partial=True)
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    for key, value in data.items():
        if hasattr(mascota, key):
            setattr(mascota, key, value)

    db.session.commit()
    relation = MascotaDueno.query.filter_by(cliente_id=cliente.id, mascota_id=mascota.id).first()
    return success({"mascota": _mascota_resumen(mascota, bool(relation and relation.es_principal))})


@clientes_bp.delete("/me/mascotas/<int:mascota_id>")
@requiere_rol("Cliente")
def eliminar_mi_mascota(mascota_id):
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    relacion = MascotaDueno.query.filter_by(cliente_id=cliente.id, mascota_id=mascota_id).first()
    if not relacion:
        return error("Acceso denegado", status=403)

    era_principal = relacion.es_principal
    db.session.delete(relacion)
    db.session.flush()

    if era_principal:
        siguiente = MascotaDueno.query.filter_by(cliente_id=cliente.id).order_by(MascotaDueno.desde.desc()).first()
        if siguiente:
            siguiente.es_principal = True

    db.session.commit()
    return success({"message": "Mascota desvinculada"})


@clientes_bp.post("/me/mascotas/<int:mascota_id>/vacunas")
@requiere_rol("Cliente")
def registrar_vacuna_mascota(mascota_id):
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    if not _es_propietario(cliente.id, mascota_id):
        return error("Acceso denegado", status=403)

    data = request.get_json() or {}
    nombre_vacuna = (data.get("nombre_vacuna") or "").strip()
    aplicada_en = _parse_date(data.get("aplicada_en")) or datetime.now(timezone.utc).date()
    if not nombre_vacuna:
        return error("nombre_vacuna requerido", status=400)

    vacuna = VacunaMascota(
        mascota_id=mascota_id,
        cliente_id=cliente.id,
        nombre_vacuna=nombre_vacuna,
        aplicada_en=aplicada_en,
        proxima_aplicacion=_parse_date(data.get("proxima_aplicacion")),
        lote=data.get("lote"),
        observaciones=data.get("observaciones"),
    )
    db.session.add(vacuna)
    db.session.commit()

    return success(
        {
            "vacuna": {
                "id": vacuna.id,
                "mascota_id": vacuna.mascota_id,
                "nombre_vacuna": vacuna.nombre_vacuna,
                "aplicada_en": vacuna.aplicada_en.isoformat() if vacuna.aplicada_en else None,
                "proxima_aplicacion": vacuna.proxima_aplicacion.isoformat() if vacuna.proxima_aplicacion else None,
                "lote": vacuna.lote,
                "observaciones": vacuna.observaciones,
            }
        },
        status=201,
    )


@clientes_bp.post("/me/solicitudes-cita")
@requiere_rol("Cliente")
def solicitar_cita_cliente():
    from .citas import _crear_solicitud_cita_cliente

    return _crear_solicitud_cita_cliente(request.get_json() or {})


@clientes_bp.get("/me/citas")
@requiere_rol("Cliente")
def listar_mis_citas():
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    proximas = str(request.args.get("proximas", "false")).lower() == "true"
    incluir_canceladas = str(request.args.get("incluir_canceladas", "false")).lower() == "true"
    relaciones = MascotaDueno.query.filter_by(cliente_id=cliente.id).all()
    mascota_ids = [rel.mascota_id for rel in relaciones]
    query = Cita.query.filter(Cita.mascota_id.in_(mascota_ids))
    if proximas:
        query = query.filter(Cita.fecha_hora_inicio >= datetime.now(timezone.utc))
    if not incluir_canceladas:
        query = query.filter(Cita.estado != "cancelada")
    citas = query.order_by(Cita.fecha_hora_inicio.asc()).all()
    payload = [_cita_resumen(cita) for cita in citas]
    return success({"citas": payload})


@clientes_bp.patch("/me/citas/<int:cita_id>/cancelar")
@requiere_rol("Cliente")
def cancelar_mi_cita(cita_id):
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    data = request.get_json() or {}
    if data.get("acepta_politica") is not True:
        return error("Debes aceptar la política de cancelación para continuar", status=422)

    cita = Cita.query.get(cita_id)
    if not cita:
        return error("Cita no encontrada", status=404)
    mascota_del_cliente = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id, cliente_id=cliente.id).first()
    if not mascota_del_cliente:
        return error("Mascota no encontrada", status=404)

    if cita.estado != "agendada":
        telefono_spa = current_app.config.get("TELEFONO_SPA", "recepción")
        if cita.estado == "confirmada":
            return error(f"Esta cita ya fue confirmada. Contacta a recepción para cancelarla: {telefono_spa}", status=422)
        if cita.estado == "en_progreso":
            return error("El servicio ya está en curso y no puede cancelarse", status=422)
        if cita.estado == "completada":
            return error("Esta cita ya fue completada", status=422)
        if cita.estado == "cancelada":
            return error("Esta cita ya está cancelada", status=422)
        return error("No se puede cancelar esta cita", status=422)

    if cita.fecha_hora_inicio:
        horas_restantes = (cita.fecha_hora_inicio - datetime.now()).total_seconds() / 3600
        if horas_restantes < 24:
            return jsonify(
                {
                    "error": "cancelacion_anticipacion",
                    "mensaje": "Debes cancelar con al menos 24 horas de anticipación.",
                    "horas_restantes": round(horas_restantes, 1),
                    "contacto": "Para cancelaciones de último momento llama a recepción.",
                }
            ), 422

    motivo = (data.get("motivo_cancelacion") or "").strip()
    if not motivo:
        return error("Debes indicar el motivo de la cancelación", status=422)

    datos_antes = {"estado": cita.estado}
    cita.estado = "cancelada"
    cita.motivo_cancelacion = motivo
    Notificacion.query.filter_by(cita_id=cita.id, estado="pendiente").update({"estado": "cancelado"})

    usuario, _rol = get_current_user()
    audit = AuditLog(
        tabla="citas",
        operacion="UPDATE",
        registro_id=cita.id,
        datos_antes=datos_antes,
        datos_despues={"estado": "cancelada", "motivo_cancelacion": motivo},
        usuario_id=usuario.id if usuario else None,
    )
    db.session.add(audit)
    db.session.commit()
    return success(
        {
            "ok": True,
            "mensaje": "Cita cancelada correctamente. El slot ha quedado disponible.",
            "cita_id": cita.id,
            "fecha_liberada": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        }
    )


@clientes_bp.get("/me/mascotas/<int:mascota_id>/historial")
@requiere_rol("Cliente")
def historial_mascota(mascota_id):
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    if not _es_propietario(cliente.id, mascota_id):
        return error("Acceso denegado", status=403)

    mascota = Mascota.query.filter_by(id=mascota_id).first()
    if not mascota:
        return error("Mascota no encontrada", status=404)

    return success(
        {
            "mascota": _mascota_resumen(mascota),
            "historial": _historial_eventos(cliente.id, mascota_id),
        }
    )


@clientes_bp.get("/me/mascotas/<int:mascota_id>/citas-historial")
@requiere_rol("Cliente")
def citas_historial_mascota(mascota_id):
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    if not _es_propietario(cliente.id, mascota_id):
        return error("Acceso denegado", status=403)

    citas = (
        Cita.query.filter_by(mascota_id=mascota_id)
        .order_by(Cita.fecha_hora_inicio.desc())
        .all()
    )
    return success({"citas": [_cita_resumen(cita) for cita in citas]})


@clientes_bp.get("/me/notificaciones")
@requiere_rol("Cliente")
def mis_notificaciones():
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    notificaciones = (
        Notificacion.query.filter_by(cliente_id=cliente.id)
        .order_by(Notificacion.creado_en.desc())
        .limit(200)
        .all()
    )
    payload = [
        {
            "id": item.id,
            "cita_id": item.cita_id,
            "tipo_canal": item.tipo_canal,
            "tipo_evento": item.tipo_evento,
            "destino": item.destino,
            "mensaje": item.mensaje,
            "estado": item.estado,
            "fecha_programacion": item.fecha_programacion.isoformat() if item.fecha_programacion else None,
            "fecha_envio": item.fecha_envio.isoformat() if item.fecha_envio else None,
        }
        for item in notificaciones
    ]
    return success({"notificaciones": payload})


@clientes_bp.get("/me/beneficios-frecuente")
@requiere_rol("Cliente")
def beneficios_frecuente():
    cliente = _resolve_cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    total_visitas = (
        db.session.query(Cita.id)
        .join(MascotaDueno, MascotaDueno.mascota_id == Cita.mascota_id)
        .filter(MascotaDueno.cliente_id == cliente.id, Cita.estado == "completada")
        .count()
    )

    if total_visitas >= 10:
        nivel = "Gold"
        descuento = 15
    elif total_visitas >= 5:
        nivel = "Silver"
        descuento = 10
    elif total_visitas >= 3:
        nivel = "Bronze"
        descuento = 5
    else:
        nivel = "Nuevo"
        descuento = 0

    mensaje = (
        f"Por tu fidelidad, tienes {descuento}% de descuento en tu próximo servicio"
        if descuento > 0
        else "Sigue acumulando visitas para desbloquear descuentos en tu próximo servicio"
    )
    return {
        "total_visitas": total_visitas,
        "nivel": nivel,
        "descuento_disponible": descuento,
        "mensaje": mensaje,
    }


@clientes_bp.get("/<int:cliente_id>/mascotas")
@requiere_rol("Admin", "Recepcion")
def listar_mascotas_cliente(cliente_id):
    cliente = Cliente.query.filter_by(id=cliente_id).first()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    relaciones = MascotaDueno.query.filter_by(cliente_id=cliente_id).all()
    mascotas = Mascota.query.filter(Mascota.id.in_([rel.mascota_id for rel in relaciones])).all()
    rel_map = {rel.mascota_id: rel.es_principal for rel in relaciones}
    payload = [_mascota_resumen(m, rel_map.get(m.id, False)) for m in mascotas]
    return success({"mascotas": payload})
