from sqlalchemy import create_engine #Motor de conexión a la BD
from sqlalchemy.pool import QueuePool #Gestor de conexiones para manejar múltiples solicitudes concurrentes
from sqlalchemy.orm import declarative_base #Base para definir modelos ORM
import os
from dotenv import load_dotenv

#Archivo de conexión a la base de datos. Aquí se configura el engine y la base 

# Cargar variables de entorno
load_dotenv()

# Obtener URL de conexión desde variables de entorno
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:MySecurePass123!@db:5432/restaurantes_db"
)

# Crear engine de SQLAlchemy osea la conexion
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,              # Maximo 5 conexiones simultaneas
    max_overflow=10,          # Máximo 10 conexiones extras
    pool_pre_ping=True,       # Verifica que la conexión esté viva antes de usar
    echo=False                # True para ver logs SQL (desarrollo)
)

# Base para los modelos osea las tablas de la Bd
Base = declarative_base()

