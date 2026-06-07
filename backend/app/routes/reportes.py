from datetime import date, datetime, timezone

from flask import Blueprint, request
from sqlalchemy import text

from ..extensions import db
from ..models import Cita, Cliente, Groomer, MascotaDueno
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.responses import error, success


reportes_bp = Blueprint("reportes_bp", __name__, url_prefix="/api/reportes")


def _fetch_view(sql):
    rows = db.session.execute(text(sql)).mappings().all()
    return [dict(row) for row in rows]


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _groomer_id_from_user(usuario):
    if not usuario or not usuario.perfil_groomer:
        return None
    return usuario.perfil_groomer.id


def _cliente_id_from_user(usuario):
    if not usuario or not usuario.perfil_cliente:
        return None
    return usuario.perfil_cliente.id


@reportes_bp.get("/dashboard")
@requiere_rol("Admin", "Recepcion", "Groomer", "Cliente")
def dashboard_ejecutivo():
    _usuario, rol = get_current_user()
    if rol != "Admin":
        return error("Acceso denegado", status=403)

    try:
        data = _fetch_view("SELECT * FROM v_dashboard_ejecutivo")
    except Exception:
        return error("Reporte no disponible", status=404)
    return success({"dashboard": data})


@reportes_bp.get("/top-servicios")
@requiere_rol("Admin")
def top_servicios():
    data = _fetch_view("SELECT * FROM v_top_servicios")
    return success({"items": data})


@reportes_bp.get("/ticket-por-cita")
@requiere_rol("Admin", "Recepcion")
def ticket_por_cita():
    data = _fetch_view("SELECT * FROM v_ticket_por_cita")
    if get_current_user()[1] == "Recepcion":
        for item in data:
            item.pop("subtotal", None)
            item.pop("impuesto", None)
            item.pop("total", None)
    return success({"items": data})


@reportes_bp.get("/clientes-frecuentes")
@requiere_rol("Admin", "Recepcion")
def clientes_frecuentes():
    data = _fetch_view("SELECT * FROM v_clientes_frecuentes")
    if get_current_user()[1] == "Recepcion":
        for item in data:
            item.pop("gasto_total", None)
    return success({"items": data})


@reportes_bp.get("/satisfaccion")
@requiere_rol("Admin", "Recepcion")
def satisfaccion_alias():
    data = _fetch_view("SELECT * FROM v_satisfaccion_clientes")
    comentarios = db.session.execute(
        text(
            """
            SELECT e.comentario, e.calificacion, e.nps,
                   m.nombre as mascota, s.nombre as servicio,
                   e.respondida_en
            FROM encuestas e
            JOIN citas c ON e.cita_id=c.id
            JOIN mascotas m ON c.mascota_id=m.id
            JOIN servicios s ON c.servicio_id=s.id
            WHERE e.respondida=True
            ORDER BY e.respondida_en DESC LIMIT 20
            """
        )
    ).mappings().all()
    return success({
        "por_mes": data,
        "comentarios_recientes": [dict(row) for row in comentarios],
    })


@reportes_bp.get("/satisfaccion-clientes")
@requiere_rol("Admin")
def satisfaccion_clientes():
    return satisfaccion_alias()


@reportes_bp.get("/groomer/agenda-hoy")
@requiere_rol("Groomer")
def groomer_agenda_hoy():
    usuario, _rol = get_current_user()
    groomer_id = _groomer_id_from_user(usuario)
    if not groomer_id:
        return error("Groomer no encontrado", status=404)

    hoy = datetime.now(timezone.utc).date()
    citas = Cita.query.filter(
        Cita.groomer_id == groomer_id,
        Cita.fecha_hora_inicio >= datetime.combine(hoy, datetime.min.time()),
        Cita.fecha_hora_inicio <= datetime.combine(hoy, datetime.max.time()),
    ).order_by(Cita.fecha_hora_inicio.asc()).all()

    payload = [
        {
            "cita_id": cita.id,
            "mascota_id": cita.mascota_id,
            "servicio_id": cita.servicio_id,
            "estado": cita.estado,
            "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat(),
        }
        for cita in citas
    ]
    return success({"items": payload})


