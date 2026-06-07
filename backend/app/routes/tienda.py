import os
import uuid
from datetime import date, datetime, timedelta, timezone
from math import ceil
from urllib.parse import quote

from flask import Blueprint, abort, current_app, jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    AuditLog,
    Carrito,
    CategoriaProducto,
    Cliente,
    DetalleCarrito,
    DetallePedido,
    Mascota,
    MascotaDueno,
    Pedido,
    Producto,
    Promocion,
    Usuario,
    VarianteProducto,
)
from ..utils.decorators import get_current_user, requiere_rol
from ..utils.responses import error, success


tienda_bp = Blueprint("tienda_bp", __name__, url_prefix="/api")


def _producto_payload(producto):
    categoria = getattr(producto, "categoria", None)
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "sku": producto.sku,
        "precio_base": float(producto.precio_base or 0),
        "stock": int(producto.stock or 0),
        "stock_minimo": int(producto.stock_minimo or 0),
        "imagen_url": producto.imagen_url,
        "categoria_id": producto.categoria_id,
        "categoria_nombre": categoria.nombre if categoria else None,
        "variantes": [
            {
                "id": variante.id,
                "atributo": variante.atributo,
                "valor": variante.valor,
                "precio_extra": float(variante.precio_extra or 0),
                "stock": int(variante.stock or 0),
                "sku_variante": variante.sku_variante,
                "precio_total": float(producto.precio_base or 0) + float(variante.precio_extra or 0),
            }
            for variante in getattr(producto, "variantes", [])
        ],
        "activo": bool(producto.activo),
    }


def _categoria_payload(categoria):
    return {
        "id": categoria.id,
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion,
        "total_productos": getattr(categoria, "total_productos", None),
    }


def _normalizar_bool_query(value):
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "si", "on"}:
        return True
    if text in {"0", "false", "f", "no", "off"}:
        return False
    return None


def _producto_query_base():
    return Producto.query.options(selectinload(Producto.categoria), selectinload(Producto.variantes))


def _producto_filtrado_query(categoria=None, q=None, activo=None):
    query = _producto_query_base().outerjoin(CategoriaProducto, Producto.categoria_id == CategoriaProducto.id)
    if activo is not None:
        query = query.filter(Producto.activo.is_(activo))
    if categoria is not None:
        query = query.filter(Producto.categoria_id == categoria)
    if q:
        like = f"%{q}%"
        query = query.filter((Producto.nombre.ilike(like)) | (Producto.descripcion.ilike(like)))
    return query


def _serialize_paginated_productos(productos, total, pagina, por_pagina):
    return {
        "productos": [_producto_payload(item) for item in productos],
        "total": int(total),
        "pagina": int(pagina),
        "por_pagina": int(por_pagina),
        "total_paginas": int(ceil(total / por_pagina)) if por_pagina else 0,
    }


def _recomendar_productos_para_mascota(mascota, productos, max_resultados=6):
    from ..utils.recomendador import recomendar_productos

    recomendaciones_ia = None
    if mascota is not None:
        from ..utils.recomendador_ia import recomendar_productos_con_claude

        recomendaciones_ia = recomendar_productos_con_claude(mascota, productos, max_resultados=max_resultados)

    productos_por_id = {producto.id: producto for producto in productos}
    recomendaciones = []

    if recomendaciones_ia:
        for item in recomendaciones_ia:
            producto = productos_por_id.get(item.get("producto_id"))
            if not producto:
                continue
            recomendaciones.append({
                "producto": _producto_payload(producto),
                "score": 100,
                "razones": [item.get("razon") or "Recomendado por IA"],
                "fuente": "ia",
            })
        if recomendaciones:
            return recomendaciones[:max_resultados]

    if mascota is None:
        fallback = [
            {"producto": _producto_payload(producto), "score": 0, "razones": ["Más vendido o disponible"], "fuente": "popular"}
            for producto in sorted(productos, key=lambda item: (int(item.stock or 0), item.nombre.lower()), reverse=True)
        ]
        return fallback[:max_resultados]

    for item in recomendar_productos(mascota, productos, max_resultados=max_resultados):
        recomendaciones.append({
            "producto": _producto_payload(item["producto"]),
            "score": item["score"],
            "razones": item["razones"],
            "fuente": "reglas",
        })

    if not recomendaciones:
        fallback = [
            {"producto": _producto_payload(producto), "score": 0, "razones": ["Disponible en tienda"], "fuente": "popular"}
            for producto in sorted(productos, key=lambda item: (int(item.stock or 0), item.nombre.lower()), reverse=True)
        ]
        return fallback[:max_resultados]

    return recomendaciones[:max_resultados]


