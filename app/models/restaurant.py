from sqlalchemy import Column, Integer, String, ForeignKey, Time
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import BaseModel
 
class Restaurant(BaseModel):
    """
    Tabla de restaurantes.
    Almacena información de los restaurantes registrados en la plataforma.
    """
    __tablename__ = "restaurants"
    
    id = Column(Integer, primary_key=True, index=True)
    
    nombre = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Nombre del restaurante"
    )
    
    descripcion = Column(
        String(1000),
        nullable=True,
        doc="Descripción del restaurante"
    )
    
    direccion = Column(
        String(500),
        nullable=False,
        doc="Dirección del restaurante"
    )
    
    telefono = Column(
        String(20),
        nullable=False,
        doc="Número de teléfono del restaurante"
    )
    
    email = Column(
        String(255),
        nullable=False,
        doc="Email del restaurante"
    )
    
    admin_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del usuario administrador del restaurante"
    )
    
    hora_apertura = Column(
        Time,
        nullable=False,
        doc="Hora de apertura del restaurante (HH:MM)"
    )
    
    hora_cierre = Column(
        Time,
        nullable=False,
        doc="Hora de cierre del restaurante (HH:MM)"
    )
    
    total_mesas = Column(
        Integer,
        nullable=False,
        default=10,
        doc="Total de mesas disponibles en el restaurante"
    )
    
    # Relaciones
    admin = relationship(
        "User",
        back_populates="restaurantes",
        foreign_keys=[admin_id],
        doc="Usuario administrador del restaurante"
    )
    
    menus = relationship(
        "Menu",
        back_populates="restaurante",
        cascade="all, delete-orphan",
        doc="Menús/platos del restaurante"
    )
    
    reservas = relationship(
        "Reservation",
        back_populates="restaurante",
        cascade="all, delete-orphan",
        doc="Reservas del restaurante"
    )
    
    pedidos = relationship(
        "Order",
        back_populates="restaurante",
        cascade="all, delete-orphan",
        doc="Pedidos del restaurante"
    )
    
    def __repr__(self):
        return f"<Restaurant(id={self.id}, nombre={self.nombre}, admin_id={self.admin_id})>"