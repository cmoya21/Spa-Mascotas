from flask import Blueprint

from ..models import Producto
from ..utils.decorators import requiere_rol
from ..utils.responses import success


inventario_bp = Blueprint("inventario_bp", __name__, url_prefix="/api/inventario")


def _producto_payload(item):
    return {
        "id": item.id,
        "nombre": item.nombre,
        "sku": item.sku,
        "stock": item.stock,
        "stock_minimo": item.stock_minimo,
    }


@inventario_bp.get("/alertas")
@requiere_rol("Admin", "Recepcion")
def alertas_inventario():
    productos = Producto.query.filter(Producto.stock <= Producto.stock_minimo).all()
    return success({"alertas": [_producto_payload(item) for item in productos]})


@inventario_bp.get("/productos")
@requiere_rol("Admin", "Recepcion", "Groomer")
def listar_productos():
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre.asc()).all()
    return success({"productos": [_producto_payload(item) for item in productos]})
