from sqlalchemy.orm import Session
from app.dao.base_dao import BaseDAO
from app.models.restaurant import Restaurant

# Implementacion de postgres para los restaurantes
class PostgreSQLRestaurantDAO(BaseDAO):

    def __init__(self, session: Session):
        self.session = session

    # Todos los queries de lectura

    #Regresa el restaurante con el id dado, el primero que encuentre
    def get_by_id(self, restaurant_id: int) -> Restaurant | None:
        return self.session.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    #Regresa el restaurante con el email dado, el primero que encuentre
    def get_by_email(self, email: str) -> Restaurant | None:
        return self.session.query(Restaurant).filter(Restaurant.email == email).first()

    #Retorna todos los restaurantes en la bd, sin filtro
    def get_all(self) -> list[Restaurant]:
        return self.session.query(Restaurant).all()

    #Retorna todos los restaurantes que tengan el admin_id dado, osea los restaurantes de un admin especifico
    def get_by_admin(self, admin_id: int) -> list[Restaurant]:
        return self.session.query(Restaurant).filter(Restaurant.admin_id == admin_id).all()

    # Escritura


    # Crea un restaurante en la bd usando orm, recibe un dict con los datos del restaurante y hace el commit para que se guarde en la bd
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

    #Nuevamente actualiza solo que viene en data
    def update(self, restaurant: Restaurant, data: dict) -> Restaurant:
        for field, value in data.items():
            setattr(restaurant, field, value)
        self.session.commit()
        self.session.refresh(restaurant)
        return restaurant

    #Delete fisico con cascade a menus, reservas y pedidos cuando se borra
    def delete(self, restaurant: Restaurant) -> Restaurant:
        self.session.delete(restaurant)
        self.session.commit()
        return restaurant