@reportes_bp.get("/cliente/historial")
@requiere_rol("Cliente")
def cliente_historial():
    usuario, _rol = get_current_user()
    cliente_id = _cliente_id_from_user(usuario)
    if not cliente_id:
        return error("Cliente no encontrado", status=404)

    mascotas_ids = [rel.mascota_id for rel in MascotaDueno.query.filter_by(cliente_id=cliente_id).all()]
    if not mascotas_ids:
        return success({"items": []})

    citas = Cita.query.filter(Cita.mascota_id.in_(mascotas_ids)).order_by(Cita.fecha_hora_inicio.desc()).all()
    payload = [
        {
            "cita_id": cita.id,
            "mascota_id": cita.mascota_id,
            "servicio_id": cita.servicio_id,
            "estado": cita.estado,
            "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat(),
        }
        for cita in citas
    ]
    return success({"items": payload})


@reportes_bp.get("/mis-citas")
@requiere_rol("Cliente")
def mis_citas():
    return cliente_historial()


@reportes_bp.get("/ventas")
@requiere_rol("Admin")
def ventas():
    fi = _parse_date(request.args.get("fecha_inicio"))
    ff = _parse_date(request.args.get("fecha_fin"))
    rows = db.session.execute(
        text(
            """
            SELECT
              DATE(f.fecha_emision) as fecha,
              COUNT(f.id) as total_facturas,
              SUM(f.total) as ingresos_servicios,
                            SUM(COALESCE(p2_totales.total_productos,0)) as ingresos_productos,
                            SUM(f.total) + SUM(COALESCE(p2_totales.total_productos,0))
                                as ingresos_totales
            FROM facturas f
            LEFT JOIN (
              SELECT DATE(creado_en) as fecha, SUM(total) as total_productos
              FROM pedidos WHERE estado IN ('pagado','entregado')
              GROUP BY DATE(creado_en)
                        ) p2_totales ON p2_totales.fecha = DATE(f.fecha_emision)
            WHERE f.estado='pagada'
              AND (:fi IS NULL OR DATE(f.fecha_emision) >= :fi)
              AND (:ff IS NULL OR DATE(f.fecha_emision) <= :ff)
            GROUP BY DATE(f.fecha_emision)
            ORDER BY fecha DESC
            """
        ),
        {"fi": fi, "ff": ff},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows]})


@reportes_bp.get("/ranking-rentabilidad")
@requiere_rol("Admin")
def ranking_rentabilidad():
    servicios = _fetch_view("SELECT * FROM v_top_servicios LIMIT 10")
    productos = db.session.execute(
        text(
            """
            SELECT p.nombre, SUM(dp.cantidad) as vendidos,
                   SUM(dp.cantidad * dp.precio_unitario) as ingresos
            FROM detalle_pedido dp
            JOIN productos p ON dp.producto_id=p.id
            JOIN pedidos ped ON dp.pedido_id=ped.id
            WHERE ped.estado IN ('pagado','entregado')
            GROUP BY p.id, p.nombre
            ORDER BY ingresos DESC LIMIT 10
            """
        )
    ).mappings().all()
    return success({
        "servicios": servicios,
        "productos": [dict(row) for row in productos],
    })


@reportes_bp.get("/ocupacion")
@requiere_rol("Admin")
def ocupacion():
    fi = _parse_date(request.args.get("fecha_inicio"))
    ff = _parse_date(request.args.get("fecha_fin"))
    rows = db.session.execute(
        text(
            """
            SELECT * FROM v_ocupacion_groomer
            WHERE (:fi IS NULL OR fecha >= :fi)
              AND (:ff IS NULL OR fecha <= :ff)
            """
        ),
        {"fi": fi, "ff": ff},
    ).mappings().all()
    data = [dict(row) for row in rows]

    if fi and ff and fi <= ff:
        total_dias = (ff - fi).days + 1
    elif data:
        fechas = [item["fecha"] for item in data if item.get("fecha")]
        total_dias = (max(fechas) - min(fechas)).days + 1 if fechas else 1
    else:
        total_dias = 1

    total_groomers = Groomer.query.filter_by(estado_activo=True).count()
    total_minutos_posibles = total_groomers * total_dias * 480
    total_minutos_usados = sum(float(item.get("minutos_ocupados") or 0) for item in data)
    porcentaje = round((total_minutos_usados / total_minutos_posibles * 100) if total_minutos_posibles else 0, 2)

    return success({
        "por_groomer": data,
        "porcentaje_global": porcentaje,
    })


