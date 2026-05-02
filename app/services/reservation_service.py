from datetime import date, time
from app.models.reservation import EstadoReservaEnum
from app.schemas.reservation import ReservationCreate


def check_disponibilidad(reservation_dao, restaurante_id: int, fecha: date, total_mesas: int) -> bool:
    """Lógica de negocio: verifica si hay mesas libres."""
    reservas_activas = reservation_dao.count_reservas_activas(restaurante_id, fecha)
    return reservas_activas < total_mesas


def _asignar_numero_mesa(reservation_dao, restaurante_id: int, fecha: date, total_mesas: int) -> int | None:
    """Lógica de negocio: elige la mesa más baja disponible."""
    mesas_ocupadas = reservation_dao.get_mesas_ocupadas(restaurante_id, fecha)
    for numero in range(1, total_mesas + 1):
        if numero not in mesas_ocupadas:
            return numero
    return None


def create_reservation(reservation_dao, reservation: ReservationCreate, usuario_id: int, total_mesas: int):
    """Valida disponibilidad, asigna mesa y crea la reserva."""
    if not check_disponibilidad(reservation_dao, reservation.restaurante_id, reservation.fecha, total_mesas):
        return None

    numero_mesa = _asignar_numero_mesa(reservation_dao, reservation.restaurante_id, reservation.fecha, total_mesas)
    if numero_mesa is None:
        return None

    return reservation_dao.create({
        "usuario_id": usuario_id,
        "restaurante_id": reservation.restaurante_id,
        "fecha": reservation.fecha,
        "hora": reservation.hora,
        "cantidad_personas": reservation.cantidad_personas,
        "notas": reservation.notas,
        "numero_mesa": numero_mesa,
    })


def validate_reservation_owner(reservation, usuario_id: int) -> None:
    """Valida que el usuario sea dueño de la reserva."""
    from fastapi import HTTPException
    if reservation.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para modificar esta reserva")


def validate_reservation_cancelable(reservation) -> None:
    """Valida que la reserva esté en estado cancelable."""
    from fastapi import HTTPException
    if reservation.estado.value != "reservada":
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar una reserva en estado {reservation.estado.value}"
        )