def _validar_producto_payload(data, existing=None):
    nombre = (data.get("nombre") or "").strip()
    sku = (data.get("sku") or "").strip()
    if not nombre:
        return None, error("nombre es requerido", status=422)
    if not sku:
        return None, error("sku es requerido", status=422)
    try:
        precio_base = float(data.get("precio_base"))
    except (TypeError, ValueError):
        return None, error("precio_base debe ser numérico", status=422)
    if precio_base < 0:
        return None, error("precio_base no puede ser negativo", status=422)
    try:
        stock = int(data.get("stock"))
    except (TypeError, ValueError):
        return None, error("stock debe ser entero", status=422)
    if stock < 0:
        return None, error("stock no puede ser negativo", status=422)
    try:
        stock_minimo = int(data.get("stock_minimo", 0))
    except (TypeError, ValueError):
        return None, error("stock_minimo debe ser entero", status=422)
    if stock_minimo < 0:
        return None, error("stock_minimo no puede ser negativo", status=422)

    categoria_id = data.get("categoria_id")
    if categoria_id in ("", None):
        categoria_id = None
    else:
        try:
            categoria_id = int(categoria_id)
        except (TypeError, ValueError):
            return None, error("categoria_id inválido", status=422)
        if not CategoriaProducto.query.filter_by(id=categoria_id).first():
            return None, error("Categoría no encontrada", status=422)

    imagen_url = data.get("imagen_url")

    existing_sku = Producto.query.filter(Producto.sku == sku)
    if existing:
        existing_sku = existing_sku.filter(Producto.id != existing.id)
    if existing_sku.first():
        return None, error("SKU ya existe", status=422)

    return {
        "nombre": nombre,
        "descripcion": data.get("descripcion"),
        "sku": sku,
        "precio_base": precio_base,
        "stock": stock,
        "stock_minimo": stock_minimo,
        "categoria_id": categoria_id,
        "imagen_url": imagen_url,
        "activo": bool(data.get("activo", True)),
    }, None


def _stock_adjust_core(producto, payload):
    if not producto:
        return None, error("Producto no encontrado", status=404)
    try:
        cantidad = float(payload.get("cantidad"))
    except (TypeError, ValueError):
        return None, error("cantidad invalida", status=422)
    operacion = (payload.get("operacion") or "agregar").strip().lower()
    if operacion not in {"agregar", "establecer"}:
        return None, error("operacion invalida", status=422)

    stock_anterior = float(producto.stock or 0)
    if operacion == "agregar":
        stock_nuevo = stock_anterior + cantidad
    else:
        stock_nuevo = cantidad
    if stock_nuevo < 0:
        return None, error("El stock no puede ser negativo", status=422)

    producto.stock = stock_nuevo
    audit = AuditLog(
        tabla="productos",
        operacion="UPDATE",
        registro_id=producto.id,
        datos_despues={
            "accion": "ajuste_stock",
            "operacion": operacion,
            "cantidad": cantidad,
            "stock_anterior": stock_anterior,
            "stock_nuevo": stock_nuevo,
            "notas": payload.get("notas"),
        },
        usuario_id=get_current_user()[0].id if get_current_user()[0] else None,
    )
    db.session.add(audit)
    db.session.commit()
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "stock_anterior": stock_anterior,
        "stock_nuevo": stock_nuevo,
        "stock": stock_nuevo,
    }, None


def _coerce_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(field_name)


def _coerce_optional_int(value):
    if value in (None, "", "null"):
        return None
    return _coerce_int(value, "optional")


def _cliente_actual():
    usuario, rol = get_current_user()
    if not usuario or rol != "Cliente":
        return None, None
    cliente = Cliente.query.filter_by(usuario_id=usuario.id).first()
    if not cliente:
        return None, None
    return usuario, cliente


