from datetime import datetime, timedelta, timezone

from flask import Blueprint, request

from ..extensions import db
from ..models import Cita, Cliente, Factura, Mascota, MascotaDueno, Notificacion, Pago, Promocion, Servicio, Groomer, Usuario, AuditLog
from ..utils.crear_notificacion import crear_notificacion
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.plantillas_notif import mensaje_pago_registrado
from ..utils.responses import error, success


cobros_bp = Blueprint("cobros_bp", __name__, url_prefix="/api/cobros")


def _resolve_cliente_por_mascota(mascota_id):
    relacion = (
        MascotaDueno.query.filter_by(mascota_id=mascota_id)
        .order_by(MascotaDueno.es_principal.desc())
        .first()
    )
    if not relacion:
        return None
    return Cliente.query.filter_by(id=relacion.cliente_id).first()


def _pendiente_payload(cita):
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    cliente = _resolve_cliente_por_mascota(cita.mascota_id)
    relacion = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id, es_principal=True).first()
    foto_url = mascota.foto_url if mascota else None
    return {
        "cita_id": cita.id,
        "mascota_id": cita.mascota_id,
        "mascota_nombre": mascota.nombre if mascota else None,
        "foto_url": foto_url,
        "cliente_id": cliente.id if cliente else None,
        "cliente_nombre": f"{cliente.nombre} {cliente.apellido or ''}".strip() if cliente else None,
        "telefono": cliente.telefono if cliente else None,
        "precio_estimado": float(cita.precio_estimado) if cita.precio_estimado is not None else 0.0,
        "fecha_hora_inicio": cita.fecha_hora_inicio.isoformat() if cita.fecha_hora_inicio else None,
        "fecha_hora_fin": cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
        "servicio": Servicio.query.filter_by(id=cita.servicio_id).first().nombre if Servicio.query.filter_by(id=cita.servicio_id).first() else None,
        "groomer": f"{Groomer.query.filter_by(id=cita.groomer_id).first().nombre} {Groomer.query.filter_by(id=cita.groomer_id).first().apellido or ''}".strip() if Groomer.query.filter_by(id=cita.groomer_id).first() else None,
        "minutos_espera": max(0, ((datetime.now(timezone.utc) - cita.fecha_hora_fin).total_seconds() / 60) if cita.fecha_hora_fin else 0),
    }


def _formatear_numero_factura(factura):
    if factura.numero:
        return factura.numero
    factura.numero = f"FAC-{int(factura.id):08d}"
    return factura.numero


def _recibo_payload(factura):
    cita = Cita.query.filter_by(id=factura.cita_id).first() if factura.cita_id else None
    cliente = Cliente.query.filter_by(id=factura.cliente_id).first()
    mascota = Mascota.query.filter_by(id=cita.mascota_id).first() if cita else None
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first() if cita else None
    groomer = Groomer.query.filter_by(id=cita.groomer_id).first() if cita else None
    pago = Pago.query.filter_by(factura_id=factura.id, estado="completado").order_by(Pago.fecha_pago.desc()).first()
    usuario = Usuario.query.filter_by(id=pago.registrado_por).first() if pago and pago.registrado_por else None
    return {
        "factura_id": factura.id,
        "factura_numero": factura.numero,
        "fecha_emision": factura.fecha_emision.isoformat() if factura.fecha_emision else None,
        "cliente": f"{cliente.nombre} {cliente.apellido or ''}".strip() if cliente else None,
        "mascota": mascota.nombre if mascota else None,
        "servicio": servicio.nombre if servicio else None,
        "groomer": f"{groomer.nombre} {groomer.apellido or ''}".strip() if groomer else None,
        "subtotal": float(factura.subtotal or 0),
        "descuento": float(factura.descuento or 0),
        "total": float(factura.total or 0),
        "metodo_pago": factura.metodo_pago,
        "referencia_transaccion": pago.referencia_transaccion if pago else None,
        "registrado_por": usuario.email if usuario else None,
        "mensaje": "Pago registrado correctamente",
    }


