"""
Tests esenciales para order_service.py.
Se enfocan en validaciones clave y cálculo básico del pedido.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.models.order import TipoEntregaEnum
from app.schemas.order import OrderCreate, OrderItem
from app.services.order_service import create_order


# Pruebas de creación de pedidos.
class TestCreateOrder:
# Verifica que un pedido se cree correctamente con datos válidos.
	def test_create_order_success(self):
		order_dao = Mock()
		reservation_dao = Mock()
		restaurant_dao = Mock()
		menu_dao = Mock()

		menu_dao.get_by_id.return_value = SimpleNamespace(
			id=1,
			restaurante_id=1,
			precio=6500,
			disponible=True,
		)
		order_dao.create.return_value = Mock(id=100, total=13000)

		order = OrderCreate(
			restaurante_id=1,
			items=[OrderItem(menu_id=1, cantidad=2)],
			tipo_entrega=TipoEntregaEnum.RECOGIDA,
			direccion_entrega=None,
			notas="Sin cebolla",
		)

		result = create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order, 2)

		assert result.total == 13000
		order_dao.create.assert_called_once()

# Verifica que no se pueda crear un pedido si el menú no existe.
	def test_create_order_returns_404_when_menu_not_found(self):
		order_dao = Mock()
		reservation_dao = Mock()
		restaurant_dao = Mock()
		menu_dao = Mock()

		menu_dao.get_by_id.return_value = None

		order = OrderCreate(
			restaurante_id=1,
			items=[OrderItem(menu_id=1, cantidad=1)],
			tipo_entrega=TipoEntregaEnum.RECOGIDA,
			direccion_entrega=None,
			notas=None,
		)

		with pytest.raises(HTTPException) as exc_info:
			create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order, 2)

		assert exc_info.value.status_code == 404

# Verifica que el menú pertenezca al restaurante correcto.
	def test_create_order_returns_400_when_menu_belongs_to_other_restaurant(self):
		order_dao = Mock()
		reservation_dao = Mock()
		restaurant_dao = Mock()
		menu_dao = Mock()

		menu_dao.get_by_id.return_value = SimpleNamespace(
			id=1,
			restaurante_id=99,
			precio=6500,
			disponible=True,
		)

		order = OrderCreate(
			restaurante_id=1,
			items=[OrderItem(menu_id=1, cantidad=1)],
			tipo_entrega=TipoEntregaEnum.RECOGIDA,
			direccion_entrega=None,
			notas=None,
		)

		with pytest.raises(HTTPException) as exc_info:
			create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order, 2)

		assert exc_info.value.status_code == 400

# Verifica que un menú no disponible no permita crear pedido.
	def test_create_order_returns_400_when_menu_is_not_available(self):
		order_dao = Mock()
		reservation_dao = Mock()
		restaurant_dao = Mock()
		menu_dao = Mock()

		menu_dao.get_by_id.return_value = SimpleNamespace(
			id=1,
			restaurante_id=1,
			precio=6500,
			disponible=False,
		)

		order = OrderCreate(
			restaurante_id=1,
			items=[OrderItem(menu_id=1, cantidad=1)],
			tipo_entrega=TipoEntregaEnum.RECOGIDA,
			direccion_entrega=None,
			notas=None,
		)

		with pytest.raises(HTTPException) as exc_info:
			create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order, 2)

		assert exc_info.value.status_code == 400

# Verifica que domicilio requiera dirección de entrega.
	def test_create_order_returns_400_when_delivery_address_is_missing(self):
		order_dao = Mock()
		reservation_dao = Mock()
		restaurant_dao = Mock()
		menu_dao = Mock()

		menu_dao.get_by_id.return_value = SimpleNamespace(
			id=1,
			restaurante_id=1,
			precio=6500,
			disponible=True,
		)

		order = OrderCreate(
			restaurante_id=1,
			items=[OrderItem(menu_id=1, cantidad=1)],
			tipo_entrega=TipoEntregaEnum.DOMICILIO,
			direccion_entrega=None,
			notas="Urgente",
		)

		with pytest.raises(HTTPException) as exc_info:
			create_order(order_dao, reservation_dao, restaurant_dao, menu_dao, order, 2)

		assert exc_info.value.status_code == 400