def _carrito_activo_o_crear(cliente_id):
    ahora = datetime.now(timezone.utc)
    carrito = (
        Carrito.query.filter(Carrito.cliente_id == cliente_id, Carrito.expires_at > ahora)
        .order_by(Carrito.creado_en.desc())
        .first()
    )
    if carrito:
        return carrito

    carrito = Carrito(
        cliente_id=cliente_id,
        session_token=uuid.uuid4(),
        expires_at=ahora + timedelta(days=7),
    )
    db.session.add(carrito)
    db.session.flush()
    return carrito


def _obtener_datos_item_carrito(carrito_id):
    filas = (
        db.session.query(DetalleCarrito, Producto, VarianteProducto)
        .join(Producto, DetalleCarrito.producto_id == Producto.id)
        .outerjoin(VarianteProducto, DetalleCarrito.variante_id == VarianteProducto.id)
        .filter(DetalleCarrito.carrito_id == carrito_id)
        .order_by(DetalleCarrito.id.asc())
        .all()
    )
    items = []
    total_items = 0
    subtotal = 0.0
    for detalle, producto, variante in filas:
        precio_unitario = float(detalle.precio_unitario or 0)
        cantidad = int(detalle.cantidad or 0)
        item_subtotal = round(precio_unitario * cantidad, 2)
        stock_disponible = int(variante.stock if variante else producto.stock or 0)
        items.append(
            {
                "id": detalle.id,
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "imagen_url": producto.imagen_url,
                "variante_id": variante.id if variante else None,
                "variante_label": f"{variante.atributo}: {variante.valor}" if variante else None,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": item_subtotal,
                "stock_disponible": stock_disponible,
            }
        )
        total_items += cantidad
        subtotal += item_subtotal
    return items, total_items, round(subtotal, 2)


def _serializar_carrito(carrito):
    items, total_items, subtotal = _obtener_datos_item_carrito(carrito.id)
    return {
        "id": carrito.id,
        "items": items,
        "total_items": total_items,
        "subtotal": subtotal,
        "expires_at": carrito.expires_at.astimezone(timezone.utc).isoformat() if carrito.expires_at else None,
    }


def _obtener_producto_variante(producto_id, variante_id=None):
    producto = Producto.query.filter_by(id=producto_id, activo=True).first()
    if not producto:
        return None, None, error("Producto no encontrado", status=422)

    variante = None
    if variante_id is not None:
        variante = VarianteProducto.query.filter_by(id=variante_id, producto_id=producto.id).first()
        if not variante:
            return None, None, error("Variante no encontrada", status=422)

    return producto, variante, None


def _stock_disponible(producto, variante=None):
    return int(variante.stock if variante is not None else producto.stock or 0)


def _precio_unitario(producto, variante=None):
    base = float(producto.precio_base or 0)
    return round(base + float(variante.precio_extra or 0), 2) if variante else round(base, 2)


def _item_por_producto_variante(carrito_id, producto_id, variante_id):
    return DetalleCarrito.query.filter_by(
        carrito_id=carrito_id,
        producto_id=producto_id,
        variante_id=variante_id,
    ).first()


def _mensaje_whatsapp(cliente, items, subtotal):
    lineas = "\n".join(
        [f"• {item['cantidad']}x {item['nombre']} — Bs.{item['subtotal']:.2f}" for item in items]
    )
    apellido = cliente.apellido or ""
    nombre_completo = f"{cliente.nombre} {apellido}".strip()
    mensaje = (
        f"Hola, quisiera hacer el siguiente pedido:\n\n"
        f"{lineas}\n\n"
        f"*SUBTOTAL: Bs.{subtotal:.2f}*\n\n"
        f"Nombre: {nombre_completo}\n"
        f"Teléfono: {cliente.telefono or 'No registrado'}"
    )
    return mensaje


def _calcular_descuento_promocion(promocion, subtotal):
    subtotal = float(subtotal or 0)
    if promocion.tipo == "porcentaje":
        return round(subtotal * (float(promocion.valor or 0) / 100.0), 2)
    return round(min(float(promocion.valor or 0), subtotal), 2)


