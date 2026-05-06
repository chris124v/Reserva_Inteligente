"""
Tests esenciales para restaurant_service.py.
Se enfocan en permisos, duplicados y validación de dueño.
"""

from datetime import time
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.models.restaurant import Restaurant
from app.models.user import RoleEnum, User
from app.schemas.restaurant import RestaurantCreate
from app.services.restaurant_service import create_restaurant, validate_restaurant_admin


# Pruebas de creación de restaurante y validación de permisos.
class TestCreateRestaurant:
# Verifica que un admin pueda crear un restaurante cuando no existe duplicado.
    def test_create_restaurant_success(self):
        user_dao = Mock()
        restaurant_dao = Mock()

        user_dao.get_by_id.return_value = User(
            id=1,
            email="admin@demo.com",
            nombre="María Rodríguez García",
            password_hash="hash",
            rol=RoleEnum.ADMIN,
            activo=True,
        )
        restaurant_dao.get_by_email.return_value = None
        restaurant_dao.create.return_value = Mock(
            spec=Restaurant,
            id=10,
            nombre="Sapore Trattoria",
            email="sapore@demo.com",
            admin_id=1,
        )

        restaurant_data = RestaurantCreate(
            nombre="Sapore Trattoria",
            descripcion="Auténtica comida italiana con pastas frescas y pizzas artesanales.",
            direccion="San José Centro, Avenida Central 250",
            telefono="8888-1111",
            email="sapore@demo.com",
            hora_apertura=time(10, 0),
            hora_cierre=time(22, 0),
            total_mesas=20,
        )

        result = create_restaurant(restaurant_dao, user_dao, restaurant_data, 1)

        assert result.email == "sapore@demo.com"
        restaurant_dao.create.assert_called_once()

# Verifica que no se cree si el email ya existe.
    def test_create_restaurant_returns_none_when_email_exists(self):
        user_dao = Mock()
        restaurant_dao = Mock()

        user_dao.get_by_id.return_value = User(
            id=1,
            email="admin@demo.com",
            nombre="María Rodríguez García",
            password_hash="hash",
            rol=RoleEnum.ADMIN,
            activo=True,
        )
        restaurant_dao.get_by_email.return_value = Mock(spec=Restaurant)

        restaurant_data = RestaurantCreate(
            nombre="Burger House",
            descripcion="Hamburguesas gourmet y comida rápida de alta calidad.",
            direccion="San Pedro, Calle Piedra 456",
            telefono="8888-4444",
            email="burgerhouse@demo.com",
            hora_apertura=time(11, 0),
            hora_cierre=time(23, 0),
            total_mesas=12,
        )

        result = create_restaurant(restaurant_dao, user_dao, restaurant_data, 1)

        assert result is None
        restaurant_dao.create.assert_not_called()

# Verifica que un usuario inexistente no pueda crear restaurantes.
    def test_create_restaurant_returns_none_when_admin_not_found(self):
        user_dao = Mock()
        restaurant_dao = Mock()

        user_dao.get_by_id.return_value = None

        restaurant_data = RestaurantCreate(
            nombre="Villa Italia",
            descripcion="Sabores clásicos italianos con toque moderno.",
            direccion="Escazú, Calle Vieja 145",
            telefono="8888-2222",
            email="villa@demo.com",
            hora_apertura=time(11, 0),
            hora_cierre=time(23, 0),
            total_mesas=18,
        )

        result = create_restaurant(restaurant_dao, user_dao, restaurant_data, 1)

        assert result is None
        restaurant_dao.create.assert_not_called()

# Verifica que un cliente no pueda crear restaurantes.
    def test_create_restaurant_returns_none_when_user_is_not_admin(self):
        user_dao = Mock()
        restaurant_dao = Mock()

        user_dao.get_by_id.return_value = User(
            id=2,
            email="cliente@demo.com",
            nombre="Carlos Jiménez López",
            password_hash="hash",
            rol=RoleEnum.CLIENTE,
            activo=True,
        )

        restaurant_data = RestaurantCreate(
            nombre="Los Congos",
            descripcion="Cocina fusión moderna con ambiente vibrante.",
            direccion="Heredia, Boulevard Flores 89",
            telefono="8888-3333",
            email="congos@demo.com",
            hora_apertura=time(12, 0),
            hora_cierre=time(22, 30),
            total_mesas=15,
        )

        result = create_restaurant(restaurant_dao, user_dao, restaurant_data, 2)

        assert result is None
        restaurant_dao.create.assert_not_called()


# Pruebas de validación para modificar restaurantes.
class TestValidateRestaurantAdmin:
# Verifica que el admin dueño del restaurante tenga permiso.
    def test_admin_owner_can_validate_restaurant(self):
        user_dao = Mock()
        user_dao.get_by_id.return_value = User(
            id=1,
            email="admin@demo.com",
            nombre="María Rodríguez García",
            password_hash="hash",
            rol=RoleEnum.ADMIN,
            activo=True,
        )
        restaurant = Mock(admin_id=1)

        result = validate_restaurant_admin(user_dao, 1, restaurant)

        assert result is None

# Verifica que un usuario sin autenticación sea rechazado.
    def test_validate_restaurant_admin_returns_401_when_user_not_found(self):
        user_dao = Mock()
        user_dao.get_by_id.return_value = None
        restaurant = Mock(admin_id=1)

        with pytest.raises(HTTPException) as exc_info:
            validate_restaurant_admin(user_dao, 1, restaurant)

        assert exc_info.value.status_code == 401

# Verifica que un usuario no admin no pueda modificar restaurantes.
    def test_validate_restaurant_admin_returns_403_when_user_is_not_admin(self):
        user_dao = Mock()
        user_dao.get_by_id.return_value = User(
            id=2,
            email="cliente@demo.com",
            nombre="Carlos Jiménez López",
            password_hash="hash",
            rol=RoleEnum.CLIENTE,
            activo=True,
        )
        restaurant = Mock(admin_id=2)

        with pytest.raises(HTTPException) as exc_info:
            validate_restaurant_admin(user_dao, 2, restaurant)

        assert exc_info.value.status_code == 403

# Verifica que un admin que no es dueño no pueda modificar el restaurante.
    def test_validate_restaurant_admin_returns_403_when_not_owner(self):
        user_dao = Mock()
        user_dao.get_by_id.return_value = User(
            id=1,
            email="admin@demo.com",
            nombre="María Rodríguez García",
            password_hash="hash",
            rol=RoleEnum.ADMIN,
            activo=True,
        )
        restaurant = Mock(admin_id=99)

        with pytest.raises(HTTPException) as exc_info:
            validate_restaurant_admin(user_dao, 1, restaurant)

        assert exc_info.value.status_code == 403
