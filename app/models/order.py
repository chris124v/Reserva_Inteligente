from sqlalchemy import Column, Integer, Float, ForeignKey, Enum, String, JSON
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import BaseModel
import enum
 
class EstadoPedidoEnum(str, enum.Enum):
    """Estados posibles de un pedido"""
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    EN_PREPARACION = "en_preparacion"
    LISTO = "listo"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
 
class TipoEntregaEnum(str, enum.Enum):
    """Tipos de entrega disponibles"""
    DOMICILIO = "domicilio"
    RECOGIDA = "recogida"
    EN_RESTAURANTE = "en_restaurante"
 
class Order(BaseModel):
    """
    Tabla de pedidos.
    Almacena los pedidos realizados por usuarios en restaurantes.
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    usuario_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del usuario que realiza el pedido"
    )
    
    restaurante_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del restaurante del que se hace el pedido"
    )
    
    items = Column(
        JSON,
        nullable=False,
        doc="Items del pedido en formato JSON: [{'menu_id': 1, 'cantidad': 2}, ...]"
    )
    
    subtotal = Column(
        Float,
        nullable=False,
        doc="Subtotal del pedido sin impuestos"
    )
    
    impuesto = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Impuesto aplicado al pedido"
    )
    
    total = Column(
        Float,
        nullable=False,
        doc="Total del pedido incluyendo impuestos"
    )
    
    estado = Column(
        Enum(EstadoPedidoEnum),
        default=EstadoPedidoEnum.PENDIENTE,
        nullable=False,
        index=True,
        doc="Estado actual del pedido"
    )
    
    tipo_entrega = Column(
        Enum(TipoEntregaEnum),
        default=TipoEntregaEnum.RECOGIDA,
        nullable=False,
        doc="Tipo de entrega del pedido"
    )
    
    direccion_entrega = Column(
        String(500),
        nullable=True,
        doc="Dirección de entrega (si es domicilio)"
    )
    
    notas = Column(
        String(500),
        nullable=True,
        doc="Notas adicionales del pedido (preferencias, alergias, instrucciones especiales)"
    )
    
    # Relaciones
    usuario = relationship(
        "User",
        back_populates="pedidos",
        doc="Usuario que realizó el pedido"
    )
    
    restaurante = relationship(
        "Restaurant",
        back_populates="pedidos",
        doc="Restaurante del que se hizo el pedido"
    )
    
    def __repr__(self):
        return f"<Order(id={self.id}, usuario_id={self.usuario_id}, restaurante_id={self.restaurante_id}, total={self.total}, estado={self.estado})>"
 