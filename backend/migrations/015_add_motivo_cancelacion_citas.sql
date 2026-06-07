-- Migration 015: store cancellation reason on citas if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='citas' AND column_name='motivo_cancelacion'
    ) THEN
        ALTER TABLE citas
        ADD COLUMN motivo_cancelacion TEXT;
    END IF;
END
$$;
