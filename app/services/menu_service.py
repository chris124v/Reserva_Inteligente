from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.schemas.menu import MenuCreate, MenuUpdate

def get_menu(db: Session, menu_id: int):
    return db.query(Menu).filter(Menu.id == menu_id).first()

def get_menus_by_restaurante(db: Session, restaurante_id: int):
    return db.query(Menu).filter(Menu.restaurante_id == restaurante_id).all()

def get_all_menus(db: Session):
    return db.query(Menu).all()

def create_menu(db: Session, menu: MenuCreate):
    db_menu = Menu(
        nombre=menu.nombre,
        descripcion=menu.descripcion,
        precio=menu.precio,
        disponible=menu.disponible,
        tiempo_preparacion=menu.tiempo_preparacion,
        categoria=menu.categoria,
        restaurante_id=menu.restaurante_id
    )
    db.add(db_menu)
    db.commit()
    db.refresh(db_menu)
    return db_menu

def update_menu(db: Session, menu_id: int, menu: MenuUpdate):
    db_menu = get_menu(db, menu_id)
    if not db_menu:
        return None

    update_data = menu.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_menu, field, value)

    db.commit()
    db.refresh(db_menu)
    return db_menu

def delete_menu(db: Session, menu_id: int):
    db_menu = get_menu(db, menu_id)
    if not db_menu:
        return None
    db.delete(db_menu)
    db.commit()
    return db_menu