from sqlalchemy import Boolean, Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import BaseModel
import enum

class RoleEnum(str, enum.Enum):
    """Roles de usuarios en el sistema"""
    CLIENTE = "cliente"
    ADMIN = "admin"

class User(BaseModel):
    """
    Tabla de usuarios.
    Almacena información de clientes y administradores de restaurantes.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Email único del usuario"
    )
    
    nombre = Column(
        String(255),
        nullable=False,
        doc="Nombre completo del usuario"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Hash de la contraseña (almacenado de forma segura)"
    )
    
    rol = Column(
        Enum(RoleEnum),
        default=RoleEnum.CLIENTE,
        nullable=False,
        doc="Rol del usuario: cliente o admin"
    )
    
    activo = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Indica si el usuario está activo"
    )
    
    # Relaciones
    restaurantes = relationship(
        "Restaurant",
        back_populates="admin",
        foreign_keys="Restaurant.admin_id",
        doc="Restaurantes administrados por este usuario (si es admin)"
    )
    
    reservas = relationship(
        "Reservation",
        back_populates="usuario",
        cascade="all, delete-orphan",
        doc="Reservas realizadas por este usuario"
    )
    
    pedidos = relationship(
        "Order",
        back_populates="usuario",
        cascade="all, delete-orphan",
        doc="Pedidos realizados por este usuario"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, rol={self.rol})>"