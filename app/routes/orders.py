from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse
from app.services.order_service import (
    get_order,
    get_orders_by_usuario,
    get_orders_by_restaurante,
    create_order,
    update_order_estado,
    cancel_order
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
async def crear_pedido(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Crea un nuevo pedido para el usuario autenticado.
    
    - **restaurante_id**: ID del restaurante
    - **items**: Lista de items del pedido (menu_id, cantidad)
    - **tipo_entrega**: RECOGIDA, DOMICILIO, EN_RESTAURANTE
    - **direccion_entrega**: Requerida si tipo_entrega es DOMICILIO
    - **notas**: Notas adicionales (opcional)
    """
    try:
        # Obtener usuario_id del JWT
        usuario_id = current_user.get("sub") or current_user.get("usuario_id")
        
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")

        try:
            usuario_id = int(usuario_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Usuario no autenticado")
        
        # Validar dirección de entrega si es domicilio
        if order_data.tipo_entrega.value == "domicilio" and not order_data.direccion_entrega:
            raise HTTPException(
                status_code=400,
                detail="La dirección de entrega es requerida para tipo DOMICILIO"
            )
        
        # TODO: Validar que el restaurante existe
        # TODO: Validar que los items/menús existen y calcular precios
        
        # Cálculo simple de totales (esto debería venir del servicio)
        subtotal = 0.0
        impuesto = 0.0
        total = 0.0
        
        # Crear el pedido
        db_order = create_order(
            db=db,
            order=order_data,
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
    
    - **restaurante_id**: ID del restaurante
    - **limit**: Número máximo de registros
    - **skip**: Número de registros a saltar
    """
    # TODO: Validar que el usuario es dueño del restaurante
    
    orders = get_orders_by_restaurante(db, restaurante_id)
    
    # Aplicar paginación
    return orders[skip : skip + limit]

@router.get("/{order_id}", response_model=OrderResponse)
async def obtener_pedido(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Obtiene los detalles de un pedido específico.
    El usuario solo puede ver sus propios pedidos o si es dueño del restaurante.
    """
    db_order = get_order(db, order_id)
    
    if not db_order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Validar permiso: el usuario es dueño del pedido o del restaurante
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    # TODO: Validar si es dueño del restaurante
    if db_order.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver este pedido")
    
    return db_order


@router.get("/", response_model=list[OrderResponse])
async def listar_mis_pedidos(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene todos los pedidos del usuario autenticado.
    
    - **limit**: Número máximo de registros (default: 10, máximo: 100)
    - **skip**: Número de registros a saltar para paginación
    """
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    orders = get_orders_by_usuario(db, usuario_id)
    
    # Aplicar paginación (esto debería hacerse en el servicio)
    return orders[skip : skip + limit]


@router.put("/{order_id}", response_model=OrderResponse)
async def actualizar_pedido(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Actualiza el estado y/o notas de un pedido.
    Solo el usuario que creó el pedido puede actualizarlo.
    
    - **estado**: PENDIENTE, CONFIRMADO, EN_PREPARACION, LISTO, ENTREGADO, CANCELADO
    - **notas**: Notas adicionales (opcional)
    """
    db_order = get_order(db, order_id)
    
    if not db_order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Validar permiso
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    if db_order.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este pedido")
    
    # Actualizar
    updated_order = update_order_estado(db, order_id, order_update)
    
    return updated_order


@router.delete("/{order_id}", status_code=204)
async def cancelar_pedido(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Cancela un pedido.
    Solo pedidos en estado PENDIENTE o CONFIRMADO pueden ser cancelados.
    """
    db_order = get_order(db, order_id)
    
    if not db_order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Validar permiso
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    if db_order.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para cancelar este pedido")
    
    # Validar estado
    if db_order.estado.value not in ["pendiente", "confirmado"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar un pedido en estado {db_order.estado.value}"
        )
    
    # Cancelar
    cancel_order(db, order_id)
    
    return None


