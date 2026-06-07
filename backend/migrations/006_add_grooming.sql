CREATE TABLE IF NOT EXISTS checklist_items_template (
    id SERIAL PRIMARY KEY,
    servicio_id INT NOT NULL REFERENCES servicios(id) ON DELETE CASCADE,
    nombre VARCHAR(150) NOT NULL,
    requiere_obs BOOLEAN NOT NULL DEFAULT FALSE,
    orden SMALLINT NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS fichas_grooming (
    id SERIAL PRIMARY KEY,
    cita_id INT NOT NULL UNIQUE REFERENCES citas(id) ON DELETE CASCADE,
    estado_inicial TEXT,
    temperatura_ingreso NUMERIC(4,1),
    peso_momento_servicio NUMERIC(5,2),
    raza_tamano_momento VARCHAR(100),
    estado_final TEXT,
    observaciones_final TEXT,
    notas_internas TEXT,
    consumido_inventario BOOLEAN NOT NULL DEFAULT FALSE,
    insumos_consumidos JSONB,
    fecha_cierre TIMESTAMPTZ,
    checklist_completo BOOLEAN NOT NULL DEFAULT FALSE,
    groomer_id INT REFERENCES groomers(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fichas_checklist (
    id SERIAL PRIMARY KEY,
    ficha_id INT NOT NULL REFERENCES fichas_grooming(id) ON DELETE CASCADE,
    item_id INT NOT NULL REFERENCES checklist_items_template(id) ON DELETE CASCADE,
    completado BOOLEAN NOT NULL DEFAULT FALSE,
    observacion TEXT,
    completado_en TIMESTAMPTZ,
    UNIQUE (ficha_id, item_id)
);

CREATE TABLE IF NOT EXISTS fotos_ficha (
    id SERIAL PRIMARY KEY,
    ficha_id INT NOT NULL REFERENCES fichas_grooming(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    descripcion TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
