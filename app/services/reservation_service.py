from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, time
from app.models.reservation import Reservation, EstadoReservaEnum
from app.schemas.reservation import ReservationCreate


_reservation_enum_migrated = False


def _ensure_postgres_reservation_enum(db: Session) -> None:
    """One-time, best-effort migration for PostgreSQL enum values.

    Fixes existing DBs that still have legacy enum labels (pendiente/confirmada/...).
    - Adds enum label 'reservada' if missing
    - Updates existing rows to 'reservada'
    - Sets column default to 'reservada'
    """
    global _reservation_enum_migrated
    if _reservation_enum_migrated:
        return

    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        _reservation_enum_migrated = True
        return

    with bind.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        type_exists = conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'estadoreservaenum' LIMIT 1")
        ).scalar()

        if not type_exists:
            _reservation_enum_migrated = True
            return

        labels = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT e.enumlabel
                    FROM pg_type t
                    JOIN pg_enum e ON t.oid = e.enumtypid
                    WHERE t.typname = 'estadoreservaenum'
                    """
                )
            ).all()
        }

        if "reservada" not in labels:
            conn.execute(text("ALTER TYPE estadoreservaenum ADD VALUE 'reservada'"))

        if "cancelada" not in labels:
            conn.execute(text("ALTER TYPE estadoreservaenum ADD VALUE 'cancelada'"))

        # Map legacy states (old labels) to the new labels.
        conn.execute(
            text(
                """
                UPDATE reservations
                SET estado = 'reservada'
                WHERE estado::text IN ('pendiente', 'confirmada', 'completada', 'PENDIENTE', 'CONFIRMADA', 'COMPLETADA')
                """
            )
        )

        conn.execute(
            text(
                """
                UPDATE reservations
                SET estado = 'cancelada'
                WHERE estado::text IN ('CANCELADA')
                """
            )
        )

        conn.execute(
            text("ALTER TABLE reservations ALTER COLUMN estado SET DEFAULT 'reservada'")
        )

    _reservation_enum_migrated = True

def get_reservation(db: Session, reservation_id: int):
    """Busca una reserva por su ID. Retorna None si no existe."""
    _ensure_postgres_reservation_enum(db)
    return db.query(Reservation).filter(Reservation.id == reservation_id).first()

def get_reservations_by_usuario(db: Session, usuario_id: int):
    """Retorna todas las reservas de un usuario específico."""
    _ensure_postgres_reservation_enum(db)
    return db.query(Reservation).filter(Reservation.usuario_id == usuario_id).all()

def get_reservations_by_restaurante(db: Session, restaurante_id: int):
    """Retorna todas las reservas de un restaurante específico."""
    _ensure_postgres_reservation_enum(db)
    return db.query(Reservation).filter(Reservation.restaurante_id == restaurante_id).all()

def check_disponibilidad(db: Session, restaurante_id: int, fecha: date, hora: time, total_mesas: int):
    """
    Verifica si hay mesas disponibles en un restaurante para una fecha y hora dadas.
    
    Cuenta cuántas reservas activas (reservadas) existen para ese restaurante
    en esa fecha. Si el número de reservas es menor al total de mesas, hay disponibilidad.
    """
    _ensure_postgres_reservation_enum(db)

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
    _ensure_postgres_reservation_enum(db)

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
    _ensure_postgres_reservation_enum(db)

    db_reservation = get_reservation(db, reservation_id)
    if not db_reservation:
        return None

    db_reservation.estado = EstadoReservaEnum.CANCELADA
    db.commit()
    db.refresh(db_reservation)
    return db_reservation