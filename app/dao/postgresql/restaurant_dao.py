from sqlalchemy.orm import Session
from app.dao.base_dao import BaseDAO
from app.models.restaurant import Restaurant

# Implementacion de postgres para los restaurantes
class PostgreSQLRestaurantDAO(BaseDAO):

    def __init__(self, session: Session):
        self.session = session

    # Todos los queries de lectura

    def get_by_id(self, restaurant_id: int) -> Restaurant | None:
        return self.session.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    def get_by_email(self, email: str) -> Restaurant | None:
        return self.session.query(Restaurant).filter(Restaurant.email == email).first()

    def get_all(self) -> list[Restaurant]:
        return self.session.query(Restaurant).all()

    def get_by_admin(self, admin_id: int) -> list[Restaurant]:
        return self.session.query(Restaurant).filter(Restaurant.admin_id == admin_id).all()

    # Escritura

    def create(self, data: dict) -> Restaurant:
        restaurant = Restaurant(
            nombre=data["nombre"],
            descripcion=data.get("descripcion"),
            direccion=data["direccion"],
            telefono=data.get("telefono"),
            email=data["email"],
            hora_apertura=data["hora_apertura"],
            hora_cierre=data["hora_cierre"],
            total_mesas=data["total_mesas"],
            admin_id=data["admin_id"]
        )
        self.session.add(restaurant)
        self.session.commit()
        self.session.refresh(restaurant)
        return restaurant

    def update(self, restaurant: Restaurant, data: dict) -> Restaurant:
        for field, value in data.items():
            setattr(restaurant, field, value)
        self.session.commit()
        self.session.refresh(restaurant)
        return restaurant

    #Delete fisico con cascade a menus, reservas y pedidos
    def delete(self, restaurant: Restaurant) -> Restaurant:
        self.session.delete(restaurant)
        self.session.commit()
        return restaurant