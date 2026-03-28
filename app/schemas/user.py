from pydantic import BaseModel, Field
from typing import Optional
from app.models.user import RoleEnum

# Base con los campos comunes
class UserBase(BaseModel):
    email: str = Field(..., max_length=255)
    nombre: str = Field(..., min_length=1, max_length=255)

# Para crear un usuario
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    rol: RoleEnum = RoleEnum.CLIENTE

# Para actualizar (todos opcionales)
class UserUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    activo: Optional[bool] = None

# Lo que devuelve la API
class UserResponse(UserBase):
    id: int
    rol: RoleEnum
    activo: bool

    class Config:
        from_attributes = True