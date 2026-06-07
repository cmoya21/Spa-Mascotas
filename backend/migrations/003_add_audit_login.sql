-- Create audit_login table required by auth module

CREATE TABLE IF NOT EXISTS audit_login (
    id           BIGSERIAL PRIMARY KEY,
    usuario_id   UUID REFERENCES usuarios(id),
    email_intent VARCHAR(150),
    ip_address   INET,
    user_agent   TEXT,
    exitoso      BOOLEAN NOT NULL,
    motivo_fallo VARCHAR(100),
    ocurrido_en  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_login_usuario ON audit_login(usuario_id, ocurrido_en);
CREATE INDEX IF NOT EXISTS idx_audit_login_ip ON audit_login(ip_address, ocurrido_en);
