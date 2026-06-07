CREATE TABLE IF NOT EXISTS facturas (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50) NOT NULL UNIQUE,
    cita_id INT REFERENCES citas(id) ON DELETE SET NULL,
    cliente_id INT NOT NULL REFERENCES clientes(id),
    fecha_emision TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    subtotal NUMERIC(10,2) NOT NULL DEFAULT 0,
    impuesto NUMERIC(10,2) NOT NULL DEFAULT 0,
    descuento NUMERIC(10,2) NOT NULL DEFAULT 0,
    total NUMERIC(10,2) NOT NULL DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    metodo_pago VARCHAR(30),
    notas TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    factura_id INT NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    monto NUMERIC(10,2) NOT NULL,
    metodo_pago VARCHAR(30) NOT NULL,
    referencia_transaccion VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'completado',
    fecha_pago TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registrado_por INT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
