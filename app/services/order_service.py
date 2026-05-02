from app.schemas.order import OrderCreate


def create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order: OrderCreate, usuario_id: int):
    """
    Valida menú, calcula precios y crea el pedido.
    """
    from fastapi import HTTPException

    menu = menu_dao.get_by_id(order.items[0].menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu no encontrado")

    if menu.restaurante_id != order.restaurante_id:
        raise HTTPException(status_code=400, detail="El menu no pertenece a este restaurante")

    if not menu.disponible:
        raise HTTPException(status_code=400, detail="El menu no está disponible")

    if order.tipo_entrega.value == "domicilio" and not order.direccion_entrega:
        raise HTTPException(status_code=400, detail="La dirección de entrega es requerida para tipo DOMICILIO")

    subtotal = round(float(menu.precio) * int(order.items[0].cantidad), 2)
    impuesto = 0.0
    total = subtotal

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