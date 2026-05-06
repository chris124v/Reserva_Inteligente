# Pruebas de integración para MongoDB en la capa de DAOs.
# Validan serialización, filtros y valores por defecto.

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.dao.factory import DAOFactory
from app.models.order import EstadoPedidoEnum, TipoEntregaEnum
from app.models.reservation import EstadoReservaEnum
from app.models.user import RoleEnum


# Verifica que el rol se guarda como texto al actualizar un usuario.
def test_mongodb_user_update_serializes_role_enum():
	users_collection = Mock()
	users_collection.find_one.return_value = {
		"id": 1,
		"email": "admin@test.com",
		"nombre": "Admin",
		"password_hash": "hash",
		"rol": "admin",
		"activo": False,
	}

	with patch("app.database.mongo.get_mongo_db", return_value={"users": users_collection}):
		dao = DAOFactory.get_user_dao("mongodb", None)
		result = dao.update(SimpleNamespace(id=1), {"rol": RoleEnum.ADMIN, "activo": False})

	users_collection.update_one.assert_called_once_with(
		{"id": 1},
		{"$set": {"rol": "admin", "activo": False}},
	)
	assert result.rol == RoleEnum.ADMIN
	assert result.activo is False


# Verifica que el filtro por admin funciona y las horas se parsean bien.
def test_mongodb_restaurant_get_by_admin_parses_time_fields():
	restaurants_collection = Mock()
	restaurants_collection.find.return_value = [
		{
			"id": 1,
			"nombre": "Rest 1",
			"descripcion": "desc",
			"direccion": "San Jose",
			"telefono": "88888888",
			"email": "rest1@test.com",
			"hora_apertura": "08:00:00",
			"hora_cierre": "20:00:00",
			"total_mesas": 12,
			"admin_id": 7,
		}
	]

	with patch("app.database.mongo.get_mongo_db", return_value={"restaurants": restaurants_collection}):
		dao = DAOFactory.get_restaurant_dao("mongodb", None)
		result = dao.get_by_admin(7)

	restaurants_collection.find.assert_called_once_with({"admin_id": 7})
	assert len(result) == 1
	assert result[0].hora_apertura.hour == 8
	assert result[0].hora_cierre.hour == 20


# Verifica que al crear una orden se guarda el estado inicial correcto.
def test_mongodb_order_create_sets_pending_state_and_serializes_delivery_type():
	orders_collection = Mock()
	orders_collection.find_one.return_value = {"id": 10}

	with patch("app.database.mongo.get_mongo_db", return_value={"orders": orders_collection}):
		dao = DAOFactory.get_order_dao("mongodb", None)
		created = dao.create(
			{
				"usuario_id": 1,
				"restaurante_id": 2,
				"items": [{"menu_id": 5, "cantidad": 2}],
				"subtotal": 10000,
				"impuesto": 1300,
				"total": 11300,
				"tipo_entrega": TipoEntregaEnum.DOMICILIO,
				"direccion_entrega": "Curridabat",
				"notas": "sin cebolla",
			}
		)

	inserted_doc = orders_collection.insert_one.call_args[0][0]
	assert inserted_doc["id"] == 11
	assert inserted_doc["tipo_entrega"] == "domicilio"
	assert inserted_doc["estado"] == "pendiente"
	assert created.estado == EstadoPedidoEnum.PENDIENTE
	assert created.tipo_entrega == TipoEntregaEnum.DOMICILIO


# Verifica que el conteo de reservas usa los filtros correctos.
def test_mongodb_reservation_count_active_builds_expected_query():
	reservations_collection = Mock()
	reservations_collection.count_documents.return_value = 3
	target_date = date(2026, 5, 6)

	with patch("app.database.mongo.get_mongo_db", return_value={"reservations": reservations_collection}):
		dao = DAOFactory.get_reservation_dao("mongodb", None)
		total = dao.count_reservas_activas(4, target_date)

	reservations_collection.count_documents.assert_called_once_with(
		{
			"restaurante_id": 4,
			"fecha": "2026-05-06",
			"estado": "reservada",
		}
	)
	assert total == 3


# Verifica que las mesas ocupadas se devuelven sin duplicados.
def test_mongodb_reservation_get_mesas_ocupadas_returns_unique_set():
	reservations_collection = Mock()
	reservations_collection.find.return_value = [
		{"numero_mesa": 2},
		{"numero_mesa": 2},
		{"numero_mesa": 5},
	]
	target_date = date(2026, 5, 6)

	with patch("app.database.mongo.get_mongo_db", return_value={"reservations": reservations_collection}):
		dao = DAOFactory.get_reservation_dao("mongodb", None)
		mesas = dao.get_mesas_ocupadas(9, target_date)

	reservations_collection.find.assert_called_once_with(
		{
			"restaurante_id": 9,
			"fecha": "2026-05-06",
			"estado": "reservada",
			"numero_mesa": {"$ne": None},
		},
		{"numero_mesa": 1, "_id": 0},
	)
	assert mesas == {2, 5}
