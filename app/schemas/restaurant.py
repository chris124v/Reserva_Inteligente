from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import time

# Base con los campos comunes
class RestaurantBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=1000)
    direccion: str = Field(..., min_length=1, max_length=500)
    telefono: str = Field(..., min_length=8, max_length=20)
    email: str = Field(..., max_length=255)
    hora_apertura: time
    hora_cierre: time
    total_mesas: int = Field(default=10, gt=0)

    @model_validator(mode='after')
    def validar_horario(self):
        if self.hora_cierre <= self.hora_apertura:
            raise ValueError("La hora de cierre debe ser después de la hora de apertura")
        return self

# Para crear un restaurante
class RestaurantCreate(RestaurantBase):
    pass

# Para actualizar (todos opcionales)
class RestaurantUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=1000)
    direccion: Optional[str] = Field(None, min_length=1, max_length=500)
    telefono: Optional[str] = Field(None, min_length=8, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    hora_apertura: Optional[time] = None
    hora_cierre: Optional[time] = None
    total_mesas: Optional[int] = Field(None, gt=0)

# Lo que devuelve la API
class RestaurantResponse(RestaurantBase):
    id: int
    admin_id: int

    class Config:
        from_attributes = True