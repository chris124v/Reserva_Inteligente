from app.models.user import RoleEnum
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


def get_restaurant(dao, restaurant_id: int) -> Restaurant | None:
    """Obtiene un restaurante por ID"""
    return dao.get_by_id(restaurant_id)


def get_restaurant_by_email(dao, email: str) -> Restaurant | None:
    """Obtiene un restaurante por email"""
    return dao.get_by_email(email)


def get_all_restaurants(dao) -> list[Restaurant]:
    """Obtiene todos los restaurantes"""
    return dao.get_all()


def create_restaurant(dao, user_dao, restaurant_data: RestaurantCreate, admin_id: int) -> Restaurant | None:
    """Valida permisos y email único antes de crear."""
    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        return None

    existing = dao.get_by_email(restaurant_data.email)
    if existing:
        return None

    return dao.create({
        "nombre": restaurant_data.nombre,
        "descripcion": restaurant_data.descripcion,
        "direccion": restaurant_data.direccion,
        "telefono": restaurant_data.telefono,
        "email": restaurant_data.email,
        "hora_apertura": restaurant_data.hora_apertura,
        "hora_cierre": restaurant_data.hora_cierre,
        "total_mesas": restaurant_data.total_mesas,
        "admin_id": admin_id
    })


def validate_restaurant_admin(user_dao, admin_id: int, restaurant) -> None:
    """
    Valida que el usuario autenticado sea admin y dueño del restaurante.
    Lanza HTTPException si no tiene permiso.
    """
    from fastapi import HTTPException

    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden modificar restaurantes")

    if restaurant.admin_id != admin_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para modificar este restaurante")


def update_restaurant(dao, restaurant_id: int, restaurant_data: RestaurantUpdate) -> Restaurant | None:
    """Actualiza un restaurante"""
    restaurant = dao.get_by_id(restaurant_id)
    if not restaurant:
        return None
    
    update_data = restaurant_data.model_dump(exclude_unset=True)
    return dao.update(restaurant_id, update_data)


def delete_restaurant(dao, restaurant_id: int) -> bool:
    """Elimina un restaurante"""
    restaurant = dao.get_by_id(restaurant_id)
    if not restaurant:
        return False
    
    dao.delete(restaurant_id)
    return True