from ..extensions import db


class Factura(db.Model):
    __tablename__ = "facturas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero = db.Column(db.String(50), nullable=False, unique=True)
    cita_id = db.Column(db.Integer, db.ForeignKey("citas.id"))
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    fecha_emision = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    impuesto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    descuento = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    metodo_pago = db.Column(db.String(30))
    notas = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    actualizado_en = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class Pago(db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factura_id = db.Column(db.Integer, db.ForeignKey("facturas.id"), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo_pago = db.Column(db.String(30), nullable=False)
    referencia_transaccion = db.Column(db.String(255))
    estado = db.Column(db.String(20), nullable=False, default="completado")
    fecha_pago = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    registrado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
