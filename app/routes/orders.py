from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.auth.cognito import CognitoClient
from app.config import settings
from app.schemas.order import OrderCreate, OrderCreateRequest, OrderItem, OrderResponse
from app.services.user_service import (
    get_user,
    get_user_by_email,
    resolve_current_local_user_id,
)
from app.services.restaurant_service import get_restaurant
from app.services.menu_service import get_menu
from app.models.user import RoleEnum
from app.services.order_service import (
    get_orders_by_usuario,
    get_orders_by_restaurante,
    create_order,
)

router = APIRouter(prefix="/orders", tags=["orders"])
cognito_client = CognitoClient()


@router.post("/", response_model=OrderResponse, status_code=201)
async def crear_pedido(
    order_data: OrderCreateRequest,
    restaurante_id: int = Query(..., ge=1),
    menu_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Crea un nuevo pedido para el usuario autenticado.
    
    Solo lo pueden crear los clientes.
    """
    try:
        # Obtener usuario_id del JWT
        usuario_id = resolve_current_local_user_id(current_user, db)
        
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")

        local_user = get_user(db, usuario_id)
        if not local_user:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

        if local_user.rol != RoleEnum.CLIENTE:
            raise HTTPException(status_code=403, detail="Solo clientes pueden crear pedidos")

        # Construir el pedido interno (manteniendo el schema existente)
        order_to_create = OrderCreate(
            restaurante_id=restaurante_id,
            items=[OrderItem(menu_id=menu_id, cantidad=order_data.cantidad)],
            tipo_entrega=order_data.tipo_entrega,
            direccion_entrega=order_data.direccion_entrega,
            notas=order_data.notas,
        )
        
        # Validar dirección de entrega si es domicilio
        if order_to_create.tipo_entrega.value == "domicilio" and not order_to_create.direccion_entrega:
            raise HTTPException(
                status_code=400,
                detail="La dirección de entrega es requerida para tipo DOMICILIO"
            )

        restaurante = get_restaurant(db, restaurante_id)
        if not restaurante:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado")

        menu = get_menu(db, menu_id)
        if not menu:
            raise HTTPException(status_code=404, detail="Menu no encontrado")

        if menu.restaurante_id != restaurante_id:
            raise HTTPException(status_code=400, detail="El menu no pertenece a este restaurante")

        if not menu.disponible:
            raise HTTPException(status_code=400, detail="El menu no está disponible")

        subtotal = round(float(menu.precio) * int(order_data.cantidad), 2)
        impuesto = 0.0
        total = subtotal
        
        # Crear el pedido
        db_order = create_order(
            db=db,
            order=order_to_create,
            usuario_id=usuario_id,
            subtotal=subtotal,
            impuesto=impuesto,
            total=total
        )
        
        return db_order
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el pedido: {str(e)}")

@router.get("/restaurante/{restaurante_id}", response_model=list[OrderResponse])
async def listar_pedidos_restaurante(
    restaurante_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene todos los pedidos de un restaurante.
    Solo el dueño del restaurante puede ver esta información.
    """
    usuario_id = resolve_current_local_user_id(current_user, db)
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    local_user = get_user(db, usuario_id)
    if not local_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if local_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo admins pueden ver pedidos por restaurante")

    restaurante = get_restaurant(db, restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver los pedidos de este restaurante")
    
    orders = get_orders_by_restaurante(db, restaurante_id)
    
    # Aplicar paginación
    return orders[skip : skip + limit]


@router.get("/", response_model=list[OrderResponse])
async def listar_mis_pedidos(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene todos los pedidos del usuario autenticado.
    """
    usuario_id = resolve_current_local_user_id(current_user, db)
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    orders = get_orders_by_usuario(db, usuario_id)
    
    return orders[skip : skip + limit]


