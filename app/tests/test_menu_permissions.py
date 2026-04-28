def test_menu_create_ok_si_admin_dueno(client, create_test_data, test_db, auth_headers):
    admin = create_test_data["create_user"](email="adminmenu@test.com", nombre="Admin", rol="admin")
    restaurant = create_test_data["create_restaurant"](nombre="RestMenu", admin_id=admin.id)

    payload = {
        "nombre": "Hamburguesa",
        "descripcion": "Desc",
        "precio": 10.0,
        "disponible": True,
        "restaurante_id": restaurant.id,
    }

    r = client.post("/menus/", json=payload, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["restaurante_id"] == restaurant.id


def test_menu_create_forbidden_si_admin_no_es_dueno(client, create_test_data, auth_headers):
    admin1 = create_test_data["create_user"](email="admin1@test.com", nombre="Admin1", rol="admin")
    admin2 = create_test_data["create_user"](email="admin2@test.com", nombre="Admin2", rol="admin")
    restaurant = create_test_data["create_restaurant"](nombre="RestOther", admin_id=admin2.id)

    payload = {
        "nombre": "Pizza",
        "precio": 12.0,
        "restaurante_id": restaurant.id,
    }

    r = client.post("/menus/", json=payload, headers=auth_headers)
    assert r.status_code == 403


def test_menu_create_forbidden_si_cliente(client, create_test_data, auth_headers):
    user = create_test_data["create_user"](email="cliente@test.com", nombre="Cliente", rol="cliente")
    restaurant = create_test_data["create_restaurant"](nombre="Rest", admin_id=user.id)

    payload = {
        "nombre": "Taco",
        "precio": 5.0,
        "restaurante_id": restaurant.id,
    }

    r = client.post("/menus/", json=payload, headers=auth_headers)
    assert r.status_code == 403
