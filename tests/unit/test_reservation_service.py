"""
Tests esenciales para reservation_service.py.
Se enfocan en disponibilidad, asignación de mesa y permisos.
"""

from datetime import date, time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.models.reservation import EstadoReservaEnum
from app.schemas.reservation import ReservationCreate
from app.services.reservation_service import (
	check_disponibilidad,
	create_reservation,
	validate_reservation_cancelable,
	validate_reservation_owner,
)


# Pruebas de creación y validación de reservas.
class TestCreateReservation:
# Verifica que una reserva se cree cuando hay disponibilidad.
	def test_create_reservation_success(self):
		reservation_dao = Mock()
		reservation_dao.count_reservas_activas.return_value = 3
		reservation_dao.get_mesas_ocupadas.return_value = [1, 2, 3]
		reservation_dao.create.return_value = Mock(id=100, numero_mesa=4)

		reservation = ReservationCreate(
			restaurante_id=1,
			fecha=date(2026, 6, 21),
			hora=time(19, 0),
			cantidad_personas=4,
			notas="Cena familiar",
		)

		result = create_reservation(reservation_dao, reservation, 2, 10)

		assert result.numero_mesa == 4
		reservation_dao.create.assert_called_once()

# Verifica que no se cree si no hay mesas disponibles.
	def test_create_reservation_returns_none_when_no_availability(self):
		reservation_dao = Mock()
		reservation_dao.count_reservas_activas.return_value = 10

		reservation = ReservationCreate(
			restaurante_id=1,
			fecha=date(2026, 6, 21),
			hora=time(19, 0),
			cantidad_personas=2,
			notas=None,
		)

		result = create_reservation(reservation_dao, reservation, 2, 10)

		assert result is None
		reservation_dao.create.assert_not_called()

# Verifica que no se cree si no queda ninguna mesa libre.
	def test_create_reservation_returns_none_when_no_free_table(self):
		reservation_dao = Mock()
		reservation_dao.count_reservas_activas.return_value = 2
		reservation_dao.get_mesas_ocupadas.return_value = [1, 2]

		reservation = ReservationCreate(
			restaurante_id=1,
			fecha=date(2026, 6, 21),
			hora=time(19, 0),
			cantidad_personas=2,
			notas="Ventana",
		)

		result = create_reservation(reservation_dao, reservation, 2, 2)

		assert result is None
		reservation_dao.create.assert_not_called()


# Pruebas de disponibilidad y asignación de mesa.
class TestAvailability:
# Verifica que haya disponibilidad cuando las reservas activas son menores que las mesas.
	def test_check_disponibilidad_true(self):
		reservation_dao = Mock()
		reservation_dao.count_reservas_activas.return_value = 3

		result = check_disponibilidad(reservation_dao, 1, date(2026, 6, 21), 10)

		assert result is True

# Verifica que no haya disponibilidad cuando las reservas activas llenan el local.
	def test_check_disponibilidad_false(self):
		reservation_dao = Mock()
		reservation_dao.count_reservas_activas.return_value = 10

		result = check_disponibilidad(reservation_dao, 1, date(2026, 6, 21), 10)

		assert result is False


def test_asignar_numero_mesa_returns_lowest_free():
	reservation_dao = Mock()
	# mesas ocupadas 2 y 3, total 4 -> should pick 1
	reservation_dao.get_mesas_ocupadas.return_value = [2, 3]

	from app.services.reservation_service import _asignar_numero_mesa

	numero = _asignar_numero_mesa(reservation_dao, 1, date(2026, 6, 21), 4)

	assert numero == 1


def test_asignar_numero_mesa_returns_none_when_full():
	reservation_dao = Mock()
	reservation_dao.get_mesas_ocupadas.return_value = [1, 2, 3]

	from app.services.reservation_service import _asignar_numero_mesa

	numero = _asignar_numero_mesa(reservation_dao, 1, date(2026, 6, 21), 3)

	assert numero is None


def test_create_reservation_passes_correct_payload_to_dao():
	reservation_dao = Mock()
	reservation_dao.count_reservas_activas.return_value = 0
	reservation_dao.get_mesas_ocupadas.return_value = [1]
	# ensure create returns an object for propagation
	reservation_dao.create.return_value = SimpleNamespace(id=5, numero_mesa=2)

	reservation = ReservationCreate(
		restaurante_id=7,
		fecha=date(2026, 8, 1),
		hora=time(20, 0),
		cantidad_personas=3,
		notas="Test payload",
	)

	res = create_reservation(reservation_dao, reservation, usuario_id=9, total_mesas=4)

	assert res.numero_mesa == 2
	# verify the dict passed to dao.create contains assigned numero_mesa and usuario_id
	args, kwargs = reservation_dao.create.call_args
	assert isinstance(args[0], dict)
	assert args[0]["usuario_id"] == 9
	assert "numero_mesa" in args[0]


# Pruebas de permisos sobre una reserva existente.
class TestReservationPermissions:
# Verifica que el dueño pueda modificar su propia reserva.
	def test_validate_reservation_owner_allows_owner(self):
		reservation = SimpleNamespace(usuario_id=2)

		validate_reservation_owner(reservation, 2)

# Verifica que un usuario diferente no pueda modificar la reserva.
	def test_validate_reservation_owner_rejects_other_user(self):
		reservation = SimpleNamespace(usuario_id=2)

		with pytest.raises(HTTPException) as exc_info:
			validate_reservation_owner(reservation, 3)

		assert exc_info.value.status_code == 403

# Verifica que solo se puedan cancelar reservas en estado reservada.
	def test_validate_reservation_cancelable_allows_reserved(self):
		reservation = SimpleNamespace(estado=EstadoReservaEnum.RESERVADA)

		validate_reservation_cancelable(reservation)

# Verifica que una reserva confirmada o completada no se pueda cancelar.
	def test_validate_reservation_cancelable_rejects_non_reserved(self):
		reservation = SimpleNamespace(estado=EstadoReservaEnum.CANCELADA)

		with pytest.raises(HTTPException) as exc_info:
			validate_reservation_cancelable(reservation)

		assert exc_info.value.status_code == 400
