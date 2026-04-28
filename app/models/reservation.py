from sqlalchemy import Column, Integer, Date, Time, ForeignKey, Enum, String
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import BaseModel
import enum
from datetime import datetime


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]
 
class EstadoReservaEnum(str, enum.Enum):
    """Estados posibles de una reserva"""
    RESERVADA = "reservada"
    CANCELADA = "cancelada"
 
class Reservation(BaseModel):
    """
    Tabla de reservas.
    Almacena las reservas de mesas en restaurantes.
    """
    __tablename__ = "reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    usuario_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del usuario que realiza la reserva"
    )
    
    restaurante_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del restaurante donde se hace la reserva"
    )
    
    fecha = Column(
        Date,
        nullable=False,
        index=True,
        doc="Fecha de la reserva (YYYY-MM-DD)"
    )
    
    hora = Column(
        Time,
        nullable=False,
        doc="Hora de la reserva (HH:MM)"
    )
    
    cantidad_personas = Column(
        Integer,
        nullable=False,
        doc="Cantidad de personas para la reserva"
    )
    
    estado = Column(
        Enum(
            EstadoReservaEnum,
            name="estadoreservaenum",
            values_callable=_enum_values,
        ),
        default=EstadoReservaEnum.RESERVADA,
        nullable=False,
        index=True,
        doc="Estado actual de la reserva"
    )
    
    notas = Column(
        String(500),
        nullable=True,
        doc="Notas adicionales de la reserva (preferencias especiales, alergias, etc.)"
    )
    
    numero_mesa = Column(
        Integer,
        nullable=True,
        doc="Número de mesa asignada (se asigna cuando se confirma)"
    )
    
    # Relaciones
    usuario = relationship(
        "User",
        back_populates="reservas",
        doc="Usuario que realizó la reserva"
    )
    
    restaurante = relationship(
        "Restaurant",
        back_populates="reservas",
        doc="Restaurante donde se realiza la reserva"
    )
    
    def __repr__(self):
        return f"<Reservation(id={self.id}, usuario_id={self.usuario_id}, restaurante_id={self.restaurante_id}, fecha={self.fecha}, hora={self.hora}, estado={self.estado})>"