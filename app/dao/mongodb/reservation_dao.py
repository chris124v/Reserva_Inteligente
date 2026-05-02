from types import SimpleNamespace

from app.dao.base_dao import BaseDAO
from app.models.reservation import EstadoReservaEnum
from datetime import date, time

# Implementacion mongoDB para las reservas
class MongoDBReservationDAO(BaseDAO):

    def __init__(self, db):
        self.collection = db["reservations"]

    # Metodos de lectura

    def get_by_id(self, reservation_id: int):
        doc = self.collection.find_one({"id": reservation_id})
        return self._to_model(doc)

    def get_by_usuario(self, usuario_id: int) -> list:
        docs = self.collection.find({"usuario_id": usuario_id})
        return [self._to_model(doc) for doc in docs]

    def get_by_restaurante(self, restaurante_id: int) -> list:
        docs = self.collection.find({"restaurante_id": restaurante_id})
        return [self._to_model(doc) for doc in docs]

    def count_reservas_activas(self, restaurante_id: int, fecha: date) -> int:
        return self.collection.count_documents({
            "restaurante_id": restaurante_id,
            "fecha": str(fecha),
            "estado": EstadoReservaEnum.RESERVADA.value
        })

    def get_mesas_ocupadas(self, restaurante_id: int, fecha: date) -> set[int]:
        docs = self.collection.find(
            {
                "restaurante_id": restaurante_id,
                "fecha": str(fecha),
                "estado": EstadoReservaEnum.RESERVADA.value,
                "numero_mesa": {"$ne": None}
            },
            {"numero_mesa": 1, "_id": 0}
        )
        return {doc["numero_mesa"] for doc in docs}

    # Metodos de escritura

    def create(self, data: dict):
        last = self.collection.find_one(sort=[("id", -1)])
        new_id = (last["id"] + 1) if last else 1

        doc = {
            "id": new_id,
            "usuario_id": data["usuario_id"],
            "restaurante_id": data["restaurante_id"],
            "fecha": str(data["fecha"]),
            "hora": str(data["hora"]),
            "cantidad_personas": data["cantidad_personas"],
            "notas": data.get("notas"),
            "estado": EstadoReservaEnum.RESERVADA.value,
            "numero_mesa": data["numero_mesa"]
        }
        self.collection.insert_one(doc)
        return self._to_model(doc)

    def update(self, reservation, data: dict):
        serialized = {}
        for k, v in data.items():
            if hasattr(v, "value"):
                serialized[k] = v.value
            elif isinstance(v, (date, time)):
                serialized[k] = str(v)
            else:
                serialized[k] = v

        self.collection.update_one({"id": reservation.id}, {"$set": serialized})
        return self.get_by_id(reservation.id)

    def cancel(self, reservation):
        self.collection.update_one(
            {"id": reservation.id},
            {"$set": {"estado": EstadoReservaEnum.CANCELADA.value}}
        )
        return self.get_by_id(reservation.id)

    def delete(self, reservation):
        self.collection.delete_one({"id": reservation.id})
        return reservation

    # Metodos auxiliares

    def _to_model(self, doc: dict | None):
        if doc is None:
            return None

        def parse_date(val):
            if isinstance(val, date):
                return val
            return date.fromisoformat(val)

        def parse_time(val):
            if isinstance(val, time):
                return val
            h, m, s = (val.split(":") + ["0"])[:3]
            return time(int(h), int(m), int(s))

        return SimpleNamespace(
            id=doc["id"],
            usuario_id=doc["usuario_id"],
            restaurante_id=doc["restaurante_id"],
            fecha=parse_date(doc["fecha"]),
            hora=parse_time(doc["hora"]),
            cantidad_personas=doc["cantidad_personas"],
            notas=doc.get("notas"),
            estado=EstadoReservaEnum(doc["estado"]),
            numero_mesa=doc.get("numero_mesa"),
        )