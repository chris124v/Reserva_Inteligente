# Pruebas de integración para validar el uso de cache en la app.

from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient


# Crea una app mínima para probar restaurantes con dependencias simuladas.
def _restaurants_client(restaurant_dao: Mock) -> TestClient:
	from app.routes import restaurants as restaurants_routes

	app = FastAPI()
	app.include_router(restaurants_routes.router)
	app.dependency_overrides[restaurants_routes.get_restaurant_dao] = lambda: restaurant_dao
	return TestClient(app)


# Crea una app mínima para probar menús con dependencias simuladas.
def _menus_client(menu_dao: Mock, user_dao: Mock | None = None, restaurant_dao: Mock | None = None) -> TestClient:
	from app.routes import menus as menus_routes

	app = FastAPI()
	app.include_router(menus_routes.router)
	app.dependency_overrides[menus_routes.get_menu_dao] = lambda: menu_dao
	app.dependency_overrides[menus_routes.get_user_dao] = lambda: (user_dao or Mock())
	app.dependency_overrides[menus_routes.get_restaurant_dao] = lambda: (restaurant_dao or Mock())
	app.dependency_overrides[menus_routes.verify_jwt] = lambda: {"sub": "user-1"}
	return TestClient(app)


# Verifica que la cache evita consultar el DAO cuando ya existe el dato.
def test_list_restaurants_cache_hit_returns_cached_data(monkeypatch):
	from app.routes import restaurants as restaurants_routes

	restaurant_dao = Mock()
	restaurant_dao.get_all.return_value = [{"id": 99}]
	client = _restaurants_client(restaurant_dao)

	cached_payload = [
		{
			"id": 1,
			"admin_id": 1,
			"nombre": "Rest Cached",
			"descripcion": "desc",
			"direccion": "San Jose",
			"telefono": "88888888",
			"email": "rest1@test.com",
			"hora_apertura": "08:00:00",
			"hora_cierre": "20:00:00",
			"total_mesas": 20,
		}
	]
	monkeypatch.setattr(restaurants_routes.cache_service, "get", lambda key: cached_payload)
	set_spy = Mock()
	monkeypatch.setattr(restaurants_routes.cache_service, "set", set_spy)

	response = client.get("/restaurants/?skip=0&limit=10")

	assert response.status_code == 200
	assert response.json() == cached_payload
	restaurant_dao.get_all.assert_not_called()
	set_spy.assert_not_called()


# Verifica que la cache se llena cuando no hay dato previo.
def test_list_restaurants_cache_miss_queries_dao_and_sets_cache(monkeypatch):
	from app.routes import restaurants as restaurants_routes

	restaurant_rows = [
		{
			"id": 1,
			"admin_id": 1,
			"nombre": "Rest 1",
			"descripcion": "desc",
			"direccion": "Heredia",
			"telefono": "88888888",
			"email": "r1@test.com",
			"hora_apertura": "08:00:00",
			"hora_cierre": "20:00:00",
			"total_mesas": 10,
		},
		{
			"id": 2,
			"admin_id": 1,
			"nombre": "Rest 2",
			"descripcion": "desc",
			"direccion": "Cartago",
			"telefono": "87777777",
			"email": "r2@test.com",
			"hora_apertura": "09:00:00",
			"hora_cierre": "21:00:00",
			"total_mesas": 12,
		},
	]
	restaurant_dao = Mock()
	restaurant_dao.get_all.return_value = restaurant_rows
	client = _restaurants_client(restaurant_dao)

	monkeypatch.setattr(restaurants_routes.cache_service, "get", lambda key: None)
	set_spy = Mock()
	monkeypatch.setattr(restaurants_routes.cache_service, "set", set_spy)

	response = client.get("/restaurants/?skip=0&limit=1")

	assert response.status_code == 200
	assert len(response.json()) == 1
	restaurant_dao.get_all.assert_called_once()
	set_spy.assert_called_once()
	assert set_spy.call_args[0][0] == "restaurants:all:0:1"


# Verifica que el listado de menús usa cache cuando ya existe.
def test_list_menus_by_restaurant_uses_cache_hit(monkeypatch):
	from app.routes import menus as menus_routes

	menu_dao = Mock()
	menu_dao.get_by_restaurante.return_value = []
	client = _menus_client(menu_dao)

	cached_payload = [
		{
			"id": 10,
			"restaurante_id": 1,
			"nombre": "Pizza",
			"descripcion": "Margarita",
			"precio": 4500,
			"disponible": True,
			"tiempo_preparacion": 15,
			"categoria": "italiana",
		}
	]
	monkeypatch.setattr(menus_routes.cache_service, "get", lambda key: cached_payload)
	set_spy = Mock()
	monkeypatch.setattr(menus_routes.cache_service, "set", set_spy)

	response = client.get("/menus/?restaurante_id=1")

	assert response.status_code == 200
	assert response.json() == cached_payload
	menu_dao.get_by_restaurante.assert_not_called()
	set_spy.assert_not_called()


# Verifica que el detalle de menú se guarda en cache al consultarlo.
def test_get_menu_cache_miss_queries_dao_and_sets_cache(monkeypatch):
	from app.routes import menus as menus_routes

	menu_payload = {
		"id": 20,
		"restaurante_id": 2,
		"nombre": "Pasta",
		"descripcion": "Alfredo",
		"precio": 5200,
		"disponible": True,
		"tiempo_preparacion": 18,
		"categoria": "italiana",
	}
	menu_dao = Mock()
	menu_dao.get_by_id.return_value = menu_payload
	client = _menus_client(menu_dao)

	monkeypatch.setattr(menus_routes.cache_service, "get", lambda key: None)
	set_spy = Mock()
	monkeypatch.setattr(menus_routes.cache_service, "set", set_spy)

	response = client.get("/menus/20")

	assert response.status_code == 200
	assert response.json()["id"] == 20
	menu_dao.get_by_id.assert_called_once_with(20)
	set_spy.assert_called_once()
	assert set_spy.call_args[0][0] == "menu:20"


# Verifica que crear un menú limpia las claves relacionadas.
def test_create_menu_invalidates_cache_patterns(monkeypatch):
	from app.routes import menus as menus_routes

	menu_dao = Mock()
	menu_dao.create.return_value = {
		"id": 30,
		"restaurante_id": 1,
		"nombre": "Pollo",
		"descripcion": "Pollo al horno",
		"precio": 6000,
		"disponible": True,
		"tiempo_preparacion": 25,
		"categoria": "principal",
	}
	client = _menus_client(menu_dao)

	monkeypatch.setattr(menus_routes, "resolve_current_local_user_id", lambda payload, user_dao: 1)
	monkeypatch.setattr(menus_routes, "validate_menu_admin", lambda *args, **kwargs: None)
	delete_pattern_spy = Mock()
	monkeypatch.setattr(menus_routes.cache_service, "delete_pattern", delete_pattern_spy)

	body = {
		"nombre": "Pollo",
		"descripcion": "Pollo al horno",
		"precio": 6000,
		"disponible": True,
		"tiempo_preparacion": 25,
		"categoria": "principal",
	}
	response = client.post("/menus/?restaurante_id=1", json=body)

	assert response.status_code == 201
	delete_pattern_spy.assert_any_call("menus:*")
	delete_pattern_spy.assert_any_call("menu:*")
	assert delete_pattern_spy.call_count == 2
