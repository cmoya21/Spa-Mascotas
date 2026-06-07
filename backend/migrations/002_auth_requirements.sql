-- Add fields required by authentication requirements

ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS email_verificado_en TIMESTAMP;

ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS ci VARCHAR(30),
ADD COLUMN IF NOT EXISTS direccion TEXT;

ALTER TABLE empleados
ADD COLUMN IF NOT EXISTS turno VARCHAR(50);

-- Optional: mark existing admins as verified
UPDATE usuarios
SET email_verificado = TRUE, email_verificado_en = NOW()
WHERE email = 'admin@spamascotas.com';
