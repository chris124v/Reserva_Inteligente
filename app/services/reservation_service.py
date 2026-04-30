from sqlalchemy.orm import Session
from datetime import date, time
from app.models.reservation import Reservation, EstadoReservaEnum
from app.schemas.reservation import ReservationCreate

def get_reservation(db: Session, reservation_id: int):
    """Busca una reserva por su ID. Retorna None si no existe."""
    return db.query(Reservation).filter(Reservation.id == reservation_id).first()

def get_reservations_by_usuario(db: Session, usuario_id: int):
    """Retorna todas las reservas de un usuario específico."""
    return db.query(Reservation).filter(Reservation.usuario_id == usuario_id).all()

def get_reservations_by_restaurante(db: Session, restaurante_id: int):
    """Retorna todas las reservas de un restaurante específico."""
    return db.query(Reservation).filter(Reservation.restaurante_id == restaurante_id).all()

def check_disponibilidad(db: Session, restaurante_id: int, fecha: date, hora: time, total_mesas: int):
    """
    Verifica si hay mesas disponibles en un restaurante para una fecha y hora dadas.
    
    Cuenta cuántas reservas activas (reservadas) existen para ese restaurante
    en esa fecha. Si el número de reservas es menor al total de mesas, hay disponibilidad.
    """
    reservas_activas = db.query(Reservation).filter(
        Reservation.restaurante_id == restaurante_id,
        Reservation.fecha == fecha,
        Reservation.estado == EstadoReservaEnum.RESERVADA,
    ).count()

    # Retorna True si hay al menos una mesa libre
    return reservas_activas < total_mesas


def _asignar_numero_mesa(db: Session, restaurante_id: int, fecha: date, total_mesas: int) -> int | None:
    """Asigna el menor número de mesa libre para ese restaurante y día."""
    mesas_ocupadas = {
        n
        for (n,) in db.query(Reservation.numero_mesa)
        .filter(
            Reservation.restaurante_id == restaurante_id,
            Reservation.fecha == fecha,
            Reservation.estado == EstadoReservaEnum.RESERVADA,
            Reservation.numero_mesa.isnot(None),
        )
        .all()
    }

    for numero in range(1, total_mesas + 1):
        if numero not in mesas_ocupadas:
            return numero
    return None

def create_reservation(db: Session, reservation: ReservationCreate, usuario_id: int, total_mesas: int):
    """
    Crea una nueva reserva si hay disponibilidad.
    
    Primero verifica que haya mesas libres en la fecha y hora solicitadas.
    Si no hay disponibilidad, retorna None para que el route maneje el error.
    """
    # Verificamos disponibilidad antes de crear la reserva
    hay_disponibilidad = check_disponibilidad(
        db,
        restaurante_id=reservation.restaurante_id,
        fecha=reservation.fecha,
        hora=reservation.hora,
        total_mesas=total_mesas
    )

    if not hay_disponibilidad:
        return None  # El route se encarga de lanzar el 400

    numero_mesa = _asignar_numero_mesa(db, reservation.restaurante_id, reservation.fecha, total_mesas)
    if numero_mesa is None:
        return None

    db_reservation = Reservation(
        usuario_id=usuario_id,
        restaurante_id=reservation.restaurante_id,
        fecha=reservation.fecha,
        hora=reservation.hora,
        cantidad_personas=reservation.cantidad_personas,
        notas=reservation.notas,
        estado=EstadoReservaEnum.RESERVADA,
        numero_mesa=numero_mesa,
    )
    db.add(db_reservation)
    db.commit()
    db.refresh(db_reservation)
    return db_reservation

def cancel_reservation(db: Session, reservation_id: int):
    """
    Cancela una reserva cambiando su estado a CANCELADA.
    No se elimina el registro para mantener el historial.
    Retorna None si la reserva no existe.
    """
    db_reservation = get_reservation(db, reservation_id)
    if not db_reservation:
        return None

    db_reservation.estado = EstadoReservaEnum.CANCELADA
    db.commit()
    db.refresh(db_reservation)
    return db_reservation