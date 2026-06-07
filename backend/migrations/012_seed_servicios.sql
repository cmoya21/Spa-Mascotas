INSERT INTO productos (nombre, sku, precio_base, stock, stock_minimo)
VALUES
  ('Shampoo hipoalergénico 1L', 'SHP-001', 25.00, 20, 5),
  ('Acondicionador 500ml',      'ACO-001', 18.00, 15, 5),
  ('Perfume para mascotas',     'PRF-001', 12.00, 30, 10)
ON CONFLICT (sku) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  precio_base = EXCLUDED.precio_base,
  stock = GREATEST(productos.stock, EXCLUDED.stock),
  stock_minimo = EXCLUDED.stock_minimo,
  activo = true;

UPDATE servicios
SET descripcion = 'Baño express con secado básico.',
    precio_base = 50.00,
    duracion_base_minutos = 30,
    factor_tamano_raza = '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
    consumo_insumos = jsonb_build_array(jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.05)),
    activo = true
WHERE nombre = 'Baño rápido';
INSERT INTO servicios (nombre, descripcion, precio_base, duracion_base_minutos, factor_tamano_raza, consumo_insumos, activo)
SELECT
  'Baño rápido',
  'Baño express con secado básico.',
  50.00,
  30,
  '{"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}',
  jsonb_build_array(jsonb_build_object('producto_id', (SELECT id FROM productos WHERE sku = 'SHP-001' LIMIT 1), 'cantidad', 0.05)),
  true
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
    activo = true
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
  true
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
    activo = true
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
  true
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
    activo = true
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
  true
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Servicio completo');

DELETE FROM checklist_items_template cit USING servicios s WHERE cit.servicio_id = s.id AND s.nombre IN ('Baño rápido', 'Baño completo', 'Corte y peinado', 'Servicio completo');

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
