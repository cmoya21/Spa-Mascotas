-- =============================================================================
-- BASE DE DATOS: SPA PARA MASCOTAS
-- Versión completa según requerimientos
-- Motor: PostgreSQL 15+
-- =============================================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 1. ROLES Y PERMISOS
-- =============================================================================

CREATE TABLE roles (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(50) NOT NULL UNIQUE,          -- Admin, Recepción, Groomer, Cliente
    descripcion   TEXT,
    permisos      JSONB NOT NULL DEFAULT '{}',          -- Permisos detallados por acción
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Datos iniciales de roles
INSERT INTO roles (nombre, descripcion, permisos) VALUES
('Admin',      'Acceso total al sistema',            '{"all": true}'),
('Recepcion',  'Gestión de citas y clientes',        '{"citas": true, "clientes": true, "reportes": true}'),
('Groomer',    'Acceso a su agenda y fichas',        '{"fichas": true, "agenda_propia": true}'),
('Cliente',    'Autogestión de cuenta y mascotas',   '{"autogestión": true}');


-- =============================================================================
-- 2. USUARIOS Y SESIONES
-- =============================================================================

CREATE TABLE usuarios (
    id                  SERIAL PRIMARY KEY,
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,             -- BCRYPT costo 12
    two_factor_secret   VARCHAR(255),                      -- TOTP secret
    two_factor_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    ultimo_acceso       TIMESTAMPTZ,
    rol_id              INT REFERENCES roles(id) ON DELETE SET NULL,
    estado_activo       BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT email_formato CHECK (email ~* '^[^@]+@[^@]+\.[^@]+$'),
    CONSTRAINT password_longitud CHECK (LENGTH(password_hash) >= 8)
);

CREATE TABLE user_sessions (
    id              SERIAL PRIMARY KEY,
    usuario_id      INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_jwt       TEXT NOT NULL UNIQUE,
    refresh_token   TEXT NOT NULL UNIQUE,
    ip_address      INET,
    user_agent      TEXT,
    fecha_expiracion TIMESTAMPTZ NOT NULL,               -- 1 hora para JWT
    refresh_expira  TIMESTAMPTZ NOT NULL,               -- 30 días para refresh
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_token     ON user_sessions(token_jwt);
CREATE INDEX idx_user_sessions_refresh   ON user_sessions(refresh_token);
CREATE INDEX idx_user_sessions_usuario   ON user_sessions(usuario_id);


-- =============================================================================
-- 3. SUCURSALES (Soporte multi-sucursal futuro)
-- =============================================================================

CREATE TABLE sucursales (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    direccion   TEXT,
    telefono    VARCHAR(30),
    activa      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO sucursales (nombre, direccion) VALUES ('Principal', 'Sede principal');


-- =============================================================================
-- 4. CLIENTES
-- =============================================================================

CREATE TABLE clientes (
    id                      SERIAL PRIMARY KEY,
    usuario_id              INT NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre                  VARCHAR(100) NOT NULL,
    apellido                VARCHAR(100),
    telefono                VARCHAR(30),
    direccion               TEXT,                          -- Para entregas a domicilio
    canal_notificacion      VARCHAR(20) DEFAULT 'whatsapp' -- email, whatsapp, sms
        CHECK (canal_notificacion IN ('email', 'whatsapp', 'sms')),
    horario_preferido       VARCHAR(50),                   -- Ej: "mañana", "tarde"
    sucursal_id             INT REFERENCES sucursales(id),
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clientes_usuario ON clientes(usuario_id);


-- =============================================================================
-- 5. MASCOTAS
-- =============================================================================

CREATE TABLE mascotas (
    id                      SERIAL PRIMARY KEY,
    nombre                  VARCHAR(100) NOT NULL,
    especie                 VARCHAR(50) NOT NULL,          -- Perro, Gato, etc.
    raza                    VARCHAR(100),
    fecha_nacimiento        DATE,
    peso_kg                 NUMERIC(5,2),
    temperamento            VARCHAR(50)
        CHECK (temperamento IN ('tranquilo', 'jugueton', 'agresivo', 'ansioso', 'otro')),
    alergias_conocidas      TEXT,                          -- Alerta visual en servicio
    restricciones_medicas   TEXT,                          -- Limitaciones médicas/comportamiento
    foto_url                TEXT,
    observaciones           TEXT,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Relación N:M mascota ↔ dueño (múltiples dueños por mascota)
CREATE TABLE mascota_dueno (
    mascota_id  INT NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
    cliente_id  INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    es_principal BOOLEAN NOT NULL DEFAULT FALSE,
    desde       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (mascota_id, cliente_id)
);

-- Vacunas
CREATE TABLE vacunas (
    id              SERIAL PRIMARY KEY,
    mascota_id      INT NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
    nombre          VARCHAR(100) NOT NULL,
    fecha_aplicacion DATE NOT NULL,
    fecha_vencimiento DATE,
    veterinario     VARCHAR(100),
    notas           TEXT,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vacunas_mascota ON vacunas(mascota_id);

-- Historial completo de eventos de la mascota
CREATE TABLE historial_mascota (
    id          SERIAL PRIMARY KEY,
    mascota_id  INT NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
    tipo_evento VARCHAR(50) NOT NULL
        CHECK (tipo_evento IN ('servicio', 'recomendacion', 'alerta', 'cancelacion', 'nota', 'otro')),
    descripcion TEXT NOT NULL,
    usuario_id  INT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_historial_mascota ON historial_mascota(mascota_id);


-- =============================================================================
-- 6. GROOMERS
-- =============================================================================

CREATE TABLE groomers (
    id                  SERIAL PRIMARY KEY,
    usuario_id          INT NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre              VARCHAR(100) NOT NULL,
    apellido            VARCHAR(100),
    telefono            VARCHAR(30),
    especialidad        VARCHAR(100),                  -- Ej: "Corte fino"
    capacidad_simultanea INT NOT NULL DEFAULT 1,       -- Mascotas a la vez
    capacidad_diaria    INT NOT NULL DEFAULT 8,         -- Maximo servicios por jornada
    horario_trabajo     JSONB,                         -- JSON con configuración semanal
    sucursal_id         INT REFERENCES sucursales(id),
    estado_activo       BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Disponibilidad por día de semana
CREATE TABLE disponibilidad_groomer (
    id                  SERIAL PRIMARY KEY,
    groomer_id          INT NOT NULL REFERENCES groomers(id) ON DELETE CASCADE,
    dia_semana          SMALLINT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6), -- 0=Dom, 6=Sáb
    hora_inicio         TIME NOT NULL,
    hora_fin            TIME NOT NULL,
    intervalo_descanso  JSONB,                         -- {"inicio":"13:00","fin":"14:00"}
    buffer_minutos      INT NOT NULL DEFAULT 15,       -- Tiempo limpieza entre citas
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT check_horas CHECK (hora_fin > hora_inicio),
    UNIQUE (groomer_id, dia_semana)
);

-- Bloqueos de calendario
CREATE TABLE bloqueos_calendario (
    id              SERIAL PRIMARY KEY,
    groomer_id      INT REFERENCES groomers(id) ON DELETE CASCADE, -- NULL = global
    fecha_inicio    TIMESTAMPTZ NOT NULL,
    fecha_fin       TIMESTAMPTZ NOT NULL,
    tipo_bloqueo    VARCHAR(30) NOT NULL
        CHECK (tipo_bloqueo IN ('feriado', 'vacaciones', 'mantenimiento', 'ausencia')),
    descripcion     TEXT,
    creado_por      INT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_fechas_bloqueo CHECK (fecha_fin > fecha_inicio)
);

CREATE INDEX idx_bloqueos_groomer ON bloqueos_calendario(groomer_id);
CREATE INDEX idx_bloqueos_fechas  ON bloqueos_calendario(fecha_inicio, fecha_fin);


-- =============================================================================
-- 7. CATEGORÍAS DE PRODUCTOS (jerarquía)
-- =============================================================================

CREATE TABLE categorias_producto (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    padre_id    INT REFERENCES categorias_producto(id) ON DELETE SET NULL, -- Autoreferencia
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_categorias_padre ON categorias_producto(padre_id);


-- =============================================================================
-- 8. PRODUCTOS E INVENTARIO
-- =============================================================================

CREATE TABLE productos (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL,
    descripcion     TEXT,
    sku             VARCHAR(100) NOT NULL UNIQUE,
    precio_base     NUMERIC(10,2) NOT NULL CHECK (precio_base >= 0),
    stock           INT NOT NULL DEFAULT 0,
    stock_minimo    INT NOT NULL DEFAULT 5,
    imagen_url      TEXT,
    categoria_id    INT REFERENCES categorias_producto(id) ON DELETE SET NULL,
    sucursal_id     INT REFERENCES sucursales(id),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_productos_categoria ON productos(categoria_id);
CREATE INDEX idx_productos_sku        ON productos(sku);

INSERT INTO productos (nombre, sku, precio_base, stock, stock_minimo)
VALUES
    ('Shampoo hipoalergénico 1L', 'SHP-001', 25.00, 20, 5),
    ('Acondicionador 500ml', 'ACO-001', 18.00, 15, 5),
    ('Perfume para mascotas', 'PRF-001', 12.00, 30, 10)
ON CONFLICT (sku) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    precio_base = EXCLUDED.precio_base,
    stock = GREATEST(productos.stock, EXCLUDED.stock),
    stock_minimo = EXCLUDED.stock_minimo,
    activo = TRUE;

-- Variantes de productos (talla, fragancia, etc.)
CREATE TABLE variantes_producto (
    id          SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    atributo    VARCHAR(50) NOT NULL,          -- Ej: "Tamaño", "Fragancia"
    valor       VARCHAR(100) NOT NULL,         -- Ej: "1kg", "Lavanda"
    precio_extra NUMERIC(10,2) NOT NULL DEFAULT 0,
    stock       INT NOT NULL DEFAULT 0,
    sku_variante VARCHAR(100) NOT NULL UNIQUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_variantes_producto ON variantes_producto(producto_id);


-- =============================================================================
-- 9. SERVICIOS
-- =============================================================================

CREATE TABLE servicios (
    id                          SERIAL PRIMARY KEY,
    nombre                      VARCHAR(150) NOT NULL,
    descripcion                 TEXT,
    precio_base                 NUMERIC(10,2) NOT NULL CHECK (precio_base >= 0),
    duracion_base_minutos       INT NOT NULL CHECK (duracion_base_minutos % 15 = 0),
    permite_doble_booking       BOOLEAN NOT NULL DEFAULT FALSE,
    requiere_bloqueo_consecutivo BOOLEAN NOT NULL DEFAULT FALSE,
    factor_tamano_raza          JSONB,    -- {"pequeno": 1.0, "mediano": 1.15, "grande": 1.30}
    consumo_insumos             JSONB,    -- [{"producto_id": 1, "cantidad": 0.1}]
    activo                      BOOLEAN NOT NULL DEFAULT TRUE,
    sucursal_id                 INT REFERENCES sucursales(id),
    creado_en                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Templates de checklist por tipo de servicio
CREATE TABLE checklist_items_template (
    id              SERIAL PRIMARY KEY,
    servicio_id     INT NOT NULL REFERENCES servicios(id) ON DELETE CASCADE,
    nombre          VARCHAR(150) NOT NULL,     -- Baño, corte, uñas, oídos, glándulas, perfume
    requiere_obs    BOOLEAN NOT NULL DEFAULT FALSE,
    orden           SMALLINT NOT NULL DEFAULT 0,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_checklist_template_servicio ON checklist_items_template(servicio_id);


-- =============================================================================
-- 10. CITAS
-- =============================================================================

CREATE TABLE citas (
    id                  SERIAL PRIMARY KEY,
    mascota_id          INT NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
    groomer_id          INT NOT NULL REFERENCES groomers(id),
    servicio_id         INT NOT NULL REFERENCES servicios(id),
    sucursal_id         INT REFERENCES sucursales(id),
    fecha_hora_inicio   TIMESTAMPTZ NOT NULL,
    fecha_hora_fin      TIMESTAMPTZ NOT NULL,
    duracion_estimada   INT NOT NULL,          -- Minutos estimados
    duracion_real       INT,                   -- Minutos reales (al cerrar)
    estado              VARCHAR(20) NOT NULL DEFAULT 'agendada'
        CHECK (estado IN ('pendiente','agendada','confirmada','en_progreso','completada','rechazada','cancelada','no_asistio')),
    precio_estimado     NUMERIC(10,2),
    creado_por          INT REFERENCES usuarios(id) ON DELETE SET NULL,
    -- Reprogramación
    reprogramada_desde  INT REFERENCES citas(id) ON DELETE SET NULL,
    reprogramada_en     TIMESTAMPTZ,
    reprogramada_por    INT REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_cancelacion  TEXT,
    notas               TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_fechas_cita CHECK (fecha_hora_fin > fecha_hora_inicio),
    UNIQUE (groomer_id, fecha_hora_inicio)   -- Evitar solapamientos
);

CREATE INDEX idx_citas_mascota    ON citas(mascota_id);
CREATE INDEX idx_citas_groomer    ON citas(groomer_id);
CREATE INDEX idx_citas_fecha      ON citas(fecha_hora_inicio);
CREATE INDEX idx_citas_estado     ON citas(estado);


-- =============================================================================
-- 11. FICHAS DE GROOMING
-- =============================================================================

CREATE TABLE fichas_grooming (
    id                      SERIAL PRIMARY KEY,
    cita_id                 INT NOT NULL UNIQUE REFERENCES citas(id) ON DELETE CASCADE,
    -- Estado inicial
    estado_inicial          TEXT,
    temperatura_ingreso     NUMERIC(4,1),       -- °C o °F
    peso_momento_servicio   NUMERIC(5,2),
    raza_tamano_momento     VARCHAR(100),
    -- Estado final
    estado_final            TEXT,
    observaciones_final     TEXT,
    -- Internos
    notas_internas          TEXT,               -- Solo para el equipo
    -- Control inventario
    consumido_inventario    BOOLEAN NOT NULL DEFAULT FALSE,
    insumos_consumidos      JSONB,              -- [{"producto_id":1, "cantidad":0.2}]
    -- Cierre
    fecha_cierre            TIMESTAMPTZ,
    checklist_completo      BOOLEAN NOT NULL DEFAULT FALSE,
    groomer_id              INT REFERENCES groomers(id),
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

UPDATE servicios
SET descripcion = 'Baño express con secado básico.',
    precio_base = 50.00,
    duracion_base_minutos = 30,
    factor_tamano_raza = '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    consumo_insumos = jsonb_build_array(jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.05)),
    activo = TRUE
WHERE nombre = 'Baño rápido';
INSERT INTO servicios (nombre, descripcion, precio_base, duracion_base_minutos, factor_tamano_raza, consumo_insumos, activo)
SELECT
    'Baño rápido',
    'Baño express con secado básico.',
    50.00,
    30,
    '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    jsonb_build_array(jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.05)),
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Baño rápido');

UPDATE servicios
SET descripcion = 'Baño con shampoo especializado, acondicionador y secado profesional.',
    precio_base = 80.00,
    duracion_base_minutos = 60,
    factor_tamano_raza = '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    consumo_insumos = jsonb_build_array(
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.1),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'ACO-001' LIMIT 1), 'cantidad', 0.05)
    ),
    activo = TRUE
WHERE nombre = 'Baño completo';
INSERT INTO servicios (nombre, descripcion, precio_base, duracion_base_minutos, factor_tamano_raza, consumo_insumos, activo)
SELECT
    'Baño completo',
    'Baño con shampoo especializado, acondicionador y secado profesional.',
    80.00,
    60,
    '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    jsonb_build_array(
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.1),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'ACO-001' LIMIT 1), 'cantidad', 0.05)
    ),
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Baño completo');

UPDATE servicios
SET descripcion = 'Corte de pelo según raza y estilo, incluye peinado y perfume.',
    precio_base = 120.00,
    duracion_base_minutos = 90,
    factor_tamano_raza = '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    consumo_insumos = jsonb_build_array(
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.1),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'PRF-001' LIMIT 1), 'cantidad', 1)
    ),
    activo = TRUE
WHERE nombre = 'Corte y peinado';
INSERT INTO servicios (nombre, descripcion, precio_base, duracion_base_minutos, factor_tamano_raza, consumo_insumos, activo)
SELECT
    'Corte y peinado',
    'Corte de pelo según raza y estilo, incluye peinado y perfume.',
    120.00,
    90,
    '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    jsonb_build_array(
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.1),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'PRF-001' LIMIT 1), 'cantidad', 1)
    ),
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Corte y peinado');