def _ordenar_pedido_desde_carrito(carrito, cliente, promocion_id=None):
    items, _, subtotal = _obtener_datos_item_carrito(carrito.id)
    if not items:
        return None, error("El carrito está vacío", status=422)

    promocion = None
    descuento = 0.0
    if promocion_id not in (None, "", 0, "0"):
        promocion = Promocion.query.filter_by(id=int(promocion_id)).first()
        if not promocion or not promocion.activa:
            return None, error("Promoción inválida o inactiva", status=422)
        hoy = date.today()
        if promocion.fecha_inicio and promocion.fecha_inicio > hoy:
            return None, error("Promoción inválida o inactiva", status=422)
        if promocion.fecha_fin and promocion.fecha_fin < hoy:
            return None, error("Promoción inválida o inactiva", status=422)
        if promocion.uso_maximo is not None and int(promocion.uso_actual or 0) >= int(promocion.uso_maximo or 0):
            return None, error("Promoción agotada", status=422)
        if promocion.aplica_a not in {"todo", "productos", "cliente_frecuente"}:
            return None, error("Promoción no aplicable al carrito", status=422)
        descuento = _calcular_descuento_promocion(promocion, subtotal)

    total = round(max(0, subtotal - descuento), 2)
    lineas = "\n".join([f"• {item['cantidad']}x {item['nombre']} — Bs.{item['subtotal']:.2f}" for item in items])
    mensaje_wa = (
        f"Hola, quisiera hacer el siguiente pedido:\n\n"
        f"{lineas}\n\n"
        f"*SUBTOTAL: Bs.{subtotal:.2f}*\n"
    )
    if promocion and descuento > 0:
        mensaje_wa += f"*DESCUENTO ({promocion.nombre}): -Bs.{descuento:.2f}*\n"
    mensaje_wa += (
        f"*TOTAL: Bs.{total:.2f}*\n\n"
        f"Nombre: {cliente.nombre} {cliente.apellido or ''}\n"
        f"Teléfono: {cliente.telefono or 'No registrado'}"
    )
    numero = os.environ.get("WHATSAPP_SPA_NUMBER", "59170000000")
    link_wa = f"https://wa.me/{numero}?text={quote(mensaje_wa)}"
    telegram_url = os.environ.get("TELEGRAM_SPA_URL", "")
    link_tg = f"{telegram_url}?start=pedido_{carrito.id}" if telegram_url else None

    pedido = Pedido(
        carrito_id=carrito.id,
        cliente_id=cliente.id,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
        metodo_contacto="whatsapp",
        link_contacto=link_wa,
        estado="pendiente",
    )
    db.session.add(pedido)
    db.session.flush()

    for item in items:
        db.session.add(
            DetallePedido(
                pedido_id=pedido.id,
                producto_id=item["producto_id"],
                variante_id=item["variante_id"],
                cantidad=item["cantidad"],
                precio_unitario=item["precio_unitario"],
            )
        )

    db.session.commit()
    return {
        "pedido_id": pedido.id,
        "link_whatsapp": link_wa,
        "link_telegram": link_tg,
        "mensaje_preview": mensaje_wa,
        "items": items,
        "subtotal": subtotal,
        "descuento": descuento,
        "total": total,
        "promocion_id": promocion.id if promocion else None,
    }, None


def _reabastecer_core(producto_id, data):
    cantidad_raw = data.get("cantidad", data.get("cantidad_ingresada"))
    try:
        cantidad_ingresada = float(cantidad_raw)
    except (TypeError, ValueError):
        return None, error("cantidad invalida", status=422)
    if cantidad_ingresada <= 0:
        return None, error("cantidad invalida", status=422)

    producto = Producto.query.filter_by(id=producto_id).first()
    if not producto:
        return None, error("Producto no encontrado", status=404)

    stock_actual = float(producto.stock or 0)
    producto.stock = stock_actual + cantidad_ingresada
    usuario, _rol = get_current_user()
    audit = AuditLog(
        tabla="productos",
        operacion="UPDATE",
        registro_id=producto.id,
        datos_despues={
            "accion": "reabastecimiento",
            "cantidad_ingresada": cantidad_ingresada,
            "stock_nuevo": float(producto.stock or 0),
            "notas": data.get("notas"),
        },
        usuario_id=usuario.id if usuario else None,
    )
    db.session.add(audit)
    db.session.commit()
    return producto, None


@tienda_bp.get("/categorias")
def listar_categorias_publicas():
    categorias = (
        db.session.query(
            CategoriaProducto,
            func.count(Producto.id).label("total_productos"),
        )
        .outerjoin(Producto, (Producto.categoria_id == CategoriaProducto.id) & Producto.activo.is_(True))
        .group_by(CategoriaProducto.id)
        .order_by(CategoriaProducto.nombre.asc())
        .all()
    )
    return jsonify([
        {
            "id": categoria.id,
            "nombre": categoria.nombre,
            "descripcion": categoria.descripcion,
            "total_productos": int(total_productos or 0),
        }
        for categoria, total_productos in categorias
    ])


