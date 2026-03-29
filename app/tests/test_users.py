from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import create_user, deactivate_user


def test_create_user_endpoint_ok(client):
	payload = {
		"email": "users_ok@test.com",
		"nombre": "Users OK",
		"password": "Password123!",
		"rol": "cliente",
	}

	response = client.post("/users/", json=payload)

	assert response.status_code == 201
	body = response.json()
	assert body["email"] == payload["email"]
	assert body["activo"] is True


def test_create_user_endpoint_email_duplicado(client):
	payload = {
		"email": "dup@test.com",
		"nombre": "Duplicado",
		"password": "Password123!",
		"rol": "cliente",
	}

	first = client.post("/users/", json=payload)
	second = client.post("/users/", json=payload)

	assert first.status_code == 201
	assert second.status_code == 400
	assert "Ya existe" in second.json()["detail"]


def test_update_user_forbidden_si_no_es_owner_ni_admin(client, test_db, create_test_data, auth_headers):
	_auth_user = create_test_data["create_user"](email="auth@test.com", nombre="Auth", rol="cliente")
	owner = create_test_data["create_user"](email="owner@test.com", nombre="Owner", rol="cliente")

	response = client.put(
		f"/users/{owner.id}",
		json={"nombre": "Nuevo Nombre"},
		headers=auth_headers,
	)

	# El mock de auth en conftest autentica siempre al primer usuario creado,
	# por eso intentar editar al segundo usuario debe bloquearse.
	assert response.status_code == 403
	assert "No tiene permiso" in response.json()["detail"]


def test_create_user_service_devuelve_none_si_email_existe(test_db, create_test_data):
	create_test_data["create_user"](email="exists@test.com", nombre="Exists")

	created = create_user(
		test_db,
		UserCreate(
			email="exists@test.com",
			nombre="Nuevo",
			password="Password123!",
			rol="cliente",
		),
	)

	assert created is None


def test_deactivate_user_service_desactiva_usuario(test_db, create_test_data):
	user = create_test_data["create_user"](email="active@test.com", nombre="Active")

	result = deactivate_user(test_db, user.id)

	assert result is not None
	assert result.activo is False
