from types import SimpleNamespace

from app.dao.base_dao import BaseDAO
from app.models.order import EstadoPedidoEnum

# Implementacion de mongo final dao para los pedidos
class MongoDBOrderDAO(BaseDAO):

    def __init__(self, db):
        self.collection = db["orders"]

    # Operaciones de lectura

    # Obtiene un id de pedido, retorna None si no existe
    def get_by_id(self, order_id: int):
        doc = self.collection.find_one({"id": order_id})
        return self._to_model(doc)

    #Obtiene todos los pedidos de un usuario, retorna lista vacia si no hay pedidos
    def get_by_usuario(self, usuario_id: int) -> list:
        docs = self.collection.find({"usuario_id": usuario_id})
        return [self._to_model(doc) for doc in docs]

    #Obtiene todos los pedidos de un restaurante, retorna lista vacia si no hay pedidos
    def get_by_restaurante(self, restaurante_id: int) -> list:
        docs = self.collection.find({"restaurante_id": restaurante_id})
        return [self._to_model(doc) for doc in docs]

    # Operaciones de escritura

    #Creacion de un pedido con los datos necesarios, retorna el pedido creado
    def create(self, data: dict):
        last = self.collection.find_one(sort=[("id", -1)])
        new_id = (last["id"] + 1) if last else 1

        doc = {
            "id": new_id,
            "usuario_id": data["usuario_id"],
            "restaurante_id": data["restaurante_id"],
            "items": data["items"],
            "subtotal": float(data["subtotal"]),
            "impuesto": float(data["impuesto"]),
            "total": float(data["total"]),
            "tipo_entrega": data["tipo_entrega"].value if hasattr(data["tipo_entrega"], "value") else data["tipo_entrega"],
            "direccion_entrega": data.get("direccion_entrega"),
            "notas": data.get("notas"),
            "estado": EstadoPedidoEnum.PENDIENTE.value
        }
        self.collection.insert_one(doc)
        return self._to_model(doc)

    #Updateamos lo que venga en data y lo convertimos a formato de mongo
    def update_estado(self, order, data: dict):
        serialized = {}
        for k, v in data.items():
            serialized[k] = v.value if hasattr(v, "value") else v

        self.collection.update_one({"id": order.id}, {"$set": serialized})
        return self.get_by_id(order.id)

    #Query para cancelar un pedido
    def cancel(self, order):
        self.collection.update_one(
            {"id": order.id},
            {"$set": {"estado": EstadoPedidoEnum.CANCELADO.value}}
        )
        return self.get_by_id(order.id)

    #Delete del pedido 
    def delete(self, order):
        self.collection.delete_one({"id": order.id})
        return order

    #Metodo generico que llama al update estado
    def update(self, order, data: dict):
        return self.update_estado(order, data)

    # Metodos auxiliares de conversion a modelo

    def _to_model(self, doc: dict | None):
        if doc is None:
            return None

        from app.models.order import TipoEntregaEnum

        return SimpleNamespace(
            id=doc["id"],
            usuario_id=doc["usuario_id"],
            restaurante_id=doc["restaurante_id"],
            items=doc["items"],
            subtotal=doc["subtotal"],
            impuesto=doc["impuesto"],
            total=doc["total"],
            tipo_entrega=TipoEntregaEnum(doc["tipo_entrega"]),
            direccion_entrega=doc.get("direccion_entrega"),
            notas=doc.get("notas"),
            estado=EstadoPedidoEnum(doc["estado"]),
        )