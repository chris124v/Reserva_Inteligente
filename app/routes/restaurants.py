from unittest import result

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.config import settings
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.dao.factory import DAOFactory
from app.services.user_service import resolve_current_local_user_id
from app.services.restaurant_service import create_restaurant, validate_restaurant_admin
from app.services.cache_service import cache_service

# Ruta para gestionar restaurantes 
router = APIRouter(prefix="/restaurants", tags=["restaurants"])

#Dao para restaurantes
def get_restaurant_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_restaurant_dao(settings.DATABASE_TYPE, db)

#Dao para usuarios, necesario para validar permisos de admin sobre el restaurante
def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)

#Ruta para crear el restaurante
@router.post("/", response_model=RestaurantResponse, status_code=201)
async def crear_restaurante(
    restaurant_data: RestaurantCreate,
    current_user: dict = Depends(verify_jwt),
    restaurant_dao=Depends(get_restaurant_dao),
    user_dao=Depends(get_user_dao)
):  
    #Encontrar al usuario autenticado
    admin_id = resolve_current_local_user_id(current_user, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    # Busca el usuario local y sino esta tira la excepcion
    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no sincronizado en BD local")

    #Valida que si o si tiene que ser admin
    from app.models.user import RoleEnum
    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden crear restaurantes")

    #Si ya hay un email con registrado con un restaurante no se puede usar
    if restaurant_dao.get_by_email(restaurant_data.email):
        raise HTTPException(status_code=400, detail="Ya existe un restaurante registrado con ese email")

    #Creamos el restaurante
    db_restaurant = create_restaurant(restaurant_dao, user_dao, restaurant_data, admin_id)
    if not db_restaurant:
        raise HTTPException(status_code=400, detail="Error al crear el restaurante")

    #Invalida cache 
    cache_service.delete_pattern("restaurants:*")

    return db_restaurant

    

# Ruta para listar restaurantes usando cache de redis
@router.get("/", response_model=list[RestaurantResponse])
async def listar_restaurantes(
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    restaurant_dao=Depends(get_restaurant_dao)
):  
    # key unica basada en paginacion
    cache_key = f"restaurants:all:{skip}:{limit}"

    # Intenta obtener de cache
    cached_data = cache_service.get(cache_key)
    if cached_data:
        print(f"CACHE HIT - {cache_key}")
        return cached_data
    
    print(f"CACHE MISS - {cache_key}")

    #Consulta regular a la bd
    restaurants = restaurant_dao.get_all()
    result = restaurants[skip: skip + limit]

    # Guarda en cache 
    cache_service.set(cache_key, result)

    return result

    

# Ruta para actualuzar un restaurante, nuevamente solo el admin que creo el restaurante puede
@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def actualizar_restaurante(
    restaurant_id: int,
    restaurant_update: RestaurantUpdate,
    current_user: dict = Depends(verify_jwt),
    restaurant_dao=Depends(get_restaurant_dao),
    user_dao=Depends(get_user_dao)
):
    #En caso de no encontrar el restaurante
    db_restaurant = restaurant_dao.get_by_id(restaurant_id)
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    #Si el usuario no esta autenticado
    admin_id = resolve_current_local_user_id(current_user, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    #Verificar que es el dueno del restaurante 
    validate_restaurant_admin(user_dao, admin_id, db_restaurant)

    #Si se cambia el email y es igual que otro lanza la excepcion
    if restaurant_update.email and restaurant_update.email != db_restaurant.email:
        if restaurant_dao.get_by_email(restaurant_update.email):
            raise HTTPException(status_code=400, detail="Ya existe un restaurante con ese email")

    #Actualiza el restaurante
    update_data = restaurant_update.model_dump(exclude_unset=True)

    #Invalida cache
    cache_service.delete_pattern("restaurants:*")

    return restaurant_dao.update(db_restaurant, update_data)

#Metodo para borra el restaurante validamos que el usuario este autenticado y sea el dueno. 
@router.delete("/{restaurant_id}", status_code=204)
async def eliminar_restaurante(
    restaurant_id: int,
    current_user: dict = Depends(verify_jwt),
    restaurant_dao=Depends(get_restaurant_dao),
    user_dao=Depends(get_user_dao)
):
    db_restaurant = restaurant_dao.get_by_id(restaurant_id)
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    admin_id = resolve_current_local_user_id(current_user, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    validate_restaurant_admin(user_dao, admin_id, db_restaurant)

    restaurant_dao.delete(db_restaurant)

    #Invalida cache, consulta a las dbs asi no a redis
    cache_service.delete_pattern("restaurants:*")

    return None