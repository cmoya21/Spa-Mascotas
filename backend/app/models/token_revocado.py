import uuid

from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db


class TokenRevocado(db.Model):
    __tablename__ = "tokens_revocados"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    jti = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    usuario_id = db.Column(UUID(as_uuid=True), nullable=False)
    revocado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    expira_en = db.Column(db.DateTime, nullable=False)
