from app.database.connection import Base, engine
import app.models  # noqa: F401 

#Crea todas las tablas definidas en los modelos.
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

# Permite ejecutar este script desde la terminal
if __name__ == "__main__":
    init_db()
    print("Database tables created/verified successfully.")
