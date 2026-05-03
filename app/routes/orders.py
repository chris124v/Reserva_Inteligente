from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.config import settings
from app.schemas.order import OrderCreate, OrderCreateRequest, OrderItem, OrderResponse
from app.dao.factory import DAOFactory
from app.models.user import RoleEnum
from app.services.user_service import resolve_current_local_user_id
from app.services.order_service import create_order

#Ruta de los pedidos
router = APIRouter(prefix="/orders", tags=["orders"])

#Daos para todas dependencias
def get_order_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_order_dao(settings.DATABASE_TYPE, db)

def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)

def get_restaurant_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_restaurant_dao(settings.DATABASE_TYPE, db)

def get_menu_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_menu_dao(settings.DATABASE_TYPE, db)

#Metodo para resolver usuario local 
def _resolve_user(current_user, user_dao):
    from fastapi import HTTPException
    usuario_id = resolve_current_local_user_id(current_user, user_dao)
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    local_user = user_dao.get_by_id(usuario_id)
    if not local_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
    return local_user

#Ruta para crear un nuevo pedido, si o si tiene que ser cliente entonces se valida como tal
@router.post("/", response_model=OrderResponse, status_code=201)
async def crear_pedido(
    order_data: OrderCreateRequest,
    restaurante_id: int = Query(..., ge=1),
    menu_id: int = Query(..., ge=1),
    current_user: dict = Depends(verify_jwt),
    order_dao=Depends(get_order_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao),
    menu_dao=Depends(get_menu_dao)
):
    local_user = _resolve_user(current_user, user_dao)

    if local_user.rol != RoleEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Solo clientes pueden crear pedidos")

    #Se valida tambien que sea de un restaurante real
    restaurante = restaurant_dao.get_by_id(restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    #Creamos el pedido
    order_to_create = OrderCreate(
        restaurante_id=restaurante_id,
        items=[OrderItem(menu_id=menu_id, cantidad=order_data.cantidad)],
        tipo_entrega=order_data.tipo_entrega,
        direccion_entrega=order_data.direccion_entrega,
        notas=order_data.notas,
    )

    return create_order(order_dao, None, restaurant_dao, menu_dao, order_to_create, local_user.id)

#Ruta para listar todos los pedidos que tenga el usuario cliente
@router.get("/", response_model=list[OrderResponse])
async def listar_mis_pedidos(
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    order_dao=Depends(get_order_dao),
    user_dao=Depends(get_user_dao)
):
    local_user = _resolve_user(current_user, user_dao)
    orders = order_dao.get_by_usuario(local_user.id)
    return orders[skip: skip + limit]

#Ruta para listar los pedidos de un restaurante, en especifico, si o si deben ser admins
@router.get("/restaurante/{restaurante_id}", response_model=list[OrderResponse])
async def listar_pedidos_restaurante(
    restaurante_id: int,
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    order_dao=Depends(get_order_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao)
):
    local_user = _resolve_user(current_user, user_dao)

    if local_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo admins pueden ver pedidos por restaurante")

    restaurante = restaurant_dao.get_by_id(restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver los pedidos de este restaurante")

    orders = order_dao.get_by_restaurante(restaurante_id)
    return orders[skip: skip + limit]
