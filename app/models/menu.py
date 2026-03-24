from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import BaseModel
 
class Menu(BaseModel):
    """
    Tabla de menús/platos.
    Almacena los platos disponibles en cada restaurante.
    """
    __tablename__ = "menus"
    
    id = Column(Integer, primary_key=True, index=True)
    
    nombre = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Nombre del plato"
    )
    
    descripcion = Column(
        Text,
        nullable=True,
        doc="Descripción detallada del plato"
    )
    
    precio = Column(
        Float,
        nullable=False,
        doc="Precio del plato en moneda local"
    )
    
    disponible = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Indica si el plato está disponible para pedir"
    )
    
    restaurante_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del restaurante al que pertenece este plato"
    )
    
    tiempo_preparacion = Column(
        Integer,
        nullable=True,
        doc="Tiempo de preparación en minutos"
    )
    
    categoria = Column(
        String(100),
        nullable=True,
        doc="Categoría del plato (entrada, plato principal, postre, bebida, etc.)"
    )
    
    # Relaciones
    restaurante = relationship(
        "Restaurant",
        back_populates="menus",
        doc="Restaurante al que pertenece este plato"
    )
    
    def __repr__(self):
        return f"<Menu(id={self.id}, nombre={self.nombre}, precio={self.precio})>"