-- =============================================================================
-- DATOS DE PRUEBA: CITAS PENDIENTES / POR CONFIRMAR
-- Ejecutar sobre una base ya creada con roles, sucursales, servicios y tablas.
-- Este script es idempotente para pruebas locales.
-- =============================================================================

-- Usuario cliente de prueba
WITH rol_cliente AS (
    SELECT id FROM roles WHERE nombre = 'Cliente' LIMIT 1
),
u_cliente AS (
    INSERT INTO usuarios (email, password_hash, rol_id, estado_activo)
    SELECT 'cliente.prueba@spa.local', '$2b$12$C6UzMDM.H6dfI/f/IKcEe.1yqK2qQ6xqZfN1tFoZT3zh0AwBTtPlW', rol_cliente.id, TRUE
    FROM rol_cliente
    ON CONFLICT (email) DO UPDATE SET rol_id = EXCLUDED.rol_id
    RETURNING id
),
c_cliente AS (
    INSERT INTO clientes (usuario_id, nombre, apellido, telefono, direccion, canal_notificacion)
    SELECT id, 'Cliente', 'Prueba', '70000001', 'Zona Centro', 'whatsapp'
    FROM usuarios
    WHERE email = 'cliente.prueba@spa.local'
    ON CONFLICT (usuario_id) DO NOTHING
    RETURNING id, usuario_id
),
rol_groomer AS (
    SELECT id FROM roles WHERE nombre = 'Groomer' LIMIT 1
),
u_groomer AS (
    INSERT INTO usuarios (email, password_hash, rol_id, estado_activo)
    SELECT 'groomer.prueba@spa.local', '$2b$12$C6UzMDM.H6dfI/f/IKcEe.1yqK2qQ6xqZfN1tFoZT3zh0AwBTtPlW', rol_groomer.id, TRUE
    FROM rol_groomer
    ON CONFLICT (email) DO UPDATE SET rol_id = EXCLUDED.rol_id
    RETURNING id
),
g_groomer AS (
    INSERT INTO groomers (usuario_id, nombre, apellido, telefono, especialidad, capacidad_simultanea, capacidad_diaria, estado_activo)
    SELECT id, 'Ana', 'Groomer', '70000002', 'Baño y corte', 1, 8, TRUE
    FROM usuarios
    WHERE email = 'groomer.prueba@spa.local'
    ON CONFLICT (usuario_id) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        apellido = EXCLUDED.apellido,
        telefono = EXCLUDED.telefono,
        especialidad = EXCLUDED.especialidad,
        capacidad_simultanea = EXCLUDED.capacidad_simultanea,
        capacidad_diaria = EXCLUDED.capacidad_diaria,
        estado_activo = EXCLUDED.estado_activo
    RETURNING id, usuario_id
),
m_mascota AS (
    INSERT INTO mascotas (nombre, especie, raza, tamano, peso_kg, temperamento, observaciones)
    SELECT 'Bobby', 'Perro', 'Mestizo', 'mediano', 12.50, 'tranquilo', 'Mascota de prueba para citas'
    WHERE NOT EXISTS (
        SELECT 1 FROM mascotas WHERE nombre = 'Bobby' AND especie = 'Perro' AND raza = 'Mestizo'
    )
    RETURNING id
),
md_mascota_dueno AS (
    INSERT INTO mascota_dueno (mascota_id, cliente_id, es_principal)
    SELECT m.id, c.id, TRUE
    FROM mascotas m
    CROSS JOIN clientes c
    WHERE m.nombre = 'Bobby'
      AND c.usuario_id = (SELECT id FROM usuarios WHERE email = 'cliente.prueba@spa.local' LIMIT 1)
    ON CONFLICT (mascota_id, cliente_id) DO NOTHING
    RETURNING mascota_id, cliente_id
)
INSERT INTO citas (
    mascota_id,
    groomer_id,
    servicio_id,
    sucursal_id,
    fecha_hora_inicio,
    fecha_hora_fin,
    duracion_estimada,
    estado,
    precio_estimado,
    notas,
    creado_por
)
SELECT
    m.id,
    g.id,
    s.id,
    1,
    NOW() + INTERVAL '1 day' + INTERVAL '10 hour',
    NOW() + INTERVAL '1 day' + INTERVAL '11 hour',
    60,
    'pendiente',
    s.precio_base,
    'Cita pendiente de prueba',
    (SELECT id FROM usuarios WHERE email = 'cliente.prueba@spa.local' LIMIT 1)
FROM mascotas m
CROSS JOIN groomers g
CROSS JOIN servicios s
WHERE m.nombre = 'Bobby'
  AND g.usuario_id = (SELECT id FROM usuarios WHERE email = 'groomer.prueba@spa.local' LIMIT 1)
  AND s.nombre = 'Bano completo'
    AND NOT EXISTS (
            SELECT 1
            FROM citas c
            WHERE c.mascota_id = m.id
                AND c.groomer_id = g.id
                AND c.servicio_id = s.id
                AND c.estado = 'pendiente'
                AND c.notas = 'Cita pendiente de prueba'
    )
ON CONFLICT DO NOTHING;

INSERT INTO citas (
    mascota_id,
    groomer_id,
    servicio_id,
    sucursal_id,
    fecha_hora_inicio,
    fecha_hora_fin,
    duracion_estimada,
    estado,
    precio_estimado,
    notas,
    creado_por
)
SELECT
    m.id,
    g.id,
    s.id,
    1,
    NOW() + INTERVAL '2 day' + INTERVAL '15 hour',
    NOW() + INTERVAL '2 day' + INTERVAL '16 hour',
    60,
    'confirmada',
    s.precio_base,
    'Cita confirmada de prueba',
    (SELECT id FROM usuarios WHERE email = 'cliente.prueba@spa.local' LIMIT 1)
FROM mascotas m
CROSS JOIN groomers g
CROSS JOIN servicios s
WHERE m.nombre = 'Bobby'
  AND g.usuario_id = (SELECT id FROM usuarios WHERE email = 'groomer.prueba@spa.local' LIMIT 1)
  AND s.nombre = 'Bano completo'
    AND NOT EXISTS (
            SELECT 1
            FROM citas c
            WHERE c.mascota_id = m.id
                AND c.groomer_id = g.id
                AND c.servicio_id = s.id
                AND c.estado = 'confirmada'
                AND c.notas = 'Cita confirmada de prueba'
    )
ON CONFLICT DO NOTHING;
