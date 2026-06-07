CREATE TABLE IF NOT EXISTS notificaciones (
    id SERIAL PRIMARY KEY,
    cita_id INT REFERENCES citas(id) ON DELETE CASCADE,
    cliente_id INT REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_canal VARCHAR(20) NOT NULL,
    tipo_evento VARCHAR(30) NOT NULL,
    destino VARCHAR(255) NOT NULL,
    mensaje TEXT,
    fecha_programacion TIMESTAMPTZ NOT NULL,
    fecha_envio TIMESTAMPTZ,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    reintentos SMALLINT NOT NULL DEFAULT 0,
    ultimo_intento TIMESTAMPTZ,
    error_mensaje TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
