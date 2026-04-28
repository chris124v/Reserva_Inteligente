from datetime import date, time, timedelta

import pytest

from app.schemas.reservation import ReservationCreate
from app.services.reservation_service import check_disponibilidad


def test_create_reservation_endpoint_ok(client, create_test_data, auth_headers):
	user = create_test_data["create_user"](email="resuser@test.com", nombre="ResUser", rol="cliente")
	restaurant = create_test_data["create_restaurant"](nombre="Res R", admin_id=user.id)

	payload = {
		"restaurante_id": restaurant.id,
		"fecha": (date.today() + timedelta(days=2)).isoformat(),
		"hora": "20:00:00",
		"cantidad_personas": 4,
		"notas": "Mesa interior",
	}

	response = client.post("/reservations/", json=payload, headers=auth_headers)

	assert response.status_code == 201
	body = response.json()
	assert body["restaurante_id"] == restaurant.id
	assert body["estado"] == "reservada"
	assert body["numero_mesa"] is not None
	assert 1 <= body["numero_mesa"] <= restaurant.total_mesas


def test_create_reservation_forbidden_si_es_admin(client, create_test_data, auth_headers):
	admin = create_test_data["create_user"](email="adminres@test.com", nombre="AdminRes", rol="admin")
	restaurant = create_test_data["create_restaurant"](nombre="Res R2", admin_id=admin.id)

	payload = {
		"restaurante_id": restaurant.id,
		"fecha": (date.today() + timedelta(days=2)).isoformat(),
		"hora": "20:00:00",
		"cantidad_personas": 2,
	}

	response = client.post("/reservations/", json=payload, headers=auth_headers)
	assert response.status_code == 403


def test_list_my_reservations_forbidden_si_es_admin(client, create_test_data, auth_headers):
	create_test_data["create_user"](email="adminlist@test.com", nombre="AdminList", rol="admin")

	response = client.get("/reservations/", headers=auth_headers)
	assert response.status_code == 403


def test_list_reservations_by_restaurante_forbidden_si_no_es_admin_dueno(client, create_test_data, auth_headers):
	admin1 = create_test_data["create_user"](email="a1@test.com", nombre="A1", rol="admin")
	admin2 = create_test_data["create_user"](email="a2@test.com", nombre="A2", rol="admin")
	restaurant = create_test_data["create_restaurant"](nombre="Rest", admin_id=admin2.id)

	# auth_headers apunta al primer usuario creado (admin1)
	response = client.get(f"/reservations/restaurante/{restaurant.id}", headers=auth_headers)
	assert response.status_code == 403


def test_get_reservation_endpoint_removed(client, create_test_data, test_db, auth_headers):
	user = create_test_data["create_user"](email="u1r@test.com", nombre="U1", rol="cliente")
	restaurant = create_test_data["create_restaurant"](nombre="RestX", admin_id=user.id)

	from app.models.reservation import Reservation

	reservation = Reservation(
		usuario_id=user.id,
		restaurante_id=restaurant.id,
		fecha=date.today() + timedelta(days=2),
		hora=time(21, 0),
		cantidad_personas=2,
		notas="x",
	)
	test_db.add(reservation)
	test_db.commit()
	test_db.refresh(reservation)

	response = client.get(f"/reservations/{reservation.id}", headers=auth_headers)
	assert response.status_code == 405


def test_cancel_reservation_endpoint_cambia_estado(client, create_test_data, test_db, auth_headers):
	user = create_test_data["create_user"](email="cancel@test.com", nombre="Cancel", rol="cliente")
	restaurant = create_test_data["create_restaurant"](nombre="Cancel R", admin_id=user.id)

	from app.models.reservation import Reservation

	reservation = Reservation(
		usuario_id=user.id,
		restaurante_id=restaurant.id,
		fecha=date.today() + timedelta(days=2),
		hora=time(19, 30),
		cantidad_personas=3,
		notas="cancelar",
	)
	test_db.add(reservation)
	test_db.commit()
	test_db.refresh(reservation)

	response = client.delete(f"/reservations/{reservation.id}", headers=auth_headers)

	assert response.status_code == 204

	from app.models.reservation import Reservation

	refreshed = test_db.query(Reservation).filter_by(id=reservation.id).first()
	assert refreshed.estado.value == "cancelada"


def test_check_disponibilidad_false_cuando_no_hay_mesas(test_db):
	from app.models.reservation import Reservation, EstadoReservaEnum

	fecha = date.today() + timedelta(days=3)
	hora = time(20, 0)
	restaurante_id = 50

	for i in range(2):
		test_db.add(
			Reservation(
				usuario_id=i + 1,
				restaurante_id=restaurante_id,
				fecha=fecha,
				hora=hora,
				cantidad_personas=2,
				estado=EstadoReservaEnum.RESERVADA,
				notas="ocupada",
			)
		)
	test_db.commit()

	available = check_disponibilidad(
		test_db,
		restaurante_id=restaurante_id,
		fecha=fecha,
		hora=hora,
		total_mesas=2,
	)

	assert available is False


def test_create_reservation_schema_rechaza_fecha_pasada():
	with pytest.raises(ValueError):
		ReservationCreate(
			restaurante_id=1,
			fecha=date.today() - timedelta(days=1),
			hora=time(19, 0),
			cantidad_personas=2,
			notas="pasada",
		)
