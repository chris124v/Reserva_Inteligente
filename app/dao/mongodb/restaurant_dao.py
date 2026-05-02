from types import SimpleNamespace

from app.dao.base_dao import BaseDAO

# Implementacin de monguito para los restaurantes
class MongoDBRestaurantDAO(BaseDAO):

    def __init__(self, db):
        self.collection = db["restaurants"]

    # Metodos de pura lectura

    def get_by_id(self, restaurant_id: int):
        doc = self.collection.find_one({"id": restaurant_id})
        return self._to_model(doc)

    def get_by_email(self, email: str):
        doc = self.collection.find_one({"email": email})
        return self._to_model(doc)

    def get_all(self) -> list:
        docs = self.collection.find()
        return [self._to_model(doc) for doc in docs]

    def get_by_admin(self, admin_id: int) -> list:
        docs = self.collection.find({"admin_id": admin_id})
        return [self._to_model(doc) for doc in docs]

    # Metodos de escritura

    def create(self, data: dict):
        last = self.collection.find_one(sort=[("id", -1)])
        new_id = (last["id"] + 1) if last else 1

        doc = {
            "id": new_id,
            "nombre": data["nombre"],
            "descripcion": data.get("descripcion"),
            "direccion": data["direccion"],
            "telefono": data.get("telefono"),
            "email": data["email"],
            "hora_apertura": str(data["hora_apertura"]),
            "hora_cierre": str(data["hora_cierre"]),
            "total_mesas": data["total_mesas"],
            "admin_id": data["admin_id"]
        }
        self.collection.insert_one(doc)
        return self._to_model(doc)

    def update(self, restaurant, data: dict):
        serialized = {}
        for k, v in data.items():
            serialized[k] = str(v) if hasattr(v, "hour") else v

        self.collection.update_one({"id": restaurant.id}, {"$set": serialized})
        return self.get_by_id(restaurant.id)

    def delete(self, restaurant):
        self.collection.delete_one({"id": restaurant.id})
        return restaurant

    # Metodos auxiliares de conversion y otros

    def _to_model(self, doc: dict | None):
        if doc is None:
            return None

        from app.models.restaurant import Restaurant
        from datetime import time

        def parse_time(val):
            if isinstance(val, time):
                return val
            if isinstance(val, str):
                h, m, s = (val.split(":") + ["0"])[:3]
                return time(int(h), int(m), int(s))
            return val

        return SimpleNamespace(
            id=doc["id"],
            nombre=doc["nombre"],
            descripcion=doc.get("descripcion"), 
            direccion=doc["direccion"],
            telefono=doc.get("telefono"),
            email=doc["email"],
            hora_apertura=parse_time(doc["hora_apertura"]),
            hora_cierre=parse_time(doc["hora_cierre"]),
            total_mesas=doc["total_mesas"],
            admin_id=doc["admin_id"],
        )