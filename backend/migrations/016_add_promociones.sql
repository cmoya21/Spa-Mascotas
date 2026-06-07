CREATE TABLE IF NOT EXISTS promociones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('porcentaje','monto_fijo')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    fecha_inicio DATE,
    fecha_fin DATE,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);