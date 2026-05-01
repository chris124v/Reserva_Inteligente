from sqlalchemy.orm import Session
from app.dao.base_dao import BaseDAO
from app.models.order import Order, EstadoPedidoEnum

# Implementacion PostgreSQL del dao de pedidos.
class PostgreSQLOrderDAO(BaseDAO):

    def __init__(self, session: Session):
        self.session = session

    # Lectura

    def get_by_id(self, order_id: int) -> Order | None:
        return self.session.query(Order).filter(Order.id == order_id).first()

    def get_by_usuario(self, usuario_id: int) -> list[Order]:
        return self.session.query(Order).filter(Order.usuario_id == usuario_id).all()

    def get_by_restaurante(self, restaurante_id: int) -> list[Order]:
        return self.session.query(Order).filter(Order.restaurante_id == restaurante_id).all()

    # Escritura

    # Los precios se calculan en el service, el dao solo recibe el total final para guardar. 
    def create(self, data: dict) -> Order:
        
        order = Order(
            usuario_id=data["usuario_id"],
            restaurante_id=data["restaurante_id"],
            items=data["items"],
            subtotal=data["subtotal"],
            impuesto=data["impuesto"],
            total=data["total"],
            tipo_entrega=data["tipo_entrega"],
            direccion_entrega=data.get("direccion_entrega"),
            notas=data.get("notas"),
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    # El service se encarga de validar que el nuevo estado sea correcto, el dao solo lo actualiza.
    def update_estado(self, order: Order, data: dict) -> Order:
        for field, value in data.items():
            setattr(order, field, value)
        self.session.commit()
        self.session.refresh(order)
        return order

    #Cambia estado a cancelado sin eliminar el registro
    def cancel(self, order: Order) -> Order:
        order.estado = EstadoPedidoEnum.CANCELADO
        self.session.commit()
        self.session.refresh(order)
        return order

    #Delete real
    def delete(self, order: Order) -> Order:
        self.session.delete(order)
        self.session.commit()
        return order