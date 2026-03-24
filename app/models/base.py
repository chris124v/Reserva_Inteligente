from datetime import datetime
from sqlalchemy import Column, DateTime
from app.database.connection import Base

class BaseModel(Base):
    """
    Clase base para todos los modelos.
    Proporciona campos comunes: id, fecha_creacion, fecha_actualizacion
    """
    __abstract__ = True
    
    fecha_creacion = Column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False,
        doc="Fecha y hora de creación del registro"
    )
    
    fecha_actualizacion = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Fecha y hora de última actualizacion"
    )