UPDATE servicios
SET descripcion = 'Baño, corte, peinado, limpieza de oídos, corte de uñas y perfume.',
    precio_base = 160.00,
    duracion_base_minutos = 120,
    factor_tamano_raza = '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    consumo_insumos = jsonb_build_array(
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.15),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'ACO-001' LIMIT 1), 'cantidad', 0.1),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'PRF-001' LIMIT 1), 'cantidad', 1)
    ),
    activo = TRUE
WHERE nombre = 'Servicio completo';
INSERT INTO servicios (nombre, descripcion, precio_base, duracion_base_minutos, factor_tamano_raza, consumo_insumos, activo)
SELECT
    'Servicio completo',
    'Baño, corte, peinado, limpieza de oídos, corte de uñas y perfume.',
    160.00,
    120,
    '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    jsonb_build_array(
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.15),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'ACO-001' LIMIT 1), 'cantidad', 0.1),
        jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'PRF-001' LIMIT 1), 'cantidad', 1)
    ),
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Servicio completo');

DELETE FROM checklist_items_template cit USING servicios s
WHERE cit.servicio_id = s.id AND s.nombre IN ('Baño rápido', 'Baño completo', 'Corte y peinado', 'Servicio completo');

INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Revisión estado inicial de la mascota', true, 1 FROM servicios WHERE nombre='Baño rápido';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Baño aplicado', false, 2 FROM servicios WHERE nombre='Baño rápido';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Secado completo', false, 3 FROM servicios WHERE nombre='Baño rápido';

INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Revisión estado inicial', true, 1 FROM servicios WHERE nombre='Baño completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Shampoo aplicado', false, 2 FROM servicios WHERE nombre='Baño completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Acondicionador aplicado', false, 3 FROM servicios WHERE nombre='Baño completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Secado completo', false, 4 FROM servicios WHERE nombre='Baño completo';

INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Revisión estado inicial', true, 1 FROM servicios WHERE nombre='Corte y peinado';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Baño previo al corte', false, 2 FROM servicios WHERE nombre='Corte y peinado';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Corte realizado', true, 3 FROM servicios WHERE nombre='Corte y peinado';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Peinado finalizado', false, 4 FROM servicios WHERE nombre='Corte y peinado';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Perfume aplicado', false, 5 FROM servicios WHERE nombre='Corte y peinado';

INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Revisión estado inicial', true, 1 FROM servicios WHERE nombre='Servicio completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Baño con shampoo', false, 2 FROM servicios WHERE nombre='Servicio completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Acondicionador aplicado', false, 3 FROM servicios WHERE nombre='Servicio completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Corte realizado', true, 4 FROM servicios WHERE nombre='Servicio completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Limpieza de oídos', true, 5 FROM servicios WHERE nombre='Servicio completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Corte de uñas', false, 6 FROM servicios WHERE nombre='Servicio completo';
INSERT INTO checklist_items_template (servicio_id, nombre, requiere_obs, orden)
SELECT id, 'Perfume y presentación', false, 7 FROM servicios WHERE nombre='Servicio completo';

