"""
Unit tests para search_service (Elasticsearch).
Pruebas unitarias que validan la lógica de indexación y búsqueda sin ES real.

Cobertura esperada: >95% de search_service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from types import SimpleNamespace

# Mock elasticsearch antes de importar search_service
if "elasticsearch" not in sys.modules:
    class _FakeElasticsearch:
        def __init__(self, *a, **k):
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


# create_menus_index: Verifica que el índice se crea solo si no existe
def test_create_menus_index_when_not_exists(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = False
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import create_menus_index
    create_menus_index()
    
    mock_es.indices.create.assert_called_once()
    assert "mappings" in mock_es.indices.create.call_args[1]["body"]


# create_menus_index: No crea índice si ya existe
def test_create_menus_index_when_exists(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = True
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import create_menus_index
    create_menus_index()
    
    mock_es.indices.create.assert_not_called()


# index_menu: Indexa un menú con atributos extraídos correctamente
def test_index_menu_extracts_attributes(monkeypatch):
    mock_es = Mock()
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import index_menu
    
    mock_menu = Mock()
    mock_menu.id = 1
    mock_menu.nombre = "Pizza"
    mock_menu.categoria = "italiana"
    mock_menu.descripcion = "Pizza clásica"
    mock_menu.precio = 5000.0
    mock_menu.disponible = True
    mock_menu.tiempo_preparacion = 20
    mock_menu.restaurante_id = 1
    
    index_menu(mock_menu)
    
    mock_es.index.assert_called_once()
    call_args = mock_es.index.call_args
    doc = call_args[1]["document"]
    
    assert doc["id"] == "1"
    assert doc["nombre"] == "Pizza"
    assert doc["categoria"] == "italiana"


# index_menu: Usa descripción por defecto si falta
def test_index_menu_default_description(monkeypatch):
    mock_es = Mock()
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import index_menu
    
    mock_menu = Mock()
    mock_menu.id = 1
    mock_menu.nombre = "Item"
    mock_menu.categoria = "cat"
    mock_menu.descripcion = None
    mock_menu.precio = 100.0
    mock_menu.disponible = True
    mock_menu.tiempo_preparacion = 10
    mock_menu.restaurante_id = 1
    
    index_menu(mock_menu)
    
    doc = mock_es.index.call_args[1]["document"]
    assert doc["descripcion"] == "Producto sin descripción"


# search_menus: Retorna lista de menús encontrados
def test_search_menus_returns_results(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = True
    mock_es.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"id": "1", "nombre": "Pizza"}},
                {"_source": {"id": "2", "nombre": "Pasta"}}
            ]
        }
    }
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import search_menus
    result = search_menus("pasta")
    
    assert len(result) == 2
    assert result[0]["nombre"] == "Pizza"
    assert result[1]["nombre"] == "Pasta"


# search_menus: Devuelve lista vacía si no hay resultados
def test_search_menus_empty_results(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = True
    mock_es.search.return_value = {"hits": {"hits": []}}
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import search_menus
    result = search_menus("inexistente")
    
    assert result == []


# search_menus_by_category: Retorna menús de categoría específica
def test_search_menus_by_category_returns_filtered(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = True
    mock_es.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"id": "1", "categoria": "pizza"}},
                {"_source": {"id": "2", "categoria": "pizza"}}
            ]
        }
    }
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import search_menus_by_category
    result = search_menus_by_category("pizza")
    
    assert len(result) == 2
    mock_es.search.assert_called_once()
    query = mock_es.search.call_args[1]["query"]
    assert "term" in query


# reindex_menus: Elimina índice anterior y crea uno nuevo
def test_reindex_menus_deletes_and_creates(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = True
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import reindex_menus
    
    mock_menu1 = Mock()
    mock_menu1.id = 1
    mock_menu1.nombre = "Item1"
    mock_menu1.categoria = "cat"
    mock_menu1.descripcion = "desc"
    mock_menu1.precio = 100.0
    mock_menu1.disponible = True
    mock_menu1.tiempo_preparacion = 10
    mock_menu1.restaurante_id = 1
    
    result = reindex_menus([mock_menu1])
    
    mock_es.indices.delete.assert_called_once_with(index="menus")
    mock_es.indices.refresh.assert_called_once()
    assert result["total_indexed"] == 1


# reindex_menus: Retorna mensaje con cantidad indexada
def test_reindex_menus_returns_correct_count(monkeypatch):
    mock_es = Mock()
    mock_es.indices.exists.return_value = True
    
    monkeypatch.setattr("app.services.search_service.es_client", mock_es)
    
    from app.services.search_service import reindex_menus
    
    menus = [Mock(id=i, nombre=f"Item{i}", categoria="cat", descripcion="desc",
                   precio=100.0, disponible=True, tiempo_preparacion=10, 
                   restaurante_id=1) for i in range(5)]
    
    result = reindex_menus(menus)
    
    assert result["message"] == "Menus reindexed successfully"
    assert result["total_indexed"] == 5
