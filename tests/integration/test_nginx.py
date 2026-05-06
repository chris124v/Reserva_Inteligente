# Pruebas de Nginx para validar el proxy y las respuestas esperadas.

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest


NGINX_BASE_URL = os.getenv("NGINX_BASE_URL", "http://localhost:8080")


# Hace una solicitud GET y devuelve estado, cuerpo y encabezados.
def _request_json(path: str):
	url = f"{NGINX_BASE_URL}{path}"
	request = Request(url, headers={"Accept": "application/json"})

	try:
		with urlopen(request, timeout=10) as response:
			body = response.read().decode("utf-8")
			return response.status, json.loads(body), dict(response.headers)
	except HTTPError as exc:
		body = exc.read().decode("utf-8")
		parsed = json.loads(body) if body else None
		return exc.code, parsed, dict(exc.headers or {})
	except URLError as exc:
		pytest.skip(f"Nginx no disponible en {NGINX_BASE_URL}: {exc}")


# Verifica que la API responde correctamente a través de Nginx.
def test_nginx_routes_api_health():
	status, payload, headers = _request_json("/api/health")

	assert status == 200
	assert payload == {"status": "ok"}
	assert "nginx" in headers.get("Server", "").lower()


# Verifica que la búsqueda responde correctamente a través de Nginx.
def test_nginx_routes_search_menus():
	status, payload, headers = _request_json("/search/menus?q=pollo")

	assert status == 200
	assert isinstance(payload, list)
	assert len(payload) > 0
	assert any("pollo" in item.get("nombre", "").lower() for item in payload)
	assert "nginx" in headers.get("Server", "").lower()


# Verifica que la búsqueda por categoría responde correctamente.
def test_nginx_routes_search_category():
	status, payload, _ = _request_json("/search/menus/category/pizza")

	assert status == 200
	assert isinstance(payload, list)
	assert len(payload) > 0
	assert all(item.get("categoria") == "pizza" for item in payload)


# Verifica que la API no expone la búsqueda por ese prefijo.
def test_nginx_api_prefix_does_not_expose_search_route():
	status, payload, _ = _request_json("/api/search/menus?q=pollo")

	assert status == 404
	assert payload == {"detail": "Not Found"}