@cobros_bp.get("/pendientes")
@requiere_rol("Admin", "Recepcion")
def cobros_pendientes():
    citas = Cita.query.filter_by(estado="completada").order_by(Cita.fecha_hora_fin.asc()).all()
    pendientes = []
    for cita in citas:
        if Factura.query.filter_by(cita_id=cita.id, estado="pagada").first():
            continue
        pendientes.append(_pendiente_payload(cita))

    pendientes.sort(key=lambda item: item["minutos_espera"], reverse=True)
    return success({"pendientes": pendientes})


@cobros_bp.post("/<int:cita_id>/pagar")
@requiere_rol("Admin", "Recepcion")
def pagar_cita(cita_id):
    data = request.get_json() or {}
    metodo_pago = data.get("metodo_pago")
    if metodo_pago not in {"efectivo", "qr", "transferencia"}:
        return error("Método de pago inválido. Opciones: efectivo, qr, transferencia", status=422)

    cita = Cita.query.filter_by(id=cita_id).first()
    if not cita:
        return error("Cita no encontrada", status=404)
    if cita.estado != "completada":
        return error("Solo se pueden cobrar citas completadas", status=422)
    if Factura.query.filter_by(cita_id=cita.id, estado="pagada").first():
        return error("La cita ya fue cobrada", status=409)

    cliente = _resolve_cliente_por_mascota(cita.mascota_id)
    if not cliente:
        return error("Cliente no encontrado", status=404)

    subtotal = float(cita.precio_estimado) if cita.precio_estimado is not None else 0.0
    descuento = float(data.get("descuento") or 0) or 0.0
    promocion_id = data.get("promocion_id")
    if promocion_id not in (None, "", 0, "0"):
        promocion = db.session.get(Promocion, int(promocion_id))
        if not promocion:
          return error("Promocion no encontrada", status=404)
        if not promocion.activa:
          return error("Promocion inactiva", status=422)
        hoy = datetime.now(timezone.utc).date()
        if promocion.fecha_inicio and promocion.fecha_inicio > hoy:
            return error("Promocion fuera de vigencia", status=422)
        if promocion.fecha_fin and promocion.fecha_fin < hoy:
            return error("Promocion fuera de vigencia", status=422)
        if promocion.uso_maximo is not None and int(promocion.uso_actual or 0) >= int(promocion.uso_maximo or 0):
            return error("Promocion agotada", status=422)
        if promocion.tipo == "porcentaje":
            descuento = subtotal * (float(promocion.valor) / 100.0)
        else:
            descuento = float(promocion.valor)
    if descuento < 0:
        return error("El descuento no puede ser negativo", status=422)
    total = subtotal - descuento
    if total < 0:
        return error("El descuento supera el subtotal", status=422)

    if metodo_pago in {"qr", "transferencia"} and not data.get("referencia_transaccion"):
        return error("QR y transferencia requieren código de referencia/transacción", status=422)

    usuario, _rol = get_current_user()
    usuario_id = usuario.id if usuario else None

    factura = Factura(
        numero="",
        cita_id=cita.id,
        cliente_id=cliente.id,
        subtotal=subtotal,
        impuesto=0,
        descuento=descuento,
        total=total,
        estado="pendiente",
        metodo_pago=metodo_pago,
        notas=data.get("notas"),
        fecha_emision=datetime.now(timezone.utc),
    )
    db.session.add(factura)
    db.session.flush()
    _formatear_numero_factura(factura)

    pago = Pago(
        factura_id=factura.id,
        monto=total,
        metodo_pago=metodo_pago,
        referencia_transaccion=data.get("referencia_transaccion"),
        estado="completado",
        registrado_por=usuario_id,
    )
    db.session.add(pago)

    factura.estado = "pagada"
    factura.metodo_pago = metodo_pago

    if promocion_id not in (None, "", 0, "0"):
        promocion.uso_actual = int(promocion.uso_actual or 0) + 1

    mascota = Mascota.query.filter_by(id=cita.mascota_id).first()
    servicio = Servicio.query.filter_by(id=cita.servicio_id).first()
    _ = crear_notificacion(
        cita_id=cita.id,
        cliente=cliente,
        tipo_evento="pago_registrado",
        mensaje=mensaje_pago_registrado(
            mascota.nombre if mascota else "Tu mascota",
            servicio.nombre if servicio else "servicio",
            total,
            metodo_pago,
            factura.numero,
        ),
    )

    # crear notificacion tipo encuesta en 2 horas
    try:
        encuesta = Notificacion(
            cita_id=cita.id,
            cliente_id=cliente.id,
            tipo_canal=cliente.canal_notificacion or "email",
            tipo_evento="encuesta",
            destino=cliente.telefono if (cliente.canal_notificacion or "email") in {"whatsapp", "sms"} else cliente.usuario.email,
            mensaje="Por favor, califica nuestro servicio.",
            fecha_programacion=datetime.now(timezone.utc) + timedelta(hours=2),
            estado="pendiente",
        )
        db.session.add(encuesta)
    except Exception:
        pass

    audit = AuditLog(
        tabla="facturas",
        operacion="INSERT",
        registro_id=factura.id,
        datos_despues={
            "factura_numero": factura.numero,
            "subtotal": float(factura.subtotal or 0),
            "descuento": float(factura.descuento or 0),
            "total": float(factura.total or 0),
            "metodo_pago": factura.metodo_pago,
        },
        usuario_id=usuario_id,
    )
    db.session.add(audit)

    db.session.commit()

    return success(_recibo_payload(factura))


