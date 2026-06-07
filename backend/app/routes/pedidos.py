from urllib.parse import quote

from flask import Blueprint, request

from ..extensions import db
from ..models import Cliente, DetalleCarrito, Pedido, Producto
from ..utils.decorators import requiere_rol
from ..utils.responses import error, success


pedidos_bp = Blueprint("pedidos_bp", __name__, url_prefix="/api/pedidos")


def _format_bs(value):
    return f"Bs.{value:.2f}"


def _sanitize_phone(value):
    if not value:
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 8:
        return f"591{digits}"
    return digits


def _build_message(items, total):
    lines = ["Hola! Mi pedido:"]
    for item in items:
        lines.append(f"- {item['cantidad']}x {item['nombre']} - {_format_bs(item['subtotal'])}")
    lines.append(f"TOTAL: {_format_bs(total)}")
    return "\n".join(lines)


def _build_link(phone, message, metodo_contacto):
    encoded = quote(message)
    if metodo_contacto == "telegram":
        return f"https://t.me/share/url?text={encoded}"
    return f"https://wa.me/{phone}?text={encoded}"


def _get_carrito_items(carrito_id):
    detalles = DetalleCarrito.query.filter_by(carrito_id=carrito_id).all()
    producto_ids = [item.producto_id for item in detalles]
    productos = Producto.query.filter(Producto.id.in_(producto_ids)).all() if producto_ids else []
    productos_map = {item.id: item.nombre for item in productos}

    items = []
    total = 0
    for detalle in detalles:
        nombre = productos_map.get(detalle.producto_id, "Producto")
        subtotal = float(detalle.precio_unitario) * int(detalle.cantidad)
        items.append({
            "producto_id": detalle.producto_id,
            "nombre": nombre,
            "cantidad": int(detalle.cantidad),
            "subtotal": subtotal,
        })
        total += subtotal

    return items, total


@pedidos_bp.post("/<int:pedido_id>/enviar")
@requiere_rol("Admin", "Recepcion", "Cliente")
def enviar_pedido(pedido_id):
    pedido = Pedido.query.filter_by(id=pedido_id).first()
    if not pedido:
        return error("Pedido no encontrado", status=404)

    if not pedido.carrito_id:
        return error("Pedido sin carrito", status=400)

    items, total = _get_carrito_items(pedido.carrito_id)
    if not items:
        return error("Carrito vacio", status=400)

    body = request.get_json() or {}
    telefono = body.get("telefono")
    if not telefono and pedido.cliente_id:
        cliente = Cliente.query.filter_by(id=pedido.cliente_id).first()
        telefono = cliente.telefono if cliente else None

    telefono = _sanitize_phone(telefono)
    if not telefono:
        return error("Telefono requerido", status=422)

    metodo = body.get("metodo_contacto") or pedido.metodo_contacto or "whatsapp"
    mensaje = _build_message(items, total)
    link = _build_link(telefono, mensaje, metodo)

    pedido.link_contacto = link
    pedido.estado = "enviado"
    pedido.metodo_contacto = metodo
    db.session.commit()

    return success({
        "mensaje": mensaje,
        "link_contacto": link,
        "total": float(total),
    })
