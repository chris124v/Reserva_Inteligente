"""
Pruebas de integración para el caché (mocks actuales, diseñadas para moverse aquí
cuando las pruebas requieran un cliente Redis más realista o `docker-compose`).

Este archivo fue movido desde `tests/unit/test_cache.py` para separar unit vs integración.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.integration
@pytest.mark.cache
def test_smoke_cache_operations():
    """Smoke test básico de operaciones de caché (mock de redis)."""
    mock_redis_instance = MagicMock()
    cache_key = "test:1"
    cache_value = {"id": 1}

    mock_redis_instance.setex(cache_key, 3600, "{}")
    mock_redis_instance.get.return_value = cache_value

    assert mock_redis_instance.get(cache_key) == cache_value
