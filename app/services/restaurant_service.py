from app.models.user import RoleEnum
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate
from fastapi import HTTPException


# Logica de negocio

# Valida permisos y email único antes de crear y delega al dao.
def create_restaurant(dao, user_dao, restaurant_data: RestaurantCreate, admin_id: int) -> Restaurant | None:
    admin_user = user_dao.get_by_id(admin_id) #Solo los admins pueden hacer restaurantes
    if not admin_user:
        return None

    #Si el usuario no es admin, no tiene permisos para crear restaurantes
    if admin_user.rol != RoleEnum.ADMIN:
        return None

    #Verificamos que no exista un restaurante con el mismo email, si existe retornamos None
    existing = dao.get_by_email(restaurant_data.email)
    if existing:
        return None

    #Creamos el restaurante con los datos necesarios y retornamos el restaurante creado todo delegado al dao
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

#Valida que admin_id corresponde a un admin y dueño del restaurante.
def validate_restaurant_admin(user_dao, admin_id: int, restaurant) -> None:
    
    admin_user = user_dao.get_by_id(admin_id)
    
    #Lanzamos excepciones para cada caso si no es el dueno del restaurante o si ni squeria es admin
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden modificar restaurantes")

    if restaurant.admin_id != admin_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para modificar este restaurante")