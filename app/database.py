import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Pega a URL do banco da nuvem (.env). Se não tiver, usa o SQLite local de forma segura.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "quadrinhos.db").replace("\\", "/"))

# Ajuste automático caso o serviço na nuvem (como Render/Neon) forneça "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# A engine muda dependendo de ser SQLite (local) ou Postgres (nuvem)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrar_banco():
    from sqlalchemy import inspect, text
    with engine.begin() as conn:
        if 'colecao' not in {c['name'] for c in inspect(conn).get_columns('quadrinhos')}:
            conn.execute(text('ALTER TABLE quadrinhos ADD COLUMN colecao VARCHAR'))
        conn.execute(text("UPDATE quadrinhos SET isbn = NULL WHERE TRIM(isbn) = ''"))
