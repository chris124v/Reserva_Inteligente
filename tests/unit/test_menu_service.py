"""
Tests esenciales para menu_service.py.
Se enfocan en la validación de admin, restaurante y permisos.
"""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.models.restaurant import Restaurant
from app.models.user import RoleEnum, User
from app.services.menu_service import validate_menu_admin


# Pruebas de validación de permisos para crear o modificar menús.
class TestValidateMenuAdmin:
# Verifica que un admin dueño del restaurante puede continuar.
	def test_admin_owner_can_validate_menu(self):
		user_dao = Mock()
		restaurant_dao = Mock()

		user_dao.get_by_id.return_value = User(
			id=1,
			email="admin@demo.com",
			nombre="Admin",
			password_hash="hash",
			rol=RoleEnum.ADMIN,
			activo=True,
		)
		restaurant_dao.get_by_id.return_value = Restaurant(
			id=10,
			nombre="Restaurante Demo",
			descripcion="Demo",
			direccion="Calle 1",
			telefono="8888-8888",
			email="rest@demo.com",
			admin_id=1,
			hora_apertura="08:00:00",
			hora_cierre="22:00:00",
			total_mesas=10,
		)

		result = validate_menu_admin(user_dao, restaurant_dao, 1, 10)

		assert result.admin_id == 1

# Verifica que un usuario sin autenticación sea rechazado.
	def test_user_not_found_returns_401(self):
		user_dao = Mock()
		restaurant_dao = Mock()
		user_dao.get_by_id.return_value = None

		with pytest.raises(HTTPException) as exc_info:
			validate_menu_admin(user_dao, restaurant_dao, 1, 10)

		assert exc_info.value.status_code == 401

# Verifica que solo un admin pueda administrar menús.
	def test_non_admin_is_rejected(self):
		user_dao = Mock()
		restaurant_dao = Mock()

		user_dao.get_by_id.return_value = User(
			id=2,
			email="cliente@demo.com",
			nombre="Cliente",
			password_hash="hash",
			rol=RoleEnum.CLIENTE,
			activo=True,
		)

		with pytest.raises(HTTPException) as exc_info:
			validate_menu_admin(user_dao, restaurant_dao, 2, 10)

		assert exc_info.value.status_code == 403

# Verifica que no se pueda usar un restaurante inexistente.
	def test_restaurant_not_found_returns_404(self):
		user_dao = Mock()
		restaurant_dao = Mock()

		user_dao.get_by_id.return_value = User(
			id=1,
			email="admin@demo.com",
			nombre="Admin",
			password_hash="hash",
			rol=RoleEnum.ADMIN,
			activo=True,
		)
		restaurant_dao.get_by_id.return_value = None

		with pytest.raises(HTTPException) as exc_info:
			validate_menu_admin(user_dao, restaurant_dao, 1, 999)

		assert exc_info.value.status_code == 404

# Verifica que un admin no pueda modificar menús de otro restaurante.
	def test_admin_not_owner_is_rejected(self):
		user_dao = Mock()
		restaurant_dao = Mock()

		user_dao.get_by_id.return_value = User(
			id=1,
			email="admin@demo.com",
			nombre="Admin",
			password_hash="hash",
			rol=RoleEnum.ADMIN,
			activo=True,
		)
		restaurant_dao.get_by_id.return_value = Restaurant(
			id=10,
			nombre="Restaurante Demo",
			descripcion="Demo",
			direccion="Calle 1",
			telefono="8888-8888",
			email="rest@demo.com",
			admin_id=99,
			hora_apertura="08:00:00",
			hora_cierre="22:00:00",
			total_mesas=10,
		)

		with pytest.raises(HTTPException) as exc_info:
			validate_menu_admin(user_dao, restaurant_dao, 1, 10)

		assert exc_info.value.status_code == 403
