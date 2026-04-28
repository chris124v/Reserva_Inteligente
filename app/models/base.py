from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from app.database.connection import Base


def _utcnow_naive() -> datetime:
    # Avoid datetime.utcnow deprecation while keeping naive UTC datetimes. significa que no tienen información de zona horaria, pero se asume que están en UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)

class BaseModel(Base):
    """
    Clase base para todos los modelos.
    Proporciona campos comunes: id, fecha_creacion, fecha_actualizacion
    """
    __abstract__ = True
    
    fecha_creacion = Column(
        DateTime, 
        default=_utcnow_naive,
        nullable=False,
        doc="Fecha y hora de creación del registro"
    )
    
    fecha_actualizacion = Column(
        DateTime,
        default=_utcnow_naive,
        onupdate=_utcnow_naive,
        nullable=False,
        doc="Fecha y hora de última actualizacion"
    )