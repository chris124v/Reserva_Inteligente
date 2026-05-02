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

router = APIRouter(prefix="/menus", tags=["menus"])


def get_menu_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_menu_dao(settings.DATABASE_TYPE, db)

def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)

def get_restaurant_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_restaurant_dao(settings.DATABASE_TYPE, db)


@router.get("/", response_model=List[MenuResponse])
async def listar_menus(
    restaurante_id: int = None,
    menu_dao=Depends(get_menu_dao)
):
    if restaurante_id:
        return menu_dao.get_by_restaurante(restaurante_id)
    return menu_dao.get_all()


@router.get("/{menu_id}", response_model=MenuResponse)
async def obtener_menu(
    menu_id: int,
    menu_dao=Depends(get_menu_dao)
):
    menu = menu_dao.get_by_id(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menú no encontrado")
    return menu


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
    return nuevo_menu


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

    return menu_dao.update(menu_existente, menu.model_dump(exclude_unset=True))


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
    return None