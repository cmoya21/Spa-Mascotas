from ..extensions import db


class CategoriaProducto(db.Model):
    __tablename__ = "categorias_producto"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    padre_id = db.Column(db.Integer, db.ForeignKey("categorias_producto.id"))
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    padre = db.relationship("CategoriaProducto", remote_side=[id], backref=db.backref("subcategorias", lazy="selectin"))
    productos = db.relationship("Producto", back_populates="categoria", lazy="selectin")


class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    sku = db.Column(db.String(100), unique=True)
    precio_base = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=5)
    imagen_url = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_producto.id"))
    sucursal_id = db.Column(db.Integer)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    categoria = db.relationship("CategoriaProducto", back_populates="productos")
    variantes = db.relationship("VarianteProducto", back_populates="producto", cascade="all, delete-orphan", lazy="selectin")


class VarianteProducto(db.Model):
    __tablename__ = "variantes_producto"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    atributo = db.Column(db.String(50), nullable=False)
    valor = db.Column(db.String(100), nullable=False)
    precio_extra = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    sku_variante = db.Column(db.String(100), nullable=False, unique=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    producto = db.relationship("Producto", back_populates="variantes")


class InsumoSalida(db.Model):
    __tablename__ = "insumos_salida"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ficha_id = db.Column(db.Integer, db.ForeignKey("fichas_grooming.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    groomer_id = db.Column(db.Integer, db.ForeignKey("groomers.id"))
    cantidad = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="entregado")
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class SalidaInsumo(db.Model):
    __tablename__ = "salida_insumos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ficha_id = db.Column(db.Integer, db.ForeignKey("fichas_grooming.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad_entregada = db.Column(db.Numeric(10, 3), nullable=False)
    cantidad_usada = db.Column(db.Numeric(10, 3))
    cantidad_devuelta = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    cantidad_desperdicio = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    estado = db.Column(db.String(20), nullable=False, default="entregado")
    groomer_id = db.Column(db.Integer, db.ForeignKey("groomers.id"), nullable=False)
    entregado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    confirmado_en = db.Column(db.DateTime)
    notas = db.Column(db.Text)
