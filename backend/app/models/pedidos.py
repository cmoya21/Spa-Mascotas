import uuid

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from ..extensions import db


class Carrito(db.Model):
    __tablename__ = "carritos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    session_token = db.Column(PG_UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    expires_at = db.Column(db.DateTime, nullable=False)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    items = db.relationship("DetalleCarrito", back_populates="carrito", cascade="all, delete-orphan")


class DetalleCarrito(db.Model):
    __tablename__ = "detalle_carrito"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey("carritos.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    variante_id = db.Column(db.Integer, db.ForeignKey("variantes_producto.id"))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    agregado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    carrito = db.relationship("Carrito", back_populates="items")
    producto = db.relationship("Producto")
    variante = db.relationship("VarianteProducto")


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey("carritos.id"))
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    descuento = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    metodo_contacto = db.Column(db.String(20), nullable=False, default="whatsapp")
    link_contacto = db.Column(db.Text)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    sucursal_id = db.Column(db.Integer)
    notas = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    detalles = db.relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")


class DetallePedido(db.Model):
    __tablename__ = "detalle_pedido"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    variante_id = db.Column(db.Integer, db.ForeignKey("variantes_producto.id"))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    pedido = db.relationship("Pedido", back_populates="detalles")
    producto = db.relationship("Producto")
    variante = db.relationship("VarianteProducto")
