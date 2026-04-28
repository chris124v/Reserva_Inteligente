from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Base con los campos comunes
class MenuBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=500)
    precio: float = Field(..., gt=0)
    disponible: bool = True
    tiempo_preparacion: Optional[int] = Field(None, gt=0)  # en minutos
    categoria: Optional[str] = Field(None, max_length=100)

# Request para crear un plato (restaurante_id se pasa por parámetro, no en el body)
class MenuCreateRequest(MenuBase):
    pass

# Para crear un plato (requiere restaurante_id)
class MenuCreate(MenuBase):
    restaurante_id: int

# Para actualizar (todos los campos opcionales)
class MenuUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=500)
    precio: Optional[float] = Field(None, gt=0)
    disponible: Optional[bool] = None
    tiempo_preparacion: Optional[int] = Field(None, gt=0)
    categoria: Optional[str] = Field(None, max_length=100)

# Lo que devuelve la API (incluye id)
class MenuResponse(MenuBase):
    id: int
    restaurante_id: int

    model_config = ConfigDict(from_attributes=True)