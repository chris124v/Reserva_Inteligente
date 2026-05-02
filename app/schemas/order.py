from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from app.models.order import EstadoPedidoEnum, TipoEntregaEnum

# Schema para cada item dentro del pedido
class OrderItem(BaseModel):
    menu_id: int
    cantidad: int = Field(..., gt=0)


# Request simplificado para crear pedido (idss van por query params)
class OrderCreateRequest(BaseModel):
    cantidad: int = Field(1, gt=0)
    tipo_entrega: TipoEntregaEnum = TipoEntregaEnum.RECOGIDA
    direccion_entrega: Optional[str] = Field(None, max_length=500)
    notas: Optional[str] = Field(None, max_length=500)

# Base con los campos comunes
class OrderBase(BaseModel):
    restaurante_id: int
    items: List[OrderItem] = Field(..., min_length=1)
    tipo_entrega: TipoEntregaEnum = TipoEntregaEnum.RECOGIDA
    direccion_entrega: Optional[str] = Field(None, max_length=500)
    notas: Optional[str] = Field(None, max_length=500)

# Para crear un pedido
class OrderCreate(OrderBase):
    pass

# Para actualizar (solo estado y notas tiene sentido actualizar)
class OrderUpdate(BaseModel):
    estado: Optional[EstadoPedidoEnum] = None
    notas: Optional[str] = Field(None, max_length=500)

# Lo que devuelve la API
class OrderResponse(OrderBase):
    id: int
    usuario_id: int
    subtotal: float
    impuesto: float
    total: float
    estado: EstadoPedidoEnum

    model_config = ConfigDict(from_attributes=True)