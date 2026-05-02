from types import SimpleNamespace

from app.dao.base_dao import BaseDAO
from app.models.user import RoleEnum

#Implementacion mongo del DAO de usuarios
class MongoDBUserDAO(BaseDAO):

    def __init__(self, db):
        # db es la base de datos MongoDB (get_mongo_db())
        self.collection = db["users"]

    # Lectura

    def get_by_id(self, user_id: int):
        doc = self.collection.find_one({"id": user_id})
        return self._to_model(doc)

    def get_by_email(self, email: str):
        doc = self.collection.find_one({"email": email})
        return self._to_model(doc)

    def get_all(self) -> list:
        docs = self.collection.find()
        return [self._to_model(doc) for doc in docs]

    def get_first_admin(self):
        doc = self.collection.find_one({"rol": RoleEnum.ADMIN.value})
        return self._to_model(doc)

    # Escritura

    def create(self, data: dict):
        # Generar ID autoincremental simple
        last = self.collection.find_one(sort=[("id", -1)])
        new_id = (last["id"] + 1) if last else 1

        doc = {
            "id": new_id,
            "email": data["email"],
            "nombre": data["nombre"],
            "password_hash": data.get("password_hash", "cognito"),
            "rol": data.get("rol", RoleEnum.CLIENTE).value if hasattr(data.get("rol"), "value") else data.get("rol", "cliente"),
            "activo": data.get("activo", True)
        }
        self.collection.insert_one(doc)
        return self._to_model(doc)

    def update(self, user, data: dict):
        # Serializar enums si vienen en data
        serialized = {}
        for k, v in data.items():
            serialized[k] = v.value if hasattr(v, "value") else v

        self.collection.update_one({"id": user.id}, {"$set": serialized})
        return self.get_by_id(user.id)

    def delete(self, user):
        self.collection.delete_one({"id": user.id})
        return user

    def deactivate(self, user):
        self.collection.update_one({"id": user.id}, {"$set": {"activo": False}})
        return self.get_by_id(user.id)

    # Auxiliares para conversion

    def _to_model(self, doc: dict | None):
        """
        Convierte un documento de monguito a un objeto compatible
        con lo que esperan los services y routes.
        mongo por defecto retorna dicts, pero el resto del codigo claramente son objetos.
        """
        if doc is None:
            return None

        return SimpleNamespace(
            id=doc["id"],
            email=doc["email"],
            nombre=doc["nombre"],
            password_hash=doc.get("password_hash", "cognito"),
            rol=RoleEnum(doc["rol"]),
            activo=doc.get("activo", True),
        )