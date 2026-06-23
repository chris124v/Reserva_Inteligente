# Pruebas de integración para los endpoints del buscador.

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# Evita depender de Elasticsearch real al importar el servicio.
if "elasticsearch" not in sys.modules:
    class _FakeElasticsearch:
        def __init__(self, *args, **kwargs):
            pass

        class indices:
            @staticmethod
            def exists(index=None):
                return False

            @staticmethod
            def create(index=None, body=None):
                return None

            @staticmethod
            def delete(index=None):
                return None

            @staticmethod
            def refresh(index=None):
                return None

        def search(self, **kwargs):
            return {"hits": {"hits": []}}

        def index(self, **kwargs):
            return None

    sys.modules["elasticsearch"] = SimpleNamespace(Elasticsearch=_FakeElasticsearch)


# Crea una app mínima para probar el router de búsqueda.
@pytest.fixture
def client():
    from search_service.app.routes.search import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# Verifica que la búsqueda devuelve resultados.
def test_get_search_menus_returns_results(client, monkeypatch):
    expected = [{"id": "1", "nombre": "Pollo al Ajillo"}]
    monkeypatch.setattr("search_service.app.routes.search.search_menus", lambda q: expected)

    response = client.get("/search/menus", params={"q": "pollo"})

    assert response.status_code == 200
    assert response.json() == expected


# Verifica que la búsqueda devuelve lista vacía si no hay coincidencias.
def test_get_search_menus_returns_empty_list(client, monkeypatch):
    monkeypatch.setattr("search_service.app.routes.search.search_menus", lambda q: [])

    response = client.get("/search/menus", params={"q": "inexistente"})

    assert response.status_code == 200
    assert response.json() == []


# Verifica que el filtro por categoría devuelve datos.
def test_get_search_menus_by_category_returns_results(client, monkeypatch):
    expected = [
        {"id": "10", "nombre": "Pizza Margarita", "categoria": "pizza"},
        {"id": "11", "nombre": "Pizza Pepperoni", "categoria": "pizza"},
    ]
    monkeypatch.setattr(
        "search_service.app.routes.search.search_menus_by_category",
        lambda categoria: expected,
    )

    response = client.get("/search/menus/category/pizza")

    assert response.status_code == 200
    assert response.json() == expected


# Verifica que el filtro por categoría puede devolver vacío.
def test_get_search_menus_by_category_returns_empty_list(client, monkeypatch):
    monkeypatch.setattr("search_service.app.routes.search.search_menus_by_category", lambda categoria: [])

    response = client.get("/search/menus/category/postres")

    assert response.status_code == 200
    assert response.json() == []


# Verifica que reindex responde con el resumen correcto.
def test_post_reindex_calls_upstream_and_returns_summary(client, monkeypatch):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [{"id": "1", "nombre": "Pollo"}]

    mock_http_client = Mock()
    mock_http_client.get.return_value = mock_response

    class _FakeClientContext:
        def __init__(self, fake_client):
            self.fake_client = fake_client

        def __enter__(self):
            return self.fake_client

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "search_service.app.routes.search.httpx.Client",
        lambda timeout=30.0, follow_redirects=False: _FakeClientContext(mock_http_client),
    )
    monkeypatch.setattr(
        "search_service.app.routes.search.reindex_menus",
        lambda menus: {"message": "Menus reindexed successfully", "total_indexed": len(menus)},
    )

    response = client.post("/search/reindex")

    assert response.status_code == 200
    assert response.json() == {"message": "Menus reindexed successfully", "total_indexed": 1}


# Verifica que reindex devuelve error si falla la fuente de datos.
def test_post_reindex_returns_error_when_upstream_fails(client, monkeypatch):
    class _FailingClientContext:
        def __enter__(self):
            raise RuntimeError("upstream unavailable")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "search_service.app.routes.search.httpx.Client",
        lambda timeout=30.0, follow_redirects=False: _FailingClientContext(),
    )

    response = client.post("/search/reindex")

    assert response.status_code == 200
    assert "error" in response.json()
    assert "upstream unavailable" in response.json()["error"]
