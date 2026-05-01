from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.config import settings
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.dao.factory import DAOFactory
from app.services.user_service import resolve_current_local_user_id
from app.services.restaurant_service import create_restaurant, validate_restaurant_admin

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_restaurant_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_restaurant_dao(settings.DATABASE_TYPE, db)

def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)


@router.post("/", response_model=RestaurantResponse, status_code=201)
async def crear_restaurante(
    restaurant_data: RestaurantCreate,
    current_user: dict = Depends(verify_jwt),
    restaurant_dao=Depends(get_restaurant_dao),
    user_dao=Depends(get_user_dao)
):
    admin_id = resolve_current_local_user_id(current_user, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    # Validar rol antes de crear
    admin_user = user_dao.get_by_id(admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no sincronizado en BD local")

    from app.models.user import RoleEnum
    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden crear restaurantes")

    if restaurant_dao.get_by_email(restaurant_data.email):
        raise HTTPException(status_code=400, detail="Ya existe un restaurante registrado con ese email")

    db_restaurant = create_restaurant(restaurant_dao, user_dao, restaurant_data, admin_id)
    if not db_restaurant:
        raise HTTPException(status_code=400, detail="Error al crear el restaurante")

    return db_restaurant


@router.get("/", response_model=list[RestaurantResponse])
async def listar_restaurantes(
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    restaurant_dao=Depends(get_restaurant_dao)
):
    restaurants = restaurant_dao.get_all()
    return restaurants[skip: skip + limit]


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def actualizar_restaurante(
    restaurant_id: int,
    restaurant_update: RestaurantUpdate,
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

    if restaurant_update.email and restaurant_update.email != db_restaurant.email:
        if restaurant_dao.get_by_email(restaurant_update.email):
            raise HTTPException(status_code=400, detail="Ya existe un restaurante con ese email")

    update_data = restaurant_update.model_dump(exclude_unset=True)
    return restaurant_dao.update(db_restaurant, update_data)


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
    return None