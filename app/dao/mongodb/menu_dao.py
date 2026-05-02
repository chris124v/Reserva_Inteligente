from types import SimpleNamespace

from app.dao.base_dao import BaseDAO

# Dao para menus en mongo
class MongoDBMenuDAO(BaseDAO):

    def __init__(self, db):
        self.collection = db["menus"]

    # Todos los metodos de lectura

    #Obtiene un menu por su id
    def get_by_id(self, menu_id: int):
        doc = self.collection.find_one({"id": menu_id})
        return self._to_model(doc)

    #Obtiene los menus de un restaurante
    def get_by_restaurante(self, restaurante_id: int) -> list:
        docs = self.collection.find({"restaurante_id": restaurante_id})
        return [self._to_model(doc) for doc in docs]

    #Obtiene todos los menus
    def get_all(self) -> list:
        docs = self.collection.find()
        return [self._to_model(doc) for doc in docs]

    # Metodos de escritura

    #Metodo para crear un nuevo menu, hacemos lo mismo de subir +1 el id mas grande
    def create(self, data: dict):
        last = self.collection.find_one(sort=[("id", -1)])
        new_id = (last["id"] + 1) if last else 1

        doc = {
            "id": new_id,
            "nombre": data["nombre"],
            "descripcion": data.get("descripcion"),
            "precio": float(data["precio"]),
            "disponible": data.get("disponible", True),
            "tiempo_preparacion": data.get("tiempo_preparacion"),
            "categoria": data.get("categoria"),
            "restaurante_id": data["restaurante_id"]
        }
        self.collection.insert_one(doc)
        return self._to_model(doc)

    #Updateamos lo que nos pasa data en schemas
    def update(self, menu, data: dict):
        self.collection.update_one({"id": menu.id}, {"$set": data})
        return self.get_by_id(menu.id)

    #Deleteamos el menu que nos pasan
    def delete(self, menu):
        self.collection.delete_one({"id": menu.id})
        return menu

    # Conversion del doc a un modelo easy money

    def _to_model(self, doc: dict | None):
        if doc is None:
            return None

        return SimpleNamespace(
            id=doc["id"],
            nombre=doc["nombre"],
            descripcion=doc.get("descripcion"),
            precio=doc["precio"],
            disponible=doc.get("disponible", True),
            tiempo_preparacion=doc.get("tiempo_preparacion"),
            categoria=doc.get("categoria"),
            restaurante_id=doc["restaurante_id"],
        )