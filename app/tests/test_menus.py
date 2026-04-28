"""
Tests para el módulo de menús.
Cubre los servicios, endpoints y validaciones de esquemas.
"""

import pytest
from fastapi import HTTPException
from datetime import datetime
from app.models.menu import Menu
from app.schemas.menu import MenuCreate, MenuUpdate, MenuResponse
from app.services.menu_service import (
    get_menu,
    get_menus_by_restaurante,
    get_all_menus,
    create_menu,
    update_menu,
    delete_menu
)


# ==================== TESTS DE SERVICIOS ====================

class TestMenuService:
    """Tests para las funciones de servicio de menús."""
    
    def test_create_menu(self, test_db, create_test_data):
        """Debe crear un menú correctamente."""
        # Arrange
        user = create_test_data["create_user"](email="admin@test.com", rol="admin")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        menu_data = MenuCreate(
            nombre="Hamburguesa",
            descripcion="Deliciosa hamburguesa casera",
            precio=15.50,
            disponible=True,
            tiempo_preparacion=10,
            categoria="plato_principal",
            restaurante_id=restaurant.id
        )
        
        # Act
        db_menu = create_menu(test_db, menu_data)
        
        # Assert
        assert db_menu.id is not None
        assert db_menu.nombre == "Hamburguesa"
        assert db_menu.precio == 15.50
        assert db_menu.disponible is True
        assert db_menu.restaurante_id == restaurant.id
    
    def test_get_menu(self, test_db, create_test_data):
        """Debe obtener un menú por su ID."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        menu_data = MenuCreate(
            nombre="Pizza",
            descripcion="Clásica pizza margarita",
            precio=12.00,
            restaurante_id=restaurant.id
        )
        created_menu = create_menu(test_db, menu_data)
        
        # Act
        retrieved_menu = get_menu(test_db, created_menu.id)
        
        # Assert
        assert retrieved_menu is not None
        assert retrieved_menu.id == created_menu.id
        assert retrieved_menu.nombre == "Pizza"
    
    def test_get_menu_not_found(self, test_db):
        """Debe retornar None si el menú no existe."""
        # Act
        result = get_menu(test_db, 999)
        
        # Assert
        assert result is None
    
    def test_get_menus_by_restaurante(self, test_db, create_test_data):
        """Debe obtener todos los menús de un restaurante."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        menu1 = MenuCreate(nombre="Pizza", precio=12.0, restaurante_id=restaurant.id)
        menu2 = MenuCreate(nombre="Pasta", precio=13.0, restaurante_id=restaurant.id)
        menu3 = MenuCreate(nombre="Ensalada", precio=8.0, restaurante_id=restaurant.id)
        
        create_menu(test_db, menu1)
        create_menu(test_db, menu2)
        create_menu(test_db, menu3)
        
        # Act
        menus = get_menus_by_restaurante(test_db, restaurant.id)
        
        # Assert
        assert len(menus) == 3
        assert all(menu.restaurante_id == restaurant.id for menu in menus)
    
    def test_get_menus_by_restaurante_empty(self, test_db, create_test_data):
        """Debe retornar lista vacía si el restaurante no tiene menús."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        # Act
        menus = get_menus_by_restaurante(test_db, restaurant.id)
        
        # Assert
        assert len(menus) == 0
    
    def test_get_all_menus(self, test_db, create_test_data):
        """Debe obtener todos los menús de todos los restaurantes."""
        # Arrange
        user = create_test_data["create_user"]()
        rest1 = create_test_data["create_restaurant"](admin_id=user.id)
        rest2 = create_test_data["create_restaurant"](nombre="Restaurant 2", admin_id=user.id)
        
        menu1 = MenuCreate(nombre="Pizza", precio=12.0, restaurante_id=rest1.id)
        menu2 = MenuCreate(nombre="Burger", precio=10.0, restaurante_id=rest2.id)
        
        create_menu(test_db, menu1)
        create_menu(test_db, menu2)
        
        # Act
        all_menus = get_all_menus(test_db)
        
        # Assert
        assert len(all_menus) >= 2
    
    def test_update_menu(self, test_db, create_test_data):
        """Debe actualizar un menú correctamente."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        menu_data = MenuCreate(
            nombre="Pizza",
            precio=12.0,
            restaurante_id=restaurant.id
        )
        menu = create_menu(test_db, menu_data)
        
        # Act
        update_data = MenuUpdate(
            nombre="Pizza Especial",
            precio=15.0,
            disponible=False
        )
        updated = update_menu(test_db, menu.id, update_data)
        
        # Assert
        assert updated.nombre == "Pizza Especial"
        assert updated.precio == 15.0
        assert updated.disponible is False
    
    def test_update_menu_not_found(self, test_db):
        """Debe retornar None al actualizar menú inexistente."""
        # Act
        result = update_menu(test_db, 999, MenuUpdate(nombre="Inexistente"))
        
        # Assert
        assert result is None
    
    def test_delete_menu(self, test_db, create_test_data):
        """Debe eliminar un menú correctamente."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        menu_data = MenuCreate(
            nombre="Pizza",
            precio=12.0,
            restaurante_id=restaurant.id
        )
        menu = create_menu(test_db, menu_data)
        
        # Act
        deleted = delete_menu(test_db, menu.id)
        retrieved = get_menu(test_db, menu.id)
        
        # Assert
        assert deleted is not None
        assert retrieved is None
    
    def test_delete_menu_not_found(self, test_db):
        """Debe retornar None al eliminar menú inexistente."""
        # Act
        result = delete_menu(test_db, 999)
        
        # Assert
        assert result is None


# ==================== TESTS DE SCHEMAS ====================

class TestMenuSchemas:
    """Tests para validación de esquemas."""
    
    def test_menu_create_valid(self):
        """Debe crear MenuCreate válido."""
        menu = MenuCreate(
            nombre="Pizza",
            descripcion="Pizza margarita",
            precio=12.50,
            restaurante_id=1,
            categoria="plato_principal"
        )
        assert menu.nombre == "Pizza"
        assert menu.precio == 12.50
    
    def test_menu_create_invalid_precio(self):
        """Debe rechazar precio negativo."""
        with pytest.raises(ValueError):
            MenuCreate(
                nombre="Pizza",
                precio=-10.0,
                restaurante_id=1
            )
    
    def test_menu_create_invalid_nombre_vacio(self):
        """Debe rechazar nombre vacío."""
        with pytest.raises(ValueError):
            MenuCreate(
                nombre="",
                precio=10.0,
                restaurante_id=1
            )
    
    def test_menu_update_partial(self):
        """Debe permitir actualización parcial."""
        update = MenuUpdate(
            nombre="Nuevo nombre"
        )
        assert update.nombre == "Nuevo nombre"
        assert update.precio is None
        assert update.disponible is None
    
    def test_menu_response_valid(self):
        """Debe crear MenuResponse válido."""
        response = MenuResponse(
            id=1,
            nombre="Pizza",
            precio=12.50,
            restaurante_id=1,
            disponible=True
        )
        assert response.id == 1
        assert response.nombre == "Pizza"


# ==================== TESTS DE ENDPOINTS ====================

class TestMenuEndpoints:
    """Tests para los endpoints de menús."""
    
    def test_crear_menu_exitoso(self, client, test_db, create_test_data):
        """POST /menus/ debe crear un menú."""
        # Arrange
        user = create_test_data["create_user"](email="admin@test.com", rol="admin")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        menu_data = {
            "nombre": "Hamburguesa",
            "descripcion": "Hamburguesa deliciosa",
            "precio": 15.50,
            "disponible": True,
            "tiempo_preparacion": 10,
            "categoria": "plato_principal",
            "restaurante_id": restaurant.id
        }
        
        # Act
        response = client.post(
            "/menus/",
            json=menu_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Hamburguesa"
        assert data["precio"] == 15.50
    
    def test_crear_menu_sin_auth(self, client):
        """POST /menus/ debe requerir autenticación."""
        # Act
        response = client.post(
            "/menus/",
            json={
                "nombre": "Pizza",
                "precio": 12.0,
                "restaurante_id": 1
            }
        )
        
        # Assert
        assert response.status_code == 401
    
    def test_obtener_menu_exitoso(self, client, test_db, create_test_data):
        """GET /menus/{id} debe obtener un menú."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        menu_data = MenuCreate(
            nombre="Pizza",
            precio=12.0,
            restaurante_id=restaurant.id
        )
        menu = create_menu(test_db, menu_data)
        
        # Act
        response = client.get(f"/menus/{menu.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == menu.id
        assert data["nombre"] == "Pizza"
    
    def test_obtener_menu_no_existe(self, client):
        """GET /menus/{id} debe retornar 404 si no existe."""
        # Act
        response = client.get("/menus/999")
        
        # Assert
        assert response.status_code == 404
    
    def test_listar_menus_restaurante(self, client, test_db, create_test_data):
        """GET /menus/restaurante/{id} debe listar menús."""
        # Arrange
        user = create_test_data["create_user"]()
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        
        for i in range(3):
            menu_data = MenuCreate(
                nombre=f"Plato {i+1}",
                precio=10.0 + i,
                restaurante_id=restaurant.id
            )
            create_menu(test_db, menu_data)
        
        # Act
        response = client.get(f"/menus/restaurante/{restaurant.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    def test_actualizar_menu_exitoso(self, client, test_db, create_test_data):
        """PUT /menus/{id} debe actualizar un menú."""
        # Arrange
        user = create_test_data["create_user"](email="admin@test.com", rol="admin")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        menu_data = MenuCreate(
            nombre="Pizza",
            precio=12.0,
            restaurante_id=restaurant.id
        )
        menu = create_menu(test_db, menu_data)
        
        # Act
        response = client.put(
            f"/menus/{menu.id}",
            json={
                "nombre": "Pizza Especial",
                "precio": 15.0
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Pizza Especial"
        assert data["precio"] == 15.0
    
    def test_eliminar_menu_exitoso(self, client, test_db, create_test_data):
        """DELETE /menus/{id} debe eliminar un menú."""
        # Arrange
        user = create_test_data["create_user"](email="admin@test.com", rol="admin")
        restaurant = create_test_data["create_restaurant"](admin_id=user.id)
        menu_data = MenuCreate(
            nombre="Pizza",
            precio=12.0,
            restaurante_id=restaurant.id
        )
        menu = create_menu(test_db, menu_data)
        
        # Act
        response = client.delete(
            f"/menus/{menu.id}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 204
        
        # Verificar que fue eliminado
        retrieved = get_menu(test_db, menu.id)
        assert retrieved is None
    
    def test_eliminar_menu_no_existe(self, client, create_test_data):
        """DELETE /menus/{id} debe retornar 404 si no existe."""
        create_test_data["create_user"](email="admin_del@test.com", rol="admin")
        # Act
        response = client.delete(
            "/menus/999",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assert
        assert response.status_code == 404
