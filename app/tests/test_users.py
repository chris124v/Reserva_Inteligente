from app.services.user_service import deactivate_user


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


def test_listar_usuarios_endpoint_ok(client, test_db, create_test_data, auth_headers):
	user1 = create_test_data["create_user"](email="user1@test.com", nombre="User 1")
	user2 = create_test_data["create_user"](email="user2@test.com", nombre="User 2")

	response = client.get("/users/", headers=auth_headers)

	assert response.status_code == 200
	body = response.json()
	assert len(body) >= 2


def test_deactivate_user_service_desactiva_usuario(test_db, create_test_data):
	user = create_test_data["create_user"](email="active@test.com", nombre="Active")

	result = deactivate_user(test_db, user.id)

	assert result is not None
	assert result.activo is False


def test_delete_user_endpoint_desactiva_en_vez_de_borrar(client, test_db, create_test_data, auth_headers):
	# El mock de auth en conftest autentica siempre al primer usuario creado.
	user = create_test_data["create_user"](email="deleteme@test.com", nombre="Delete Me")

	response = client.delete(f"/users/{user.id}", headers=auth_headers)
	assert response.status_code == 204

	refreshed = test_db.query(type(user)).filter_by(id=user.id).first()
	assert refreshed is not None
	assert refreshed.activo is False


def test_admin_no_puede_actualizar_otro_user_sin_master_code(client, test_db, create_test_data, auth_headers):
	from unittest.mock import patch
	from app.routes import users as users_routes

	create_test_data["create_user"](email="admin@test.com", nombre="Admin", rol="admin")
	other = create_test_data["create_user"](email="other@test.com", nombre="Other", rol="cliente")

	with patch.object(users_routes.settings, "MASTER_ADMIN_CODE", "master"):
		r = client.put(f"/users/{other.id}", json={"nombre": "Nuevo"}, headers=auth_headers)
	assert r.status_code == 403


def test_admin_puede_actualizar_otro_user_con_master_code(client, test_db, create_test_data, auth_headers):
	from unittest.mock import patch
	from app.routes import users as users_routes

	create_test_data["create_user"](email="admin2@test.com", nombre="Admin2", rol="admin")
	other = create_test_data["create_user"](email="other2@test.com", nombre="Other2", rol="cliente")

	with patch.object(users_routes.settings, "MASTER_ADMIN_CODE", "master"):
		r = client.put(
			f"/users/{other.id}",
			json={"nombre": "Nuevo Nombre"},
			headers={**auth_headers, "X-Master-Admin-Code": "master"},
		)
	assert r.status_code == 200
	assert r.json()["nombre"] == "Nuevo Nombre"


def test_admin_no_puede_eliminar_otro_user_sin_master_code(client, test_db, create_test_data, auth_headers):
	from unittest.mock import patch
	from app.routes import users as users_routes

	create_test_data["create_user"](email="admin3@test.com", nombre="Admin3", rol="admin")
	other = create_test_data["create_user"](email="other3@test.com", nombre="Other3", rol="cliente")

	with patch.object(users_routes.settings, "MASTER_ADMIN_CODE", "master"):
		r = client.delete(f"/users/{other.id}", headers=auth_headers)
	assert r.status_code == 403


def test_admin_puede_actualizar_su_propio_user_sin_master_code(client, test_db, create_test_data, auth_headers):
	# El mock de auth en conftest autentica siempre al primer usuario creado.
	admin = create_test_data["create_user"](email="selfadmin@test.com", nombre="Self Admin", rol="admin")

	r = client.put(
		f"/users/{admin.id}",
		json={"nombre": "Admin Actualizado"},
		headers=auth_headers,
	)
	assert r.status_code == 200
	assert r.json()["nombre"] == "Admin Actualizado"


def test_cliente_puede_actualizar_su_propio_user_sin_master_code(client, test_db, create_test_data, auth_headers):
	cliente = create_test_data["create_user"](email="selfcliente@test.com", nombre="Self Cliente", rol="cliente")

	r = client.put(
		f"/users/{cliente.id}",
		json={"nombre": "Cliente Actualizado"},
		headers=auth_headers,
	)
	assert r.status_code == 200
	assert r.json()["nombre"] == "Cliente Actualizado"


def test_update_email_sincroniza_con_cognito(client, test_db, create_test_data, auth_headers):
	from unittest.mock import patch
	from app.routes import users as users_routes

	user = create_test_data["create_user"](email="old@test.com", nombre="Old", rol="cliente")

	with patch.object(users_routes.cognito_client, "update_user_email") as mock_update_email:
		r = client.put(
			f"/users/{user.id}",
			json={"email": "new@test.com"},
			headers=auth_headers,
		)

	assert r.status_code == 200
	assert r.json()["email"] == "new@test.com"
	mock_update_email.assert_called_once_with("old@test.com", "new@test.com")


def test_self_update_con_activo_igual_no_requiere_master_admin(client, test_db, create_test_data, auth_headers):
	# Caso típico de Swagger: envía `activo` aunque no se esté cambiando.
	admin = create_test_data["create_user"](email="swaggeradmin@test.com", nombre="Swagger Admin", rol="admin")

	r = client.put(
		f"/users/{admin.id}",
		json={"nombre": "Swagger Admin 2", "activo": True},
		headers=auth_headers,
	)
	assert r.status_code == 200
	assert r.json()["nombre"] == "Swagger Admin 2"
	assert r.json()["activo"] is True


def test_self_update_cliente_con_activo_igual_no_falla(client, test_db, create_test_data, auth_headers):
	cliente = create_test_data["create_user"](email="swaggercliente@test.com", nombre="Swagger Cliente", rol="cliente")

	r = client.put(
		f"/users/{cliente.id}",
		json={"nombre": "Swagger Cliente 2", "activo": True},
		headers=auth_headers,
	)
	assert r.status_code == 200
	assert r.json()["nombre"] == "Swagger Cliente 2"
	assert r.json()["activo"] is True
