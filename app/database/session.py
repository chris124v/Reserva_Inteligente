from sqlalchemy.orm import sessionmaker #Sesiones para preguntar a la BD
from app.database.connection import engine
 
# Crear session factory de sesiones
SessionLocal = sessionmaker(
    autocommit=False,         # No auto-commit, controla transacciones manualmente nos permite hacer rollback
    autoflush=False,          # No auto-flush de cambios
    bind=engine               # Conecta al engine
)
 
def get_db():
    """
    Dependencia para FastAPI.
    Proporciona una sesión de BD para cada request.
    Esto se llama cada que un endpoint necesita acceso a la BD
    """
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()