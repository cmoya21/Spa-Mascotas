-- Migration 014: add carnet_vacunas_url to mascotas if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='mascotas' AND column_name='carnet_vacunas_url'
    ) THEN
        ALTER TABLE mascotas
        ADD COLUMN carnet_vacunas_url TEXT;
    END IF;
END
$$;

-- Ensure tamano constraint (only create if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'mascotas' AND c.conname = 'chk_mascotas_tamano'
    ) THEN
        ALTER TABLE mascotas
        ADD CONSTRAINT chk_mascotas_tamano CHECK (tamano IN ('pequeno','mediano','grande','gigante'));
    END IF;
END
$$;