@reportes_bp.get("/auditoria-insumos")
@requiere_rol("Admin")
def auditoria_insumos():
    fi = request.args.get("fecha_inicio")
    ff = request.args.get("fecha_fin")
    gid = request.args.get("groomer_id")
    rows = db.session.execute(
        text(
            """
            SELECT g.nombre as groomer,
                   p.nombre as producto,
                   SUM(si.cantidad_entregada) as entregado,
                   SUM(COALESCE(si.cantidad_usada,0)) as usado,
                   SUM(COALESCE(si.cantidad_devuelta,0)) as devuelto,
                   SUM(COALESCE(si.cantidad_desperdicio,0)) as desperdicio,
                   SUM(si.cantidad_entregada) -
                     SUM(COALESCE(si.cantidad_usada,0)) as diferencia
            FROM salida_insumos si
            JOIN groomers g ON si.groomer_id=g.id
            JOIN productos p ON si.producto_id=p.id
            WHERE (:fi IS NULL OR si.entregado_en >= :fi)
              AND (:ff IS NULL OR si.entregado_en <= :ff)
              AND (:gid IS NULL OR si.groomer_id = :gid)
            GROUP BY g.id, g.nombre, p.id, p.nombre
            ORDER BY desperdicio DESC
            """
        ),
        {"fi": fi, "ff": ff, "gid": gid},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows]})


@reportes_bp.get("/cronograma-diario")
@requiere_rol("Admin", "Recepcion")
def cronograma_diario():
    fecha = _parse_date(request.args.get("fecha")) or datetime.now(timezone.utc).date()
    rows = db.session.execute(
        text(
            """
            SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin,
                   c.estado, c.precio_estimado,
                   m.nombre as mascota, m.foto_url,
                   s.nombre as servicio,
                   g.nombre as groomer,
                   cl.nombre as cliente, cl.telefono,
                   CASE WHEN f.id IS NOT NULL THEN 'pagada' ELSE 'pendiente'
                   END as estado_pago
            FROM citas c
            JOIN mascotas m ON c.mascota_id=m.id
            JOIN servicios s ON c.servicio_id=s.id
            LEFT JOIN groomers g ON c.groomer_id=g.id
            JOIN mascota_dueno md ON md.mascota_id=m.id AND md.es_principal=true
            JOIN clientes cl ON md.cliente_id=cl.id
            LEFT JOIN facturas f ON f.cita_id=c.id AND f.estado='pagada'
            WHERE DATE(c.fecha_hora_inicio) = :fecha
              AND c.estado NOT IN ('cancelada','no_asistio')
            ORDER BY c.fecha_hora_inicio ASC
            """
        ),
        {"fecha": fecha},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows]})


@reportes_bp.get("/cancelaciones")
@requiere_rol("Admin", "Recepcion")
def cancelaciones():
    fi = _parse_date(request.args.get("fecha_inicio"))
    ff = _parse_date(request.args.get("fecha_fin"))
    tipo = request.args.get("tipo")
    rows = db.session.execute(
        text(
            """
            SELECT c.id, c.fecha_hora_inicio, c.estado,
                   c.motivo_cancelacion, c.creado_en,
                   m.nombre as mascota,
                   cl.nombre as cliente, cl.telefono,
                   s.nombre as servicio,
                   g.nombre as groomer
            FROM citas c
            JOIN mascotas m ON c.mascota_id=m.id
            JOIN mascota_dueno md ON md.mascota_id=m.id AND md.es_principal=true
            JOIN clientes cl ON md.cliente_id=cl.id
            JOIN servicios s ON c.servicio_id=s.id
            LEFT JOIN groomers g ON c.groomer_id=g.id
            WHERE c.estado IN ('cancelada','no_asistio')
              AND (:fi IS NULL OR DATE(c.fecha_hora_inicio) >= :fi)
              AND (:ff IS NULL OR DATE(c.fecha_hora_inicio) <= :ff)
              AND (:tipo IS NULL OR c.estado = :tipo)
            ORDER BY c.fecha_hora_inicio DESC
            """
        ),
        {"fi": fi, "ff": ff, "tipo": tipo},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows]})