@cobros_bp.get("/recibo/<int:factura_id>")
@requiere_rol("Admin", "Recepcion")
def obtener_recibo(factura_id):
    factura = Factura.query.filter_by(id=factura_id).first()
    if not factura:
        return error("Factura no encontrada", status=404)
    if not factura.numero:
        _formatear_numero_factura(factura)
        db.session.commit()
    return success(_recibo_payload(factura))


@cobros_bp.get("/cierre-caja")
@requiere_rol("Admin")
def cierre_caja():
    fecha = request.args.get("fecha") or datetime.now(timezone.utc).date().isoformat()
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
    except Exception:
        return error("fecha invalida", status=400)

    inicio = datetime.combine(fecha_dt, datetime.min.time())
    fin = datetime.combine(fecha_dt, datetime.max.time())

    pagos = (
        Pago.query
        .join(Factura, Pago.factura_id == Factura.id)
        .filter(Pago.fecha_pago >= inicio, Pago.fecha_pago <= fin, Pago.estado == "completado")
        .order_by(Pago.fecha_pago.asc())
        .all()
    )

    detalle = []
    total_efectivo = 0.0
    total_qr = 0.0
    total_transferencia = 0.0
    total_general = 0.0
    for pago in pagos:
        factura = Factura.query.filter_by(id=pago.factura_id).first()
        cita = Cita.query.filter_by(id=factura.cita_id).first() if factura and factura.cita_id else None
        mascota = Mascota.query.filter_by(id=cita.mascota_id).first() if cita else None
        relacion = MascotaDueno.query.filter_by(mascota_id=cita.mascota_id, es_principal=True).first() if cita else None
        cliente = relacion.cliente if relacion else (Cliente.query.filter_by(id=factura.cliente_id).first() if factura else None)
        servicio = Servicio.query.filter_by(id=cita.servicio_id).first() if cita else None
        item = {
            "hora": pago.fecha_pago.strftime("%H:%M") if pago.fecha_pago else None,
            "cliente": f"{cliente.nombre} {cliente.apellido or ''}".strip() if cliente else None,
            "servicio": servicio.nombre if servicio else None,
            "metodo": pago.metodo_pago,
            "monto": float(pago.monto or 0),
            "referencia": pago.referencia_transaccion,
            "factura": factura.numero if factura else None,
        }
        detalle.append(item)
        total_general += float(pago.monto or 0)
        if pago.metodo_pago == "efectivo":
            total_efectivo += float(pago.monto or 0)
        elif pago.metodo_pago == "qr":
            total_qr += float(pago.monto or 0)
        elif pago.metodo_pago == "transferencia":
            total_transferencia += float(pago.monto or 0)

    return success({
        "total_transacciones": len(detalle),
        "total_efectivo": round(total_efectivo, 2),
        "total_qr": round(total_qr, 2),
        "total_transferencia": round(total_transferencia, 2),
        "total_general": round(total_general, 2),
        "detalle": detalle,
    })
