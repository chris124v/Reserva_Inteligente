from datetime import date, time
from app.models.reservation import EstadoReservaEnum
from app.schemas.reservation import ReservationCreate

#Logica de negocio y validaciones de reservas

# Verifica si hay mesas libres, usamos queries del dao para contar reservas activas y mesas ocupadas
def check_disponibilidad(reservation_dao, restaurante_id: int, fecha: date, total_mesas: int) -> bool:
    
    reservas_activas = reservation_dao.count_reservas_activas(restaurante_id, fecha)
    return reservas_activas < total_mesas

# Elije el numero de mesa mas bajo disponible, si no hay mesas retorna None
def _asignar_numero_mesa(reservation_dao, restaurante_id: int, fecha: date, total_mesas: int) -> int | None:
    
    mesas_ocupadas = reservation_dao.get_mesas_ocupadas(restaurante_id, fecha)
    for numero in range(1, total_mesas + 1):
        if numero not in mesas_ocupadas:
            return numero
    return None

# Valida disponibilidad, asigna mesa y crea la reserva.
def create_reservation(reservation_dao, reservation: ReservationCreate, usuario_id: int, total_mesas: int):

    if not check_disponibilidad(reservation_dao, reservation.restaurante_id, reservation.fecha, total_mesas):
        return None

    numero_mesa = _asignar_numero_mesa(reservation_dao, reservation.restaurante_id, reservation.fecha, total_mesas)
    if numero_mesa is None:
        return None

    # Crear la reserva con el número de mesa asignado delegado al daooo
    return reservation_dao.create({
        "usuario_id": usuario_id,
        "restaurante_id": reservation.restaurante_id,
        "fecha": reservation.fecha,
        "hora": reservation.hora,
        "cantidad_personas": reservation.cantidad_personas,
        "notas": reservation.notas,
        "numero_mesa": numero_mesa,
    })

# Valida que el usuario sea dueño de la reserva, si no lo es no puede actualizar nada
def validate_reservation_owner(reservation, usuario_id: int) -> None:
    
    from fastapi import HTTPException
    if reservation.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para modificar esta reserva")


#Valida que no se pueda cancelar algo que ya esta cancelado
def validate_reservation_cancelable(reservation) -> None:
    from fastapi import HTTPException
    if reservation.estado.value != "reservada":
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar una reserva en estado {reservation.estado.value}"
        )