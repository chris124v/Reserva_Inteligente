from sqlalchemy.orm import Session
from datetime import date, time
from app.dao.base_dao import BaseDAO
from app.models.reservation import Reservation, EstadoReservaEnum

#Implementacion postgre dao para reservas 
class PostgreSQLReservationDAO(BaseDAO):

    def __init__(self, session: Session):
        self.session = session

    # Lectura sencilla

    #Retorna una reserva por su id, o None si no existe
    def get_by_id(self, reservation_id: int) -> Reservation | None:
        return self.session.query(Reservation).filter(Reservation.id == reservation_id).first()

    #Retorna las reservas de un usuario, esto es para el endpoint de ver mis reservas
    def get_by_usuario(self, usuario_id: int) -> list[Reservation]:
        return self.session.query(Reservation).filter(Reservation.usuario_id == usuario_id).all()

    #Retorna las reservas de un restaurante, esto es para el endpoint de ver reservas del restaurante y asi el admin puede ver que atender
    def get_by_restaurante(self, restaurante_id: int) -> list[Reservation]:
        return self.session.query(Reservation).filter(Reservation.restaurante_id == restaurante_id).all()

    # este metodo cuenta reservas activas para un restaurante en una fecha, es para verificar disponibilidad
    def count_reservas_activas(self, restaurante_id: int, fecha: date) -> int:
        
        return self.session.query(Reservation).filter(
            Reservation.restaurante_id == restaurante_id,
            Reservation.fecha == fecha,
            Reservation.estado == EstadoReservaEnum.RESERVADA,
        ).count()

    # Retorna el conjunto de numeros de mesa ocupados.
    def get_mesas_ocupadas(self, restaurante_id: int, fecha: date) -> set[int]:

        rows = self.session.query(Reservation.numero_mesa).filter(
            Reservation.restaurante_id == restaurante_id,
            Reservation.fecha == fecha,
            Reservation.estado == EstadoReservaEnum.RESERVADA,
            Reservation.numero_mesa.isnot(None),
        ).all() #Devuelve lista en tuplas pero las convertimos
        return {n for (n,) in rows}

    # Queries de escritura

    # Crea una nueva reserva y hace el commit en la bd
    def create(self, data: dict) -> Reservation:
        reservation = Reservation(
            usuario_id=data["usuario_id"],
            restaurante_id=data["restaurante_id"],
            fecha=data["fecha"],
            hora=data["hora"],
            cantidad_personas=data["cantidad_personas"],
            notas=data.get("notas"),
            estado=EstadoReservaEnum.RESERVADA,
            numero_mesa=data["numero_mesa"],
        )
        self.session.add(reservation)
        self.session.commit()
        self.session.refresh(reservation)
        return reservation

    #Cambia estado a cancelada sin eliminar el registro, mas que todo para la implementacion del endpoint
    def cancel(self, reservation: Reservation) -> Reservation:
        reservation.estado = EstadoReservaEnum.CANCELADA
        self.session.commit()
        self.session.refresh(reservation)
        return reservation

    # Delete real en postgres
    def delete(self, reservation: Reservation) -> Reservation:
        self.session.delete(reservation)
        self.session.commit()
        return reservation