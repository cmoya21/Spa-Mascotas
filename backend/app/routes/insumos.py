from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_

from ..extensions import db
from ..models import AuditLog, FichaGrooming, Groomer, Producto, SalidaInsumo, Servicio
from ..utils.decorators import requiere_rol


insumos_bp = Blueprint("insumos_bp", __name__, url_prefix="/api/insumos")
productos_insumos_bp = Blueprint("productos_insumos_bp", __name__, url_prefix="/api/productos")


def _to_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _registro_payload(item, producto):
    return {
        "id": item.id,
        "ficha_id": item.ficha_id,
        "producto_id": item.producto_id,
        "producto_nombre": producto.nombre if producto else None,
        "sku": producto.sku if producto else None,
        "stock": _to_float(producto.stock) if producto else None,
        "cantidad_entregada": _to_float(item.cantidad_entregada),
        "cantidad_usada": _to_float(item.cantidad_usada, None),
        "cantidad_devuelta": _to_float(item.cantidad_devuelta),
        "cantidad_desperdicio": _to_float(item.cantidad_desperdicio),
        "estado": item.estado,
        "notas": item.notas,
        "entregado_en": item.entregado_en.isoformat() if item.entregado_en else None,
        "confirmado_en": item.confirmado_en.isoformat() if item.confirmado_en else None,
    }


def _current_groomer():
    try:
        usuario_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    return Groomer.query.filter_by(usuario_id=usuario_id).first()


def _touch_insumos_consumidos(ficha, producto_id, cantidad):
    actuales = list(ficha.insumos_consumidos or [])
    actualizado = False
    for item in actuales:
        if int(item.get("producto_id") or 0) == int(producto_id):
            item["cantidad"] = float(max(cantidad, 0))
            actualizado = True
            break
    if not actualizado:
        actuales.append({"producto_id": int(producto_id), "cantidad": float(max(cantidad, 0))})
    ficha.insumos_consumidos = actuales


def _cantidad_para_trigger(salida):
    if salida.cantidad_usada is not None:
        return float(salida.cantidad_usada or 0)
    entregada = float(salida.cantidad_entregada or 0)
    devuelta = float(salida.cantidad_devuelta or 0)
    desperdicio = float(salida.cantidad_desperdicio or 0)
    return max(0.0, entregada - devuelta - desperdicio)


def _parse_confirmar_uso_payload(data):
    cantidad_usada = data.get("cantidad_usada")
    cantidad_devuelta = data.get("cantidad_devuelta", 0)
    cantidad_desperdicio = data.get("cantidad_desperdicio", 0)

    if cantidad_usada is None or float(cantidad_usada) <= 0:
        raise ValueError("cantidad_usada debe ser mayor a 0")
    if cantidad_devuelta is not None and float(cantidad_devuelta) < 0:
        raise ValueError("cantidad_devuelta no puede ser negativa")
    if cantidad_desperdicio is not None and float(cantidad_desperdicio) < 0:
        raise ValueError("cantidad_desperdicio no puede ser negativa")

    return float(cantidad_usada), float(cantidad_devuelta or 0), float(cantidad_desperdicio or 0)


def _confirmar_uso_core(salida, groomer, data):
    if not salida:
        return {"kind": "not_found", "mensaje": "Salida no encontrada"}
    if salida.groomer_id != groomer.id:
        return {"kind": "forbidden", "mensaje": "Acceso denegado"}

    ficha = FichaGrooming.query.filter_by(id=salida.ficha_id).first()
    if not ficha:
        return {"kind": "not_found", "mensaje": "Ficha no encontrada"}
    if ficha.fecha_cierre is not None:
        return {"kind": "conflict", "mensaje": "Ficha cerrada"}

    try:
        cantidad_usada, cantidad_devuelta, cantidad_desperdicio = _parse_confirmar_uso_payload(data)
    except ValueError as exc:
        return {"kind": "validation", "mensaje": str(exc)}

    entregada = float(salida.cantidad_entregada or 0)
    if (cantidad_usada + cantidad_devuelta + cantidad_desperdicio) > (entregada + 0.001):
        return {
            "kind": "validation",
            "mensaje": "La suma de usado+devuelto+desperdicio supera la cantidad entregada",
        }

    salida.cantidad_usada = cantidad_usada
    salida.cantidad_devuelta = cantidad_devuelta
    salida.cantidad_desperdicio = cantidad_desperdicio
    salida.estado = "usado"
    salida.confirmado_en = datetime.now(timezone.utc)
    if data.get("notas") is not None:
        salida.notas = data.get("notas")

    _touch_insumos_consumidos(ficha, salida.producto_id, cantidad_usada)
    return {"kind": "ok", "salida": salida, "ficha": ficha}