-- Checklist por ficha
CREATE TABLE fichas_checklist (
    id              SERIAL PRIMARY KEY,
    ficha_id        INT NOT NULL REFERENCES fichas_grooming(id) ON DELETE CASCADE,
    item_id         INT NOT NULL REFERENCES checklist_items_template(id) ON DELETE CASCADE,
    completado      BOOLEAN NOT NULL DEFAULT FALSE,
    observacion     TEXT,
    completado_en   TIMESTAMPTZ,
    UNIQUE (ficha_id, item_id)
);

CREATE INDEX idx_fichas_checklist_ficha ON fichas_checklist(ficha_id);

-- Fotos antes/después
CREATE TABLE fotos_ficha (
    id          SERIAL PRIMARY KEY,
    ficha_id    INT NOT NULL REFERENCES fichas_grooming(id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    tipo        VARCHAR(10) NOT NULL CHECK (tipo IN ('antes', 'despues')),
    descripcion TEXT,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fotos_ficha ON fotos_ficha(ficha_id);


-- =============================================================================
-- 12. CARRITO DE COMPRAS
-- =============================================================================

CREATE TABLE carritos (
    id              SERIAL PRIMARY KEY,
    cliente_id      INT REFERENCES clientes(id) ON DELETE CASCADE,
    session_token   UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE, -- Para anónimos
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_carritos_cliente ON carritos(cliente_id);
CREATE INDEX idx_carritos_token   ON carritos(session_token);

CREATE TABLE detalle_carrito (
    id              SERIAL PRIMARY KEY,
    carrito_id      INT NOT NULL REFERENCES carritos(id) ON DELETE CASCADE,
    producto_id     INT NOT NULL REFERENCES productos(id),
    variante_id     INT REFERENCES variantes_producto(id),
    cantidad        INT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL,  -- Precio congelado al agregar
    agregado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_detalle_carrito ON detalle_carrito(carrito_id);


-- =============================================================================
-- 13. PEDIDOS
-- =============================================================================

CREATE TABLE pedidos (
    id                  SERIAL PRIMARY KEY,
    carrito_id          INT REFERENCES carritos(id) ON DELETE SET NULL,
    cliente_id          INT NOT NULL REFERENCES clientes(id),
    subtotal            NUMERIC(10,2) NOT NULL DEFAULT 0,
    descuento           NUMERIC(10,2) NOT NULL DEFAULT 0,
    total               NUMERIC(10,2) NOT NULL DEFAULT 0,
    metodo_contacto     VARCHAR(20) NOT NULL DEFAULT 'whatsapp'
        CHECK (metodo_contacto IN ('whatsapp', 'telegram')),
    link_contacto       TEXT,               -- URL WhatsApp/Telegram generado
    estado              VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','enviado','confirmado','pagado','entregado','cancelado')),
    sucursal_id         INT REFERENCES sucursales(id),
    notas               TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pedidos_cliente ON pedidos(cliente_id);

CREATE TABLE detalle_pedido (
    id              SERIAL PRIMARY KEY,
    pedido_id       INT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    producto_id     INT NOT NULL REFERENCES productos(id),
    variante_id     INT REFERENCES variantes_producto(id),
    cantidad        INT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL   -- Precio congelado al vender
);

CREATE INDEX idx_detalle_pedido ON detalle_pedido(pedido_id);


-- =============================================================================
-- 14. FACTURAS Y PAGOS
-- =============================================================================

CREATE TABLE facturas (
    id              SERIAL PRIMARY KEY,
    numero          VARCHAR(50) NOT NULL UNIQUE,    -- Numeración correlativa
    cita_id         INT REFERENCES citas(id) ON DELETE SET NULL,
    pedido_id       INT REFERENCES pedidos(id) ON DELETE SET NULL,
    cliente_id      INT NOT NULL REFERENCES clientes(id),
    fecha_emision   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    subtotal        NUMERIC(10,2) NOT NULL DEFAULT 0,
    impuesto        NUMERIC(10,2) NOT NULL DEFAULT 0,
    descuento       NUMERIC(10,2) NOT NULL DEFAULT 0,
    total           NUMERIC(10,2) NOT NULL DEFAULT 0,
    estado          VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','pagada','cancelada')),
    metodo_pago     VARCHAR(30)
        CHECK (metodo_pago IN ('efectivo','qr','transferencia')),
    sucursal_id     INT REFERENCES sucursales(id),
    notas           TEXT,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_total CHECK (total = subtotal + impuesto - descuento)
);

CREATE INDEX idx_facturas_cliente ON facturas(cliente_id);
CREATE INDEX idx_facturas_cita    ON facturas(cita_id);
CREATE INDEX idx_facturas_pedido  ON facturas(pedido_id);

-- =============================================================================
-- 14.1. PROMOCIONES Y CUPONES
-- =============================================================================

CREATE TABLE promociones (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL,
    descripcion     TEXT,
    tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('porcentaje', 'monto_fijo')),
    valor           NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    codigo_cupon    VARCHAR(50) UNIQUE,
    uso_maximo      INT,
    uso_actual      INT NOT NULL DEFAULT 0,
    aplica_a        VARCHAR(20) NOT NULL DEFAULT 'todo'
        CHECK (aplica_a IN ('todo', 'servicios', 'productos', 'cliente_frecuente')),
    fecha_inicio    DATE,
    fecha_fin       DATE,
    activa          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE detalle_factura (
    id              SERIAL PRIMARY KEY,
    factura_id      INT NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    descripcion     VARCHAR(255) NOT NULL,
    cantidad        INT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL,
    subtotal        NUMERIC(10,2) NOT NULL
);

CREATE INDEX idx_detalle_factura ON detalle_factura(factura_id);

-- Secuencia para número de factura
CREATE SEQUENCE seq_factura START 1;

-- Pagos parciales
CREATE TABLE pagos (
    id                  SERIAL PRIMARY KEY,
    factura_id          INT NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    monto               NUMERIC(10,2) NOT NULL CHECK (monto > 0),
    metodo_pago         VARCHAR(30) NOT NULL
        CHECK (metodo_pago IN ('efectivo','qr','transferencia')),
    referencia_transaccion VARCHAR(255),
    estado              VARCHAR(20) NOT NULL DEFAULT 'completado'
        CHECK (estado IN ('completado','pendiente','fallido')),
    fecha_pago          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registrado_por      INT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pagos_factura ON pagos(factura_id);


-- =============================================================================
-- 15. NOTIFICACIONES
-- =============================================================================

CREATE TABLE notificaciones (
    id                  SERIAL PRIMARY KEY,
    cita_id             INT REFERENCES citas(id) ON DELETE CASCADE,
    cliente_id          INT REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_canal          VARCHAR(20) NOT NULL
        CHECK (tipo_canal IN ('email','whatsapp','sms')),
    tipo_evento         VARCHAR(30) NOT NULL
        CHECK (tipo_evento IN ('confirmacion','recordatorio_24h','recordatorio_2h','listo_recoger','encuesta','promocion','solicitud_revision','bajo_stock','pago_registrado')),
    destino             VARCHAR(255) NOT NULL,       -- Email o teléfono
    mensaje             TEXT,
    fecha_programacion  TIMESTAMPTZ NOT NULL,
    fecha_envio         TIMESTAMPTZ,
    estado              VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','enviado','fallido','cancelado')),
    reintentos          SMALLINT NOT NULL DEFAULT 0,
    ultimo_intento      TIMESTAMPTZ,
    error_mensaje       TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notificaciones_cita       ON notificaciones(cita_id);
CREATE INDEX idx_notificaciones_cliente    ON notificaciones(cliente_id);
CREATE INDEX idx_notificaciones_programada ON notificaciones(fecha_programacion) WHERE estado = 'pendiente';


-- =============================================================================
-- 16. ENCUESTAS POST-SERVICIO
-- =============================================================================

CREATE TABLE encuestas (
    id          SERIAL PRIMARY KEY,
    cita_id     INT NOT NULL UNIQUE REFERENCES citas(id) ON DELETE CASCADE,
    cliente_id  INT NOT NULL REFERENCES clientes(id),
    calificacion SMALLINT CHECK (calificacion BETWEEN 1 AND 5),
    nps         SMALLINT CHECK (nps BETWEEN 0 AND 10),
    comentario  TEXT,
    respondida  BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    respondida_en TIMESTAMPTZ
);

CREATE INDEX idx_encuestas_cita    ON encuestas(cita_id);
CREATE INDEX idx_encuestas_cliente ON encuestas(cliente_id);


-- =============================================================================
-- 17. AUDITORÍA
-- =============================================================================

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    tabla       VARCHAR(100) NOT NULL,
    operacion   VARCHAR(10) NOT NULL CHECK (operacion IN ('INSERT','UPDATE','DELETE')),
    registro_id BIGINT,
    datos_antes JSONB,
    datos_despues JSONB,
    usuario_id  INT REFERENCES usuarios(id) ON DELETE SET NULL,
    ip_address  INET,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_tabla   ON audit_log(tabla, registro_id);
CREATE INDEX idx_audit_usuario ON audit_log(usuario_id);
CREATE INDEX idx_audit_fecha   ON audit_log(creado_en);


-- =============================================================================
-- 18. TRIGGERS Y FUNCIONES
-- =============================================================================

-- Función: actualizar timestamp automático
CREATE OR REPLACE FUNCTION fn_actualizar_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$;

-- Aplicar trigger de timestamp a todas las tablas relevantes
CREATE TRIGGER trg_ts_usuarios         BEFORE UPDATE ON usuarios         FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_clientes         BEFORE UPDATE ON clientes         FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_mascotas         BEFORE UPDATE ON mascotas         FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_groomers         BEFORE UPDATE ON groomers         FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_servicios        BEFORE UPDATE ON servicios        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_citas            BEFORE UPDATE ON citas            FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_fichas_grooming  BEFORE UPDATE ON fichas_grooming  FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_productos        BEFORE UPDATE ON productos        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_pedidos          BEFORE UPDATE ON pedidos          FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
CREATE TRIGGER trg_ts_facturas         BEFORE UPDATE ON facturas         FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();

-- -------------------------------------------------------------------
-- Trigger: Descuento de inventario al cerrar ficha de grooming
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_descontar_inventario()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    insumo JSONB;
    pid    INT;
    cant   NUMERIC;
BEGIN
    -- Solo ejecutar si se acaba de poner consumido_inventario = TRUE
    IF NEW.consumido_inventario = TRUE AND OLD.consumido_inventario = FALSE THEN
        IF NEW.insumos_consumidos IS NOT NULL THEN
            FOR insumo IN SELECT * FROM jsonb_array_elements(NEW.insumos_consumidos)
            LOOP
                pid  := (insumo->>'producto_id')::INT;
                cant := (insumo->>'cantidad')::NUMERIC;
                UPDATE productos
                   SET stock = stock - cant
                 WHERE id = pid AND stock - cant >= 0;
                -- Si el resultado es stock negativo, se ignora (no negativo según regla de negocio)
            END LOOP;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_descontar_inventario
    BEFORE UPDATE ON fichas_grooming
    FOR EACH ROW EXECUTE FUNCTION fn_descontar_inventario();

-- -------------------------------------------------------------------
-- Trigger: Alerta de bajo inventario
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_alerta_bajo_inventario()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.stock <= NEW.stock_minimo AND OLD.stock > OLD.stock_minimo THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, datos_despues)
        VALUES ('productos', 'UPDATE', NEW.id,
                jsonb_build_object('alerta', 'bajo_inventario', 'stock', NEW.stock, 'stock_minimo', NEW.stock_minimo));
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_alerta_inventario
    AFTER UPDATE ON productos
    FOR EACH ROW EXECUTE FUNCTION fn_alerta_bajo_inventario();

-- -------------------------------------------------------------------
-- Trigger: Validar que suma de pagos no exceda total de factura
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_validar_pago()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    total_pagado NUMERIC;
    total_factura NUMERIC;
BEGIN
    SELECT COALESCE(SUM(monto), 0) INTO total_pagado
      FROM pagos
     WHERE factura_id = NEW.factura_id AND estado = 'completado';

    SELECT total INTO total_factura
      FROM facturas
     WHERE id = NEW.factura_id;

    IF total_pagado + NEW.monto > total_factura THEN
        RAISE EXCEPTION 'Los pagos superan el total de la factura (Total: %, Ya pagado: %, Nuevo: %)',
            total_factura, total_pagado, NEW.monto;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_pago
    BEFORE INSERT ON pagos
    FOR EACH ROW EXECUTE FUNCTION fn_validar_pago();

-- -------------------------------------------------------------------
-- Trigger: Número de factura correlativo automático
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_generar_numero_factura()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.numero IS NULL OR NEW.numero = '' THEN
        NEW.numero := 'FAC-' || LPAD(nextval('seq_factura')::TEXT, 8, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_numero_factura
    BEFORE INSERT ON facturas
    FOR EACH ROW EXECUTE FUNCTION fn_generar_numero_factura();

-- -------------------------------------------------------------------
-- Trigger: Ficha grooming - validar checklist antes de cerrar
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_validar_cierre_ficha()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    items_pendientes INT;
    fotos_antes INT;
    fotos_despues INT;
BEGIN
    IF NEW.fecha_cierre IS NOT NULL AND OLD.fecha_cierre IS NULL THEN
        -- Verificar checklist completo
        SELECT COUNT(*) INTO items_pendientes
          FROM fichas_checklist fc
          JOIN checklist_items_template cit ON fc.item_id = cit.id
         WHERE fc.ficha_id = NEW.id AND fc.completado = FALSE AND cit.requiere_obs = TRUE;

        IF items_pendientes > 0 THEN
            RAISE EXCEPTION 'No se puede cerrar la ficha: hay % items de checklist pendientes', items_pendientes;
        END IF;

        -- Verificar mínimo 1 foto antes y 1 después
        SELECT COUNT(*) INTO fotos_antes   FROM fotos_ficha WHERE ficha_id = NEW.id AND tipo = 'antes';
        SELECT COUNT(*) INTO fotos_despues FROM fotos_ficha WHERE ficha_id = NEW.id AND tipo = 'despues';

        IF fotos_antes = 0 OR fotos_despues = 0 THEN
            RAISE EXCEPTION 'Se requiere al menos 1 foto antes y 1 foto después para cerrar la ficha';
        END IF;

        NEW.checklist_completo = TRUE;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_cierre_ficha
    BEFORE UPDATE ON fichas_grooming
    FOR EACH ROW EXECUTE FUNCTION fn_validar_cierre_ficha();

-- -------------------------------------------------------------------
-- Trigger: No modificar groomer de cita ya confirmada
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_proteger_cita_confirmada()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.estado IN ('confirmada','en_progreso','completada') AND NEW.groomer_id <> OLD.groomer_id THEN
        RAISE EXCEPTION 'No se puede cambiar el groomer de una cita en estado "%"', OLD.estado;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_proteger_cita_confirmada
    BEFORE UPDATE ON citas
    FOR EACH ROW EXECUTE FUNCTION fn_proteger_cita_confirmada();

-- -------------------------------------------------------------------
-- Función: limpiar carritos expirados (ejecutar por cron)
-- -------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_limpiar_carritos_expirados()
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM carritos WHERE expires_at < NOW();
END;
$$;


-- =============================================================================
-- 19. VISTAS PARA REPORTES
-- =============================================================================

-- Reporte: Ocupación por groomer
CREATE OR REPLACE VIEW v_ocupacion_groomer AS
SELECT
    g.id AS groomer_id,
    g.nombre AS groomer,
    DATE(c.fecha_hora_inicio) AS fecha,
    COUNT(c.id) AS total_citas,
    SUM(c.duracion_estimada) AS minutos_ocupados,
    COUNT(c.id) FILTER (WHERE c.estado = 'completada') AS citas_completadas,
    COUNT(c.id) FILTER (WHERE c.estado = 'cancelada')  AS citas_canceladas
FROM groomers g
LEFT JOIN citas c ON c.groomer_id = g.id
GROUP BY g.id, g.nombre, DATE(c.fecha_hora_inicio);

-- Reporte: Ticket por cita
CREATE OR REPLACE VIEW v_ticket_por_cita AS
SELECT
    c.id AS cita_id,
    c.fecha_hora_inicio,
    g.nombre AS groomer,
    m.nombre AS mascota,
    s.nombre AS servicio,
    f.subtotal,
    f.impuesto,
    f.total,
    f.estado AS estado_factura
FROM citas c
JOIN groomers g  ON c.groomer_id  = g.id
JOIN mascotas m  ON c.mascota_id  = m.id
JOIN servicios s ON c.servicio_id = s.id
LEFT JOIN facturas f ON f.cita_id = c.id;

-- Reporte: Top 10 servicios
CREATE OR REPLACE VIEW v_top_servicios AS
SELECT
    s.id,
    s.nombre,
    COUNT(c.id) AS total_citas,
    SUM(f.total) AS ingresos_totales
FROM servicios s
JOIN citas c    ON c.servicio_id = s.id
LEFT JOIN facturas f ON f.cita_id = c.id AND f.estado = 'pagada'
WHERE c.estado = 'completada'
GROUP BY s.id, s.nombre
ORDER BY total_citas DESC
LIMIT 10;

-- Reporte: Top 10 productos
CREATE OR REPLACE VIEW v_top_productos AS
SELECT
    p.id,
    p.nombre,
    SUM(dp.cantidad) AS total_vendido,
    SUM(dp.cantidad * dp.precio_unitario) AS ingresos_totales
FROM productos p
JOIN detalle_pedido dp ON dp.producto_id = p.id
JOIN pedidos ped       ON dp.pedido_id = ped.id
WHERE ped.estado IN ('pagado','entregado')
GROUP BY p.id, p.nombre
ORDER BY total_vendido DESC
LIMIT 10;

-- Reporte: Clientes frecuentes
CREATE OR REPLACE VIEW v_clientes_frecuentes AS
SELECT
    cl.id AS cliente_id,
    cl.nombre,
    COUNT(DISTINCT c.id) AS total_visitas,
    COALESCE(SUM(f.total), 0) AS gasto_total
FROM clientes cl
LEFT JOIN mascota_dueno md ON md.cliente_id = cl.id
LEFT JOIN mascotas m       ON m.id = md.mascota_id
LEFT JOIN citas c          ON c.mascota_id = m.id AND c.estado = 'completada'
LEFT JOIN facturas f       ON f.cita_id = c.id AND f.estado = 'pagada'
GROUP BY cl.id, cl.nombre
ORDER BY total_visitas DESC, gasto_total DESC;

-- Reporte: Inventario crítico
CREATE OR REPLACE VIEW v_inventario_critico AS
SELECT
    id,
    nombre,
    sku,
    stock,
    stock_minimo,
    (stock_minimo - stock) AS unidades_faltantes
FROM productos
WHERE stock <= stock_minimo AND activo = TRUE
ORDER BY (stock_minimo - stock) DESC;

-- Reporte: Satisfacción clientes
CREATE OR REPLACE VIEW v_satisfaccion_clientes AS
SELECT
    DATE_TRUNC('month', e.creado_en) AS mes,
    ROUND(AVG(e.calificacion), 2) AS promedio_estrellas,
    ROUND(AVG(e.nps), 2) AS promedio_nps,
    COUNT(*) AS total_encuestas
FROM encuestas e
WHERE e.respondida = TRUE
GROUP BY DATE_TRUNC('month', e.creado_en)
ORDER BY mes DESC;

-- Dashboard ejecutivo: KPIs del día
CREATE OR REPLACE VIEW v_dashboard_ejecutivo AS
SELECT
    CURRENT_DATE AS fecha,
    (SELECT COUNT(*) FROM citas WHERE DATE(fecha_hora_inicio) = CURRENT_DATE) AS citas_hoy,
    (SELECT COUNT(*) FROM citas WHERE DATE(fecha_hora_inicio) = CURRENT_DATE AND estado = 'completada') AS citas_completadas_hoy,
    (SELECT COUNT(*) FROM citas WHERE DATE(fecha_hora_inicio) = CURRENT_DATE AND estado = 'cancelada') AS citas_canceladas_hoy,
    (SELECT COALESCE(SUM(total),0) FROM facturas WHERE DATE(fecha_emision) = CURRENT_DATE AND estado = 'pagada') AS ingresos_hoy,
    (SELECT COUNT(*) FROM productos WHERE stock <= stock_minimo AND activo = TRUE) AS productos_bajo_stock,
    (SELECT COUNT(*) FROM notificaciones WHERE estado = 'pendiente' AND fecha_programacion <= NOW()) AS notificaciones_pendientes;


-- =============================================================================
-- 20. ÍNDICES ADICIONALES DE RENDIMIENTO
-- =============================================================================

CREATE INDEX idx_citas_fecha_groomer  ON citas(groomer_id, fecha_hora_inicio);
CREATE INDEX idx_facturas_fecha       ON facturas(fecha_emision);
CREATE INDEX idx_notif_estado_fecha   ON notificaciones(estado, fecha_programacion);
CREATE INDEX idx_historial_tipo       ON historial_mascota(tipo_evento);
CREATE INDEX idx_sesiones_expiracion  ON user_sessions(fecha_expiracion);


-- =============================================================================
-- FIN DEL SCRIPT
-- =============================================================================
-- NOTAS DE IMPLEMENTACIÓN:
-- 1. Motor recomendado: PostgreSQL 15+
-- 2. Ejecutar como superusuario o con permisos CREATE
-- 3. Jobs programados recomendados (pg_cron o externo):
--    - Cada hora:  procesar notificaciones pendientes
--    - Cada día:   fn_limpiar_carritos_expirados(), backup
--    - Cada hora:  recordatorios 24h y 2h antes de cita
-- 4. Para encriptación AES-256 de datos sensibles usar pgcrypto
-- 5. Rate limiting y CSRF implementar a nivel de API (no SQL)
-- 6. sucursal_id en tablas permite expansión multi-sucursal
-- =============================================================================
