"""
Tests para el módulo de pedidos/órdenes.
Cubre los servicios, endpoints y validaciones de esquemas.
"""

import pytest
from app.models.order import Order, EstadoPedidoEnum, TipoEntregaEnum
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItem
from app.services.order_service import (
    get_order,
    get_orders_by_usuario,
    get_orders_by_restaurante,
    create_order,
    update_order_estado,
    cancel_order
)


# ==================== TESTS DE SERVICIOS ====================

class TestOrderService:
    """Tests para las funciones de servicio de pedidos."""
    
    def test_create_order(self, test_db, create_test_data):
        """Debe crear un pedido correctamente."""
        # Arrange
        user = create_test_data["create_user"](email="customer@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=2)],
            tipo_entrega=TipoEntregaEnum.EN_RESTAURANTE,
            notas="Sin picante"
        )
        
        # Act
        db_order = create_order(
            test_db,
            order_data,
            usuario_id=user.id,
            subtotal=30.0,
            impuesto=5.0,
            total=35.0
        )
        
        # Assert
        assert db_order.id is not None
        assert db_order.usuario_id == user.id
        assert db_order.restaurante_id == restaurant.id
        assert db_order.total == 35.0
        assert db_order.estado == EstadoPedidoEnum.PENDIENTE
    
    def test_get_order(self, test_db, create_test_data):
        """Debe obtener un pedido por su ID."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA
        )
        created_order = create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        retrieved_order = get_order(test_db, created_order.id)
        
        # Assert
        assert retrieved_order is not None
        assert retrieved_order.id == created_order.id
        assert retrieved_order.usuario_id == user.id
    
    def test_get_order_not_found(self, test_db):
        """Debe retornar None si el pedido no existe."""
        # Act
        result = get_order(test_db, 999)
        
        # Assert
        assert result is None
    
    def test_get_orders_by_usuario(self, test_db, create_test_data):
        """Debe obtener todos los pedidos de un usuario."""
        # Arrange
        user = create_test_data["create_user"](email="customer@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        for i in range(3):
            order_data = OrderCreate(
                restaurante_id=restaurant.id,
                items=[OrderItem(menu_id=1, cantidad=i+1)],
                tipo_entrega=TipoEntregaEnum.RECOGIDA
            )
            create_order(test_db, order_data, user.id, 10.0 * (i+1), 2.0, 12.0 * (i+1))
        
        # Act
        orders = get_orders_by_usuario(test_db, user.id)
        
        # Assert
        assert len(orders) == 3
        assert all(order.usuario_id == user.id for order in orders)
    
    def test_get_orders_by_usuario_empty(self, test_db):
        """Debe retornar lista vacía si el usuario no tiene pedidos."""
        # Act
        orders = get_orders_by_usuario(test_db, 999)
        
        # Assert
        assert len(orders) == 0
    
    def test_get_orders_by_restaurante(self, test_db, create_test_data):
        """Debe obtener todos los pedidos de un restaurante."""
        # Arrange
        user1 = create_test_data["create_user"](email="user1@test.com")
        user2 = create_test_data["create_user"](email="user2@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user1.id)
        
        for user in [user1, user2]:
            order_data = OrderCreate(
                restaurante_id=restaurant.id,
                items=[OrderItem(menu_id=1, cantidad=1)],
                tipo_entrega=TipoEntregaEnum.RECOGIDA
            )
            create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        orders = get_orders_by_restaurante(test_db, restaurant.id)
        
        # Assert
        assert len(orders) == 2
        assert all(order.restaurante_id == restaurant.id for order in orders)
    
    def test_update_order_estado(self, test_db, create_test_data):
        """Debe actualizar el estado de un pedido."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA
        )
        order = create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        update_data = OrderUpdate(
            estado=EstadoPedidoEnum.CONFIRMADO,
            notas="Pedido confirmado"
        )
        updated = update_order_estado(test_db, order.id, update_data)
        
        # Assert
        assert updated.estado == EstadoPedidoEnum.CONFIRMADO
        assert updated.notas == "Pedido confirmado"
    
    def test_update_order_estado_not_found(self, test_db):
        """Debe retornar None al actualizar pedido inexistente."""
        # Act
        result = update_order_estado(
            test_db,
            999,
            OrderUpdate(estado=EstadoPedidoEnum.ENTREGADO)
        )
        
        # Assert
        assert result is None
    
    def test_cancel_order(self, test_db, create_test_data):
        """Debe cancelar un pedido."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA
        )
        order = create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        cancelled = cancel_order(test_db, order.id)
        
        # Assert
        assert cancelled.estado == EstadoPedidoEnum.CANCELADO
    
    def test_cancel_order_not_found(self, test_db):
        """Debe retornar None al cancelar pedido inexistente."""
        # Act
        result = cancel_order(test_db, 999)
        
        # Assert
        assert result is None


# ==================== TESTS DE SCHEMAS ====================

class TestOrderSchemas:
    """Tests para validación de esquemas."""
    
    def test_order_item_valid(self):
        """Debe crear OrderItem válido."""
        item = OrderItem(menu_id=1, cantidad=2)
        assert item.menu_id == 1
        assert item.cantidad == 2
    
    def test_order_item_invalid_cantidad_zero(self):
        """Debe rechazar cantidad=0."""
        with pytest.raises(ValueError):
            OrderItem(menu_id=1, cantidad=0)
    
    def test_order_item_invalid_cantidad_negative(self):
        """Debe rechazar cantidad negativa."""
        with pytest.raises(ValueError):
            OrderItem(menu_id=1, cantidad=-1)
    
    def test_order_create_valid(self):
        """Debe crear OrderCreate válido."""
        order = OrderCreate(
            restaurante_id=1,
            items=[OrderItem(menu_id=1, cantidad=2)],
            tipo_entrega=TipoEntregaEnum.EN_RESTAURANTE,
            notas="Sin cebolla"
        )
        assert order.restaurante_id == 1
        assert len(order.items) == 1
        assert order.tipo_entrega == TipoEntregaEnum.EN_RESTAURANTE
    
    def test_order_create_invalid_empty_items(self):
        """Debe rechazar lista de items vacía."""
        with pytest.raises(ValueError):
            OrderCreate(
                restaurante_id=1,
                items=[],
                tipo_entrega=TipoEntregaEnum.RECOGIDA
            )
    
    def test_order_create_default_tipo_entrega(self):
        """Debe usar RECOGIDA como tipo_entrega por defecto."""
        order = OrderCreate(
            restaurante_id=1,
            items=[OrderItem(menu_id=1, cantidad=1)]
        )
        assert order.tipo_entrega == TipoEntregaEnum.RECOGIDA
    
    def test_order_create_domicilio_requires_direccion(self):
        """Debe permitir crear con DOMICILIO sin dirección (validada en endpoint)."""
        # El schema permite crear sin dirección, la validación es en el endpoint
        order = OrderCreate(
            restaurante_id=1,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.DOMICILIO
        )
        assert order.tipo_entrega == TipoEntregaEnum.DOMICILIO
        assert order.direccion_entrega is None
    
    def test_order_update_partial(self):
        """Debe permitir actualización parcial."""
        update = OrderUpdate(
            estado=EstadoPedidoEnum.CONFIRMADO
        )
        assert update.estado == EstadoPedidoEnum.CONFIRMADO
        assert update.notas is None
    
    def test_order_response_valid(self):
        """Debe crear OrderResponse válido."""
        response = OrderResponse(
            id=1,
            usuario_id=1,
            restaurante_id=1,
            items=[OrderItem(menu_id=1, cantidad=2)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA,
            subtotal=20.0,
            impuesto=4.0,
            total=24.0,
            estado=EstadoPedidoEnum.PENDIENTE
        )
        assert response.id == 1
        assert response.total == 24.0
        assert response.estado == EstadoPedidoEnum.PENDIENTE


# ==================== TESTS DE ENDPOINTS ====================

class TestOrderEndpoints:
    """Tests para los endpoints de pedidos."""
    
    def test_crear_pedido_exitoso(self, client, test_db, create_test_data):
        """POST /orders/ debe crear un pedido."""
        # Arrange
        user = create_test_data["create_user"](email="customer@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = {
            "restaurante_id": restaurant.id,
            "items": [
                {"menu_id": 1, "cantidad": 2}
            ],
            "tipo_entrega": "en_restaurante",
            "notas": "Sin picante"
        }
        
        # Act
        response = client.post(
            "/orders/",
            json=order_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["usuario_id"] == 1  # El JWT mock retorna usuario_id=1
        assert data["restaurante_id"] == restaurant.id
    
    def test_crear_pedido_sin_auth(self, client):
        """POST /orders/ debe requerir autenticación."""
        # Act
        response = client.post(
            "/orders/",
            json={
                "restaurante_id": 1,
                "items": [{"menu_id": 1, "cantidad": 1}]
            }
        )
        
        # Assert
        assert response.status_code == 401
    
    def test_obtener_pedido_exitoso(self, client, test_db, create_test_data):
        """GET /orders/{id} debe obtener un pedido."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA
        )
        order = create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        response = client.get(
            f"/orders/{order.id}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order.id
        assert data["usuario_id"] == user.id
    
    def test_obtener_pedido_no_existe(self, client):
        """GET /orders/{id} debe retornar 404 si no existe."""
        # Act
        response = client.get(
            "/orders/999",
            headers={"Authorization": "Bearer test-token"}
        )
        # Assert
        assert response.status_code == 404
    
    def test_listar_mis_pedidos(self, client, test_db, create_test_data):
        """GET /orders/ debe listar mis pedidos."""
        # Arrange
        user = create_test_data["create_user"](email="customer@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        for i in range(3):
            order_data = OrderCreate(
                restaurante_id=restaurant.id,
                items=[OrderItem(menu_id=1, cantidad=i+1)],
                tipo_entrega=TipoEntregaEnum.RECOGIDA
            )
            create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        response = client.get(
            "/orders/",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
    
    def test_actualizar_pedido_exitoso(self, client, test_db, create_test_data):
        """PUT /orders/{id} debe actualizar un pedido."""
        # Arrange
        user = create_test_data["create_user"](email="customer@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA
        )
        order = create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        response = client.put(
            f"/orders/{order.id}",
            json={
                "estado": "confirmado",
                "notas": "Confirmado por cliente"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "confirmado"
        assert data["notas"] == "Confirmado por cliente"
    
    def test_actualizar_pedido_no_existe(self, client):
        """PUT /orders/{id} debe retornar 404 si no existe."""
        # Act
        response = client.put(
            "/orders/999",
            json={"estado": "confirmado"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 404
    
    def test_cancelar_pedido_exitoso(self, client, test_db, create_test_data):
        """DELETE /orders/{id} debe cancelar un pedido."""
        # Arrange
        user = create_test_data["create_user"](email="customer@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = OrderCreate(
            restaurante_id=restaurant.id,
            items=[OrderItem(menu_id=1, cantidad=1)],
            tipo_entrega=TipoEntregaEnum.RECOGIDA
        )
        order = create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        response = client.delete(
            f"/orders/{order.id}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 204
        
        # Verificar que fue cancelado
        updated = get_order(test_db, order.id)
        assert updated.estado == EstadoPedidoEnum.CANCELADO
    
    def test_cancelar_pedido_no_existe(self, client):
        """DELETE /orders/{id} debe retornar 404 si no existe."""
        # Act
        response = client.delete(
            "/orders/999",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 404
    
    def test_listar_pedidos_restaurante(self, client, test_db, create_test_data):
        """GET /orders/restaurante/{id} debe listar pedidos del restaurante."""
        # Arrange
        user1 = create_test_data["create_user"](email="user1@test.com")
        user2 = create_test_data["create_user"](email="user2@test.com")
        restaurant = create_test_data["create_restaurant"](admin_id=user1.id)
        
        for user in [user1, user2]:
            order_data = OrderCreate(
                restaurante_id=restaurant.id,
                items=[OrderItem(menu_id=1, cantidad=1)],
                tipo_entrega=TipoEntregaEnum.RECOGIDA
            )
            create_order(test_db, order_data, user.id, 10.0, 2.0, 12.0)
        
        # Act
        response = client.get(
            f"/orders/restaurante/{restaurant.id}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
    
    def test_crear_pedido_domicilio_sin_direccion(self, client, test_db, create_test_data):
        """POST /orders/ debe rechazar DOMICILIO sin dirección."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        order_data = {
            "restaurante_id": restaurant.id,
            "items": [{"menu_id": 1, "cantidad": 1}],
            "tipo_entrega": "domicilio"
            # Sin direccion_entrega
        }
        
        # Act
        response = client.post(
            "/orders/",
            json=order_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 400
