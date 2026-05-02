from app.schemas.order import OrderCreate

# Lógica de negocio y validaciones de pedidos
def create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order: OrderCreate, usuario_id: int):
    
    from fastapi import HTTPException

    # Si no se encuentra el menu de donde sale el pedido no lo da
    menu = menu_dao.get_by_id(order.items[0].menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu no encontrado")

    #Si tampoco se especifica el restaurante no se puede crear el pedido
    if menu.restaurante_id != order.restaurante_id:
        raise HTTPException(status_code=400, detail="El menu no pertenece a este restaurante")

    # Si el menu no esta disponible no se puede crear el pedido osea no existe
    if not menu.disponible:
        raise HTTPException(status_code=400, detail="El menu no está disponible")

    if order.tipo_entrega.value == "domicilio" and not order.direccion_entrega:
        raise HTTPException(status_code=400, detail="La dirección de entrega es requerida para tipo DOMICILIO")

    subtotal = round(float(menu.precio) * int(order.items[0].cantidad), 2)
    impuesto = 0.0
    total = subtotal

    #Crea el pedido y se delega al dao
    return order_dao.create({
        "usuario_id": usuario_id,
        "restaurante_id": order.restaurante_id,
        "items": [item.model_dump() for item in order.items],
        "subtotal": subtotal,
        "impuesto": impuesto,
        "total": total,
        "tipo_entrega": order.tipo_entrega,
        "direccion_entrega": order.direccion_entrega,
        "notas": order.notas,
    })