from datetime import date, datetime

from flask import Blueprint, request

from ..extensions import db
from ..models import Cita, Cliente, MascotaDueno, Promocion
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.responses import error, success


promociones_bp = Blueprint("promociones_bp", __name__, url_prefix="/api/promociones")


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _promotion_active(promo):
    hoy = date.today()
    if not promo.activa:
        return False
    if promo.fecha_inicio and promo.fecha_inicio > hoy:
        return False
    if promo.fecha_fin and promo.fecha_fin < hoy:
        return False
    return True


def _promo_status(promo):
    hoy = date.today()
    if promo.fecha_fin and promo.fecha_fin < hoy:
        return "Vencida"
    return "Activa" if promo.activa else "Inactiva"


def _calcular_descuento(promo, subtotal):
    subtotal = float(subtotal or 0)
    if promo.tipo == "porcentaje":
        descuento = subtotal * (float(promo.valor or 0) / 100.0)
    else:
        descuento = min(float(promo.valor or 0), subtotal)
    return round(descuento, 2)


def _serialize(item):
    return {
        "id": item.id,
        "nombre": item.nombre,
        "descripcion": item.descripcion,
        "tipo": item.tipo,
        "valor": float(item.valor or 0),
        "fecha_inicio": item.fecha_inicio.isoformat() if item.fecha_inicio else None,
        "fecha_fin": item.fecha_fin.isoformat() if item.fecha_fin else None,
        "activa": bool(item.activa),
        "estado": _promo_status(item),
        "creado_en": item.creado_en.isoformat() if item.creado_en else None,
    }


@promociones_bp.get("")
def listar_promociones():
    hoy = date.today()
    promociones = (
        Promocion.query.filter(
            Promocion.activa.is_(True),
            (Promocion.fecha_inicio.is_(None) | (Promocion.fecha_inicio <= hoy)),
            (Promocion.fecha_fin.is_(None) | (Promocion.fecha_fin >= hoy)),
        )
        .order_by(Promocion.creado_en.desc())
        .all()
    )
    return [_serialize(item) for item in promociones]


@promociones_bp.post("")
@requiere_rol("Admin")
def crear_promocion():
    data = request.get_json() or {}
    nombre = str(data.get("nombre", "")).strip()
    tipo = str(data.get("tipo", "")).strip()
    descripcion = data.get("descripcion")
    valor_raw = data.get("valor")

    if not nombre:
        return error("nombre requerido", status=422)
    if tipo not in {"porcentaje", "monto_fijo"}:
        return error("Tipo invalido. Opciones: porcentaje, monto_fijo", status=422)

    try:
        valor = float(valor_raw)
    except (TypeError, ValueError):
        return error("valor invalido", status=422)
    if valor <= 0:
        return error("valor invalido", status=422)
    if tipo == "porcentaje" and valor > 100:
        return error("El porcentaje no puede ser mayor a 100", status=422)

    fecha_inicio = _parse_date(data.get("fecha_inicio"))
    fecha_fin = _parse_date(data.get("fecha_fin"))
    if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
        return error("fecha_fin no puede ser menor que fecha_inicio", status=422)

    promocion = Promocion(
        nombre=nombre,
        descripcion=descripcion,
        tipo=tipo,
        valor=valor,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        activa=bool(data.get("activa", True)),
    )
    db.session.add(promocion)
    db.session.commit()
    return _serialize(promocion), 201


@promociones_bp.patch("/<int:promocion_id>/toggle")
@requiere_rol("Admin")
def toggle_promocion(promocion_id):
    promocion = db.session.get(Promocion, promocion_id)
    if not promocion:
        return error("Promocion no encontrada", status=404)

    promocion.activa = not bool(promocion.activa)
    db.session.commit()
    return {"id": promocion.id, "activa": bool(promocion.activa)}


@promociones_bp.post("/validar-cupon")
def validar_cupon():
    data = request.get_json() or {}
    try:
        subtotal = float(data.get("subtotal") or 0)
    except (TypeError, ValueError):
        return error("subtotal invalido", status=422)

    hoy = date.today()
    promo = Promocion.query.filter(
        Promocion.activa.is_(True),
        (Promocion.fecha_inicio.is_(None) | (Promocion.fecha_inicio <= hoy)),
        (Promocion.fecha_fin.is_(None) | (Promocion.fecha_fin >= hoy)),
    ).first()
    
    if not promo:
        return error("No hay cupones disponibles", status=404)

    descuento = _calcular_descuento(promo, subtotal)
    total = round(max(0, subtotal - descuento), 2)
    return {
        "promocion_id": promo.id,
        "nombre": promo.nombre,
        "tipo": promo.tipo,
        "valor": float(promo.valor or 0),
        "descuento_calculado": descuento,
        "subtotal_original": round(subtotal, 2),
        "total_con_descuento": total,
    }


@promociones_bp.post("/<int:promocion_id>/aplicar-a-factura")
@requiere_rol("Admin", "Recepcion")
def aplicar_a_factura(promocion_id):
    data = request.get_json() or {}
    factura_id = data.get("factura_id")
    if not factura_id:
        return error("factura_id requerido", status=422)

    from ..models import Factura

    factura = db.session.get(Factura, int(factura_id))
    if not factura:
        return error("Factura no encontrada", status=404)
    if factura.estado == "pagada":
        return error("Factura ya pagada", status=409)

    promo = db.session.get(Promocion, promocion_id)
    if not promo:
        return error("Promocion no encontrada", status=404)
    if not _promotion_active(promo):
        return error("Promocion inactiva o vencida", status=422)

    descuento = _calcular_descuento(promo, factura.subtotal)
    factura.descuento = descuento
    factura.total = round(float(factura.subtotal or 0) + float(factura.impuesto or 0) - descuento, 2)
    db.session.commit()
    return {
        "factura_id": factura.id,
        "subtotal": float(factura.subtotal or 0),
        "impuesto": float(factura.impuesto or 0),
        "descuento": float(factura.descuento or 0),
        "total": float(factura.total or 0),
    }


@promociones_bp.get("/clientes/me/beneficios-frecuente")
@requiere_rol("Cliente")
def beneficios_frecuente():
    usuario, rol = get_current_user()
    cliente = Cliente.query.filter_by(usuario_id=usuario.id).first() if usuario and rol == "Cliente" else None
    if not cliente:
        return error("Cliente no encontrado", status=404)

    from ..models import Mascota

    total_visitas = (
        db.session.query(Cita.id)
        .join(Mascota, Mascota.id == Cita.mascota_id)
        .join(MascotaDueno, MascotaDueno.mascota_id == Mascota.id)
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