@tienda_bp.get("/productos")
def listar_productos_publicos():
    categoria = request.args.get("categoria", type=int)
    q = (request.args.get("q") or "").strip()
    activo = _normalizar_bool_query(request.args.get("activo"))
    pagina = max(request.args.get("page", default=1, type=int) or 1, 1)
    por_pagina = min(max(request.args.get("per_page", default=20, type=int) or 20, 1), 100)

    query = _producto_filtrado_query(categoria=categoria, q=q, activo=activo)
    total = query.count()
    productos = (
        query.order_by(CategoriaProducto.nombre.asc().nullslast(), Producto.nombre.asc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    return jsonify(_serialize_paginated_productos(productos, total, pagina, por_pagina))


@tienda_bp.get("/productos/<int:producto_id>")
def obtener_producto(producto_id):
    producto = Producto.query.options(
        selectinload(Producto.categoria),
        selectinload(Producto.variantes),
    ).filter_by(id=producto_id, activo=True).first()
    if not producto:
        abort(404)
    return jsonify(_producto_payload(producto))


@tienda_bp.get("/productos/recomendados")
def recomendar_productos_publicos():
    mascota_id = request.args.get("mascota_id", type=int)
    productos = (
        _producto_query_base()
        .filter(Producto.activo.is_(True), Producto.stock > 0)
        .order_by(CategoriaProducto.nombre.asc().nullslast(), Producto.nombre.asc())
        .all()
    )
    mascota = None
    if mascota_id:
        mascota = Mascota.query.filter_by(id=mascota_id).first()
    recomendaciones = _recomendar_productos_para_mascota(mascota, productos)
    return jsonify({
        "mascota_id": mascota.id if mascota else None,
        "mascota_nombre": mascota.nombre if mascota else None,
        "recomendaciones": recomendaciones,
    })


@tienda_bp.get("/productos/publicos")
def listar_productos_publicos_alias():
    return listar_productos_publicos()


@tienda_bp.post("/productos")
@requiere_rol("Admin")
def crear_producto():
    data = request.get_json() or {}
    payload, err = _validar_producto_payload(data)
    if err:
        return err
    producto = Producto(**payload)
    db.session.add(producto)
    db.session.commit()
    producto = Producto.query.options(
        selectinload(Producto.categoria),
        selectinload(Producto.variantes),
    ).filter_by(id=producto.id).first()
    return jsonify(_producto_payload(producto)), 201


@tienda_bp.put("/productos/<int:producto_id>")
@requiere_rol("Admin")
def actualizar_producto(producto_id):
    producto = Producto.query.filter_by(id=producto_id).first()
    if not producto:
        abort(404)
    data = request.get_json() or {}
    merged = {
        "nombre": data.get("nombre", producto.nombre),
        "descripcion": data.get("descripcion", producto.descripcion),
        "sku": data.get("sku", producto.sku),
        "precio_base": data.get("precio_base", float(producto.precio_base or 0)),
        "stock": data.get("stock", int(producto.stock or 0)),
        "stock_minimo": data.get("stock_minimo", int(producto.stock_minimo or 0)),
        "categoria_id": data.get("categoria_id", producto.categoria_id),
        "imagen_url": data.get("imagen_url", producto.imagen_url),
        "activo": data.get("activo", producto.activo),
    }
    payload, err = _validar_producto_payload(merged, existing=producto)
    if err:
        return err
    for key, value in payload.items():
        setattr(producto, key, value)
    db.session.commit()
    producto = Producto.query.options(
        selectinload(Producto.categoria),
        selectinload(Producto.variantes),
    ).filter_by(id=producto.id).first()
    return jsonify(_producto_payload(producto))


@tienda_bp.patch("/productos/<int:producto_id>/stock")
@requiere_rol("Admin")
def ajustar_stock_producto(producto_id):
    producto = Producto.query.filter_by(id=producto_id).first()
    data = request.get_json() or {}
    payload, err = _stock_adjust_core(producto, data)
    if err:
        return err
    return jsonify(payload)


@tienda_bp.post("/productos/<int:producto_id>/variantes")
@requiere_rol("Admin")
def crear_variante_producto(producto_id):
    producto = Producto.query.filter_by(id=producto_id).first()
    if not producto:
        abort(404)
    data = request.get_json() or {}
    atributo = (data.get("atributo") or "").strip()
    valor = (data.get("valor") or "").strip()
    sku_variante = (data.get("sku_variante") or "").strip()
    if not atributo or not valor or not sku_variante:
        return error("atributo, valor y sku_variante son requeridos", status=422)
    if VarianteProducto.query.filter_by(sku_variante=sku_variante).first():
        return error("SKU variante ya existe", status=422)
    try:
        precio_extra = float(data.get("precio_extra", 0))
        stock = int(data.get("stock", 0))
    except (TypeError, ValueError):
        return error("Datos de variante inválidos", status=422)
    variante = VarianteProducto(
        producto_id=producto.id,
        atributo=atributo,
        valor=valor,
        precio_extra=precio_extra,
        stock=stock,
        sku_variante=sku_variante,
    )
    db.session.add(variante)
    db.session.commit()
    return jsonify({
        "id": variante.id,
        "producto_id": variante.producto_id,
        "atributo": variante.atributo,
        "valor": variante.valor,
        "precio_extra": float(variante.precio_extra or 0),
        "stock": int(variante.stock or 0),
        "sku_variante": variante.sku_variante,
    }), 201


@tienda_bp.post("/productos/<int:producto_id>/imagen")
@requiere_rol("Admin")
def subir_imagen_producto(producto_id):
    producto = Producto.query.filter_by(id=producto_id).first()
    if not producto:
        abort(404)
    archivo = request.files.get("imagen")
    if not archivo or not archivo.filename:
        return error("imagen es requerida", status=422)
    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        return error("Formato de imagen invalido", status=422)
    archivo.stream.seek(0, os.SEEK_END)
    tamaño = archivo.stream.tell()
    archivo.stream.seek(0)
    if tamaño > 5 * 1024 * 1024:
        return error("La imagen excede 5MB", status=422)

    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], "productos")
    os.makedirs(carpeta, exist_ok=True)
    nombre_archivo = f"{producto.id}_{int(datetime.now(timezone.utc).timestamp())}{ext}"
    ruta = os.path.join(carpeta, secure_filename(nombre_archivo))
    archivo.save(ruta)
    url = f"/uploads/productos/{os.path.basename(ruta)}"
    producto.imagen_url = url
    db.session.commit()
    return jsonify({"imagen_url": url})


