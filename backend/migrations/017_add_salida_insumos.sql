CREATE TABLE IF NOT EXISTS salida_insumos (
    id SERIAL PRIMARY KEY,
    ficha_id INT NOT NULL REFERENCES fichas_grooming(id) ON DELETE CASCADE,
    producto_id INT NOT NULL REFERENCES productos(id),
    cantidad_entregada NUMERIC(10,3) NOT NULL CHECK (cantidad_entregada > 0),
    cantidad_usada NUMERIC(10,3),
    cantidad_devuelta NUMERIC(10,3) DEFAULT 0,
    cantidad_desperdicio NUMERIC(10,3) DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'entregado'
        CHECK (estado IN ('entregado', 'usado', 'devuelto', 'desperdiciado')),
    groomer_id INT NOT NULL REFERENCES groomers(id),
    entregado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmado_en TIMESTAMPTZ,
    notas TEXT
);

ALTER TABLE IF EXISTS salida_insumos
    ADD COLUMN IF NOT EXISTS cantidad_usada NUMERIC(10,3),
    ADD COLUMN IF NOT EXISTS cantidad_devuelta NUMERIC(10,3) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cantidad_desperdicio NUMERIC(10,3) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS confirmado_en TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS notas TEXT;

CREATE INDEX IF NOT EXISTS idx_salida_insumos_ficha ON salida_insumos(ficha_id);
CREATE INDEX IF NOT EXISTS idx_salida_insumos_groomer ON salida_insumos(groomer_id);
CREATE INDEX IF NOT EXISTS idx_salida_insumos_producto ON salida_insumos(producto_id);