@insumos_bp.post("/salida")
@requiere_rol("Groomer")
def registrar_salida():
    data = request.get_json() or {}
    ficha_id = data.get("ficha_id")
    insumos = data.get("insumos") or []
    if not ficha_id or not isinstance(insumos, list) or not insumos:
        return jsonify({"error": "datos_invalidos", "mensaje": "ficha_id e insumos son requeridos"}), 400

    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return jsonify({"error": "ficha_no_encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.groomer_id != groomer.id:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403
    if ficha.fecha_cierre is not None:
        return jsonify({"error": "ficha_cerrada", "mensaje": "No se pueden registrar insumos en una ficha cerrada"}), 409

    registros = []
    trigger_items = []
    log_items = []

    for row in insumos:
        producto_id = row.get("producto_id")
        cantidad_entregada = row.get("cantidad_entregada")
        if not producto_id or cantidad_entregada is None:
            return jsonify({"error": "insumo_invalido", "mensaje": "producto_id y cantidad_entregada son requeridos"}), 422

        producto = Producto.query.filter_by(id=producto_id).first()
        if not producto:
            return jsonify({"error": "producto_no_encontrado", "mensaje": f"Producto ID {producto_id} no encontrado"}), 422

        try:
            cantidad_entregada = float(cantidad_entregada)
        except (TypeError, ValueError):
            return jsonify({"error": "cantidad_invalida", "mensaje": "cantidad_entregada debe ser un número válido"}), 422
        if cantidad_entregada <= 0:
            return jsonify({"error": "cantidad_invalida", "mensaje": "La cantidad entregada debe ser mayor a 0"}), 422

        if float(producto.stock or 0) < cantidad_entregada:
            return jsonify(
                {
                    "error": "stock_insuficiente",
                    "mensaje": f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}",
                }
            ), 422

        registro = SalidaInsumo(
            ficha_id=ficha.id,
            producto_id=producto.id,
            cantidad_entregada=cantidad_entregada,
            estado="entregado",
            groomer_id=groomer.id,
            notas=row.get("notas"),
        )
        db.session.add(registro)
        registros.append((registro, producto))
        trigger_items.append({"producto_id": producto.id, "cantidad": cantidad_entregada})
        log_items.append({"producto": producto.nombre, "cantidad": cantidad_entregada})

    ficha.insumos_consumidos = trigger_items

    db.session.add(
        AuditLog(
            tabla="salida_insumos",
            operacion="INSERT",
            registro_id=ficha.id,
            datos_despues={
                "groomer_id": groomer.id,
                "groomer_nombre": groomer.nombre,
                "ficha_id": ficha.id,
                "cita_id": ficha.cita_id,
                "insumos_entregados": log_items,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            usuario_id=groomer.usuario_id,
        )
    )

    db.session.commit()

    return jsonify(
        {
            "registros_creados": len(registros),
            "insumos": [
                {
                    "id": registro.id,
                    "producto_id": producto.id,
                    "producto_nombre": producto.nombre,
                    "cantidad_entregada": float(registro.cantidad_entregada),
                    "estado": registro.estado,
                }
                for registro, producto in registros
            ],
            "mensaje": "Insumos registrados correctamente",
        }
    ), 201


@insumos_bp.get("/salida/ficha/<int:ficha_id>")
@requiere_rol("Groomer")
def listar_salida_por_ficha(ficha_id):
    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return jsonify({"error": "ficha_no_encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.groomer_id != groomer.id:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    rows = SalidaInsumo.query.filter_by(ficha_id=ficha_id).order_by(SalidaInsumo.entregado_en.asc()).all()
    productos = {
        p.id: p
        for p in Producto.query.filter(Producto.id.in_([r.producto_id for r in rows])).all()
    } if rows else {}
    return jsonify([_registro_payload(row, productos.get(row.producto_id)) for row in rows])


@insumos_bp.get("/log-groomer")
@requiere_rol("Groomer")
def log_salida_groomer():
    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    limit = min(request.args.get("limit", type=int) or 20, 200)

    query = SalidaInsumo.query.filter(SalidaInsumo.groomer_id == groomer.id)
    if fecha_inicio:
        query = query.filter(SalidaInsumo.entregado_en >= datetime.fromisoformat(fecha_inicio))
    if fecha_fin:
        query = query.filter(SalidaInsumo.entregado_en <= datetime.fromisoformat(fecha_fin))

    rows = query.order_by(SalidaInsumo.entregado_en.desc()).limit(limit).all()
    producto_ids = [r.producto_id for r in rows]
    ficha_ids = [r.ficha_id for r in rows]
    productos = {p.id: p for p in Producto.query.filter(Producto.id.in_(producto_ids)).all()} if producto_ids else {}
    fichas = {f.id: f for f in FichaGrooming.query.filter(FichaGrooming.id.in_(ficha_ids)).all()} if ficha_ids else {}
    return jsonify(
        [
            {
                **_registro_payload(row, productos.get(row.producto_id)),
                "cita_id": fichas.get(row.ficha_id).cita_id if fichas.get(row.ficha_id) else None,
            }
            for row in rows
        ]
    )


@insumos_bp.get("/log-admin")
@requiere_rol("Admin", "Recepcion")
def log_salida_admin():
    fecha = request.args.get("fecha")
    groomer_id = request.args.get("groomer_id", type=int)
    tipo = (request.args.get("tipo") or "").strip().lower()

    if tipo == "merma":
        fecha_inicio = request.args.get("fecha_inicio")
        fecha_fin = request.args.get("fecha_fin")
        logs = AuditLog.query.filter(AuditLog.tabla == "salida_insumos").order_by(AuditLog.creado_en.desc()).all()
        if groomer_id:
            logs = [item for item in logs if int(item.groomer_id or 0) == int(groomer_id)]
        if fecha_inicio:
            inicio = datetime.fromisoformat(f"{fecha_inicio}T00:00:00")
            logs = [item for item in logs if item.creado_en and item.creado_en >= inicio]
        if fecha_fin:
            fin = datetime.fromisoformat(f"{fecha_fin}T23:59:59")
            logs = [item for item in logs if item.creado_en and item.creado_en <= fin]

        merma_logs = [
            item
            for item in logs
            if isinstance(item.datos_despues, dict) and item.datos_despues.get("accion") == "merma_registrada"
        ]
        producto_ids = [item.datos_despues.get("producto_id") for item in merma_logs if item.datos_despues.get("producto_id")]
        groomer_ids = [item.groomer_id for item in merma_logs if item.groomer_id]
        productos = {p.id: p for p in Producto.query.filter(Producto.id.in_(producto_ids)).all()} if producto_ids else {}
        groomers = {g.id: g for g in Groomer.query.filter(Groomer.id.in_(groomer_ids)).all()} if groomer_ids else {}

        return jsonify(
            [
                {
                    "log_id": item.id,
                    "groomer_id": item.groomer_id,
                    "groomer_nombre": (
                        f"{groomers[item.groomer_id].nombre} {groomers[item.groomer_id].apellido or ''}".strip()
                        if item.groomer_id in groomers
                        else None
                    ),
                    "producto_id": item.datos_despues.get("producto_id"),
                    "producto_nombre": (
                        productos[item.datos_despues.get("producto_id")].nombre
                        if item.datos_despues.get("producto_id") in productos
                        else None
                    ),
                    "cantidad_desperdicio": _to_float(item.datos_despues.get("cantidad_desperdicio"), None),
                    "porcentaje_desperdicio": _to_float(item.datos_despues.get("porcentaje_desperdicio"), None),
                    "motivo": item.datos_despues.get("motivo"),
                    "fecha": item.creado_en.isoformat() if item.creado_en else None,
                    "alerta": item.datos_despues.get("alerta"),
                }
                for item in merma_logs
            ]
        )

    query = SalidaInsumo.query
    if groomer_id:
        query = query.filter(SalidaInsumo.groomer_id == groomer_id)
    if fecha:
        start = datetime.fromisoformat(f"{fecha}T00:00:00")
        end = datetime.fromisoformat(f"{fecha}T23:59:59")
        query = query.filter(SalidaInsumo.entregado_en >= start, SalidaInsumo.entregado_en <= end)

    rows = query.order_by(SalidaInsumo.entregado_en.desc()).limit(500).all()
    producto_ids = [r.producto_id for r in rows]
    fichas_ids = [r.ficha_id for r in rows]
    groomer_ids = [r.groomer_id for r in rows]
    productos = {p.id: p for p in Producto.query.filter(Producto.id.in_(producto_ids)).all()} if producto_ids else {}
    fichas = {f.id: f for f in FichaGrooming.query.filter(FichaGrooming.id.in_(fichas_ids)).all()} if fichas_ids else {}
    groomers = {g.id: g for g in Groomer.query.filter(Groomer.id.in_(groomer_ids)).all()} if groomer_ids else {}

    return jsonify(
        [
            {
                **_registro_payload(row, productos.get(row.producto_id)),
                "cita_id": fichas.get(row.ficha_id).cita_id if fichas.get(row.ficha_id) else None,
                "groomer_nombre": (
                    f"{groomers[row.groomer_id].nombre} {groomers[row.groomer_id].apellido or ''}".strip()
                    if row.groomer_id in groomers
                    else None
                ),
            }
            for row in rows
        ]
    )


@insumos_bp.patch("/salida/<int:salida_id>/confirmar-uso")
@requiere_rol("Groomer")
def confirmar_uso_salida(salida_id):
    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    salida = SalidaInsumo.query.filter_by(id=salida_id).first()
    result = _confirmar_uso_core(salida, groomer, request.get_json() or {})
    if result["kind"] == "not_found":
        return jsonify({"error": "no_encontrado", "mensaje": result["mensaje"]}), 404
    if result["kind"] == "forbidden":
        return jsonify({"error": "acceso_denegado", "mensaje": result["mensaje"]}), 403
    if result["kind"] == "conflict":
        return jsonify({"error": "ficha_cerrada", "mensaje": result["mensaje"]}), 409
    if result["kind"] == "validation":
        return jsonify({"error": "validacion", "mensaje": result["mensaje"]}), 422

    db.session.commit()
    row = result["salida"]
    producto = Producto.query.filter_by(id=row.producto_id).first()
    return jsonify(
        {
            "id": row.id,
            "estado": row.estado,
            "cantidad_usada": _to_float(row.cantidad_usada),
            "cantidad_devuelta": _to_float(row.cantidad_devuelta),
            "cantidad_desperdicio": _to_float(row.cantidad_desperdicio),
            "confirmado_en": row.confirmado_en.isoformat() if row.confirmado_en else None,
            "producto_nombre": producto.nombre if producto else None,
        }
    )


@insumos_bp.patch("/salida/ficha/<int:ficha_id>/confirmar-todos")
@requiere_rol("Groomer")
def confirmar_uso_todos_ficha(ficha_id):
    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=ficha_id).first()
    if not ficha:
        return jsonify({"error": "ficha_no_encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.groomer_id != groomer.id:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403
    if ficha.fecha_cierre is not None:
        return jsonify({"error": "ficha_cerrada", "mensaje": "Ficha cerrada"}), 409

    insumos = (request.get_json() or {}).get("insumos") or []
    if not isinstance(insumos, list) or not insumos:
        return jsonify({"error": "datos_invalidos", "mensaje": "insumos es requerido"}), 400

    errores = []
    confirmados = 0
    try:
        for item in insumos:
            salida_id = item.get("salida_id")
            salida = SalidaInsumo.query.filter_by(id=salida_id, ficha_id=ficha_id).first()
            result = _confirmar_uso_core(salida, groomer, item)
            if result["kind"] != "ok":
                errores.append({"salida_id": salida_id, "error": result["mensaje"]})
                raise ValueError("rollback")
            confirmados += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        if not errores:
            errores.append({"salida_id": None, "error": "No se pudo confirmar todos los insumos"})
        return jsonify({"confirmados": 0, "errores": errores}), 422

    return jsonify({"confirmados": confirmados, "errores": []})


@insumos_bp.patch("/salida/<int:salida_id>/devolver")
@requiere_rol("Groomer")
def devolver_salida(salida_id):
    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    salida = SalidaInsumo.query.filter_by(id=salida_id).first()
    if not salida:
        return jsonify({"error": "no_encontrado", "mensaje": "Salida no encontrada"}), 404
    if salida.groomer_id != groomer.id:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=salida.ficha_id).first()
    if not ficha:
        return jsonify({"error": "ficha_no_encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.fecha_cierre is not None:
        return jsonify({"error": "ficha_cerrada", "mensaje": "Ficha cerrada"}), 409

    data = request.get_json() or {}
    cantidad_devuelta = data.get("cantidad_devuelta")
    if cantidad_devuelta is None or float(cantidad_devuelta) < 0:
        return jsonify({"error": "validacion", "mensaje": "cantidad_devuelta debe ser mayor o igual a 0"}), 422

    cantidad_devuelta = float(cantidad_devuelta)
    if cantidad_devuelta > (float(salida.cantidad_entregada or 0) + 0.001):
        return jsonify({"error": "validacion", "mensaje": "La devolución no puede superar la cantidad entregada"}), 422

    salida.cantidad_devuelta = cantidad_devuelta
    salida.estado = "devuelto"
    salida.confirmado_en = datetime.now(timezone.utc)
    if data.get("notas") is not None:
        salida.notas = data.get("notas")

    _touch_insumos_consumidos(ficha, salida.producto_id, _cantidad_para_trigger(salida))
    db.session.commit()

    return jsonify(
        {
            "id": salida.id,
            "estado": salida.estado,
            "cantidad_devuelta": _to_float(salida.cantidad_devuelta),
            "cantidad_usada": _to_float(salida.cantidad_usada, None),
        }
    )


@insumos_bp.patch("/salida/<int:salida_id>/merma")
@requiere_rol("Groomer")
def registrar_merma_salida(salida_id):
    groomer = _current_groomer()
    if not groomer:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    salida = SalidaInsumo.query.filter_by(id=salida_id).first()
    if not salida:
        return jsonify({"error": "no_encontrado", "mensaje": "Salida no encontrada"}), 404
    if salida.groomer_id != groomer.id:
        return jsonify({"error": "acceso_denegado", "mensaje": "Acceso denegado"}), 403

    ficha = FichaGrooming.query.filter_by(id=salida.ficha_id).first()
    if not ficha:
        return jsonify({"error": "ficha_no_encontrada", "mensaje": "Ficha no encontrada"}), 404
    if ficha.fecha_cierre is not None:
        return jsonify({"error": "ficha_cerrada", "mensaje": "Ficha cerrada"}), 409

    data = request.get_json() or {}
    cantidad_desperdicio = data.get("cantidad_desperdicio")
    motivo = (data.get("motivo") or "").strip()
    if cantidad_desperdicio is None or float(cantidad_desperdicio) < 0:
        return jsonify({"error": "validacion", "mensaje": "cantidad_desperdicio debe ser mayor o igual a 0"}), 422
    if not motivo:
        return jsonify({"error": "validacion", "mensaje": "motivo es requerido"}), 422

    cantidad_desperdicio = float(cantidad_desperdicio)
    if cantidad_desperdicio > (float(salida.cantidad_entregada or 0) + 0.001):
        return jsonify({"error": "validacion", "mensaje": "La merma no puede superar la cantidad entregada"}), 422

    salida.cantidad_desperdicio = cantidad_desperdicio
    salida.estado = "desperdiciado"
    salida.notas = motivo
    salida.confirmado_en = datetime.now(timezone.utc)

    entregada = float(salida.cantidad_entregada or 0)
    porcentaje = round((cantidad_desperdicio / entregada) * 100, 1) if entregada > 0 else 0

    db.session.add(
        AuditLog(
            tabla="salida_insumos",
            operacion="UPDATE",
            registro_id=salida.id,
            usuario_id=groomer.usuario_id,
            datos_despues={
                "accion": "merma_registrada",
                "salida_id": salida.id,
                "producto_id": salida.producto_id,
                "cantidad_desperdicio": cantidad_desperdicio,
                "cantidad_entregada": entregada,
                "porcentaje_desperdicio": porcentaje,
                "motivo": motivo,
            },
        )
    )

    if entregada > 0 and cantidad_desperdicio > (entregada * 0.3):
        db.session.add(
            AuditLog(
                tabla="salida_insumos",
                operacion="UPDATE",
                registro_id=salida.id,
                usuario_id=groomer.usuario_id,
                datos_despues={
                    "accion": "merma_registrada",
                    "alerta": "alto_desperdicio",
                    "salida_id": salida.id,
                    "groomer_id": groomer.id,
                    "producto_id": salida.producto_id,
                    "cantidad_desperdicio": cantidad_desperdicio,
                    "porcentaje_desperdicio": porcentaje,
                    "motivo": motivo,
                },
            )
        )

    _touch_insumos_consumidos(ficha, salida.producto_id, _cantidad_para_trigger(salida))
    db.session.commit()

    return jsonify(
        {
            "id": salida.id,
            "estado": salida.estado,
            "cantidad_desperdicio": _to_float(salida.cantidad_desperdicio),
            "porcentaje_desperdicio": porcentaje,
        }
    )


@productos_insumos_bp.get("/disponibles-para-insumos")
@requiere_rol("Groomer")
def productos_disponibles_para_insumos():
    q = (request.args.get("q") or "").strip().lower()
    servicio_id = request.args.get("servicio_id", type=int)

    sugeridos_ids = []
    sugeridos_cantidad = {}
    if servicio_id:
        servicio = Servicio.query.filter_by(id=servicio_id).first()
        for item in (servicio.consumo_insumos or []) if servicio else []:
            pid = item.get("producto_id")
            if pid:
                sugeridos_ids.append(pid)
                sugeridos_cantidad[pid] = item.get("cantidad")

    query = Producto.query.filter(Producto.activo.is_(True), Producto.stock > 0)
    if q:
        query = query.filter(or_(Producto.nombre.ilike(f"%{q}%"), Producto.sku.ilike(f"%{q}%")))
    productos = query.order_by(Producto.nombre.asc()).limit(100).all()

    return jsonify(
        [
            {
                "id": p.id,
                "nombre": p.nombre,
                "sku": p.sku,
                "stock": float(p.stock or 0),
                "precio_base": float(p.precio_base or 0),
                "es_sugerido": p.id in sugeridos_ids,
                "cantidad_sugerida": _to_float(sugeridos_cantidad.get(p.id), None),
            }
            for p in productos
        ]
    )
