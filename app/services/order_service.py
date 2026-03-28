from sqlalchemy.orm import Session
from app.models.order import Order, EstadoPedidoEnum
from app.schemas.order import OrderCreate, OrderUpdate

def get_order(db: Session, order_id: int):
    return db.query(Order).filter(Order.id == order_id).first()

def get_orders_by_usuario(db: Session, usuario_id: int):
    return db.query(Order).filter(Order.usuario_id == usuario_id).all()

def get_orders_by_restaurante(db: Session, restaurante_id: int):
    return db.query(Order).filter(Order.restaurante_id == restaurante_id).all()

def create_order(db: Session, order: OrderCreate, usuario_id: int, subtotal: float, impuesto: float, total: float):
    db_order = Order(
        usuario_id=usuario_id,
        restaurante_id=order.restaurante_id,
        items=[item.model_dump() for item in order.items],
        subtotal=subtotal,
        impuesto=impuesto,
        total=total,
        tipo_entrega=order.tipo_entrega,
        direccion_entrega=order.direccion_entrega,
        notas=order.notas
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order_estado(db: Session, order_id: int, order: OrderUpdate):
    db_order = get_order(db, order_id)
    if not db_order:
        return None

    update_data = order.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)

    db.commit()
    db.refresh(db_order)
    return db_order

def cancel_order(db: Session, order_id: int):
    db_order = get_order(db, order_id)
    if not db_order:
        return None
    
    db_order.estado = EstadoPedidoEnum.CANCELADO
    db.commit()
    db.refresh(db_order)
    return db_order