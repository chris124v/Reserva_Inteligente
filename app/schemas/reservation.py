from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional
from datetime import date, time, datetime
from app.models.reservation import EstadoReservaEnum

# Base con los campos comunes
class ReservationBase(BaseModel):
    restaurante_id: int
    fecha: date
    hora: time
    cantidad_personas: int = Field(..., gt=0, le=20)
    notas: Optional[str] = Field(None, max_length=500)

# Para crear una reserva
class ReservationCreate(ReservationBase):

    @model_validator(mode='after')
    def validar_fecha_futura(self):
        fecha_hora = datetime.combine(self.fecha, self.hora)
        if fecha_hora <= datetime.now():
            raise ValueError("La reserva debe ser en una fecha y hora futura")
        return self

# Para cancelar una reserva
class ReservationCancel(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)

# Para actualizar (admin puede cambiar estado y mesa)
class ReservationUpdate(BaseModel):
    estado: Optional[EstadoReservaEnum] = None
    numero_mesa: Optional[int] = Field(None, gt=0)
    notas: Optional[str] = Field(None, max_length=500)

# Lo que devuelve la API
class ReservationResponse(ReservationBase):
    id: int
    usuario_id: int
    estado: EstadoReservaEnum
    numero_mesa: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)