from app.models.user import RoleEnum
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate
from fastapi import HTTPException


# Logica de negocio

def create_restaurant(dao, user_dao, restaurant_data: RestaurantCreate, admin_id: int) -> Restaurant | None:
    """Valida permisos y email único antes de crear y delega al DAO."""
    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        return None

    if admin_user.rol != RoleEnum.ADMIN:
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
        "admin_id": admin_id,
    })


def validate_restaurant_admin(user_dao, admin_id: int, restaurant) -> None:
    """Valida que `admin_id` corresponde a un admin y dueño del restaurante.
    Lanza HTTPException en caso de error."""
    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden modificar restaurantes")

    if restaurant.admin_id != admin_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para modificar este restaurante")