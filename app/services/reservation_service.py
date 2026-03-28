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
    
    Cuenta cuántas reservas activas (pendientes o confirmadas) existen para ese
    restaurante en esa fecha y hora. Si el número de reservas es menor al total
    de mesas, hay disponibilidad.
    """
    reservas_activas = db.query(Reservation).filter(
        Reservation.restaurante_id == restaurante_id,
        Reservation.fecha == fecha,
        Reservation.hora == hora,
        Reservation.estado.in_([
            EstadoReservaEnum.PENDIENTE,
            EstadoReservaEnum.CONFIRMADA
        ])
    ).count()

    # Retorna True si hay al menos una mesa libre
    return reservas_activas < total_mesas

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

    db_reservation = Reservation(
        usuario_id=usuario_id,
        restaurante_id=reservation.restaurante_id,
        fecha=reservation.fecha,
        hora=reservation.hora,
        cantidad_personas=reservation.cantidad_personas,
        notas=reservation.notas
        # estado queda en PENDIENTE por defecto (definido en el modelo)
        # numero_mesa se asigna después cuando se confirme
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

def confirm_reservation(db: Session, reservation_id: int, numero_mesa: int):
    """
    Confirma una reserva y le asigna un número de mesa.
    Solo el admin del restaurante debería poder hacer esto.
    Retorna None si la reserva no existe.
    """
    db_reservation = get_reservation(db, reservation_id)
    if not db_reservation:
        return None

    db_reservation.estado = EstadoReservaEnum.CONFIRMADA
    db_reservation.numero_mesa = numero_mesa
    db.commit()
    db.refresh(db_reservation)
    return db_reservation