"""
Pruebas unitarias para `CacheService` (servicio de cache basado en Redis).

Cobertura principal:
- `get`: devuelve valores parseados desde JSON, maneja deshabilitado y excepciones.
- `set`: codifica a JSON y llama a `setex` con el TTL configurado; es no-op si está deshabilitado.
- `delete`: elimina una key; no hace nada si está deshabilitado y atrapa excepciones.
- `delete_pattern`: elimina múltiples keys por patrón usando `keys` + `delete`.

Estas pruebas usan `monkeypatch` para parchear `get_redis` y `settings`, por lo que
no requieren un servidor Redis real.

Cómo ejecutar (desde la raíz del proyecto):
pytest -q tests/unit/test_cache_service.py
"""

import json
import pytest
from unittest.mock import Mock

# Importar el módulo bajo prueba
from app.services import cache_service as cs_mod
from app.services.cache_service import CacheService


# `get` debe devolver el JSON parseado cuando la key existe
def test_get_returns_parsed_json_when_exists(monkeypatch):
    mock_redis = Mock()
    mock_redis.get.return_value = json.dumps({"foo": "bar"})

    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "60")

    svc = CacheService()
    result = svc.get("test:key")

    assert result == {"foo": "bar"}
    mock_redis.get.assert_called_once_with("test:key")


# Si la cache está deshabilitada, `get` no hace nada y devuelve None
def test_get_returns_none_when_disabled(monkeypatch):
    mock_redis = Mock()
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "false")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "60")

    svc = CacheService()
    assert svc.get("any") is None
    assert not mock_redis.get.called


# `get` debe capturar excepciones y devolver None
def test_get_handles_exception_and_returns_none(monkeypatch):
    mock_redis = Mock()
    mock_redis.get.side_effect = Exception("boom")

    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "60")

    svc = CacheService()
    assert svc.get("k") is None


# `set` debe codificar a JSON y llamar a `setex` con el TTL
def test_set_encodes_and_sets_with_ttl(monkeypatch):
    mock_redis = Mock()
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "123")

    svc = CacheService()
    payload = {"x": 1}
    svc.set("k1", payload)

    # verificar que setex fue llamado con key, ttl y un JSON válido
    mock_redis.setex.assert_called_once()
    called_args = mock_redis.setex.call_args[0]
    assert called_args[0] == "k1"
    assert int(called_args[1]) == 123
    # decodificar el payload JSON y comparar
    assert json.loads(called_args[2]) == payload


# `set` no hace nada cuando la cache está deshabilitada
def test_set_noop_when_disabled(monkeypatch):
    mock_redis = Mock()
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "false")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    svc.set("k", {"a": 1})
    assert not mock_redis.setex.called


# `delete` debe llamar a redis.delete cuando está habilitado
def test_delete_calls_redis_delete_when_enabled(monkeypatch):
    mock_redis = Mock()
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    svc.delete("to:remove")
    mock_redis.delete.assert_called_once_with("to:remove")


# `delete` es no-op cuando está deshabilitado
def test_delete_noop_when_disabled(monkeypatch):
    mock_redis = Mock()
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "false")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    svc.delete("k")
    assert not mock_redis.delete.called


# `delete` debe atrapar excepciones y no propagarlas
def test_delete_handles_exception_silently(monkeypatch):
    mock_redis = Mock()
    mock_redis.delete.side_effect = Exception("boom")
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    # no debe lanzar excepción
    svc.delete("k")


# `delete_pattern` debe llamar a keys y eliminar las keys devueltas
def test_delete_pattern_calls_keys_and_delete(monkeypatch):
    mock_redis = Mock()
    mock_redis.keys.return_value = [b"a:1", b"a:2"]
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    svc.delete_pattern("a:*")
    mock_redis.keys.assert_called_once_with("a:*")
    mock_redis.delete.assert_called_once()


# `delete_pattern` no hace nada si no se encuentran keys
def test_delete_pattern_no_keys_no_delete(monkeypatch):
    mock_redis = Mock()
    mock_redis.keys.return_value = []
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "true")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    svc.delete_pattern("nope:*")
    mock_redis.keys.assert_called_once_with("nope:*")
    assert not mock_redis.delete.called


# `delete_pattern` es no-op cuando la cache está deshabilitada
def test_delete_pattern_noop_when_disabled(monkeypatch):
    mock_redis = Mock()
    monkeypatch.setattr(cs_mod, "get_redis", lambda: mock_redis)
    monkeypatch.setattr(cs_mod.settings, "REDIS_ENABLED", "false")
    monkeypatch.setattr(cs_mod.settings, "REDIS_TTL", "1")

    svc = CacheService()
    svc.delete_pattern("x:*")
    assert not mock_redis.keys.called

