from datetime import time

from app.schemas.restaurant import RestaurantCreate
from app.services.restaurant_service import create_restaurant


def test_create_restaurant_endpoint_ok(client, create_test_data, test_restaurant_data, auth_headers):
	create_test_data["create_user"](email="admin1@test.com", nombre="Admin Uno", rol="cliente")

	response = client.post("/restaurants/", json=test_restaurant_data, headers=auth_headers)

	assert response.status_code == 201
	body = response.json()
	assert body["nombre"] == test_restaurant_data["nombre"]
	assert body["admin_id"] == 1


def test_update_restaurant_forbidden_si_no_es_admin(client, create_test_data, auth_headers):
	# Primer usuario = autenticado por el mock.
	create_test_data["create_user"](email="u1@test.com", nombre="U1", rol="cliente")
	admin2 = create_test_data["create_user"](email="u2@test.com", nombre="U2", rol="cliente")
	restaurant = create_test_data["create_restaurant"](nombre="R2", admin_id=admin2.id)

	response = client.put(
		f"/restaurants/{restaurant.id}",
		json={"telefono": "9999-0000"},
		headers=auth_headers,
	)

	assert response.status_code == 403
	assert "No tiene permiso" in response.json()["detail"]


def test_list_restaurants_es_publico(client, create_test_data):
	owner = create_test_data["create_user"](email="owner@test.com", nombre="Owner", rol="cliente")
	create_test_data["create_restaurant"](nombre="Publico", admin_id=owner.id)

	response = client.get("/restaurants/")

	assert response.status_code == 200
	assert isinstance(response.json(), list)
	assert len(response.json()) >= 1


def test_create_restaurant_service_devuelve_none_en_email_duplicado(test_db, create_test_data):
	owner = create_test_data["create_user"](email="owner2@test.com", nombre="Owner2", rol="cliente")
	create_test_data["create_restaurant"](nombre="Original", admin_id=owner.id)

	created = create_restaurant(
		test_db,
		RestaurantCreate(
			nombre="Duplicado",
			descripcion="desc",
			direccion="Dir 1",
			telefono="555-1111",
			email="original@test.com",
			hora_apertura=time(9, 0),
			hora_cierre=time(22, 0),
			total_mesas=10,
		),
		admin_id=owner.id,
	)

	assert created is None