@reportes_bp.get("/inventario-critico")
@requiere_rol("Admin", "Recepcion")
def inventario_critico():
    data = _fetch_view("SELECT * FROM v_inventario_critico")
    return success({"items": data})


@reportes_bp.get("/groomer/productividad")
@requiere_rol("Groomer")
def productividad_groomer():
    usuario, _rol = get_current_user()
    groomer_id = _groomer_id_from_user(usuario)
    if not groomer_id:
        return error("Groomer no encontrado", status=404)
    fi = request.args.get("fecha_inicio")
    ff = request.args.get("fecha_fin")
    row = db.session.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE estado='completada') as servicios_completados,
              COUNT(*) FILTER (WHERE estado='cancelada') as cancelados,
              AVG(duracion_real) FILTER (WHERE estado='completada') as promedio_minutos,
              COUNT(DISTINCT DATE(fecha_hora_inicio)) as dias_trabajados
            FROM citas
            WHERE groomer_id=:gid
              AND (:fi IS NULL OR fecha_hora_inicio >= :fi)
              AND (:ff IS NULL OR fecha_hora_inicio <= :ff)
            """
        ),
        {"gid": groomer_id, "fi": fi, "ff": ff},
    ).mappings().first()
    return success({"data": dict(row) if row else {}})


@reportes_bp.get("/groomer/historial-servicios")
@requiere_rol("Groomer")
def historial_servicios_groomer():
    usuario, _rol = get_current_user()
    groomer_id = _groomer_id_from_user(usuario)
    if not groomer_id:
        return error("Groomer no encontrado", status=404)
    fi = request.args.get("fecha_inicio")
    ff = request.args.get("fecha_fin")
    page = max(int(request.args.get("page") or 1), 1)
    rows = db.session.execute(
        text(
            """
            SELECT c.id, c.fecha_hora_inicio, c.duracion_real,
                   c.estado, m.nombre as mascota, m.raza,
                   s.nombre as servicio,
                   fg.estado_final, fg.observaciones_final,
                   fg.checklist_completo,
                   (SELECT COUNT(*) FROM fotos_ficha ff
                    WHERE ff.ficha_id=fg.id) as total_fotos
            FROM citas c
            JOIN mascotas m ON c.mascota_id=m.id
            JOIN servicios s ON c.servicio_id=s.id
            LEFT JOIN fichas_grooming fg ON fg.cita_id=c.id
            WHERE c.groomer_id=:gid
              AND c.estado='completada'
              AND (:fi IS NULL OR c.fecha_hora_inicio >= :fi)
              AND (:ff IS NULL OR c.fecha_hora_inicio <= :ff)
            ORDER BY c.fecha_hora_inicio DESC
            LIMIT 20 OFFSET :offset
            """
        ),
        {"gid": groomer_id, "fi": fi, "ff": ff, "offset": (page - 1) * 20},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows], "page": page})


@reportes_bp.get("/groomer/consumo-insumos")
@requiere_rol("Groomer")
def consumo_insumos_groomer():
    usuario, _rol = get_current_user()
    groomer_id = _groomer_id_from_user(usuario)
    if not groomer_id:
        return error("Groomer no encontrado", status=404)
    fecha = _parse_date(request.args.get("fecha")) or datetime.now(timezone.utc).date()
    rows = db.session.execute(
        text(
            """
            SELECT p.nombre as producto, p.sku,
                   si.cantidad_entregada, si.cantidad_usada,
                   si.cantidad_devuelta, si.cantidad_desperdicio,
                   si.estado, si.entregado_en,
                   fg.cita_id
            FROM salida_insumos si
            JOIN productos p ON si.producto_id=p.id
            JOIN fichas_grooming fg ON si.ficha_id=fg.id
            WHERE si.groomer_id=:gid
              AND DATE(si.entregado_en) = :fecha
            ORDER BY si.entregado_en DESC
            """
        ),
        {"gid": groomer_id, "fecha": fecha},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows]})


@reportes_bp.get("/cliente/historial-mascota/<int:mascota_id>")
@requiere_rol("Cliente")
def historial_mascota_cliente(mascota_id):
    usuario, _rol = get_current_user()
    cliente = Cliente.query.filter_by(usuario_id=usuario.id).first() if usuario else None
    if not cliente:
        return error("Cliente no encontrado", status=404)
    if not MascotaDueno.query.filter_by(cliente_id=cliente.id, mascota_id=mascota_id).first():
        return error("Mascota no encontrada", status=404)

    rows = db.session.execute(
        text(
            """
            SELECT c.id, c.fecha_hora_inicio, s.nombre as servicio,
                   g.nombre as groomer, c.duracion_real,
                   fg.estado_final, fg.observaciones_final,
                   fg.checklist_completo,
                   f.total as monto_pagado, f.metodo_pago,
                   (SELECT hm.descripcion FROM historial_mascota hm
                    WHERE hm.mascota_id=c.mascota_id
                      AND hm.tipo_evento='recomendacion'
                      AND hm.creado_en::date = c.fecha_hora_inicio::date
                    LIMIT 1) as recomendacion
            FROM citas c
            JOIN servicios s ON c.servicio_id=s.id
            LEFT JOIN groomers g ON c.groomer_id=g.id
            LEFT JOIN fichas_grooming fg ON fg.cita_id=c.id
            LEFT JOIN facturas f ON f.cita_id=c.id AND f.estado='pagada'
            WHERE c.mascota_id=:mid AND c.estado='completada'
            ORDER BY c.fecha_hora_inicio DESC
            """
        ),
        {"mid": mascota_id},
    ).mappings().all()
    return success({"items": [dict(row) for row in rows]})


@reportes_bp.get("/cliente/galeria/<int:mascota_id>")
@requiere_rol("Cliente")
def galeria_cliente(mascota_id):
    usuario, _rol = get_current_user()
    cliente = Cliente.query.filter_by(usuario_id=usuario.id).first() if usuario else None
    if not cliente:
        return error("Cliente no encontrado", status=404)
    if not MascotaDueno.query.filter_by(cliente_id=cliente.id, mascota_id=mascota_id).first():
        return error("Mascota no encontrada", status=404)

    rows = db.session.execute(
        text(
            """
            SELECT c.id as cita_id, c.fecha_hora_inicio, s.nombre as servicio,
                   ff.url, ff.tipo, ff.descripcion
            FROM citas c
            JOIN servicios s ON c.servicio_id=s.id
            JOIN fichas_grooming fg ON fg.cita_id=c.id
            JOIN fotos_ficha ff ON ff.ficha_id=fg.id
            WHERE c.mascota_id=:mid
            ORDER BY c.fecha_hora_inicio DESC, ff.tipo ASC
            """
        ),
        {"mid": mascota_id},
    ).mappings().all()

    agrupado = {}
    for row in rows:
        cita_id = row["cita_id"]
        if cita_id not in agrupado:
            fecha = row["fecha_hora_inicio"].date().isoformat() if row.get("fecha_hora_inicio") else None
            agrupado[cita_id] = {
                "cita_id": cita_id,
                "fecha": fecha,
                "servicio": row.get("servicio"),
                "fotos": {"antes": [], "despues": []},
            }
        if row.get("tipo") == "antes":
            agrupado[cita_id]["fotos"]["antes"].append(row.get("url"))
        else:
            agrupado[cita_id]["fotos"]["despues"].append(row.get("url"))

    return success({"citas": list(agrupado.values())})


@reportes_bp.get("/cliente/puntos")
@requiere_rol("Cliente")
def puntos_cliente():
    usuario, rol = get_current_user()
    cliente = Cliente.query.filter_by(usuario_id=usuario.id).first() if usuario and rol == "Cliente" else None
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
    return success({
        "nivel": nivel,
        "total_visitas": total_visitas,
        "descuento_disponible": descuento,
        "mensaje": mensaje,
        "promociones_activas": [],
    })
