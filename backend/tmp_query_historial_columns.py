import os
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv('.env')
url = os.getenv('DATABASE_URL')
print('DATABASE_URL=', url)
engine = sa.create_engine(url)
with engine.connect() as conn:
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'historial_mascota' ORDER BY ordinal_position;"))
    for row in result:
        print(row[0])
