from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import AuditLog, Groomer, Producto, Rol, SalidaInsumo, Usuario
from ..utils.notif_worker import notificar_bajo_stock
from ..utils.decorators import requiere_rol
from ..utils.responses import success


alertas_bp = Blueprint("alertas_bp", __name__, url_prefix="/api/alertas")


@alertas_bp.get("/inventario")
@requiere_rol("Admin", "Recepcion")
def alertas_inventario():
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)

    criticos = (
        Producto.query.filter(Producto.stock <= Producto.stock_minimo, Producto.activo.is_(True))
        .order_by((Producto.stock_minimo - Producto.stock).desc())
        .all()
    )

    def _producto_alerta(item, tipo):
        stock = float(item.stock or 0)
        minimo = float(item.stock_minimo or 0)
        if stock <= 0:
            prioridad = "URGENTE"
        elif stock <= (minimo * 0.5):
            prioridad = "ALTO"
        else:
            prioridad = "MEDIO"
        return {
            "id": item.id,
            "nombre": item.nombre,
            "sku": item.sku,
            "stock": stock,
            "stock_minimo": minimo,
            "unidades_faltantes": max(minimo - stock, 0),
            "tipo": tipo,
            "prioridad": prioridad,
        }

    bajo_stock_tienda = [_producto_alerta(item, "tienda") for item in criticos]
    bajo_stock_insumos = [_producto_alerta(item, "insumo_tecnico") for item in criticos]

    admins = (
        Usuario.query.join(Rol)
        .filter(Rol.nombre.in_(["Admin", "Recepcion"]), Usuario.estado_activo.is_(True))
        .all()
    )
    insertadas = 0
    for item in criticos:
        insertadas += notificar_bajo_stock(item, admins)

    alertas_audit = (
        AuditLog.query.filter(AuditLog.tabla == "salida_insumos", AuditLog.creado_en >= since_7d)
        .order_by(AuditLog.creado_en.desc())
        .all()
    )
    alto_consumo = []
    for item in alertas_audit:
        datos = item.datos_despues if isinstance(item.datos_despues, dict) else {}
        if datos.get("alerta") != "alto_desperdicio":
            continue
        groomer = Groomer.query.filter_by(id=datos.get("groomer_id")).first() if datos.get("groomer_id") else None
        producto = Producto.query.filter_by(id=datos.get("producto_id")).first() if datos.get("producto_id") else None
        alto_consumo.append(
            {
                "groomer_id": datos.get("groomer_id"),
                "groomer_nombre": (
                    f"{groomer.nombre} {groomer.apellido or ''}".strip() if groomer else None
                ),
                "producto_id": datos.get("producto_id"),
                "producto_nombre": producto.nombre if producto else datos.get("producto_nombre"),
                "porcentaje": float(datos.get("porcentaje_desperdicio") or 0),
                "creado_en": item.creado_en.isoformat() if item.creado_en else None,
                "motivo": datos.get("motivo"),
            }
        )
    alto_consumo = alto_consumo[:10]

    consumo_30d = {
        int(row.producto_id): float(row.total or 0)
        for row in db.session.query(
            SalidaInsumo.producto_id.label("producto_id"),
            func.sum(SalidaInsumo.cantidad_usada).label("total"),
        )
        .filter(SalidaInsumo.entregado_en >= (datetime.now(timezone.utc) - timedelta(days=30)))
        .group_by(SalidaInsumo.producto_id)
        .all()
    }

    recomendaciones = []
    urgentes = 0
    altos = 0
    medios = 0
    for item in criticos:
        stock = float(item.stock or 0)
        minimo = float(item.stock_minimo or 0)
        if stock <= 0:
            prioridad = "URGENTE"
            urgentes += 1
        elif stock <= (minimo * 0.5):
            prioridad = "ALTO"
            altos += 1
        else:
            prioridad = "MEDIO"
            medios += 1
        recomendaciones.append(
            {
                "id": item.id,
                "nombre": item.nombre,
                "sku": item.sku,
                "stock": stock,
                "stock_minimo": minimo,
                "consumo_mensual": consumo_30d.get(int(item.id), 0),
                "prioridad": prioridad,
            }
        )

    payload = {
        "bajo_stock_tienda": bajo_stock_tienda,
        "bajo_stock_insumos": bajo_stock_insumos,
        "alto_consumo": alto_consumo,
        "recomendaciones": recomendaciones,
        "total_criticos": len(bajo_stock_tienda),
        "total_alto_consumo": len(alto_consumo),
        "resumen": {
            "urgentes": urgentes,
            "altos": altos,
            "medios": medios,
        },
    }

    if insertadas:
        db.session.commit()

    return jsonify(payload)


@alertas_bp.get("/consumo-por-groomer")
@requiere_rol("Admin")
def consumo_por_groomer():
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    query = (
        db.session.query(
            Groomer.id.label("groomer_id"),
            Groomer.nombre.label("groomer_nombre"),
            Groomer.apellido.label("groomer_apellido"),
            Producto.id.label("producto_id"),
            Producto.nombre.label("producto_nombre"),
            func.sum(SalidaInsumo.cantidad_usada).label("total_usado"),
            func.sum(SalidaInsumo.cantidad_desperdicio).label("total_desperdicio"),
            func.count(SalidaInsumo.id).label("total_servicios"),
        )
        .join(Groomer, SalidaInsumo.groomer_id == Groomer.id)
        .join(Producto, SalidaInsumo.producto_id == Producto.id)
    )

    if fecha_inicio:
        query = query.filter(SalidaInsumo.entregado_en >= datetime.fromisoformat(fecha_inicio))
    if fecha_fin:
        query = query.filter(SalidaInsumo.entregado_en <= datetime.fromisoformat(fecha_fin))

    rows = (
        query.group_by(Groomer.id, Groomer.nombre, Groomer.apellido, Producto.id, Producto.nombre)
        .order_by(func.sum(SalidaInsumo.cantidad_desperdicio).desc())
        .all()
    )

    result = []
    for row in rows:
        total_usado = float(row.total_usado or 0)
        total_desperdicio = float(row.total_desperdicio or 0)
        porcentaje_merma = round((total_desperdicio / total_usado) * 100, 1) if total_usado > 0 else 0.0
        result.append(
            {
                "groomer_id": row.groomer_id,
                "groomer": f"{row.groomer_nombre} {row.groomer_apellido or ''}".strip(),
                "producto_id": row.producto_id,
                "producto": row.producto_nombre,
                "total_usado": total_usado,
                "total_desperdicio": total_desperdicio,
                "total_servicios": int(row.total_servicios or 0),
                "porcentaje_merma": porcentaje_merma,
            }
        )

    result.sort(key=lambda item: item["porcentaje_merma"], reverse=True)
    return jsonify(result)


@alertas_bp.get("/inventario/activos")
@requiere_rol("Admin", "Recepcion")
def alertas_inventario_activos():
    total = Producto.query.filter(Producto.stock <= Producto.stock_minimo, Producto.activo.is_(True)).count()
    return success({"total": total, "total_criticos": total})
