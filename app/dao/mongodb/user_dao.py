from types import SimpleNamespace

from app.dao.base_dao import BaseDAO
from app.models.user import RoleEnum

#Implementacion mongo del dao de usuarios
class MongoDBUserDAO(BaseDAO):

    def __init__(self, db):
        # db es la base de datos MongoDB (get_mongo_db())
        self.collection = db["users"]

    # Lectura

    #Busca un documento en mongo donde el campo id sea igual a user id
    def get_by_id(self, user_id: int):
        doc = self.collection.find_one({"id": user_id})
        return self._to_model(doc) #Convierte el documento de mongo a un objeto compatible con lo que esperan los services y routes que es el modelo ya definido.

    #Busca un documento en mongo donde el campo email sea igual a email
    def get_by_email(self, email: str):
        doc = self.collection.find_one({"email": email})
        return self._to_model(doc)

    #Obtiene todos los documentos en mongo
    def get_all(self) -> list:
        docs = self.collection.find()
        return [self._to_model(doc) for doc in docs]

    #Obtiene el primer documento en mongo donde el campo rol sea igual a admin
    def get_first_admin(self):
        doc = self.collection.find_one({"rol": RoleEnum.ADMIN.value})
        return self._to_model(doc)

    # Escritura

    def create(self, data: dict):
        # Generar ID autoincremental simple, busca el usuario con el id mas alto y lo que hace es sumarle 1
        last = self.collection.find_one(sort=[("id", -1)])
        new_id = (last["id"] + 1) if last else 1

        #Aqui armamos el docu
        doc = {
            "id": new_id,
            "email": data["email"],
            "nombre": data["nombre"],
            "password_hash": data.get("password_hash", "cognito"),
            "rol": data.get("rol", RoleEnum.CLIENTE).value if hasattr(data.get("rol"), "value") else data.get("rol", "cliente"),
            "activo": data.get("activo", True)
        }
        self.collection.insert_one(doc) #Inserta el documento en mongo
        return self._to_model(doc) #Convierte el documento de mongo a un objeto 

    # Serializar enums si vienen en data, osea si tiene serialized es que se pueden cambiar y los actualiza
    def update(self, user, data: dict):
        serialized = {}
        for k, v in data.items():
            serialized[k] = v.value if hasattr(v, "value") else v

        self.collection.update_one({"id": user.id}, {"$set": serialized})
        return self.get_by_id(user.id)

    # Eliminar documento de mongo donde el campo id sea igual a user id
    def delete(self, user):
        self.collection.delete_one({"id": user.id})
        return user

    #Deactivar usuario es lo que usamos en vez de eliminarlo, lo que hace es actualizar el campo activo a false, y luego retorna el usuario actualizado
    def deactivate(self, user):
        self.collection.update_one({"id": user.id}, {"$set": {"activo": False}})
        return self.get_by_id(user.id)

    # Auxiliares para conversion

    def _to_model(self, doc: dict | None):
        """
        Convierte un documento de monguito a un objeto compatible
        con lo que esperan los services y routes.
        mongo por defecto retorna dicts, entonces hay que convertirlo.
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