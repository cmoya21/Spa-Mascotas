from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..extensions import db
from ..models import Factura, Pago, Usuario
from ..schemas.facturacion_schema import FacturaSchema, PagoSchema
from ..utils.decorators import requiere_rol
from ..utils.responses import error, success


pagos_bp = Blueprint("pagos_bp", __name__, url_prefix="/api/pagos")


def _coerce_user_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _factura_payload(factura):
    return {
        "id": factura.id,
        "numero": factura.numero,
        "cliente_id": factura.cliente_id,
        "cita_id": factura.cita_id,
        "subtotal": float(factura.subtotal),
        "impuesto": float(factura.impuesto),
        "descuento": float(factura.descuento),
        "total": float(factura.total),
        "estado": factura.estado,
        "metodo_pago": factura.metodo_pago,
    }


@pagos_bp.post("/facturas")
@requiere_rol("Admin", "Recepcion")
def crear_factura():
    try:
        data = FacturaSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    subtotal = data.get("subtotal", 0)
    impuesto = data.get("impuesto") or 0
    descuento = data.get("descuento") or 0
    total = subtotal + impuesto - descuento
    if total < 0:
        return error("Total invalido", status=400)

    numero = f"FAC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    factura = Factura(
        numero=numero,
        cita_id=data.get("cita_id"),
        cliente_id=data["cliente_id"],
        subtotal=subtotal,
        impuesto=impuesto,
        descuento=descuento,
        total=total,
        estado="pendiente",
        metodo_pago=data.get("metodo_pago"),
        notas=data.get("notas"),
    )
    db.session.add(factura)
    db.session.commit()

    return success({"factura": _factura_payload(factura)}, status=201)


@pagos_bp.post("/pagos")
@requiere_rol("Admin", "Recepcion")
def registrar_pago():
    try:
        data = PagoSchema().load(request.get_json() or {})
    except ValidationError as exc:
        return error("Datos invalidos", status=400, details=exc.messages)

    factura = Factura.query.filter_by(id=data["factura_id"]).first()
    if not factura:
        return error("Factura no encontrada", status=404)

    total_pagado = sum(p.monto for p in Pago.query.filter_by(factura_id=factura.id).all())
    if total_pagado + data["monto"] > factura.total:
        return error("Pago excede el total", status=409)

    usuario_id = _coerce_user_id(get_jwt_identity())
    pago = Pago(
        factura_id=factura.id,
        monto=data["monto"],
        metodo_pago=data["metodo_pago"],
        referencia_transaccion=data.get("referencia_transaccion"),
        estado="completado",
        registrado_por=usuario_id,
    )
    db.session.add(pago)

    if total_pagado + data["monto"] >= factura.total:
        factura.estado = "pagada"
        factura.metodo_pago = data["metodo_pago"]

    db.session.commit()
    return success({"pago": {"id": pago.id, "factura_id": pago.factura_id}}, status=201)


@pagos_bp.get("/facturas")
@requiere_rol("Admin", "Recepcion")
def listar_facturas():
    facturas = Factura.query.order_by(Factura.fecha_emision.desc()).limit(200).all()
    return success({"facturas": [_factura_payload(item) for item in facturas]})