@tienda_bp.get("/carrito/me")
@requiere_rol("Cliente")
def obtener_carrito_mi():
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    carrito = _carrito_activo_o_crear(cliente.id)
    return jsonify(_serializar_carrito(carrito))


@tienda_bp.post("/carrito/me/items")
@requiere_rol("Cliente")
def agregar_item_carrito():
    data = request.get_json() or {}
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    try:
        producto_id = _coerce_int(data.get("producto_id"), "producto_id")
        cantidad = _coerce_int(data.get("cantidad", 1), "cantidad")
        variante_id = _coerce_optional_int(data.get("variante_id"))
    except ValueError:
        return error("producto_id, variante_id y cantidad inválidos", status=422)

    if cantidad <= 0:
        return error("cantidad invalida", status=422)

    producto, variante, err = _obtener_producto_variante(producto_id, variante_id)
    if err:
        return err

    stock_disponible = _stock_disponible(producto, variante)
    precio_unitario = _precio_unitario(producto, variante)

    carrito = _carrito_activo_o_crear(cliente.id)
    detalle = _item_por_producto_variante(carrito.id, producto.id, variante.id if variante else None)
    cantidad_actual = int(detalle.cantidad or 0) if detalle else 0
    if cantidad_actual + cantidad > stock_disponible:
        return error(f"Stock insuficiente. Disponible: {stock_disponible}", status=422)

    if detalle:
        detalle.cantidad = cantidad_actual + cantidad
    else:
        detalle = DetalleCarrito(
            carrito_id=carrito.id,
            producto_id=producto.id,
            variante_id=variante.id if variante else None,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
        )
        db.session.add(detalle)

    db.session.commit()
    return jsonify(_serializar_carrito(carrito)), 201


