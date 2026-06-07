CREATE TABLE IF NOT EXISTS mascotas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    especie VARCHAR(50) NOT NULL,
    raza VARCHAR(100),
    tamano VARCHAR(30),
    fecha_nacimiento DATE,
    peso_kg NUMERIC(5,2),
    temperamento VARCHAR(50),
    alergias_conocidas TEXT,
    restricciones_medicas TEXT,
    foto_url TEXT,
    observaciones TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mascota_dueno (
    mascota_id INT NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
    cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    es_principal BOOLEAN NOT NULL DEFAULT FALSE,
    desde TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (mascota_id, cliente_id)
);

ALTER TABLE mascotas
ADD COLUMN IF NOT EXISTS tamano VARCHAR(30);
