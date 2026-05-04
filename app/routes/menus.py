from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.config import settings
from app.schemas.menu import MenuCreate, MenuCreateRequest, MenuUpdate, MenuResponse
from app.dao.factory import DAOFactory
from app.services.user_service import resolve_current_local_user_id
from app.services.menu_service import validate_menu_admin
from typing import List
from app.services.cache_service import cache_service

#Ruta de menus
router = APIRouter(prefix="/menus", tags=["menus"])

#Metodos para obtener los daos necesarios
def get_menu_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_menu_dao(settings.DATABASE_TYPE, db)

def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)

def get_restaurant_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_restaurant_dao(settings.DATABASE_TYPE, db)

#Ruta para listar todos los menus dispobonibles, si se pide id restaurante se pasa sino todo bien
@router.get("/", response_model=List[MenuResponse])
async def listar_menus(
    restaurante_id: int = None,
    menu_dao=Depends(get_menu_dao)
):  
    if restaurante_id:
        cache_key = f"menus:restaurant:{restaurante_id}"
    else:
        cache_key = "menus:all"

    cached_data = cache_service.get(cache_key)
    if cached_data is not None:
        print(f"CACHE HIT - {cache_key}")
        return cached_data

    print(f"CACHE MISS - {cache_key}")

    if restaurante_id:
        result = menu_dao.get_by_restaurante(restaurante_id)
    else:
        result = menu_dao.get_all()

    cache_service.set(cache_key, result)

    return result

#Ruta para obtener menu por id en especifico
@router.get("/{menu_id}", response_model=MenuResponse)
async def obtener_menu(
    menu_id: int,
    menu_dao=Depends(get_menu_dao)
):
    cache_key = f"menu:{menu_id}"

    cached_data = cache_service.get(cache_key)
    if cached_data is not None:
        print(f"CACHE HIT - {cache_key}")
        return cached_data

    print(f"CACHE MISS - {cache_key}")

    menu = menu_dao.get_by_id(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menú no encontrado")

    cache_service.set(cache_key, menu)

    return menu

#Ruta para crear un menu, validamos que sea admin y
@router.post("/", response_model=MenuResponse, status_code=201)
async def crear_menu(
    menu: MenuCreateRequest,
    restaurante_id: int = Query(..., gt=0),
    payload: dict = Depends(verify_jwt),
    menu_dao=Depends(get_menu_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao)
):
    admin_id = resolve_current_local_user_id(payload, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    validate_menu_admin(user_dao, restaurant_dao, admin_id, restaurante_id)

    nuevo_menu = menu_dao.create({
        **menu.model_dump(),
        "restaurante_id": restaurante_id
    })

    #Invalidamos cache

    cache_service.delete_pattern("menus:*")
    cache_service.delete_pattern("menu:*")

    return nuevo_menu

#Ruta para actualizar un menu, vemos que exista y que sea un usuario autenticado
@router.put("/{menu_id}", response_model=MenuResponse)
async def actualizar_menu(
    menu_id: int,
    menu: MenuUpdate,
    payload: dict = Depends(verify_jwt),
    menu_dao=Depends(get_menu_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao)
):
    menu_existente = menu_dao.get_by_id(menu_id)
    if not menu_existente:
        raise HTTPException(status_code=404, detail="Menú no encontrado")

    admin_id = resolve_current_local_user_id(payload, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    validate_menu_admin(user_dao, restaurant_dao, admin_id, menu_existente.restaurante_id)

    menu_actualizado = menu_dao.update(menu_existente, menu.model_dump(exclude_unset=True))

    #Invalidamos cache
    cache_service.delete_pattern("menus:*")
    cache_service.delete_pattern("menu:*")

    return menu_actualizado

#Ruta para borrar un emnu, validamos que exista y que sea un usuario autenticado
@router.delete("/{menu_id}", status_code=204)
async def eliminar_menu(
    menu_id: int,
    payload: dict = Depends(verify_jwt),
    menu_dao=Depends(get_menu_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao)
):
    menu_existente = menu_dao.get_by_id(menu_id)
    if not menu_existente:
        raise HTTPException(status_code=404, detail="Menú no encontrado")

    admin_id = resolve_current_local_user_id(payload, user_dao)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    validate_menu_admin(user_dao, restaurant_dao, admin_id, menu_existente.restaurante_id)

    menu_dao.delete(menu_existente)

    cache_service.delete_pattern("menus:*")
    cache_service.delete_pattern("menu:*")
    
    return None