@tienda_bp.patch("/carrito/me/items/<int:item_id>")
@requiere_rol("Cliente")
def actualizar_item_carrito(item_id):
    data = request.get_json() or {}
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    carrito = _carrito_activo_o_crear(cliente.id)
    detalle = DetalleCarrito.query.filter_by(id=item_id, carrito_id=carrito.id).first()
    if not detalle:
        return error("Item no encontrado", status=404)

    try:
        cantidad = _coerce_int(data.get("cantidad"), "cantidad")
    except ValueError:
        return error("cantidad invalida", status=422)

    producto, variante, err = _obtener_producto_variante(detalle.producto_id, detalle.variante_id)
    if err:
        return err

    stock_disponible = _stock_disponible(producto, variante)
    if cantidad <= 0:
        db.session.delete(detalle)
    else:
        if cantidad > stock_disponible:
            return error(f"Stock insuficiente. Disponible: {stock_disponible}", status=422)
        detalle.cantidad = cantidad

    db.session.commit()
    return jsonify(_serializar_carrito(carrito))


@tienda_bp.delete("/carrito/me/items/<int:item_id>")
@requiere_rol("Cliente")
def eliminar_item_carrito(item_id):
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    carrito = _carrito_activo_o_crear(cliente.id)
    detalle = DetalleCarrito.query.filter_by(id=item_id, carrito_id=carrito.id).first()
    if not detalle:
        return error("Item no encontrado", status=404)
    db.session.delete(detalle)
    db.session.commit()
    return jsonify({"mensaje": "Item eliminado"})


@tienda_bp.delete("/carrito/me")
@requiere_rol("Cliente")
def vaciar_carrito_mi():
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    carrito = _carrito_activo_o_crear(cliente.id)
    DetalleCarrito.query.filter_by(carrito_id=carrito.id).delete()
    db.session.commit()
    return jsonify({"mensaje": "Carrito vaciado"})


@tienda_bp.post("/pedidos/generar-whatsapp")
@requiere_rol("Cliente")
def generar_whatsapp_pedido():
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)
    carrito = _carrito_activo_o_crear(cliente.id)
    data, err = _ordenar_pedido_desde_carrito(carrito, cliente)
    if err:
        return err
    return jsonify(data)


@tienda_bp.get("/pedidos/me")
@requiere_rol("Cliente")
def listar_pedidos_mi():
    _usuario, cliente = _cliente_actual()
    if not cliente:
        return error("Cliente no encontrado", status=404)

    pedidos = (
        Pedido.query.options(
            selectinload(Pedido.detalles).selectinload(DetallePedido.producto),
            selectinload(Pedido.detalles).selectinload(DetallePedido.variante),
        )
        .filter_by(cliente_id=cliente.id)
        .order_by(Pedido.creado_en.desc())
        .limit(20)
        .all()
    )
    payload = []
    for pedido in pedidos:
        payload.append(
            {
                "id": pedido.id,
                "subtotal": float(pedido.subtotal or 0),
                "descuento": float(pedido.descuento or 0),
                "total": float(pedido.total or 0),
                "estado": pedido.estado,
                "metodo_contacto": pedido.metodo_contacto,
                "link_contacto": pedido.link_contacto,
                "creado_en": pedido.creado_en.isoformat() if pedido.creado_en else None,
                "items": [
                    {
                        "id": detalle.id,
                        "producto_id": detalle.producto_id,
                        "nombre": detalle.producto.nombre if detalle.producto else None,
                        "variante_id": detalle.variante_id,
                        "variante_label": f"{detalle.variante.atributo}: {detalle.variante.valor}" if detalle.variante else None,
                        "cantidad": int(detalle.cantidad or 0),
                        "precio_unitario": float(detalle.precio_unitario or 0),
                    }
                    for detalle in pedido.detalles
                ],
            }
        )
    return jsonify(payload)


@tienda_bp.post("/productos/<int:producto_id>/stock")
@requiere_rol("Admin")
def reabastecer_producto(producto_id):
    producto, err = _reabastecer_core(producto_id, request.get_json() or {})
    if err:
        return err
    return success(_producto_payload(producto))


@tienda_bp.post("/productos/<int:producto_id>/reabastecer")
@requiere_rol("Admin")
def reabastecer_producto_mod73(producto_id):
    producto, err = _reabastecer_core(producto_id, request.get_json() or {})
    if err:
        return err
    return jsonify(_producto_payload(producto))
