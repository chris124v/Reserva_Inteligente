from sqlalchemy.orm import Session
from app.dao.base_dao import BaseDAO
from app.models.menu import Menu

#Implementacion de postgres para los menus
class PostgreSQLMenuDAO(BaseDAO):

    def __init__(self, session: Session):
        self.session = session

    # Lectura

    #Obtiene un menu por si id
    def get_by_id(self, menu_id: int) -> Menu | None:
        return self.session.query(Menu).filter(Menu.id == menu_id).first()

    #Obtiene los menus de un restaurante al que pertence
    def get_by_restaurante(self, restaurante_id: int) -> list[Menu]:
        return self.session.query(Menu).filter(Menu.restaurante_id == restaurante_id).all()

    #Devuelve todos los menus disponibles en la bd de postgres
    def get_all(self) -> list[Menu]:
        return self.session.query(Menu).all()

    # Escritura

    # Crea un nuevo menu y hace el commit en la bd
    def create(self, data: dict) -> Menu:
        menu = Menu(
            nombre=data["nombre"],
            descripcion=data.get("descripcion"),
            precio=data["precio"],
            disponible=data.get("disponible", True),
            tiempo_preparacion=data.get("tiempo_preparacion"),
            categoria=data.get("categoria"),
            restaurante_id=data["restaurante_id"]
        )
        self.session.add(menu)
        self.session.commit()
        self.session.refresh(menu)
        return menu

    # Updatea un menu con lo que venga en data, esto lo definimos en schemas
    def update(self, menu: Menu, data: dict) -> Menu:
        for field, value in data.items():
            setattr(menu, field, value)
        self.session.commit()
        self.session.refresh(menu)
        return menu

    #Delete fisico del menu en la bd
    def delete(self, menu: Menu) -> Menu:
        self.session.delete(menu)
        self.session.commit()
        return menu